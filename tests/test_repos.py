import allure
import pytest
from utils.api_client import GitHubAPIClient


@allure.epic("GitHub REST API")
@allure.feature("Repository API")
@pytest.mark.repos
class TestListRepositories:

    @allure.story("List public repos for a user")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_list_public_repos_returns_200(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}/repos")
        assert response.status_code == 200

    @allure.story("List public repos for a user")
    def test_list_public_repos_returns_list(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}/repos")
        assert isinstance(response.json(), list)

    @allure.story("List public repos for a user")
    def test_list_public_repos_schema(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}/repos", params={"per_page": 1})
        repos = response.json()
        if not repos:
            pytest.skip("No public repositories to validate schema.")
        repo = repos[0]
        required = {"id", "name", "full_name", "private", "owner", "html_url", "fork"}
        for field in required:
            assert field in repo, f"Missing field: {field}"

    @allure.story("List public repos for a user")
    def test_list_public_repos_are_public(self, client: GitHubAPIClient, username: str):
        # /users/{username}/repos accepts type ∈ {all, owner, member}; it never
        # returns private repos, so the assertion verifies that guarantee holds.
        response = client.get(f"/users/{username}/repos", params={"type": "owner", "per_page": 10})
        assert response.status_code == 200, response.text
        for repo in response.json():
            assert repo["private"] is False

    @allure.story("List public repos for a user")
    def test_list_repos_pagination(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}/repos", params={"per_page": 1, "page": 1})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @allure.story("List public repos for a user")
    def test_list_repos_sort_by_updated(self, client: GitHubAPIClient, username: str):
        response = client.get(
            f"/users/{username}/repos",
            params={"sort": "updated", "direction": "desc", "per_page": 5},
        )
        assert response.status_code == 200

    @allure.story("List public repos for a user")
    def test_list_repos_invalid_sort_returns_422_or_200(self, client: GitHubAPIClient, username: str):
        response = client.get(
            f"/users/{username}/repos",
            params={"sort": "nonexistent_sort_value"},
        )
        assert response.status_code in (200, 422)

    @allure.story("List repos for nonexistent user")
    def test_list_repos_for_nonexistent_user_returns_404(self, client: GitHubAPIClient):
        response = client.get("/users/this-user-definitely-does-not-exist-xyzxyz999/repos")
        assert response.status_code == 404


@allure.epic("GitHub REST API")
@allure.feature("Repository API")
@pytest.mark.repos
class TestGetRepository:

    @allure.story("Get a single repository")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_repo_returns_200(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}")
        assert response.status_code == 200

    @allure.story("Get a single repository")
    def test_get_repo_name_matches(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}")
        assert response.status_code == 200, response.text
        assert response.json()["name"] == public_repo

    @allure.story("Get a single repository")
    def test_get_repo_owner_matches(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}")
        assert response.status_code == 200, response.text
        assert response.json()["owner"]["login"].lower() == username.lower()

    @allure.story("Get a single repository")
    def test_get_repo_schema(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}")
        body = response.json()
        required = {
            "id", "name", "full_name", "owner", "private",
            "html_url", "description", "fork", "created_at", "updated_at",
            "stargazers_count", "watchers_count", "forks_count", "default_branch",
        }
        for field in required:
            assert field in body, f"Missing field: {field}"

    @allure.story("Get a single repository")
    def test_get_nonexistent_repo_returns_404(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/repos/{username}/repo-that-does-not-exist-xyz9999")
        assert response.status_code == 404

    @allure.story("Repository languages")
    def test_get_repo_languages_returns_200(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}/languages")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    @allure.story("Repository topics")
    def test_get_repo_topics_returns_200(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}/topics")
        assert response.status_code == 200
        assert "names" in response.json()

    @allure.story("Repository contributors")
    def test_get_repo_contributors_returns_200_or_204(self, client: GitHubAPIClient, username: str, public_repo: str):
        response = client.get(f"/repos/{username}/{public_repo}/contributors")
        assert response.status_code in (200, 204)
