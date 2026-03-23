---
name: ralph-loop
description: |
  This skill should be used when iteratively improving codebase dimension scores to target thresholds
  using analyze-codebase + ralph-loop. Supports single-dimension (positional args)
  or multi-dimension (--targets flag) with per-dimension target scores.
  Applies when the user wants to fix findings across one or more dimensions,
  run a score improvement loop, or automate refactoring until quality thresholds are reached.
  Supports --plugin flag for Claude Code plugin analysis dimensions.
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent", "Skill"]
---

# Ralph-Loop × Analyze-Codebase

Iteratively scan codebase dimensions, implement the generated refactoring plans, commit to main, and loop until all dimension scores reach their targets. Supports single-dimension mode (backward-compatible) and multi-dimension mode with per-dimension target scores.

## Why a Loop is Required

The scoring formula is `score = max(1.0, 10 - min(raw, 9))` where `raw = 3×critical + 2×high + 1×medium + 0.5×low`. Because the penalty is capped at 9, **all dimensions with many findings sit at the 1.0 floor**. Individual scattered fixes appear invisible. You must clear enough findings to bring `raw < 9` before the score moves at all.

## Input Parsing

**Single-dimension mode** (backward-compatible):
```bash
/code-analysis:ralph-loop <dimension> <target> [--plugin] [--max-iterations N] [--model <model-spec>] [--completion-promise "SCORE_REACHED"]
```

**Multi-dimension mode**:
```bash
/code-analysis:ralph-loop --targets="skl:8,cvn:7" --plugin [--max-iterations N] [--model <model-spec>] [--completion-promise "SCORE_REACHED"]
```

### Parsing rules

- Positional args `<dimension> <target>` → single-dimension mode (existing behavior unchanged)
- `--targets` flag → multi-dimension mode (2+ dimensions)
- `--targets` with a single dimension → auto-converted to single-dimension mode for state file consistency
- Cannot mix positional args and `--targets` — error if both provided
- Dimension shorthand: `struct` → structure, `quality`, `security`, `testing`. Backwards-compat aliases: `arch` → structure, `patterns` → structure, `deps` → (adds both security + testing), `perf` → quality, `debt` → quality
- Plugin dimension shorthand (requires `--plugin`): `mnf` → manifest-structure, `skl` → skill-quality, `agt` → agent-design, `hkc` → hook-correctness, `mkt` → marketplace-consistency, `cvn` → convention-adherence
- When `--plugin` is set, only plugin-valid dimensions are accepted: quality, security, mnf/manifest-structure, skl/skill-quality, agt/agent-design, hkc/hook-correctness, mkt/marketplace-consistency, cvn/convention-adherence
- Non-plugin dimensions (struct, testing) with `--plugin` flag → error: "Dimension '{name}' is not available in plugin mode"
- `--model` flag → stored as-is, passed through verbatim to all `/analyze-codebase` invocations. Ralph-loop does not resolve model config — resolution happens inside analyze-codebase.

### Validation

- Duplicate dimension in `--targets` → error: `"Duplicate dimension: {name}"`
- Target score < 1 or > 10 → error: `"Target must be between 1.0 and 10.0"`

## State File

`.claude/loop-state.md` persists between ralph-loop iterations:

```markdown
# Ralph-Loop State
dimension: structure
target: 10
current_score: 6.0
starting_score: 1.0
plan_path: .code-analysis/plans/2026-03-19-structure-plan.md
completed_finding_ids: [STRC-8f3a21-a1b2, STRC-000000-c3d4, STRC-2b4e6a-e5f6]
last_commit_sha: 2614d94a
starting_commit_sha: a1b2c3d4
phase: committed
iteration: 3
score_history: [1.0, 4.5, 6.0]
started_at: 2026-03-19T06:25:42Z
last_updated_at: 2026-03-19T14:26:48Z
mode: plugin  # only present when --plugin was passed
```

> **Note on finding ID format:** `completed_finding_ids` uses the scanner's fingerprint ID format: `{DIM}-{file_hash6}-{title_hash4}` (e.g., `STRC-8f3a21-a1b2`). Title-hash IDs are stable across code shifts, unlike the deprecated line-bucket format.

