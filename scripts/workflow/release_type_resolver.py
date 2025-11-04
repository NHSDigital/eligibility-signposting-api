"""
Resolve release_type from PR labels with safe defaults.

Modes
- Manual override (MANUAL_RELEASE_TYPE): emit that and exit.
- Aggregate mode (AGGREGATE=true): consider TEST-deployed PRs merged since latest final tag
  up to LATEST_TEST_SHA (BOUNDARY), and pick highest of major > minor > patch > rc.

Env inputs
- GH_TOKEN / GITHUB_TOKEN: required
- THIS_SHA: SHA being promoted (required unless manual override)
- LATEST_TEST_SHA: required when AGGREGATE=true
- MANUAL_RELEASE_TYPE: (rc|patch|minor|major)
- AGGREGATE: "true"|"false" (default "false")
- BRANCH: branch (default "main")

Outputs
- release_type: rc|patch|minor|major
- basis: manual|single-pr|aggregate
- pr_numbers: comma-separated PR numbers considered
"""

from __future__ import annotations
import os
import sys
from typing import List, Set

from ci_utils import (
    ensure_token,
    fetch_latest_from_remote,
    latest_final_tag,
    first_commit,
    list_merged_pr_commits,
    prs_for_commit,
    labels_for_pr,
    fail,
)

def pick_highest(labels: List[str]) -> str | None:
    has_major = any(l == "release:major" for l in labels)
    has_minor = any(l == "release:minor" for l in labels)
    has_patch = any(l == "release:patch" for l in labels)
    has_rc    = any(l == "release:rc"    for l in labels)
    if has_major: return "major"
    if has_minor: return "minor"
    if has_patch: return "patch"
    if has_rc:    return "rc"
    return None

def main() -> int:
    ensure_token()

    manual = (os.getenv("MANUAL_RELEASE_TYPE") or "").strip()
    if manual:
        if manual not in {"rc","patch","minor","major"}:
            fail(f"Invalid MANUAL_RELEASE_TYPE: {manual}")
        out = os.getenv("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write(f"release_type={manual}\n")
                f.write("basis=manual\n")
                f.write("pr_numbers=\n")
        print(f"Release type (manual) → {manual}")
        return 0

    this_sha = (os.getenv("THIS_SHA") or "").strip()
    if not this_sha:
        fail("Cannot determine sha")

    fetch_latest_from_remote()

    aggregate = (os.getenv("AGGREGATE","false").lower() == "true")
    pr_nums: Set[int] = set()
    basis = "single-pr"
    release_type = "rc"

    if aggregate:
        latest_test_sha = (os.getenv("LATEST_TEST_SHA") or "").strip()
        if not latest_test_sha:
            fail("LATEST_TEST_SHA is required when AGGREGATE=true")
        base = latest_final_tag() or first_commit()
        merges = list_merged_pr_commits(base, latest_test_sha)
        for m in merges:
            for n in prs_for_commit(m):
                pr_nums.add(n)
        all_labels: List[str] = []
        for pr in pr_nums:
            all_labels.extend(labels_for_pr(pr))
        release_type = pick_highest(all_labels) or "rc"
        basis = "aggregate"
    else:
        pnums = prs_for_commit(this_sha)
        if pnums:
            pr = pnums[0]
            pr_nums.add(pr)
            release_type = pick_highest(labels_for_pr(pr)) or "rc"
        else:
            release_type = "rc"
        basis = "single-pr"

    out = os.getenv("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"release_type={release_type}\n")
            f.write(f"basis={basis}\n")
            f.write(f"pr_numbers={','.join(str(x) for x in sorted(pr_nums))}\n")

    print(f"Release type ({basis}) → {release_type}")
    if pr_nums:
        print(f"Considered PRs: {', '.join(str(x) for x in sorted(pr_nums))}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
