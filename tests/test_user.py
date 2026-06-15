import allure
import pytest

from utils.api_client import GitHubAPIClient


@allure.epic("GitHub REST API")
@allure.feature("User API")
@pytest.mark.user
class TestPublicUser:
    @allure.story("Get public user profile")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    def test_get_public_user_returns_200(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}")
        assert response.status_code == 200

    @allure.story("Get public user profile")
    def test_get_public_user_response_schema(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}")
        body = response.json()
        required_fields = {"login", "id", "type", "public_repos", "followers", "following"}
        for field in required_fields:
            assert field in body, f"Missing field: {field}"

    @allure.story("Get public user profile")
    def test_get_public_user_login_matches(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}")
        assert response.status_code == 200, response.text
        assert response.json()["login"].lower() == username.lower()

    @allure.story("Get public user profile")
    def test_get_public_user_type_is_user(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}")
        assert response.status_code == 200, response.text
        assert response.json()["type"] == "User"

    @allure.story("Get public user profile")
    def test_get_nonexistent_user_returns_404(self, client: GitHubAPIClient, nonexistent_username: str):
        response = client.get(f"/users/{nonexistent_username}")
        assert response.status_code == 404

    @allure.story("Get public user profile")
    def test_response_content_type_is_json(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}")
        assert "application/json" in response.headers.get("Content-Type", "")


@allure.epic("GitHub REST API")
@allure.feature("User API")
@pytest.mark.user
class TestAuthenticatedUser:
    @allure.story("Get authenticated user")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_authenticated_user_returns_200_or_401(self, client: GitHubAPIClient):
        response = client.get("/user")
        assert response.status_code in (200, 401), f"Unexpected status: {response.status_code}"

    @allure.story("Get authenticated user")
    def test_get_authenticated_user_schema_when_authed(self, client: GitHubAPIClient):
        response = client.get("/user")
        if response.status_code == 401:
            pytest.skip("No token provided — skipping authenticated-only test.")
        body = response.json()
        assert "login" in body
        assert "email" in body, "Authenticated user response must include an 'email' field"
        # email may be private, but when present it must be a string (or null)
        assert body["email"] is None or isinstance(body["email"], str)

    @allure.story("List public emails")
    def test_list_public_emails_requires_auth(self, client: GitHubAPIClient):
        response = client.get("/user/emails")
        # 200: authed with user:email scope, 401/403: no token, 404: token lacks user:email scope
        assert response.status_code in (200, 401, 403, 404)


@allure.epic("GitHub REST API")
@allure.feature("User API")
@pytest.mark.user
class TestUserFollowers:
    @allure.story("List user followers")
    def test_get_followers_returns_200(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}/followers")
        assert response.status_code == 200

    @allure.story("List user followers")
    def test_get_followers_returns_list(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}/followers")
        assert isinstance(response.json(), list)

    @allure.story("List users followed")
    def test_get_following_returns_200(self, client: GitHubAPIClient, username: str):
        response = client.get(f"/users/{username}/following")
        assert response.status_code == 200
