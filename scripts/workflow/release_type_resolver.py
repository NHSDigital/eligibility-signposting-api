"""
Resolve release_type from PR labels with safe defaults.

Modes

- Manual override (MANUAL_RELEASE_TYPE): emit that and exit.
- Single-PR mode (default): inspect PR labels for THIS_SHA; default "rc".
- Aggregate mode (AGGREGATE=true): consider TEST deployed PRs merged since latest final tag*
   up to LATEST_TEST_SHA (BOUNDARY), and pick highest of major > minor > patch > rc

Env inputs

GH_TOKEN / GITHUB_TOKEN: required
THIS_SHA: SHA being promoted (required unless manual override)
LATEST_TEST_SHA: required when AGGREGATE=true
MANUAL_RELEASE_TYPE: (rc|patch|minor|major)
AGGREGATE: "true"|"false" (default "false")
BRANCH: branch (default "main")

Outputs

release_type: rc|patch|minor|major
basis: manual|single-pr|aggregate
pr_numbers: comma-separated PR numbers considered
"""

import os, subprocess, sys
from typing import List, Set

BRANCH = os.getenv("BRANCH", "main")

def run(cmd: List[str], check=True, capture=True) -> subprocess.CompletedProcess:
    # cp = completed process (will use this to refer)
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)

def fail(msg: str) -> int:
    print(f"::error::{msg}", file=sys.stderr)
    return 1

def ensure_graph():
    run(["git","fetch","origin", BRANCH, "--quiet"], check=True)
    run(["git","fetch","--tags","--force","--quiet"], check=True)

def gh_api(path: str, jq: str | None = None) -> List[str]:
    """
    A simple python wrapper around the GitHub API
    to make it a callable function.
    """
    args = ["gh","api", path]
    if jq:
        args += ["--jq", jq]
    cp = run(args, check=True)
    return [x for x in cp.stdout.splitlines() if x]

def latest_final_tag() -> str | None:
    """
    Grabs the version tags and sorts semantically desc
    """
    cp = run(["git","tag","--list","v[0-9]*.[0-9]*.[0-9]*","--sort=-v:refname"], check=True)
    tags = cp.stdout.splitlines()
    return tags[0] if tags else None

def first_commit() -> str:
    """
    Returns the first commit of the current branch.

    We will never use this for our project since we
    already have a release but can be used as a
    fallback for new projects.
    """
    return run(["git","rev-list","--max-parents=0","HEAD"], check=True).stdout.strip()

def list_merged_pr_commits(base: str, head: str) -> List[str]:
    rng = f"{base}..{head}"
    cp = run(["git","rev-list","--merges","--first-parent", rng], check=False)
    return [x for x in cp.stdout.splitlines() if x]

def prs_for_commit(sha: str) -> List[int]:
    nums = gh_api(f"/repos/{os.getenv('GITHUB_REPOSITORY')}/commits/{sha}/pulls", jq=".[].number")
    return [int(n) for n in nums]

def labels_for_pr(pr: int) -> List[str]:
    return gh_api(f"/repos/{os.getenv('GITHUB_REPOSITORY')}/issues/{pr}/labels", jq=".[].name")

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
    if not (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")):
        return fail("GH_TOKEN/GITHUB_TOKEN is required")

    manual = (os.getenv("MANUAL_RELEASE_TYPE") or "").strip()
    if manual:
        if manual not in {"rc","patch","minor","major"}:
            return fail(f"Invalid MANUAL_RELEASE_TYPE: {manual}")
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
        return fail("THIS_SHA is required when no MANUAL_RELEASE_TYPE is provided")

    ensure_graph()

    aggregate = (os.getenv("AGGREGATE","false").lower() == "true")
    pr_nums: Set[int] = set()
    basis = "single-pr"
    release_type = "rc"

    if aggregate:
        latest_test_sha = (os.getenv("LATEST_TEST_SHA") or "").strip()
        if not latest_test_sha:
            return fail("LATEST_TEST_SHA is required when AGGREGATE=true")
        base = latest_final_tag() or first_commit()
        merges = first_parent_merges(base, latest_test_sha)
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
