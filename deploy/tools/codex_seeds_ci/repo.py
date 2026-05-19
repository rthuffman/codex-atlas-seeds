"""Locate codex-atlas-seeds repository root."""

from __future__ import annotations

from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for _ in range(20):
        if (p / "packs").is_dir() and (p / "deploy" / "tools").is_dir() and (p / "manifest.yaml").is_file():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise FileNotFoundError(
        "Could not find codex-atlas-seeds root (expected packs/, manifest.yaml, deploy/tools). "
        "Run from inside the codex-atlas-seeds clone."
    )
