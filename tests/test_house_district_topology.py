"""Validator coverage for us_house_district_topology schema v2."""

from __future__ import annotations

from pathlib import Path

from codex_seeds_ci.manifest import validate_house_district_topology


def _valid_payload() -> dict:
    return {
        "format_version": 2,
        "source": {"generator": "test", "notes": "reviewed fixture"},
        "intervals": [
            {
                "postal": "PA",
                "first_congress": 13,
                "last_congress": 13,
                "topology_kind": "plural_districts",
                "numbered_single_member_count": 21,
                "statewide_at_large_count": 0,
                "plural_districts": [{"district": "1", "seat_count": 2}],
                "source_authority": "martis",
                "source_note": "test row",
                "confidence": "high",
                "review_status": "reviewed",
            }
        ],
        "crosswalks": [
            {
                "postal": "PA",
                "congress": 13,
                "district": 1,
                "bioguide_to_seat_code": {"A000001": "1-A", "B000002": "1-B"},
            }
        ],
    }


def test_validate_house_district_topology_pack_file() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "packs" / "us_house_district_topology" / "topology.json"
    if not path.is_file():
        return
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_house_district_topology(data, path="topology.json")
    assert errors == []


def test_validate_house_district_topology_accepts_v2_plural_row() -> None:
    assert validate_house_district_topology(_valid_payload(), path="topology.json") == []


def test_validate_house_district_topology_rejects_v1() -> None:
    payload = _valid_payload()
    payload["format_version"] = 1
    errors = validate_house_district_topology(payload, path="topology.json")
    assert any("format_version must be 2" in e for e in errors)


def test_validate_house_district_topology_rejects_overlaps() -> None:
    payload = _valid_payload()
    payload["intervals"].append(dict(payload["intervals"][0]))
    errors = validate_house_district_topology(payload, path="topology.json")
    assert any("overlaps" in e for e in errors)


def test_validate_house_district_topology_rejects_invalid_plural_crosswalk_code() -> None:
    payload = _valid_payload()
    payload["crosswalks"][0]["bioguide_to_seat_code"]["A000001"] = "1-"
    errors = validate_house_district_topology(payload, path="topology.json")
    assert any("invalid seat_code" in e for e in errors)
