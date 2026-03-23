---
name: ralph-loop
version: 0.8.0
description: |
  This skill should be used when iteratively improving codebase dimension scores to target thresholds
  using analyze-codebase + ralph-loop. Supports single-dimension (positional args)
  or multi-dimension (--targets flag) with per-dimension target scores.
  Applies when the user wants to fix findings across one or more dimensions,
  run a score improvement loop, or automate refactoring until quality thresholds are reached.
  Supports --plugin flag for Claude Code plugin analysis dimensions.
  Use when the user asks to "run ralph loop", "improve dimension scores", "iterate until score reaches target", or "automate refactoring until targets".
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent", "Skill"]
---

# Ralph-Loop × Analyze-Codebase

Iteratively scan codebase dimensions, implement the generated refactoring plans, commit to main, and loop until all dimension scores reach their targets. Supports single-dimension mode (backward-compatible) and multi-dimension mode with per-dimension target scores.

## Why a Loop is Required

The scoring formula is `score = max(1.0, 10 - min(raw, 9))` where `raw = 3×critical + 2×high + 1×medium + 0.5×low`. Because the penalty is capped at 9, **all dimensions with many findings sit at the 1.0 floor**. Individual scattered fixes appear invisible. Clear enough findings to bring `raw < 9` before the score moves at all.

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
- `--model` flag → stored as-is, passed through verbatim to all `/analyze-codebase` invocations.

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

```markdown
converged_dimensions: []
converged_at_iteration: {}
```

> **Converged dimensions (v0.8.0):** Dimensions whose score has reached the target. Skipped during re-scans
> except on safety-net iterations (every 5th). If a converged dimension regresses, it is removed from the list.

```markdown
mechanical_dimensions: [manifest-structure, skill-quality, agent-design, hook-correctness, marketplace-consistency, convention-adherence]
```

> **Mechanical dimensions (v0.8.0):** Only present when `--plugin` is set. Populated automatically from the
> Mechanical Dimensions list. Findings from these dimensions always skip the superpowers pipeline.

> **Note on finding ID format:** `completed_finding_ids` uses the scanner's fingerprint ID format: `{DIM}-{file_hash6}-{title_hash4}` (e.g., `STRC-8f3a21-a1b2`). Title-hash IDs are stable across code shifts, unlike the deprecated line-bucket format.

> **Scoring formula:** `current_score` and `target` use the authoritative formula from `skills/reconcile-report/SKILL.md`: `score = max(1.0, 10 - min(raw, 9))` where `raw = 3×critical + 2×high + 1×medium + 0.5×low`. The floor is **1.0**, not 0.

For multi-dimension state file format and cross-mode details, Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/multi-dimension.md`.

## Every Iteration: Steps in Order

### Step 1 — Read State & Recover

Check if `.claude/loop-state.md` exists and read it.

**If no state file** → first run (go to Step 3).

**If state file exists** → detect mode from `mode` key, then recover based on stored `phase`.

For full recovery protocol (all CASE blocks, SHA verification, phase state machine), Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/recovery-protocol.md`.

### Step 2 — Check Completion

**Single-dimension:** If `phase` is `done` or `current_score >= target`, output exactly:
```
<promise>SCORE_REACHED</promise>
```
Then stop. Do nothing else.

**Multi-dimension:** If `phase` is `done` or `current_scores[dim] >= targets[dim]` for every dimension, output `SCORE_REACHED` and stop.

### Step 3 — First-Run: Generate Plan (only if no state file)

- Capture current HEAD SHA, write initial state with `phase: scanning`.
- Invoke analyze-codebase: `/analyze-codebase --dimensions=DIMENSION --skip-critics [--model MODEL_SPEC if provided]`
  When `--plugin` is set, pass `--plugin` to all `/analyze-codebase` invocations.
- At Stage 5 user checkpoint, automatically choose **Proceed to refactoring plans**.
- Wait for all stages (1-10) to complete and plans to be written to disk.
- Find the plan at `.code-analysis/plans/*-DIMENSION-plan.md` (use latest date).
- Extract `current_score` from `.code-analysis/reports/*-scores.json`.
- Update state: set `phase: planning`, record score, plan path, `iteration: 0`.
- Go to Step 7.

