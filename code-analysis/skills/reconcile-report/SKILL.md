---
name: reconcile-report
version: 0.7.0
description: |
  This skill should be used when the user asks to "reconcile findings", "deduplicate cross-dimension results",
  "assemble unified report", or when performing cross-dimension deduplication, scoring, and unified report assembly.
  Loaded by the report-reconciler agent.
allowed-tools: ["Read", "Write", "Glob", "Grep"]
---

# Reconcile Report

## Purpose

Deduplicate findings across dimensions, compute numeric scores, and produce a unified analysis report with a codebase health score.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `FINDINGS_BY_DIMENSION`: Object mapping dimension names to their findings arrays
- `STACK`: Detected language/framework
- `PROJECT_PATH`: Root directory of the project
- `WEIGHTS`: Optional object mapping dimension names to weight values (default: all 1.0)
- `CRITIC_FEEDBACK`: Optional CriticFeedback from a prior iteration (null on first run)
- `PREVIOUS_SCORES`: Optional ScoresReport from a prior run (null if first scan) — enables delta analysis
- `OVERRIDES`: Optional content of `.code-analysis/overrides.json` (null if file does not exist)

## Reconciliation Workflow

### Step 0 — Apply Overrides (if OVERRIDES provided)

If `OVERRIDES` is not null:

1. Parse the override file for `false_positives` and `wont_fix` arrays
2. **`false_positives`**: Remove matching finding IDs entirely from all dimension findings arrays before any processing. These findings are excluded from dedup, scoring, and the report.
3. **`wont_fix`**: Keep the finding in the report but tag it `[WONT-FIX]`; exclude it from score calculation (treat as if it were `info` severity for scoring purposes)
4. Log counts: `"X findings suppressed as false_positives, Y findings marked as wont_fix"` — include this line in the report's executive summary

### Step 1 — Cross-Dimension Deduplication

Apply hard deduplication rules (do NOT use LLM-based title similarity judgment):

**Hard rules (always merge):**
- **Rule 1**: Same `file_path` + overlapping line ranges (within 5 lines of each other) → merge
- **Rule 2**: Same `file_path` + null lines on both findings + exact `title` match → merge

**Do NOT merge based on:**
- Title similarity alone (too subjective, causes non-determinism)
- Same description without file match
- Cross-file findings even if "related"

**When merging:**
- Keep the higher severity
- Combine dimension tags: `"dimensions": ["structure", "quality"]`
- Keep the finding with the most specific line numbers
- Merge recommendations (deduplicate identical ones)
- Assign the merged finding to the dimension with the highest weight
- **Merge key format**: `{dimension}:{file_path}:{line_start // 10 * 10}` (document for transparency)

**Dedup summary table**: After dedup, produce a table for inclusion in the report:

| Finding ID | Absorbed By | Reason |
|-----------|-------------|--------|
| STRC-a1b2c3-0140  | QUAL-d4e5f6-0080    | Same file + overlapping lines (Rule 1) |

### Step 2 — Compute Dimension Scores

For each dimension, after dedup:

1. Count findings assigned to this dimension (including merged findings assigned here). Exclude `wont_fix` findings from score calculation.
2. Apply deduction formula:
   ```
   raw = (3 × criticals) + (2 × highs) + (1 × mediums) + (0.5 × lows)
   score = max(1.0, 10 - min(raw, 9))    # floor = 1.0, cap deductions at 9
   ```
3. Round to 1 decimal place

**Rationale**: Floor of 1.0 means "scanner ran and found real issues" — not zero. Capping deductions at 9 ensures a project with 20 criticals (very bad) still differs from one with 3 criticals (concerning). Projects with scores near 1.0 need urgent attention.

**Edge cases**:
- A dimension with zero findings (all clean) scores **10.0**. A dimension with only `info` findings also scores 10.0 — info findings are observations, not problems.
- A dimension where **all findings were deduplicated into other dimensions** scores **8.0** (not 10.0 — the scanner found issues, they just belong elsewhere). This prevents false inflation of dimensions that happened to lose all their findings to dedup.