> **Scoring formula:** `current_score` and `target` use the authoritative formula from `skills/reconcile-report/SKILL.md`: `score = max(1.0, 10 - min(raw, 9))` where `raw = 3×critical + 2×high + 1×medium + 0.5×low`. The floor is **1.0**, not 0.

### Phase State Machine

```
scanning → planning → implementing → committed → rescanning → planning (next iteration)
                                                                  ↓
                                                           score >= target → done
```

Each phase transition writes to `loop-state.md` **before** starting the next phase. A crash at any point leaves the state file pointing to the last *completed* phase.

| Phase | Meaning | What was completed before entering |
|-------|---------|-----------------------------------|
| `scanning` | Initial dimension scan in progress | Nothing yet (first run) |
| `planning` | Selecting/generating plan for next batch | Scan complete, score known |
| `implementing` | Subagents are making code changes | Plan selected, batch chosen |
| `committed` | Changes committed to git | All changes committed, SHA recorded |
| `rescanning` | Re-scan in progress to measure new score | Commit verified |
| `done` | Target score reached | Final score recorded |

### Multi-Dimension State File

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
- `targets` — map of dimension → target score (replaces `dimension` + `target`)
- `current_scores` / `starting_scores` — maps (replace `current_score` / `starting_score`)
- `plan_paths` — map of dimension → plan path (replaces `plan_path`)
- `completed_finding_ids` — flat list (unchanged; IDs contain dimension prefix e.g. `ARCH-`, `PAT-`)
- `score_history` — entries are maps (replace scalar values)
- `starting_commit_sha` — recorded at first run, used for accumulated diff scope (same in both modes)

**Backward compatibility:** If `mode` key is absent, treat as single-dimension (existing format). Old state files work unchanged.

**v0.6→v0.7 state migration:** If a state file contains old dimension names (`architecture`, `patterns`, `performance`, `tech-debt`, `dependencies`), map them automatically: `architecture`→structure, `patterns`→structure, `performance`→quality, `tech-debt`→quality, `dependencies`→security+testing. Clear `completed_finding_ids` containing old prefixes (`ARCH-`, `PAT-`, `PERF-`, `DEBT-`, `DEP-`) since those IDs no longer exist. Log migration: `"Migrated state from v0.6 dimension '{old}' to v0.7 dimension '{new}'"`.

**Exit condition:** Loop exits when `current_scores[dim] >= targets[dim]` for **every** dimension.

## Every Iteration: Steps in Order

### Step 1 — Read State & Recover

Check if `.claude/loop-state.md` exists and read it.

**If no state file** → first run (go to Step 3).

**If state file exists:**

**Mode detection:** Check for `mode` key in state file.
- If absent → single-dimension recovery (existing logic below)
- If `mode: multi` → multi-dimension recovery (see below)

**Cross-mode conflicts:**
- Existing single-dimension state + `--targets` flag → error: `"Active single-dimension loop found. Complete or delete .claude/loop-state.md first"`
- Existing multi-dimension state + positional args → error: `"Active multi-dimension loop found. Use --targets or delete .claude/loop-state.md first"`

**Multi-dimension recovery:**

1. **Arg mismatch detection**: Compare `--targets` from CLI args against stored `targets` map.
   - If maps are identical → resume at the stored `phase`
   - If maps differ → prompt user: `"State has targets {stored}, args have {new}. Resume existing loop, or delete and start fresh?"`
   - If positional args were provided instead of `--targets` → error (see cross-mode conflicts above)

2. **Phase recovery**: Same logic as single-dimension — read `phase` from state, execute the corresponding recovery action. The only difference: recovery reads `targets`/`current_scores`/`plan_paths` (maps) instead of `dimension`/`target`/`current_score`/`plan_path` (scalars).

3. **SHA verification**: Same as single-dimension — compare `last_commit_sha` against HEAD.

**Single-dimension recovery** (existing behavior, unchanged):
Read `dimension` and `target` from state (no need to re-specify via args).
If args are provided AND differ from state, warn: "State says {dim}/{target}, args say {new_dim}/{new_target}. Use state values? [Y/n]"

**Backwards compatibility:** If `phase` key is absent (old 3-field format), treat as `phase: committed`. If `last_commit_sha` is also absent, skip SHA verification entirely and resume at Step 7 (re-scan).

