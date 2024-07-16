"""Add changes."""

from dataclasses import dataclass
from json import loads
from re import sub
from shlex import quote, split
from subprocess import run
from textwrap import dedent
from typing import Any, NamedTuple
from urllib.parse import urlparse

from dulwich.repo import Repo

from copier_python_tools.types import ChangeType


def add_change(typ: ChangeType = "change"):
    """Add change."""
    owner, repo, issue = get_issue_from_active_branch()
    change = get_change(owner, repo, issue)
    content = quote(f"{change.name}\n")
    run(
        split(f"""towncrier create --content {content} {change.id}.{typ}.md"""),
        check=True,
    )


class Issue(NamedTuple):
    """Issue."""

    owner: str
    """Owner."""
    repo: str
    """Repository."""
    issue: int
    """Issue."""


def get_issue_from_active_branch() -> Issue:
    """Get issue associated with active branch."""
    repository = Repo(".")
    owner, repo = (
        urlparse(repository.get_config().get(("remote", "origin"), "url"))
        .path.decode("utf-8")
        .removesuffix(".git")
        .strip("/")
        .split("/")
    )
    (_, ref), _ = repository.refs.follow(b"HEAD")
    issue = ref.decode("utf-8").split("/")[-1].split("=")[0].split("-")[0]
    return Issue(owner, repo, issue)


@dataclass
class Change:
    """Change."""

    id: int
    """ID."""
    name: str
    """Name."""


def get_change(owner: str, repo: str, issue: int) -> Change:
    """Get related issue title."""
    first = 1
    if nodes := get_connected_prs(owner, repo, issue, first):
        subject = nodes[0]["subject"]
        return Change(id=subject["number"], name=subject["title"])
    return Change(id=issue, name=query_gh_issue(owner, repo, issue)["title"])


def get_connected_prs(
    owner: str, repo: str, issue: int, first: int
) -> list[dict[str, Any]]:
    """Get first PR connected to an issue."""
    return query_gh_issue(
        owner,
        repo,
        issue,
        query=f"""
            timelineItems(itemTypes: CONNECTED_EVENT, first: {first}) {{
                nodes {{
                    ... on ConnectedEvent {{
                        subject {{ ... on PullRequest {{ number title }} }}
                    }}
                }}
            }}""",
    )["timelineItems"]["nodes"]


def query_gh_issue(
    owner: str, repo: str, issue: int, query: str = "title"
) -> dict[str, Any]:
    """Query GitHub for an issue."""
    result = run(
        [  # noqa: S607
            "gh",
            "api",
            "graphql",
            "-f",
            sanitize(f"""query= {{
                repository(owner:"{owner}", name:"{repo}") {{
                    issue(number: {issue}) {{ {sanitize(query)} }}
                }}
            }}"""),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    data = loads(result.stdout)["data"].get("repository")
    if not data:
        raise RuntimeError("Query does not return a repository.")
    if data := data.get("issue"):
        return data
    else:
        raise RuntimeError("Query does not return an issue.")


def sanitize(query: str) -> str:
    """Sanitize query."""
    return sub(r"\s+", " ", f"{dedent(query)}").strip().replace("\n", "")


if __name__ == "__main__":
    add_change()
