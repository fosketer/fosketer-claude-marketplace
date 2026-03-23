# Token Optimization — Design Spec v0.8.0

> The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Problem

Code-analysis v0.7.0 consumes disproportionate tokens relative to value delivered. A 10-dimension `--plugin` ralph-loop run consumed **515M tokens (~$1,200 API cost)** over 5 days due to:

1. **Redundant scanner dispatches** — dimensions already at/above target are re-scanned every iteration
2. **Reconciler dispatched on every re-scan** — even when only per-dimension scores are needed
3. **Large reference files loaded by every agent** — `output-schemas.md` (26KB) loaded in full regardless of role
4. **Opus model used everywhere** — scanners doing pattern matching use the same model as reconciliation/planning
5. **Superpowers pipeline for mechanical fixes** — plugin dimension fixes (markdown/JSON edits) run through brainstorm → write-plan → subagent-driven-development
6. **No per-dimension iteration tracking** — can't detect stalled dimensions or apply targeted interventions

## Goal

Reduce token consumption by **5-8x** while maintaining or improving analysis quality. Target: a 10-dimension plugin ralph-loop run SHOULD consume < 10M tokens instead of 50M+.

## Design Sections

### 1. Skip-Clean Dimensions in Ralph-Loop

**Scope:** `skills/ralph-loop/SKILL.md`, `skills/ralph-loop/references/verification-scan.md`

#### Current Behavior

Every re-scan iteration dispatches ALL target dimensions to scanners, regardless of score vs target.

#### New Behavior

Before dispatching scanners in Step 7 (re-scan):

1. Compare `current_scores[dim]` against `targets[dim]` for each dimension
2. If `current_scores[dim] >= targets[dim]`, add to `converged_dimensions` list
3. **Skip** scanner dispatch for converged dimensions
4. **Safety net**: Every 5th iteration (`iteration % 5 == 0`), re-scan ALL dimensions including converged ones to detect regressions from cross-dimension fixes
5. If a converged dimension regresses below target, remove it from `converged_dimensions` and resume scanning

#### State File Additions

```markdown
converged_dimensions: [manifest-structure, hook-correctness]
converged_at_iteration: {manifest-structure: 3, hook-correctness: 4}
```

#### Rules

- MUST NOT skip a dimension on the very first re-scan after initial analysis
- MUST re-scan all dimensions on iterations divisible by 5
- MUST remove dimension from `converged_dimensions` if score drops below target
- SHOULD log skipped dimensions in the iteration summary

#### Estimated Impact

If 4 of 10 dimensions converge by iteration 5, this saves ~4 scanner dispatches per iteration for remaining iterations. Over 15 iterations: ~40 fewer agent dispatches.

---

### 2. Inline Scoring in Scanners + Reconciler Bypass on Re-Scans

**Scope:** All `skills/scan-*/SKILL.md`, `skills/analyze-codebase/SKILL.md`, `skills/ralph-loop/references/verification-scan.md`

#### Current Behavior

Scanners return raw findings JSON → reconciler agent always dispatched to score and produce reports, even on `--draft-only` re-scans.

#### New Behavior

**Scanner self-scoring:**

Each scanner MUST compute its own dimension score and include it in the response:

```json
{
  "dimension": "quality",
  "score": 6.5,
  "raw_penalty": 3.5,
  "summary": { "total": 12, "critical": 0, "high": 1, "medium": 3, "low": 8, "info": 0 },
  "findings": [...]
}
```

Scoring formula (same as reconciler): `raw = 3×critical + 2×high + 1×medium + 0.5×low`, `score = max(1.0, 10 - min(raw, 9))`.

Each scanner MUST also persist its scan report to `.code-analysis/scan-reports/YYYY-MM-DD-{dimension}.json`.

**Orchestrator behavior:**

- **On re-scans (`--draft-only`)**: The orchestrator reads dimension scores directly from scanner output, computes the weighted overall score inline, and updates `scores.json`. No reconciler dispatch.
- **On first scan or full analysis**: The reconciler is dispatched as before for cross-dimension deduplication, root-cause clustering, and the unified narrative report.

#### Scanner SKILL.md Addition

Add to each `scan-*/SKILL.md` a section (≤ 200 words):

```markdown
## Self-Scoring Protocol

After generating all findings, compute the dimension score:
1. Count findings by severity: critical, high, medium, low (exclude info)
2. raw = 3×critical + 2×high + 1×medium + 0.5×low
3. score = max(1.0, 10 - min(raw, 9))
4. Include score, raw_penalty in response header
5. Persist findings to SCAN_REPORTS_DIR/YYYY-MM-DD-{dimension}.json
```

#### Rules

- Scanner MUST compute score using the canonical formula
- Scanner MUST persist its own scan report to disk
- Orchestrator MUST NOT dispatch reconciler on `--draft-only` re-scans
- Orchestrator MUST dispatch reconciler on first scan and when `--draft-only` is NOT set
- Reconciler behavior is unchanged when dispatched

