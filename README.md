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

**Tag push** (`v*`) is meant to re-run validate + build + parity and then **`codex-seeds-release`** to attach `dist/*.tar.gz` to GitHub Releases. **That release job does not currently work**: the workflow checks out the private **athena-codex** repository with the default Actions token and fails at checkout on every `v*` tag (observed v0.3.26 to v0.3.28). Until the workflow gets a scoped token, release **locally**: push `main` and the tag first, then run `codex-seeds-release --tag vX.Y.Z` (optionally `--skip-build --archive dist/...`) with `GITHUB_TOKEN` / `GH_TOKEN` in the process environment. The bundle build is deterministic, so the local digest equals what CI would produce.

### Deploy pin (AS-1) — after you release a new bundle

Clusters do **not** read `manifest.yaml` from this repo at runtime. **athena-codex** pins the tarball that bootstrap downloads, and that pin has **one source of truth**:

| Layer | Location | Fields |
|-------|----------|--------|
| **Committed contract** | [`codex/docs/atlas_bundles.yaml`](https://github.com/rthuffman/athena-codex/blob/main/codex/docs/atlas_bundles.yaml) → `generate-codex-ddls --commit` → generated [`codex/docs/atlas_seeds_bundle_pin.json`](https://github.com/rthuffman/athena-codex/blob/main/codex/docs/atlas_seeds_bundle_pin.json) | `bundle_version`, `bundle_sha256`, `bundle_url`, **`pack_count`**, **`expected_slice_count`**, `requires_atlas_schema_version`, release notes. Bundled into the Talisman/Athena images as `/app/ddl/atlas_seeds_bundle_pin.json`; bootstrap **Apply Atlas reference packs** and CI materialize/parity read it from there. |

The old **environment override** (`CODEX_ATLAS_SEEDS_VERSION` / `_SHA256` / `_URL` in the deploy env → Secret `talisman-db-credentials`) is **deprecated**: do not set those keys. The runtime still honours them only when present, as a rollout escape hatch; the `*-env-example` files keep them commented out for that reason.

**Bump checklist:** (1) push `main` + tag, then release **locally** with `codex-seeds-release --tag vX.Y.Z` (see CI / releases above); it runs athena-codex `codex_ci.atlas_bundle_pin_sync` for you and rewrites `atlas_bundles.yaml` + the generated pin JSON; (2) in athena-codex, verify the diff, compare `bundle_sha256` with the published `.sha256` sidecar, run `generate-codex-ddls --verify-committed`, and commit YAML + generated JSON together (hand-edit the `seeds:` block and run `generate-codex-ddls --commit` only if the automatic sync did not run); (3) rebuild + redeploy so the images carry the new `/app/ddl/atlas_seeds_bundle_pin.json`; (4) Talisman bootstrap **Apply Atlas reference packs**. Full procedure: athena-codex `docs/operations/atlas-bundle-release-and-pin-runbook.html` Part A.

Policy: [`2026-05-20-codex-atlas-seeds-reference-packs`](https://github.com/rthuffman/athena-codex/blob/main/docs/decisions/2026-05-20-codex-atlas-seeds-reference-packs.md) (**AS-1**). Example env comments: `deploy/kubernetes/deploy-local-dev.env-example` § Atlas reference packs.

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

**Current release:** [`v0.3.28`](https://github.com/rthuffman/codex-atlas-seeds/releases/tag/v0.3.28) — `us_person_nickname_lookup` 0.2.0 (carltonnorthern `names.csv` at upstream 1524308b68, 2026-08-02) on top of v0.3.27 (**18** packs). Earlier highlights below are retained for history.

**Deploy pin (single source of truth):** athena-codex `codex/docs/atlas_bundles.yaml` → generated `atlas_seeds_bundle_pin.json`, written automatically by `codex-seeds-release` (see **Deploy pin (AS-1)** above). No deploy-env keys.

**Bundle `0.3.7`** (twelve packs) — highlights since `0.3.1`:

| Pack | Notes |
|------|--------|
| `us_house_district_topology` | Schema v2 reviewed rows (v0.3.4+); Civil War 36-41 operator-gold corrections (v0.3.7) |
| `us_house_legislators_term_index` | format_version 2 + topology-aware seat codes (v0.3.2+); regenerated after Civil War topology patch (v0.3.7) |
| `usg_congress_session_readiness` | Gate C operator certification catalog (v0.3.6) |
| *(earlier v0.3.x)* | `us_geo_bootstrap`, `us_gold_current_structure`, `us_gold_historical_structure`, six USG catalog packs |

Refresh catalog packs: `python scripts/with_athena_venv.py codex-seeds-sync-from-athena --verify`.  
Refresh Prospectus projection packs: `python scripts/with_athena_venv.py codex-seeds-sync-from-athena --export-prospectus-packs`.  
Tag release: `codex-seeds-release --tag v0.3.7`.

Bootstrap: apply Atlas bundle in talisman-bootstrap, then **Project Atlas seeds → Prospectus** (Option B).

Data stability work tracker: [`DATA_COMPLETENESS_CHECKLIST.md`](DATA_COMPLETENESS_CHECKLIST.md).
