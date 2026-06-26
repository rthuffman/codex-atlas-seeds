"""Regenerate us_person_nickname_lookup pack from carltonnorthern upstream."""

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
    parser.add_argument("--download", action="store_true", help="Fetch upstream names.csv from GitHub")
    args = parser.parse_args()
    seeds_root = find_repo_root()
    athena = _athena_root(seeds_root)
    py = _venv_python(athena)
    if not py.is_file():
        print(f"missing venv python: {py}", file=sys.stderr)
        return 1
    cmd = [
        str(py),
        str(athena / "base-data" / "tools" / "sync_carltonnorthern_nickname_lookup.py"),
        "--seeds-pack-dir",
        str(seeds_root / "packs" / "us_person_nickname_lookup"),
        "--seeds-sources-dir",
        str(seeds_root / "sources" / "carltonnorthern" / "nickname-and-diminutive-names-lookup"),
        "--athena-sources-dir",
        str(athena / "base-data" / "sources" / "carltonnorthern" / "nickname-and-diminutive-names-lookup"),
    ]
    if args.download:
        cmd.append("--download")
    return subprocess.run(cmd, cwd=athena).returncode


if __name__ == "__main__":
    raise SystemExit(main())
