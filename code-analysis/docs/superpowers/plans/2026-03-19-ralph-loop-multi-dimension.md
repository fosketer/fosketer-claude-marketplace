# Ralph-Loop Multi-Dimension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend ralph-loop to accept `--targets="dim:score,..."` for multi-dimension iteration with per-dimension target scores and cross-dimension batch selection.

**Architecture:** Two files modified — `skills/ralph-loop/SKILL.md` (core logic) and `README.md` (user docs). All changes are markdown skill definitions, not executable code. The analyze-codebase pipeline and reconciler already support multi-dimension input; only ralph-loop's single-dimension assumption needs updating.

**Tech Stack:** Markdown skill definitions for Claude Code plugin system.

**Spec:** `docs/superpowers/specs/2026-03-19-ralph-loop-multi-dimension-design.md`

**Base path:** `/Users/keven.foster/document-perso/local-claude-marketplace/code-analysis/`

---

### Task 1: Update frontmatter and skill introduction

**Files:**
- Modify: `skills/ralph-loop/SKILL.md:1-17`

- [ ] **Step 1: Update frontmatter description**

Change the `description` field from single-dimension to multi-dimension:

```yaml
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
```

- [ ] **Step 2: Update the skill title and introduction paragraph**

Replace the `# Ralph-Loop x Analyze-Codebase` heading and its introductory paragraph:
```markdown
# Ralph-Loop x Analyze-Codebase

Iteratively scan codebase dimensions, implement the generated refactoring plans, commit to main, and loop until all dimension scores reach their targets. Supports single-dimension mode (backward-compatible) and multi-dimension mode with per-dimension target scores.
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): update frontmatter and intro for multi-dimension support"
```

---

### Task 2: Add input parsing and multi-dimension state file format

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` — insert after "Why a Loop is Required" section, before "State File" section

- [ ] **Step 1: Add Input Parsing section after "Why a Loop is Required"**

Insert after the "Why a Loop is Required" section, before the "State File" section:

```markdown
## Input Parsing

**Single-dimension mode** (backward-compatible):
```bash
/code-analysis:ralph-loop <dimension> <target> [--max-iterations N] [--completion-promise "SCORE_REACHED"]
```

**Multi-dimension mode**:
```bash
/code-analysis:ralph-loop --targets="arch:8,patterns:9,security:10" [--max-iterations N] [--completion-promise "SCORE_REACHED"]
```

### Parsing rules

- Positional args `<dimension> <target>` → single-dimension mode (existing behavior unchanged)
- `--targets` flag → multi-dimension mode (2+ dimensions)
- `--targets` with a single dimension → auto-converted to single-dimension mode for state file consistency
- Cannot mix positional args and `--targets` — error if both provided
- Dimension shorthand: `arch` → architecture, `deps` → dependencies, `perf` → performance, `debt` → tech-debt

### Validation

- Duplicate dimension in `--targets` → error: `"Duplicate dimension: {name}"`
- Target score < 1 or > 10 → error: `"Target must be between 1.0 and 10.0"`
```

- [ ] **Step 2: Add multi-dimension state file format**

Keep the existing single-dimension state file section as-is. Add a new section immediately after it:

```markdown
### Multi-Dimension State File

When running in multi-dimension mode, `.claude/loop-state.md` uses an extended format:

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

**Key differences from single-dimension format:**
- `mode: multi` — identifies multi-dimension state (absent in single-dimension)
- `targets` — map of dimension → target score (replaces `dimension` + `target`)
- `current_scores` / `starting_scores` — maps (replace `current_score` / `starting_score`)
- `plan_paths` — map of dimension → plan path (replaces `plan_path`)
- `completed_finding_ids` — flat list (unchanged; IDs contain dimension prefix e.g. `ARCH-`, `PAT-`)
- `score_history` — entries are maps (replace scalar values)

**Backward compatibility:** If `mode` key is absent, treat as single-dimension (existing format). Old state files work unchanged.

