#!/usr/bin/env bash

_docker_systemd_active() {
  [[ "$(ps -p 1 -o comm= 2>/dev/null | tr -d ' ')" == "systemd" ]]
}

ensure_systemd_in_wsl_conf() {
  local current_content=""
  local desired_content

  if [[ -f /etc/wsl.conf ]]; then
    current_content="$(cat /etc/wsl.conf)"
  fi

  desired_content="$(python3 - <<'PY'
from pathlib import Path

path = Path("/etc/wsl.conf")
content = path.read_text() if path.exists() else ""
lines = content.splitlines()

out = []
in_boot = False
systemd_written = False

for line in lines:
    stripped = line.strip()
    if stripped == "[boot]":
        in_boot = True
        out.append(line)
        continue
    if in_boot and stripped.startswith("systemd="):
        out.append("systemd=true")
        systemd_written = True
        in_boot = False
        continue
    if stripped.startswith("[") and stripped.endswith("]") and in_boot and not systemd_written:
        out.append("systemd=true")
        systemd_written = True
        in_boot = False
    out.append(line)

if not systemd_written:
    if out and out[-1].strip():
        out.append("")
    out.append("[boot]")
    out.append("systemd=true")

print("\n".join(out).rstrip() + "\n")
PY
)"

  if [[ "$current_content" != "$desired_content" ]]; then
    printf '%s' "$desired_content" | sudo_run tee /etc/wsl.conf >/dev/null
    report_warn "Updated /etc/wsl.conf with systemd=true; run 'wsl --shutdown' after completion, then rerun if Docker daemon is unavailable"
  else
    report_ok "systemd=true already present in /etc/wsl.conf"
  fi
}

ensure_docker_engine() {
  if [[ "$DOCKER_STRATEGY" == "skip" ]]; then
    report_warn "Docker checks skipped by configuration"
    return
  fi

  if command_exists docker && docker compose version >/dev/null 2>&1; then
    report_ok "Docker CLI and Compose plugin available"
    if docker info >/dev/null 2>&1; then
      report_ok "Docker daemon reachable"
      if docker run --rm hello-world >/dev/null 2>&1; then
        report_ok "docker run hello-world succeeded"
      else
        report_warn "docker run hello-world failed"
      fi
    else
    return

    if [[ "$MODE" != "create" ]]; then
      report_warn "Docker installed but daemon is not reachable"
      return
    fi

    report_warn "Docker daemon not reachable; attempting remediation"
    ensure_systemd_in_wsl_conf
    sudo_run usermod -aG docker "$USER"

    if _docker_systemd_active; then
      sudo_run systemctl enable --now docker || true
    else
      report_warn "systemd is not active in this WSL session; Docker daemon may need a WSL restart"
    fi

    if docker info >/dev/null 2>&1; then
      report_ok "Docker daemon reachable after remediation"
      if docker run --rm hello-world >/dev/null 2>&1; then
        report_ok "docker run hello-world succeeded"
      else
        report_warn "docker run hello-world failed"
      fi
    else
      report_warn "Docker daemon is still not reachable; run 'wsl --shutdown' and rerun create"
    fi
    return

  if [[ "$DOCKER_STRATEGY" == "desktop" ]]; then
    report_warn "Docker Desktop selected; install and enable WSL integration manually if Docker is unavailable"
    return
  fi

  if [[ "$MODE" != "create" ]]; then
    report_fail "Docker is missing"
    return
  fi

  ensure_systemd_in_wsl_conf

  sudo_run install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo_run gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo_run chmod a+r /etc/apt/keyrings/docker.gpg

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo_run tee /etc/apt/sources.list.d/docker.list >/dev/null

  sudo_run apt update
  sudo_run apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo_run usermod -aG docker "$USER"

  if _docker_systemd_active; then
    sudo_run systemctl enable --now docker || true
  else
    report_warn "systemd is not active in this WSL session; Docker daemon may need a WSL restart"
  fi

  if command_exists docker; then
    report_ok "Docker packages installed"
  else
    report_fail "Docker install did not complete correctly"
    return
  fi

  if docker compose version >/dev/null 2>&1; then
    report_ok "Docker Compose plugin available"
  else
    report_warn "Docker Compose plugin is unavailable"
  fi

  if docker info >/dev/null 2>&1; then
    report_ok "Docker daemon reachable"
    if docker run --rm hello-world >/dev/null 2>&1; then
      report_ok "docker run hello-world succeeded"
    else
      report_warn "docker run hello-world failed"
    fi
  else
    report_warn "Docker daemon is not reachable yet; a full 'wsl --shutdown' and rerun may be required"
  fi
}
