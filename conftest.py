import pytest

from config.settings import GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_WRITE_REPO
from utils.api_client import GitHubAPIClient


@pytest.fixture(scope="session")
def client() -> GitHubAPIClient:
    return GitHubAPIClient()


@pytest.fixture(scope="session")
def username() -> str:
    return GITHUB_USERNAME


@pytest.fixture(scope="session")
def nonexistent_username() -> str:
    """A username guaranteed not to exist — shared by the 404 negative cases."""
    return "this-user-definitely-does-not-exist-xyzxyz999"


@pytest.fixture(scope="session")
def public_repo(client, username) -> str:
    """Returns the name of a public repo whose Issues API is usable.

    The read-only Issues suite hits `GET /repos/.../issues`, which returns 410
    on repos that have Issues disabled (common on forks). Picking just the first
    repo would intermittently false-fail, so we fetch a page and select the
    first repo with `has_issues` enabled, falling back to the first repo only if
    none qualify (the repo-only tests still work in that case).
    """
    response = client.get(f"/users/{username}/repos", params={"type": "owner", "per_page": 100})
    if response.status_code != 200:
        pytest.skip(f"Could not fetch repos ({response.status_code}): {response.json().get('message')}")
    repos = response.json()
    if not repos:
        pytest.skip("No public repositories found for this account.")
    with_issues = next((r for r in repos if r.get("has_issues")), None)
    return (with_issues or repos[0])["name"]


@pytest.fixture(scope="session")
def write_repo(client, username) -> str:
    """A repo we are allowed to create/update/delete data in.

    Write-path tests mutate real GitHub data, so they run only against a
    dedicated sandbox repo — never the portfolio repos. The fixture gates the
    whole write suite:
      - no token, or a token without `repo` scope -> skip (read-only run).
      - sandbox repo missing -> create it once (it persists as the sandbox).
      - finally verify we actually have push permission before handing it out.
    Returns the sandbox repo name.
    """
    if not GITHUB_TOKEN:
        pytest.skip("Write tests need a PAT with `repo` scope (set GITHUB_TOKEN).")

    repo = client.get(f"/repos/{username}/{GITHUB_WRITE_REPO}")
    if repo.status_code == 404:
        created = client.post(
            "/user/repos",
            payload={
                "name": GITHUB_WRITE_REPO,
                "private": True,
                "auto_init": True,
                "has_issues": True,
                "description": "Sandbox for GitHub_API QA write-path (CRUD) tests.",
            },
        )
        if created.status_code != 201:
            pytest.skip(
                f"Could not create sandbox repo ({created.status_code}) — "
                f"token likely lacks `repo` scope: {created.json().get('message')}"
            )
        repo = client.get(f"/repos/{username}/{GITHUB_WRITE_REPO}")

    if repo.status_code != 200 or not repo.json().get("permissions", {}).get("push"):
        pytest.skip("Token lacks push permission on the sandbox repo.")
    return GITHUB_WRITE_REPO
