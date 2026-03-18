#!/usr/bin/env bash
set -euo pipefail

MODE="${DEVENV_MODE:-check}"

print_create_step_summary() {
  cat <<'EOF'
=== Create Mode Step Summary ===
[1/6] Repository bootstrap (workspace, clone, base branch, init branch)
[2/6] Base system remediation (OS checks, sudo, apt refresh/packages, core commands)
[3/6] Docker remediation (install/fix daemon and compose)
[4/6] asdf + toolchain remediation
[5/6] Project setup remediation (make config/install)
[6/6] Validation (onboarding-check and configured test/build targets)
================================
EOF
}

announce_create_step() {
  local step="$1"
  local title="$2"
  printf '\n>>> [%s/6] %s\n' "$step" "$title"
}

# Optional YAML loading (only fills missing env vars)
load_config_from_yaml() {
  local config_path="${DEVENV_CONFIG_PATH:-}"
  [[ -n "$config_path" && -f "$config_path" ]] || return 0
  command -v python3 >/dev/null 2>&1 || return 0

  local emitted
  emitted="$(python3 - "$config_path" <<'PY' || true
import sys
p = sys.argv[1]
try:
    import yaml
except Exception:
    sys.exit(0)

cfg = yaml.safe_load(open(p, "r", encoding="utf-8")) or {}

def get(path, default=""):
    node = cfg
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node

pairs = {
    "DEVENV_WSL_CLONE_URL": get(["git", "clone_url"], ""),
    "DEVENV_WSL_BASE_BRANCH": get(["git", "default_base_branch"], "main"),
    "DEVENV_INIT_BRANCH_PATTERN": get(["git", "init_branch", "pattern"], "init/{user}/init_branch_{timestamp}"),
    "DEVENV_INIT_BRANCH_TIMESTAMP_FORMAT": get(["git", "init_branch", "timestamp_format"], "yyyyMMddHHmm"),
    "DEVENV_INIT_BRANCH_PUSH_ON_CREATE": str(get(["git", "init_branch", "push_on_create"], True)).lower(),
    "DEVENV_INIT_BRANCH_FAIL_IF_EXISTS": str(get(["git", "init_branch", "fail_if_exists_on_remote"], True)).lower(),
    "DEVENV_WSL_REPO_ROOT": get(["platforms", "windows-wsl", "wsl", "repo_root"], "/home/{user}/workspace"),
    "DEVENV_WSL_REPO_NAME": get(["platforms", "windows-wsl", "wsl", "repo_name"], "eligibility-signposting-api"),
    "DEVENV_REQUIRE_NON_ROOT": str(get(["platforms", "windows-wsl", "wsl", "linux_user", "require_non_root"], True)).lower(),
    "DEVENV_DOCKER_STRATEGY": get(["tooling", "docker_strategy"], "engine"),
}
for k, v in pairs.items():
    if v is None:
        v = ""
    print(f"{k}\t{v}")
PY
)"
  while IFS=$'\t' read -r k v; do
    [[ -n "$k" ]] || continue
    if [[ -z "${!k:-}" ]]; then
      export "$k=$v"
    fi
  done <<< "$emitted"
}

sanitize_user() {
  local raw="$1"
  raw="$(echo "$raw" | tr '[:upper:]' '[:lower:]')"
  raw="$(echo "$raw" | sed -E 's/[[:space:]]+/-/g; s/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//')"
  [[ -n "$raw" ]] || raw="developer"
  echo "$raw"
}

render_init_branch() {
  local pattern="$1"
  local user_segment="$2"
  local timestamp="$3"
  local rendered
  rendered="${pattern//\{user\}/$user_segment}"
  rendered="${rendered//\{timestamp\}/$timestamp}"
  printf '%s\n' "$rendered" | tr -d '\r'
}

validate_init_branch_pattern() {
  local pattern="$1"

  if [[ "$pattern" != *"{user}"* || "$pattern" != *"{timestamp}"* ]]; then
    echo "Init branch pattern must include both {user} and {timestamp}: $pattern" >&2
    exit 1
  fi

  local stripped
  stripped="${pattern//\{user\}/}"
  stripped="${stripped//\{timestamp\}/}"
  if [[ "$stripped" == *"{"* || "$stripped" == *"}"* ]]; then
    echo "Init branch pattern contains unsupported placeholder braces: $pattern" >&2
    exit 1
  fi
}