### Step 2b — Estimate Ralph-Loop Iterations

For each dimension, after computing the score in Step 2, estimate how many ralph-loop iterations would be needed to reach three target scores.

#### 2b.1 — Aggregate findings by effort

For each dimension, count scoreable findings (severity != `info`, excluding `wont_fix`) by effort level:
```
by_effort = { trivial: 0, small: 0, medium: 0, large: 0, xl: 0 }
```
Count each finding's `effort` field into the corresponding bucket.

#### 2b.2 — Compute true_raw

```
true_raw = 3 × criticals + 2 × highs + 1 × mediums + 0.5 × lows
```

This is the **unclipped** penalty — it is NOT capped at 9 like the score formula. `true_raw` reveals the actual penalty magnitude: two dimensions both scoring 1.0 may have `true_raw` of 9 vs 50, requiring very different effort.

#### 2b.3 — Compute iteration estimates for each target

Three targets: `quick_win` (5/10), `full_quality` (8/10), `perfect` (10/10).

For each target:
```
target_raw = 10 - target_score           # e.g., 10 - 8 = 2
raw_to_remove = max(0, true_raw - target_raw)

# If dimension already at or above target, estimated = 0
if raw_to_remove == 0:
    estimated = 0
    range = [0, 0]
else:
    # Effort cost: how many "iteration slots" each effort level consumes
    EFFORT_COST = { trivial: 0.20, small: 0.25, medium: 0.40, large: 0.67, xl: 1.00 }

    scoreable_findings = sum(by_effort.values())
    total_cost = sum(by_effort[level] × EFFORT_COST[level] for level in EFFORT_COST)
    findings_per_iter = scoreable_findings / total_cost
    avg_penalty = true_raw / scoreable_findings
    raw_per_iter = findings_per_iter × avg_penalty

    estimated = ceil(1.4 × raw_to_remove / raw_per_iter)
    estimated = max(1, min(estimated, scoreable_findings))
    range = [max(1, estimated - 1), estimated + 1]
```

**Edge cases**:
- If `scoreable_findings == 0`: all estimates are 0 (nothing to fix)
- If dimension already at or above target score: `estimated = 0`, `range = [0, 0]`

#### 2b.4 — Store results

Attach to each dimension score entry:
```json
{
  "by_effort": { "trivial": 2, "small": 3, "medium": 1, "large": 0, "xl": 0 },
  "iteration_estimates": {
    "true_raw": 12.5,
    "quick_win":    { "target_score": 5,  "estimated_iterations": 3, "range": [2, 4] },
    "full_quality": { "target_score": 8,  "estimated_iterations": 5, "range": [4, 6] },
    "perfect":      { "target_score": 10, "estimated_iterations": 7, "range": [6, 8] }
  }
}
```

### Step 3 — Compute Overall Score

```
overall = sum(dimension_score * weight) / sum(weights)
```

Round to 1 decimal place. If `--weights` not provided, all weights are 1.0 (simple average).

For partial `--weights` (e.g., only security:2 specified), unspecified dimensions default to 1.0.

### Step 4 — Identify Cross-Cutting Observations

Scan the deduplicated findings for patterns:
- Dimensions where score < 5.0 → flag as critical areas
- Dimensions with 0 findings → note as clean
- Clusters of findings in the same file across dimensions → note as hotspot files
- Significant score gaps between related dimensions (e.g., structure 3/10 but quality 9/10) → note inconsistency

Write 3-5 bullet points summarizing these observations.

### Step 4b — Root Cause Clustering

After cross-cutting observations, identify hot modules:

1. Group all findings by `file_path` (exclude null file_path findings)
2. A file appearing in ≥ 3 findings across ≥ 2 dimensions is a **hot module**
3. For each hot module, compute:
   - Total finding count
   - Distinct dimensions affected
   - Aggregate effort (largest individual effort in the cluster)
   - A one-sentence remediation recommendation
