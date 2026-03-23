# Verification and Re-Scan Logic

## Step 7 — Re-Scan Modes

Write `phase: rescanning` and `last_updated_at` to `.claude/loop-state.md`.

Determine scan mode by checking `iteration` from state file:
- If `iteration % 3 == 0` (every 3rd iteration: 3, 6, 9, ...): **full re-discovery scan** (no `--changed-files-hint`)
- Otherwise: **carry-forward scan** (with `--changed-files-hint`)

### Carry-Forward Scan (default)

Compute changed files since **loop start** (accumulated diff):
```bash
git diff --name-only {starting_commit_sha}..HEAD
```
Use `starting_commit_sha` (not `last_commit_sha`) so that ALL files modified across the entire loop are re-scanned, preventing carry-forward drift from narrow diff scope.

Run a draft scan:
- **Single-dimension:**
  ```
  /analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics \
    --changed-files-hint="{comma-separated file list from git diff}" \
    [--model MODEL_SPEC if provided]
  ```
- **Multi-dimension:**
  ```
  /analyze-codebase --dimensions=dim1,dim2,... --draft-only --skip-critics \
    --changed-files-hint="{comma-separated file list from git diff}" \
    [--model MODEL_SPEC if provided]
  ```
  All target dimensions are scanned together (including dimensions already at target, for cross-dimension context).

**Note:** The `--model` flag is passed through verbatim from ralph-loop's input. When `--skip-critics` is active, any `critique` model override is silently unused since critique stages are skipped. This is expected — the flag is not consumed.

When `--plugin` is set, pass `--plugin` to all `/analyze-codebase` invocations.

This enables diff-scoped carry-forward: unchanged files' findings are carried forward without re-reading, reducing re-scan token cost.

### Full Re-Discovery Scan (every 3rd iteration)

Run a draft scan **without** `--changed-files-hint`:
- **Single-dimension:**
  ```
  /analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics \
    [--model MODEL_SPEC if provided]
  ```
- **Multi-dimension:**
  ```
  /analyze-codebase --dimensions=dim1,dim2,... --draft-only --skip-critics \
    [--model MODEL_SPEC if provided]
  ```

Force scanners to re-verify ALL previous findings and scan the full codebase for new ones, breaking the carry-forward ratchet effect where findings can be incorrectly marked as resolved and never rediscovered.

Log: `"Iteration {N}: full re-discovery scan (carry-forward ratchet break)"`

### Post-Scan Update

- Read the new score from `.code-analysis/reports/*-scores.json` (latest date file).
- Update `.claude/loop-state.md`:
  - `phase: planning`
  - `current_score: <new score>`
  - Append new score to `score_history`
  - **Multi-dimension:** Update all entries in `current_scores`, append full score map to `score_history`
  - Update `last_updated_at`
- Phase transitions to `planning` (not `committed`) because the next action is selecting a new batch.

## Step 8b — Final Verification Scan

Before outputting `<promise>SCORE_REACHED</promise>`, run a final verification scan to catch carry-forward inflation:

1. Run a fresh full scan **without** `--changed-files-hint` on all loop dimensions:
   - **Single-dimension:** `/analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics [--model MODEL_SPEC if provided]`
   - **Multi-dimension:** `/analyze-codebase --dimensions=dim1,dim2,... --draft-only --skip-critics [--model MODEL_SPEC if provided]`
   Log: `"Running final verification scan (full codebase, no carry-forward)"`

2. Read verified scores from `.code-analysis/reports/*-scores.json`.

3. Compare loop scores vs verified scores for each dimension:
   - If `|loop_score - verified_score| <= 2.0` for ALL dimensions: scores confirmed.
     Update `current_score` / `current_scores` with verified values. Proceed to output `SCORE_REACHED`.
   - If `|loop_score - verified_score| > 2.0` for ANY dimension: **score inflation detected**.
     Log warning: `"Score inflation detected: {dimension} loop={loop_score} verified={verified_score} (delta={delta})"`
     Update `current_score` / `current_scores` with verified values.
     If verified scores still meet targets: proceed to output `SCORE_REACHED` with verified scores.
     If verified scores do NOT meet targets: set `phase: planning`, log `"Continuing loop with verified scores"`, and resume at Step 4.
