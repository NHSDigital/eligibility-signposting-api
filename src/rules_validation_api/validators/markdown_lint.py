from __future__ import annotations
import os, sys, shutil, subprocess, tempfile, shlex, logging
from typing import Sequence

log = logging.getLogger(__name__)

class MarkdownLintError(ValueError):
    pass

def _resolve_pymarkdown_command() -> list[str]:
    """
    Priority:
      1) PYMARKDOWN_CMD env (e.g. '/path/venv/bin/pymarkdown')
      2) 'pymarkdown' on PATH
      3) 'pymarkdownlnt' on PATH
      4) python -m pymarkdown (same interpreter)
    """
    env_cmd = os.environ.get("PYMARKDOWN_CMD")
    if env_cmd:
        return env_cmd.split()

    for exe in ("pymarkdown", "pymarkdownlnt"):
        path = shutil.which(exe)
        if path:
            return [path]

    return [sys.executable, "-m", "pymarkdown"]

def _ensure_scan_subcommand(cmd: list[str]) -> list[str]:
    # If it's 'python -m pymarkdown', keep the trio intact and then add 'scan'
    if len(cmd) >= 3 and cmd[0].endswith("python") and cmd[1] == "-m" and cmd[2].startswith("pymarkdown"):
        base = cmd[:3]
        rest = cmd[3:]
        # If user already provided a subcommand, keep it; otherwise add 'scan'
        return base + (rest if rest else ["scan"])
    # Otherwise plain 'pymarkdown' or 'pymarkdownlnt'
    return cmd if (len(cmd) > 1 and cmd[1] in {"extensions","fix","plugins","scan","scan-stdin","version"}) else [*cmd, "scan"]

def _sanitize_extra_args(extra_args: Sequence[str] | None) -> list[str]:
    if not extra_args:
        return []
    allowed_prefixes = ("-e", "-d", "--enable-extensions", "--add-plugin", "--config",
                        "--set", "--strict-config", "--no-json5", "--stack-trace",
                        "--continue-on-error", "--log-level", "--log-file",
                        "--return-code-scheme")
    cleaned: list[str] = []
    i = 0
    while i < len(extra_args):
        tok = str(extra_args[i])
        if tok.startswith(allowed_prefixes):
            cleaned.append(tok)
            # naive: also append a following value if present and not another flag
            if i + 1 < len(extra_args) and not str(extra_args[i+1]).startswith("-"):
                cleaned.append(str(extra_args[i+1]))
                i += 2
                continue
        # else drop unexpected tokens (e.g., a stray field name)
        i += 1
    return cleaned

def lint_markdown_string_cli(value: str, field_name: str, extra_args: Sequence[str] | None = None) -> None:
    if value is None or not str(value).strip():
        return

    cmd = _resolve_pymarkdown_command()
    cmd = _ensure_scan_subcommand(cmd)
    args = _sanitize_extra_args(extra_args)

    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write(value)
        tf.flush()
        path = tf.name

    full_cmd = [*cmd, *args, path]
    log.debug("[PyMarkdown] cmd=%s", " ".join(shlex.quote(x) for x in full_cmd))

    try:
        proc = subprocess.run(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise MarkdownLintError(
            "PyMarkdown CLI not found. Install `pip install pymarkdownlnt`, "
            "or set PYMARKDOWN_CMD to the executable (e.g., '/path/to/venv/bin/pymarkdown')."
        ) from e
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    if proc.returncode != 0:
        # replace temp path with the field name for friendlier errors
        details = (proc.stdout or proc.stderr or "").replace(path, field_name).strip()
        raise MarkdownLintError(f"{field_name}: Markdown style errors:\n{details}")