timestamp_from_format() {
  local fmt="${1:-yyyyMMddHHmm}"
  case "$fmt" in
    yyyyMMddHHmm) date +%Y%m%d%H%M ;;
    yyyyMMddHHmmss) date +%Y%m%d%H%M%S ;;
    *) date +%Y%m%d%H%M ;;
  esac
}

repo_exists() {
  local path="$1"
  git -C "$path" rev-parse --is-inside-work-tree >/dev/null 2>&1
}

resolve_base_ref() {
  local repo_path="$1"
  local base_branch="$2"

  if git -C "$repo_path" show-ref --verify --quiet "refs/remotes/origin/$base_branch"; then
    printf 'origin/%s\n' "$base_branch"
    return 0
  fi

  if git -C "$repo_path" show-ref --verify --quiet "refs/heads/$base_branch"; then
    printf '%s\n' "$base_branch"
    return 0
  fi

  if git_auth -C "$repo_path" ls-remote --exit-code --heads origin "$base_branch" >/dev/null 2>&1; then
    git_auth -C "$repo_path" fetch origin "$base_branch:refs/remotes/origin/$base_branch"
    printf 'origin/%s\n' "$base_branch"
    return 0
  fi

  return 1
}

AUTH_CLONE_URL=""
GIT_AUTH_CONFIG_KEY=""
GIT_AUTH_HEADER=""

git_auth() {
  if [[ -n "$GIT_AUTH_CONFIG_KEY" && -n "$GIT_AUTH_HEADER" ]]; then
    git -c credential.helper= -c "$GIT_AUTH_CONFIG_KEY=AUTHORIZATION: basic $GIT_AUTH_HEADER" "$@"
  else
    git "$@"
  fi
}

