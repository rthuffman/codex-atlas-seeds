"""Run codex-atlas-seeds pytest (athena-codex venv)."""

from __future__ import annotations

import argparse

from codex_seeds_ci.athena_venv import ensure_athena_venv
from codex_seeds_ci.pipeline import run_pytest
from codex_seeds_ci.repo import find_repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Run codex-atlas-seeds unit tests.")
    parser.parse_args()
    root = find_repo_root()
    run_pytest(repo_root=root, python=ensure_athena_venv())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
