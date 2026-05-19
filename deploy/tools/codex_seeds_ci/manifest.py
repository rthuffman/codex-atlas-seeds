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


def validate_pack_payloads(repo_root: Path) -> list[str]:
    errors: list[str] = []
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
            if pack_dir.name == "usg_administration_skeleton" and rel_s == "catalog.json":
                if isinstance(data, dict):
                    errors.extend(validate_administration_catalog(data, path=rel_s))
            if pack_dir.name == "usg_statutory_cabinet_timeline" and rel_s == "timeline.json":
                deps = data.get("departments") if isinstance(data, dict) else None
                if not isinstance(deps, list) or not deps:
                    errors.append(f"{path}: departments must be a non-empty list")
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
