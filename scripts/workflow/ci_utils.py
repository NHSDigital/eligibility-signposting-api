"""
CI shared utilities:
- light wrappers around subprocess and GitHub CLI
- git/gh helpers used by both resolver scripts
- consistent failure handling and environment access
"""

from __future__ import annotations
import os
import subprocess
import sys
from typing import List, Optional, NoReturn, Any

BRANCH = os.getenv("BRANCH", "main")
REPO_FALLBACK = "NHSDigital/eligibility-signposting-api"


def _repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or REPO_FALLBACK

def fail(msg: str) -> NoReturn:
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)

def run(cmd: List[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    cp = subprocess.run(cmd, check=False, capture_output=True, text=True, **kwargs)
    if check and cp.returncode != 0:
        raise subprocess.CalledProcessError(
            cp.returncode, cmd, output=cp.stdout, stderr=cp.stderr
        )
    return cp

def ensure_token() -> None:
    if not (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")):
        fail("GH_TOKEN/GITHUB_TOKEN is required")

def fetch_latest_from_remote() -> None:
    run(["git", "fetch", "origin", BRANCH, "--quiet"])
    run(["git", "fetch", "--tags", "--force", "--quiet"])

def git_ok(args: List[str]) -> bool:
    return subprocess.run(["git", *args]).returncode == 0

def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer]).returncode == 0

def dev_tag_for_sha(sha: str) -> Optional[str]:
    cp = run(["git", "tag", "--points-at", sha], check=False)
    for t in cp.stdout.splitlines():
        if t.startswith("dev-"):
            return t
    return None

def sha_for_tag(tag: str) -> Optional[str]:
    cp = run(["git", "rev-list", "-n1", tag], check=False)
    return cp.stdout.strip() or None

def latest_release_tag() -> Optional[str]:
    cp = run(["git", "tag", "--list", "v[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"], check=True)
    tags = cp.stdout.splitlines()
    return tags[0] if tags else None

def first_commit() -> str:
    """
    Returns the first commit of the current branch.

    We will never use this for our project since we
    already have a release but can be used as a
    fallback.
    """
    return run(["git", "rev-list", "--max-parents=0", "HEAD"], check=True).stdout.strip()

def labels_for_pr(pr: int) -> List[str]:
    """Return all labels on a PR (or issue)."""
    args = [
        "gh", "api",
        f"/repos/{_repo()}/issues/{pr}/labels",
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "--jq", ".[].name",
    ]
    cp = run(args, check=False)
    if cp.returncode not in (0, 1):
        print(f"Warning: gh api exit {cp.returncode} for PR #{pr}", file=sys.stderr)
    if cp.stdout.strip():
        return [x.strip() for x in cp.stdout.splitlines() if x.strip()]
    return []


def commit_subject(sha: str) -> str:
    """Return the one-line subject for a commit SHA."""
    cp = run(["git", "log", "-1", "--pretty=%s", sha], check=False)
    return (cp.stdout or "").strip()

def parse_merge_subject_for_pr_numbers(subject: str) -> List[int]:
    """
    Extract PR numbers from common merge subjects, e.g.:
    - 'Merge pull request #123 from ...'
    - 'Some feature (#456)'
    """
    import re
    nums = set()
    for m in re.finditer(r"(?:#|\bPR\s*#)(\d+)", subject, flags=re.IGNORECASE):
        try:
            nums.add(int(m.group(1)))
        except ValueError:
            pass
    # Also match explicit 'Merge pull request #123'
    m2 = re.search(r"Merge pull request #(\d+)", subject, flags=re.IGNORECASE)
    if m2:
        try:
            nums.add(int(m2.group(1)))
        except ValueError:
            pass
    return sorted(nums)

def list_merge_commits(base: str, head: str) -> List[str]:
    """
    Merge commits on the first-parent path from base..head.
    """
    rng = f"{base}..{head}"
    cp = run(["git", "rev-list", "--merges", "--first-parent", rng], check=False)
    return [x for x in cp.stdout.splitlines() if x]

def list_all_commits(base: str, head: str) -> List[str]:
    """
    All commits on the first-parent path base..head (includes squash merges as single commits).
    """
    rng = f"{base}..{head}"
    # We choose first-parent so we're scanning the mainline history only.
    cp = run(["git", "rev-list", "--first-parent", rng], check=False)
    return [x for x in cp.stdout.splitlines() if x]

def prs_for_commit_via_api(sha: str) -> List[int]:
    """
    Use the official endpoint linking any commit to associated PRs.
    Works for merge commits and for commits that landed via rebase merges.
    """
    args = [
        "gh", "api",
        f"/repos/{_repo()}/commits/{sha}/pulls",
        "-H", "Accept: application/vnd.github.groot-preview+json",
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "--jq", ".[].number"
    ]
    try:
        cp = run(args, check=True)
        return [int(x) for x in cp.stdout.splitlines() if x]
    except subprocess.CalledProcessError as e:
        print(f"Warning: commit→PR lookup failed for {sha[:7]} ({e.returncode})", file=sys.stderr)
        return []

def title_for_pr(pr: int) -> str:
    """
    Return the title of a pull request.
    """
    args = [
        "gh", "pr", "view", str(pr),
        "--repo", _repo(),
        "--json", "title",
        "--jq", ".title",
    ]
    cp = run(args, check=False)
    if cp.returncode not in (0, 1):
        print(f"Warning: gh pr view exit {cp.returncode} for PR #{pr}", file=sys.stderr)
    return cp.stdout.strip()