#### Estimated Impact

Eliminates 1 reconciler agent dispatch per re-scan iteration (saves ~40KB context loading + processing). Over 15 iterations: ~14 fewer reconciler dispatches.

---

### 3. Reference File Splitting

**Scope:** `references/output-schemas.md` → split into role-specific fragments

#### Current Structure

`output-schemas.md` (26.5KB, ~804 lines) loaded by reconciler, critics, and planners regardless of role.

#### New Structure

| New File | Content | Est. Size | Loaded By |
|----------|---------|-----------|-----------|
| `references/schemas/finding-schema.md` | Finding, DimensionReport types | ~4KB | Scanners, Reconciler |
| `references/schemas/scoring-schema.md` | ScoresReport, scoring formula, weights | ~3KB | Scanners (new), Reconciler |
| `references/schemas/reconciler-schema.md` | CrossAnalysis, dedup rules, action tiers, delta | ~8KB | Reconciler only |
| `references/schemas/critic-schema.md` | CriticFeedback format, verdict rules | ~4KB | Report-critic, Plan-critic |
| `references/schemas/plan-schema.md` | RefactoringPlan, OrchestratorPlan types | ~7KB | Planner only |

#### Rules

- Each agent MUST load only its relevant schema fragment(s)
- `output-schemas.md` MAY be kept as a concatenated reference but MUST NOT be loaded by agents
- Scanner agents load: `finding-schema.md` + `scoring-schema.md` (~7KB vs 26KB)
- Reconciler loads: `finding-schema.md` + `scoring-schema.md` + `reconciler-schema.md` (~15KB vs 26KB)
- Critics load: `critic-schema.md` (~4KB vs 26KB)
- Planners load: `plan-schema.md` (~7KB vs 26KB)

#### Migration

- `output-schemas.md` remains as a generated concatenation for human reference
- All agent SKILL.md and AGENT.md references updated to point to specific fragments

#### Estimated Impact

Per scan cycle with 8 scanner dispatches: saves (26-7)×8 = ~152KB of context. Over 15 iterations: ~2.3MB of avoided context loading.

---

### 4. Smart Model Defaults

**Scope:** `skills/analyze-codebase/references/model-resolution.md`

#### Current Behavior

All stages default to `inherit` (session model, typically Opus).

#### New Default Model Map

| Stage | Default | Rationale |
|-------|---------|-----------|
| `scanning` | `sonnet` | Pattern matching, grep-based, structured output |
| `reconciliation` | `inherit` | Cross-dimension reasoning benefits from stronger models |
| `critique` | `sonnet` | Checklist validation, formula verification |
| `planning` | `inherit` | Complex dependency analysis benefits from stronger models |

#### Override Behavior (unchanged)

- `--model opus` → all stages use Opus
- `--model scanning:opus` → only scanning stage uses Opus
- `--model scanning:opus,critique:opus` → multiple stage overrides
- Per-stage overrides take precedence over blanket overrides

#### Rules

- Haiku MUST NOT be used as a default for any stage (Sonnet is the quality floor)
- The `inherit` default for reconciliation and planning means they use whatever the user's session model is
- Progressive escalation (Section 6) MAY override scanning model to Opus for stalled dimensions
- The `--model` flag always takes precedence over defaults and escalation

#### Quality Validation

Before committing these defaults as shipped behavior:

1. Run `analyze-codebase --plugin --model scanning:sonnet` on the code-analysis plugin
2. Run `analyze-codebase --plugin --model scanning:opus` on the same commit
3. Compare: finding count, severity distribution, finding ID overlap
4. **Acceptance criteria:**
   - Sonnet catches ≥ 90% of Opus critical+high findings
   - Dimension scores within 1.0 point
   - No critical findings missed

If validation fails, default reverts to `inherit` and progressive escalation (Section 6) becomes the primary cost optimization.

#### Estimated Impact

Scanners move from Opus ($1.875/MTok cache read) to Sonnet ($0.30/MTok cache read) = **6.25x cost reduction** for scanner dispatches. Scanners account for ~60% of total dispatches.

---

### 5. Mechanical Fix Bypass for Plugin Dimensions

**Scope:** `skills/ralph-loop/SKILL.md` (Step 4)

#### Current Behavior

Ralph-loop Step 4 invokes the superpowers pipeline (brainstorm → write-plan → subagent-driven-development) for any batch not entirely XS-mechanical.

#### New Behavior

Define `mechanical_dimensions` — dimensions where ALL fixes are known to be mechanical edits:

**Plugin mechanical dimensions:**
- `manifest-structure` — JSON edits, file moves
- `skill-quality` — markdown edits, frontmatter additions
- `agent-design` — markdown edits, examples additions
- `hook-correctness` — JSON schema fixes, script edits
- `marketplace-consistency` — JSON alignment, README edits
- `convention-adherence` — pattern replacements, file renames

