"""world_nations_bootstrap projection pack (ATH-474)."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from codex_seeds_ci.manifest import validate_world_nations_bootstrap
from codex_seeds_ci.repo import find_repo_root

PATH = "bootstrap.json"


@pytest.fixture(scope="module")
def payload() -> dict[str, Any]:
    p = find_repo_root() / "packs" / "world_nations_bootstrap" / "bootstrap.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["submission_temp_id"]: r for r in payload["records"]}


def test_validator_passes_on_committed_payload(payload: dict[str, Any]) -> None:
    assert validate_world_nations_bootstrap(payload, path=PATH) == []


def test_validator_fails_on_dangling_edge(payload: dict[str, Any]) -> None:
    bad = copy.deepcopy(payload)
    edge = next(r for r in bad["records"] if r.get("EdgeType"))
    edge["to_vertex_temp_id"] = "world-nation-ZZ-v999"
    errors = validate_world_nations_bootstrap(bad, path=PATH)
    assert any("world-nation-ZZ-v999" in e for e in errors)


def test_validator_fails_on_bare_code_alias(payload: dict[str, Any]) -> None:
    bad = copy.deepcopy(payload)
    vertex = next(r for r in bad["records"] if r.get("VertexType") == "Territory")
    vertex["Aliases"] = list(vertex.get("Aliases") or []) + ["GB"]
    errors = validate_world_nations_bootstrap(bad, path=PATH)
    assert any("bare" in e and "GB" in e for e in errors)


def test_validator_fails_on_taxonomy_field_and_duplicate_id(payload: dict[str, Any]) -> None:
    bad = copy.deepcopy(payload)
    bad["records"][0]["L1"] = "x"
    bad["records"][1]["submission_temp_id"] = bad["records"][0]["submission_temp_id"]
    errors = validate_world_nations_bootstrap(bad, path=PATH)
    assert any("L1" in e for e in errors)
    assert any("duplicate" in e for e in errors)


def test_payload_counts(payload: dict[str, Any]) -> None:
    assert payload["pack_id"] == "world_nations_bootstrap"
    assert payload["record_count"] == 488
    assert len(payload["records"]) == 488
    vertices = [r for r in payload["records"] if "VertexType" in r]
    edges = [r for r in payload["records"] if "EdgeType" in r]
    assert len(vertices) == 244
    assert len(edges) == 244


def test_earth_row(payload: dict[str, Any]) -> None:
    earth = _by_id(payload)["world-earth-v001"]
    assert earth["VertexType"] == "Planet"
    assert earth["Name"] == "Earth"
    assert earth["Sticker"] == "EARTH"
    assert "M49:001" in earth["Aliases"]
    assert "NAIF:399" in earth["Aliases"]


def test_cayman_is_territory_of_gb(payload: dict[str, Any]) -> None:
    rows = _by_id(payload)
    assert rows["world-nation-KY-v001"]["VertexType"] == "Territory"
    edge = rows["world-nation-KY-e001"]
    assert edge["from_vertex_temp_id"] == "world-nation-KY-v001"
    assert edge["to_vertex_temp_id"] == "world-nation-GB-v001"


def test_taiwan_is_disputed_state_in_earth(payload: dict[str, Any]) -> None:
    rows = _by_id(payload)
    assert rows["world-nation-TW-v001"]["VertexType"] == "DisputedState"
    edge = rows["world-nation-TW-e001"]
    assert edge["to_vertex_temp_id"] == "world-earth-v001"


def test_us_geo_extent_contained_by_earth(payload: dict[str, Any]) -> None:
    edge = _by_id(payload)["world-usgeo-natregion-e001"]
    assert edge["from_vertex_temp_id"] == "us-geo-natregion-us-v001"
    assert edge["to_vertex_temp_id"] == "world-earth-v001"
