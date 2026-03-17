#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MODULES_DIR="$REPO_ROOT/devenv/modules"
DEFAULTS_FILE="$REPO_ROOT/devenv/config/defaults.env"

# shellcheck source=/dev/null
source "$DEFAULTS_FILE"
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

MODE="${DEVENV_MODE:-check}"
DOCKER_STRATEGY="${DEVENV_DOCKER_STRATEGY:-${DOCKER_STRATEGY:-engine}}"

ASDF_VERSION="${ASDF_VERSION:-v0.16.7}"
PYTHON_VERSION="${DEVENV_PYTHON_VERSION:-$(version_from_tool_versions python "${PYTHON_VERSION:-3.13.5}")}"
POETRY_VERSION="${DEVENV_POETRY_VERSION:-$(version_from_tool_versions poetry "${POETRY_VERSION:-2.1.4}")}"
NODE_VERSION="${DEVENV_NODE_VERSION:-$(version_from_tool_versions nodejs "${NODE_VERSION:-22.18.0}")}"
TERRAFORM_VERSION="${DEVENV_TERRAFORM_VERSION:-$(version_from_tool_versions terraform "${TERRAFORM_VERSION:-1.12.1}")}"
PRECOMMIT_VERSION="${DEVENV_PRECOMMIT_VERSION:-$(version_from_tool_versions pre-commit "${PRECOMMIT_VERSION:-4.2.0}")}"
VALE_VERSION="${DEVENV_VALE_VERSION:-$(version_from_tool_versions vale "${VALE_VERSION:-3.11.2}")}"
ACT_VERSION="${DEVENV_ACT_VERSION:-$(version_from_tool_versions act "${ACT_VERSION:-0.2.77}")}"

RUN_PROJECT_SETUP="${DEVENV_RUN_PROJECT_SETUP:-${RUN_PROJECT_SETUP:-true}}"
RUN_VALIDATION="${DEVENV_RUN_VALIDATION:-${RUN_VALIDATION:-true}}"
RUN_UNIT_TESTS="${DEVENV_RUN_UNIT_TESTS:-${RUN_UNIT_TESTS:-true}}"
RUN_BUILD="${DEVENV_RUN_BUILD:-${RUN_BUILD:-false}}"
RUN_INTEGRATION_TESTS="${DEVENV_RUN_INTEGRATION_TESTS:-${RUN_INTEGRATION_TESTS:-false}}"

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

report_section "Base system"
check_ubuntu_release
verify_sudo_access
ensure_core_apt_packages
verify_core_commands
verify_gnu_toolchain

report_section "Docker"
ensure_docker_engine

report_section "asdf and toolchain"
ensure_asdf
ensure_asdf_tool python "$PYTHON_VERSION" python
ensure_asdf_tool poetry "$POETRY_VERSION" poetry
ensure_asdf_tool nodejs "$NODE_VERSION" node
ensure_asdf_tool terraform "$TERRAFORM_VERSION" terraform
ensure_asdf_tool pre-commit "$PRECOMMIT_VERSION" pre-commit
ensure_asdf_tool vale "$VALE_VERSION" vale
ensure_asdf_tool act "$ACT_VERSION" act

report_section "Project setup"
ensure_project_files
run_project_setup

report_section "Validation"
run_validation

if [[ "$REPORT_FAILURES" -eq 0 ]]; then
  report_finalize "success"
else
  report_finalize "failure"
  exit 1
fi