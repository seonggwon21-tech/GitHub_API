"""Request-payload builders for the write-path tests.

Centralizes the request bodies so tests don't repeat dict literals, and gives
every created artifact a unique, traceable name (``qa-bot`` prefix + uuid
suffix) — unique names keep reruns from colliding and make stray sandbox data
easy to spot.
"""

from uuid import uuid4

QA_PREFIX = "qa-bot"


def unique_suffix() -> str:
    """Short, collision-resistant suffix for uniquely named artifacts."""
    return uuid4().hex[:8]


def issue_payload(
    title: str | None = None,
    body: str = "Created by the write-path test suite.",
    labels: list[str] | None = None,
    milestone: int | None = None,
) -> dict:
    """Body for ``POST /repos/{o}/{r}/issues``. Unique title unless given one."""
    payload: dict = {"title": title or f"[{QA_PREFIX}] issue {unique_suffix()}", "body": body}
    if labels is not None:
        payload["labels"] = labels
    if milestone is not None:
        payload["milestone"] = milestone
    return payload


def label_payload(
    name: str | None = None,
    color: str = "ededed",
    description: str = "QA write-path test label.",
) -> dict:
    """Body for ``POST /repos/{o}/{r}/labels``. Unique name unless given one."""
    return {"name": name or f"{QA_PREFIX}-{unique_suffix()}", "color": color, "description": description}


def comment_payload(body: str = "Comment from the QA write-path suite.") -> dict:
    """Body for ``POST .../issues/{n}/comments``."""
    return {"body": body}


def milestone_payload(
    title: str | None = None,
    description: str = "QA write-path milestone.",
    state: str = "open",
) -> dict:
    """Body for ``POST /repos/{o}/{r}/milestones``. Unique title unless given one."""
    return {
        "title": title or f"[{QA_PREFIX}] milestone {unique_suffix()}",
        "description": description,
        "state": state,
    }
