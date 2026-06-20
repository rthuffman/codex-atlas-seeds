"""CI driver: validate, pytest, build bundle, optional GitHub release."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from codex_seeds_ci.athena_venv import ensure_athena_venv, venv_python
from codex_seeds_ci.build_bundle import build_bundle
from codex_seeds_ci.manifest import validate_repo
from codex_seeds_ci.parity import _load_policy, run_parity
from codex_seeds_ci.release import release_bundle
from codex_seeds_ci.repo import find_repo_root


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def run_pytest(*, repo_root: Path, python: Path) -> None:
    tests = repo_root / "tests"
    if not tests.is_dir():
        print("skip: no tests/ directory", flush=True)
        return
    _run([str(python), "-m", "pytest", str(tests), "-q"], cwd=repo_root)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="codex-atlas-seeds CI pipeline (use athena-codex .venv — see README)."
    )
    parser.add_argument("--validate", action="store_true", help="Validate manifests and pack payloads")
    parser.add_argument("--test", action="store_true", help="Run pytest")
    parser.add_argument("--build", action="store_true", help="Build dist/*.tar.gz bundle")
    parser.add_argument("--parity", action="store_true", help="Run AS-5 parity checks")
    parser.add_argument("--release", metavar="TAG", default=None, help="Upload GitHub release for TAG")
    parser.add_argument("--draft-release", action="store_true", help="Draft GitHub release")
    parser.add_argument(
        "--sync-suite-pin",
        action="store_true",
        help="After build, update athena-codex atlas_bundles.yaml and generated pin JSON",
    )
    parser.add_argument(
        "--dry-run-suite-pin",
        action="store_true",
        help="Validate suite pin sync without writing athena-codex files",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="validate + test + build (default when no flags)",
    )
    args = parser.parse_args()

    any_flag = args.validate or args.test or args.build or args.parity or args.release
    do_validate = args.validate or args.all or not any_flag
    do_test = args.test or args.all or not any_flag
    do_build = args.build or args.all or not any_flag
    do_parity = args.parity or args.all or not any_flag

    repo_root = find_repo_root()
    athena_py = ensure_athena_venv()

    if do_validate:
        errors = validate_repo(repo_root)
        if errors:
            for msg in errors:
                print(f"error: {msg}", file=sys.stderr)
            return 1
        print("validate: ok")

    if do_test:
        run_pytest(repo_root=repo_root, python=athena_py)

    if do_build:
        archive, sidecar = build_bundle(repo_root=repo_root)
        print(f"build: {archive.name} sha256={sidecar.read_text(encoding='utf-8').strip()}")
        if args.sync_suite_pin:
            from codex_seeds_ci.manifest import load_bundle_manifest
            from codex_seeds_ci.suite_pin_sync import sync_suite_pin as _sync_suite_pin

            version = str(load_bundle_manifest(repo_root).get("bundle_version") or "").strip()
            if not version:
                print("error: manifest.yaml bundle_version is required for suite pin sync", file=sys.stderr)
                return 1
            _sync_suite_pin(
                "seeds",
                archive=archive,
                sidecar=sidecar,
                bundle_version=version,
                dry_run=args.dry_run_suite_pin,
                repo_root=repo_root,
            )

    if do_parity:
        policy = _load_policy(repo_root, None)
        code, report = run_parity(
            repo_root=repo_root,
            gold_detail_path=athena_py.parents[2] / "base-data" / "phase1-ingest-gold-detail.json",
            mode="full",
            sentinel_congresses=[118],
            sentinel_admin_years=[2021],
            reserved_prefix="72a4cd2a-fa72-774a-a73c-72587",
            output_json=repo_root / "dist" / "parity-report.json",
            output_summary_json=repo_root / "dist" / "parity-summary.json",
            policy=policy,
        )
        if code != 0:
            print("parity: FAILED", flush=True)
            print(f"report: {repo_root / 'dist' / 'parity-report.json'}", flush=True)
            return 1
        print(
            f"parity: {report['status']} ({report['counts']['diff_count']} diff(s))",
            flush=True,
        )
        legacy = report.get("legacy_exceptions") or {}
        legacy_count = int(legacy.get("count") or 0)
        if legacy_count:
            items = legacy.get("items") or []
            next_date = items[0].get("target_date") if items and isinstance(items[0], dict) else "n/a"
            playbook = repo_root / "LEGACY_EXCEPTION_RETIREMENT.md"
            print("!!! WARNING: PARITY LEGACY EXCEPTIONS ACTIVE !!!", flush=True)
            print(
                f"parity: legacy exceptions active={legacy_count} next_target_date={next_date}",
                flush=True,
            )
            print(
                "parity: exact retirement steps -> "
                f"{playbook}",
                flush=True,
            )

    if args.release:
        release_bundle(
            tag=args.release,
            repo_root=repo_root,
            draft=args.draft_release,
            dry_run_suite_pin=args.dry_run_suite_pin,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
