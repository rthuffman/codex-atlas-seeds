"""AS-5 parity gate: compare deterministic builder output to gold-detail baselines."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from codex_seeds_ci.athena_venv import athena_codex_root
from codex_seeds_ci.manifest import load_bundle_manifest
from codex_seeds_ci.repo import find_repo_root

DEFAULT_RESERVED_PREFIX = "72a4cd2a-fa72-774a-a73c-72587"
DEFAULT_SENTINEL_CONGRESSES = [118]
DEFAULT_SENTINEL_ADMIN_YEARS = [2021]
DEFAULT_ALLOWED_GOLD_MEMBERSHIP_EXTRA = {"Umbrella to numbered Congress"}
DEFAULT_POLICY_PATH = Path("parity_policy.yaml")
POLICY_FORMAT_VERSION = 1


def _parse_csv_ints(raw: str) -> list[int]:
    out: list[int] = []
    for token in raw.split(","):
        t = token.strip()
        if not t:
            continue
        out.append(int(t))
    return out


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be an object")
    return data


def _load_policy(repo_root: Path, policy_path: Path | None) -> dict[str, Any]:
    path = policy_path or (repo_root / DEFAULT_POLICY_PATH)
    if not path.is_file():
        return {
            "policy_format_version": POLICY_FORMAT_VERSION,
            "required_packs": [
                "usg_administration_skeleton",
                "usg_statutory_cabinet_timeline",
                "usg_house_apportionment_vintages",
                "usg_congress_session_bounds",
                "usg_congress_state_seating",
                "usg_house_non_voting_delegate_seats",
            ],
            "scope": {
                "sentinel": {
                    "congresses": DEFAULT_SENTINEL_CONGRESSES,
                    "administration_years": DEFAULT_SENTINEL_ADMIN_YEARS,
                },
                "full": {
                    "congresses": DEFAULT_SENTINEL_CONGRESSES,
                    "administration_years": DEFAULT_SENTINEL_ADMIN_YEARS,
                },
            },
            "allowed_gold_membership_extra": sorted(DEFAULT_ALLOWED_GOLD_MEMBERSHIP_EXTRA),
            "reserved_prospectus_id_prefix": DEFAULT_RESERVED_PREFIX,
            "builder_fixture_mappings": [
                {
                    "pack_id": "usg_administration_skeleton",
                    "source_file": "catalog.json",
                    "builder_fixture_name": "us_administration_skeleton_catalog.json",
                },
                {
                    "pack_id": "usg_statutory_cabinet_timeline",
                    "source_file": "timeline.json",
                    "builder_fixture_name": "us_statutory_cabinet_departments_timeline.json",
                },
                {
                    "pack_id": "usg_house_apportionment_vintages",
                    "source_file": "vintages.json",
                    "builder_fixture_name": "us_house_apportionment_vintages.json",
                },
                {
                    "pack_id": "usg_congress_session_bounds",
                    "source_file": "bounds.json",
                    "builder_fixture_name": "us_congress_session_bounds.json",
                },
                {
                    "pack_id": "usg_congress_state_seating",
                    "source_file": "seating.json",
                    "builder_fixture_name": "us_congress_state_seating.json",
                },
                {
                    "pack_id": "usg_house_non_voting_delegate_seats",
                    "source_file": "delegates.json",
                    "builder_fixture_name": "us_house_non_voting_delegate_seats.json",
                },
                {
                    "pack_id": "us_house_district_topology",
                    "source_file": "topology.json",
                    "builder_fixture_name": "us_house_district_topology.json",
                },
            ],
        }
    return _load_yaml(path)


def _validate_policy(policy: dict[str, Any]) -> None:
    ver = int(policy.get("policy_format_version") or 0)
    if ver != POLICY_FORMAT_VERSION:
        raise ValueError(
            f"unsupported policy_format_version {ver}; expected {POLICY_FORMAT_VERSION}"
        )
    required = policy.get("required_packs")
    if not isinstance(required, list) or not required:
        raise ValueError("parity policy requires non-empty required_packs list")
    scope = policy.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("parity policy requires scope mapping")
    for mode in ("sentinel", "full"):
        raw = scope.get(mode)
        if not isinstance(raw, dict):
            raise ValueError(f"parity policy requires scope.{mode} mapping")
        if not isinstance(raw.get("congresses"), list) or not raw.get("congresses"):
            raise ValueError(f"parity policy requires scope.{mode}.congresses list")
        if not isinstance(raw.get("administration_years"), list) or not raw.get("administration_years"):
            raise ValueError(f"parity policy requires scope.{mode}.administration_years list")
    allowed_gold_extras = {
        str(x).strip() for x in (policy.get("allowed_gold_membership_extra") or []) if str(x).strip()
    }
    raw_legacy = policy.get("legacy_exceptions") or []
    if raw_legacy and not isinstance(raw_legacy, list):
        raise ValueError("parity policy legacy_exceptions must be a list")
    for i, item in enumerate(raw_legacy):
        if not isinstance(item, dict):
            raise ValueError(f"legacy_exceptions[{i}] must be an object")
        for key in (
            "id",
            "applies_to",
            "token",
            "rationale",
            "owner",
            "retirement_criteria",
            "target_date",
        ):
            if not str(item.get(key) or "").strip():
                raise ValueError(f"legacy_exceptions[{i}] missing required field: {key}")
        applies_to = str(item.get("applies_to") or "").strip()
        token = str(item.get("token") or "").strip()
        if applies_to == "allowed_gold_membership_extra" and token not in allowed_gold_extras:
            raise ValueError(
                f"legacy_exceptions[{i}] token {token!r} not present in allowed_gold_membership_extra"
            )
        if applies_to == "administration_membership_gold_subset_years":
            subset_years = {
                str(x).strip()
                for x in (policy.get("administration_membership_gold_subset_years") or [])
                if str(x).strip()
            }
            tokens = {t.strip() for t in token.split(",") if t.strip()}
            if not tokens.issubset(subset_years):
                raise ValueError(
                    f"legacy_exceptions[{i}] token years {sorted(tokens)} not in administration_membership_gold_subset_years"
                )
        target_date = str(item.get("target_date") or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_date):
            raise ValueError(f"legacy_exceptions[{i}] target_date must be YYYY-MM-DD")


def _legacy_exception_report_entries(policy: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for raw in policy.get("legacy_exceptions") or []:
        if not isinstance(raw, dict):
            continue
        entries.append(
            {
                "id": str(raw.get("id") or "").strip(),
                "applies_to": str(raw.get("applies_to") or "").strip(),
                "token": str(raw.get("token") or "").strip(),
                "owner": str(raw.get("owner") or "").strip(),
                "target_date": str(raw.get("target_date") or "").strip(),
                "rationale": str(raw.get("rationale") or "").strip(),
                "retirement_criteria": str(raw.get("retirement_criteria") or "").strip(),
            }
        )
    entries.sort(key=lambda x: (x.get("target_date") or "9999-99-99", x.get("id") or ""))
    return entries


def _assert_required_packs(repo_root: Path, policy: dict[str, Any]) -> None:
    required = [str(x).strip() for x in policy.get("required_packs") or [] if str(x).strip()]
    if not required:
        return
    manifest = load_bundle_manifest(repo_root)
    packs = manifest.get("packs")
    present = set()
    if isinstance(packs, list):
        for raw in packs:
            if isinstance(raw, dict):
                pid = str(raw.get("pack_id") or "").strip()
                if pid:
                    present.add(pid)
    missing = [p for p in required if p not in present]
    if missing:
        raise ValueError(f"manifest missing required pack(s): {missing}")


def _assert_required_catalog_years(repo_root: Path, policy: dict[str, Any]) -> None:
    years = [int(x) for x in (policy.get("required_catalog_inauguration_years") or [])]
    if not years:
        return
    path = repo_root / "packs" / "usg_administration_skeleton" / "catalog.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing administration catalog: {path}")
    data = _load_json(path)
    rows = data.get("administrations")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: administrations must be a list")
    present = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        try:
            present.add(int(raw.get("inauguration_year")))
        except (TypeError, ValueError):
            continue
    missing = [y for y in years if y not in present]
    if missing:
        raise ValueError(f"administration catalog missing required inauguration_year(s): {missing}")


def _load_gold_detail_structural(path: Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    rows = data.get("records")
    if not isinstance(rows, list):
        raise ValueError("gold-detail records must be a list")
    records = [r for r in rows if isinstance(r, dict)]
    person_ids = {
        str(r.get("submission_temp_id") or "").strip()
        for r in records
        if r.get("VertexType") == "Person" and str(r.get("submission_temp_id") or "").strip()
    }
    out: list[dict[str, Any]] = []
    for r in records:
        if r.get("VertexType") == "Person" or r.get("EdgeType") == "HoldsSeat":
            continue
        if r.get("EdgeType"):
            fr = str(r.get("from_vertex_temp_id") or "").strip()
            to = str(r.get("to_vertex_temp_id") or "").strip()
            if fr in person_ids or to in person_ids:
                continue
        out.append(r)
    return out


def _gold_congress_slice(
    records: list[dict[str, Any]],
    congress: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    variants = {str(congress), f"{int(congress):03d}"}
    session_ids = {
        f"usg-gold-leg-cong{n}-v{s}"
        for n in variants
        for s in ("01", "02", "03")
    }
    v2_candidates = {sid for sid in session_ids if sid.endswith("-v02")}
    orgs = [
        r
        for r in records
        if r.get("VertexType") == "GovernmentalOrg" and str(r.get("submission_temp_id") or "") in session_ids
    ]
    membership = [
        r
        for r in records
        if r.get("EdgeType") == "Membership"
        and (
            str(r.get("from_vertex_temp_id") or "") in session_ids
            or str(r.get("to_vertex_temp_id") or "") in session_ids
        )
    ]
    seatof = [
        r
        for r in records
        if r.get("EdgeType") == "SeatOf" and str(r.get("to_vertex_temp_id") or "") in v2_candidates
    ]
    office_ids = {str(r.get("from_vertex_temp_id") or "") for r in seatof}
    offices = [
        r
        for r in records
        if r.get("VertexType") == "Office" and str(r.get("submission_temp_id") or "") in office_ids
    ]
    return orgs, membership, offices, seatof


def _copy_pack_payloads_for_builders(repo_root: Path, out_dir: Path, policy: dict[str, Any]) -> None:
    mappings = policy.get("builder_fixture_mappings") or []
    if not isinstance(mappings, list) or not mappings:
        raise ValueError("parity policy requires non-empty builder_fixture_mappings")
    out_dir.mkdir(parents=True, exist_ok=True)
    for raw in mappings:
        if not isinstance(raw, dict):
            raise ValueError("builder_fixture_mappings entries must be objects")
        pack_id = str(raw.get("pack_id") or "").strip()
        src_name = str(raw.get("source_file") or "").strip()
        dst_raw = raw.get("builder_fixture_name")
        if dst_raw is None or (isinstance(dst_raw, str) and not dst_raw.strip()):
            # Projection-only packs (geo/structure envelopes) are in required_packs but not AS-5 builder fixtures.
            continue
        dst_name = str(dst_raw).strip()
        if not pack_id or not src_name or not dst_name:
            raise ValueError("builder_fixture_mappings entries require pack_id/source_file/builder_fixture_name")
        src = repo_root / "packs" / pack_id / src_name
        if not src.is_file():
            raise FileNotFoundError(f"missing pack payload: {src}")
        shutil.copy2(src, out_dir / dst_name)


def _parity_polity_slugs() -> dict[str, str]:
    """Synthetic postal→slug map so House delegation/seat scaffolding runs in CI (no live graph)."""
    from artemis.usg_congress_session_builder import _STATE_POSTAL_TO_NAME  # type: ignore

    slugs = {postal: f"parity-polity-{postal.lower()}" for postal in _STATE_POSTAL_TO_NAME}
    for code in ("DC", "PR", "AS", "GU", "MP", "VI"):
        slugs[code] = f"parity-polity-{code.lower()}"
    return slugs


def _compare_congress(
    *,
    congress: int,
    gold_records: list[dict[str, Any]],
    build_records: list[dict[str, Any]],
    allowed_gold_membership_extra: set[str],
) -> list[str]:
    errors: list[str] = []
    gold_orgs, gold_mem, gold_offices, gold_seatof = _gold_congress_slice(gold_records, congress)

    api_orgs = [r for r in build_records if r.get("VertexType") == "GovernmentalOrg"]
    api_mem = [r for r in build_records if r.get("EdgeType") == "Membership"]
    api_offices = [r for r in build_records if r.get("VertexType") == "Office"]
    api_seatof = [r for r in build_records if r.get("EdgeType") == "SeatOf"]

    if len(api_orgs) != len(gold_orgs):
        errors.append(f"congress {congress}: GovernmentalOrg count {len(api_orgs)} != {len(gold_orgs)}")
    if len(api_offices) != len(gold_offices):
        errors.append(f"congress {congress}: Office count {len(api_offices)} != {len(gold_offices)}")
    if len(api_seatof) != len(gold_seatof):
        errors.append(f"congress {congress}: SeatOf count {len(api_seatof)} != {len(gold_seatof)}")

    if {str(r.get("Name") or "") for r in api_orgs} != {str(r.get("Name") or "") for r in gold_orgs}:
        errors.append(f"congress {congress}: GovernmentalOrg name set drift")

    api_mem_by_sticker = {str(r.get("Sticker") or ""): r for r in api_mem}
    gold_mem_by_sticker = {str(r.get("Sticker") or ""): r for r in gold_mem}
    api_stickers = set(api_mem_by_sticker.keys())
    gold_stickers = set(gold_mem_by_sticker.keys())
    if not api_stickers.issubset(gold_stickers):
        extras = sorted(api_stickers - gold_stickers)
        errors.append(f"congress {congress}: Membership stickers not in gold-detail: {extras}")
    unexpected_gold_only = gold_stickers - api_stickers - allowed_gold_membership_extra
    if unexpected_gold_only:
        errors.append(
            f"congress {congress}: unexpected gold-only Membership stickers: {sorted(unexpected_gold_only)}"
        )

    gold_office_dob_doe = {
        str(r.get("Name") or ""): (str(r.get("DoB") or ""), str(r.get("DoE") or "")) for r in gold_offices
    }
    api_office_dob_doe = {
        str(r.get("Name") or ""): (str(r.get("DoB") or ""), str(r.get("DoE") or "")) for r in api_offices
    }
    if api_office_dob_doe != gold_office_dob_doe:
        errors.append(f"congress {congress}: Office interval drift")

    gold_office_name_by_id = {
        str(r.get("submission_temp_id") or ""): str(r.get("Name") or "") for r in gold_offices
    }
    api_office_name_by_id = {
        str(r.get("submission_temp_id") or ""): str(r.get("Name") or "") for r in api_offices
    }
    gold_seatof_dob_doe = {
        gold_office_name_by_id[str(r.get("from_vertex_temp_id") or "")]: (
            str(r.get("DoB") or ""),
            str(r.get("DoE") or ""),
        )
        for r in gold_seatof
        if str(r.get("from_vertex_temp_id") or "") in gold_office_name_by_id
    }
    api_seatof_dob_doe = {
        api_office_name_by_id[str(r.get("from_vertex_temp_id") or "")]: (
            str(r.get("DoB") or ""),
            str(r.get("DoE") or ""),
        )
        for r in api_seatof
        if str(r.get("from_vertex_temp_id") or "") in api_office_name_by_id
    }
    if api_seatof_dob_doe != gold_seatof_dob_doe:
        errors.append(f"congress {congress}: SeatOf interval drift")
    return errors


def _compare_congress_catalog_only(
    *,
    congress: int,
    build_records: list[dict[str, Any]],
    expected_names: set[str],
) -> list[str]:
    """
    Fallback checks for congresses with no reliable gold-detail baseline.

    Enforces deterministic topology/interval invariants directly from builder output.
    """
    errors: list[str] = []
    api_orgs = [r for r in build_records if r.get("VertexType") == "GovernmentalOrg"]
    api_mem = [r for r in build_records if r.get("EdgeType") == "Membership"]
    api_offices = [r for r in build_records if r.get("VertexType") == "Office"]
    api_seatof = [r for r in build_records if r.get("EdgeType") == "SeatOf"]

    if len(api_orgs) < 3:
        errors.append(f"congress {congress}: expected at least 3 GovernmentalOrg rows, got {len(api_orgs)}")
    found_names = {str(r.get("Name") or "") for r in api_orgs}
    missing = expected_names - found_names
    if missing:
        errors.append(f"congress {congress}: missing expected org names: {sorted(missing)}")
    if len(api_mem) < 6:
        errors.append(f"congress {congress}: expected at least 6 Membership rows, got {len(api_mem)}")
    if not api_offices:
        errors.append(f"congress {congress}: expected at least one Office row")
    if len(api_offices) != len(api_seatof):
        errors.append(
            f"congress {congress}: Office/SeatOf count mismatch {len(api_offices)} != {len(api_seatof)}"
        )

    interval_rows = api_orgs + api_mem + api_offices + api_seatof
    if interval_rows:
        intervals = {(str(r.get("DoB") or ""), str(r.get("DoE") or "")) for r in interval_rows}
        if len(intervals) != 1:
            errors.append(f"congress {congress}: mixed interval set across records")
        only = next(iter(intervals))
        if not only[0] or not only[1]:
            errors.append(f"congress {congress}: missing DoB/DoE on congress structural records")
    return errors


def _compare_admin(
    *,
    inauguration_year: int,
    gold_records: list[dict[str, Any]],
    build_records: list[dict[str, Any]],
    admin_suffix: str,
    gold_membership_subset: bool = False,
) -> list[str]:
    errors: list[str] = []
    n = admin_suffix
    gold = [
        r
        for r in gold_records
        if str(r.get("submission_temp_id") or "") in {f"usg-gold-adm-v{n}", f"usg-gold-cab-v{n}"}
        or str(r.get("submission_temp_id") or "").startswith(f"usg-gold-adm-e{n}-")
        or str(r.get("submission_temp_id") or "").startswith(f"usg-gold-cab-e{n}-")
        or str(r.get("submission_temp_id") or "").startswith(f"usg-gold-cabseat-{n}-")
    ]
    api_orgs = [r for r in build_records if r.get("VertexType") == "GovernmentalOrg"]
    gold_orgs = [r for r in gold if r.get("VertexType") == "GovernmentalOrg"]
    api_mem = [r for r in build_records if r.get("EdgeType") == "Membership"]
    gold_mem = [r for r in gold if r.get("EdgeType") == "Membership"]

    if len(api_orgs) != len(gold_orgs):
        errors.append(f"administration {inauguration_year}: GovernmentalOrg count {len(api_orgs)} != {len(gold_orgs)}")
    if gold_membership_subset:
        if len(api_mem) < len(gold_mem):
            errors.append(
                f"administration {inauguration_year}: Membership count {len(api_mem)} < gold {len(gold_mem)}"
            )
    elif len(api_mem) != len(gold_mem):
        errors.append(f"administration {inauguration_year}: Membership count {len(api_mem)} != {len(gold_mem)}")
    if {str(r.get("Name") or "") for r in api_orgs} != {str(r.get("Name") or "") for r in gold_orgs}:
        errors.append(f"administration {inauguration_year}: GovernmentalOrg name set drift")

    api_edge_interval = {
        (str(r.get("submission_temp_id") or ""), str(r.get("DoB") or ""), str(r.get("DoE") or "")) for r in api_mem
    }
    gold_edge_interval = {
        (str(r.get("submission_temp_id") or ""), str(r.get("DoB") or ""), str(r.get("DoE") or "")) for r in gold_mem
    }
    if api_edge_interval != gold_edge_interval:
        if gold_membership_subset and gold_edge_interval.issubset(api_edge_interval):
            pass
        else:
            errors.append(f"administration {inauguration_year}: Membership interval drift")
    return errors


def _compare_admin_catalog_only(
    *,
    inauguration_year: int,
    build_records: list[dict[str, Any]],
    expected_name: str,
    expected_dob: str | None,
    expected_doe: str | None,
) -> list[str]:
    """
    Fallback checks for inauguration years that have no gold_adm_index baseline.

    These rows are still required for coverage, but topology parity against gold-detail
    is unavailable. Enforce deterministic catalog-backed invariants instead.
    """
    errors: list[str] = []
    api_orgs = [r for r in build_records if r.get("VertexType") == "GovernmentalOrg"]
    api_mem = [r for r in build_records if r.get("EdgeType") == "Membership"]
    if len(api_orgs) < 2:
        errors.append(f"administration {inauguration_year}: expected at least 2 GovernmentalOrg rows")
    if len(api_mem) < 3:
        errors.append(f"administration {inauguration_year}: expected at least 3 Membership rows")
    if expected_name and expected_name not in {str(r.get("Name") or "") for r in api_orgs}:
        errors.append(f"administration {inauguration_year}: expected org name missing: {expected_name!r}")
    for row in api_orgs + api_mem:
        if expected_dob and str(row.get("DoB") or "") != expected_dob:
            errors.append(f"administration {inauguration_year}: DoB drift on {row.get('submission_temp_id')}")
            break
    for row in api_orgs + api_mem:
        row_doe = str(row.get("DoE") or "")
        exp = str(expected_doe or "")
        if row_doe != exp:
            errors.append(f"administration {inauguration_year}: DoE drift on {row.get('submission_temp_id')}")
            break
    return errors


def _reserved_id_errors(
    *,
    records: list[dict[str, Any]],
    reserved_prefix: str,
) -> list[str]:
    errors: list[str] = []
    for i, row in enumerate(records):
        pid = str(row.get("ProspectusID") or "").strip().lower()
        if not pid:
            continue
        if not pid.startswith(reserved_prefix):
            errors.append(f"record[{i}] has non-reserved ProspectusID: {pid}")
    return errors


def run_parity(
    *,
    repo_root: Path,
    gold_detail_path: Path,
    mode: str,
    sentinel_congresses: list[int],
    sentinel_admin_years: list[int],
    reserved_prefix: str,
    output_json: Path,
    output_summary_json: Path | None,
    policy: dict[str, Any],
    max_diffs: int = 200,
) -> tuple[int, dict[str, Any]]:
    _validate_policy(policy)
    _assert_required_packs(repo_root, policy)
    _assert_required_catalog_years(repo_root, policy)
    gold_records = _load_gold_detail_structural(gold_detail_path)
    athena_root = athena_codex_root(start=repo_root)

    with tempfile.TemporaryDirectory(prefix="codex-seeds-parity-") as td:
        skeleton_dir = Path(td)
        _copy_pack_payloads_for_builders(repo_root, skeleton_dir, policy)

        import sys

        sys.path.insert(0, str(athena_root / "artemis" / "src"))
        from artemis.usg_administration_skeleton_builder import (  # type: ignore
            DEPT_GOLD_TEMP_BY_SEAT,
            build_administration_skeleton_intent,
            catalog_row_for_inauguration_year,
            gold_adm_index_for_inauguration_year,
        )
        from artemis.usg_congress_session_builder import build_congress_session_intent  # type: ignore
        from artemis.usg_congress_session_builder import (  # type: ignore
            bicameral_congress_org_name,
            session_house_org_name,
            session_senate_org_name,
        )

        leg_slugs = {
            "usg-gold-leg-v00003": "u-s-house-of-representatives",
            "usg-gold-leg-v00004": "u-s-senate",
        }
        dept_slugs = {
            "usg-gold-exec-v00564": "executive-branch",
            "usg-gold-exec-v00565": "president-office",
            "usg-gold-exec-v00566": "vp-office",
        }
        for seat, tid in DEPT_GOLD_TEMP_BY_SEAT.items():
            dept_slugs[tid] = f"dept-{seat}"

        scope_raw = policy.get("scope") or {}
        if not isinstance(scope_raw, dict):
            scope_raw = {}
        mode_scope = scope_raw.get(mode) if isinstance(scope_raw.get(mode), dict) else {}
        scope_congress = [int(x) for x in (mode_scope.get("congresses") or sentinel_congresses)]
        scope_admin = [int(x) for x in (mode_scope.get("administration_years") or sentinel_admin_years)]
        allowed_gold_membership_extra = {
            str(x).strip() for x in (policy.get("allowed_gold_membership_extra") or []) if str(x).strip()
        }
        catalog_only_congresses = {
            int(x) for x in (policy.get("catalog_only_congresses") or []) if str(x).strip()
        }
        catalog_only_admin_years = {
            int(x) for x in (policy.get("catalog_only_administration_years") or []) if str(x).strip()
        }
        admin_membership_gold_subset_years = {
            int(x)
            for x in (policy.get("administration_membership_gold_subset_years") or [])
            if str(x).strip()
        }

        all_records_for_reserved_check: list[dict[str, Any]] = []
        diffs: list[str] = []
        old_skeleton = os.environ.get("ARTEMIS_USG_SKELETON_DIR")
        old_token = os.environ.get("ARTEMIS_CONGRESS_GOV_API_TOKEN")
        try:
            os.environ["ARTEMIS_USG_SKELETON_DIR"] = str(skeleton_dir)
            os.environ["ARTEMIS_CONGRESS_GOV_API_TOKEN"] = ""
            polity_slugs = _parity_polity_slugs()
            for congress in scope_congress:
                intent = build_congress_session_intent(
                    congress,
                    permanent_slugs=leg_slugs,
                    polity_slugs=polity_slugs,
                    as_of="2026-05-20",
                )
                all_records_for_reserved_check.extend(intent.records)
                if congress in catalog_only_congresses:
                    diffs.extend(
                        _compare_congress_catalog_only(
                            congress=congress,
                            build_records=intent.records,
                            expected_names={
                                bicameral_congress_org_name(congress),
                                session_house_org_name(congress),
                                session_senate_org_name(congress),
                            },
                        )
                    )
                    continue
                diffs.extend(
                    _compare_congress(
                        congress=congress,
                        gold_records=gold_records,
                        build_records=intent.records,
                        allowed_gold_membership_extra=allowed_gold_membership_extra,
                    )
                )

            for year in scope_admin:
                row = catalog_row_for_inauguration_year(year)
                intent = build_administration_skeleton_intent(
                    year,
                    department_slugs=dept_slugs,
                    as_of="2026-05-20",
                )
                all_records_for_reserved_check.extend(intent.records)
                if year in catalog_only_admin_years:
                    diffs.extend(
                        _compare_admin_catalog_only(
                            inauguration_year=year,
                            build_records=intent.records,
                            expected_name=str(row.get("name") or ""),
                            expected_dob=str(row.get("DoB") or "") or None,
                            expected_doe=str(row.get("DoE") or "") or None,
                        )
                    )
                    continue
                try:
                    suffix = f"{gold_adm_index_for_inauguration_year(year):03d}"
                    diffs.extend(
                        _compare_admin(
                            inauguration_year=year,
                            gold_records=gold_records,
                            build_records=intent.records,
                            admin_suffix=suffix,
                            gold_membership_subset=year in admin_membership_gold_subset_years,
                        )
                    )
                except ValueError:
                    diffs.extend(
                        _compare_admin_catalog_only(
                            inauguration_year=year,
                            build_records=intent.records,
                            expected_name=str(row.get("name") or ""),
                            expected_dob=str(row.get("DoB") or "") or None,
                            expected_doe=str(row.get("DoE") or "") or None,
                        )
                    )
        finally:
            if old_skeleton is None:
                os.environ.pop("ARTEMIS_USG_SKELETON_DIR", None)
            else:
                os.environ["ARTEMIS_USG_SKELETON_DIR"] = old_skeleton
            if old_token is None:
                os.environ.pop("ARTEMIS_CONGRESS_GOV_API_TOKEN", None)
            else:
                os.environ["ARTEMIS_CONGRESS_GOV_API_TOKEN"] = old_token

    reserved_errors = _reserved_id_errors(records=all_records_for_reserved_check, reserved_prefix=reserved_prefix)
    status = "pass" if not diffs and not reserved_errors else "fail"
    combined_diffs = sorted(diffs + reserved_errors)
    trimmed = combined_diffs[:max_diffs]
    legacy_exceptions = _legacy_exception_report_entries(policy)
    report = {
        "status": status,
        "mode": mode,
        "policy_format_version": int(policy.get("policy_format_version") or 0),
        "legacy_exceptions": {
            "count": len(legacy_exceptions),
            "items": legacy_exceptions,
        },
        "checks": {
            "topology_intervals": {
                "status": "pass" if not diffs else "fail",
                "diff_count": len(diffs),
            },
            "reserved_ids": {
                "status": "pass" if not reserved_errors else "fail",
                "diff_count": len(reserved_errors),
                "reserved_prefix": reserved_prefix,
            },
        },
        "scope": {
            "congresses_tested": scope_congress,
            "administration_years_tested": scope_admin,
        },
        "inputs": {
            "repo_root": str(repo_root),
            "gold_detail_path": str(gold_detail_path),
        },
        "counts": {
            "records_examined": len(all_records_for_reserved_check),
            "diff_count": len(combined_diffs),
        },
        "diffs": trimmed,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if output_summary_json is not None:
        output_summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "status": report["status"],
            "mode": report["mode"],
            "policy_format_version": report["policy_format_version"],
            "diff_count": report["counts"]["diff_count"],
            "records_examined": report["counts"]["records_examined"],
            "scope": report["scope"],
            "checks": {
                "topology_intervals": report["checks"]["topology_intervals"]["status"],
                "reserved_ids": report["checks"]["reserved_ids"]["status"],
            },
            "legacy_exceptions": {
                "count": report["legacy_exceptions"]["count"],
                "next_target_date": (
                    report["legacy_exceptions"]["items"][0]["target_date"]
                    if report["legacy_exceptions"]["items"]
                    else None
                ),
            },
        }
        output_summary_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return (0 if status == "pass" else 1), report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AS-5 parity checks against gold-detail.")
    parser.add_argument("--repo-root", type=Path, default=None, help="codex-atlas-seeds repo root")
    parser.add_argument(
        "--gold-detail",
        type=Path,
        default=None,
        help="Path to phase1-ingest-gold-detail.json (defaults from ATHENA_CODEX_ROOT)",
    )
    parser.add_argument("--mode", choices=("sentinel", "full"), default="full")
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Parity policy YAML (default: <repo_root>/parity_policy.yaml)",
    )
    parser.add_argument("--sentinel-congresses", default="118")
    parser.add_argument("--sentinel-admin-years", default="2021")
    parser.add_argument("--reserved-prefix", default=DEFAULT_RESERVED_PREFIX)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-summary-json", type=Path, default=None)
    parser.add_argument("--max-diffs", type=int, default=200)
    args = parser.parse_args()

    repo_root = args.repo_root or find_repo_root()
    policy = _load_policy(repo_root, args.policy)
    athena_root = athena_codex_root(start=repo_root)
    gold_detail = args.gold_detail or (athena_root / "base-data" / "phase1-ingest-gold-detail.json")
    policy_prefix = str(policy.get("reserved_prospectus_id_prefix") or DEFAULT_RESERVED_PREFIX).strip().lower()
    reserved_prefix = str(args.reserved_prefix).strip().lower()
    if reserved_prefix != policy_prefix:
        raise SystemExit(
            f"--reserved-prefix ({reserved_prefix}) does not match policy reserved_prospectus_id_prefix ({policy_prefix})"
        )
    output_json = args.output_json or (repo_root / "dist" / "parity-report.json")
    output_summary_json = args.output_summary_json or (repo_root / "dist" / "parity-summary.json")
    code, report = run_parity(
        repo_root=repo_root,
        gold_detail_path=gold_detail,
        mode=args.mode,
        sentinel_congresses=_parse_csv_ints(args.sentinel_congresses),
        sentinel_admin_years=_parse_csv_ints(args.sentinel_admin_years),
        reserved_prefix=reserved_prefix,
        output_json=output_json,
        output_summary_json=output_summary_json,
        policy=policy,
        max_diffs=max(1, int(args.max_diffs)),
    )
    print(f"parity: {report['status']} ({report['counts']['diff_count']} diff(s))")
    print(f"report: {output_json}")
    print(f"summary: {output_summary_json}")
    legacy = report.get("legacy_exceptions") or {}
    legacy_count = int(legacy.get("count") or 0)
    if legacy_count:
        playbook = repo_root / "LEGACY_EXCEPTION_RETIREMENT.md"
        next_date = "n/a"
        items = legacy.get("items") or []
        if items and isinstance(items[0], dict):
            next_date = str(items[0].get("target_date") or "n/a")
        print("!!! WARNING: PARITY LEGACY EXCEPTIONS ACTIVE !!!")
        print(f"parity: legacy exceptions active={legacy_count} next_target_date={next_date}")
        print(f"parity: exact retirement steps -> {playbook}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
