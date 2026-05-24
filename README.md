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
python scripts/with_athena_venv.py codex-seeds-parity --mode full
python scripts/with_athena_venv.py codex-seeds-sync-from-athena --export-prospectus-packs
```

### Stable reference policy (v0.3.0+)

Once geo, gold-current structure, or historical congress scaffolding is **canonical**, edits belong **only in this repo** — not by regenerating primary artifacts in athena-codex. Export tooling (`export_atlas_prospectus_packs.py` / `--export-prospectus-packs`) is for migration and parity only. See athena-codex ADR [`2026-05-21-atlas-seeds-stable-reference-one-way-policy.md`](https://github.com/rthuffman/athena-codex/blob/main/docs/decisions/2026-05-21-atlas-seeds-stable-reference-one-way-policy.md).

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

`.github/workflows/codex-seeds-ci.yml` checks out **athena-codex** (for venv bootstrap), installs **`codex-seeds-ci`**, runs validate + test + build + parity.

**Tag push** (`v*`) re-runs validate + build + parity and then **`codex-seeds-release`** to attach `dist/*.tar.gz` to GitHub Releases. You can also run release upload locally with `GITHUB_TOKEN` set.

Pin consumed bundles in **athena-codex** deploy manifests (`version` + `sha256`) — not in application Docker images.

## Consumption in athena-codex

| Stage | Where |
|-------|--------|
| **Atlas runtime** | `AtlasReferencePackSlice` rows after talisman-bootstrap **Apply Atlas reference packs** |
| **Prospectus runtime** | **Project Atlas seeds → Prospectus** reads three projection slices + merges records ([`atlas_prospectus_bootstrap.ts`](https://github.com/rthuffman/athena-codex/blob/main/talisman/src/lib/atlas_prospectus_bootstrap.ts)) |
| **Artemis structure jobs** | Catalog packs via Athena ilink / Atlas slices (apportionment, bounds, admin catalog, …) |
| **Legacy / DR** | [`phase1-ingest-gold-current.json`](https://github.com/rthuffman/athena-codex/blob/main/base-data/phase1-ingest-gold-current.json) export — not authoritative after v0.3.0 |

Runbook: [athena-codex `docs/prospectus-environment-first-setup.md`](https://github.com/rthuffman/athena-codex/blob/main/docs/prospectus-environment-first-setup.md) Phase **0.3a**, **0.4a**, **1B**.

## Roadmap (not in this repo alone)

- **AS-2b:** Operator pack-apply / export Atlas → git without full cluster reinstall
- **AS-5:** Delegation-aware parity vs `gold-detail` (congress 118 full compare)
- **AS-6:** Big-bang orchestrator gate on Atlas pack pin before structure fan-out
- **SOC pack:** `soc_occupation_definitions_2018` in bundle (definitions CSV only)
- **Sunset:** direct `gold-current.json` bootstrap where Atlas projection is available (Talisman imports page labels legacy path)

## Status

**Release [`v0.3.0`](https://github.com/rthuffman/codex-atlas-seeds/releases/tag/v0.3.0)** published **2026-05-24**. Pin in athena-codex: [`codex/docs/atlas_seeds_bundle_pin.json`](https://github.com/rthuffman/athena-codex/blob/main/codex/docs/atlas_seeds_bundle_pin.json).

**Bundle `0.3.0`** (nine USG packs):

| Pack | Payload |
|------|---------|
| *(v0.2.0 catalog packs)* | administration, cabinet timeline, apportionment, session bounds, seating, delegates |
| `us_geo_bootstrap` | NationState, 50 states, territories, DC, federal apex (220 records) |
| `us_gold_current_structure` | 119th Congress + 47th administration shell (1527 records, no geo) |
| `us_gold_historical_structure` | 1st–118th Congress session org scaffolding (391 records) |

Refresh catalog packs: `python scripts/with_athena_venv.py codex-seeds-sync-from-athena --verify`.  
Refresh Prospectus projection packs: `python scripts/with_athena_venv.py codex-seeds-sync-from-athena --export-prospectus-packs`.  
Tag release: `codex-seeds-release --tag v0.3.0`.

Bootstrap: apply Atlas bundle in talisman-bootstrap, then **Project Atlas seeds → Prospectus** (Option B).

Pin consumed bundles in **athena-codex** (`codex/docs/atlas_seeds_bundle_pin.json`).

Data stability work tracker: [`DATA_COMPLETENESS_CHECKLIST.md`](DATA_COMPLETENESS_CHECKLIST.md).
