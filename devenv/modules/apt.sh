#!/usr/bin/env bash

APT_PACKAGES=(
  build-essential
  curl
  git
  wget
  unzip
  zip
  jq
  libssl-dev
  zlib1g-dev
  libbz2-dev
  libreadline-dev
  libsqlite3-dev
  libncursesw5-dev
  xz-utils
  tk-dev
  libxml2-dev
  libxmlsec1-dev
  libffi-dev
  liblzma-dev
  ca-certificates
  gnupg
  lsb-release
  software-properties-common
)

check_ubuntu_release() {
  if grep -q 'VERSION_ID="24.04"' /etc/os-release; then
    report_ok "Running on Ubuntu 24.04"
  else
    report_warn "Current distro is not Ubuntu 24.04"
  fi
}

ensure_core_apt_packages() {
  local missing=()
  local package

  if [[ "$MODE" == "create" ]]; then
    sudo_run apt update
    sudo_run apt upgrade -y
    report_ok "Refreshed apt package indexes and applied upgrades"
  fi

  for package in "${APT_PACKAGES[@]}"; do
    if ! dpkg -s "$package" >/dev/null 2>&1; then
      missing+=("$package")
    fi
  done

  if [[ ${#missing[@]} -eq 0 ]]; then
    report_ok "Core apt packages already installed"
    return
  fi

  if [[ "$MODE" != "create" ]]; then
    report_fail "Missing apt packages: ${missing[*]}"
    return
  fi

  sudo_run apt install -y "${missing[@]}"
  report_ok "Installed core apt packages"
}

verify_core_commands() {
  local commands=(gcc make git jq)
  local command_name

  for command_name in "${commands[@]}"; do
    if command_exists "$command_name"; then
      report_ok "$command_name command available"
    else
      report_fail "$command_name command missing"
    fi
  done
}

verify_gnu_toolchain() {
  if sed --version 2>/dev/null | head -1 | grep -qi 'gnu sed'; then
    report_ok "GNU sed available"
  else
    report_warn "GNU sed not detected"
  fi

  if grep --version 2>/dev/null | head -1 | grep -qi 'gnu grep'; then
    report_ok "GNU grep available"
  else
    report_warn "GNU grep not detected"
  fi
}
