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
