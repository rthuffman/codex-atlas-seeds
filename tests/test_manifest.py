"""Pack and bundle manifest validation."""

from __future__ import annotations

from codex_seeds_ci.manifest import load_bundle_manifest, validate_repo
from codex_seeds_ci.repo import find_repo_root


def test_validate_repo_clean() -> None:
    errors = validate_repo(find_repo_root())
    assert errors == []


def test_bundle_has_six_usg_packs() -> None:
    manifest = load_bundle_manifest(find_repo_root())
    pack_ids = {p["pack_id"] for p in manifest["packs"]}
    assert len(manifest["packs"]) == 6
    assert pack_ids == {
        "usg_administration_skeleton",
        "usg_statutory_cabinet_timeline",
        "usg_house_apportionment_vintages",
        "usg_congress_session_bounds",
        "usg_congress_state_seating",
        "usg_house_non_voting_delegate_seats",
    }


def test_administration_catalog_covers_1789() -> None:
    import json
    from pathlib import Path

    path = find_repo_root() / "packs" / "usg_administration_skeleton" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["administrations"]
    assert len(rows) >= 50
    assert rows[0]["inauguration_year"] == 1789
