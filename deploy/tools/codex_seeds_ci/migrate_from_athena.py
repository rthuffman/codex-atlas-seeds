"""Copy USG skeleton fixtures from athena-codex into pack directories."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from codex_seeds_ci.athena_venv import athena_codex_root
from codex_seeds_ci.repo import find_repo_root

# (fixture filename under athena/docs/fixtures/usg-structure, pack_id, pack payload filename)
USG_FIXTURE_MAPPINGS: tuple[tuple[str, str, str], ...] = (
    ("us_administration_skeleton_catalog.json", "usg_administration_skeleton", "catalog.json"),
    ("us_statutory_cabinet_departments_timeline.json", "usg_statutory_cabinet_timeline", "timeline.json"),
    ("us_house_apportionment_vintages.json", "usg_house_apportionment_vintages", "vintages.json"),
    ("us_congress_session_bounds.json", "usg_congress_session_bounds", "bounds.json"),
    ("us_congress_state_seating.json", "usg_congress_state_seating", "seating.json"),
    ("us_house_non_voting_delegate_seats.json", "usg_house_non_voting_delegate_seats", "delegates.json"),
)


def sync_usg_packs(*, athena_root: Path | None = None, repo_root: Path | None = None) -> list[Path]:
    athena = athena_root or athena_codex_root()
    root = repo_root or find_repo_root()
    fixture_dir = athena / "athena" / "docs" / "fixtures" / "usg-structure"
    written: list[Path] = []
    for fixture_name, pack_id, payload_name in USG_FIXTURE_MAPPINGS:
        src = fixture_dir / fixture_name
        dst = root / "packs" / pack_id / payload_name
        if not src.is_file():
            raise FileNotFoundError(f"missing athena fixture: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written.append(dst)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync pack JSON from athena-codex fixtures.")
    parser.add_argument(
        "--regenerate-catalog",
        action="store_true",
        help="Run athena base-data/tools/generate_administration_catalog.py first",
    )
    args = parser.parse_args()
    athena = athena_codex_root()
    if args.regenerate_catalog:
        import subprocess

        script = athena / "base-data" / "tools" / "generate_administration_catalog.py"
        from codex_seeds_ci.athena_venv import venv_python

        py = venv_python(athena)
        subprocess.run([str(py), str(script)], cwd=athena, check=True)
    paths = sync_usg_packs(athena_root=athena)
    for p in paths:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
