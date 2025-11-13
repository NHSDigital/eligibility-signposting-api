from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Sequence


class MarkdownLintError(ValueError):
    pass


def _pymarkdown_cmd() -> list[str]:
    """
    Resolve the pymarkdown executable. Override with env var PYMARKDOWN_CMD if needed.
    """
    cmd = os.environ.get("PYMARKDOWN_CMD", "pymarkdown")
    return cmd.split() if isinstance(cmd, str) else list(cmd)


def lint_markdown_string_cli(value: str, field_name: str, extra_args: Sequence[str] | None = None) -> None:
    """
    Lint a Markdown string using the PyMarkdown **CLI** (no API usage).
    Raises MarkdownLintError if any style issues are detected.

    :param value: the text to lint
    :param field_name: used to label errors
    :param extra_args: extra CLI args, e.g. ["-d", "MD013"] to disable a rule
    """
    if value is None or not str(value).strip():
        return

    args = _pymarkdown_cmd()
    # -l = lint, we'll pass a temp file path next
    cmd = [*args, "-l"]
    if extra_args:
        cmd.extend(extra_args)

    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write(value)
        tf.flush()
        path = tf.name

    try:
        # PyMarkdown returns non-zero exit when violations exist.
        # stdout has human-readable findings, stderr may include rule help.
        proc = subprocess.run(
            [*cmd, path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    if proc.returncode != 0:
        # Compact error message. You can keep stdout only, or merge with stderr.
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        details = out if out else err
        details = details.replace(path, field_name)  # friendlier label
        raise MarkdownLintError(f"{field_name}: Markdown style errors:\n{details}")
