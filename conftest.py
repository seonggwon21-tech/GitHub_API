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


# Fixed-name labels seeded once per session — they tag the seed issues so the
# baseline mirrors a realistic repo. Created and torn down with the seed; the
# run-unique `session_label` (not these) is what the deterministic reads filter on.
SEED_LABELS = {
    "seed-bug": "d73a4a",
    "seed-enhancement": "a2eeef",
    "seed-wontfix": "ffffff",
}
SEED_MILESTONE_TITLE = "seed-milestone"


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
    labels: list[str]  # the fixed-name seed labels (SEED_LABELS keys)
    issues: list[SeededIssue] = field(default_factory=list)
    milestone_number: int = 0
    milestone_title: str = SEED_MILESTONE_TITLE

    @property
    def open_count(self) -> int:
        return sum(1 for i in self.issues if i.state == "open")

    @property
    def closed_count(self) -> int:
        return sum(1 for i in self.issues if i.state == "closed")


@pytest.fixture(scope="session")
def seed(client: GitHubAPIClient, username: str, write_repo: str) -> SeedData:
    """Lay down a known baseline in the sandbox, then tear it all down.

    Creates fixed-name labels, a unique per-session label, three issues
    (2 open + 1 closed, each tagged with the session label and a milestone) and
    one milestone. Every artifact is tracked and removed on session teardown —
    issues are closed (no REST hard-delete), labels/milestones are deleted.
    Creation is idempotent (delete-if-exists), so a crashed prior run can't
    poison the next one. Inherits the `write_repo` token gate, so a read-only
    run skips the whole seed-dependent suite.
    """
    base = f"/repos/{username}/{write_repo}"
    created_issues: list[int] = []
    created_labels: list[str] = []
    created_milestones: list[int] = []

    def make_label(name: str, color: str) -> str:
        # delete-if-exists so a leftover label from a crashed run doesn't 422.
        client.delete(f"{base}/labels/{name}")
        resp = client.post(f"{base}/labels", payload=factories.label_payload(name=name, color=color))
        assert resp.status_code == 201, resp.text
        created_labels.append(name)
        return name

    for label_name, label_color in SEED_LABELS.items():
        make_label(label_name, label_color)

    session_label = f"seed-session-{factories.unique_suffix()}"
    make_label(session_label, "0e8a16")

    # Milestone — delete any stale same-title one first, then create fresh.
    # Page fully: GitHub rejects a duplicate milestone title with 422, so a
    # stale one left beyond the default page size must still be found and removed.
    for milestone in client.get(f"{base}/milestones", params={"state": "all", "per_page": 100}).json():
        if milestone.get("title") == SEED_MILESTONE_TITLE:
            client.delete(f"{base}/milestones/{milestone['number']}")
    ms_resp = client.post(f"{base}/milestones", payload=factories.milestone_payload(title=SEED_MILESTONE_TITLE))
    assert ms_resp.status_code == 201, ms_resp.text
    milestone_number = ms_resp.json()["number"]
    created_milestones.append(milestone_number)

    # Three issues: 2 open + 1 closed, all tagged with the session label.
    specs = [
        ("[qa-bot] seed open bug", ["seed-bug"], "open"),
        ("[qa-bot] seed open enhancement", ["seed-enhancement"], "open"),
        ("[qa-bot] seed closed wontfix", ["seed-wontfix"], "closed"),
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
        labels=list(SEED_LABELS),
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
