"""
Pre-release resolver:
- Determines the furthest-ahead successful (TEST env deployed) commit on main (sha + dev-* tag).
- Resolves THIS run's sha + dev-* tag (auto via workflow_run, or manual via input tag).
- Applies the stale-run guard (auto blocks older).
- Fails if the commit being run is not the furthest-ahead successful
- Emits outputs for later steps.

Outputs (via $GITHUB_OUTPUT):
  this_sha, this_ref, latest_test_sha, latest_test_ref
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import List, Optional

from ci_utils import (
    BRANCH,
    fail,
    ensure_token,
    fetch_latest_from_remote,
    dev_tag_for_sha,
    sha_for_tag,
    is_ancestor,
    git_ok,
    run
)

WORKFLOW_ID = os.getenv("TEST_WORKFLOW_ID", "190123511")
LIMIT = int(os.getenv("LIMIT", "100"))

HEAD_SHA_AUTO = os.getenv("WORKFLOW_RUN_HEAD_SHA", "")
MANUAL_REF = os.getenv("MANUAL_REF", "")
REPO = "NHSDigital/eligibility-signposting-api"

@dataclass(frozen=True)
class RefInfo:
    sha: str
    ref: str

def get_event_name() -> str:
    """Determine the effective event name,
     correcting for act quirks."""
    evt_env = os.getenv("GITHUB_EVENT_NAME", "")
    evt_payload = None
    path = os.getenv("GITHUB_EVENT_PATH")
    if path and os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict):
                evt_payload = data.get("event_name")
        except Exception:
            pass

    # If running under act, prefer payload’s event_name if present
    if os.getenv("ACT") == "true" and evt_payload:
        return evt_payload

    return evt_payload or evt_env or ""

EVENT_NAME = get_event_name()

def _ensure_gh_token_env() -> None:
    if "GH_TOKEN" not in os.environ and os.environ.get("GITHUB_TOKEN"):
        os.environ["GH_TOKEN"] = os.environ["GITHUB_TOKEN"]

def _run_gh(args: list[str]) -> str:
    _ensure_gh_token_env()
    cmd = ["gh", *args, "--repo", REPO]
    cp = run(cmd, check=False)
    if cp.returncode != 0:
        # surface errors for act logs
        print("---- gh STDOUT ----\n", cp.stdout or "")
        print("---- gh STDERR ----\n", cp.stderr or "")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return cp.stdout

def list_successful_test_shas() -> List[str]:
    """
    Return SHAs for successful runs of the test deploy workflow on BRANCH.
    """
    out = _run_gh([
        "run", "list",
        "--workflow", str(WORKFLOW_ID),
        "--json", "headBranch,headSha,conclusion,createdAt",
        "--limit", str(LIMIT),
    ])
    rows = json.loads(out or "[]")

    # keep successful runs on the target branch with a SHA
    rows = [
        r for r in rows
        if r.get("conclusion") == "success"
        and r.get("headBranch") == BRANCH
        and r.get("headSha")
    ]

    # newest first (ISO timestamps sort lexicographically)
    rows.sort(key=lambda r: r.get("createdAt", ""), reverse=True)

    return [r["headSha"] for r in rows]

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
    if EVENT_NAME == "workflow_run" and older_than_latest:
        fail(
            f"Stale PreProd approval. Latest tested is {latest.ref} ({latest.sha}); "
            f"this run is {current.ref} ({current.sha})."
            )

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
