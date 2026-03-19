# Ralph-Loop Suggested Phases in Analysis Report

**Date**: 2026-03-19
**Status**: Approved
**Affects**: `templates/analysis-draft.md`, `skills/reconcile-report/SKILL.md`, `skills/critique-report/SKILL.md`, `skills/analyze-codebase/SKILL.md`, `README.md`

## Problem

After running a multi-dimension analysis, users see iteration estimates per dimension but must manually craft ralph-loop commands and decide which dimensions to tackle first. The report should suggest phased execution commands based on the analysis results, reducing the gap between "seeing the scores" and "starting to fix."

## Solution

Extend the existing "Ralph-Loop Effort Estimates" section in the analysis report with a "Suggested Execution Plan" subsection. The reconciler uses judgment to group dimensions into 1-3 phases, pick per-dimension targets based on iteration difficulty, and render ready-to-paste commands. An all-at-once alternative is included when there are 2+ phases. The entire subsection is conditionally omitted when all dimensions already score >= 8/10.

## Template Addition

Extend `templates/analysis-draft.md`. After the existing `{{recommended_ralph_order}}` line and before the `---` separator, add:

The entire subsection is wrapped in `{{#has_phases}}...{{/has_phases}}`. The reconciler sets `has_phases = true` when at least one dimension scores < 8/10, and omits it when all dimensions are clean. Phase 1 is always present when `has_phases` is true. Phases 2-3 are conditional. The all-at-once alternative is conditional on `{{#has_multiple_phases}}` (2+ phases) — when there's only one phase, it would be a redundant duplicate.

Template content to add (using mustache syntax):

```
{{#has_phases}}
### Suggested Execution Plan

**Phase 1 — {{phase_1_name}}** (~{{phase_1_iterations}} iterations)
  /code-analysis:ralph-loop --targets="{{phase_1_targets}}" --completion-promise "SCORE_REACHED" --max-iterations {{phase_1_max_iterations}}
{{phase_1_rationale}}

{{#phase_2_targets}}
**Phase 2 — {{phase_2_name}}** (~{{phase_2_iterations}} iterations)
  /code-analysis:ralph-loop --targets="{{phase_2_targets}}" --completion-promise "SCORE_REACHED" --max-iterations {{phase_2_max_iterations}}
{{phase_2_rationale}}
{{/phase_2_targets}}

{{#phase_3_targets}}
**Phase 3 — {{phase_3_name}}** (~{{phase_3_iterations}} iterations)
  /code-analysis:ralph-loop --targets="{{phase_3_targets}}" --completion-promise "SCORE_REACHED" --max-iterations {{phase_3_max_iterations}}
{{phase_3_rationale}}
{{/phase_3_targets}}

{{#has_multiple_phases}}
**All-at-once alternative:**
  /code-analysis:ralph-loop --targets="{{all_targets}}" --completion-promise "SCORE_REACHED" --max-iterations {{all_max_iterations}}
> Note: Phased execution is recommended — fixes in earlier phases cascade into later dimensions, reducing total effort.
{{/has_multiple_phases}}
{{/has_phases}}
```

Maximum 3 phases. `--completion-promise "SCORE_REACHED"` is the existing ralph-loop completion token (defined in `skills/ralph-loop/SKILL.md` Step 2 and Step 8).

## Reconciler Instructions (Step 2c)

Add **Step 2c — Generate Ralph-Loop Execution Plan** in `skills/reconcile-report/SKILL.md`, after Step 2b (iteration estimates).

### Phase grouping

The reconciler uses judgment to group dimensions into 1-3 phases:

1. **Exclude** dimensions already at or above 8/10
2. **Exclude** dimensions with only info findings (score 10.0)
3. **Group** remaining dimensions using these signals:
   - Iteration estimates: lower-effort dimensions go in earlier phases
   - Shared hotspot modules: dimensions sharing hotspot files benefit from being in the same phase (fixes cascade)
   - Root cause clusters from Step 4b: dimensions that share hot modules (from the RootCauseCluster data) benefit from being in the same phase
4. **Name** each phase descriptively (e.g., "Quick wins", "Structural fixes", "Deep refactoring")

### Per-dimension target selection