**Recovery by phase:**

CASE "done":
  Output SCORE_REACHED. Stop.

CASE "committed":
  Verify: `git log -1 --format=%H` == `last_commit_sha`?
    YES → resume at Step 7 (re-scan)
    NO, HEAD is ahead → external commits detected. Log warning, re-scan to recalibrate (Step 7)
    NO, HEAD is behind → prompt user: "State records commit {sha} but HEAD is at {head_sha} (behind). Options:
      1. Keep state and re-scan from current HEAD
      2. Delete state and start fresh"
    Do NOT delete state without user confirmation.

CASE "rescanning":
  Re-scan was interrupted. Restart Step 7.

CASE "implementing":
  First, check if subagents committed independently:
    `git log -1 --format=%H` vs `last_commit_sha`:
      HEAD is AHEAD → subagents committed. Update last_commit_sha, treat as "committed" → Step 7.
      HEAD is BEHIND → prompt user (same as committed HEAD-behind case).
  If HEAD matches (no independent commits):
    `git status --porcelain`:
      CLEAN → no changes from interrupted implementation. Log message, resume Step 4.
      DIRTY → prompt user: "Found uncommitted changes from interrupted session. Options:
        1. Review changes, attempt compilation, and commit if it passes
        2. Discard changes (git checkout .) and re-implement this batch
        3. Start fresh (delete state, re-scan dimension)"

CASE "planning":
  Plan generation was interrupted. Restart Step 4.

CASE "scanning":
  Initial scan was interrupted. Restart Step 3.

### Step 2 — Check Completion

**Single-dimension:** If `phase` is `done` or `current_score >= target`, output exactly:
```
<promise>SCORE_REACHED</promise>
```
Then stop. Do nothing else.

**Multi-dimension:** If `phase` is `done` or `current_scores[dim] >= targets[dim]` for every dimension, output exactly:
```
<promise>SCORE_REACHED</promise>
```
Then stop. Do nothing else.

> Note: On restart, the recovery logic in Step 1 handles phase-based completion checks. Step 2 is the fallback for within-session iteration.

### Step 3 — First-Run: Generate Plan (only if no state file)

- Before invoking analyze-codebase, capture the current HEAD SHA and write initial state to `.claude/loop-state.md`:
  ```bash
  git log -1 --format=%H  # → starting_commit_sha
  ```
  ```
  dimension: DIMENSION
  target: TARGET
  starting_commit_sha: <captured SHA>
  phase: scanning
  started_at: <ISO 8601 now>
  last_updated_at: <ISO 8601 now>
  ```
- Invoke the analyze-codebase skill for this dimension:
  ```
  /analyze-codebase --dimensions=DIMENSION --skip-critics [--model MODEL_SPEC if provided]
  ```
  When `--plugin` is set, pass `--plugin` to all `/analyze-codebase` invocations.
- At Stage 5 user checkpoint, automatically choose **Proceed to refactoring plans**.
- Wait for all stages (1–10) to complete and plans to be written to disk.
- Find the plan at `.code-analysis/plans/*-DIMENSION-plan.md` (use latest date).
- Find latest score in `.code-analysis/reports/*-scores.json`.
- Extract `current_score` for dimension DIMENSION.
- After scan completes, update `.claude/loop-state.md`:
  ```
  dimension: DIMENSION
  target: TARGET
  current_score: <score>
  starting_score: <score>
  plan_path: <path>
  completed_finding_ids: []
  last_commit_sha:
  starting_commit_sha: <preserved from above>
  phase: planning
  iteration: 0
  score_history: [<score>]
  started_at: <preserved from above>
  last_updated_at: <ISO 8601 now>
  ```
- Go to Step 7.

**Multi-dimension variant of Step 3:**

