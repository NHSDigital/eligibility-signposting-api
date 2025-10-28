"""
Pre-release resolver:
- Determines the furthest-ahead successful (TEST env deployed) commit on main (sha + dev-* tag).
- Resolves THIS run's sha + dev-* tag (auto via workflow_run, or manual via input tag).
- Applies the stale-run guard (auto blocks older; manual requires allow_older=true).
- Fails if the commit being run is not the furthest-ahead successful
- Emits outputs for later steps.

Outputs (via $GITHUB_OUTPUT):
  this_sha, this_ref, latest_test_sha, latest_test_ref
"""

from __future__ import annotations
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Optional, NoReturn

from ci_utils import (
    BRANCH,
    fail,
    ensure_token,
    fetch_latest_from_remote,
    gh_json,
    dev_tag_for_sha,
    sha_for_tag,
    is_ancestor,
    git_ok,
)

WORKFLOW_NAME = os.getenv("WORKFLOW_NAME", "3. CD | Deploy to Test")
LIMIT = int(os.getenv("LIMIT", "30"))
EVENT_NAME = os.getenv("EVENT_NAME", "")
HEAD_SHA_AUTO = os.getenv("WORKFLOW_RUN_HEAD_SHA", "")
MANUAL_REF = os.getenv("MANUAL_REF", "")
ALLOW_OLDER = os.getenv("ALLOW_OLDER", "true").lower()

@dataclass(frozen=True)
class RefInfo:
    sha: str
    ref: str

def list_successful_test_shas() -> List[str]:
    data = gh_json([
        "run", "list",
        "--workflow", WORKFLOW_NAME,
        "--branch", BRANCH,
        "--status", "success",
        "--json", "headSha",
        "--limit", str(LIMIT),
    ])
    return [c["headSha"] for c in data if c.get("headSha")]

def pick_furthest_ahead(shas: List[str]) -> str:
    latest: Optional[str] = None
    for candidate in shas:
        if latest is None or is_ancestor(latest, candidate):
            latest = candidate
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

def enforce_guard(current: RefInfo, latest: RefInfo) -> None:
    older_than_latest = (current.sha != latest.sha) and is_ancestor(current.sha, latest.sha)
    if EVENT_NAME == "workflow_run":
        if older_than_latest:
            fail(
                f"Stale PreProd approval. Latest tested is {latest.ref} ({latest.sha}); "
                f"this run is {current.ref} ({current.sha})."
            )
    else:
        if ALLOW_OLDER != "true" and older_than_latest:
            fail("Older than latest tested. Set allow_older=true if you intend to backdeploy.")

def write_outputs(current: RefInfo, latest: RefInfo) -> None:
    out = os.getenv("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a") as f:
        f.write(f"this_sha={current.sha}\n")
        f.write(f"this_ref={current.ref}\n")
        f.write(f"latest_test_sha={latest.sha}\n")
        f.write(f"latest_test_ref={latest.ref}\n")

def main() -> int:
    ensure_token()
    fetch_latest_from_remote()
    latest = resolve_latest_test()
    current = resolve_this_run()
    enforce_guard(current, latest)
    write_outputs(current, latest)
    print(f"THIS: {current.ref} ({current.sha})")
    print(f"LATEST TEST: {latest.ref} ({latest.sha})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
