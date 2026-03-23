# Multi-Dimension Mode

## Multi-Dimension State File Format

When running in multi-dimension mode, `.claude/loop-state.md` uses an extended format:

```markdown
# Ralph-Loop State
mode: multi
targets: { structure: 8, quality: 9 }
current_scores: { structure: 1.0, quality: 1.0 }
starting_scores: { structure: 1.0, quality: 1.0 }
plan_paths: { structure: .code-analysis/plans/2026-03-19-structure-plan.md, quality: .code-analysis/plans/2026-03-19-quality-plan.md }
completed_finding_ids: [STRC-1ec634-0000, QUAL-8d5fec-0020]
last_commit_sha: 2614d94a
starting_commit_sha: a1b2c3d4
phase: committed
iteration: 3
score_history:
  - { structure: 1.0, quality: 1.0 }
  - { structure: 4.5, quality: 3.0 }
  - { structure: 6.0, quality: 5.5 }
started_at: 2026-03-19T06:25:42Z
last_updated_at: 2026-03-19T14:26:48Z
```

**Key differences from single-dimension format:**
- `mode: multi` — identifies multi-dimension state (absent in single-dimension)
- `targets` — map of dimension to target score (replaces `dimension` + `target`)
- `current_scores` / `starting_scores` — maps (replace `current_score` / `starting_score`)
- `plan_paths` — map of dimension to plan path (replaces `plan_path`)
- `completed_finding_ids` — flat list (unchanged; IDs contain dimension prefix e.g. `ARCH-`, `PAT-`)
- `score_history` — entries are maps (replace scalar values)
- `starting_commit_sha` — recorded at first run, used for accumulated diff scope (same in both modes)

**Backward compatibility:** If `mode` key is absent, treat as single-dimension (existing format). Old state files work unchanged.

**v0.6 to v0.7 state migration:** If a state file contains old dimension names (`architecture`, `patterns`, `performance`, `tech-debt`, `dependencies`), map them automatically: `architecture` to structure, `patterns` to structure, `performance` to quality, `tech-debt` to quality, `dependencies` to security+testing. Clear `completed_finding_ids` containing old prefixes (`ARCH-`, `PAT-`, `PERF-`, `DEBT-`, `DEP-`) since those IDs no longer exist. Log migration: `"Migrated state from v0.6 dimension '{old}' to v0.7 dimension '{new}'"`.

**Exit condition:** Loop exits when `current_scores[dim] >= targets[dim]` for **every** dimension.

## Gap-Weighted Batch Selection Algorithm

When in multi-dimension mode, select findings across ALL dimensions' plans using gap-weighted priority:

1. Compute each dimension's gap: `gap = target - current_score`
2. Dimensions already at or above target: gap = 0 (excluded from selection)
3. Score each finding: `priority = severity_weight x gap_of_its_dimension`
   - Severity weights: critical=3, high=2, medium=1, low=0.5
4. Sort by priority descending, pick top 3-5 (not yet in `completed_finding_ids`)
5. Effort tiebreaker: among equal-priority findings, prefer smaller effort (trivial to small to medium to large to xl)

**Example:** Structure at 1.0 (target 8, gap=7), quality at 5.0 (target 9, gap=4). A high-severity structure finding scores `2 x 7 = 14`, a high-severity quality finding scores `2 x 4 = 8`. Structure findings get picked first.

**Cross-dimension fixes:** When a fix resolves findings in multiple dimensions (e.g., refactoring a god struct that spans structure and quality), add ALL affected finding IDs to `completed_finding_ids` regardless of dimension. The re-scan naturally drops resolved findings from all dimensions.

**XS-gate in multi-dimension mode:** The trivial-effort gate applies to the batch as a whole, regardless of how many dimensions are represented. A batch with 3 trivial arch findings and 1 small patterns finding goes through the full design pipeline.

## Multi-Dimension Variants by Step

### Step 3 — First-Run (Multi-Dimension)

- Before invoking analyze-codebase, capture the current HEAD SHA and write initial state:
  ```bash
  git log -1 --format=%H  # starting_commit_sha
  ```
  ```
  mode: multi
  targets: { structure: 8, quality: 9 }
  starting_commit_sha: <captured SHA>
  phase: scanning
  started_at: <ISO 8601 now>
  last_updated_at: <ISO 8601 now>
  ```
- Invoke analyze-codebase with all target dimensions:
  ```
  /analyze-codebase --dimensions=struct,quality --skip-critics [--model MODEL_SPEC if provided]
  ```
  When `--plugin` is set, pass `--plugin` to all `/analyze-codebase` invocations.
  **Note:** The initial scan does not use `--changed-files-hint` since there is no prior commit SHA to diff against.