- Before invoking analyze-codebase, capture the current HEAD SHA and write initial state to `.claude/loop-state.md`:
  ```bash
  git log -1 --format=%H  # → starting_commit_sha
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
- Wait for all stages (1–10) to complete and plans to be written to disk.
- Find each plan at `.code-analysis/plans/*-{DIMENSION}-plan.md` (use latest date).
- Find latest scores in `.code-analysis/reports/*-scores.json`.
- Extract scores for all target dimensions.
- **Dimensions already at target on initial scan:** Mark as met in `current_scores` but do NOT remove from the scan list — they are still scanned each iteration for cross-dimension context. Exclude from batch selection. Log: `"{dimension} already at {score} (target {target}), skipping fixes — still scanning for cross-dimension context"`. If all dimensions already meet their targets → output `SCORE_REACHED`, done.
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
- Go to Step 4 (batch selection). **Note:** Single-dimension Step 3 continues to go to Step 7 (re-scan, unchanged). Multi-dimension goes to Step 4 because the first batch hasn't been selected yet from the multi-plan priority queue.

### Step 4 — Brainstorm & Plan the Next Batch

Write `phase: planning` and `last_updated_at` to `.claude/loop-state.md`.

**Multi-dimension batch selection:**

When in multi-dimension mode, findings are selected across ALL dimensions' plans using a gap-weighted priority algorithm:

1. Compute each dimension's gap: `gap = target - current_score`
2. Dimensions already at or above target: gap = 0 (excluded from selection)
3. Score each finding: `priority = severity_weight × gap_of_its_dimension`
   - Severity weights: critical=3, high=2, medium=1, low=0.5
4. Sort by priority descending, pick top 3-5 (not yet in `completed_finding_ids`)
5. Effort tiebreaker: among equal-priority findings, prefer smaller effort (trivial → small → medium → large → xl)

**Example:** Structure at 1.0 (target 8, gap=7), quality at 5.0 (target 9, gap=4). A high-severity structure finding scores `2 × 7 = 14`, a high-severity quality finding scores `2 × 4 = 8`. Structure findings get picked first.

**Cross-dimension fixes:** When a fix resolves findings in multiple dimensions (e.g., refactoring a god struct that spans structure and quality), add ALL affected finding IDs to `completed_finding_ids` regardless of dimension. The re-scan naturally drops resolved findings from all dimensions.

**Single-dimension mode:** Unchanged — select next 3-5 findings from the plan, prioritizing trivial → small → medium effort.

Before touching code, select the next 3–5 findings from the plan (not yet in `completed_finding_ids`, prioritizing XS → S → M effort).

**Gate:** If every finding in this batch is an XS-effort mechanical fix (rename, delete unused import, bump version, whitespace), skip Steps 4a–4c and go directly to Step 5 to avoid overhead.

**XS-gate in multi-dimension mode:** The trivial-effort gate applies to the batch as a whole, regardless of how many dimensions are represented. A batch with 3 trivial arch findings and 1 small patterns finding goes through the full design pipeline.

Otherwise, run the superpowers design pipeline on this batch:

**4a. Brainstorm** — invoke `superpowers:brainstorming` skill with the selected findings as input.
  - Scope: only the findings selected for this iteration (not the full plan).
  - Output: a design doc describing the approach for each finding.
  - Skip the visual companion offer (not applicable in a loop context).
  - Auto-approve the design if every finding's recommended action is a single concrete action (e.g. "move X to module Y") with no design alternatives needed.

**4b. Write implementation plan** — invoke `superpowers:writing-plans` skill using the brainstorm output.
  - Plan scope: only this batch, not the full dimension.
  - **Stay on current branch** — do NOT invoke `superpowers:using-git-worktrees`.
  - Add this note at the top of the generated plan file:
    ```
    branch: current (no worktree — ralph-loop manages its own commit cadence)
    ```

**4c. Execute plan** — Write `phase: implementing` and `last_updated_at` to `.claude/loop-state.md`.
  invoke `superpowers:subagent-driven-development` skill (always prefer subagents over `superpowers:executing-plans`).
  - Skip the `superpowers:finishing-a-development-branch` sub-skill (ralph-loop handles commits in Step 6).
  - Follow the plan steps exactly; stop immediately on any blocker.

After execution completes, add the implemented finding IDs to `completed_finding_ids` in `.claude/loop-state.md`.

### Step 5 — Subsequent Runs: Implement Next Batch (mechanical fixes only)

Used when the batch selected in Step 4 consists entirely of XS-effort mechanical fixes (skipping the design pipeline):

Write `phase: implementing` and `last_updated_at` to `.claude/loop-state.md`.

- **Single-dimension:** Read plan at `plan_path` from state file.
- **Multi-dimension:** Read plans from all `plan_paths` entries. Identify the batch of trivial findings NOT yet in `completed_finding_ids` across all dimensions, using the gap-weighted priority from Step 4.
- Identify the batch of XS findings NOT yet in `completed_finding_ids`.
- Implement them directly:
  - Read each affected file before editing it.
  - Make the minimal code change that resolves the finding.
  - Do NOT refactor unrelated code.
- Add the implemented finding IDs to `completed_finding_ids` in `.claude/loop-state.md`.

### Step 6 — Commit

- Stage all modified files individually (never `git add -A`).
- Commit to main:
  - **Single-dimension:** `git commit -m 'fix(DIMENSION): <one-line summary>'`
  - **Multi-dimension:** `git commit -m 'fix(ralph-loop): <one-line summary> [dim1,dim2]'`
    In multi-dimension mode, the commit scope is always `ralph-loop`, even if a particular batch only contains findings from a single dimension. The bracket suffix lists which dimensions' findings were addressed in that batch.
- After successful commit:
  - Capture SHA: `git log -1 --format=%H`
  - Update `.claude/loop-state.md`:
    - `phase: committed`
    - `last_commit_sha: <captured SHA>`
    - Increment `iteration`
    - Update `last_updated_at`

### Step 7 — Re-scan

- Write `phase: rescanning` and `last_updated_at` to `.claude/loop-state.md`.
- **Determine scan mode** — check `iteration` from state file:
  - If `iteration % 3 == 0` (every 3rd iteration: 3, 6, 9, …) → **full re-discovery scan** (no `--changed-files-hint`)
  - Otherwise → **carry-forward scan** (with `--changed-files-hint`)

#### Carry-forward scan (default)

- Compute changed files since **loop start** (accumulated diff):
  ```bash
  git diff --name-only {starting_commit_sha}..HEAD
  ```
  This uses `starting_commit_sha` (not `last_commit_sha`) so that ALL files modified across the entire loop are re-scanned, preventing carry-forward drift from narrow diff scope.
- Run a draft scan:
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

#### Full re-discovery scan (every 3rd iteration)

- Run a draft scan **without** `--changed-files-hint`:
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
  This forces scanners to re-verify ALL previous findings and scan the full codebase for new ones, breaking the carry-forward ratchet effect where findings can be incorrectly marked as resolved and never rediscovered.
  Log: `"Iteration {N}: full re-discovery scan (carry-forward ratchet break)"`

#### Post-scan update

- Read the new score from `.code-analysis/reports/*-scores.json` (latest date file).
- Update `.claude/loop-state.md`:
  - `phase: planning`
  - `current_score: <new score>`
  - Append new score to `score_history`
  - **Multi-dimension:** Update all entries in `current_scores`, append full score map to `score_history`
  - Update `last_updated_at`
- Note: phase transitions to `planning` (not `committed`) because the next action is selecting a new batch — not re-scanning again.

### Step 8 — Check Completion

If `current_score >= TARGET`:
- Write `phase: done` and `last_updated_at` to `.claude/loop-state.md`.
- Output exactly:
```
<promise>SCORE_REACHED</promise>
```

**Multi-dimension:** If `current_scores[dim] >= targets[dim]` for every dimension:
- Write `phase: done` and `last_updated_at` to `.claude/loop-state.md`.
- Output exactly:
```
<promise>SCORE_REACHED</promise>
```

### Step 8b — Final Verification Scan (after SCORE_REACHED)

Before outputting `<promise>SCORE_REACHED</promise>`, run a final verification scan to catch carry-forward inflation:

1. Run a fresh full scan **without** `--changed-files-hint` on all loop dimensions:
   - **Single-dimension:** `/analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics [--model MODEL_SPEC if provided]`
   - **Multi-dimension:** `/analyze-codebase --dimensions=dim1,dim2,... --draft-only --skip-critics [--model MODEL_SPEC if provided]`
   Log: `"Running final verification scan (full codebase, no carry-forward)"`

2. Read verified scores from `.code-analysis/reports/*-scores.json`.

3. Compare loop scores vs verified scores for each dimension:
   - If `|loop_score - verified_score| <= 2.0` for ALL dimensions → scores confirmed.
     Update `current_score` / `current_scores` with verified values. Proceed to output `SCORE_REACHED`.
   - If `|loop_score - verified_score| > 2.0` for ANY dimension → **score inflation detected**.
     Log warning: `"Score inflation detected: {dimension} loop={loop_score} verified={verified_score} (delta={delta})"`
     Update `current_score` / `current_scores` with verified values.
     If verified scores still meet targets → proceed to output `SCORE_REACHED` with verified scores.
     If verified scores do NOT meet targets → set `phase: planning`, log `"Continuing loop with verified scores"`, and resume at Step 4.

**Mid-loop dimension completion** (multi-dimension only): When a dimension reaches its target but others haven't:
- Log: `"{dimension} reached {score} (target {target}) — continuing for {remaining dimensions}"`
- That dimension's findings are no longer selected in batch picks
- Still scanned each iteration (cross-dimension context)
- If score drops below target due to another fix, re-enters fix pool

### Step 9 — Refresh Plan if Exhausted

If all plan steps are completed but score < TARGET, the codebase has changed enough to warrant a fresh scan. Clear `completed_finding_ids` and delete `loop-state.md`, then on the next iteration a new plan will be generated (Step 3).

**Multi-dimension:**
- **One dimension's plan exhausted, score below target:** Clear its IDs from `completed_finding_ids` using the finding ID prefix (e.g., `STRC-*` belongs to structure, `QUAL-*` to quality). Next scan generates a fresh plan for that dimension. Other dimensions continue using their existing plans.
- **All plans exhausted, any score below target:** Clear all `completed_finding_ids`, delete `loop-state.md`. Next iteration starts fresh (Step 3).

## How to Run

### Single-dimension (backward-compatible)

Run one dimension at a time. Pass this skill's content as the ralph-loop prompt,
replacing `DIMENSION` with the target dimension flag and `TARGET` with the desired
minimum score (e.g. 6 for a quick win, 9 for full quality):

```bash
/ralph-loop --completion-promise "SCORE_REACHED" --max-iterations 20 "
<paste Steps 1–9 above with DIMENSION and TARGET replaced>
"
```

### Multi-dimension

```bash
/code-analysis:ralph-loop --targets="struct:8,quality:9,security:10" --completion-promise "SCORE_REACHED" --max-iterations 10
```

All target dimensions are scanned together each iteration, preserving cross-scanner context. Findings are selected across all dimensions using a gap-weighted priority algorithm. The loop exits when every dimension reaches its own target.

### Max iterations exhausted

`--max-iterations` applies to total loop count across all dimensions. When exhausted:

```
Ralph-loop stopped after 6 iterations (max reached)
  structure: 1.0 -> 7.5 (target: 8) -- not reached
  quality: 1.0 -> 9.0 (target: 9) -- reached
```

### Error Handling (multi-dimension)

| Scenario | Resolution |
|----------|-----------|
| One dimension's plan generation fails | Log warning, continue with other dimensions. Retry plan generation on next re-scan. |
| All findings are xl effort | Proceed normally. Log: `"Only xl-effort findings remaining, iterations may be slow"` |
| Fix in dimension A introduces new finding in dimension B | Re-scan catches it, batch selection picks it up if impactful enough (gap-weighted priority) |
| Dimension reaches target then regresses below target | Re-enters fix pool automatically — mid-loop completion is reversible |

### Dimension Flags

| Flag | Dimension | Why First |
|------|-----------|-----------|
| `struct` | Structure | Fewest findings, fastest win |
| `security` | Security | 1 critical clears fast |
| `quality` | Quality | Many items spanning code health, debt, and perf |
| `testing` | Testing | Coverage gaps + dependency hygiene, largest effort, do last |

## Verification After Each Dimension

```bash
# Score should be ≥ TARGET
cat .code-analysis/reports/*-scores.json | grep DIMENSION

# No regressions (run project-specific test suite)
# e.g.: cargo test, npm test, pytest, etc.

# Commits on main
git log --oneline -10
```

## Files

| File | Purpose |
|------|---------|
| `.claude/loop-state.md` | Ephemeral state, deleted after dimension finishes |
| `.code-analysis/plans/` | Plans written by analyze-codebase |
| `.code-analysis/reports/` | Scores and analysis reports |
| `.code-analysis/scan-reports/` | Raw dimension scan JSON |
