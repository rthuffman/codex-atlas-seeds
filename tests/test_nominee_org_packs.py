"""Nominee org skeleton catalog packs (judiciary + independent executive orgs)."""

from __future__ import annotations

import json
from pathlib import Path

from codex_seeds_ci.repo import find_repo_root


def test_judiciary_catalog_counts() -> None:
    path = find_repo_root() / "packs" / "usg_federal_judiciary_orgs" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["circuit_count"] == 13
    assert data["district_count"] == 94
    assert len(data["circuits"]) == 13
    assert len(data["districts"]) == 94


def test_independent_orgs_catalog_counts() -> None:
    path = find_repo_root() / "packs" / "usg_executive_independent_orgs" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["org_count"] == 53
    assert len(data["orgs"]) == 53
    slugs = {str(row["slug"]) for row in data["orgs"]}
    assert "usg-org-fed-system" in slugs
    assert "usg-ent-fannie-mae" in slugs
    assert "usg-org-nea" in slugs
    assert "usg-org-nfah" in slugs


def test_statutory_cabinet_timeline_v4() -> None:
    path = find_repo_root() / "packs" / "usg_statutory_cabinet_timeline" / "timeline.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format_version"] == 4
    departments = data["departments"]
    assert len(departments) >= 15
    cabinet_level = [row for row in departments if row.get("role_kind") == "cabinet_level"]
    assert len(cabinet_level) >= 5
    assert all(str(row.get("org_slug") or "").startswith(("usg-org-", "usg-gold-")) for row in cabinet_level)


def test_senate_class_assignments_track2_streams() -> None:
    path = find_repo_root() / "packs" / "usg_senate_class_assignments" / "class_assignments.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["catalog_id"] == "usg_senate_class_assignments"
    assert len(data["state_classes"]) == 50
    streams = [row for row in data["assignments"] if row.get("track2_gold_stream")]
    assert len(streams) == 96
    assert data["assignment_count"] == 96


def test_structure_assigned_attachments_pack() -> None:
    path = find_repo_root() / "packs" / "usg_structure_assigned_attachments" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["attachment_count"] == 295
    assert len(data["attachments"]) == 295
    assert data["certification_status"] == "certified"
    assert "usg-gold-leg-v00001" in data["parent_vertices"]
    slugs = {str(r["org_slug"]) for r in data["attachments"]}
    assert "usg-org-epa" in slugs
    assert "usg-org-circuit-ninth" in slugs
    assert "usg-org-nea" in slugs
    assert "usg-org-neh" in slugs


def test_appointed_offices_catalog_counts() -> None:
    path = find_repo_root() / "packs" / "usg_appointed_offices" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["certification_status"] == "certified"
    assert data["office_count"] >= 200
    assert len(data["offices"]) == data["office_count"]
    assert "potus" in data["offices"]
    assert "scotus" in data["offices"]
    judicial = [
        key for key, row in data["offices"].items() if str(row.get("role_kind") or "") == "judicial"
    ]
    assert len(judicial) >= 50
