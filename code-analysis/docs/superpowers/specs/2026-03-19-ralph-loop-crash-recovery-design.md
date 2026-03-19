# Spec A: Ralph-Loop Crash Recovery & Checkpointing

**Date:** 2026-03-19
**Status:** Approved
**Scope:** `skills/ralph-loop/SKILL.md` only — no changes to orchestrator, scanners, or agents
**Motivation:** Session evidence from the claude-automatic-orchestrator project showed 6 of 11 sessions wasted due to OOM kills, SSH failures, and user interrupts. Each restart re-read stale state, re-scanned unnecessarily, and couldn't determine whether prior subagent work was committed.

## Problem Statement

The current `loop-state.md` persists 3 fields: `current_score`, `plan_path`, `completed_finding_ids`. This is insufficient for crash recovery because:

1. **No git anchor**: After a crash, the loop can't verify whether its last batch of changes was committed. It may re-implement already-committed work or skip uncommitted work.
2. **No phase tracking**: The loop doesn't know *where* in the iteration cycle it crashed (scanning? implementing? committing?). Every restart defaults to "re-scan everything."
3. **No session metadata**: Target score, dimension, timing, and score history must be re-specified or reconstructed from git log.
4. **Partial implementation ambiguity**: If subagents made changes but the loop crashed before committing, the working tree is dirty. The loop has no protocol for handling this.

## Design

### 1. Enhanced State File

Replace the current 3-field `loop-state.md` with a richer format:

```markdown
# Ralph-Loop State
dimension: architecture
target: 10
current_score: 6.0
starting_score: 1.0
plan_path: .code-analysis/plans/2026-03-19-arch-plan.md
completed_finding_ids: [ARCH-8f3a21-0370, ARCH-c4d7e2-0120]
last_commit_sha: 2614d94a
phase: committed
iteration: 3
score_history: [1.0, 4.5, 6.0]
started_at: 2026-03-19T06:25:42Z
last_updated_at: 2026-03-19T14:26:48Z
```

| Field | Type | Purpose |
|-------|------|---------|
| `dimension` | string | Which dimension is being improved |
| `target` | number | Target score (eliminates re-specification on restart) |
| `current_score` | number | Latest known score |
| `starting_score` | number | Baseline for effectiveness tracking |
| `plan_path` | string | Path to the active refactoring plan |
| `completed_finding_ids` | array | Finding IDs resolved so far |
| `last_commit_sha` | string | SHA of the last ralph-loop commit — git anchor |
| `phase` | enum | Where in the iteration cycle (see Section 2) |
| `iteration` | number | Current iteration counter |
| `score_history` | array | Score after each re-scan (enables trend analysis) |
| `started_at` | ISO 8601 | When the loop started |
| `last_updated_at` | ISO 8601 | When state was last written |

### 2. Phase State Machine

```
scanning → planning → implementing → committed → rescanning
                                                      ↓
                                               [next iteration: planning]
                                                      ↓
                                               score >= target → done
```

Each phase transition writes to `loop-state.md` **before** starting the next phase. A crash at any point leaves the state file pointing to the last *completed* phase.

Phase definitions:

| Phase | Meaning | What was completed before entering |
|-------|---------|-----------------------------------|
| `scanning` | Initial dimension scan in progress | Nothing yet (first run) |
| `planning` | Selecting/generating plan for next batch | Scan complete, score known |
| `implementing` | Subagents are making code changes | Plan selected, batch chosen |
| `committed` | Changes committed to git | All changes committed, SHA recorded |
| `rescanning` | Re-scan in progress to measure new score | Commit verified |
| `done` | Target score reached | Final score recorded |

### 3. Recovery Logic (New Step 1.5)

On restart, after reading `loop-state.md`:

```
IF no state file → first run (existing Step 3)

IF state file exists:
  Read dimension and target from state (no need to re-specify via args)

  SWITCH phase:
    CASE "done":
      Output SCORE_REACHED. Stop.

    CASE "committed":
      Verify: git log -1 --format=%H == last_commit_sha?
        YES → resume at Step 7 (re-scan)
        NO, HEAD is ahead → external commits detected
          Log: "HEAD is {HEAD_SHA}, expected {last_commit_sha}. External commits detected."
          Re-scan to recalibrate (Step 7)
        NO, HEAD is behind → should not happen; treat as corruption
          Log warning, delete state, restart fresh (Step 3)

    CASE "rescanning":
      Re-scan was interrupted. Restart Step 7.

    CASE "implementing":
      Check: git status --porcelain
        CLEAN working tree → implementation complete but not committed
          Verify compilation: cargo build / npm run build
            SUCCESS → proceed to Step 6 (commit)
            FAILURE → discard and re-implement: git checkout .
              Resume at Step 4 (select batch)

        DIRTY working tree → partial implementation
          Prompt user with 3 options:
            1. "Review changes, commit what's there, and re-scan"
            2. "Discard changes and re-implement this batch"
            3. "Start fresh (delete state, re-scan dimension)"
          Execute chosen option.

    CASE "planning":
      Plan generation was interrupted. Restart Step 4.

    CASE "scanning":
      Initial scan was interrupted. Restart Step 3.
```

### 4. Modified Ralph-Loop Steps (Delta from Current)

Changes are minimal — only adding phase writes at transition points:

**Step 1 — Read State:**
- Add recovery logic from Section 3
- Read `dimension` and `target` from state file
- If args are provided AND differ from state, warn: "State says {dim}/{target}, args say {new_dim}/{new_target}. Use state values? [Y/n]"

**Step 3 — First Run (Generate Plan):**
- Before invoking analyze-codebase: write `phase: scanning`
- After scan completes and score extracted: write `phase: planning` + `starting_score` + `current_score`

**Step 4 — Brainstorm & Plan Next Batch:**
- At entry: write `phase: planning`
- No other changes

**Step 4c / Step 5 — Implement:**
- Before dispatching subagents: write `phase: implementing`
- After subagents complete and compilation verified: no phase change (Step 6 handles it)

**Step 6 — Commit:**
- After successful `git commit`:
  - Capture SHA: `git log -1 --format=%H`
  - Write `phase: committed`, `last_commit_sha`, increment `iteration`, update `last_updated_at`
  - Append current score to `score_history` (score not yet known — append after Step 7)

**Step 7 — Re-scan:**
- Before invoking analyze-codebase: write `phase: rescanning`
- After score extracted: write `phase: committed`, update `current_score`, append to `score_history`, update `last_updated_at`

**Step 8 — Check Completion:**
- If score >= target: write `phase: done`, output SCORE_REACHED

### 5. Backwards Compatibility

- **Old state files** (3 fields, no `phase`): Detected by absence of `phase` key. Treated as `phase: committed` with no SHA verification. The loop resumes at re-scan — safe default that may repeat one scan but loses no work.
- **Old args format** (`/ralph-loop arch 10`): Still works. On restart, args are optional if state file has `dimension` and `target`.
- **No changes to other skills or agents**: This spec is entirely contained within `ralph-loop/SKILL.md`.

### 6. Files Changed

| File | Change |
|------|--------|
| `skills/ralph-loop/SKILL.md` | Add phase state machine, recovery logic, enhanced state format |

### 7. Verification

After implementation, verify with this scenario:

1. Start ralph-loop on a test dimension
2. Let it complete one iteration (reach `committed` phase)
3. Kill the session (Ctrl+C)
4. Restart ralph-loop — should resume at re-scan without re-implementing
5. Let it reach `implementing` phase
6. Kill the session
7. Restart — should detect dirty/clean working tree and offer recovery options
