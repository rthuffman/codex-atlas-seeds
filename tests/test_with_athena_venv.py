"""Regression tests for the athena-codex venv wrapper."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def _load_wrapper(repo_root: Path) -> ModuleType:
    module_path = repo_root / "scripts" / "with_athena_venv.py"
    spec = importlib.util.spec_from_file_location("with_athena_venv", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_known_seed_command_uses_python_module_even_when_shim_exists(
    tmp_path: Path, monkeypatch
) -> None:
    """Avoid racing Windows console-script .exe shims during normal wrapper runs."""

    repo_root = Path(__file__).resolve().parents[1]
    wrapper = _load_wrapper(repo_root)
    py = tmp_path / "Scripts" / "python.exe"
    py.parent.mkdir(parents=True)
    py.write_text("", encoding="utf-8")
    shim = py.parent / "codex-seeds-validate.exe"
    shim.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        calls.append([str(part) for part in cmd])
        return SimpleNamespace(returncode=17)

    monkeypatch.setattr(wrapper.sys, "platform", "win32")
    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)

    assert wrapper._run_command(py, "codex-seeds-validate", ["--strict"]) == 17
    assert calls == [[str(py), "-m", "codex_seeds_ci.validate", "--strict"]]


def test_tools_install_skips_pip_when_package_imports(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = _load_wrapper(repo_root)
    py = tmp_path / "python"
    py.write_text("", encoding="utf-8")

    monkeypatch.setattr(wrapper, "_codex_seeds_ci_importable", lambda _py: True)

    def fail_install(_py):
        raise AssertionError("pip install should be skipped when codex_seeds_ci imports")

    monkeypatch.setattr(wrapper, "_pip_install_editable", fail_install)

    wrapper._ensure_tools_installed(py, reinstall=False)


def test_tools_install_can_be_forced(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = _load_wrapper(repo_root)
    py = tmp_path / "python"
    py.write_text("", encoding="utf-8")
    installed: list[Path] = []

    monkeypatch.setattr(wrapper, "_codex_seeds_ci_importable", lambda _py: True)
    monkeypatch.setattr(wrapper, "_pip_install_editable", lambda value: installed.append(value))

    wrapper._ensure_tools_installed(py, reinstall=True)

    assert installed == [py]


def test_import_check_uses_venv_python(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = _load_wrapper(repo_root)
    py = tmp_path / "python"
    py.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append([str(part) for part in cmd])
        assert kwargs["cwd"] == wrapper.SEEDS_ROOT
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)

    assert wrapper._codex_seeds_ci_importable(py) is True
    assert calls == [[str(py), "-c", "import codex_seeds_ci"]]
