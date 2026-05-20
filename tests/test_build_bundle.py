"""Release bundle build determinism."""

from __future__ import annotations

import hashlib
import tarfile

from codex_seeds_ci.build_bundle import build_bundle
from codex_seeds_ci.repo import find_repo_root


def _member_digest_map(archive: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            data = tar.extractfile(member)
            assert data is not None
            out[member.name] = hashlib.sha256(data.read()).hexdigest()
    return out


def test_build_bundle_deterministic(tmp_path) -> None:
    root = find_repo_root()
    out1 = tmp_path / "a.tar.gz"
    out2 = tmp_path / "b.tar.gz"
    build_bundle(repo_root=root, output=out1)
    build_bundle(repo_root=root, output=out2)
    assert _member_digest_map(out1) == _member_digest_map(out2)


def test_bundle_contains_manifest_and_sums(tmp_path) -> None:
    root = find_repo_root()
    archive, _ = build_bundle(repo_root=root, output=tmp_path / "bundle.tar.gz")
    names: list[str] = []
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert "manifest.release.yaml" in names
    assert "SHA256SUMS" in names
    assert any(n.startswith("packs/usg_administration_skeleton/") for n in names)
    assert any(n.startswith("packs/usg_house_apportionment_vintages/") for n in names)
