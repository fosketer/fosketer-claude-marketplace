# Recovery Protocol

## Phase State Machine

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

## SHA Verification Logic

Compare `last_commit_sha` from state file against current HEAD:

- **HEAD matches** — normal resume at the phase-appropriate step
- **HEAD is ahead** — external commits detected. Log warning, re-scan to recalibrate
- **HEAD is behind** — prompt user: "State records commit {sha} but HEAD is at {head_sha} (behind). Options:
  1. Keep state and re-scan from current HEAD
  2. Delete state and start fresh"

Do NOT delete state without user confirmation.

## Recovery by Phase

### CASE "done"

Output `SCORE_REACHED`. Stop.

### CASE "committed"

Verify: `git log -1 --format=%H` == `last_commit_sha`?
- YES: resume at Step 7 (re-scan)
- NO, HEAD is ahead: external commits detected. Log warning, re-scan to recalibrate (Step 7)
- NO, HEAD is behind: prompt user (see SHA verification logic above)

### CASE "rescanning"

Re-scan was interrupted. Restart Step 7.

### CASE "implementing"

First, check if subagents committed independently:

`git log -1 --format=%H` vs `last_commit_sha`:
- HEAD is AHEAD: subagents committed. Update `last_commit_sha`, treat as "committed" and go to Step 7.
- HEAD is BEHIND: prompt user (same as committed HEAD-behind case).

If HEAD matches (no independent commits):

`git status --porcelain`:
- CLEAN: no changes from interrupted implementation. Log message, resume Step 4.
- DIRTY: prompt user: "Found uncommitted changes from interrupted session. Options:
  1. Review changes, attempt compilation, and commit if it passes
  2. Discard changes (git checkout .) and re-implement this batch
  3. Start fresh (delete state, re-scan dimension)"

### CASE "planning"

Plan generation was interrupted. Restart Step 4.

### CASE "scanning"

Initial scan was interrupted. Restart Step 3.

## Mode Detection and Backward Compatibility

**Mode detection:** Check for `mode` key in state file.
- If absent: single-dimension recovery (existing logic)
- If `mode: multi`: multi-dimension recovery (Read `${CLAUDE_PLUGIN_ROOT}/skills/ralph-loop/references/multi-dimension.md` for details)

**Backwards compatibility:** If `phase` key is absent (old 3-field format), treat as `phase: committed`. If `last_commit_sha` is also absent, skip SHA verification entirely and resume at Step 7 (re-scan).

## Single-Dimension Recovery

Read `dimension` and `target` from state (no need to re-specify via args).
If args are provided AND differ from state, warn: "State says {dim}/{target}, args say {new_dim}/{new_target}. Use state values? [Y/n]"
