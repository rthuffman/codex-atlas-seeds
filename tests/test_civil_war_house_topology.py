"""Sentinel coverage for Civil War House structural topology fixes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_PACK = ROOT / "packs" / "us_house_district_topology" / "topology.json"
APPORTIONMENT_PACK = ROOT / "packs" / "usg_house_apportionment_vintages" / "vintages.json"


def _load_json(path: Path) -> dict:
    if not path.is_file():
        pytest.skip(f"{path.name} not present")
    return json.loads(path.read_text(encoding="utf-8"))


def _topology_helpers():
    artemis_src = ROOT.parent / "athena-codex" / "artemis" / "src"
    if not artemis_src.is_dir():
        pytest.skip("athena-codex artemis not available")
    if str(artemis_src) not in sys.path:
        sys.path.insert(0, str(artemis_src))
    try:
        from artemis.usg_house_district_topology import list_seat_codes, topology_for
    except Exception:  # pragma: no cover - environment guard
        pytest.skip("artemis topology module not importable")
    return topology_for, list_seat_codes


def _apportioned_count(congress: int, postal: str) -> int:
    vintages = _load_json(APPORTIONMENT_PACK)["vintages"]
    parsed = sorted(
        (
            int(row["first_congress"]),
            int(row["last_congress"]),
            row,
        )
        for row in vintages
    )
    for first, last, row in parsed:
        if first <= congress <= last:
            return int(row["seats_by_postal"].get(postal, 0))
    raise AssertionError(f"no apportionment vintage for congress {congress}")


@pytest.mark.parametrize(
    "congress,postal,expected_count",
    [
        (36, "KS", 1),
        (36, "MN", 2),
        (36, "OR", 1),
        (38, "NV", 1),
        (38, "WV", 3),
        (38, "NE", 0),
        (39, "NE", 1),
    ],
)
def test_civil_war_admission_and_split_apportionment(congress: int, postal: str, expected_count: int) -> None:
    assert _apportioned_count(congress, postal) == expected_count


@pytest.mark.parametrize(
    "congress,postal,expected_codes",
    [
        (36, "KS", ["A"]),
        (37, "KS", ["A"]),
        (36, "MN", ["A", "B"]),
        (37, "MN", ["A", "B"]),
        (36, "OR", ["A"]),
        (37, "OR", ["A"]),
        (37, "MO", ["1", "2", "3", "4", "5", "6", "7"]),
        (38, "IL", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "A"]),
        (38, "NV", ["A"]),
        (38, "WV", ["1", "2", "3"]),
        (39, "NE", ["A"]),
        (39, "VA", ["1", "2", "3", "4", "5", "6", "7", "8"]),
        (39, "WV", ["1", "2", "3"]),
        (40, "KY", ["1", "2", "3", "4", "5", "6", "7", "8", "9"]),
        (41, "VA", ["1", "2", "3", "4", "5", "6", "7", "8"]),
    ],
)
def test_civil_war_gold_topology_seat_codes(congress: int, postal: str, expected_codes: list[str]) -> None:
    topology_for, list_seat_codes = _topology_helpers()
    intervals = _load_json(TOPOLOGY_PACK)["intervals"]
    topo = topology_for(
        congress,
        postal,
        intervals=intervals,
        apportioned_count=_apportioned_count(congress, postal),
    )
    assert list_seat_codes(
        topo["numbered_count"],
        topo["at_large_count"],
        topo.get("plural_districts"),
    ) == expected_codes
