import time
from dataclasses import dataclass, field

import pytest

from config.settings import GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_WRITE_REPO
from utils import factories
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


# Colours for the seed labels that tag the seed issues (kind -> hex). The actual
# label names are generated unique PER SESSION inside `seed` — concurrent CI
# jobs (the 3.12/3.13 matrix) share one sandbox, so fixed names would collide
# (a name already exists -> 422; or one job's delete-if-exists wipes another's).
SEED_LABEL_COLORS = {
    "bug": "d73a4a",
    "enhancement": "a2eeef",
    "wontfix": "ffffff",
}


@dataclass
class SeededIssue:
    number: int
    title: str
    state: str  # the state we drove it to: "open" | "closed"


@dataclass
class SeedData:
    """Known baseline laid down in the sandbox so reads are deterministic.

    The three seed issues all carry `session_label` — a label unique to this
    run — so filtering by it returns exactly this run's issues, never leftovers
    from a previous run (issues can't be hard-deleted, only closed).
    """

    repo: str
    session_label: str
    labels: list[str]  # the per-session seed label names tagging the issues
    milestone_title: str
    issues: list[SeededIssue] = field(default_factory=list)
    milestone_number: int = 0

    @property
    def open_count(self) -> int:
        return sum(1 for i in self.issues if i.state == "open")

    @property
    def closed_count(self) -> int:
        return sum(1 for i in self.issues if i.state == "closed")


@pytest.fixture(scope="session")
def seed(client: GitHubAPIClient, username: str, write_repo: str) -> SeedData:
    """Lay down a known baseline in the sandbox, then tear it all down.

    Creates seed labels, a session label, three issues (2 open + 1 closed, each
    tagged with the session label and a milestone) and one milestone. Every
    artifact is tracked and removed on session teardown — issues are closed (no
    REST hard-delete), labels/milestones are deleted.

    Every created name is suffixed with a run-unique token, so two jobs seeding
    the same sandbox concurrently (the CI version matrix) never collide. We
    therefore do NOT delete-if-exists: unique names can't pre-exist, and a
    blind delete would be the very thing that wipes a sibling job's data.
    Inherits the `write_repo` token gate, so a read-only run skips the suite.
    """
    base = f"/repos/{username}/{write_repo}"
    suffix = factories.unique_suffix()
    created_issues: list[int] = []
    created_labels: list[str] = []
    created_milestones: list[int] = []

    def make_label(name: str, color: str) -> str:
        resp = client.post(f"{base}/labels", payload=factories.label_payload(name=name, color=color))
        assert resp.status_code == 201, resp.text
        created_labels.append(name)
        return name

    # Per-session seed labels (kind -> unique name) plus the filter label.
    seed_labels = {kind: make_label(f"seed-{kind}-{suffix}", color) for kind, color in SEED_LABEL_COLORS.items()}
    session_label = make_label(f"seed-session-{suffix}", "0e8a16")

    # Milestone — unique title, so no stale-cleanup (and no duplicate-title 422).
    milestone_title = f"seed-milestone-{suffix}"
    ms_resp = client.post(f"{base}/milestones", payload=factories.milestone_payload(title=milestone_title))
    assert ms_resp.status_code == 201, ms_resp.text
    milestone_number = ms_resp.json()["number"]
    created_milestones.append(milestone_number)

    # Three issues: 2 open + 1 closed, all tagged with the session label.
    specs = [
        (f"[qa-bot] seed open bug {suffix}", [seed_labels["bug"]], "open"),
        (f"[qa-bot] seed open enhancement {suffix}", [seed_labels["enhancement"]], "open"),
        (f"[qa-bot] seed closed wontfix {suffix}", [seed_labels["wontfix"]], "closed"),
    ]
    issues: list[SeededIssue] = []
    for title, labels, target_state in specs:
        resp = client.post(
            f"{base}/issues",
            payload=factories.issue_payload(title=title, labels=[*labels, session_label], milestone=milestone_number),
        )
        assert resp.status_code == 201, resp.text
        number = resp.json()["number"]
        created_issues.append(number)
        if target_state == "closed":
            client.patch(f"{base}/issues/{number}", payload={"state": "closed"})
        issues.append(SeededIssue(number=number, title=title, state=target_state))

    # The issues `labels=` filter is served by a search index that lags creation
    # by a few seconds. Wait (once per session) until it reflects all seeded
    # issues, so the label-filter read tests are deterministic instead of racy.
    deadline = time.time() + 30
    while time.time() < deadline:
        indexed = client.get(
            f"{base}/issues",
            params={"labels": session_label, "state": "all", "per_page": 100},
        ).json()
        if len(indexed) == len(issues):
            break
        time.sleep(2)

    data = SeedData(
        repo=write_repo,
        session_label=session_label,
        labels=list(seed_labels.values()),
        milestone_title=milestone_title,
        issues=issues,
        milestone_number=milestone_number,
    )
    yield data

    # Teardown — idempotent. Deleting the session label also detaches it from
    # the (now closed) issues, so the next run's label filter stays exact.
    for number in created_issues:
        client.patch(f"{base}/issues/{number}", payload={"state": "closed"})
    for name in created_labels:
        client.delete(f"{base}/labels/{name}")
    for number in created_milestones:
        client.delete(f"{base}/milestones/{number}")
