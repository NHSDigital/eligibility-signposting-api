#!/usr/bin/env bash

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

is_true() {
  case "${1:-false}" in
    1|true|TRUE|yes|YES|y|Y|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

version_from_tool_versions() {
  local tool="$1"
  local fallback="$2"
  local file_path="${REPO_ROOT}/.tool-versions"

  if [[ -f "$file_path" ]]; then
    local value
    value="$(awk -v tool="$tool" '$1 == tool { print $2; exit }' "$file_path")"
    if [[ -n "${value:-}" ]]; then
      printf '%s\n' "$value"
      return
    fi
  fi

  printf '%s\n' "$fallback"
}

init_sudo_password() {
  DEVENV_SUDO_PASSWORD=""
  if [[ -n "${DEVENV_SUDO_PASSWORD_B64:-}" ]]; then
    DEVENV_SUDO_PASSWORD="$(printf '%s' "$DEVENV_SUDO_PASSWORD_B64" | base64 -d)"
  fi
}

cleanup_secret() {
  unset DEVENV_SUDO_PASSWORD
  unset DEVENV_SUDO_PASSWORD_B64
}

sudo_run() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
    return
  fi

  if [[ -n "${DEVENV_SUDO_PASSWORD:-}" ]]; then
    printf '%s\n' "$DEVENV_SUDO_PASSWORD" | sudo -S -p '' "$@"
    return
  fi

  sudo "$@"
}

verify_sudo_access() {
  if sudo_run -v >/dev/null 2>&1; then
    report_ok "sudo access verified"
    return 0
  fi

  report_fail "sudo access unavailable for user '$USER'"
  return 1
}