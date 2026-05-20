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
codex-seeds-parity
codex-seeds-ci --validate --test --build
codex-seeds-release --tag v0.1.0
codex-seeds-sync-from-athena --verify
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
| `--parity` | Run AS-5 gold-detail parity checks and write `dist/parity-report.json` + `dist/parity-summary.json` |
| `--release TAG` | Build (unless assets exist) and upload to GitHub Releases |

Default (no flags): `--validate`, `--test`, `--build`, `--parity`.

Parity policy is configured in repo-root `parity_policy.yaml` (policy format version, required pack IDs,
sentinel/full scope windows, allowed legacy exceptions, reserved ID prefix, and
pack payload -> builder fixture mapping). It also supports `catalog_only_administration_years`
and `catalog_only_congresses` for years/congresses where gold-detail equivalence is intentionally
replaced by deterministic catalog-backed invariant checks. `legacy_exceptions` metadata
(`owner`, `rationale`, `retirement_criteria`, `target_date`) is emitted into parity reports
to keep retirement work visible in CI.
