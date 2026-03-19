# Ralph-Loop Crash Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add git-anchored checkpointing and phase-based crash recovery to the ralph-loop skill so interrupted sessions can resume without re-scanning or re-implementing.

**Architecture:** Replace the 3-field loop-state.md with an 12-field state file that tracks phase, git commit SHA, iteration count, and score history. Add recovery logic (Step 1.5) that reads phase + SHA to determine exactly where to resume.

**Tech Stack:** Markdown skill files (no code — this is a prompt engineering change to `skills/ralph-loop/SKILL.md`)

**Spec:** `docs/superpowers/specs/2026-03-19-ralph-loop-crash-recovery-design.md`

---

### Task 1: Update State File Format

**Files:**
- Modify: `skills/ralph-loop/SKILL.md:19-27` (State File section)

- [ ] **Step 1: Replace the State File section**

Replace the current 3-field state file block (lines 19-27) with the enhanced format from the spec:

```markdown
## State File

`.claude/loop-state.md` persists between ralph-loop iterations:

\`\`\`markdown
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
\`\`\`

> **Note on finding ID format:** `completed_finding_ids` uses whatever ID format the scanner produces. If fingerprint IDs are implemented, these will be fingerprint-format IDs (e.g., `ARCH-8f3a21-0370`). Otherwise they use the current scanner-assigned format.

> **Scoring formula:** `current_score` and `target` use the authoritative formula from `skills/reconcile-report/SKILL.md`: `score = max(1.0, 10 - min(raw, 9))` where `raw = 3×critical + 2×high + 1×medium + 0.5×low`. The floor is **1.0**, not 0.

### Phase State Machine

\`\`\`
scanning → planning → implementing → committed → rescanning → planning (next iteration)
                                                                  ↓
                                                           score >= target → done
\`\`\`

Each phase transition writes to `loop-state.md` **before** starting the next phase. A crash at any point leaves the state file pointing to the last *completed* phase.

| Phase | Meaning | What was completed before entering |
|-------|---------|-----------------------------------|
| `scanning` | Initial dimension scan in progress | Nothing yet (first run) |
| `planning` | Selecting/generating plan for next batch | Scan complete, score known |
| `implementing` | Subagents are making code changes | Plan selected, batch chosen |
| `committed` | Changes committed to git | All changes committed, SHA recorded |
| `rescanning` | Re-scan in progress to measure new score | Commit verified |
| `done` | Target score reached | Final score recorded |
```

- [ ] **Step 2: Verify the edit**

Read the file and confirm the State File section has the new format with all 12 fields and the phase state machine.

- [ ] **Step 3: Commit**

```bash
git add skills/ralph-loop/SKILL.md
git commit -m "feat(ralph-loop): enhanced state file format with phase tracking and git anchor"
```

---

### Task 2: Add Recovery Logic (Step 1 → Step 1.5)

**Files:**
- Modify: `skills/ralph-loop/SKILL.md:31-34` (Step 1 — Read State)

- [ ] **Step 1: Replace Step 1 with enhanced version including recovery**

Replace the current Step 1 (lines 31-34) with the recovery-aware version from the spec. The new Step 1 reads state AND determines where to resume:

```markdown
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
```

- [ ] **Step 2: Verify the edit**

Read the updated Step 1 and confirm all 6 phase cases are present with correct recovery actions.

- [ ] **Step 3: Commit**

```bash
git add skills/ralph-loop/SKILL.md
git commit -m "feat(ralph-loop): add crash recovery logic with phase-based resume"
```

---

### Task 3: Add Phase Writes to Steps 3-8

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` (Steps 3, 4, 5, 6, 7, 8)

- [ ] **Step 1: Update Step 3 (First Run)**

Add phase writes: `phase: scanning` before analyze-codebase invocation, then `phase: planning` + `starting_score` + `current_score` + `score_history: [<initial_score>]` + `started_at` after scan completes.

In the state file creation block, replace the current 3-field format:
```
current_score: <score>
plan_path: <path>
completed_finding_ids: []
```
with:
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
started_at: <ISO 8601 now>
last_updated_at: <ISO 8601 now>
```

- [ ] **Step 2: Update Step 4 (Brainstorm & Plan)**

Add at entry: "Write `phase: planning` to loop-state.md before selecting the batch."

- [ ] **Step 3: Update Step 4c/5 (Implement)**

Add: "Write `phase: implementing` to loop-state.md before dispatching subagents."

- [ ] **Step 4: Update Step 6 (Commit)**

After the `git commit` instruction, add:
```
- Capture SHA: `git log -1 --format=%H`
- Update loop-state.md: `phase: committed`, `last_commit_sha: <SHA>`, increment `iteration`, update `last_updated_at`
```

- [ ] **Step 5: Update Step 7 (Re-scan)**

Add before analyze-codebase: "Write `phase: rescanning` to loop-state.md."
After score extracted, change to: "Write `phase: planning`, update `current_score`, append new score to `score_history`, update `last_updated_at`."

Add note: "Phase transitions to `planning` (not `committed`) because the next action is selecting a new batch."

- [ ] **Step 6: Update Step 8 (Check Completion)**

Add: "If score >= target: write `phase: done` to loop-state.md, then output SCORE_REACHED."

- [ ] **Step 7: Verify all phase writes**

Read through the entire SKILL.md and verify every step writes the correct phase before its action.

- [ ] **Step 8: Commit**

```bash
git add skills/ralph-loop/SKILL.md
git commit -m "feat(ralph-loop): add phase transition writes to all iteration steps"
```

---

### Task 4: Final Review & Version Bump

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` (full review)
- Modify: `.claude-plugin/plugin.json` (version bump)

- [ ] **Step 1: Read the complete SKILL.md end-to-end**

Verify:
- State file section has 12 fields + phase state machine
- Step 1 has recovery logic for all 6 phases
- Steps 3-8 all have phase transition writes
- Backwards compat note for old state files
- No orphaned references to old 3-field format

- [ ] **Step 2: Commit final cleanup if needed**

```bash
git add skills/ralph-loop/SKILL.md
git commit -m "chore(ralph-loop): finalize crash recovery implementation"
```
