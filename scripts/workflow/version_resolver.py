"""
PreProd resolver:
- Determines the furthest-ahead successful TEST commit on main (sha + dev-* tag).
- Resolves THIS run's sha + dev-* tag (auto via workflow_run, or manual via input tag).
- Applies the stale-run guard (auto blocks older; manual requires allow_older=true).
- Emits outputs for later steps.

Outputs (via $GITHUB_OUTPUT):
  this_sha, this_ref, latest_test_sha, latest_test_ref
"""

from __future__ import annotations
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional


WORKFLOW_NAME = os.getenv("WORKFLOW_NAME", "3. CD | Deploy to Test")
BRANCH        = os.getenv("BRANCH", "main")
LIMIT         = int(os.getenv("LIMIT", "30"))

EVENT_NAME    = os.getenv("EVENT_NAME", "")
HEAD_SHA_AUTO = os.getenv("WORKFLOW_RUN_HEAD_SHA", "")
MANUAL_REF    = os.getenv("MANUAL_REF", "")
ALLOW_OLDER   = os.getenv("ALLOW_OLDER", "false").lower()


def fail(msg: str) -> "NoReturn":
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)

def run(cmd: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

def git_ok(args: List[str]) -> bool:
    return subprocess.run(["git", *args]).returncode == 0

def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer]).returncode == 0

def fetch_graph() -> None:
    run(["git", "fetch", "origin", BRANCH, "--quiet"])
    run(["git", "fetch", "--tags", "--force", "--quiet"])

def gh_json(args: List[str]) -> list:
    cp = run(["gh", *args])
    raw = cp.stdout.strip()
    return json.loads(raw) if raw else []

def dev_tag_for_sha(sha: str) -> Optional[str]:
    cp = run(["git", "tag", "--points-at", sha], check=False)
    for t in cp.stdout.splitlines():
        if t.startswith("dev-"):
            return t
    return None

def sha_for_tag(tag: str) -> Optional[str]:
    cp = run(["git", "rev-list", "-n1", tag], check=False)
    return cp.stdout.strip() or None


@dataclass(frozen=True)
class RefInfo:
    sha: str
    ref: str


def require_token() -> None:
    if not (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")):
        fail("GH_TOKEN/GITHUB_TOKEN is required")

def list_successful_test_shas() -> List[str]:
    data = gh_json([
        "run", "list",
        "--workflow", WORKFLOW_NAME,
        "--branch", BRANCH,
        "--status", "success",
        "--json", "headSha",
        "--limit", str(LIMIT),
    ])
    return [it["headSha"] for it in data if it.get("headSha")]

def pick_furthest_ahead(shas: List[str]) -> str:
    latest: Optional[str] = None
    for cand in shas:
        if latest is None or is_ancestor(latest, cand):
            latest = cand
    return latest or ""

def resolve_latest_test() -> RefInfo:
    shas = list_successful_test_shas()
    if not shas:
        fail("No successful TEST runs found on branch")
    shas = [s for s in shas if is_ancestor(s, f"origin/{BRANCH}")]
    if not shas:
        fail("No TEST SHAs are ancestors of origin/main")
    latest_sha = pick_furthest_ahead(shas)
    if not latest_sha:
        fail("Could not determine latest TEST SHA")
    latest_ref = dev_tag_for_sha(latest_sha)
    if not latest_ref:
        fail(f"No dev-* tag found on latest TEST SHA ({latest_sha})")
    return RefInfo(sha=latest_sha, ref=latest_ref)

def resolve_this_run() -> RefInfo:
    if EVENT_NAME == "workflow_run":
        if not HEAD_SHA_AUTO:
            fail("WORKFLOW_RUN_HEAD_SHA missing for workflow_run event")
        ref = dev_tag_for_sha(HEAD_SHA_AUTO)
        if not ref:
            fail(f"No dev-* tag found on THIS SHA ({HEAD_SHA_AUTO})")
        return RefInfo(sha=HEAD_SHA_AUTO, ref=ref)

    if EVENT_NAME == "workflow_dispatch":
        if not MANUAL_REF:
            fail("MANUAL_REF (inputs.ref) is required for manual dispatch")
        if not re.match(r"^dev-\d{14}$", MANUAL_REF):
            fail(f"Invalid dev-* tag format: {MANUAL_REF}")
        if not git_ok(["rev-parse", "-q", "--verify", f"refs/tags/{MANUAL_REF}"]):
            fail(f"Tag not found: {MANUAL_REF}")
        sha = sha_for_tag(MANUAL_REF)
        if not sha:
            fail(f"Cannot resolve SHA for {MANUAL_REF}")
        if not is_ancestor(sha, f"origin/{BRANCH}"):
            fail(f"Chosen tag {MANUAL_REF} is not on origin/{BRANCH} history")
        return RefInfo(sha=sha, ref=MANUAL_REF)

    fail(f"Unsupported EVENT_NAME: {EVENT_NAME}")
    raise AssertionError("unreachable")

def enforce_guard(this_: RefInfo, latest: RefInfo) -> None:
    older_than_latest = (this_.sha != latest.sha) and is_ancestor(this_.sha, latest.sha)

    if EVENT_NAME == "workflow_run":
        if older_than_latest:
            fail(
                f"Stale PreProd approval. Latest tested is {latest.ref} ({latest.sha}); "
                f"this run is {this_.ref} ({this_.sha})."
            )
    else:
        if ALLOW_OLDER != "true" and older_than_latest:
            fail("Older than latest tested. Set allow_older=true if you intend to backdeploy.")

def write_outputs(this_: RefInfo, latest: RefInfo) -> None:
    out = os.getenv("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a") as f:
        f.write(f"this_sha={this_.sha}\n")
        f.write(f"this_ref={this_.ref}\n")
        f.write(f"latest_test_sha={latest.sha}\n")
        f.write(f"latest_test_ref={latest.ref}\n")


def main() -> int:
    require_token()
    fetch_graph()
    latest = resolve_latest_test()
    current = resolve_this_run()
    enforce_guard(current, latest)
    write_outputs(current, latest)
    print(f"THIS: {current.ref} ({current.sha})")
    print(f"LATEST TEST: {latest.ref} ({latest.sha})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
