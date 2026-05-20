#!/usr/bin/env python3
"""
Run codex-seeds-ci entrypoints using the athena-codex repo .venv.

Examples::

    python scripts/with_athena_venv.py
    python scripts/with_athena_venv.py codex-seeds-validate
    python scripts/with_athena_venv.py codex-seeds-ci --all
    python scripts/with_athena_venv.py codex-seeds-release --tag v0.1.0

Set ``ATHENA_CODEX_ROOT`` to the athena-codex clone, or place it beside this repo as ``../athena-codex``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SEEDS_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_TOOLS = SEEDS_ROOT / "deploy" / "tools"

# Console script name -> ``python -m`` module (fallback if script shim missing).
_CLI_MODULES: dict[str, str] = {
    "codex-seeds-validate": "codex_seeds_ci.validate",
    "codex-seeds-build-bundle": "codex_seeds_ci.build_bundle",
    "codex-seeds-release": "codex_seeds_ci.release",
    "codex-seeds-ci": "codex_seeds_ci.pipeline",
    "codex-seeds-run-unit-tests": "codex_seeds_ci.unit_tests",
    "codex-seeds-sync-from-athena": "codex_seeds_ci.migrate_from_athena",
    "codex-seeds-parity": "codex_seeds_ci.parity",
}


def _athena_codex_root() -> Path:
    import os

    raw = (os.environ.get("ATHENA_CODEX_ROOT") or os.environ.get("CODEX_ATHENA_ROOT") or "").strip()
    if raw:
        return Path(raw).resolve()
    sibling = SEEDS_ROOT.parent / "athena-codex"
    if (sibling / "scripts" / "bootstrap_athena_codex_venv.py").is_file():
        return sibling.resolve()
    raise FileNotFoundError(
        "athena-codex not found. Clone beside codex-atlas-seeds or set ATHENA_CODEX_ROOT."
    )


def _venv_python(athena_root: Path) -> Path:
    if sys.platform == "win32":
        return athena_root / ".venv" / "Scripts" / "python.exe"
    return athena_root / ".venv" / "bin" / "python"


def _ensure_venv(athena_root: Path) -> Path:
    py = _venv_python(athena_root)
    if py.is_file():
        return py
    bootstrap = athena_root / "scripts" / "bootstrap_athena_codex_venv.py"
    subprocess.run([sys.executable, str(bootstrap)], cwd=athena_root, check=True)
    if not py.is_file():
        raise FileNotFoundError(f"venv still missing after bootstrap: {py}")
    return py


def _pip_install_editable(py: Path) -> None:
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", "-e", str(DEPLOY_TOOLS)],
        cwd=SEEDS_ROOT,
        check=True,
    )


def _console_script_path(py: Path, name: str) -> Path | None:
    scripts = py.parent
    if sys.platform == "win32":
        candidate = scripts / f"{name}.exe"
    else:
        candidate = scripts / name
    return candidate if candidate.is_file() else None


def _run_command(py: Path, command: str, args: list[str]) -> int:
    shim = _console_script_path(py, command)
    if shim is not None:
        return subprocess.run([str(shim), *args], cwd=SEEDS_ROOT).returncode
    module = _CLI_MODULES.get(command)
    if module is None:
        print(f"unknown command: {command}", file=sys.stderr)
        print(f"known: {', '.join(sorted(_CLI_MODULES))}", file=sys.stderr)
        return 2
    return subprocess.run([str(py), "-m", module, *args], cwd=SEEDS_ROOT).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run codex-seeds-ci via athena-codex .venv (installs editable deploy/tools first)."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="codex-seeds-ci",
        help="CLI name (default: codex-seeds-ci)",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the CLI")
    parsed = parser.parse_args(argv)
    cli_args = list(parsed.args)
    if cli_args and cli_args[0] == "--":
        cli_args = cli_args[1:]
    athena = _athena_codex_root()
    py = _ensure_venv(athena)
    _pip_install_editable(py)
    if parsed.command == "codex-seeds-ci" and not cli_args:
        cli_args = ["--all"]
    return _run_command(py, parsed.command, cli_args)


if __name__ == "__main__":
    raise SystemExit(main())
