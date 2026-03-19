---
name: ralph-loop
description: |
  Use when iteratively improving codebase dimension scores to target thresholds
  using analyze-codebase + ralph-loop. Supports single-dimension (positional args)
  or multi-dimension (--targets flag) with per-dimension target scores.
  Applies when the user wants to fix findings across one or more dimensions,
  run a score improvement loop, or automate refactoring until quality thresholds are reached.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, Skill
---

# Ralph-Loop × Analyze-Codebase

Iteratively scan codebase dimensions, implement the generated refactoring plans, commit to main, and loop until all dimension scores reach their targets. Supports single-dimension mode (backward-compatible) and multi-dimension mode with per-dimension target scores.

## Why a Loop is Required

The scoring formula is `score = max(1.0, 10 - min(raw, 9))` where `raw = 3×critical + 2×high + 1×medium + 0.5×low`. Because the penalty is capped at 9, **all dimensions with many findings sit at the 1.0 floor**. Individual scattered fixes appear invisible. You must clear enough findings to bring `raw < 9` before the score moves at all.

## State File

`.claude/loop-state.md` persists between ralph-loop iterations:

```markdown
# Ralph-Loop State
dimension: architecture
target: 10
current_score: 6.0
starting_score: 1.0
plan_path: .code-analysis/plans/2026-03-19-arch-plan.md
completed_finding_ids: [arch-001, arch-003, arch-005]
last_commit_sha: 2614d94a
phase: committed
iteration: 3
score_history: [1.0, 4.5, 6.0]
started_at: 2026-03-19T06:25:42Z
last_updated_at: 2026-03-19T14:26:48Z
```

> **Note on finding ID format:** `completed_finding_ids` uses whatever ID format the scanner produces. If fingerprint IDs are implemented, these will be fingerprint-format IDs (e.g., `ARCH-8f3a21-0370`). Otherwise they use the current scanner-assigned format.

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

## Every Iteration: Steps in Order

### Step 1 — Read State & Recover

Check if `.claude/loop-state.md` exists and read it.

**If no state file** → first run (go to Step 3).

**If state file exists:**
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

If `phase` is `done` or `current_score >= TARGET`, output exactly:
```
<promise>SCORE_REACHED</promise>
```
Then stop. Do nothing else.

> Note: On restart, the recovery logic in Step 1 handles phase-based completion checks. Step 2 is the fallback for within-session iteration.

### Step 3 — First-Run: Generate Plan (only if no state file)

- Before invoking analyze-codebase, write initial state to `.claude/loop-state.md`:
  ```
  dimension: DIMENSION
  target: TARGET
  phase: scanning
  started_at: <ISO 8601 now>
  last_updated_at: <ISO 8601 now>
  ```
- Invoke the analyze-codebase skill for this dimension:
  ```
  /analyze-codebase --dimensions=DIMENSION --skip-critics
  ```
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
  phase: planning
  iteration: 0
  score_history: [<score>]
  started_at: <preserved from above>
  last_updated_at: <ISO 8601 now>
  ```
- Go to Step 7.

### Step 4 — Brainstorm & Plan the Next Batch

Write `phase: planning` and `last_updated_at` to `.claude/loop-state.md`.

Before touching code, select the next 3–5 findings from the plan (not yet in `completed_finding_ids`, prioritizing XS → S → M effort).

**Gate:** If every finding in this batch is an XS-effort mechanical fix (rename, delete unused import, bump version, whitespace), skip Steps 4a–4c and go directly to Step 5 to avoid overhead.

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

- Read plan at `plan_path` from state file.
- Identify the batch of XS findings NOT yet in `completed_finding_ids`.
- Implement them directly:
  - Read each affected file before editing it.
  - Make the minimal code change that resolves the finding.
  - Do NOT refactor unrelated code.
- Add the implemented finding IDs to `completed_finding_ids` in `.claude/loop-state.md`.

### Step 6 — Commit

- Stage all modified files individually (never `git add -A`).
- Commit to main:
  ```
  git commit -m 'fix(DIMENSION): <one-line summary of what was fixed>'
  ```
- After successful commit:
  - Capture SHA: `git log -1 --format=%H`
  - Update `.claude/loop-state.md`:
    - `phase: committed`
    - `last_commit_sha: <captured SHA>`
    - Increment `iteration`
    - Update `last_updated_at`

### Step 7 — Re-scan

- Write `phase: rescanning` and `last_updated_at` to `.claude/loop-state.md`.
- Compute changed files since last commit:
  ```bash
  git diff --name-only {last_commit_sha}..HEAD
  ```
- Run a fresh draft scan:
  ```
  /analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics \
    --changed-files-hint="{comma-separated file list from git diff}"
  ```
  This enables diff-scoped carry-forward: unchanged files' findings are carried forward without re-reading, reducing re-scan token cost.
- Read the new score from `.code-analysis/reports/*-scores.json` (latest date file).
- Update `.claude/loop-state.md`:
  - `phase: planning`
  - `current_score: <new score>`
  - Append new score to `score_history`
  - Update `last_updated_at`
- Note: phase transitions to `planning` (not `committed`) because the next action is selecting a new batch — not re-scanning again.

### Step 8 — Check Completion

If `current_score >= TARGET`:
- Write `phase: done` and `last_updated_at` to `.claude/loop-state.md`.
- Output exactly:
```
<promise>SCORE_REACHED</promise>
```

### Step 9 — Refresh Plan if Exhausted

If all plan steps are completed but score < TARGET, the codebase has changed enough to warrant a fresh scan. Clear `completed_finding_ids` and delete `loop-state.md`, then on the next iteration a new plan will be generated (Step 3).

## How to Run

Run one dimension at a time. Pass this skill's content as the ralph-loop prompt,
replacing `DIMENSION` with the target dimension flag and `TARGET` with the desired
minimum score (e.g. 6 for a quick win, 9 for full quality):

```bash
/ralph-loop --completion-promise "SCORE_REACHED" --max-iterations 20 "
<paste Steps 1–9 above with DIMENSION and TARGET replaced>
"
```

### Dimension Flags

| Flag | Dimension | Why First |
|------|-----------|-----------|
| `arch` | Architecture | Fewest findings, fastest win |
| `debt` | Tech-debt | Many XS/S effort items |
| `security` | Security | 1 critical clears fast |
| `perf` | Performance | Mostly medium items |
| `patterns` | Patterns | Many low-effort structural fixes |
| `deps` | Dependencies | Cargo.toml updates, mostly XS |
| `quality` | Quality | 20 findings, largest batch |
| `testing` | Testing | 2 criticals, largest effort, do last |

## Verification After Each Dimension

```bash
# Score should be ≥ TARGET
cat .code-analysis/reports/*-scores.json | grep DIMENSION

# No regressions
cd /root/src/claude-k3s-orchestrator/rust && cargo test

# No new warnings
cargo clippy

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