configure_git_https_auth() {
  if [[ "$CLONE_URL" != https://* ]]; then
    return
  fi

  if [[ -z "${DEVENV_GIT_PAT_B64:-}" ]]; then
    echo "HTTPS git authentication requires a GitHub PAT in create mode." >&2
    exit 1
  fi

  DEVENV_GIT_PAT="$(printf '%s' "$DEVENV_GIT_PAT_B64" | base64 -d)"
  if [[ -z "$DEVENV_GIT_PAT" ]]; then
    echo "GitHub PAT is empty after decoding." >&2
    exit 1
  fi

  DEVENV_GIT_USERNAME="${DEVENV_GIT_USERNAME:-x-access-token}"
  local auth_scope
  auth_scope="$(printf '%s\n' "$CLONE_URL" | sed -E 's#(https://[^/]+/).*#\1#')"
  GIT_AUTH_CONFIG_KEY="http.${auth_scope}.extraheader"
  GIT_AUTH_HEADER="$(printf '%s:%s' "$DEVENV_GIT_USERNAME" "$DEVENV_GIT_PAT" | base64 | tr -d '\n')"
  AUTH_CLONE_URL="${CLONE_URL/https:\/\//https://$DEVENV_GIT_USERNAME@}"
}

cleanup_git_https_auth() {
  unset DEVENV_GIT_PAT
  GIT_AUTH_CONFIG_KEY=""
  GIT_AUTH_HEADER=""
  AUTH_CLONE_URL=""
}

require_non_root_if_configured() {
  local require_non_root="${DEVENV_REQUIRE_NON_ROOT:-true}"
  if [[ "$require_non_root" == "true" && "$(id -u)" -eq 0 ]]; then
    echo "Non-root user is required by config." >&2
    exit 1
  fi
}

load_config_from_yaml

WSL_USERNAME_EFFECTIVE="${DEVENV_WSL_USERNAME:-}"
if [[ -z "$WSL_USERNAME_EFFECTIVE" ]]; then
  WSL_USERNAME_EFFECTIVE="$(whoami)"
fi

WSL_REPO_ROOT="${DEVENV_WSL_REPO_ROOT:-}"
if [[ -z "$WSL_REPO_ROOT" ]]; then
  WSL_REPO_ROOT="/home/$WSL_USERNAME_EFFECTIVE/workspace"
fi

WSL_REPO_NAME="${DEVENV_WSL_REPO_NAME:-}"
if [[ -z "$WSL_REPO_NAME" ]]; then
  WSL_REPO_NAME="eligibility-signposting-api"
fi

WSL_REPO_PATH="${DEVENV_WSL_REPO_PATH:-}"
if [[ -z "$WSL_REPO_PATH" ]]; then
  WSL_REPO_PATH="$WSL_REPO_ROOT/$WSL_REPO_NAME"
fi

CLONE_URL="${DEVENV_WSL_CLONE_URL:-https://github.com/NHSDigital/eligibility-signposting-api.git}"
BASE_BRANCH="${DEVENV_WSL_BASE_BRANCH:-main}"
INIT_BRANCH_PATTERN="${DEVENV_INIT_BRANCH_PATTERN:-}"
if [[ -z "$INIT_BRANCH_PATTERN" ]]; then
  INIT_BRANCH_PATTERN='init/{user}/init_branch_{timestamp}'
fi
INIT_TS_FORMAT="${DEVENV_INIT_BRANCH_TIMESTAMP_FORMAT:-yyyyMMddHHmm}"
PUSH_INIT="${DEVENV_INIT_BRANCH_PUSH_ON_CREATE:-true}"
FAIL_IF_EXISTS="${DEVENV_INIT_BRANCH_FAIL_IF_EXISTS:-true}"

WINDOWS_ORIGIN_URL="${DEVENV_WINDOWS_ORIGIN_URL:-}"

require_non_root_if_configured

echo "Mode: $MODE"
echo "WSL repo root: $WSL_REPO_ROOT"
echo "WSL repo path: $WSL_REPO_PATH"
echo "Clone URL: $CLONE_URL"
echo "Base branch: $BASE_BRANCH"

if [[ "$MODE" == "check" ]]; then
  if repo_exists "$WSL_REPO_PATH"; then
    actual_origin="$(git -C "$WSL_REPO_PATH" remote get-url origin 2>/dev/null || true)"
    echo "repo_present: yes"
    echo "origin: ${actual_origin:-<missing>}"
    echo "branch: $(git -C "$WSL_REPO_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '<unknown>')"
    echo "commit: $(git -C "$WSL_REPO_PATH" rev-parse --short HEAD 2>/dev/null || echo '<unknown>')"

    if [[ -n "$WINDOWS_ORIGIN_URL" && -n "$actual_origin" && "$WINDOWS_ORIGIN_URL" != "$actual_origin" ]]; then
      echo "Origin mismatch with Windows repo." >&2
      exit 1
    fi
  else
    echo "repo_present: no"
  fi
  exit 0
fi

if [[ "$MODE" != "create" ]]; then
  echo "Unsupported DEVENV_MODE: $MODE" >&2
  exit 1
fi

print_create_step_summary
announce_create_step "1" "Repository bootstrap"

configure_git_https_auth
trap cleanup_git_https_auth EXIT

# Only directory structure creation allowed here: WSL workspace root
mkdir -p "$WSL_REPO_ROOT"

if ! command -v git >/dev/null 2>&1; then
  if [[ -z "${DEVENV_SUDO_PASSWORD_B64:-}" ]]; then
    echo "git is missing in WSL and sudo credentials are unavailable." >&2
    exit 1
  fi

  bootstrap_sudo_password="$(printf '%s' "$DEVENV_SUDO_PASSWORD_B64" | base64 -d)"
  printf '%s\n' "$bootstrap_sudo_password" | sudo -S -p '' apt update
  printf '%s\n' "$bootstrap_sudo_password" | sudo -S -p '' apt install -y git
  unset bootstrap_sudo_password

  if ! command -v git >/dev/null 2>&1; then
    echo "Failed to install git in WSL." >&2
    exit 1
  fi
fi

if ! repo_exists "$WSL_REPO_PATH"; then
  if [[ -e "$WSL_REPO_PATH" ]]; then
    echo "Path exists but is not a git repo: $WSL_REPO_PATH" >&2
    exit 1
  fi
  git_auth clone "${AUTH_CLONE_URL:-$CLONE_URL}" "$WSL_REPO_PATH"
  git_auth -C "$WSL_REPO_PATH" remote set-url origin "$CLONE_URL"
fi

git_auth -C "$WSL_REPO_PATH" fetch origin --prune
base_ref="$(resolve_base_ref "$WSL_REPO_PATH" "$BASE_BRANCH" || true)"
if [[ -z "$base_ref" ]]; then
  echo "Base branch '$BASE_BRANCH' is unavailable in '$WSL_REPO_PATH'." >&2
  echo "Expected either origin/$BASE_BRANCH on remote, or a local branch named $BASE_BRANCH in the WSL repo." >&2
  echo "If this branch only exists on your Windows clone, push it first and rerun:" >&2
  echo "  git push -u origin $BASE_BRANCH" >&2
  exit 1
fi

git_auth -C "$WSL_REPO_PATH" checkout -B "$BASE_BRANCH" "$base_ref"

git_user="$(git -C "$WSL_REPO_PATH" config --get user.name 2>/dev/null || true)"
[[ -n "$git_user" ]] || git_user="$(whoami)"
user_segment="$(sanitize_user "$git_user")"
timestamp="$(timestamp_from_format "$INIT_TS_FORMAT")"
validate_init_branch_pattern "$INIT_BRANCH_PATTERN"
init_branch="$(render_init_branch "$INIT_BRANCH_PATTERN" "$user_segment" "$timestamp")"

if [[ "$FAIL_IF_EXISTS" == "true" ]]; then
  if git_auth -C "$WSL_REPO_PATH" ls-remote --exit-code --heads origin "$init_branch" >/dev/null 2>&1; then
    echo "Init branch already exists on remote: $init_branch" >&2
    exit 1
  fi
fi

if [[ "$init_branch" == *"{"* || "$init_branch" == *"}"* ]]; then
  echo "Resolved init branch contains unresolved placeholders: $init_branch" >&2
  exit 1
fi

git_auth -C "$WSL_REPO_PATH" checkout -B "$init_branch" "$BASE_BRANCH"
if [[ "$PUSH_INIT" == "true" ]]; then
  git_auth -C "$WSL_REPO_PATH" push -u origin "$init_branch"
fi

echo "Created/checked out init branch: $init_branch"

cleanup_git_https_auth
trap - EXIT

# Continue with existing devenv setup in the WSL repo
REPO_ROOT="$WSL_REPO_PATH"
MODULES_DIR="$REPO_ROOT/devenv/modules"
DEFAULTS_FILE="$REPO_ROOT/devenv/config/defaults.env"

if [[ -f "$DEFAULTS_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$DEFAULTS_FILE"
fi

# shellcheck source=/dev/null
source "$MODULES_DIR/common.sh"
# shellcheck source=/dev/null
source "$MODULES_DIR/report.sh"
# shellcheck source=/dev/null
source "$MODULES_DIR/apt.sh"
# shellcheck source=/dev/null
source "$MODULES_DIR/docker.sh"
# shellcheck source=/dev/null
source "$MODULES_DIR/asdf.sh"
# shellcheck source=/dev/null
source "$MODULES_DIR/project.sh"

legacy_docker_strategy="${DOCKER_STRATEGY:-}"
DOCKER_STRATEGY="${DEVENV_DOCKER_STRATEGY:-$legacy_docker_strategy}"
if [[ -z "$DOCKER_STRATEGY" ]]; then
  DOCKER_STRATEGY="engine"
fi

ASDF_VERSION="${ASDF_VERSION:-v0.16.7}"

python_seed_version="${PYTHON_VERSION:-3.13.5}"
if [[ -n "${DEVENV_PYTHON_VERSION:-}" ]]; then
  PYTHON_VERSION="$DEVENV_PYTHON_VERSION"
else
  PYTHON_VERSION="$(version_from_tool_versions python "$python_seed_version")"
fi

poetry_seed_version="${POETRY_VERSION:-2.1.4}"
if [[ -n "${DEVENV_POETRY_VERSION:-}" ]]; then
  POETRY_VERSION="$DEVENV_POETRY_VERSION"
else
  POETRY_VERSION="$(version_from_tool_versions poetry "$poetry_seed_version")"
fi

node_seed_version="${NODE_VERSION:-22.18.0}"
if [[ -n "${DEVENV_NODE_VERSION:-}" ]]; then
  NODE_VERSION="$DEVENV_NODE_VERSION"
else
  NODE_VERSION="$(version_from_tool_versions nodejs "$node_seed_version")"
fi

terraform_seed_version="${TERRAFORM_VERSION:-1.12.1}"
if [[ -n "${DEVENV_TERRAFORM_VERSION:-}" ]]; then
  TERRAFORM_VERSION="$DEVENV_TERRAFORM_VERSION"
else
  TERRAFORM_VERSION="$(version_from_tool_versions terraform "$terraform_seed_version")"
fi

precommit_seed_version="${PRECOMMIT_VERSION:-4.2.0}"
if [[ -n "${DEVENV_PRECOMMIT_VERSION:-}" ]]; then
  PRECOMMIT_VERSION="$DEVENV_PRECOMMIT_VERSION"
else
  PRECOMMIT_VERSION="$(version_from_tool_versions pre-commit "$precommit_seed_version")"
fi

vale_seed_version="${VALE_VERSION:-3.11.2}"
if [[ -n "${DEVENV_VALE_VERSION:-}" ]]; then
  VALE_VERSION="$DEVENV_VALE_VERSION"
else
  VALE_VERSION="$(version_from_tool_versions vale "$vale_seed_version")"
fi

act_seed_version="${ACT_VERSION:-0.2.77}"
if [[ -n "${DEVENV_ACT_VERSION:-}" ]]; then
  ACT_VERSION="$DEVENV_ACT_VERSION"
else
  ACT_VERSION="$(version_from_tool_versions act "$act_seed_version")"
fi

legacy_run_project_setup="${RUN_PROJECT_SETUP:-}"
RUN_PROJECT_SETUP="${DEVENV_RUN_PROJECT_SETUP:-$legacy_run_project_setup}"
if [[ -z "$RUN_PROJECT_SETUP" ]]; then
  RUN_PROJECT_SETUP="true"
fi

legacy_run_validation="${RUN_VALIDATION:-}"
RUN_VALIDATION="${DEVENV_RUN_VALIDATION:-$legacy_run_validation}"
if [[ -z "$RUN_VALIDATION" ]]; then
  RUN_VALIDATION="true"
fi

legacy_run_unit_tests="${RUN_UNIT_TESTS:-}"
RUN_UNIT_TESTS="${DEVENV_RUN_UNIT_TESTS:-$legacy_run_unit_tests}"
if [[ -z "$RUN_UNIT_TESTS" ]]; then
  RUN_UNIT_TESTS="true"
fi

legacy_run_build="${RUN_BUILD:-}"
RUN_BUILD="${DEVENV_RUN_BUILD:-$legacy_run_build}"
if [[ -z "$RUN_BUILD" ]]; then
  RUN_BUILD="false"
fi

legacy_run_integration_tests="${RUN_INTEGRATION_TESTS:-}"
RUN_INTEGRATION_TESTS="${DEVENV_RUN_INTEGRATION_TESTS:-$legacy_run_integration_tests}"
if [[ -z "$RUN_INTEGRATION_TESTS" ]]; then
  RUN_INTEGRATION_TESTS="false"
fi

REPORT_DIR="$REPO_ROOT/devenv/reports"
mkdir -p "$REPORT_DIR"

init_sudo_password

bootstrap_on_error() {
  local exit_code=$?
  local line_number="$1"
  report_fail "Unexpected bootstrap error at line $line_number"
  report_finalize "failure"
  exit "$exit_code"
}

trap 'bootstrap_on_error $LINENO' ERR
trap cleanup_secret EXIT

report_init

announce_create_step "2" "Base system remediation"
report_section "Base system"
check_ubuntu_release
verify_sudo_access
ensure_core_apt_packages
verify_core_commands
verify_gnu_toolchain

announce_create_step "3" "Docker remediation"
report_section "Docker"
ensure_docker_engine

announce_create_step "4" "asdf and toolchain remediation"
report_section "asdf and toolchain"
ensure_asdf
ensure_asdf_tool python "$PYTHON_VERSION" python
ensure_asdf_tool poetry "$POETRY_VERSION" poetry
ensure_asdf_tool nodejs "$NODE_VERSION" node
ensure_asdf_tool terraform "$TERRAFORM_VERSION" terraform
ensure_asdf_tool pre-commit "$PRECOMMIT_VERSION" pre-commit
ensure_asdf_tool vale "$VALE_VERSION" vale
ensure_asdf_tool act "$ACT_VERSION" act

announce_create_step "5" "Project setup remediation"
report_section "Project setup"
ensure_project_files
run_project_setup

announce_create_step "6" "Validation"
report_section "Validation"
run_validation

if [[ "$REPORT_FAILURES" -eq 0 ]]; then
  report_finalize "success"
else
  report_finalize "failure"
  exit 1
fi
