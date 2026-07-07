"""Pack and bundle manifest validation."""

from __future__ import annotations

from codex_seeds_ci.manifest import load_bundle_manifest, validate_repo
from codex_seeds_ci.repo import find_repo_root


def test_validate_repo_clean() -> None:
    errors = validate_repo(find_repo_root())
    assert errors == []


def test_bundle_has_seventeen_packs() -> None:
    manifest = load_bundle_manifest(find_repo_root())
    pack_ids = {p["pack_id"] for p in manifest["packs"]}
    assert len(manifest["packs"]) == 17
    assert pack_ids == {
        "usg_administration_skeleton",
        "usg_statutory_cabinet_timeline",
        "usg_house_apportionment_vintages",
        "usg_congress_session_bounds",
        "usg_congress_state_seating",
        "usg_house_non_voting_delegate_seats",
        "us_geo_bootstrap",
        "us_gold_current_structure",
        "us_gold_historical_structure",
        "us_house_district_topology",
        "us_house_legislators_term_index",
        "usg_congress_session_readiness",
        "us_person_nickname_lookup",
        "usg_federal_judiciary_orgs",
        "usg_executive_independent_orgs",
        "usg_structure_assigned_attachments",
        "usg_appointed_offices",
    }


def test_administration_catalog_covers_1789() -> None:
    import json
    from pathlib import Path

    path = find_repo_root() / "packs" / "usg_administration_skeleton" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["administrations"]
    assert len(rows) >= 50
    assert rows[0]["inauguration_year"] == 1789


def test_administration_catalog_includes_obama_second_inauguration() -> None:
    import json
    from pathlib import Path

    path = find_repo_root() / "packs" / "usg_administration_skeleton" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    years = {int(r["inauguration_year"]) for r in data["administrations"] if "inauguration_year" in r}
    assert 2013 in years


def test_projection_packs_do_not_pin_optional_taxonomy_fields() -> None:
    import json

    root = find_repo_root()
    payloads = [
        root / "packs" / "us_geo_bootstrap" / "bootstrap.json",
        root / "packs" / "us_gold_current_structure" / "envelope.json",
        root / "packs" / "us_gold_historical_structure" / "envelope.json",
    ]
    for path in payloads:
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("records") or []
        assert records
        assert not [
            (path.name, idx, sorted({"L1", "L2", "L3"} & set(record)))
            for idx, record in enumerate(records)
            if isinstance(record, dict) and {"L1", "L2", "L3"} & set(record)
        ]
