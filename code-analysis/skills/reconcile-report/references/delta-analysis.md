# Delta Analysis Protocol

Run this step when `PREVIOUS_SCORES` is not null. Compare current findings against the prior run to classify each finding as new, resolved, or unchanged.

## Finding Comparison Logic

With fingerprint-based IDs, delta analysis is reliable:

- **Resolved**: IDs in PREVIOUS_SCORES findings but not in current — genuinely fixed
- **New**: IDs in current but not in PREVIOUS_SCORES — genuinely new issues
- **Unchanged**: IDs present in both — persistent issues

## Handling Merged IDs

During dedup (Step 1), findings may be merged. Handle resolved_ids from carry_forward_summary correctly:

1. Build mapping: `{original_scanner_id → merged_id}` from dedup table
2. Check both original and merged IDs when computing deltas
3. A finding is "resolved" if its scanner ID is in `carry_forward_summary.resolved_ids`, even if PREVIOUS_SCORES stored a different merged ID
4. Include both scanner ID and mapped merged ID in `resolved_finding_ids`

## Old-Format Detection

If ANY finding ID in PREVIOUS_SCORES matches `^[a-z-]+-\d{3}$` (old sequential format), treat the entire previous report as old-format and skip delta comparison (all findings treated as "new").

## v0.6-to-v0.7 ID Prefix Migration

If PREVIOUS_SCORES contains finding IDs with old dimension prefixes (`ARCH-`, `PAT-`, `DEBT-`, `PERF-`, `DEP-`), map them for delta comparison:

| Old Prefix | New Prefix |
|------------|------------|
| `ARCH-*` | `STRC-*` |
| `PAT-*` | `STRC-*` |
| `DEBT-*` | `QUAL-*` |
| `PERF-*` | `QUAL-*` |
| `DEP-*` | `SEC-*` or `TST-*` |

If old 8-dimension names appear in `PREVIOUS_SCORES.dimension_scores`, skip delta for those dimensions (dimension count mismatch).

## Report Output

Add a "Run Delta" section to the report with new, resolved, unchanged counts and score deltas.

Produce a `RunDelta` object matching the schema in `output-schemas.md`.
