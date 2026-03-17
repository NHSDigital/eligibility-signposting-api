#!/usr/bin/env bash

ensure_asdf() {
  local asdf_dir="$HOME/.asdf"
  local bashrc="$HOME/.bashrc"

  if [[ ! -d "$asdf_dir" ]]; then
    if [[ "$MODE" != "create" ]]; then
      report_fail "asdf missing"
      return 1
    fi

    if git clone https://github.com/asdf-vm/asdf.git "$asdf_dir" --branch "$ASDF_VERSION"; then
      report_ok "Installed asdf $ASDF_VERSION"
    else
      report_fail "Failed to install asdf $ASDF_VERSION"
      return 1
    fi
  else
    report_ok "asdf directory exists"
  fi

  if ! grep -Fq '. "$HOME/.asdf/asdf.sh"' "$bashrc" 2>/dev/null; then
    {
      echo
      echo '# asdf version manager'
      echo '. "$HOME/.asdf/asdf.sh"'
      echo '. "$HOME/.asdf/completions/asdf.bash"'
    } >> "$bashrc"
    report_ok "Updated ~/.bashrc for asdf"
  else
    report_ok "~/.bashrc already configured for asdf"
  fi

  # shellcheck source=/dev/null
  source "$HOME/.asdf/asdf.sh"

  if command_exists asdf; then
    report_ok "asdf command available"
  else
    report_fail "asdf command unavailable after setup"
    return 1
  fi
}

ensure_asdf_tool() {
  local plugin="$1"
  local version="$2"
  local binary="${3:-$1}"

  if ! command_exists asdf; then
    report_fail "asdf unavailable before checking $plugin"
    return
  fi

  if ! asdf plugin list 2>/dev/null | grep -Fxq "$plugin"; then
    if [[ "$MODE" != "create" ]]; then
      report_fail "asdf plugin missing: $plugin"
      return
    fi

    if asdf plugin add "$plugin"; then
      report_ok "Added asdf plugin: $plugin"
    else
      report_fail "Failed to add asdf plugin: $plugin"
      return
    fi
  else
    report_ok "asdf plugin present: $plugin"
  fi

  if ! asdf list "$plugin" 2>/dev/null | tr -d ' ' | grep -Fxq "$version"; then
    if [[ "$MODE" != "create" ]]; then
      report_fail "$plugin version missing: $version"
      return
    fi

    if asdf install "$plugin" "$version"; then
      report_ok "Installed $plugin $version"
    else
      report_fail "Failed to install $plugin $version"
      return
    fi
  else
    report_ok "$plugin $version already installed"
  fi

  if [[ "$MODE" == "create" ]]; then
    if asdf global "$plugin" "$version"; then
      report_ok "Set global $plugin version to $version"
    else
      report_warn "Failed to set global $plugin version to $version"
    fi

    asdf reshim "$plugin" "$version" >/dev/null 2>&1 || true
  fi

  if command_exists "$binary"; then
    report_ok "$binary command available"
  else
    report_warn "$binary command not available in current shell"
  fi
}