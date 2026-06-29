"""Load and validate bundle / pack manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from codex_seeds_ci.repo import find_repo_root


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a mapping")
    return data


def packs_dir(repo_root: Path | None = None) -> Path:
    return (repo_root or find_repo_root()) / "packs"


def manifest_path(repo_root: Path | None = None) -> Path:
    return (repo_root or find_repo_root()) / "manifest.yaml"


def load_bundle_manifest(repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(manifest_path(repo_root))


def load_pack_manifest(pack_dir: Path) -> dict[str, Any]:
    pack_yaml = pack_dir / "pack.yaml"
    if not pack_yaml.is_file():
        raise FileNotFoundError(f"missing pack.yaml in {pack_dir}")
    data = load_yaml(pack_yaml)
    if str(data.get("pack_id") or "") != pack_dir.name:
        raise ValueError(f"{pack_yaml}: pack_id must match directory name {pack_dir.name!r}")
    return data


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_pack_file_hashes(pack_dir: Path, pack: dict[str, Any]) -> dict[str, str]:
    files = pack.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError(f"{pack_dir}/pack.yaml: files must be a non-empty list")
    out: dict[str, str] = {}
    for rel in files:
        rel_s = str(rel).replace("\\", "/")
        path = pack_dir / rel_s
        if not path.is_file():
            raise FileNotFoundError(f"pack {pack_dir.name}: missing file {rel_s}")
        out[rel_s] = file_sha256(path)
    return out


def discover_packs(repo_root: Path | None = None) -> list[Path]:
    root = packs_dir(repo_root)
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "pack.yaml").is_file())


def validate_bundle_manifest(manifest: dict[str, Any], *, repo_root: Path) -> list[str]:
    errors: list[str] = []
    if int(manifest.get("bundle_format_version") or 0) != 1:
        errors.append("bundle_format_version must be 1")
    if not str(manifest.get("bundle_version") or "").strip():
        errors.append("bundle_version is required")
    if not str(manifest.get("requires_atlas_schema_version") or "").strip():
        errors.append("requires_atlas_schema_version is required")
    packs = manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        errors.append("packs must be a non-empty list")
        return errors
    seen_ids: set[str] = set()
    for raw in packs:
        if not isinstance(raw, dict):
            errors.append("each packs[] entry must be a mapping")
            continue
        pack_id = str(raw.get("pack_id") or "").strip()
        if not pack_id:
            errors.append("pack entry missing pack_id")
            continue
        if pack_id in seen_ids:
            errors.append(f"duplicate pack_id: {pack_id}")
        seen_ids.add(pack_id)
        pack_dir = packs_dir(repo_root) / pack_id
        if not pack_dir.is_dir():
            errors.append(f"pack directory missing: packs/{pack_id}")
            continue
        try:
            pm = load_pack_manifest(pack_dir)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if str(pm.get("version") or "") != str(raw.get("version") or ""):
            errors.append(f"{pack_id}: pack.yaml version must match manifest packs[].version")
        listed = raw.get("files")
        if not isinstance(listed, list):
            errors.append(f"{pack_id}: files must be a list in bundle manifest")
            continue
        expected = {str(f).replace("\\", "/") for f in pm.get("files") or []}
        actual = {str(f).replace("\\", "/") for f in listed}
        if expected != actual:
            errors.append(f"{pack_id}: manifest file list must match pack.yaml files")
    return errors


def validate_administration_catalog(data: dict[str, Any], *, path: str) -> list[str]:
    errors: list[str] = []
    rows = data.get("administrations")
    if not isinstance(rows, list) or not rows:
        errors.append(f"{path}: administrations must be a non-empty list")
        return errors
    for i, raw in enumerate(rows):
        if not isinstance(raw, dict):
            errors.append(f"{path}: administrations[{i}] must be an object")
            continue
        if not str(raw.get("name") or "").strip():
            errors.append(f"{path}: administrations[{i}] missing name")
        try:
            int(raw["inauguration_year"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{path}: administrations[{i}] invalid inauguration_year")
    return errors


def _require_non_empty_list(
    data: dict[str, Any],
    *,
    key: str,
    path: str,
) -> list[str]:
    rows = data.get(key)
    if not isinstance(rows, list) or not rows:
        return [f"{path}: {key} must be a non-empty list"]
    return []


def validate_apportionment_vintages(data: dict[str, Any], *, path: str) -> list[str]:
    errors = _require_non_empty_list(data, key="vintages", path=path)
    for i, raw in enumerate(data.get("vintages") or []):
        if not isinstance(raw, dict):
            errors.append(f"{path}: vintages[{i}] must be an object")
            continue
        try:
            int(raw["first_congress"])
            int(raw["last_congress"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{path}: vintages[{i}] missing first_congress/last_congress")
    return errors


def validate_congress_bounds(data: dict[str, Any], *, path: str) -> list[str]:
    errors = _require_non_empty_list(data, key="congresses", path=path)
    for i, raw in enumerate(data.get("congresses") or []):
        if not isinstance(raw, dict):
            errors.append(f"{path}: congresses[{i}] must be an object")
            continue
        try:
            c = int(raw["congress"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{path}: congresses[{i}] invalid congress")
            continue
        if c < 1:
            errors.append(f"{path}: congresses[{i}] congress must be >= 1")
    return errors


def validate_state_seating(data: dict[str, Any], *, path: str) -> list[str]:
    errors = _require_non_empty_list(data, key="rows", path=path)
    for i, raw in enumerate(data.get("rows") or []):
        if not isinstance(raw, dict):
            errors.append(f"{path}: rows[{i}] must be an object")
            continue
        try:
            int(raw["congress"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{path}: rows[{i}] invalid congress")
        if not str(raw.get("postal") or "").strip():
            errors.append(f"{path}: rows[{i}] missing postal")
    return errors


def validate_delegate_seats(data: dict[str, Any], *, path: str) -> list[str]:
    errors = _require_non_empty_list(data, key="seats", path=path)
    for i, raw in enumerate(data.get("seats") or []):
        if not isinstance(raw, dict):
            errors.append(f"{path}: seats[{i}] must be an object")
            continue
        try:
            int(raw["first_congress"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{path}: seats[{i}] invalid first_congress")
    return errors


def validate_house_district_topology(data: dict[str, Any], *, path: str) -> list[str]:
    errors: list[str] = []
    if int(data.get("format_version") or 0) != 2:
        errors.append(f"{path}: format_version must be 2")
    source = data.get("source")
    if not isinstance(source, dict) or not source:
        errors.append(f"{path}: source must be a non-empty object")
    intervals = data.get("intervals")
    if not isinstance(intervals, list) or not intervals:
        errors.append(f"{path}: intervals must be a non-empty list")
    seen_ranges: dict[str, list[tuple[int, int, int]]] = {}
    valid_kinds = {
        "single_statewide_at_large",
        "statewide_general_ticket",
        "hybrid_at_large",
        "single_member_districts",
        "plural_districts",
        "mixed_plural",
    }
    for i, raw in enumerate(intervals or []):
        if not isinstance(raw, dict):
            errors.append(f"{path}: intervals[{i}] must be an object")
            continue
        postal = str(raw.get("postal") or "").strip().upper()
        try:
            first = int(raw["first_congress"])
            last = int(raw.get("last_congress") or first)
            numbered = int(raw.get("numbered_single_member_count", raw.get("numbered_count", 0)))
            at_large = int(raw.get("statewide_at_large_count", raw.get("at_large_count", 0)))
        except (KeyError, TypeError, ValueError):
            errors.append(f"{path}: intervals[{i}] invalid counts or first_congress")
            continue
        if not postal:
            errors.append(f"{path}: intervals[{i}] missing postal")
        if first < 1 or last < first:
            errors.append(f"{path}: intervals[{i}] invalid congress range")
        if numbered < 0 or at_large < 0:
            errors.append(f"{path}: intervals[{i}] counts must be non-negative")
        kind = str(raw.get("topology_kind") or "").strip()
        if kind not in valid_kinds:
            errors.append(f"{path}: intervals[{i}] invalid topology_kind")
        if not str(raw.get("source_authority") or "").strip():
            errors.append(f"{path}: intervals[{i}] missing source_authority")
        if str(raw.get("review_status") or "").strip() != "reviewed":
            errors.append(f"{path}: intervals[{i}] review_status must be reviewed")
        # Post-92nd: multi-seat states use numbered districts only. Single-seat states
        # (apportionment=1) legitimately use statewide at-large seat code A (ND/MT/SD).
        if first >= 92 and numbered > 0 and at_large > 0:
            errors.append(f"{path}: intervals[{i}] violates post-92nd single-member district invariant")
        plural = raw.get("plural_districts") or []
        if plural and not isinstance(plural, list):
            errors.append(f"{path}: intervals[{i}] plural_districts must be a list")
        for j, p_raw in enumerate(plural if isinstance(plural, list) else []):
            if not isinstance(p_raw, dict):
                errors.append(f"{path}: intervals[{i}].plural_districts[{j}] must be an object")
                continue
            try:
                district = int(p_raw["district"])
                seat_count = int(p_raw["seat_count"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{path}: intervals[{i}].plural_districts[{j}] invalid district/seat_count")
                continue
            includes_numbered = bool(p_raw.get("includes_numbered_seat"))
            min_seats = 1 if includes_numbered else 2
            if district < 1 or seat_count < min_seats:
                errors.append(
                    f"{path}: intervals[{i}].plural_districts[{j}] seat_count must be >= {min_seats}"
                )
        ranges = seen_ranges.setdefault(postal, [])
        for prev_first, prev_last, prev_i in ranges:
            if prev_first <= last and first <= prev_last:
                errors.append(f"{path}: intervals[{i}] overlaps intervals[{prev_i}] for {postal}")
                break
        ranges.append((first, last, i))
    crosswalks = data.get("crosswalks")
    if crosswalks is not None and not isinstance(crosswalks, list):
        errors.append(f"{path}: crosswalks must be a list when present")
    import re

    seat_re = re.compile(r"^([1-9][0-9]*|[A-Z]+|[1-9][0-9]*-[A-Z]+)$")
    for i, row in enumerate(crosswalks or []):
        if not isinstance(row, dict):
            errors.append(f"{path}: crosswalks[{i}] must be an object")
            continue
        mapping = row.get("bioguide_to_seat_code")
        if not isinstance(mapping, dict) or not mapping:
            errors.append(f"{path}: crosswalks[{i}] bioguide_to_seat_code must be a non-empty object")
            continue
        for bid, code in mapping.items():
            if not str(bid or "").strip():
                errors.append(f"{path}: crosswalks[{i}] empty bioguide")
            if not seat_re.match(str(code or "").strip().upper()):
                errors.append(f"{path}: crosswalks[{i}] invalid seat_code {code!r}")
    return errors


def validate_house_legislators_term_index(data: dict[str, Any], *, path: str) -> list[str]:
    errors: list[str] = []
    fmt = int(data.get("format_version") or 0)
    if fmt not in (1, 2):
        errors.append(f"{path}: format_version must be 1 or 2")
    holds = data.get("holds_by_office")
    if not isinstance(holds, dict) or not holds:
        errors.append(f"{path}: holds_by_office must be a non-empty object")
    persons = data.get("persons")
    if not isinstance(persons, dict):
        errors.append(f"{path}: persons must be an object")
    source = data.get("source")
    if not isinstance(source, dict) or not str(source.get("upstream") or "").strip():
        errors.append(f"{path}: source.upstream is required")
    return errors


def validate_pack_payloads(repo_root: Path) -> list[str]:
    errors: list[str] = []
    validators: dict[tuple[str, str], Any] = {
        ("usg_administration_skeleton", "catalog.json"): validate_administration_catalog,
        ("usg_house_apportionment_vintages", "vintages.json"): validate_apportionment_vintages,
        ("usg_congress_session_bounds", "bounds.json"): validate_congress_bounds,
        ("usg_congress_state_seating", "seating.json"): validate_state_seating,
        ("usg_house_non_voting_delegate_seats", "delegates.json"): validate_delegate_seats,
        ("us_house_district_topology", "topology.json"): validate_house_district_topology,
        ("us_house_legislators_term_index", "term_index.json"): validate_house_legislators_term_index,
    }
    for pack_dir in discover_packs(repo_root):
        pack = load_pack_manifest(pack_dir)
        for rel in pack.get("files") or []:
            rel_s = str(rel).replace("\\", "/")
            path = pack_dir / rel_s
            if not rel_s.endswith(".json"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{path}: invalid JSON: {exc}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{path}: root must be an object")
                continue
            fn = validators.get((pack_dir.name, rel_s))
            if fn is not None:
                errors.extend(fn(data, path=rel_s))
            if pack_dir.name == "usg_statutory_cabinet_timeline" and rel_s == "timeline.json":
                errors.extend(_require_non_empty_list(data, key="departments", path=rel_s))
    return errors


def validate_repo(repo_root: Path | None = None) -> list[str]:
    root = repo_root or find_repo_root()
    errors = validate_bundle_manifest(load_bundle_manifest(root), repo_root=root)
    errors.extend(validate_pack_payloads(root))
    for pack_dir in discover_packs(root):
        try:
            collect_pack_file_hashes(pack_dir, load_pack_manifest(pack_dir))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    return errors
