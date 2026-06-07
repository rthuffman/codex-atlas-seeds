"""Regenerate us_house_legislators_term_index pack slice via athena-codex generator."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from codex_seeds_ci.repo import find_repo_root


def _athena_root(seeds_root: Path) -> Path:
    import os

    raw = (os.environ.get("ATHENA_CODEX_ROOT") or os.environ.get("CODEX_ATHENA_ROOT") or "").strip()
    if raw:
        return Path(raw).resolve()
    sibling = seeds_root.parent / "athena-codex"
    if sibling.is_dir():
        return sibling.resolve()
    raise FileNotFoundError("athena-codex not found; set ATHENA_CODEX_ROOT")


def _venv_python(athena_root: Path) -> Path:
    if sys.platform == "win32":
        return athena_root / ".venv" / "Scripts" / "python.exe"
    return athena_root / ".venv" / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Fetch upstream legislators JSON first")
    args = parser.parse_args()
    seeds_root = find_repo_root()
    athena = _athena_root(seeds_root)
    py = _venv_python(athena)
    if not py.is_file():
        print(f"missing venv python: {py}", file=sys.stderr)
        return 1
    out = seeds_root / "packs" / "us_house_legislators_term_index" / "term_index.json"
    cmd = [
        str(py),
        str(athena / "base-data" / "tools" / "generate_house_legislators_term_index.py"),
        "--out",
        str(out),
        "--sources-dir",
        str(seeds_root / "sources" / "unitedstates" / "congress-legislators"),
        "--bounds",
        str(athena / "athena" / "docs" / "fixtures" / "usg-structure" / "us_congress_session_bounds.json"),
        "--fixture-out",
        str(athena / "athena" / "docs" / "fixtures" / "usg-structure" / "us_house_legislators_term_index.json"),
    ]
    if args.download:
        cmd.append("--download")
    return subprocess.run(cmd, cwd=athena).returncode


if __name__ == "__main__":
    raise SystemExit(main())
