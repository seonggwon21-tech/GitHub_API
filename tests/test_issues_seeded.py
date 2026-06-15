"""Deterministic read tests over a seeded sandbox baseline.

The read-only Issues suite (`test_issues.py`) runs against a real portfolio repo
whose contents we don't control, so it can only make conditional assertions
("skip if no issues"). These tests instead query the `seed` baseline — a known
set of 3 issues (2 open + 1 closed) tagged with a unique session label — so the
expected counts are exact, not conditional.

They need the seeded sandbox (hence a repo-scope PAT); the `seed` fixture's
`write_repo` gate auto-skips the whole module on a token-less run.
"""

import allure
import pytest

from conftest import SeedData
from utils.api_client import GitHubAPIClient

pytestmark = pytest.mark.write


@allure.epic("GitHub REST API")
@allure.feature("Issues API (seeded)")
class TestSeededIssueQueries:
    """Counts are exact because we filter by the run-unique session label."""

    @allure.story("Filter seeded issues by label")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_all_seed_issues_returned(self, client: GitHubAPIClient, username: str, seed: SeedData):
        response = client.get(
            f"/repos/{username}/{seed.repo}/issues",
            params={"labels": seed.session_label, "state": "all", "per_page": 100},
        )
        assert response.status_code == 200, response.text
        assert len(response.json()) == len(seed.issues) == 3

    @allure.story("Filter seeded issues by state")
    def test_open_seed_issue_count(self, client: GitHubAPIClient, username: str, seed: SeedData):
        response = client.get(
            f"/repos/{username}/{seed.repo}/issues",
            params={"labels": seed.session_label, "state": "open", "per_page": 100},
        )
        issues = response.json()
        assert len(issues) == seed.open_count == 2
        assert all(issue["state"] == "open" for issue in issues)

    @allure.story("Filter seeded issues by state")
    def test_closed_seed_issue_count(self, client: GitHubAPIClient, username: str, seed: SeedData):
        response = client.get(
            f"/repos/{username}/{seed.repo}/issues",
            params={"labels": seed.session_label, "state": "closed", "per_page": 100},
        )
        issues = response.json()
        assert len(issues) == seed.closed_count == 1
        assert all(issue["state"] == "closed" for issue in issues)

    @allure.story("Filter seeded issues by label")
    def test_seed_issues_all_carry_session_label(self, client: GitHubAPIClient, username: str, seed: SeedData):
        response = client.get(
            f"/repos/{username}/{seed.repo}/issues",
            params={"labels": seed.session_label, "state": "all", "per_page": 100},
        )
        issues = response.json()
        assert len(issues) == len(seed.issues)  # guard against a vacuous pass
        for issue in issues:
            label_names = {label["name"] for label in issue["labels"]}
            assert seed.session_label in label_names

    @allure.story("Paginate the seeded set")
    def test_pagination_covers_exactly_the_seed_set(self, client: GitHubAPIClient, username: str, seed: SeedData):
        # One issue per page across the 3-issue seed set; collected numbers must
        # match the seeded numbers exactly, with no duplicates across pages.
        collected: list[int] = []
        for page in range(1, len(seed.issues) + 1):
            page_items = client.get(
                f"/repos/{username}/{seed.repo}/issues",
                params={"labels": seed.session_label, "state": "all", "per_page": 1, "page": page},
            ).json()
            assert len(page_items) == 1
            collected.append(page_items[0]["number"])
        assert sorted(collected) == sorted(i.number for i in seed.issues)
        assert len(set(collected)) == len(collected)  # no overlap between pages


@allure.epic("GitHub REST API")
@allure.feature("Milestones API (seeded)")
class TestSeededMilestone:
    @allure.story("Seeded milestone is queryable")
    def test_seed_milestone_present(self, client: GitHubAPIClient, username: str, seed: SeedData):
        response = client.get(f"/repos/{username}/{seed.repo}/milestones/{seed.milestone_number}")
        assert response.status_code == 200, response.text
        assert response.json()["title"] == seed.milestone_title

    @allure.story("Seeded milestone tracks its issues")
    def test_seed_milestone_open_issue_count(self, client: GitHubAPIClient, username: str, seed: SeedData):
        # GitHub keeps per-milestone open/closed issue tallies; our seed put all
        # three issues on the milestone (2 open + 1 closed).
        response = client.get(f"/repos/{username}/{seed.repo}/milestones/{seed.milestone_number}")
        body = response.json()
        assert body["open_issues"] == seed.open_count
        assert body["closed_issues"] == seed.closed_count
