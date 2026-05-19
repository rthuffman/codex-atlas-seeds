# codex-seeds-ci

Python CI for **codex-atlas-seeds**: validate pack sources, build deterministic release bundles, upload **GitHub Releases**.

Requires **Python 3.14.3** (use the **athena-codex** repo `.venv` — see repo root `README.md`).

## Install (athena-codex venv)

From **codex-atlas-seeds** root (sibling `athena-codex` clone recommended):

```bash
python scripts/with_athena_venv.py codex-seeds-ci --all
```

Or install explicitly:

```bash
python ../athena-codex/scripts/bootstrap_athena_codex_venv.py
../athena-codex/.venv/bin/python -m pip install -e "./deploy/tools"
```

## CLI

```bash
codex-seeds-validate
codex-seeds-run-unit-tests
codex-seeds-build-bundle
codex-seeds-ci --validate --test --build
codex-seeds-release --tag v0.1.0
codex-seeds-sync-from-athena
```

Or:

```bash
python -m codex_seeds_ci.pipeline --all
```

**Release upload** needs `GITHUB_TOKEN` (or `GH_TOKEN`) and optionally [GitHub CLI](https://cli.github.com/) (`gh`). Set `CODEX_SEEDS_FORCE_GITHUB_API=1` to skip `gh` and use the REST API.

## Pipeline driver

`codex-seeds-ci` is the entry point for local runs and for `.github/workflows/codex-seeds-ci.yml`:

| Flag | Action |
|------|--------|
| `--validate` | Check `manifest.yaml` and pack payloads |
| `--test` | `pytest` under `tests/` |
| `--build` | Write `dist/codex-atlas-seeds-<version>.tar.gz` + `.sha256` sidecar |
| `--release TAG` | Build (unless assets exist) and upload to GitHub Releases |

Default (no flags): `--validate`, `--test`, `--build`.
