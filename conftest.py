import pytest
from utils.api_client import GitHubAPIClient
from config.settings import GITHUB_USERNAME


@pytest.fixture(scope="session")
def client() -> GitHubAPIClient:
    return GitHubAPIClient()


@pytest.fixture(scope="session")
def username() -> str:
    return GITHUB_USERNAME


@pytest.fixture(scope="session")
def public_repo(client, username) -> str:
    """Returns the name of the first public repo found for the test user."""
    response = client.get(f"/users/{username}/repos", params={"type": "owner", "per_page": 1})
    if response.status_code != 200:
        pytest.skip(f"Could not fetch repos ({response.status_code}): {response.json().get('message')}")
    repos = response.json()
    if not repos:
        pytest.skip("No public repositories found for this account.")
    return repos[0]["name"]
