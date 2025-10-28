"""
CI shared utilities:
- light wrappers around subprocess and GitHub CLI
- git/gh helpers used by both resolver scripts
- consistent failure handling and environment access
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
from typing import List, Optional, NoReturn

BRANCH = os.getenv("BRANCH", "main")

def fail(msg: str) -> NoReturn:
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)

def run(cmd: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    # cp = completed process (will use this to refer)
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

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

def gh_json(args: List[str]) -> list:
    cp = run(["gh", *args])
    raw = cp.stdout.strip()
    return json.loads(raw) if raw else []

def gh_api(path: str, jq: Optional[str] = None) -> List[str]:
    """
    A simple python wrapper around the GitHub API
    to make it a callable function.
    """
    args = ["gh", "api", path]
    if jq:
        args += ["--jq", jq]
    cp = run(args, check=True)
    return [x for x in cp.stdout.splitlines() if x]

def dev_tag_for_sha(sha: str) -> Optional[str]:
    cp = run(["git", "tag", "--points-at", sha], check=False)
    for t in cp.stdout.splitlines():
        if t.startswith("dev-"):
            return t
    return None

def sha_for_tag(tag: str) -> Optional[str]:
    cp = run(["git", "rev-list", "-n1", tag], check=False)
    return cp.stdout.strip() or None

def latest_final_tag() -> Optional[str]:
    cp = run(["git", "tag", "--list", "v[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"], check=True)
    tags = cp.stdout.splitlines()
    return tags[0] if tags else None

def first_commit() -> str:
    """
    Returns the first commit of the current branch.

    We will never use this for our project since we
    already have a release but can be used as a
    fallback for new projects.
    """
    return run(["git", "rev-list", "--max-parents=0", "HEAD"], check=True).stdout.strip()

def list_merged_pr_commits(base: str, head: str) -> List[str]:
    rng = f"{base}..{head}"
    cp = run(["git", "rev-list", "--merges", "--first-parent", rng], check=False)
    return [x for x in cp.stdout.splitlines() if x]

def prs_for_commit(sha: str) -> List[int]:
    nums = gh_api(
        f"/repos/{os.getenv('GITHUB_REPOSITORY')}/commits/{sha}/pulls",
        jq=".[].number",
    )
    return [int(n) for n in nums]

def labels_for_pr(pr: int) -> List[str]:
    return gh_api(
        f"/repos/{os.getenv('GITHUB_REPOSITORY')}/issues/{pr}/labels",
        jq=".[].name",
    )
