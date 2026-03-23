# Token Optimization v0.8.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce code-analysis token consumption by 5-8x while maintaining analysis quality, targeting redundant work elimination, smarter model routing, and reference file optimization.

**Architecture:** Six independent changes that compose: (1) skip-clean dimensions in ralph-loop, (2) inline scanner scoring to bypass reconciler on re-scans, (3) split output-schemas.md into role-specific fragments, (4) smart model defaults per pipeline stage, (5) mechanical fix bypass for plugin dimensions, (6) per-dimension iteration tracking with progressive model escalation.

**Tech Stack:** Claude Code plugin (markdown skills, JSON schemas, YAML frontmatter)

**Spec:** `docs/superpowers/specs/2026-03-23-token-optimization-design.md`

---

### Task 1: Split output-schemas.md into Role-Specific Fragments

**Files:**
- Create: `references/schemas/finding-schema.md`
- Create: `references/schemas/scoring-schema.md`
- Create: `references/schemas/reconciler-schema.md`
- Create: `references/schemas/critic-schema.md`
- Create: `references/schemas/plan-schema.md`
- Modify: `references/output-schemas.md` (add deprecation notice + pointer)
- Modify: `agents/code-analyzer/AGENT.md` (update resource loading)
- Modify: `agents/report-reconciler/AGENT.md` (update resource loading)
- Modify: `agents/report-critic/AGENT.md` (update resource loading)
- Modify: `agents/plan-critic/AGENT.md` (update resource loading)
- Modify: `agents/refactoring-planner/AGENT.md` (update resource loading)

- [ ] **Step 1: Create `references/schemas/finding-schema.md`**

Extract from `output-schemas.md`: the Finding Schema and DimensionReport Schema sections (lines 1–155 approx). Add a header:

```markdown
# Finding & Dimension Report Schemas

> Extracted from output-schemas.md for role-specific loading. Canonical source for finding structure.

> schema_version: 0.8.0
```

Include: Finding JSON schema, DimensionReport JSON schema, carry_forward_summary sub-schema.

- [ ] **Step 2: Create `references/schemas/scoring-schema.md`**

Extract: ScoresReport schema, IterationTarget sub-schema, and the scoring formula. Add a header:

```markdown
# Scoring Schemas

> Extracted from output-schemas.md for role-specific loading.

> schema_version: 0.8.0

## Scoring Formula

`raw = 3×critical + 2×high + 1×medium + 0.5×low`
`score = max(1.0, 10 - min(raw, 9))`

Info-severity findings are excluded from scoring.
```

Include: ScoresReport JSON schema, IterationTarget JSON schema, RunDelta schema.

- [ ] **Step 3: Create `references/schemas/reconciler-schema.md`**

Extract: CrossAnalysis schema, RootCauseCluster schema, Override File schema. Add header:

```markdown
# Reconciler Schemas

> Extracted from output-schemas.md. Loaded by report-reconciler agent only.

> schema_version: 0.8.0
```

- [ ] **Step 4: Create `references/schemas/critic-schema.md`**

Extract: CriticFeedback schema. Add header:

```markdown
# Critic Feedback Schema

> Extracted from output-schemas.md. Loaded by report-critic and plan-critic agents.

> schema_version: 0.8.0
```

- [ ] **Step 5: Create `references/schemas/plan-schema.md`**

Extract: RefactoringPlan schema, OrchestratorPlan schema. Add header:

```markdown
# Plan Schemas

> Extracted from output-schemas.md. Loaded by refactoring-planner agent only.

> schema_version: 0.8.0
```

- [ ] **Step 6: Add deprecation notice to `references/output-schemas.md`**

Prepend to the file:

```markdown
> **DEPRECATED (v0.8.0):** This file is kept for human reference only. Agents MUST load
> role-specific fragments from `references/schemas/` instead. See:
> - `finding-schema.md` — scanners, reconciler
> - `scoring-schema.md` — scanners, reconciler
> - `reconciler-schema.md` — reconciler only
> - `critic-schema.md` — report-critic, plan-critic
> - `plan-schema.md` — refactoring-planner only
```

