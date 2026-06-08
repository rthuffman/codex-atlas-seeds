# USG Administration Data Completeness Checklist

Baseline objective: stable and complete administration skeleton coverage from `1789` to present,
with reproducible CI gates that prevent regressions.

## Immediate stabilization

- [x] Add explicit `2013` administration row to seeds artifact catalog.
- [x] Add policy guard for required inauguration years (`parity_policy.yaml`).
- [x] Enforce required-year validation in parity runner (`codex_seeds_ci.parity`).
- [x] Add test coverage for `2013` presence in pack payload and policy scope.

## Upstream source integrity (athena-codex)

- [x] Update `generate_administration_catalog.py` to split long inauguration-based presidencies
  into 4-year term rows (adds missing term starts like `2013`).
- [x] Regenerate `athena/docs/fixtures/usg-structure/us_administration_skeleton_catalog.json`.
- [x] Sync regenerated fixture into `packs/usg_administration_skeleton/catalog.json`.

## CI and release safeguards

- [x] Run parity in active PR/build path (`codex-seeds-ci` workflow).
- [x] Run parity in release path before upload.
- [x] Emit deterministic machine-readable artifacts:
  - `dist/parity-report.json`
  - `dist/parity-summary.json`
- [x] Keep staged PR parity workflow disabled-by-default (`*.yml.disabled`).

## Follow-up hardening

- [x] Expand `full` parity scope windows beyond current certified set with cross-era
  administration checkpoints (`1789`, `1841`, `1865`, `1901`, `1945`, `2009`, `2013`, `2021`, `2025`).
- [x] Expand `full` congress checkpoints across eras (`1`, `40`, `80`, `100`, `118`) using
  policy-based `catalog_only_congresses` for pre-gold congresses and strict gold parity where available.
- [x] Add explicit policy notes for legacy exceptions and target removal date, and surface
  those in parity report/summary artifacts for CI visibility.
- [x] Add sync command guard mode (`codex-seeds-sync-from-athena --verify`) that fails if required
  catalog years/pack invariants are lost after copy.

## v0.3.0 Prospectus projection packs (2026-05-21)

- [x] Add **`us_geo_bootstrap`**, **`us_gold_current_structure`**, **`us_gold_historical_structure`** to bundle manifest (nine packs total).
- [x] Export path from athena-codex (`export_atlas_prospectus_packs.py` / `--export-prospectus-packs`).
- [x] Parity policy: projection packs in **`required_packs`** but **not** in **`builder_fixture_mappings`** (AS-5 catalog parity only).
- [x] Publish GitHub Release **`v0.3.0`** and verify athena-codex pin SHA matches release asset (**2026-05-24**).
- [x] Prepare **`v0.3.1`** bundle removing stale optional `L1`/`L2`/`L3` projection fields so Athena derives taxonomy from current schema.
- [ ] AS-5: delegation-aware full parity for congress **118** vs gold-detail (retire catalog-only workaround).
- [ ] Document pack changelog when stable reference edits (e.g. jurisdictional splits) land in seeds repo only.

## v0.3.3/v0.3.4 House district topology + term index v2 (2026-06-07)

**Seeds authoring repo (local clone):** `D:\repos\codex-atlas-seeds`

**Ordering:** complete P1+ topology research **before** publishing the bundle so the release artifact is complete; then commit → push → tag → GitHub release; **then** bump athena-codex deploy pin (`atlas_seeds_bundle_pin.json` + `CODEX_ATLAS_SEEDS_*` in deploy dotenv/SOPS) and run cluster rebuild.

- [x] **v0.3.3 superseded/tainted:** inferred 368-row topology blurred plural districts and statewide at-large seats.
- [x] **v0.3.4 corrective source audit:** schema v2 reviewed rows only; explicit plural district seats (e.g. `1-A`) and source metadata in `base-data/sources/usg/house_district_topology_overrides.json`.
- [x] athena-codex Phase C — topology module, session builder, term index format_version 2, vacancy `seat_code` (ADR 2026-06-07).
- [x] Add `packs/us_house_district_topology/` (`pack.yaml`, `topology.json`, `sources/state_intervals_research.json`).
- [x] Regenerate `packs/us_house_legislators_term_index/term_index.json` with topology slice (format_version 2).
- [x] Bump `manifest.yaml` to **v0.3.4** (11 packs); schema-v2 validator rejects v1/unsafe topology.
- [x] Release: commit, push, tag **v0.3.3**, `codex-seeds-release --tag v0.3.3` — https://github.com/rthuffman/codex-atlas-seeds/releases/tag/v0.3.3
- [x] athena-codex: update `codex/docs/atlas_seeds_bundle_pin.json` (version, sha256, url, `pack_count`) **and** matching `CODEX_ATLAS_SEEDS_VERSION` / `SHA256` / `URL` in deploy env (`deploy-local-dev.env`, `deploy-local-dev.env-example`, or SOPS `deploy-dev.env` for dev clusters).
- [ ] Cluster: re-apply Atlas seeds (11 slices); Prospectus wipe + structural backfill; vacancy spot-checks.
