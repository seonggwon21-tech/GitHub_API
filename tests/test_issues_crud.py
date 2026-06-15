"""Write-path (CRUD) tests for the GitHub Issues, Labels & Milestones APIs.

Unlike the read-only suites, these tests mutate real GitHub data, so they run
only against the dedicated sandbox repo provided by the `write_repo` fixture and
clean up everything they create:
  - Issues can't be hard-deleted via REST, so created issues are closed on teardown.
  - Comments, labels and milestones ARE deletable, so those teardowns delete.
The whole module auto-skips when no PAT with `repo` scope is configured.
"""

import allure
import pytest

from utils import factories
from utils.api_client import GitHubAPIClient

pytestmark = pytest.mark.write


@pytest.fixture
def new_issue(client: GitHubAPIClient, username: str, write_repo: str):
    """Create an issue for one test, then close it on teardown.

    Yields the raw POST response so a test can assert on the 201 itself.
    """
    response = client.post(f"/repos/{username}/{write_repo}/issues", payload=factories.issue_payload())
    yield response
    # No REST hard-delete exists for issues — close it to keep the sandbox tidy.
    # Idempotent: harmless even if the test already closed it.
    if response.status_code == 201:
        number = response.json()["number"]
        client.patch(f"/repos/{username}/{write_repo}/issues/{number}", payload={"state": "closed"})


@pytest.fixture
def new_comment(client: GitHubAPIClient, username: str, write_repo: str, new_issue):
    """Create a comment on a fresh issue, then delete it on teardown.

    Yields the raw POST response so a test can assert on the 201. Teardown delete
    is idempotent, so a test is free to delete the comment itself — and if the
    test fails mid-way, the sandbox is still cleaned up.
    """
    number = new_issue.json()["number"]
    response = client.post(
        f"/repos/{username}/{write_repo}/issues/{number}/comments",
        payload=factories.comment_payload(),
    )
    yield response
    if response.status_code == 201:
        client.delete(f"/repos/{username}/{write_repo}/issues/comments/{response.json()['id']}")


@pytest.fixture
def created_label(client: GitHubAPIClient, username: str, write_repo: str):
    """Create a uniquely-named label, then delete it on teardown.

    Yields (post_response, label_name). Teardown delete is idempotent, so a test
    is free to delete the label itself.
    """
    payload = factories.label_payload()
    response = client.post(f"/repos/{username}/{write_repo}/labels", payload=payload)
    yield response, payload["name"]
    client.delete(f"/repos/{username}/{write_repo}/labels/{payload['name']}")


@pytest.fixture
def new_labeled_issue(client: GitHubAPIClient, username: str, write_repo: str, created_label):
    """Create an issue that carries a fresh label; close it on teardown.

    Yields (issue_response, label_name). The label itself is cleaned up by the
    `created_label` teardown this fixture depends on.
    """
    _, label_name = created_label
    response = client.post(
        f"/repos/{username}/{write_repo}/issues",
        payload=factories.issue_payload(labels=[label_name]),
    )
    yield response, label_name
    if response.status_code == 201:
        number = response.json()["number"]
        client.patch(f"/repos/{username}/{write_repo}/issues/{number}", payload={"state": "closed"})


