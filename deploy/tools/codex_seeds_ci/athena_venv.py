"""Resolve athena-codex repo and its .venv interpreter (shared tooling)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def athena_codex_root(*, start: Path | None = None) -> Path:
    raw = (os.environ.get("ATHENA_CODEX_ROOT") or os.environ.get("CODEX_ATHENA_ROOT") or "").strip()
    if raw:
        return Path(raw).resolve()
    if start is not None:
        for parent in [start, *start.parents]:
            sibling = parent.parent / "athena-codex"
            if (sibling / "scripts" / "bootstrap_athena_codex_venv.py").is_file():
                return sibling.resolve()
    sibling = Path.cwd().resolve().parent / "athena-codex"
    if (sibling / "scripts" / "bootstrap_athena_codex_venv.py").is_file():
        return sibling.resolve()
    raise FileNotFoundError(
        "athena-codex not found. Clone beside codex-atlas-seeds or set ATHENA_CODEX_ROOT."
    )


def venv_python(athena_root: Path | None = None) -> Path:
    root = athena_root or athena_codex_root()
    if sys.platform == "win32":
        exe = root / ".venv" / "Scripts" / "python.exe"
    else:
        exe = root / ".venv" / "bin" / "python"
    if not exe.is_file():
        raise FileNotFoundError(
            f"Missing {exe}. From athena-codex run: python scripts/bootstrap_athena_codex_venv.py"
        )
    return exe


def ensure_athena_venv(*, athena_root: Path | None = None) -> Path:
    root = athena_root or athena_codex_root()
    py = venv_python(root)
    if py.is_file():
        return py
    bootstrap = root / "scripts" / "bootstrap_athena_codex_venv.py"
    subprocess.run([sys.executable, str(bootstrap)], cwd=root, check=True)
    return venv_python(root)
