import allure
import pytest

from utils.api_client import GitHubAPIClient


@allure.epic("GitHub REST API")
@allure.feature("Issues API")
@pytest.mark.issues
class TestListIssues:
    @allure.story("List repository issues")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_list_issues_returns_200(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}/issues")
        assert response.status_code == 200

    @allure.story("List repository issues")
    def test_list_issues_returns_list(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}/issues")
        assert isinstance(response.json(), list)

    @allure.story("List repository issues")
    def test_list_open_issues_state_is_open(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"state": "open", "per_page": 5},
        )
        for issue in response.json():
            assert issue["state"] == "open"

    @allure.story("List repository issues")
    def test_list_closed_issues_state_is_closed(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"state": "closed", "per_page": 5},
        )
        for issue in response.json():
            assert issue["state"] == "closed"

    @allure.story("List repository issues")
    def test_list_issues_schema(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"per_page": 1},
        )
        issues = response.json()
        if not issues:
            pytest.skip("No issues found — skipping schema validation.")
        issue = issues[0]
        required = {"id", "number", "title", "state", "user", "created_at", "updated_at", "html_url"}
        for field in required:
            assert field in issue, f"Missing field: {field}"

    @allure.story("List repository issues")
    def test_list_issues_pagination(self, client: GitHubAPIClient, username: str, public_repo: str):
        page1 = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"state": "all", "per_page": 1, "page": 1},
        ).json()
        page2 = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"state": "all", "per_page": 1, "page": 2},
        ).json()
        if page1 and page2:
            assert page1[0]["id"] != page2[0]["id"]

    @allure.story("List repository issues")
    def test_list_issues_invalid_state_returns_422(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"state": "invalid_state"},
        )
        assert response.status_code == 422

    @allure.story("List repository issues")
    def test_list_issues_for_nonexistent_repo_returns_404(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/repos/{username}/repo-that-does-not-exist-xyz9999/issues")
        assert response.status_code == 404


@allure.epic("GitHub REST API")
@allure.feature("Issues API")
@pytest.mark.issues
class TestGetIssue:
    @allure.story("Get a single issue")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_first_issue_if_exists(self, client: GitHubAPIClient, username: str, public_repo: str):
        issues = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"state": "all", "per_page": 1},
        ).json()
        if not issues:
            pytest.skip("No issues in this repo.")

        issue_number = issues[0]["number"]
        response = client.get(f"/repos/{username}/{public_repo}/issues/{issue_number}")
        assert response.status_code == 200

    @allure.story("Get a single issue")
    def test_get_nonexistent_issue_returns_404(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}/issues/9999999")
        assert response.status_code == 404

    @allure.story("Issue comments")
    def test_list_issue_comments_returns_200_if_issue_exists(
        self, client: GitHubAPIClient, username: str, public_repo: str
    ):
        issues = client.get(
            f"/repos/{username}/{public_repo}/issues",
            params={"state": "all", "per_page": 1},
        ).json()
        if not issues:
            pytest.skip("No issues in this repo.")

        issue_number = issues[0]["number"]
        response = client.get(f"/repos/{username}/{public_repo}/issues/{issue_number}/comments")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
