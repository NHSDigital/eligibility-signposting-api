from __future__ import annotations

import os
import sys
import shutil
import subprocess
import tempfile
import logging
from typing import Iterable, Sequence

log = logging.getLogger(__name__)


class MarkdownLintError(ValueError):
    """Raised when the PyMarkdown CLI reports style errors."""


def _resolve_cmd() -> list[str]:
    env_cmd = os.environ.get("PYMARKDOWN_CMD")
    if env_cmd:
        return env_cmd.split()

    for exe in ("pymarkdown", "pymarkdownlnt"):
        found = shutil.which(exe)
        if found:
            return [found]

    return [sys.executable, "-m", "pymarkdown"]


def _disable_args(disable_rules: Iterable[str] | None) -> list[str]:
    """
    Convert a list/tuple of rule IDs into a single '-d' arg with comma-separated rules.
    Returns [] if no rules to disable.
    """
    if not disable_rules:
        return []
    rules = [r.strip() for r in disable_rules if r and str(r).strip()]
    return ["-d", ",".join(rules)] if rules else []


def lint_markdown_string_cli(
    value: str,
    field_name: str,
    extra_args: Sequence[str] | None = None,
    disable_rules: Iterable[str] | None = None,
) -> None:
    """
    Lint a string with the PyMarkdown CLI. Raises MarkdownLintError on failure.

    Args:
        value: The markdown text to lint.
        field_name: Used to label errors (replaces temp path in messages).
        extra_args: Optional extra CLI flags (placed BEFORE 'scan').
        disable_rules: Optional iterable of rule IDs to disable (e.g., ('MD041','MD047')).
    """
    if value is None or not str(value).strip():
        return

    cmd = _resolve_cmd()
    flags = []
    flags += _disable_args(disable_rules)
    if extra_args:
        flags += list(extra_args)

    base_cmd = [*cmd, *flags, "scan"]

    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write(value)
        tf.flush()
        tmp_path = tf.name

    full_cmd = [*base_cmd, tmp_path]
    log.debug("[PyMarkdown] cmd=%s", " ".join(full_cmd))

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
            "or set PYMARKDOWN_CMD to the executable path."
        ) from e
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if proc.returncode != 0:
        details = (proc.stdout or proc.stderr or "").replace(tmp_path, field_name).strip()
        raise MarkdownLintError(f"{field_name}: Markdown style errors:\n{details}")
