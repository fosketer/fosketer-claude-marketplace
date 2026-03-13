---
name: reconcile-report
description: |
  Sub-skill for cross-dimension deduplication, scoring, and unified report assembly.
  Loaded by the report-reconciler agent.
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

## Reconciliation Workflow

### Step 1 — Cross-Dimension Deduplication

For each pair of findings across different dimensions:

1. **Check file overlap**: Do they reference the same `file_path`?
2. **Check line overlap**: Do their `[line_start, line_end]` ranges overlap (within 5-line tolerance)?
3. **If both match**: Merge into a single finding:
   - Keep the higher severity
   - Combine dimension tags: `"dimensions": ["architecture", "patterns"]`
   - Merge recommendations (deduplicate identical ones)
   - Use the more specific description
   - Assign the merged finding to the dimension with the highest weight

**Conservative dedup rule**: Only merge when file AND line range overlap. Do NOT merge based on title similarity alone — false positives are worse than duplicates.

### Step 2 — Compute Dimension Scores

For each dimension, after dedup:

1. Count findings assigned to this dimension (including merged findings assigned here)
2. Apply deduction formula:
   ```
   score = max(0, 10 - sum(deductions))

   deductions per finding:
     critical = 3
     high     = 2
     medium   = 1
     low      = 0.5
     info     = 0
   ```
3. Round to 1 decimal place

**Edge case**: A dimension with zero findings (all clean) scores 10.0. A dimension with only `info` findings also scores 10.0. This is intended — info findings are observations, not problems.

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
- Significant score gaps between related dimensions (e.g., architecture 3/10 but patterns 9/10) → note inconsistency

Write 3-5 bullet points summarizing these observations.

### Step 5 — Assemble Report

Use the `analysis-draft.md` template:
1. Set `is_draft = true` for draft reports
2. For each dimension section, include top 5 findings by severity
3. If dimension has > 5 findings, show `remaining_count`
4. Include cross-cutting observations from Step 4

### Step 6 — Assemble Scores JSON

Produce `scores.json` matching the ScoresReport schema.

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
- Missing abstraction layers (architecture + testing + quality issues in same area)
- Dependency issues causing cascade effects (dependencies → performance → quality)

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

- [ ] All findings deduplicated across dimensions
- [ ] Per-dimension scores computed and valid (0-10)
- [ ] Overall score computed with correct weights
- [ ] Cross-cutting observations include 3-5 bullet points
- [ ] Draft report written using template
- [ ] scores.json matches ScoresReport schema
- [ ] Critic feedback addressed (if provided)