4. Sort clusters by (finding_count DESC, dimension_count DESC)

Produce a "Root Cause Analysis" section in the report:

```
## Root Cause Analysis

| Cluster | Module | Findings | Dimensions | Effort | Recommendation |
|---------|--------|----------|------------|--------|----------------|
| C1 | src/commands.rs | 8 | structure, quality, testing | large | Refactor into dispatcher + handlers |
| C2 | storage/redis_store.rs | 5 | quality, security | medium | Extract storage trait, fix KEYS usage |
```

If no hot modules exist, omit this section.

Produce `RootCauseCluster` objects matching the schema in `output-schemas.md`.

### Step 4c — Priority Tiers

After scoring, assign `priority_tier` to every finding (excluding `wont_fix`) using the rules in `analysis-dimensions.md`:

- `immediate`: security critical, injection/auth-bypass/hardcoded-secrets
- `sprint-1`: all other criticals, security high, structure critical
- `sprint-2`: high severity (non-security), medium severity (structural)
- `backlog`: medium severity (style/naming), low, info

Then produce an "Action Plan" section in the report:

```
## Action Plan

### 🔴 Immediate (fix before next deploy)
- SEC-001: Hardcoded API key in config.py — trivial
- SEC-003: SSRF in fetch_url() — small

### 🟠 Sprint 1
- STRC-001: Circular dependency core ↔ workpackage — medium

### 🟡 Sprint 2
- QUAL-004: Duplicated validation logic — small

### ⚪ Backlog
- QUAL-002: 12 TODO markers in auth module — medium
```

### Step 4d — Delta Analysis (if PREVIOUS_SCORES provided)

If `PREVIOUS_SCORES` is not null:

With fingerprint-based IDs, delta analysis is reliable:

- **Resolved**: IDs in PREVIOUS_SCORES findings but not in current → genuinely fixed
- **New**: IDs in current but not in PREVIOUS_SCORES → genuinely new issues
- **Unchanged**: IDs present in both → persistent issues

**Handling merged IDs:**
During dedup (Step 1), findings may be merged. To handle resolved_ids from
carry_forward_summary correctly:
1. Build mapping: {original_scanner_id → merged_id} from dedup table
2. Check both original and merged IDs when computing deltas
3. A finding is "resolved" if its scanner ID is in carry_forward_summary.resolved_ids,
   even if PREVIOUS_SCORES stored a different merged ID
4. Include both scanner ID and mapped merged ID in resolved_finding_ids

**Old-format detection:** If ANY finding ID in PREVIOUS_SCORES matches `^[a-z-]+-\d{3}$`
(old sequential format), treat the entire previous report as old-format and skip delta
comparison (all findings treated as "new").

**v0.6→v0.7 ID prefix migration:** If PREVIOUS_SCORES contains finding IDs with old dimension prefixes (`ARCH-`, `PAT-`, `DEBT-`, `PERF-`, `DEP-`), map them for delta comparison: `ARCH-*`→`STRC-*`, `PAT-*`→`STRC-*`, `DEBT-*`→`QUAL-*`, `PERF-*`→`QUAL-*`, `DEP-*`→`SEC-*` or `TST-*`. If old 8-dim dimension names appear in PREVIOUS_SCORES.dimension_scores, skip delta for those dimensions (dimension count mismatch).

Add a "Run Delta" section to the report with new, resolved, unchanged counts and score deltas.

Produce a `RunDelta` object matching the schema in `output-schemas.md`.

### Step 5 — Assemble Report

Use the `analysis-draft.md` template:
1. Set `is_draft = true` for draft reports
2. For each dimension section, include top 5 findings by severity
3. If dimension has > 5 findings, show `remaining_count`
4. Include cross-cutting observations from Step 4

### Step 6 — Assemble Scores JSON