- [ ] **Step 7: Update `agents/code-analyzer/AGENT.md` resource loading**

In the Process / Step 2 section where it loads `output-schemas.md`, replace with:
```
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/finding-schema.md`
```
Remove any reference to loading the full `output-schemas.md`.

- [ ] **Step 8: Update `agents/report-reconciler/AGENT.md` resource loading**

Replace `output-schemas.md` reference with:
```
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/finding-schema.md`
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/scoring-schema.md`
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/reconciler-schema.md`
```

- [ ] **Step 9: Update `agents/report-critic/AGENT.md` resource loading**

Replace `output-schemas.md` reference with:
```
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/critic-schema.md`
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/scoring-schema.md`
```

- [ ] **Step 10: Update `agents/plan-critic/AGENT.md` resource loading**

Replace `output-schemas.md` reference with:
```
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/critic-schema.md`
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/plan-schema.md`
```

- [ ] **Step 11: Update `agents/refactoring-planner/AGENT.md` resource loading**

Replace `output-schemas.md` reference with:
```
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/plan-schema.md`
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/finding-schema.md`
```

- [ ] **Step 12: Commit**

```bash
git add -f references/schemas/ references/output-schemas.md agents/
git commit -m 'refactor(schemas): split output-schemas.md into role-specific fragments

Reduces per-agent context loading from 26KB to 3-8KB.
Agents now load only the schema fragments relevant to their role.'
```

---

### Task 2: Add Self-Scoring Protocol to All Scanners

**Files:**
- Modify: `skills/scan-structure/SKILL.md`
- Modify: `skills/scan-quality/SKILL.md`
- Modify: `skills/scan-security/SKILL.md`
- Modify: `skills/scan-testing/SKILL.md`
- Modify: `skills/scan-manifest-structure/SKILL.md`
- Modify: `skills/scan-skill-quality/SKILL.md`
- Modify: `skills/scan-agent-design/SKILL.md`
- Modify: `skills/scan-hook-correctness/SKILL.md`
- Modify: `skills/scan-marketplace-consistency/SKILL.md`
- Modify: `skills/scan-convention-adherence/SKILL.md`
- Modify: `agents/code-analyzer/AGENT.md`

- [ ] **Step 1: Add self-scoring section to `skills/scan-structure/SKILL.md`**

Before the final output section (or at the end of the Workflow), add:

