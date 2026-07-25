"""Suite pin sync: expected_slice_count counts JSON slices only."""

from __future__ import annotations

from pathlib import Path

import yaml

from codex_seeds_ci.repo import find_repo_root
from codex_seeds_ci.suite_pin_sync import _seeds_slice_counts


def test_seeds_slice_counts_skips_non_json_files(tmp_path: Path) -> None:
    """One all-JSON pack + one CSV-only pack → pack_count 2, expected_slice_count 1."""
    (tmp_path / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "bundle_format_version": 1,
                "bundle_version": "0.0.0-test",
                "requires_atlas_schema_version": "1.2.0",
                "packs": [
                    {
                        "pack_id": "json_only_pack",
                        "version": "0.1.0",
                        "files": ["catalog.json"],
                    },
                    {
                        "pack_id": "csv_asset_pack",
                        "version": "0.1.0",
                        "files": ["names.csv"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    pack_count, expected_slice_count = _seeds_slice_counts(tmp_path)
    assert pack_count == 2
    assert expected_slice_count == 1


def test_seeds_slice_counts_real_manifest_excludes_nickname_csv() -> None:
    """Current repo manifest: 18 packs, 17 JSON slices (nickname pack is CSV-only)."""
    root = find_repo_root()
    pack_count, expected_slice_count = _seeds_slice_counts(root)
    assert pack_count == 18
    assert expected_slice_count == 17