Produce `scores.json` matching the ScoresReport schema. Each entry in `dimension_scores` MUST include:
- `by_effort`: effort distribution from Step 2b.1
- `iteration_estimates`: estimates from Step 2b.3 (including `true_raw`)

**6b.** If any DimensionReport contains a `carry_forward_summary`, aggregate into
`scan_metadata.carry_forward_stats` in the ScoresReport:
For each dimension with carry_forward_summary:
  `scan_metadata.carry_forward_stats[dimension] = { carried_forward, resolved, new }`

### Step 7 — Handle Critic Feedback (if present)

If `CRITIC_FEEDBACK` is provided:
1. Read each issue in the feedback
2. For `blocking` issues:
   - `score-calibration`: Re-check scoring formula application
   - `coverage-gap`: Note the gap in cross-cutting observations (cannot re-scan)
   - `dedup-error`: Undo or redo specific merges as suggested
   - `actionability`: Revise affected recommendations
3. For `warning` issues: Address if trivial, otherwise note in report
4. Re-run Steps 2-6 with corrections

## Cross-Analysis Workflow (--deep mode)

When invoked with `--deep`:

### Step 1 — Identify Shared Root Causes

For each cluster of findings across 2+ dimensions that affect the same files:
1. Analyze whether a single architectural/design issue could explain all of them
2. If yes, create a root cause entry with:
   - A descriptive title
   - Which dimensions are affected
   - Which finding IDs are related

### Step 2 — Detect Systemic Patterns

Look for:
- Files that appear in 3+ dimension findings → "hotspot" pattern
- Entire directories with consistent issues → "module-level" pattern
- Missing abstraction layers (structure + testing + quality issues in same area)
- Dependency issues causing cascade effects (testing → quality → security)

### Step 3 — Suggest Combined Fixes

For each root cause, propose a fix that addresses multiple dimensions:
- Title and description
- Which root causes it addresses
- Estimated effort

### Step 4 — Return CrossAnalysis JSON

Produce output matching the CrossAnalysis schema. Do NOT persist — return to orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Empty findings for a dimension | Score 10.0, skip from report sections |
| All dimensions empty | Score 10/10 overall, note codebase is clean |
| Dedup merges > 30% of findings | Log warning — may indicate dimension overlap, but proceed |
| Critic feedback references non-existent finding | Skip that feedback item, note in response |
| --deep with < 2 dimensions | Skip cross-analysis, return empty CrossAnalysis |

## Success Checklist

- [ ] Overrides applied: false_positives removed, wont_fix tagged (if OVERRIDES provided)
- [ ] All findings deduplicated using hard rules only (no LLM title similarity)
- [ ] Dedup summary table produced (Finding ID, Absorbed By, Reason)
- [ ] Per-dimension scores computed using new formula (floor 1.0, cap 9)
- [ ] Empty-after-dedup dimensions scored 8.0, truly-clean dimensions scored 10.0
- [ ] Overall score computed with correct weights
- [ ] Root Cause Analysis section produced (if hot modules exist)
- [ ] priority_tier assigned to every finding
- [ ] Action Plan section produced with tier groupings
- [ ] Cross-cutting observations include 3-5 bullet points
- [ ] Run Delta section produced (if PREVIOUS_SCORES provided)
- [ ] scan_metadata.carry_forward_stats aggregated from DimensionReport.carry_forward_summary (if any scanner provided it)
- [ ] Old-format PREVIOUS_SCORES detected and delta comparison skipped if applicable
- [ ] `by_effort` computed for each dimension (scoreable findings only, excluding info)
- [ ] `true_raw` computed as unclipped penalty for each dimension
- [ ] `iteration_estimates` computed for all 3 targets per dimension (0 when already at/above target)
- [ ] Draft report written using template
- [ ] scores.json matches ScoresReport schema (including `by_effort` and `iteration_estimates`)
- [ ] Critic feedback addressed (if provided)
