import json, os, re, subprocess, sys
from typing import List, Optional

WORKFLOW_NAME = os.getenv("WORKFLOW_NAME", "3. CD | Deploy to Test")
BRANCH        = os.getenv("BRANCH", "main")
LIMIT         = int(os.getenv("LIMIT", "30"))

EVENT_NAME    = os.getenv("EVENT_NAME", "")
HEAD_SHA_AUTO = os.getenv("WORKFLOW_RUN_HEAD_SHA", "")
MANUAL_REF    = os.getenv("MANUAL_REF", "")
ALLOW_OLDER   = os.getenv("ALLOW_OLDER", "false").lower()
REPO          = os.getenv("GITHUB_REPOSITORY", "")

def run(cmd: List[str], check=True, capture=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)

def git_ok(args: List[str]) -> bool:
    return subprocess.run(["git", *args]).returncode == 0

def is_ancestor(a: str, b: str) -> bool:
    return subprocess.run(["git","merge-base","--is-ancestor", a, b]).returncode == 0

def fetch_graph():
    subprocess.run(["git","fetch","origin", BRANCH, "--quiet"], check=True)
    subprocess.run(["git","fetch","--tags","--force","--quiet"], check=True)

def dev_tag_for_sha(sha: str) -> Optional[str]:
    cp = run(["git","tag","--points-at", sha], check=False)
    for t in (cp.stdout or "").splitlines():
        if t.startswith("dev-"):
            return t
    return None

def sha_for_tag(tag: str) -> Optional[str]:
    cp = run(["git","rev-list","-n1", tag], check=False)
    return cp.stdout.strip() or None

def list_successful_test_shas() -> List[str]:
    cp = run([
        "gh","run","list",
        "--workflow", WORKFLOW_NAME,
        "--branch", BRANCH,
        "--status","success",
        "--json","headSha",
        "--limit", str(LIMIT),
    ])
    data = json.loads(cp.stdout or "[]")
    return [it["headSha"] for it in data if "headSha" in it and it["headSha"]]

def pick_furthest_ahead(shas: List[str]) -> str:
    latest = None
    for cand in shas:
        if latest is None:
            latest = cand
            continue
        if is_ancestor(latest, cand):
            latest = cand
    return latest

def fail(msg: str) -> int:
    print(f"::error::{msg}", file=sys.stderr)
    return 1

def main() -> int:
    if not (os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")):
        return fail("GH_TOKEN/GITHUB_TOKEN is required")

    fetch_graph()

    shas = list_successful_test_shas()
    if not shas:
        return fail("No successful TEST runs found on branch")
    shas = [s for s in shas if is_ancestor(s, f"origin/{BRANCH}")]
    if not shas:
        return fail("No TEST SHAs are ancestors of origin/main")
    latest_test_sha = pick_furthest_ahead(shas)
    if not latest_test_sha:
        return fail("Could not determine latest TEST SHA")
    latest_test_ref = dev_tag_for_sha(latest_test_sha)
    if not latest_test_ref:
        return fail(f"No dev-* tag found on latest TEST SHA ({latest_test_sha})")

    if EVENT_NAME == "workflow_run":
        if not HEAD_SHA_AUTO:
            return fail("WORKFLOW_RUN_HEAD_SHA missing for workflow_run event")
        this_sha = HEAD_SHA_AUTO
        this_ref = dev_tag_for_sha(this_sha) or ""
        if not this_ref:
            return fail(f"No dev-* tag found on THIS SHA ({this_sha})")
    elif EVENT_NAME == "workflow_dispatch":
        if not MANUAL_REF:
            return fail("MANUAL_REF (inputs.ref) is required for manual dispatch")
        if not re.match(r"^dev-\d{14}$", MANUAL_REF):
            return fail(f"Invalid dev-* tag format: {MANUAL_REF}")
        if not git_ok(["rev-parse","-q","--verify", f"refs/tags/{MANUAL_REF}"]):
            return fail(f"Tag not found: {MANUAL_REF}")
        this_ref = MANUAL_REF
        this_sha = sha_for_tag(this_ref) or ""
        if not this_sha:
            return fail(f"Cannot resolve SHA for {this_ref}")
        if not is_ancestor(this_sha, f"origin/{BRANCH}"):
            return fail(f"Chosen tag {this_ref} is not on origin/{BRANCH} history")
    else:
        return fail(f"Unsupported EVENT_NAME: {EVENT_NAME}")

    if EVENT_NAME == "workflow_run":
        # Stale guard: block if THIS is behind latest tested
        if this_sha != latest_test_sha and is_ancestor(this_sha, latest_test_sha):
            return fail(
                f"Stale PreProd approval. Latest tested is {latest_test_ref} ({latest_test_sha}); "
                f"this run is {this_ref} ({this_sha})."
            )
    else:
        # Manual: allow older only if explicitly requested
        if ALLOW_OLDER != "true" and this_sha != latest_test_sha and is_ancestor(this_sha, latest_test_sha):
            return fail("Older than latest tested. Set allow_older=true if you intend to roll back deploy.")

    out = os.getenv("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"this_sha={this_sha}\n")
            f.write(f"this_ref={this_ref}\n")
            f.write(f"latest_test_sha={latest_test_sha}\n")
            f.write(f"latest_test_ref={latest_test_ref}\n")

    print(f"THIS: {this_ref} ({this_sha})")
    print(f"LATEST TEST: {latest_test_ref} ({latest_test_sha})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
