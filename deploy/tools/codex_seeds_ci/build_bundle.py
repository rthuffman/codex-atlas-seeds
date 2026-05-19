"""Build deterministic release bundle (.tar.gz) with SHA256SUMS."""

from __future__ import annotations

import argparse
import io
import tarfile
from pathlib import Path
from typing import Any

import yaml

from codex_seeds_ci.manifest import (
    collect_pack_file_hashes,
    discover_packs,
    file_sha256,
    load_bundle_manifest,
    load_pack_manifest,
)
from codex_seeds_ci.repo import find_repo_root


def _tar_add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> str:
    arc = arcname.replace("\\", "/")
    info = tarfile.TarInfo(name=arc)
    info.size = len(data)
    info.mtime = 0
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))
    return file_sha256_from_bytes(data)


def file_sha256_from_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def build_release_manifest(repo_root: Path) -> dict[str, Any]:
    base = load_bundle_manifest(repo_root)
    packs_out: list[dict[str, Any]] = []
    for pack_dir in discover_packs(repo_root):
        pack = load_pack_manifest(pack_dir)
        hashes = collect_pack_file_hashes(pack_dir, pack)
        packs_out.append(
            {
                "pack_id": pack_dir.name,
                "version": str(pack.get("version") or ""),
                "requires_atlas_schema_version": str(
                    pack.get("requires_atlas_schema_version")
                    or base.get("requires_atlas_schema_version")
                    or ""
                ),
                "files": [{"path": rel, "sha256": digest} for rel, digest in sorted(hashes.items())],
            }
        )
    return {
        "bundle_format_version": 1,
        "bundle_version": str(base.get("bundle_version") or ""),
        "requires_atlas_schema_version": str(base.get("requires_atlas_schema_version") or ""),
        "repository": "https://github.com/rthuffman/codex-atlas-seeds",
        "packs": packs_out,
    }


def build_bundle(*, repo_root: Path | None = None, output: Path | None = None) -> tuple[Path, Path]:
    root = repo_root or find_repo_root()
    base = load_bundle_manifest(root)
    version = str(base.get("bundle_version") or "0.0.0")
    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    archive = output or (dist / f"codex-atlas-seeds-{version}.tar.gz")

    release_manifest = build_release_manifest(root)
    manifest_bytes = yaml.safe_dump(release_manifest, sort_keys=False, allow_unicode=True).encode("utf-8")
    checksum_lines: list[str] = []

    with tarfile.open(archive, "w:gz", format=tarfile.GNU_FORMAT) as tar:
        for pack_dir in discover_packs(root):
            pack = load_pack_manifest(pack_dir)
            for rel in pack.get("files") or []:
                rel_s = str(rel).replace("\\", "/")
                src = pack_dir / rel_s
                data = src.read_bytes()
                arc = f"packs/{pack_dir.name}/{rel_s}"
                digest = _tar_add_bytes(tar, arc, data)
                checksum_lines.append(f"{digest}  {arc}")
            pack_yaml = pack_dir / "pack.yaml"
            py_data = pack_yaml.read_bytes()
            arc_pack = f"packs/{pack_dir.name}/pack.yaml"
            digest = _tar_add_bytes(tar, arc_pack, py_data)
            checksum_lines.append(f"{digest}  {arc_pack}")

        digest = _tar_add_bytes(tar, "manifest.release.yaml", manifest_bytes)
        checksum_lines.append(f"{digest}  manifest.release.yaml")

        sums_text = ("\n".join(sorted(checksum_lines)) + "\n").encode("utf-8")
        digest = _tar_add_bytes(tar, "SHA256SUMS", sums_text)
        checksum_lines.append(f"{digest}  SHA256SUMS")

    sidecar = archive.with_suffix(".tar.gz.sha256")
    sidecar.write_text(file_sha256(archive) + "\n", encoding="utf-8")
    return archive, sidecar


def main() -> int:
    parser = argparse.ArgumentParser(description="Build codex-atlas-seeds release .tar.gz bundle.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output archive path (default: dist/codex-atlas-seeds-<bundle_version>.tar.gz)",
    )
    args = parser.parse_args()
    archive, sidecar = build_bundle(output=args.output)
    print(f"Wrote {archive}")
    print(f"Wrote {sidecar} ({sidecar.read_text(encoding='utf-8').strip()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
