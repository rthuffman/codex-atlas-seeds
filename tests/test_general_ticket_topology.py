"""Sentinel coverage for promoted historical general-ticket House topology.

Phase AT (athena-codex ``usg-delegation-vacancy-fix-checklist``): early general-ticket
states (CT/NH/NJ/RI/DE/GA/VT) elected their whole delegation statewide at-large, so the
topology pack must yield ``at_large_count`` seats (codes A, B, C, ...) rather than the
default numbered single-member districts. This guards the CT-2/8th-Congress regression
where the term index produced only ``8|CT|A`` for a seven-member at-large delegation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[1] / "packs" / "us_house_district_topology" / "topology.json"


def _load_intervals() -> list[dict]:
    if not PACK.is_file():
        pytest.skip("topology.json not present")
    data = json.loads(PACK.read_text(encoding="utf-8"))
    return [r for r in data.get("intervals", []) if isinstance(r, dict)]


def _interval_for(intervals: list[dict], postal: str, congress: int) -> dict | None:
    for row in intervals:
        if str(row.get("postal")).upper() != postal:
            continue
        first = int(row["first_congress"])
        last = int(row.get("last_congress") or first)
        if first <= congress <= last:
            return row
    return None


# (postal, congress, expected at-large seat count) for promoted general-ticket cells.
# Counts follow corrected (historically-accurate) apportionment: the constitutional
# apportionment governs the 1st-2nd Congresses, the 1790 census the 3rd onward, etc.
GENERAL_TICKET_CASES = [
    ("CT", 1, 5),
    ("CT", 2, 5),   # constitutional apportionment (5 seats) through the 2nd Congress
    ("CT", 8, 7),   # Wright-Patman-class regression sentinel (CT-2/8th)
    ("CT", 17, 7),  # 1810 census (7 seats) governs through the 17th Congress
    ("CT", 24, 6),
    ("NH", 8, 5),
    ("NJ", 8, 6),
    ("NJ", 2, 4),   # constitutional apportionment (4 seats) for the 2nd Congress
    ("RI", 8, 2),
    ("DE", 14, 2),
    ("GA", 8, 4),
    ("GA", 22, 7),  # 1820 census (7 seats) governs the 22nd Congress
    ("VT", 14, 6),
]


@pytest.mark.parametrize("postal,congress,expected_al", GENERAL_TICKET_CASES)
def test_general_ticket_interval_counts(postal: str, congress: int, expected_al: int) -> None:
    intervals = _load_intervals()
    row = _interval_for(intervals, postal, congress)
    assert row is not None, f"missing general-ticket interval for {postal} congress {congress}"
    assert row.get("topology_kind") == "statewide_general_ticket"
    assert int(row.get("statewide_at_large_count") or 0) == expected_al
    assert int(row.get("numbered_single_member_count") or 0) == 0
    assert str(row.get("review_status")) == "reviewed"
    assert str(row.get("source_url") or "").startswith("http")


def test_new_jersey_district_and_plural_gaps_excluded() -> None:
    """NJ used single-member districts (6th); 13th is plural districts (Phase 1d operator review)."""
    intervals = _load_intervals()
    assert _interval_for(intervals, "NJ", 6) is None  # default single-member
    row13 = _interval_for(intervals, "NJ", 13)
    assert row13 is not None
    assert row13.get("topology_kind") == "plural_districts"
    assert int(row13.get("numbered_single_member_count") or 0) == 3


def test_ct8_crosswalk_pins_seven_seats() -> None:
    if not PACK.is_file():
        pytest.skip("topology.json not present")
    data = json.loads(PACK.read_text(encoding="utf-8"))
    crosswalks = data.get("crosswalks") or []
    ct8 = [c for c in crosswalks if str(c.get("postal")).upper() == "CT" and int(c.get("congress") or 0) == 8]
    assert ct8, "CT 8th-Congress crosswalk missing"
    mapping = ct8[0]["bioguide_to_seat_code"]
    assert sorted(mapping.values()) == ["A", "B", "C", "D", "E", "F", "G"]


def _topology_helpers():
    root = athena = Path(__file__).resolve().parents[2] / "athena-codex" / "artemis" / "src"
    if not root.is_dir():
        pytest.skip("athena-codex artemis not available")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from artemis.usg_house_district_topology import list_seat_codes, topology_for
    except Exception:  # pragma: no cover - environment guard
        pytest.skip("artemis topology module not importable")
    return topology_for, list_seat_codes


@pytest.mark.parametrize(
    "postal,congress,expected_codes",
    [
        ("CT", 8, ["A", "B", "C", "D", "E", "F", "G"]),
        ("CT", 2, ["A", "B", "C", "D", "E"]),
        ("CT", 17, ["A", "B", "C", "D", "E", "F", "G"]),
        ("NJ", 8, ["A", "B", "C", "D", "E", "F"]),
        ("RI", 8, ["A", "B"]),
        ("DE", 14, ["A", "B"]),
        ("GA", 8, ["A", "B", "C", "D"]),
        ("VT", 14, ["A", "B", "C", "D", "E", "F"]),
    ],
)
def test_general_ticket_seat_codes_resolve_at_large(postal, congress, expected_codes) -> None:
    topology_for, list_seat_codes = _topology_helpers()
    intervals = _load_intervals()
    topo = topology_for(congress, postal, intervals=intervals)
    codes = list_seat_codes(topo["numbered_count"], topo["at_large_count"], topo.get("plural_districts"))
    assert codes == expected_codes


def test_modern_single_member_unaffected() -> None:
    """Promotions must not turn a modern numbered-district state into at-large."""
    topology_for, list_seat_codes = _topology_helpers()
    intervals = _load_intervals()
    topo = topology_for(118, "CA", intervals=intervals)
    codes = list_seat_codes(topo["numbered_count"], topo["at_large_count"], topo.get("plural_districts"))
    assert codes[:3] == ["1", "2", "3"]
    assert topo["at_large_count"] == 0
