#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any
from pathlib import Path


PLATFORM_SCRIPTS = {
    "windows-wsl": "devenv/platforms/windows/bootstrap.ps1",
    "macos": "devenv/platforms/macos/bootstrap.sh",
    "linux-native": "devenv/platforms/linux/bootstrap.sh",
}


def detect_default_platform() -> str:
    if os.name == "nt":
        return "windows-wsl"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux-native"
    raise RuntimeError(f"Unsupported host platform: {sys.platform}")


def ensure_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required command not found: {name}")


def get_shell_command_for_windows() -> list[str]:
    pwsh = shutil.which("pwsh")
    if pwsh:
        return [pwsh]

    powershell = shutil.which("powershell")
    if powershell:
        return [powershell]

    raise RuntimeError("PowerShell is required but was not found on PATH.")


def ensure_yaml_module() -> Any:
    try:
        import yaml  # type: ignore
        return yaml
    except ModuleNotFoundError:
        install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "PyYAML"],
            check=False,
            text=True,
            capture_output=True,
        )
        if install.returncode != 0:
            raise RuntimeError(
                "Failed to install PyYAML in active environment. "
                f"Command: {sys.executable} -m pip install PyYAML\n"
                f"stdout: {install.stdout.strip()}\n"
                f"stderr: {install.stderr.strip()}"
            )

        try:
            import yaml  # type: ignore
            return yaml
        except ModuleNotFoundError as exc:
            raise RuntimeError("PyYAML installation reported success but module import still failed") from exc


def load_bootstrap_config(config_path: Path) -> dict[str, Any]:
    yaml = ensure_yaml_module()

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)

    if not isinstance(loaded, dict):
        raise RuntimeError(f"Invalid YAML config structure in {config_path}: expected a mapping at root")

    return loaded


def run_platform_bootstrap(platform: str, repo_root: Path) -> int:
    rel_script = PLATFORM_SCRIPTS.get(platform)
    if not rel_script:
        supported = ", ".join(sorted(PLATFORM_SCRIPTS))
        raise RuntimeError(f"Unsupported platform key '{platform}'. Supported: {supported}")

    script_path = repo_root / rel_script
    if not script_path.exists():
        raise RuntimeError(f"Bootstrap script not found for platform '{platform}': {script_path}")

    env = os.environ.copy()
    if "DEVENV_REPO_ROOT" not in env:
        env["DEVENV_REPO_ROOT"] = str(repo_root)

    print(f"Platform: {platform}")
    print(f"Bootstrap: {script_path}")
    print()

    if platform == "windows-wsl":
        shell = get_shell_command_for_windows()
        cmd = shell + ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        completed = subprocess.run(cmd, env=env, check=False)
        return completed.returncode

    if platform in {"macos", "linux-native"}:
        ensure_command("bash")
        completed = subprocess.run(["bash", str(script_path)], env=env, check=False)
        return completed.returncode

    raise RuntimeError(f"No execution strategy defined for platform '{platform}'")


def main() -> int:
    parser = argparse.ArgumentParser(description="Developer environment bootstrap launcher")
    parser.add_argument(
        "--config-path",
        default="./config/devenv.bootstrap.yaml",
        help="Path to bootstrap YAML config, relative to devenv directory by default",
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Override platform key (windows-wsl, macos, linux-native)",
    )
    args = parser.parse_args()

    devenv_root = Path(__file__).resolve().parent
    repo_root = devenv_root.parent
    config_path = (devenv_root / args.config_path).resolve()

    if not config_path.exists():
        raise RuntimeError(f"Config file not found: {config_path}")

    config = load_bootstrap_config(config_path)
    platform_key = args.platform or detect_default_platform()

    platforms = config.get("platforms")
    if not isinstance(platforms, dict) or platform_key not in platforms:
        supported = ", ".join(sorted(PLATFORM_SCRIPTS))
        raise RuntimeError(f"Platform '{platform_key}' not defined in config. Supported: {supported}")

    platform_cfg = platforms.get(platform_key)
    if not isinstance(platform_cfg, dict) or not platform_cfg.get("enabled", False):
        raise RuntimeError(f"Platform '{platform_key}' is disabled in config")

    ensure_command("git")

    # Always pass the current interpreter so downstream scripts can reuse the same venv Python.
    os.environ["DEVENV_PYTHON_EXE"] = sys.executable
    os.environ["DEVENV_CONFIG_PATH"] = str(config_path)
    os.environ["DEVENV_PLATFORM"] = platform_key
    os.environ["DEVENV_CONFIG_JSON"] = json.dumps(config)
    os.environ["DEVENV_REPO_ROOT"] = str(repo_root)

    print(f"Using config: {config_path}")
    return run_platform_bootstrap(platform_key, repo_root)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
