# Ralph-Loop Multi-Dimension Design

**Date**: 2026-03-19
**Status**: Approved
**Affects**: `skills/ralph-loop/SKILL.md`, `README.md`

## Problem

Ralph-loop currently operates on a single dimension. When dimensions are scanned individually, cross-cutting findings (TOCTOU race conditions, god structs spanning multiple concerns) are missed — the same gap that caused patterns to score 8.0 alone but 1.0 when scanned alongside architecture. Users must run sequential ralph-loops with no guarantee that cross-dimensional issues will be caught.

## Solution

Extend ralph-loop to accept multiple dimensions with per-dimension target scores. All specified dimensions are scanned together each iteration, preserving cross-scanner context. Findings are selected across all dimensions using a gap-weighted priority algorithm. The loop exits when every dimension reaches its own target.

## Interface

### New syntax

```bash
# Multi-dimension with per-dimension targets
/code-analysis:ralph-loop --targets="arch:8,patterns:9,security:10"

# Single dimension (backward-compatible, unchanged)
/code-analysis:ralph-loop patterns 8
```

### Parsing rules

- Positional args `<dimension> <target>` → single-dimension mode (internally converted to `--targets="dimension:target"`)
- `--targets` flag → multi-dimension mode
- Cannot mix both — error if positional args and `--targets` are both provided
- `--max-iterations` and `--completion-promise` work the same in both modes
- Dimension shorthand uses the existing map: `arch` → architecture, `deps` → dependencies, `perf` → performance, `debt` → tech-debt

## State File

### Multi-dimension format

```markdown
# Ralph-Loop State
mode: multi
targets: { architecture: 8, patterns: 9 }
current_scores: { architecture: 1.0, patterns: 1.0 }
starting_scores: { architecture: 1.0, patterns: 1.0 }
plan_paths: { architecture: .code-analysis/plans/2026-03-19-architecture-plan.md, patterns: .code-analysis/plans/2026-03-19-patterns-plan.md }
completed_finding_ids: [ARCH-1ec634-0000, PAT-8d5fec-0020]
last_commit_sha: 2614d94a
phase: committed
iteration: 3
score_history:
  - { architecture: 1.0, patterns: 1.0 }
  - { architecture: 4.5, patterns: 3.0 }
  - { architecture: 6.0, patterns: 5.5 }
started_at: 2026-03-19T06:25:42Z
last_updated_at: 2026-03-19T14:26:48Z
```

### Changes from single-dimension format

| Single-dimension | Multi-dimension |
|-----------------|-----------------|
| (absent) | `mode: multi` |
| `dimension: arch` | `targets: { architecture: 8, patterns: 9 }` |
| `target: 8` | absorbed into `targets` |
| `current_score: 6.0` | `current_scores: { architecture: 6.0, patterns: 5.5 }` |
| `starting_score: 1.0` | `starting_scores: { architecture: 1.0, patterns: 1.0 }` |
| `plan_path: ...` | `plan_paths: { architecture: ..., patterns: ... }` |
| `score_history: [1.0, 4.5]` | `score_history: [{ arch: 1.0, pat: 1.0 }, ...]` |

### Backward compatibility

If `mode` key is absent, treat as single-dimension (existing format). Old state files work unchanged.

### Exit condition

Loop exits when `current_scores[dim] >= targets[dim]` for every dimension.

## Scan & Reconciliation

### Scan dispatch

All target dimensions are scanned together each iteration:

```bash
# Initial scan (Step 3)
/analyze-codebase --dimensions=arch,patterns --skip-critics

# Re-scan (Step 7)
/analyze-codebase --dimensions=arch,patterns --draft-only --skip-critics --changed-files-hint=...
```

Both scanners run together, so cross-cutting findings (god struct, TOCTOU) are caught every iteration.

### Reconciliation

Unchanged. The report-reconciler already handles multi-dimension input. Ralph-loop reads scores for all target dimensions from `scores.json`.

### Phase state machine

Unchanged. The 6-phase cycle (`scanning → planning → implementing → committed → rescanning → planning`) and recovery logic work identically — phases don't care how many dimensions are tracked.

## Batch Selection Strategy

### Priority algorithm

1. Compute each dimension's gap: `gap = target - current_score`
2. Score each finding: `priority = severity_weight x gap_of_its_dimension`
   - Severity weights: critical=3, high=2, medium=1, low=0.5