**Exit condition:** Loop exits when `current_scores[dim] >= targets[dim]` for **every** dimension.
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): add input parsing rules and multi-dimension state format"
```

---

### Task 3: Update Step 1 recovery for multi-dimension mode

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` — "Step 1 — Read State & Recover" section

- [ ] **Step 1: Add multi-dimension recovery logic to Step 1**

After the existing "If state file exists:" block (line 71-73), add a mode detection gate:

```markdown
**Mode detection:** Check for `mode` key in state file.
- If absent → single-dimension recovery (existing logic below)
- If `mode: multi` → multi-dimension recovery (see below)

**Multi-dimension recovery:**

1. **Arg mismatch detection**: Compare `--targets` from CLI args against stored `targets` map.
   - If maps are identical → resume at the stored `phase`
   - If maps differ → prompt user: `"State has targets {stored}, args have {new}. Resume existing loop, or delete and start fresh?"`
   - If positional args were provided instead of `--targets` → error: `"Active multi-dimension loop found. Use --targets or delete .claude/loop-state.md"`

2. **Phase recovery**: Same logic as single-dimension — read `phase` from state, execute the corresponding recovery action. The only difference: recovery reads `targets`/`current_scores`/`plan_paths` (maps) instead of `dimension`/`target`/`current_score`/`plan_path` (scalars).

3. **SHA verification**: Same as single-dimension — compare `last_commit_sha` against HEAD.
```

Also add to the error handling at the top of Step 1:

```markdown
**Cross-mode conflicts:**
- Existing single-dimension state + `--targets` flag → error: `"Active single-dimension loop found. Complete or delete .claude/loop-state.md first"`
- Existing multi-dimension state + positional args → error: `"Active multi-dimension loop found. Use --targets or delete .claude/loop-state.md first"`
```

- [ ] **Step 2: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): add multi-dimension recovery logic to Step 1"
```

---

### Task 4: Update Steps 2-3 for multi-dimension mode

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` — "Step 2 — Check Completion" and "Step 3 — First-Run: Generate Plan" sections

- [ ] **Step 1: Update Step 2 completion check**

Add multi-dimension completion logic:

```markdown
### Step 2 — Check Completion

**Single-dimension:** If `phase` is `done` or `current_score >= target`, output `<promise>SCORE_REACHED</promise>` and stop.

**Multi-dimension:** If `phase` is `done` or `current_scores[dim] >= targets[dim]` for every dimension, output `<promise>SCORE_REACHED</promise>` and stop.
```

- [ ] **Step 2: Update Step 3 initial scan for multi-dimension**

Add a multi-dimension variant after the existing single-dimension Step 3:

