"""
Resolve release_type with manual override or aggregate-only mode.

Behaviour
- Manual override: if MANUAL_RELEASE_TYPE is set (rc|patch|minor|major), emit that and exit.
- Otherwise aggregate: scan PRs merged since latest final tag up to LATEST_TEST_SHA
and pick the highest label: major > minor > patch > rc.

Env inputs (required)
- GH_TOKEN / GITHUB_TOKEN
- LATEST_TEST_SHA (for aggregate path)

Optional
- MANUAL_RELEASE_TYPE: rc|patch|minor|major

Outputs
- release_type: rc|patch|minor|major
- basis: manual|aggregate
- pr_numbers: comma-separated PR numbers considered
"""

from __future__ import annotations
import os
import sys
from typing import Iterable, List, Set

from ci_utils import (
    ensure_token,
    fetch_latest_from_remote,
    latest_release_tag,
    first_commit,
    list_merge_commits,
    list_all_commits,
    prs_for_commit_via_api,
    commit_subject,
    parse_merge_subject_for_pr_numbers,
    labels_for_pr,
    fail,
)

def pick_highest(labels: Iterable[str]) -> str | None:
    labels = list(labels)
    if any(l == "release:major" for l in labels): return "major"
    if any(l == "release:minor" for l in labels): return "minor"
    if any(l == "release:patch" for l in labels): return "patch"
    if any(l == "release:rc"    for l in labels): return "rc"
    return None

def manual_override() -> str | None:
    manual = (os.getenv("MANUAL_RELEASE_TYPE") or "").strip()
    if not manual:
        return None
    if manual not in {"rc", "patch", "minor", "major"}:
        fail(f"Invalid MANUAL_RELEASE_TYPE: {manual}")
    return manual

def discover_prs(base: str, head: str) -> Set[int]:
    """
    Three-stage PR discovery in base..head:
    1) merge commits → commits/{sha}/pulls
    2) parse 'Merge pull request #123' subjects
    3) all commits → commits/{sha}/pulls (covers squash/rebase)
    """
    pr_nums: Set[int] = set()

    merges = list_merge_commits(base, head)

    # API on merge commits
    for m in merges:
        for n in prs_for_commit_via_api(m):
            pr_nums.add(n)

    # parse merge subjects
    for m in merges:
        subj = commit_subject(m)
        for n in parse_merge_subject_for_pr_numbers(subj):
            pr_nums.add(n)

    # scan all commits if still empty
    if not pr_nums:
        for c in list_all_commits(base, head):
            for n in prs_for_commit_via_api(c):
                pr_nums.add(n)

    return pr_nums

def compute_release_type(pr_nums: Set[int]) -> str:
    if not pr_nums:
        return "rc"
    all_labels: List[str] = []
    for pr in pr_nums:
        all_labels.extend(labels_for_pr(pr))
    return pick_highest(all_labels) or "rc"

def emit_outputs(release_type: str, basis: str, pr_nums: Set[int]) -> None:
    out = os.getenv("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a") as f:
        f.write(f"release_type={release_type}\n")
        f.write(f"basis={basis}\n")
        f.write(f"pr_numbers={','.join(str(x) for x in sorted(pr_nums))}\n")

def print_summary(basis: str, release_type: str, pr_nums: Set[int]) -> None:
    print(f"Release type ({basis}) → {release_type}")
    if pr_nums:
        print(f"Considered PRs: {', '.join(str(x) for x in sorted(pr_nums))}")
        try:
            from ci_utils import title_for_pr
            for pr in sorted(pr_nums):
                title = title_for_pr(pr)
                if title:
                    print(f"  #{pr}: {title}")
        except Exception:
            pass

def main() -> int:
    ensure_token()
    manual = manual_override()
    if manual:
        emit_outputs(manual, "manual", set())
        print(f"Release type (manual) → {manual}")
        return 0

    latest_test_sha = (os.getenv("LATEST_TEST_SHA") or "").strip()
    if not latest_test_sha:
        fail("This is not the latest tested candidate, there is a more recent one.")

    fetch_latest_from_remote()
    base = latest_release_tag() or first_commit()

    pr_nums = discover_prs(base, latest_test_sha)
    release_type = compute_release_type(pr_nums)

    emit_outputs(release_type, "aggregate", pr_nums)
    print_summary("aggregate", release_type, pr_nums)
    return 0

if __name__ == "__main__":
    sys.exit(main())
