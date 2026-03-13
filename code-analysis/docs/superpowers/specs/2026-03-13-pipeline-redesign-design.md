# Code-Analysis Pipeline Redesign — Design Spec

> Date: 2026-03-13
> Status: Approved
> Scope: Full pipeline rewrite of the `code-analysis` plugin

## Summary

Rewrite the code-analysis orchestrator from a 6-phase sequential pipeline to a 10-stage pipeline with full parallelism, a dedicated reconciliation agent, numeric scoring, auto-persisted draft reports, and two specialized critic agents (report-critic and plan-critic) with feedback loops.

## Goals

1. **Scoring**: Add numeric per-dimension (0-10) and weighted overall codebase health scores
2. **Report persistence**: Auto-persist draft reports after reconciliation; finalize after user approval
3. **Full parallelism**: Dispatch all 8 dimension scanners simultaneously (remove batch-of-3 limit)
4. **Reconciliation agent**: Dedicated agent for cross-dimension dedup, scoring, and unified report generation
5. **Report critic agent**: Validates analysis quality, scoring calibration, and coverage
6. **Plan critic agent**: Validates orchestrator refactoring plan feasibility, dependencies, and completeness

## Pipeline Architecture

```
Stage 1:  Detect Stack (sequential)
    |
Stage 2:  Scan All Dimensions (ALL 8 in parallel)
    |
Stage 3:  Reconcile (report-reconciler agent — dedup, score, draft report)
    |         -> Auto-persist draft reports to disk
    |
Stage 4:  Critique Report (report-critic agent)
    |         -> Feedback loop: max 3 iterations, then surface to user
    |
Stage 5:  User Checkpoint (review scored report, approve/skip/re-scan)
    |         -> Finalize reports on disk (overwrite drafts)
    |
Stage 6:  Deep Cross-Analysis + Refactoring Plans (only if user proceeds)
    |         -> Cross-dimension root cause analysis
    |         -> Per-dimension refactoring plans
    |
Stage 7:  Orchestrator Plan Generation
    |
Stage 8:  Critique Plan (plan-critic agent)
    |         -> Feedback loop: max 3 iterations, then surface to user
    |
Stage 9:  User Approval Gate (mandatory)
    |
Stage 10: Persist All Final Outputs
```

### Key Changes from Current Pipeline

| Aspect | Current (v0.0.2) | Redesign |
|--------|-------------------|----------|
| Dimension dispatch | Batches of 3 | All 8 in parallel |
| Reconciliation | Inline in orchestrator (Phase 3) | Dedicated `report-reconciler` agent |
| Scoring | None | Numeric 0-10 per dimension + weighted overall |
| Report persistence | Phase 6 only (end) | Draft at Stage 3, finalized at Stage 5/10 |
| Quality gates | None | 2 critic agents with feedback loops |
| Deep cross-analysis | None | Stage 6, gated on user proceeding to plans |
| Orchestrator role | Heavy (summary, reports, plans) | Thin dispatcher (JSON routing + agent dispatch) |

## New Agents

### Report Reconciler (`report-reconciler`)

**Purpose**: Receive all 8 dimension findings, deduplicate cross-dimension overlaps, compute numeric scores, produce unified analysis report.

**Inputs**: All dimension finding JSON arrays (passed by orchestrator after Stage 2).

**Workflow**:
1. **Dedup**: Identify findings that reference the same file/line range across dimensions (e.g., a god-class flagged by both `architecture` and `patterns`). Merge into single finding with multi-dimension tags.
2. **Score**: Compute per-dimension 0-10 score (severity-weighted deductions from base 10). Compute weighted overall score.
3. **Draft report**: Produce unified markdown report with score summary table, per-dimension breakdown, and cross-cutting observations.
4. **Auto-persist**: Write draft to `.code-analysis/reports/YYYY-MM-DD-analysis-draft.md`.

**Tools**: Read, Write, Grep, Glob

### Report Critic (`report-critic`)

**Purpose**: Validate quality of the reconciled analysis report.

**Evaluation criteria**:
- **Score calibration**: Are scores consistent across dimensions? (e.g., 3 critical findings MUST NOT score 8/10)
- **Coverage**: Are there obvious gaps? (e.g., no security findings in a web app with user input)
- **Dedup quality**: Were overlapping findings properly merged or incorrectly deduplicated?
- **Actionability**: Are recommendations specific enough to act on?

**Output**: Structured feedback JSON — `{ "verdict": "pass" | "fail", "issues": [...] }`. On fail, feedback is sent back to reconciler for revision.

**Tools**: Read, Grep, Glob

### Plan Critic (`plan-critic`)

**Purpose**: Validate quality and feasibility of the orchestrator refactoring plan.

**Evaluation criteria**:
- **Dependency correctness**: Are phase dependencies valid? Would executing Phase 1 break Phase 2 assumptions?
- **Effort realism**: Are effort estimates consistent with finding complexity?
- **Completeness**: Does the plan address all high/critical findings?
- **Risk assessment**: Are high-risk steps identified with rollback strategies?
- **Ordering**: Are quick wins genuinely quick? Are foundation steps placed before dependent work?

**Output**: Structured feedback JSON — `{ "verdict": "pass" | "fail", "issues": [...] }`. On fail, feedback loops back to plan generation.

**Tools**: Read, Grep, Glob

## Scoring System

### Per-Dimension Score (0-10)

- Base score: 10
- Deductions per finding (after dedup):
  - critical: -3
  - high: -2
  - medium: -1
  - low: -0.5
  - info: 0
- Floor: 0

### Overall Score (0-10)

