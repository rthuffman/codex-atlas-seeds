"""Pack and bundle manifest validation."""

from __future__ import annotations

from codex_seeds_ci.manifest import load_bundle_manifest, validate_repo
from codex_seeds_ci.repo import find_repo_root


def test_validate_repo_clean() -> None:
    errors = validate_repo(find_repo_root())
    assert errors == []


def test_bundle_has_two_packs() -> None:
    manifest = load_bundle_manifest(find_repo_root())
    assert len(manifest["packs"]) == 2
