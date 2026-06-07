"""Validator coverage for us_house_legislators_term_index pack."""

from __future__ import annotations

from pathlib import Path

from codex_seeds_ci.manifest import validate_house_legislators_term_index


def test_validate_house_legislators_term_index_pack_file() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "packs" / "us_house_legislators_term_index" / "term_index.json"
    if not path.is_file():
        return
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_house_legislators_term_index(data, path="term_index.json")
    assert errors == []
