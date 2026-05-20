# Legacy Exception Retirement Playbook

This document defines the exact edits required to retire the remaining parity exception:
`Umbrella to numbered Congress`.

## Exception being retired

- Policy token: `Umbrella to numbered Congress`
- Policy location: `parity_policy.yaml`
- Metadata id: `umbrella-to-numbered-congress`

## Required code/data changes

1. **Normalize parity source or builder output**
   - Make congress membership comparison deterministic without umbrella-only extras.
   - Concretely: either remove the umbrella-only edge from the parity baseline input, or
     align builder output/parity selection so this edge no longer appears as a special case.

2. **Remove policy allowance**
   - Edit `parity_policy.yaml`:
     - remove `Umbrella to numbered Congress` from `allowed_gold_membership_extra`

3. **Remove exception metadata**
   - Edit `parity_policy.yaml`:
     - remove the `legacy_exceptions` entry with id `umbrella-to-numbered-congress`

4. **Update test expectations**
   - Edit `tests/test_parity.py`:
     - remove the assertion expecting the token in `legacy_exceptions`
     - if needed, assert `legacy_exceptions` is empty or reflects new exceptions only

5. **Re-run and confirm**
   - `python -m pytest tests -q`
   - `python -m codex_seeds_ci.parity --mode full`
   - `python -m codex_seeds_ci.pipeline --parity`

## Exit criteria

- `dist/parity-report.json` shows `legacy_exceptions.count = 0` (or only intended successors)
- `dist/parity-summary.json` shows the same
- Pipeline parity run has no legacy-exception warning banner for this token