@pytest.fixture
def new_milestone(client: GitHubAPIClient, username: str, write_repo: str):
    """Create a milestone, then delete it on teardown (idempotent)."""
    response = client.post(f"/repos/{username}/{write_repo}/milestones", payload=factories.milestone_payload())
    yield response
    if response.status_code == 201:
        client.delete(f"/repos/{username}/{write_repo}/milestones/{response.json()['number']}")


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
    def test_created_issue_is_readable(self, client: GitHubAPIClient, username: str, write_repo: str, new_issue):
        created = new_issue.json()
        response = client.get(f"/repos/{username}/{write_repo}/issues/{created['number']}")
        assert response.status_code == 200
        # The data we POSTed should round-trip back unchanged.
        assert response.json()["title"] == created["title"]
        assert response.json()["body"] == "Created by the write-path test suite."

    @allure.story("Create an issue with labels")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_issue_with_labels_applies_them(self, new_labeled_issue):
        response, label_name = new_labeled_issue
        assert response.status_code == 201, response.text
        applied = {label["name"] for label in response.json()["labels"]}
        assert label_name in applied

    @allure.story("Update an issue")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_issue_title_returns_200(self, client: GitHubAPIClient, username: str, write_repo: str, new_issue):
        number = new_issue.json()["number"]
        new_title = f"[qa-bot] edited {factories.unique_suffix()}"
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/{number}",
            payload={"title": new_title},
        )
        assert response.status_code == 200
        assert response.json()["title"] == new_title
        # Confirm the change is persisted, not just echoed in the PATCH response.
        readback = client.get(f"/repos/{username}/{write_repo}/issues/{number}")
        assert readback.json()["title"] == new_title

    @allure.story("Update an issue")
    def test_update_issue_body_returns_200(self, client: GitHubAPIClient, username: str, write_repo: str, new_issue):
        number = new_issue.json()["number"]
        new_body = f"edited body {factories.unique_suffix()}"
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/{number}",
            payload={"body": new_body},
        )
        assert response.status_code == 200
        assert response.json()["body"] == new_body

    @allure.story("Close an issue")
    def test_close_issue_returns_state_closed(self, client: GitHubAPIClient, username: str, write_repo: str, new_issue):
        number = new_issue.json()["number"]
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/{number}",
            payload={"state": "closed"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "closed"

    @allure.story("Reopen an issue")
    @allure.severity(allure.severity_level.NORMAL)
    def test_close_then_reopen_issue(self, client: GitHubAPIClient, username: str, write_repo: str, new_issue):
        number = new_issue.json()["number"]
        with allure.step("Close -> state closed"):
            closed = client.patch(f"/repos/{username}/{write_repo}/issues/{number}", payload={"state": "closed"})
            assert closed.json()["state"] == "closed"
        with allure.step("Reopen -> state open"):
            reopened = client.patch(f"/repos/{username}/{write_repo}/issues/{number}", payload={"state": "open"})
            assert reopened.status_code == 200
            assert reopened.json()["state"] == "open"

    @allure.story("Lock and unlock an issue")
    def test_lock_then_unlock_issue(self, client: GitHubAPIClient, username: str, write_repo: str, new_issue):
        number = new_issue.json()["number"]
        with allure.step("Lock -> 204, issue locked"):
            locked = client.put(
                f"/repos/{username}/{write_repo}/issues/{number}/lock",
                payload={"lock_reason": "resolved"},
            )
            assert locked.status_code == 204
            assert client.get(f"/repos/{username}/{write_repo}/issues/{number}").json()["locked"] is True
        with allure.step("Unlock -> 204, issue unlocked"):
            unlocked = client.delete(f"/repos/{username}/{write_repo}/issues/{number}/lock")
            assert unlocked.status_code == 204
            assert client.get(f"/repos/{username}/{write_repo}/issues/{number}").json()["locked"] is False


@allure.epic("GitHub REST API")
@allure.feature("Issues API (write)")
class TestIssueComment:
    @allure.story("Create and delete a comment")
    @allure.severity(allure.severity_level.NORMAL)
    def test_comment_create_then_delete(self, client: GitHubAPIClient, username: str, write_repo: str, new_comment):
        assert new_comment.status_code == 201, new_comment.text
        comment_id = new_comment.json()["id"]

        with allure.step("Delete comment -> 204"):
            deleted = client.delete(f"/repos/{username}/{write_repo}/issues/comments/{comment_id}")
            assert deleted.status_code == 204

        with allure.step("Deleted comment is gone -> 404"):
            gone = client.get(f"/repos/{username}/{write_repo}/issues/comments/{comment_id}")
            assert gone.status_code == 404

    @allure.story("Edit a comment")
    def test_comment_edit_updates_body(self, client: GitHubAPIClient, username: str, write_repo: str, new_comment):
        comment_id = new_comment.json()["id"]
        new_body = f"edited comment {factories.unique_suffix()}"
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/comments/{comment_id}",
            payload={"body": new_body},
        )
        assert response.status_code == 200
        assert response.json()["body"] == new_body

    @allure.story("Comment appears in the issue's comment list")
    def test_comment_appears_in_list(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_issue, new_comment
    ):
        # new_comment depends on new_issue, so within one test they resolve to
        # the same issue — the comment must show up in that issue's listing.
        number = new_issue.json()["number"]
        comment_id = new_comment.json()["id"]
        listing = client.get(f"/repos/{username}/{write_repo}/issues/{number}/comments")
        assert listing.status_code == 200
        assert comment_id in [comment["id"] for comment in listing.json()]


