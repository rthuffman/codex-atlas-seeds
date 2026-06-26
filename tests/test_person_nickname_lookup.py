"""Validator coverage for us_person_nickname_lookup pack."""

from __future__ import annotations

import csv
from pathlib import Path


def test_nickname_lookup_csv_has_robert_bob_edge() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "packs" / "us_person_nickname_lookup" / "names.csv"
    if not path.is_file():
        return
    edges: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            left = str(row.get("name1") or "").strip().casefold()
            rel = str(row.get("relationship") or "").strip().casefold()
            right = str(row.get("name2") or "").strip().casefold()
            if rel == "has_nickname":
                edges.add((left, right))
    assert ("robert", "bob") in edges
