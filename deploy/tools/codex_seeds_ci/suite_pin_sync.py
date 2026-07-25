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


def _is_json_slice_file(rel: object) -> bool:
    """True for files applied as AtlasReferencePackSlice rows (JSON only).

    Matches athena-codex ``atlas_seeds_apply.apply_atlas_seeds_bundle``, which skips
    non-``.json`` pack assets (e.g. ``us_person_nickname_lookup`` ``names.csv``).
    Pack manifests list relative paths as strings; there is no separate file-kind field.
    """
    return str(rel).replace("\\", "/").rsplit("/", 1)[-1].endswith(".json")


def _seeds_slice_counts(repo_root: Path) -> tuple[int, int]:
    """Return ``(pack_count, expected_slice_count)`` for suite pin sync.

    ``pack_count`` is every pack in ``manifest.yaml``. ``expected_slice_count`` counts
    only ``.json`` files — the same set ``apply_atlas_seeds_bundle`` upserts as slices.
    """
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
        slice_count += sum(1 for f in files if _is_json_slice_file(f))
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
    notes: str | None = None,
) -> None:
    root = repo_root or find_repo_root()
    if notes is None:
        # Mirror the seeds repo's own manifest.yaml notes by default (already operator-authored
        # release-summary prose); explicit callers can still override.
        manifest = load_bundle_manifest(root)
        notes = str(manifest.get("notes") or "").strip() or None
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
    if notes:
        cmd.extend(["--notes", notes])
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
    _print_safely(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def _print_safely(line: str) -> None:
    """Print without crashing on a legacy console codepage (e.g. Windows cp1252)
    choking on notes text containing non-ASCII characters like em dashes/arrows."""
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "ascii"
        print(line.encode(encoding, errors="replace").decode(encoding), flush=True)


def main() -> int:
    print("Use codex-seeds-release or codex-seeds-build-bundle --sync-suite-pin", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