- At Stage 5 user checkpoint, automatically choose **Proceed to refactoring plans**.
- Wait for all stages (1-10) to complete and plans to be written to disk.
- Find each plan at `.code-analysis/plans/*-{DIMENSION}-plan.md` (use latest date).
- Find latest scores in `.code-analysis/reports/*-scores.json`.
- Extract scores for all target dimensions.
- **Dimensions already at target on initial scan:** Mark as met in `current_scores` but do NOT remove from the scan list — they are still scanned each iteration for cross-dimension context. Exclude from batch selection. Log: `"{dimension} already at {score} (target {target}), skipping fixes — still scanning for cross-dimension context"`. If all dimensions already meet their targets, output `SCORE_REACHED`, done.
- After scan completes, update `.claude/loop-state.md`:
  ```
  mode: multi
  targets: { structure: 8, quality: 9 }
  current_scores: { structure: <score>, quality: <score> }
  starting_scores: { structure: <score>, quality: <score> }
  plan_paths: { structure: <path>, quality: <path> }
  completed_finding_ids: []
  last_commit_sha:
  starting_commit_sha: <preserved from above>
  phase: planning
  iteration: 0
  score_history:
    - { structure: <score>, quality: <score> }
  started_at: <preserved from above>
  last_updated_at: <ISO 8601 now>
  ```
- Go to Step 4 (batch selection). **Note:** Single-dimension Step 3 continues to go to Step 7 (re-scan, unchanged). Multi-dimension goes to Step 4 because the first batch has not been selected yet from the multi-plan priority queue.

### Step 5 — Mechanical Fixes (Multi-Dimension)

Read plans from all `plan_paths` entries. Identify the batch of trivial findings NOT yet in `completed_finding_ids` across all dimensions, using the gap-weighted priority from Step 4.

### Step 6 — Commit (Multi-Dimension)

Use commit message: `git commit -m 'fix(ralph-loop): <one-line summary> [dim1,dim2]'`

The commit scope is always `ralph-loop`, even if a particular batch only contains findings from a single dimension. The bracket suffix lists which dimensions' findings were addressed in that batch.

### Step 7 — Re-scan (Multi-Dimension)

Run analyze-codebase with all target dimensions together:
```
/analyze-codebase --dimensions=dim1,dim2,... --draft-only --skip-critics \
  --changed-files-hint="{comma-separated file list from git diff}" \
  [--model MODEL_SPEC if provided]
```
Active dimensions (excluding converged) are scanned. Converged dimensions are skipped unless this is a
safety-net iteration (`iteration % 5 == 0`). See main skill Step 7 for convergence rules. Update all entries in `current_scores`, append full score map to `score_history`.

### Step 8 — Completion (Multi-Dimension)

If `current_scores[dim] >= targets[dim]` for every dimension:
- Write `phase: done` and `last_updated_at` to `.claude/loop-state.md`.
- Output `<promise>SCORE_REACHED</promise>`.

**Mid-loop dimension completion:** When a dimension reaches its target but others have not:
- Log: `"{dimension} reached {score} (target {target}) — continuing for {remaining dimensions}"`
- That dimension's findings are no longer selected in batch picks
- Added to `converged_dimensions`, skipped on non-safety-net iterations
- If score drops below target due to another fix, re-enters fix pool

### Step 9 — Plan Refresh (Multi-Dimension)

- **One dimension's plan exhausted, score below target:** Clear its IDs from `completed_finding_ids` using the finding ID prefix (e.g., `STRC-*` belongs to structure, `QUAL-*` to quality). Next scan generates a fresh plan for that dimension. Other dimensions continue using their existing plans.
- **All plans exhausted, any score below target:** Clear all `completed_finding_ids`, delete `loop-state.md`. Next iteration starts fresh (Step 3).

## Cross-Mode Conflict Rules

- Existing single-dimension state + `--targets` flag: error `"Active single-dimension loop found. Complete or delete .claude/loop-state.md first"`
- Existing multi-dimension state + positional args: error `"Active multi-dimension loop found. Use --targets or delete .claude/loop-state.md first"`

## Multi-Dimension Recovery

1. **Arg mismatch detection**: Compare `--targets` from CLI args against stored `targets` map.
   - If maps are identical: resume at the stored `phase`
   - If maps differ: prompt user `"State has targets {stored}, args have {new}. Resume existing loop, or delete and start fresh?"`
   - If positional args were provided instead of `--targets`: error (see cross-mode conflicts above)

2. **Phase recovery**: Same logic as single-dimension — read `phase` from state, execute the corresponding recovery action. The only difference: recovery reads `targets`/`current_scores`/`plan_paths` (maps) instead of `dimension`/`target`/`current_score`/`plan_path` (scalars).

3. **SHA verification**: Same as single-dimension — compare `last_commit_sha` against HEAD.

## Error Handling (Multi-Dimension)

| Scenario | Resolution |
|----------|-----------|
| One dimension's plan generation fails | Log warning, continue with other dimensions. Retry plan generation on next re-scan. |
| All findings are xl effort | Proceed normally. Log: `"Only xl-effort findings remaining, iterations may be slow"` |
| Fix in dimension A introduces new finding in dimension B | Re-scan catches it, batch selection picks it up if impactful enough (gap-weighted priority) |
| Dimension reaches target then regresses below target | Re-enters fix pool automatically — mid-loop completion is reversible |
