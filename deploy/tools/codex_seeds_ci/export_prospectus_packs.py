"""Export Prospectus projection packs from athena-codex generators."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from codex_seeds_ci.athena_venv import athena_codex_root, venv_python
from codex_seeds_ci.repo import find_repo_root


def export_prospectus_packs(*, athena_root: Path | None = None, seeds_root: Path | None = None) -> None:
    athena = athena_root or athena_codex_root()
    seeds = seeds_root or find_repo_root()
    script = athena / "base-data" / "tools" / "export_atlas_prospectus_packs.py"
    if not script.is_file():
        raise FileNotFoundError(f"missing export script: {script}")
    py = venv_python(athena)
    subprocess.run([str(py), str(script), "--seeds-root", str(seeds)], cwd=athena, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export geo/structure packs from athena-codex.")
    parser.add_argument(
        "--seeds-root",
        type=Path,
        default=None,
        help="codex-atlas-seeds root (default: this repo)",
    )
    args = parser.parse_args()
    export_prospectus_packs(seeds_root=args.seeds_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
