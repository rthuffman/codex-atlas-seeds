"""Invoke athena-codex suite pin sync after bundle build/release."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Literal

from codex_seeds_ci.athena_venv import athena_codex_root, ensure_athena_venv
from codex_seeds_ci.manifest import load_bundle_manifest
from codex_seeds_ci.repo import find_repo_root

BundleKind = Literal["seeds", "reference"]


def _ensure_codex_ci_installed(python: Path) -> None:
    athena_root = athena_codex_root()
    deploy_tools = athena_root / "deploy" / "tools"
    subprocess.run(
        [str(python), "-m", "pip", "install", "-q", "-e", str(deploy_tools)],
        check=True,
    )


def _seeds_slice_counts(repo_root: Path) -> tuple[int, int]:
    manifest = load_bundle_manifest(repo_root)
    packs = manifest.get("packs")
    if not isinstance(packs, list) or not packs:
        raise ValueError(f"{repo_root / 'manifest.yaml'}: packs must be a non-empty list")
    pack_count = 0
    slice_count = 0
    for idx, raw in enumerate(packs):
        if not isinstance(raw, dict):
            raise ValueError(f"manifest.yaml packs[{idx}] must be a mapping")
        files = raw.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError(f"manifest.yaml packs[{idx}].files must be a non-empty list")
        pack_count += 1
        slice_count += len(files)
    return pack_count, slice_count


def sync_suite_pin(
    kind: BundleKind,
    *,
    archive: Path,
    sidecar: Path,
    bundle_version: str,
    tag: str | None = None,
    dry_run: bool = False,
    repo_root: Path | None = None,
) -> None:
    root = repo_root or find_repo_root()
    python = ensure_athena_venv()
    _ensure_codex_ci_installed(python)
    cmd = [
        str(python),
        "-m",
        "codex_ci.atlas_bundle_pin_sync",
        "--kind",
        kind,
        "--archive",
        str(archive.resolve()),
        "--sidecar",
        str(sidecar.resolve()),
        "--bundle-version",
        bundle_version,
    ]
    if tag:
        cmd.extend(["--tag", tag])
    if dry_run:
        cmd.append("--dry-run")
    if kind == "seeds":
        pack_count, expected_slice_count = _seeds_slice_counts(root)
        cmd.extend(
            [
                "--pack-count",
                str(pack_count),
                "--expected-slice-count",
                str(expected_slice_count),
            ]
        )
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    print("Use codex-seeds-release or codex-seeds-build-bundle --sync-suite-pin", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