Apply rules in priority order (first match wins):

1. If a dimension's `quick_win` estimated iterations > 4 → target **5/10** (quick_win)
2. If a dimension's `full_quality` estimated iterations > 6 → target **5/10** (quick_win)
3. Otherwise → target **8/10** (full_quality)

Only two target levels are used: 5/10 and 8/10. These map directly to the pre-computed `quick_win` and `full_quality` iteration estimates in scores.json, so `phase_N_iterations` can be read directly from the existing estimates without interpolation.

### Max iterations per phase

- Per phase: sum the highest `range[1]` values across dimensions in that phase + 2 buffer
- All-at-once: sum across all phases + 3 buffer

### Output

Populate the template fields:
- `phase_N_name`: descriptive phase name
- `phase_N_targets`: `--targets` value string (e.g., `"debt:8,patterns:8,perf:8"`)
- `phase_N_rationale`: 1-2 sentence explanation of why these dimensions are grouped
- `phase_N_iterations`: estimated iteration range for this phase (e.g., "4-6")
- `phase_N_max_iterations`: computed max iterations for the phase
- `all_targets`: all dimensions needing work (score < 8/10) combined into one `--targets` string. Dimensions already at or above 8/10 are excluded.
- `all_max_iterations`: computed max iterations for all-at-once
- `has_phases`: boolean, true when at least one dimension scores < 8/10
- `has_multiple_phases`: boolean, true when 2+ phases are generated

**Tiebreaker:** When two dimensions have identical iteration estimates during phase assignment, sort alphabetically by dimension name for deterministic output.

### Step 5 update (Assemble Report)

Include the phase fields (`has_phases`, `has_multiple_phases`, `phase_N_*`, `all_targets`, `all_max_iterations`) when rendering the report from the template in Step 5.

### Success checklist additions

- [ ] Dimensions at or above 8/10 excluded from suggested commands
- [ ] All dimensions below 8/10 appear in at least one phase and in the all-at-once command
- [ ] Per-dimension targets adjusted based on iteration difficulty
- [ ] Phase rationale references hotspot overlap or cross-cutting observations when applicable

## Critic Validation

Extend Check 4 (Actionability) in `skills/critique-report/SKILL.md` with a new item:

**Suggested execution plan validation** (when report contains the "Suggested Execution Plan" subsection):
- Verify suggested commands use valid `--targets` syntax (dimension shorthand, colon-separated scores)
- Verify no dimension appears in the commands that already scores >= 8/10
- Verify `--max-iterations` values are reasonable (> 0, not exceeding total scoreable findings across included dimensions)
- Verify all dimensions needing work (score < 8/10) appear in at least one phase and in the all-at-once command (if present)
- Verify all-at-once alternative is present only when 2+ phases exist

**Issue category**: `actionability`
**Severity**: `warning` (commands are suggestions, not breaking if imperfect)

## Orchestrator Update

Update Stage 5 presentation list in `skills/analyze-codebase/SKILL.md` to include the suggested execution plan. The orchestrator reads the phased commands from the persisted draft report (`.code-analysis/reports/YYYY-MM-DD-analysis-draft.md`) — it does NOT need to read the template or recompute phase data. This is consistent with how Stage 5 already reads cross-cutting observations from the draft report.

## Non-changes

- `references/output-schemas.md` — no schema changes; phase data is rendered into the report template, not stored in scores.json
- `skills/ralph-loop/SKILL.md` — no changes; it already supports `--targets` syntax

## Files to Modify

| File | Change |
|------|--------|
| `templates/analysis-draft.md` | Add "Suggested Execution Plan" subsection to Ralph-Loop Effort Estimates |
| `skills/reconcile-report/SKILL.md` | Add Step 2c (phase grouping, target selection, max iterations), update Step 5 (Assemble Report) |
| `skills/critique-report/SKILL.md` | Extend Check 4 (Actionability) with command validation |
| `skills/analyze-codebase/SKILL.md` | Update Stage 5 presentation list |
| `README.md` | Add bullet point to Scoring System section: "**Suggested execution plan** = phased ralph-loop commands with per-dimension targets, generated from iteration estimates and hotspot analysis" |