```markdown
**Multi-dimension variant of Step 3:**

- Before invoking analyze-codebase, write initial state to `.claude/loop-state.md`:
  ```
  mode: multi
  targets: { architecture: 8, patterns: 9 }
  phase: scanning
  started_at: <ISO 8601 now>
  last_updated_at: <ISO 8601 now>
  ```
- Invoke analyze-codebase with all target dimensions:
  ```
  /analyze-codebase --dimensions=arch,patterns --skip-critics
  ```
  **Note:** The initial scan does not use `--changed-files-hint` since there is no prior commit SHA to diff against.
- At Stage 5 user checkpoint, automatically choose **Proceed to refactoring plans**.
- Wait for all stages (1-10) to complete and plans to be written to disk.
- Find each plan at `.code-analysis/plans/*-{DIMENSION}-plan.md` (use latest date).
- Find latest scores in `.code-analysis/reports/*-scores.json`.
- Extract scores for all target dimensions.
- **Dimensions already at target on initial scan:** Mark as met in `current_scores` but do NOT remove from the scan list — they are still scanned each iteration for cross-dimension context. Exclude from batch selection. Log: `"{dimension} already at {score} (target {target}), skipping fixes — still scanning for cross-dimension context"`. If all dimensions already meet their targets → output `SCORE_REACHED`, done.
- After scan completes, update `.claude/loop-state.md`:
  ```
  mode: multi
  targets: { architecture: 8, patterns: 9 }
  current_scores: { architecture: <score>, patterns: <score> }
  starting_scores: { architecture: <score>, patterns: <score> }
  plan_paths: { architecture: <path>, patterns: <path> }
  completed_finding_ids: []
  last_commit_sha:
  phase: planning
  iteration: 0
  score_history:
    - { architecture: <score>, patterns: <score> }
  started_at: <preserved from above>
  last_updated_at: <ISO 8601 now>
  ```
- Go to Step 4 (batch selection). **Note:** Single-dimension Step 3 continues to go to Step 7 (re-scan, unchanged). Multi-dimension goes to Step 4 because the first batch hasn't been selected yet from the multi-plan priority queue.
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): update Steps 2-3 for multi-dimension initial scan and completion"
```

---

### Task 5: Update Step 4 with cross-dimension batch selection

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` — "Step 4 — Brainstorm & Plan the Next Batch" section

- [ ] **Step 1: Add cross-dimension batch selection algorithm**

Add a multi-dimension variant to Step 4's batch selection logic. Insert before the existing "Gate:" paragraph:

```markdown
**Multi-dimension batch selection:**

When in multi-dimension mode, findings are selected across ALL dimensions' plans using a gap-weighted priority algorithm:

1. Compute each dimension's gap: `gap = target - current_score`
2. Dimensions already at or above target: gap = 0 (excluded from selection)
3. Score each finding: `priority = severity_weight x gap_of_its_dimension`
   - Severity weights: critical=3, high=2, medium=1, low=0.5
4. Sort by priority descending, pick top 3-5 (not yet in `completed_finding_ids`)
5. Effort tiebreaker: among equal-priority findings, prefer smaller effort (trivial → small → medium → large → xl)

**Example:** Architecture at 1.0 (target 8, gap=7), patterns at 5.0 (target 9, gap=4). A high-severity architecture finding scores `2 x 7 = 14`, a high-severity patterns finding scores `2 x 4 = 8`. Architecture findings get picked first.

**Single-dimension mode:** Unchanged — select next 3-5 findings from the plan, prioritizing trivial → small → medium effort.

**Cross-dimension fixes:** When a fix resolves findings in multiple dimensions (e.g., refactoring a god struct that spans architecture and patterns), add ALL affected finding IDs to `completed_finding_ids` regardless of dimension. The re-scan naturally drops resolved findings from all dimensions.
```

Also add after the existing "Gate:" paragraph:

```markdown
**XS-gate in multi-dimension mode:** The trivial-effort gate applies to the batch as a whole, regardless of how many dimensions are represented. A batch with 3 trivial arch findings and 1 small patterns finding goes through the full design pipeline.
```

- [ ] **Step 2: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): add cross-dimension batch selection with gap-weighted priority"
```

---

### Task 6: Update Steps 5-6 for multi-dimension

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` — "Step 5 — Subsequent Runs" and "Step 6 — Commit" sections

- [ ] **Step 1: Update Step 5 to handle multi-dimension plan reading**

In Step 5, update "Read plan at `plan_path`" to handle multi-dimension:

```markdown
- **Single-dimension:** Read plan at `plan_path` from state file.
- **Multi-dimension:** Read plans from all `plan_paths` entries. Identify the batch of trivial findings NOT yet in `completed_finding_ids` across all dimensions, using the gap-weighted priority from Step 4.
```

- [ ] **Step 2: Update Step 6 commit format**

Add multi-dimension commit format:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): update Steps 5-6 for multi-dimension plan reading and commit format"
```

---

### Task 7: Update Steps 7-9 for multi-dimension

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` — "Step 7 — Re-scan", "Step 8 — Check Completion", and "Step 9 — Refresh Plan if Exhausted" sections

- [ ] **Step 1: Update Step 7 re-scan for multi-dimension**

```markdown
### Step 7 — Re-scan

- Write `phase: rescanning` and `last_updated_at` to `.claude/loop-state.md`.
- Compute changed files since last commit:
  ```bash
  git diff --name-only {last_commit_sha}..HEAD
  ```
- Run a fresh draft scan:
  - **Single-dimension:**
    ```
    /analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics \
      --changed-files-hint="{comma-separated file list from git diff}"
    ```
  - **Multi-dimension:**
    ```
    /analyze-codebase --dimensions=dim1,dim2,... --draft-only --skip-critics \
      --changed-files-hint="{comma-separated file list from git diff}"
    ```
    All target dimensions are scanned together (including dimensions already at target, for cross-dimension context).
- Read scores from `.code-analysis/reports/*-scores.json` (latest date file).
- Update `.claude/loop-state.md`:
  - **Single-dimension:** `current_score: <new score>`, append to `score_history`
  - **Multi-dimension:** Update all entries in `current_scores`, append full score map to `score_history`
  - `phase: planning`
  - Update `last_updated_at`
```

- [ ] **Step 2: Update Step 8 completion check for multi-dimension**

```markdown
### Step 8 — Check Completion

**Single-dimension:** If `current_score >= target` → write `phase: done`, output `<promise>SCORE_REACHED</promise>`.

**Multi-dimension:** If `current_scores[dim] >= targets[dim]` for every dimension → write `phase: done`, output `<promise>SCORE_REACHED</promise>`.

**Mid-loop dimension completion** (multi-dimension only): When a dimension reaches its target but others haven't:
- Log: `"{dimension} reached {score} (target {target}) -- continuing for {remaining dimensions}"`
- That dimension's findings are no longer selected in batch picks
- Still scanned each iteration (cross-dimension context)
- If score drops below target due to another fix, re-enters fix pool
```

- [ ] **Step 3: Update Step 9 plan exhaustion for multi-dimension**

```markdown
### Step 9 — Refresh Plan if Exhausted

**Single-dimension:** If all plan steps are completed but score < target, clear `completed_finding_ids` and delete `loop-state.md`. Next iteration generates a new plan (Step 3).

**Multi-dimension:**
- **One dimension's plan exhausted, score below target:** Clear its IDs from `completed_finding_ids` using the finding ID prefix (e.g., `ARCH-*` belongs to architecture, `PAT-*` to patterns). Next scan generates a fresh plan for that dimension. Other dimensions continue using their existing plans.
- **All plans exhausted, any score below target:** Clear all `completed_finding_ids`, delete `loop-state.md`. Next iteration starts fresh (Step 3).
```

- [ ] **Step 4: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): update Steps 7-9 for multi-dimension re-scan, completion, and plan exhaustion"
```

---

### Task 8: Update How to Run section and error handling

**Files:**
- Modify: `skills/ralph-loop/SKILL.md` — "How to Run" section

- [ ] **Step 1: Update How to Run with multi-dimension syntax**

Replace the "How to Run" section with the following content. Add a "Multi-dimension" subsection after the existing single-dimension example, and a "Max iterations exhausted" subsection at the end:

**New "Multi-dimension" subsection to add:**

> \## How to Run
>
> \### Single-dimension (backward-compatible)
>
> `/code-analysis:ralph-loop perf 8 --completion-promise "SCORE_REACHED" --max-iterations 10`
>
> \### Multi-dimension
>
> `/code-analysis:ralph-loop --targets="arch:8,patterns:9,security:10" --completion-promise "SCORE_REACHED" --max-iterations 10`
>
> All target dimensions are scanned together each iteration, preserving cross-scanner context. Findings are selected across all dimensions using a gap-weighted priority algorithm. The loop exits when every dimension reaches its own target.
>
> \### Max iterations exhausted
>
> `--max-iterations` applies to total loop count across all dimensions. When exhausted, output per-dimension progress showing starting score, current score, target, and whether reached.

### Error Handling

Add an error handling section to SKILL.md covering all multi-dimension scenarios. Note: validation errors (`--targets` parsing, duplicates, range checks) are already documented in the "Input Parsing" section from Task 2. Cross-mode conflicts are documented in Step 1 from Task 3. This table covers runtime scenarios:

| Scenario | Resolution |
|----------|-----------|
| One dimension's plan generation fails | Log warning, continue with other dimensions. Retry plan generation on next re-scan. |
| All findings are xl effort | Proceed normally. Log: `"Only xl-effort findings remaining, iterations may be slow"` |
| Fix in dimension A introduces new finding in dimension B | Re-scan catches it, batch selection picks it up if impactful enough (gap-weighted priority) |
| Dimension reaches target then regresses below target | Re-enters fix pool automatically — mid-loop completion is reversible |

- [ ] **Step 2: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(ralph-loop): update How to Run section with multi-dimension syntax"
```

---

### Task 9: Update README.md

**Files:**
- Modify: `README.md` — "Ralph-Loop (Iterative Fix Loop)" and "Changelog" sections

- [ ] **Step 1: Update Ralph-Loop section in README**

Update the "Ralph-Loop (Iterative Fix Loop)" section to include multi-dimension:

After the existing single-dimension ralph-loop example in the "Ralph-Loop (Iterative Fix Loop)" section, add:

```markdown
**Multi-dimension** (v0.4.0) — scan multiple dimensions together, fix with per-dimension targets:

```
/code-analysis:ralph-loop --targets="arch:8,patterns:9" --completion-promise "SCORE_REACHED" --max-iterations 10
```

All target dimensions are scanned together each iteration, so cross-cutting findings (god structs, race conditions spanning multiple concerns) are caught. Findings are prioritized by a gap-weighted algorithm — dimensions furthest from target get fixed first.
```

Update the "How it works" list to add:

```markdown
7. **Multi-dimension:** When using `--targets`, all dimensions are scanned together and findings are selected across dimensions using gap-weighted priority
```

- [ ] **Step 2: Add changelog entry**

Add to the Changelog section, above v0.3.1:

```markdown
### v0.4.0 (2026-03-19)
- **Multi-dimension ralph-loop**: `--targets="arch:8,patterns:9"` runs multiple dimensions in one loop with per-dimension target scores
- **Cross-dimension scanning**: All target dimensions scanned together each iteration, catching cross-cutting findings
- **Gap-weighted batch selection**: Findings prioritized by dimension gap — furthest from target gets fixed first
```

- [ ] **Step 3: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/README.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "docs(code-analysis): update README with multi-dimension ralph-loop syntax and changelog"
```

---

### Task 10: Version bump, final commit, push, and cache update

**Files:**
- Modify: `code-analysis/.claude-plugin/plugin.json`

- [ ] **Step 1: Bump version to 0.4.0**

In `.claude-plugin/plugin.json`, change `"version": "0.3.1"` to `"version": "0.4.0"`.

- [ ] **Step 2: Commit version bump**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/.claude-plugin/plugin.json
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "chore(code-analysis): bump version to 0.4.0"
```

- [ ] **Step 3: Push to remote**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace push
```

- [ ] **Step 4: Update Claude cache**

```bash
cp -r ~/.claude/plugins/cache/fosketer-claude-marketplace/code-analysis/0.3.1 ~/.claude/plugins/cache/fosketer-claude-marketplace/code-analysis/0.4.0
rsync -a --delete --exclude='.claude-plugin' --exclude='.git' --exclude='docs/superpowers' \
  /Users/keven.foster/document-perso/local-claude-marketplace/code-analysis/ \
  ~/.claude/plugins/cache/fosketer-claude-marketplace/code-analysis/0.4.0/
```

- [ ] **Step 5: Verify cache**

```bash
ls ~/.claude/plugins/cache/fosketer-claude-marketplace/code-analysis/
# Expected: 0.3.0  0.3.1  0.4.0
```