- Weighted average of all dimension scores
- Default weights: equal (1.0 per dimension)
- Overridable via `--weights=security:2,architecture:1.5,...`

### Score Display

```markdown
## Codebase Health Score: 6.8/10

| Dimension    | Score | Findings | Crit | High | Med | Low |
|-------------|-------|----------|------|------|-----|-----|
| Security     | 4/10  | 12       | 2    | 3    | 5   | 2   |
| Architecture | 7/10  | 8        | 0    | 2    | 4   | 2   |
| Quality      | 8/10  | 5        | 0    | 1    | 2   | 2   |
| ...          | ...   | ...      | ...  | ...  | ... | ... |
```

## Report Persistence Model

### Draft Persistence (Stage 3 — automatic)

```
.code-analysis/
├── scan-reports/
│   └── YYYY-MM-DD-{dimension}.json          # Raw findings per dimension
├── reports/
│   └── YYYY-MM-DD-analysis-draft.md         # Draft unified report (scored)
```

### Final Persistence (Stage 5 for reports, Stage 10 for plans)

```
.code-analysis/
├── scan-reports/
│   └── YYYY-MM-DD-{dimension}.json          # Unchanged from draft
├── reports/
│   ├── YYYY-MM-DD-analysis.md               # Final report (overwrites draft)
│   └── YYYY-MM-DD-scores.json               # Machine-readable scores
├── plans/
│   ├── YYYY-MM-DD-{dimension}-plan.md       # Per-dimension refactoring plans
│   └── YYYY-MM-DD-orchestrator-plan.md      # Master plan
```

`scores.json` enables tracking scores over time (diff against previous runs).

## Orchestrator Rewrite

The orchestrator becomes a **thin dispatcher**. It MUST NOT:
- Load dimension sub-skills, language profiles, or framework profiles
- Perform inline report generation or summary compilation
- Hold dimension-specific logic

It MUST:
- Parse flags and detect stack
- Dispatch agents and collect their outputs
- Manage critic feedback loops
- Handle user checkpoints
- Coordinate persistence

### Full Parallelism Rationale

The current batch-of-3 limit was a safety measure for the orchestrator's context window when it processed dimension details inline. With the redesign:
- Each `code-analyzer` agent runs in its own isolated context
- The orchestrator only receives compact JSON findings arrays
- Heavy analysis (dedup, scoring, cross-analysis) moves to dedicated agents
- Dispatching all 8 in parallel is safe and significantly faster

### Critic Feedback Loop Pattern

Both critics follow the same pattern:

```
attempt = 0
loop:
  if attempt >= max_iterations: surface issues to user, break
  dispatch critic agent with current artifact
  if critic returns "pass": break
  dispatch producer agent with critic feedback
  attempt++
```

The critic MUST NOT modify artifacts directly — it returns structured feedback that the producer (reconciler or plan generator) uses to revise.

## Deep Cross-Analysis (Stage 6)

Only executed when user approves at Stage 5 and opts to proceed to refactoring plans. This stage is handled by the `report-reconciler` agent (re-dispatched with a `--deep` flag), NOT by a separate agent. It:
- Detects when findings across different dimensions share root causes
- Suggests combined fixes that address multiple dimensions simultaneously
- Identifies systemic patterns (e.g., "lack of abstraction layer causes both architecture and testing issues")

This analysis feeds into the refactoring plan generator as additional context, enabling smarter plan construction.

**Implementation note**: The reconciler already has all dimension findings in context from Stage 3. Re-dispatching it with `--deep` avoids creating a new agent and re-loading all findings. The deep analysis output is a separate JSON artifact (`cross-analysis.json`) passed to the plan generator.

## Changes to Existing Components

| Component | Change |
|-----------|--------|
| `code-analyzer` agent | **Unchanged** — still scans one dimension, returns JSON |
| `refactoring-planner` agent | **Updated** — accepts critic feedback and cross-analysis as additional input |
| `analyze-codebase` skill | **Full rewrite** — thin dispatcher pattern |
| `refactor-plan` skill | **Updated** — passes critic feedback through |
| `scan-*` sub-skills | **Unchanged** |
| `generate-refactoring-plan` sub-skill | **Unchanged** |
| `generate-orchestrator-plan` sub-skill | **Unchanged** |

## New CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--weights=dim:N,...` | Equal (1.0) | Custom dimension weights for overall score |
| `--critic-iterations=N` | 3 | Max critic feedback loop iterations |
| `--skip-critics` | false | Bypass critic loops entirely (for speed) |
| `--draft-only` | false | Stop after Stage 3 (scan + reconcile + persist draft) |

## New Files to Create

### Agents
- `agents/report-reconciler/AGENT.md`
- `agents/report-critic/AGENT.md`
- `agents/plan-critic/AGENT.md`

### Skills
- `skills/reconcile-report/SKILL.md` — reconciliation sub-skill loaded by the agent
- `skills/critique-report/SKILL.md` — report critic evaluation criteria and workflow
- `skills/critique-plan/SKILL.md` — plan critic evaluation criteria and workflow

### Schemas
- Update `references/output-schemas.md` with `scores.json` schema and critic feedback schema

### Templates
- `templates/analysis-draft.md` — draft report template (with score table)
- Update `templates/dimension-report.md` if needed for score integration

## Files to Modify

- `skills/analyze-codebase/SKILL.md` — full rewrite (thin dispatcher)
- `skills/refactor-plan/SKILL.md` — add critic feedback passthrough
- `agents/refactoring-planner/AGENT.md` — accept critic feedback input
- `plugin.json` — register new agents
- `references/output-schemas.md` — add new schemas
