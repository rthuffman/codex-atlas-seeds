"""Copy USG skeleton fixtures from athena-codex into pack directories."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import yaml

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


def _required_catalog_years(repo_root: Path) -> list[int]:
    policy_path = repo_root / "parity_policy.yaml"
    if not policy_path.is_file():
        return []
    raw = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    years = raw.get("required_catalog_inauguration_years", [])
    out: list[int] = []
    for y in years:
        try:
            out.append(int(y))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


def verify_synced_invariants(*, repo_root: Path | None = None) -> None:
    root = repo_root or find_repo_root()
    catalog_path = root / "packs" / "usg_administration_skeleton" / "catalog.json"
    if not catalog_path.is_file():
        raise FileNotFoundError(f"missing synced catalog: {catalog_path}")
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("rows") or payload.get("administrations") or []
    else:
        rows = []
    years = sorted({int(r.get("inauguration_year")) for r in rows if r.get("inauguration_year") is not None})
    if not years:
        raise RuntimeError("administration catalog has no inauguration_year rows")
    if years[0] > 1789:
        raise RuntimeError(f"administration catalog starts at {years[0]}, expected <= 1789")
    if years[-1] < 2021:
        raise RuntimeError(f"administration catalog ends at {years[-1]}, expected >= 2021")
    required = _required_catalog_years(root)
    missing = [y for y in required if y not in years]
    if missing:
        raise RuntimeError(f"administration catalog missing required inauguration years: {missing}")


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
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Validate post-sync invariants (coverage horizon + required inauguration years)",
    )
    parser.add_argument(
        "--export-prospectus-packs",
        action="store_true",
        help="Run athena export_atlas_prospectus_packs.py into this repo's packs/",
    )
    args = parser.parse_args()
    athena = athena_codex_root()
    if args.export_prospectus_packs:
        from codex_seeds_ci.export_prospectus_packs import export_prospectus_packs

        export_prospectus_packs(athena_root=athena, seeds_root=find_repo_root())
    if args.regenerate_catalog:
        import subprocess

        script = athena / "base-data" / "tools" / "generate_administration_catalog.py"
        from codex_seeds_ci.athena_venv import venv_python

        py = venv_python(athena)
        subprocess.run([str(py), str(script)], cwd=athena, check=True)
    paths = sync_usg_packs(athena_root=athena)
    if args.verify:
        verify_synced_invariants()
    for p in paths:
        print(f"Wrote {p}")
    if args.verify:
        print("Verified synced invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