**Non-mechanical (even in plugin mode):**
- `quality` — may require code refactoring
- `security` — may require architectural changes

For mechanical dimensions, ALL findings skip Step 4 (superpowers pipeline) and go directly to Step 5 (implement directly).

#### State File Addition

```markdown
mechanical_dimensions: [manifest-structure, skill-quality, agent-design, hook-correctness, marketplace-consistency, convention-adherence]
```

#### Rules

- Plugin dimensions listed above MUST be treated as mechanical by default
- `quality` and `security` MUST NOT be treated as mechanical
- Standard codebase dimensions (structure, testing) follow existing effort-based gating
- User MAY override via a future `--force-design` flag (not in this version)

#### Estimated Impact

Eliminates up to 3 agent dispatches per iteration (brainstorm + write-plan + subagent-driven-development) for plugin dimension fixes. Over 15 iterations: ~45 fewer agent dispatches.

---

### 6. Per-Dimension Iteration Tracking + Progressive Model Escalation

**Scope:** `skills/ralph-loop/SKILL.md`, `skills/ralph-loop/references/multi-dimension.md`

#### Current Behavior

Single global `iteration` counter. All dimensions use the same model throughout the loop.

#### New Behavior

**Per-dimension progress tracking:**

```markdown
dimension_progress:
  manifest-structure: {iterations: 5, score_history: [1.0, 4.0, 7.0, 8.5, 9.0], status: converged}
  quality: {iterations: 5, score_history: [1.0, 1.0, 2.0, 3.5, 4.0], status: active}
  security: {iterations: 5, score_history: [1.0, 5.0, 8.0, 8.0, 8.0], status: stalled}
```

**Stall detection:**
- A dimension is `stalled` if its score has not improved (delta ≤ 0) for 2 consecutive iterations
- Status values: `active` (default), `stalled` (no progress), `converged` (score ≥ target), `escalated` (model bumped)

**Progressive model escalation:**
- When a dimension is `stalled` AND current scanner model is Sonnet → escalate to Opus for that dimension's scanner only
- Mark status as `escalated`
- If still stalled after 2 more iterations at Opus → surface to user: "Dimension {name} has stalled at score {score}. Remaining findings may require manual intervention."

#### State File Additions

The `dimension_progress` block replaces the simple `score_history` list and provides:
- Per-dimension iteration count
- Per-dimension score history
- Per-dimension status
- Per-dimension model override (when escalated)

#### Rules

- MUST track per-dimension progress starting from iteration 1
- MUST detect stall after 2 consecutive iterations without score improvement
- MUST NOT escalate beyond Opus
- MUST surface stalled-at-Opus dimensions to the user
- Global `iteration` counter is preserved for overall loop control (`--max-iterations`)
- Global `max_iterations` still applies to total loop count

#### Estimated Impact

Opus is used surgically (only for stalled dimensions) instead of blanket. Combined with Sonnet defaults (Section 4), most scanning stays on Sonnet with Opus applied only where needed.

---

## Summary of Changes

| Section | Files Modified | New Files | Token Impact |
|---------|---------------|-----------|--------------|
| 1. Skip-Clean | ralph-loop/SKILL.md, verification-scan.md | — | ~40 fewer dispatches |
| 2. Inline Scoring | All scan-*/SKILL.md, analyze-codebase/SKILL.md | — | ~14 fewer reconciler dispatches |
| 3. Ref Splitting | All AGENT.md, relevant SKILL.md refs | 5 new schema files | ~2.3MB less context |
| 4. Model Defaults | model-resolution.md | — | 6.25x scanner cost reduction |
| 5. Mechanical Bypass | ralph-loop/SKILL.md | — | ~45 fewer dispatches |
| 6. Per-Dim Tracking | ralph-loop/SKILL.md, multi-dimension.md | — | Surgical Opus usage |

**Combined estimated impact:** 5-8x token reduction for a 10-dimension plugin ralph-loop run.

## Implementation Order

1. **Reference file splitting** (Section 3) — no behavioral changes, pure restructuring
2. **Inline scoring** (Section 2) — add self-scoring to scanners, update orchestrator
3. **Skip-clean dimensions** (Section 1) — update ralph-loop re-scan logic
4. **Mechanical fix bypass** (Section 5) — update ralph-loop Step 4
5. **Per-dimension tracking** (Section 6) — update ralph-loop state file and loop logic
6. **Smart model defaults** (Section 4) — update model-resolution.md, run validation
7. **Sonnet vs Opus validation** — run comparison and decide on shipping defaults

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Sonnet misses findings Opus catches | Progressive escalation (Section 6) + validation gate (Section 4) |
| Skip-clean misses regressions | Every-5th-iteration full scan safety net |
| Inline scoring formula drift | Same canonical formula documented in one place, referenced by all |
| Mechanical bypass misses design-needed fixes | quality + security excluded; plugin structure fixes are inherently mechanical |
| Per-dimension state file complexity | Backward-compatible: old state files still work, new fields are optional |
