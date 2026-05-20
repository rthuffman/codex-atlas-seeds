"""AS-5 parity gate tests."""

from __future__ import annotations

from codex_seeds_ci.athena_venv import athena_codex_root
from codex_seeds_ci.parity import _load_policy, _parse_csv_ints, run_parity
from codex_seeds_ci.repo import find_repo_root


def test_parse_csv_ints() -> None:
    assert _parse_csv_ints("118, 119,130") == [118, 119, 130]


def test_run_parity_sentinel_passes(tmp_path) -> None:
    repo_root = find_repo_root()
    policy = _load_policy(repo_root, None)
    gold_detail = athena_codex_root(start=repo_root) / "base-data" / "phase1-ingest-gold-detail.json"
    code, report = run_parity(
        repo_root=repo_root,
        gold_detail_path=gold_detail,
        mode="sentinel",
        sentinel_congresses=[118],
        sentinel_admin_years=[2021],
        reserved_prefix="72a4cd2a-fa72-774a-a73c-72587",
        output_json=tmp_path / "parity-report.json",
        output_summary_json=tmp_path / "parity-summary.json",
        policy=policy,
    )
    assert code == 0
    assert report["status"] == "pass"
    assert report["counts"]["diff_count"] == 0
    assert report["policy_format_version"] == 1
    assert report["legacy_exceptions"]["count"] >= 1


def test_parity_policy_file_loads() -> None:
    repo_root = find_repo_root()
    policy = _load_policy(repo_root, None)
    assert "required_packs" in policy
    assert "scope" in policy
    assert 1789 in policy.get("required_catalog_inauguration_years", [])
    assert 2013 in policy.get("required_catalog_inauguration_years", [])
    assert 2025 in policy.get("required_catalog_inauguration_years", [])
    assert 1 in policy["scope"]["full"]["congresses"]
    assert 40 in policy.get("catalog_only_congresses", [])
    assert 100 in policy.get("catalog_only_congresses", [])
    assert 1945 in policy.get("catalog_only_administration_years", [])
    legacy = policy.get("legacy_exceptions", [])
    assert isinstance(legacy, list) and legacy
    tokens = {str(x.get("token")) for x in legacy if isinstance(x, dict)}
    assert "Umbrella to numbered Congress" in tokens
    assert 1789 in policy["scope"]["full"]["administration_years"]
    assert 2013 in policy["scope"]["full"]["administration_years"]
    assert len(policy["scope"]["full"]["congresses"]) >= 4
    assert len(policy["scope"]["full"]["administration_years"]) >= 6
