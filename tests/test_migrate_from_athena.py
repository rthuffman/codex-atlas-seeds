from __future__ import annotations

import json

import pytest

from codex_seeds_ci.migrate_from_athena import verify_synced_invariants


def _write_catalog(repo_root, years: list[int]) -> None:
    p = repo_root / "packs" / "usg_administration_skeleton"
    p.mkdir(parents=True, exist_ok=True)
    rows = [{"inauguration_year": y, "name": f"Y{y}", "DoB": f"{y}-01-20", "DoE": f"{y + 4}-01-20"} for y in years]
    (p / "catalog.json").write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")


def test_verify_synced_invariants_passes_with_required_years(tmp_path) -> None:
    _write_catalog(tmp_path, [1789, 2013, 2021, 2025])
    (tmp_path / "parity_policy.yaml").write_text(
        "required_catalog_inauguration_years: [2013, 2021]\n",
        encoding="utf-8",
    )
    verify_synced_invariants(repo_root=tmp_path)


def test_verify_synced_invariants_fails_when_required_year_missing(tmp_path) -> None:
    _write_catalog(tmp_path, [1789, 2021, 2025])
    (tmp_path / "parity_policy.yaml").write_text(
        "required_catalog_inauguration_years: [2013]\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="missing required inauguration years"):
        verify_synced_invariants(repo_root=tmp_path)
