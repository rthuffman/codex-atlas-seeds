# codex-atlas-seeds

Versioned **Atlas reference packs** (flat interchange + release bundles) for the Codex suite.

**Policy ADR:** [athena-codex `docs/decisions/2026-05-20-codex-atlas-seeds-reference-packs.md`](https://github.com/rthuffman/athena-codex/blob/main/docs/decisions/2026-05-20-codex-atlas-seeds-reference-packs.md)

## Role

- **Authoritative blueprints** in **Atlas** (isolated subgraphs per pack; no inter-pack graph edges).
- **Prospectus** = materialized “houses” (Artemis projection / structure jobs).
- **Releases** = downloadable `.tar.gz` + checksums for bootstrap and installers.

## Tooling (same pattern as athena-codex `codex-ci`)

CI lives in **`deploy/tools/`** (`codex-seeds-ci` package). Use the **athena-codex** virtualenv so Python version and dependencies stay aligned when switching repos.

### One-time setup

`scripts/with_athena_venv.py` bootstraps the **athena-codex** venv (if needed), installs **`codex-seeds-ci`** editable, and runs a CLI. Optional: set `ATHENA_CODEX_ROOT` to your athena-codex clone; otherwise `../athena-codex` is used.

```bash
cd d:\repos\codex-atlas-seeds
python scripts/with_athena_venv.py codex-seeds-ci --all
```

To install only (without the helper):

```bash
python d:\repos\athena-codex\scripts\bootstrap_athena_codex_venv.py
set ATHENA_CODEX_ROOT=d:\repos\athena-codex
d:\repos\athena-codex\.venv\Scripts\python.exe -m pip install -e "./deploy/tools"
```

### Common commands

```bash
python scripts/with_athena_venv.py codex-seeds-validate
python scripts/with_athena_venv.py codex-seeds-ci --all
python scripts/with_athena_venv.py codex-seeds-sync-from-athena
python scripts/with_athena_venv.py codex-seeds-release --tag v0.1.0
```

### Layout

```
manifest.yaml              # bundle index (pack list + bundle_version)
packs/
  <pack_id>/
    pack.yaml
    *.json / *.csv         # pack payloads
deploy/tools/              # codex-seeds-ci (pip install -e)
tests/
dist/                      # build output (gitignored)
```

## CI / releases

`.github/workflows/codex-seeds-ci.yml` checks out **athena-codex** (for venv bootstrap), installs **`codex-seeds-ci`**, runs validate + test + build.

**Tag push** (`v*`) runs the same pipeline and **`codex-seeds-release`** to attach `dist/*.tar.gz` to GitHub Releases. You can also run release upload locally with `GITHUB_TOKEN` set.

Pin consumed bundles in **athena-codex** deploy manifests (`version` + `sha256`) — not in application Docker images.

## Status

**Bundle `0.2.0`** (six USG packs, synced from `athena/docs/fixtures/usg-structure/`):

| Pack | Payload |
|------|---------|
| `usg_administration_skeleton` | 50 administrations (1789 → 2025) |
| `usg_statutory_cabinet_timeline` | Department era map |
| `usg_house_apportionment_vintages` | Apportionment 1st–130th |
| `usg_congress_session_bounds` | Congress DoB/DoE hints |
| `usg_congress_state_seating` | Civil War seating mask (37th–41st) |
| `usg_house_non_voting_delegate_seats` | Territorial delegates |

Refresh from athena-codex: `python scripts/with_athena_venv.py codex-seeds-sync-from-athena` (optional `--regenerate-catalog`). Tag release: `codex-seeds-release --tag v0.2.0`.

Atlas populate / Artemis ilink read paths are follow-ups in athena-codex (bootstrap bundle pin).
