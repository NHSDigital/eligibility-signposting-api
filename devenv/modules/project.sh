#!/usr/bin/env bash

_run_make_target() {
  local target="$1"
  local success_message="$2"
  local failure_mode="${3:-fail}"

  if make "$target"; then
    report_ok "$success_message"
    return
  fi

  if [[ "$failure_mode" == "warn" ]]; then
    report_warn "make $target failed"
  else
    report_fail "make $target failed"
  fi
}

ensure_project_files() {
  local file_name
  local required_files=(
    .tool-versions
    Makefile
    pyproject.toml
  )

  for file_name in "${required_files[@]}"; do
    if [[ -e "$REPO_ROOT/$file_name" ]]; then
      report_ok "$file_name found"
    else
      report_fail "$file_name missing"
    fi
  done

  if [[ -d "$REPO_ROOT/.git" ]]; then
    report_ok "Git repository found"
  else
    report_fail "Git repository missing"
  fi
}

run_project_setup() {
  if ! is_true "$RUN_PROJECT_SETUP"; then
    report_warn "Project setup disabled by configuration"
    return
  fi

  if [[ "$MODE" != "create" ]]; then
    if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
      report_ok "Project virtual environment exists"
    else
      report_warn "Project virtual environment missing"
    fi

    if [[ -f "$REPO_ROOT/.git/hooks/pre-commit" ]]; then
      report_ok "pre-commit hook installed"
    else
      report_warn "pre-commit hook missing"
    fi
    return
  fi

  _run_make_target "config" "make config completed"
  _run_make_target "install" "make install completed"
}

run_validation() {
  if ! is_true "$RUN_VALIDATION"; then
    report_warn "Validation disabled by configuration"
    return
  fi

  _run_make_target "onboarding-check" "make onboarding-check passed"

  if is_true "$RUN_UNIT_TESTS"; then
    _run_make_target "test-unit" "make test-unit passed"
  else
    report_info "Unit tests skipped by configuration"
  fi

  if is_true "$RUN_BUILD"; then
    _run_make_target "build" "make build passed"
  else
    report_info "Build skipped by configuration"
  fi

  if is_true "$RUN_INTEGRATION_TESTS"; then
    _run_make_target "test-integration" "make test-integration passed"
  else
    report_info "Integration tests skipped by configuration"
  fi
}