For multi-dimension variant of Step 3, Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/multi-dimension.md`.

### Mechanical Dimensions (v0.8.0)

Plugin dimensions where ALL fixes are known to be mechanical edits (markdown, JSON, frontmatter, file moves/renames).
Findings from mechanical dimensions skip the superpowers pipeline (Step 4) and go directly to Step 5 (implement directly),
regardless of effort level.

**Mechanical by default (when `--plugin`):**
- `manifest-structure` — JSON edits, file moves
- `skill-quality` — markdown edits, frontmatter additions
- `agent-design` — markdown edits, examples additions
- `hook-correctness` — JSON schema fixes, script edits
- `marketplace-consistency` — JSON alignment, README edits
- `convention-adherence` — pattern replacements, file renames

**Non-mechanical (even in `--plugin` mode):**
- `quality` — may require code refactoring
- `security` — may require architectural changes

**Standard codebase dimensions** (structure, testing): follow existing effort-based gating (unchanged).

### Step 4 — Brainstorm & Plan the Next Batch

Write `phase: planning` and `last_updated_at` to state.

**Single-dimension:** Select next 3-5 findings from the plan (not yet in `completed_finding_ids`, prioritizing XS → S → M effort).

**Multi-dimension:** Use gap-weighted priority algorithm across all dimensions' plans. Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/multi-dimension.md` for the batch selection algorithm.

**Gate:** Skip Steps 4a-4c and go directly to Step 5 if ANY of:
- Every finding in the batch is XS-effort mechanical (existing behavior), OR
- Every finding in the batch comes from a mechanical dimension (v0.8.0; see Mechanical Dimensions above)

Otherwise, run the superpowers design pipeline:

**4a. Brainstorm** — invoke `superpowers:brainstorming` with selected findings. Auto-approve if every finding's action is a single concrete action with no design alternatives.

**4b. Write implementation plan** — invoke `superpowers:writing-plans`. Stay on current branch (no worktree). Add note: `branch: current (no worktree — ralph-loop manages its own commit cadence)`.

**4c. Execute plan** — Write `phase: implementing`. Invoke `superpowers:subagent-driven-development`. Skip `superpowers:finishing-a-development-branch`. Follow plan steps exactly; stop on any blocker.

After execution, add implemented finding IDs to `completed_finding_ids`.

### Step 5 — Implement Next Batch (mechanical fixes only)

Write `phase: implementing` and `last_updated_at` to state.

- Read plan(s) from state file. Identify XS findings not yet in `completed_finding_ids`.
- Implement directly: read each affected file before editing, make minimal changes, do NOT refactor unrelated code.
- Add implemented finding IDs to `completed_finding_ids`.

### Step 6 — Commit

- Stage all modified files individually (never `git add -A`).
- **Single-dimension:** `git commit -m 'fix(DIMENSION): <one-line summary>'`
- **Multi-dimension:** `git commit -m 'fix(ralph-loop): <one-line summary> [dim1,dim2]'`
- Capture SHA, update state: `phase: committed`, `last_commit_sha`, increment `iteration`.

### Step 7 — Re-scan

**Before dispatching re-scan (v0.8.0 skip-clean optimization):**

For multi-dimension mode, check which dimensions have converged:
1. For each dimension in targets: if `current_scores[dim] >= targets[dim]` AND dimension is not already in `converged_dimensions`, add it with `converged_at_iteration: <current iteration>`
2. If `iteration % 5 != 0` (not a safety-net iteration): exclude `converged_dimensions` from the `--dimensions` list passed to analyze-codebase
3. If `iteration % 5 == 0` (safety-net iteration): scan ALL target dimensions including converged ones. Log: `"Safety-net iteration {N}: scanning all dimensions including converged"`
4. After re-scan: if any converged dimension's score dropped below its target, remove from `converged_dimensions` and log: `"Regression detected: {dim} dropped to {score} (target {target}), resuming scanning"`

**Single-dimension mode:** Skip-clean does not apply (only one dimension to scan).

For full re-scan logic (carry-forward vs full re-discovery, scan commands, post-scan update), Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/verification-scan.md`.

### Step 8 — Check Completion

If score >= target (single-dimension) or all scores >= targets (multi-dimension):
- Write `phase: done`.
- Run final verification scan before outputting `SCORE_REACHED`.

For final verification scan details (Step 8b) and score inflation detection, Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/verification-scan.md`.

### Step 9 — Refresh Plan if Exhausted

If all plan steps are completed but score < TARGET, clear `completed_finding_ids` and delete `loop-state.md`. Next iteration generates a new plan (Step 3).

For multi-dimension plan refresh logic, Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/multi-dimension.md`.

## How to Run

### Single-dimension (backward-compatible)

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
