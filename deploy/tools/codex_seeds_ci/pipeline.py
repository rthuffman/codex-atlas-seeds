"""CI driver: validate, pytest, build bundle, optional GitHub release."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from codex_seeds_ci.athena_venv import ensure_athena_venv, venv_python
from codex_seeds_ci.build_bundle import build_bundle
from codex_seeds_ci.manifest import validate_repo
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
    parser.add_argument("--release", metavar="TAG", default=None, help="Upload GitHub release for TAG")
    parser.add_argument("--draft-release", action="store_true", help="Draft GitHub release")
    parser.add_argument(
        "--all",
        action="store_true",
        help="validate + test + build (default when no flags)",
    )
    args = parser.parse_args()

    any_flag = args.validate or args.test or args.build or args.release
    do_validate = args.validate or args.all or not any_flag
    do_test = args.test or args.all or not any_flag
    do_build = args.build or args.all or not any_flag

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

    if args.release:
        release_bundle(tag=args.release, repo_root=repo_root, draft=args.draft_release)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
