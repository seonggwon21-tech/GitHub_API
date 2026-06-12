"""Write-path (CRUD) tests for the GitHub Issues & Labels APIs.

Unlike the read-only suites, these tests mutate real GitHub data, so they run
only against the dedicated sandbox repo provided by the `write_repo` fixture and
clean up everything they create:
  - Issues can't be hard-deleted via REST, so created issues are closed on teardown.
  - Comments and labels ARE deletable, so those teardowns delete (204).
The whole module auto-skips when no PAT with `repo` scope is configured.
"""
from uuid import uuid4

import allure
import pytest

from utils.api_client import GitHubAPIClient

pytestmark = pytest.mark.write


@pytest.fixture
def new_issue(client: GitHubAPIClient, username: str, write_repo: str):
    """Create an issue for one test, then close it on teardown.

    Yields the raw POST response so a test can assert on the 201 itself.
    """
    title = f"[qa-bot] issue {uuid4().hex[:8]}"
    response = client.post(
        f"/repos/{username}/{write_repo}/issues",
        payload={"title": title, "body": "Created by the write-path test suite."},
    )
    yield response
    # No REST hard-delete exists for issues — close it to keep the sandbox tidy.
    # Idempotent: harmless even if the test already closed it.
    if response.status_code == 201:
        number = response.json()["number"]
        client.patch(
            f"/repos/{username}/{write_repo}/issues/{number}",
            payload={"state": "closed"},
        )


@pytest.fixture
def created_label(client: GitHubAPIClient, username: str, write_repo: str):
    """Create a uniquely-named label, then delete it on teardown.

    Yields (post_response, label_name). Teardown delete is idempotent, so a test
    is free to delete the label itself.
    """
    name = f"qa-bot-{uuid4().hex[:8]}"
    response = client.post(
        f"/repos/{username}/{write_repo}/labels",
        payload={"name": name, "color": "ededed", "description": "QA write-path test label."},
    )
    yield response, name
    client.delete(f"/repos/{username}/{write_repo}/labels/{name}")


@allure.epic("GitHub REST API")
@allure.feature("Issues API (write)")
class TestIssueLifecycle:

    @allure.story("Create an issue")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_issue_returns_201(self, new_issue):
        assert new_issue.status_code == 201, new_issue.text
        body = new_issue.json()
        assert isinstance(body["number"], int)
        assert body["state"] == "open"
        assert body["title"].startswith("[qa-bot] issue ")

    @allure.story("Read back a created issue")
    def test_created_issue_is_readable(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_issue
    ):
        created = new_issue.json()
        response = client.get(f"/repos/{username}/{write_repo}/issues/{created['number']}")
        assert response.status_code == 200
        # The data we POSTed should round-trip back unchanged.
        assert response.json()["title"] == created["title"]
        assert response.json()["body"] == "Created by the write-path test suite."

    @allure.story("Update an issue")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_issue_title_returns_200(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_issue
    ):
        number = new_issue.json()["number"]
        new_title = f"[qa-bot] edited {uuid4().hex[:8]}"
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/{number}",
            payload={"title": new_title},
        )
        assert response.status_code == 200
        assert response.json()["title"] == new_title
        # Confirm the change is persisted, not just echoed in the PATCH response.
        readback = client.get(f"/repos/{username}/{write_repo}/issues/{number}")
        assert readback.json()["title"] == new_title

    @allure.story("Close an issue")
    def test_close_issue_returns_state_closed(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_issue
    ):
        number = new_issue.json()["number"]
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/{number}",
            payload={"state": "closed"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "closed"


@allure.epic("GitHub REST API")
@allure.feature("Issues API (write)")
class TestIssueComment:

    @allure.story("Create and delete a comment")
    @allure.severity(allure.severity_level.NORMAL)
    def test_comment_create_then_delete(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_issue
    ):
        number = new_issue.json()["number"]

        with allure.step("Create comment -> 201"):
            created = client.post(
                f"/repos/{username}/{write_repo}/issues/{number}/comments",
                payload={"body": "Comment from the QA write-path suite."},
            )
            assert created.status_code == 201, created.text
            comment_id = created.json()["id"]

        with allure.step("Delete comment -> 204"):
            deleted = client.delete(
                f"/repos/{username}/{write_repo}/issues/comments/{comment_id}"
            )
            assert deleted.status_code == 204

        with allure.step("Deleted comment is gone -> 404"):
            gone = client.get(
                f"/repos/{username}/{write_repo}/issues/comments/{comment_id}"
            )
            assert gone.status_code == 404


@allure.epic("GitHub REST API")
@allure.feature("Labels API (write)")
class TestLabelCrud:
    """Labels are the cleanest full-CRUD resource on GitHub — create, update and
    a real DELETE (204), all fully reversible."""

    @allure.story("Create a label")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_label_returns_201(self, created_label):
        response, name = created_label
        assert response.status_code == 201, response.text
        assert response.json()["name"] == name
        assert response.json()["color"] == "ededed"

    @allure.story("Update a label")
    def test_update_label_returns_200(
        self, client: GitHubAPIClient, username: str, write_repo: str, created_label
    ):
        _, name = created_label
        response = client.patch(
            f"/repos/{username}/{write_repo}/labels/{name}",
            payload={"color": "0e8a16", "description": "Updated by QA suite."},
        )
        assert response.status_code == 200
        assert response.json()["color"] == "0e8a16"
        assert response.json()["description"] == "Updated by QA suite."

    @allure.story("Delete a label")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_label_returns_204(
        self, client: GitHubAPIClient, username: str, write_repo: str, created_label
    ):
        _, name = created_label
        response = client.delete(f"/repos/{username}/{write_repo}/labels/{name}")
        assert response.status_code == 204
        # Gone for good.
        assert client.get(f"/repos/{username}/{write_repo}/labels/{name}").status_code == 404


@allure.epic("GitHub REST API")
@allure.feature("Issues API (write)")
class TestWriteNegativeCases:
    """Rejection behaviour is part of the contract too — verify the API refuses
    bad writes with the right status codes."""

    @allure.story("Reject invalid writes")
    def test_patch_nonexistent_issue_returns_404(
        self, client: GitHubAPIClient, username: str, write_repo: str
    ):
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/9999999",
            payload={"title": "should not work"},
        )
        assert response.status_code == 404

    @allure.story("Reject invalid writes")
    def test_create_issue_without_title_returns_422(
        self, client: GitHubAPIClient, username: str, write_repo: str
    ):
        # `title` is required; GitHub validates the payload and returns 422.
        response = client.post(
            f"/repos/{username}/{write_repo}/issues",
            payload={"body": "no title here"},
        )
        assert response.status_code == 422

    @allure.story("Reject invalid writes")
    def test_create_duplicate_label_returns_422(
        self, client: GitHubAPIClient, username: str, write_repo: str, created_label
    ):
        _, name = created_label
        # Label names are unique per repo — recreating one is a 422 (already_exists).
        response = client.post(
            f"/repos/{username}/{write_repo}/labels",
            payload={"name": name, "color": "ffffff"},
        )
        assert response.status_code == 422