```markdown
## Self-Scoring & Persistence

After generating all findings, compute and include the dimension score:

1. Count findings by severity (exclude info): critical, high, medium, low
2. Compute raw penalty: `raw = 3×critical + 2×high + 1×medium + 0.5×low`
3. Compute score: `score = max(1.0, 10 - min(raw, 9))`
4. Include in response header:
   ```json
   { "dimension": "structure", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-structure.json` (overwrite if same date exists)
```

- [ ] **Step 2: Add identical self-scoring section to remaining 9 scanner skills**

Apply the same section from Step 1 to each scanner skill, changing only the dimension name in the JSON example:
- `scan-quality/SKILL.md` → `"dimension": "quality"`
- `scan-security/SKILL.md` → `"dimension": "security"`
- `scan-testing/SKILL.md` → `"dimension": "testing"`
- `scan-manifest-structure/SKILL.md` → `"dimension": "manifest-structure"`
- `scan-skill-quality/SKILL.md` → `"dimension": "skill-quality"`
- `scan-agent-design/SKILL.md` → `"dimension": "agent-design"`
- `scan-hook-correctness/SKILL.md` → `"dimension": "hook-correctness"`
- `scan-marketplace-consistency/SKILL.md` → `"dimension": "marketplace-consistency"`
- `scan-convention-adherence/SKILL.md` → `"dimension": "convention-adherence"`

- [ ] **Step 3: Update `agents/code-analyzer/AGENT.md` to include scoring in output**

In the Output section, update the expected response format to include `score` and `raw_penalty` fields in the response header. Add `Write` to the tools list since the scanner now persists to disk.

Add to the tools list: `"Write"`.

Update the response format description:
```markdown
Return a JSON object with:
- `dimension`: dimension name
- `score`: computed dimension score (0-10)
- `raw_penalty`: unclipped penalty value
- `summary`: { total, critical, high, medium, low, info }
- `findings`: array of Finding objects
```

- [ ] **Step 4: Add `scoring-schema.md` to scanner resource loading**

In `agents/code-analyzer/AGENT.md`, in the resource loading step, add:
```
- Read `${CLAUDE_PLUGIN_ROOT}/references/schemas/scoring-schema.md`
```

This gives scanners the scoring formula reference.

- [ ] **Step 5: Commit**

```bash
git add -f skills/scan-*/SKILL.md agents/code-analyzer/AGENT.md
git commit -m 'feat(scanners): add self-scoring and persistence protocol

Each scanner now computes its own dimension score and persists
scan reports to disk, enabling reconciler bypass on re-scans.'
```

---

### Task 3: Update Orchestrator to Bypass Reconciler on Re-Scans

**Files:**
- Modify: `skills/analyze-codebase/SKILL.md`

- [ ] **Step 1: Add inline scoring logic to Stage 3 for `--draft-only` mode**

In `skills/analyze-codebase/SKILL.md`, in Stage 3, add a conditional before dispatching the reconciler:

After collecting all scanner responses, add:

```markdown
**When `--draft-only` is set (re-scan mode):**

Since scanners now self-score and self-persist (v0.8.0), the orchestrator SHOULD compute the overall score inline instead of dispatching a reconciler agent:

1. Collect `{ dimension, score, raw_penalty }` from each scanner response
2. Compute overall weighted score: `overall = Σ(score × weight) / Σ(weights)` using weights from `--weights` flag (default all 1.0)
3. Build a minimal `scores.json` from scanner outputs and persist to `.code-analysis/reports/YYYY-MM-DD-scores.json`
4. Skip reconciler dispatch entirely
5. Present dimension scores summary to user. Exit.

**When `--draft-only` is NOT set (full analysis mode):**

Dispatch reconciler agent as before (unchanged behavior).
```

- [ ] **Step 2: Verify no other `--draft-only` paths depend on reconciler output**

Read through the ralph-loop re-scan references to confirm they only consume `scores.json` (not the narrative draft report). The re-scan path uses `--draft-only --skip-critics`, so it only needs scores.

- [ ] **Step 3: Commit**

```bash
git add -f skills/analyze-codebase/SKILL.md
git commit -m 'feat(orchestrator): bypass reconciler on --draft-only re-scans

Scanners self-score and self-persist, so the orchestrator computes
the overall score inline. Saves one reconciler dispatch per re-scan.'
```

---

### Task 4: Update Model Resolution Defaults

**Files:**
- Modify: `skills/analyze-codebase/references/model-resolution.md`

- [ ] **Step 1: Change default model map from `inherit` to stage-aware defaults**

In `model-resolution.md`, update Resolution Steps item 1:

Replace:
```markdown
1. Initialize all 4 stage keys (`scanning`, `reconciliation`, `critique`, `planning`) to `"inherit"`
```

With:
```markdown
1. Initialize stage keys with smart defaults:
   - `scanning`: `"sonnet"` — pattern matching and structured output; Sonnet sufficient
   - `reconciliation`: `"inherit"` — cross-dimension reasoning benefits from session model
   - `critique`: `"sonnet"` — checklist validation and formula verification
   - `planning`: `"inherit"` — complex dependency analysis benefits from session model
```

- [ ] **Step 2: Add validation note about Haiku floor**

Add after the Resolution Steps:

```markdown
## Model Quality Floor

Haiku MUST NOT be used as a default for any stage. When `--model haiku` is explicitly
provided by the user, it is honored (user override takes precedence), but the plugin's
own defaults never go below Sonnet.
```

- [ ] **Step 3: Commit**

```bash
git add -f skills/analyze-codebase/references/model-resolution.md
git commit -m 'feat(models): default scanners and critics to Sonnet

Reduces scanner cache-read cost by ~6x vs Opus while maintaining
quality. Reconciliation and planning inherit session model.'
```

---

### Task 5: Add Skip-Clean Dimensions to Ralph-Loop

**Files:**
- Modify: `skills/ralph-loop/SKILL.md`
- Modify: `skills/ralph-loop/references/verification-scan.md`
- Modify: `skills/ralph-loop/references/multi-dimension.md`

- [ ] **Step 1: Add `converged_dimensions` to state file documentation**

In `skills/ralph-loop/SKILL.md`, in the State File section, add these new fields after `score_history`:

```markdown
converged_dimensions: []
converged_at_iteration: {}
```

Add a note:
```markdown
> **Converged dimensions (v0.8.0):** Dimensions whose score has reached the target. Skipped during re-scans
> except on safety-net iterations (every 5th). If a converged dimension regresses, it is removed from the list.
```

- [ ] **Step 2: Add convergence check to ralph-loop Step 7 (re-scan)**

In `skills/ralph-loop/SKILL.md`, in Step 7 description, add before the reference to verification-scan.md:

```markdown
**Before dispatching re-scan (v0.8.0 skip-clean optimization):**

For multi-dimension mode, check which dimensions have converged:
1. For each dimension in targets: if `current_scores[dim] >= targets[dim]` AND dimension is not already in `converged_dimensions`, add it with `converged_at_iteration: <current iteration>`
2. If `iteration % 5 != 0` (not a safety-net iteration): exclude `converged_dimensions` from the `--dimensions` list passed to analyze-codebase
3. If `iteration % 5 == 0` (safety-net iteration): scan ALL target dimensions including converged ones. Log: `"Safety-net iteration {N}: scanning all dimensions including converged"`
4. After re-scan: if any converged dimension's score dropped below its target, remove from `converged_dimensions` and log: `"Regression detected: {dim} dropped to {score} (target {target}), resuming scanning"`

**Single-dimension mode:** Skip-clean does not apply (only one dimension to scan).
```

- [ ] **Step 3: Update `verification-scan.md` multi-dimension re-scan section**

In `skills/ralph-loop/references/verification-scan.md`, update the multi-dimension scan command to note the dimension list may be filtered:

In the Carry-Forward Scan section, update the multi-dimension command:
```markdown
- **Multi-dimension:**
  ```
  /analyze-codebase --dimensions=<active-dims> --draft-only --skip-critics \
    --changed-files-hint="{comma-separated file list from git diff}" \
    [--model MODEL_SPEC if provided]
  ```
  Where `<active-dims>` excludes converged dimensions (except on safety-net iterations).
  Converged dimensions are still tracked in the state file for regression detection.
```

Apply the same update to the Full Re-Discovery Scan section.

- [ ] **Step 4: Update `multi-dimension.md` Step 7 section**

In `skills/ralph-loop/references/multi-dimension.md`, update the Step 7 re-scan section to reference the skip-clean behavior:

Replace:
```markdown
All target dimensions are scanned together (including dimensions already at target, for cross-dimension context).
```

With:
```markdown
Active dimensions (excluding converged) are scanned. Converged dimensions are skipped unless this is a
safety-net iteration (`iteration % 5 == 0`). See main skill Step 7 for convergence rules.
```

Also update Step 8 mid-loop completion note. Replace:
```markdown
- Still scanned each iteration (cross-dimension context)
```

With:
```markdown
- Added to `converged_dimensions`, skipped on non-safety-net iterations
```

- [ ] **Step 5: Commit**

```bash
git add -f skills/ralph-loop/SKILL.md skills/ralph-loop/references/verification-scan.md skills/ralph-loop/references/multi-dimension.md
git commit -m 'feat(ralph-loop): skip-clean dimensions optimization

Dimensions that reach their target score are skipped during re-scans,
with a safety-net full scan every 5th iteration to catch regressions.'
```

---

### Task 6: Add Mechanical Fix Bypass for Plugin Dimensions

**Files:**
- Modify: `skills/ralph-loop/SKILL.md`

- [ ] **Step 1: Add mechanical dimensions concept to ralph-loop**

In `skills/ralph-loop/SKILL.md`, before Step 4, add a new section:

```markdown
## Mechanical Dimensions (v0.8.0)

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
```

- [ ] **Step 2: Update Step 4 gate logic**

In Step 4, update the gate:

Replace:
```markdown
**Gate:** If every finding in the batch is XS-effort mechanical, skip Steps 4a-4c and go directly to Step 5.
```

With:
```markdown
**Gate:** Skip Steps 4a-4c and go directly to Step 5 if ANY of:
- Every finding in the batch is XS-effort mechanical (existing behavior), OR
- Every finding in the batch comes from a mechanical dimension (v0.8.0; see Mechanical Dimensions above)
```

- [ ] **Step 3: Add `mechanical_dimensions` to state file**

In the State File section, add:
```markdown
mechanical_dimensions: [manifest-structure, skill-quality, agent-design, hook-correctness, marketplace-consistency, convention-adherence]
```

Add note:
```markdown
> **Mechanical dimensions (v0.8.0):** Only present when `--plugin` is set. Populated automatically from the
> Mechanical Dimensions list. Findings from these dimensions always skip the superpowers pipeline.
```

- [ ] **Step 4: Commit**

```bash
git add -f skills/ralph-loop/SKILL.md
git commit -m 'feat(ralph-loop): mechanical fix bypass for plugin dimensions

Plugin structural dimensions (manifest, skills, agents, hooks,
marketplace, conventions) skip the superpowers brainstorm/plan pipeline
since their fixes are always mechanical markdown/JSON edits.'
```

---

### Task 7: Add Per-Dimension Tracking and Progressive Model Escalation

**Files:**
- Modify: `skills/ralph-loop/SKILL.md`
- Modify: `skills/ralph-loop/references/multi-dimension.md`

- [ ] **Step 1: Add `dimension_progress` to state file format in `SKILL.md`**

In the State File section, add a new field (in multi-dimension mode):

```markdown
dimension_progress:
  manifest-structure: {iterations: 5, score_history: [1.0, 4.0, 7.0, 8.5, 9.0], status: converged}
  quality: {iterations: 5, score_history: [1.0, 1.0, 2.0, 3.5, 4.0], status: active}
  security: {iterations: 5, score_history: [1.0, 5.0, 8.0, 8.0, 8.0], status: stalled}
```

Add note:
```markdown
> **Per-dimension progress (v0.8.0):** Tracks each dimension's iteration count, score history, and status.
> Status values: `active` (default), `stalled` (no improvement for 2 iterations), `converged` (score ≥ target),
> `escalated` (model bumped to Opus). Supplements `converged_dimensions` with richer tracking.
```

- [ ] **Step 2: Add stall detection logic to ralph-loop post-scan update**

In the Post-Scan Update section (referenced by Step 7), add:

```markdown
**Stall detection (v0.8.0):**

After updating `current_scores`, check each active dimension:
1. Get last 2 scores from `dimension_progress[dim].score_history`
2. If `score_history[-1] <= score_history[-2]` (no improvement): increment stall count
3. If stalled for 2 consecutive iterations AND current scanner model for this dimension is Sonnet:
   - Set `dimension_progress[dim].status: escalated`
   - Log: `"Dimension {dim} stalled at {score} for 2 iterations — escalating scanner to Opus"`
   - On next scan dispatch, override this dimension's scanner model to `opus`
4. If stalled for 2 more iterations at Opus:
   - Log: `"Dimension {dim} stalled at {score} even with Opus. Remaining findings may require manual intervention."`
   - Continue scanning but surface warning to user
5. If score improves after escalation: keep model at Opus (don't downgrade mid-loop)
```

- [ ] **Step 3: Update `multi-dimension.md` state file format**

In `skills/ralph-loop/references/multi-dimension.md`, add `dimension_progress` to the state file example:

After `score_history`, add:
```markdown
dimension_progress:
  structure: {iterations: 3, score_history: [1.0, 4.5, 6.0], status: active}
  quality: {iterations: 3, score_history: [1.0, 3.0, 5.5], status: active}
```

Add to the Key differences list:
```markdown
- `dimension_progress` — per-dimension iteration tracking with status and model escalation (v0.8.0)
```

- [ ] **Step 4: Update analyze-codebase scanner dispatch for per-dimension model override**

In `skills/analyze-codebase/SKILL.md`, in Stage 2, add a note about per-dimension model overrides:

```markdown
**Per-dimension model override (v0.8.0):**

When ralph-loop provides per-dimension model overrides (via escalation), the orchestrator
SHOULD honor them by passing the specific model for each scanner agent dispatch. The override
is conveyed via the `--model` flag using per-dimension syntax:
`--model scanning:sonnet,scanning.quality:opus` (dimension-specific override).

If the platform does not support per-dimension model routing, fall back to the highest
model specified across all dimensions for the scanning stage.
```

- [ ] **Step 5: Commit**

```bash
git add -f skills/ralph-loop/SKILL.md skills/ralph-loop/references/multi-dimension.md skills/analyze-codebase/SKILL.md
git commit -m 'feat(ralph-loop): per-dimension tracking and progressive model escalation

Track per-dimension iteration count, score history, and status.
Detect stalled dimensions and escalate from Sonnet to Opus
automatically. Surface to user when Opus also cannot make progress.'
```

---

### Task 8: Update Plugin Version and Documentation

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `README.md`
- Modify: `package.json`

- [ ] **Step 1: Bump version in `plugin.json`**

Update `"version": "0.7.0"` to `"version": "0.8.0"`.

Update the description to mention token optimization.

- [ ] **Step 2: Bump version in `package.json`**

Update `"version": "0.7.0"` to `"version": "0.8.0"`.

- [ ] **Step 3: Update all SKILL.md frontmatter versions**

In every `skills/*/SKILL.md`, update `version: 0.7.0` to `version: 0.8.0`.

Files: analyze-codebase, ralph-loop, reconcile-report, generate-orchestrator-plan, generate-refactoring-plan, critique-report, critique-plan, refactor-plan, scan-structure, scan-quality, scan-security, scan-testing, scan-manifest-structure, scan-skill-quality, scan-agent-design, scan-hook-correctness, scan-marketplace-consistency, scan-convention-adherence.

- [ ] **Step 4: Update `references/output-schemas.md` schema version**

Change `schema_version: 0.7.0` to `schema_version: 0.8.0` in the header. Same for all new schema fragment files.

- [ ] **Step 5: Add v0.8.0 changelog section to README.md**

Add a changelog section documenting the 6 optimization features.

- [ ] **Step 6: Commit**

```bash
git add -f .claude-plugin/plugin.json package.json README.md skills/ references/
git commit -m 'chore: bump version to 0.8.0 with token optimization features

v0.8.0 adds 6 token optimization features: skip-clean dimensions,
inline scanner scoring, reference splitting, smart model defaults,
mechanical fix bypass, and per-dimension tracking.'
```

---

## Implementation Order & Dependencies

```
Task 1 (schema split) ──────────────────────────────────┐
                                                         │
Task 2 (scanner self-scoring) ──── depends on Task 1 ───┤
                                                         │
Task 3 (orchestrator bypass) ──── depends on Task 2 ────┤
                                                         │
Task 4 (model defaults) ──────── independent ───────────┤
                                                         │
Task 5 (skip-clean) ──────────── independent ───────────┤
                                                         │
Task 6 (mechanical bypass) ────── independent ───────────┤
                                                         │
Task 7 (per-dim tracking) ──────── depends on Task 5 ───┤
                                                         │
Task 8 (version bump) ──────────── depends on all ──────┘
```

**Parallelizable groups:**
- Group A: Tasks 1 → 2 → 3 (serial dependency chain)
- Group B: Tasks 4, 5, 6 (independent, can run in parallel)
- Group C: Task 7 (depends on Task 5)
- Group D: Task 8 (after all others)

**Recommended execution:** Group A first (schema split is foundational), then Group B in parallel, then Group C, then Group D.