3. Sort by priority descending, pick top 3-5
4. Effort tiebreaker: among equal-priority findings, prefer smaller effort (XS → S → M)

### Example

Architecture at 1.0 (target 8, gap=7), patterns at 5.0 (target 9, gap=4). A high-severity architecture finding scores `2 x 7 = 14`, a high-severity patterns finding scores `2 x 4 = 8`. Architecture findings get picked first.

### Cross-dimension fixes

When a fix resolves findings in multiple dimensions, `completed_finding_ids` captures all affected IDs. The re-scan naturally drops resolved findings from both dimensions.

### Plan exhaustion

- **One dimension's plan exhausted, score below target**: Clear its IDs from `completed_finding_ids`, next scan generates a fresh plan. Other dimensions continue using their existing plans.
- **All plans exhausted**: Clear all `completed_finding_ids`, delete state, let next run start fresh (same as current Step 9).

## Initial Scan Flow (Step 3)

1. Run `/analyze-codebase --dimensions=arch,patterns,... --skip-critics`
2. Auto-approve Stage 5 → "Proceed to refactoring plans"
3. Get refactoring plans for all dimensions → store each in `plan_paths`
4. Read all plans, build unified priority queue using batch selection algorithm

### Dimensions already at target

- Drop from `targets` immediately — no work needed
- If all dimensions meet targets on first scan → output `SCORE_REACHED`, done
- Log: `"architecture already at 9.0 (target 8), skipping"`

## Commit & Re-scan

### Commit message format

Multi-dimension: `fix(ralph-loop): <summary> [arch,patterns]`

The dimension list in brackets shows which dimensions' findings were addressed. Scope changes from dimension name to `ralph-loop`.

### Re-scan diff computation

Unchanged — `git diff --name-only {last_commit_sha}..HEAD` passed via `--changed-files-hint` to all dimension scanners.

### Score update after re-scan

1. Read `scores.json`
2. Update `current_scores` for all dimensions
3. Append full score map to `score_history`
4. Check exit: all dimensions at or above targets?
   - Yes → `phase: done`, output `SCORE_REACHED`
   - No → `phase: planning`, next iteration

### Mid-loop dimension completion

When a dimension reaches its target but others haven't:
- Log: `"patterns reached 9.0 (target 9) -- continuing for architecture (4.5/8)"`
- That dimension's findings no longer selected in batch picks
- Still scanned each iteration (cross-dimension context)
- If score drops below target due to another fix, re-enters fix pool

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| `--targets` has only 1 dimension | Valid — uses multi-dimension state format |
| Duplicate dimension in `--targets` | Error: `"Duplicate dimension: architecture"` |
| Target score < 1 or > 10 | Error: `"Target must be between 1.0 and 10.0"` |
| Existing single-dimension state file when starting multi-dimension | Error: `"Active single-dimension loop found. Complete or delete .claude/loop-state.md first"` |
| Existing multi-dimension state file with different targets | Prompt user: resume existing loop, or delete and start fresh? |
| One dimension's plan generation fails | Log warning, continue with others. Retry on next re-scan. |
| All findings are XL effort | Proceed normally. Log: `"Only XL-effort findings remaining, iterations may be slow"` |
| Fix in dimension A introduces finding in dimension B | Re-scan catches it, batch selection picks it up if impactful |
| Dimension reaches target then regresses | Re-enters fix pool automatically |

### Max iterations exhausted

`--max-iterations` applies to total loop count. When exhausted:

```
Ralph-loop stopped after 6 iterations (max reached)
  architecture: 1.0 -> 7.5 (target: 8) -- not reached
  patterns: 1.0 -> 9.0 (target: 9) -- reached
```

## Files to Modify

| File | Change |
|------|--------|
| `skills/ralph-loop/SKILL.md` | New `--targets` flag parsing, multi-dimension state format, cross-dimension batch selection, scan dispatch with all dimensions, per-dimension exit condition, updated commit format |
| `README.md` | Update Ralph-Loop section with multi-dimension syntax and example |

## Non-changes

The following require no modification — they already support multi-dimension:

- `skills/analyze-codebase/SKILL.md` — accepts `--dimensions=x,y,z`
- `skills/reconcile-report/SKILL.md` — handles multi-dimension reconciliation
- `references/output-schemas.md` — scores.json supports multi-dimension entries