@allure.epic("GitHub REST API")
@allure.feature("Issues API (write)")
class TestIssueLabelsOnIssue:
    """Labels attached to an issue — apply, list, replace (PUT), remove."""

    @allure.story("List labels on an issue")
    def test_list_issue_labels(self, client: GitHubAPIClient, username: str, write_repo: str, new_labeled_issue):
        issue_response, label_name = new_labeled_issue
        number = issue_response.json()["number"]
        response = client.get(f"/repos/{username}/{write_repo}/issues/{number}/labels")
        assert response.status_code == 200
        assert label_name in [label["name"] for label in response.json()]

    @allure.story("Replace all labels on an issue (PUT)")
    @allure.severity(allure.severity_level.NORMAL)
    def test_replace_issue_labels_with_empty_clears(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_labeled_issue
    ):
        issue_response, _ = new_labeled_issue
        number = issue_response.json()["number"]
        response = client.put(f"/repos/{username}/{write_repo}/issues/{number}/labels", payload={"labels": []})
        assert response.status_code == 200
        assert response.json() == []
        # Confirm it persisted.
        assert client.get(f"/repos/{username}/{write_repo}/issues/{number}/labels").json() == []

    @allure.story("Remove a single label from an issue")
    def test_remove_label_from_issue(self, client: GitHubAPIClient, username: str, write_repo: str, new_labeled_issue):
        issue_response, label_name = new_labeled_issue
        number = issue_response.json()["number"]
        response = client.delete(f"/repos/{username}/{write_repo}/issues/{number}/labels/{label_name}")
        assert response.status_code == 200
        assert label_name not in [label["name"] for label in response.json()]


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
    def test_update_label_returns_200(self, client: GitHubAPIClient, username: str, write_repo: str, created_label):
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
    def test_delete_label_returns_204(self, client: GitHubAPIClient, username: str, write_repo: str, created_label):
        _, name = created_label
        response = client.delete(f"/repos/{username}/{write_repo}/labels/{name}")
        assert response.status_code == 204
        # Gone for good.
        assert client.get(f"/repos/{username}/{write_repo}/labels/{name}").status_code == 404


@allure.epic("GitHub REST API")
@allure.feature("Milestones API (write)")
class TestMilestone:
    """Full milestone lifecycle: create -> assign to an issue -> close -> delete."""

    @allure.story("Create a milestone")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_milestone_returns_201(self, new_milestone):
        assert new_milestone.status_code == 201, new_milestone.text
        assert isinstance(new_milestone.json()["number"], int)
        assert new_milestone.json()["state"] == "open"

    @allure.story("Assign a milestone to an issue")
    def test_assign_milestone_to_issue(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_issue, new_milestone
    ):
        issue_number = new_issue.json()["number"]
        milestone_number = new_milestone.json()["number"]
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/{issue_number}",
            payload={"milestone": milestone_number},
        )
        assert response.status_code == 200
        assert response.json()["milestone"]["number"] == milestone_number

    @allure.story("Close a milestone")
    def test_close_milestone(self, client: GitHubAPIClient, username: str, write_repo: str, new_milestone):
        number = new_milestone.json()["number"]
        response = client.patch(
            f"/repos/{username}/{write_repo}/milestones/{number}",
            payload={"state": "closed"},
        )
        assert response.status_code == 200
        assert response.json()["state"] == "closed"

    @allure.story("Delete a milestone")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_milestone_returns_204(self, client: GitHubAPIClient, username: str, write_repo: str, new_milestone):
        number = new_milestone.json()["number"]
        response = client.delete(f"/repos/{username}/{write_repo}/milestones/{number}")
        assert response.status_code == 204
        assert client.get(f"/repos/{username}/{write_repo}/milestones/{number}").status_code == 404


@allure.epic("GitHub REST API")
@allure.feature("Issues API (write)")
class TestWriteIdempotency:
    """Repeating a state-changing write should converge, not error."""

    @allure.story("Re-closing a closed issue stays closed")
    def test_reclose_closed_issue_stays_closed(
        self, client: GitHubAPIClient, username: str, write_repo: str, new_issue
    ):
        number = new_issue.json()["number"]
        first = client.patch(f"/repos/{username}/{write_repo}/issues/{number}", payload={"state": "closed"})
        assert first.json()["state"] == "closed"
        second = client.patch(f"/repos/{username}/{write_repo}/issues/{number}", payload={"state": "closed"})
        assert second.status_code == 200
        assert second.json()["state"] == "closed"


@allure.epic("GitHub REST API")
@allure.feature("Issues API (write)")
class TestWriteNegativeCases:
    """Rejection behaviour is part of the contract too — verify the API refuses
    bad writes with the right status codes."""

    @allure.story("Reject invalid create payloads")
    @pytest.mark.parametrize(
        "resource, payload, expected",
        [
            ("issues", {"body": "no title here"}, 422),  # title is required
            ("labels", {"color": "ededed"}, 422),  # name is required
            ("labels", {"name": "bad-color", "color": "zzzzzz"}, 422),  # color must be hex
        ],
        ids=["issue-missing-title", "label-missing-name", "label-bad-color"],
    )
    def test_invalid_create_payload_returns_422(
        self, client: GitHubAPIClient, username: str, write_repo: str, resource, payload, expected
    ):
        response = client.post(f"/repos/{username}/{write_repo}/{resource}", payload=payload)
        assert response.status_code == expected, response.text

    @allure.story("Reject invalid writes")
    def test_patch_nonexistent_issue_returns_404(self, client: GitHubAPIClient, username: str, write_repo: str):
        response = client.patch(
            f"/repos/{username}/{write_repo}/issues/9999999",
            payload={"title": "should not work"},
        )
        assert response.status_code == 404

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
