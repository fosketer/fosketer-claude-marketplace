# Pipeline Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the code-analysis plugin from a 6-phase batched pipeline to a 10-stage fully parallel pipeline with reconciliation agent, numeric scoring, critic feedback loops, and draft/final report persistence.

**Architecture:** Thin orchestrator dispatches all 8 dimension scanners in parallel, a reconciliation agent deduplicates and scores findings, two critic agents (report-critic and plan-critic) validate quality via feedback loops, and reports auto-persist as drafts then finalize on user approval.

**Tech Stack:** Claude Code plugin system (AGENT.md, SKILL.md, plugin.json), Mustache templates, JSON schemas

**Spec:** `docs/superpowers/specs/2026-03-13-pipeline-redesign-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `agents/report-reconciler/AGENT.md` | Agent definition for reconciliation: dedup, score, draft report |
| `agents/report-critic/AGENT.md` | Agent definition for report quality validation |
| `agents/plan-critic/AGENT.md` | Agent definition for plan feasibility validation |
| `skills/reconcile-report/SKILL.md` | Sub-skill: dedup workflow, scoring formula, report assembly |
| `skills/critique-report/SKILL.md` | Sub-skill: report evaluation criteria, feedback format |
| `skills/critique-plan/SKILL.md` | Sub-skill: plan evaluation criteria, feedback format |
| `templates/analysis-draft.md` | Mustache template for unified scored report (draft & final) |

### Modified Files

| File | Change |
|------|--------|
| `plugin.json` | Register 3 new agents, bump version to 0.1.0 |
| `skills/analyze-codebase/SKILL.md` | Full rewrite — thin dispatcher with 10 stages |
| `skills/refactor-plan/SKILL.md` | Add `--skip-critics` passthrough |
| `agents/refactoring-planner/AGENT.md` | Accept critic feedback + cross-analysis input |
| `references/output-schemas.md` | Add ScoresReport, CriticFeedback, CrossAnalysis schemas |

### Unchanged Files

All `skills/scan-*/SKILL.md`, `skills/generate-refactoring-plan/SKILL.md`, `skills/generate-orchestrator-plan/SKILL.md`, `templates/dimension-report.md` (per-dimension reports do not include scores — scores live in the unified report only), `templates/refactoring-plan.md`, `templates/orchestrator-plan.md`, `agents/code-analyzer/AGENT.md` (read-only subagent), language/framework profiles.

**Note on templates**: Templates use Mustache-like syntax as rendering instructions for agents. Agents interpret and fill the template placeholders directly — no Mustache library is required.

---

## Chunk 1: Output Schemas & Templates

### Task 1: Add ScoresReport schema to output-schemas.md

**Files:**
- Modify: `references/output-schemas.md` (append after OrchestratorPlan schema)

- [ ] **Step 1: Read the current file**

Run: Read `references/output-schemas.md` to confirm current end-of-file content.

- [ ] **Step 2: Append ScoresReport schema**

Add after the closing ``` of the OrchestratorPlan schema section:

```markdown
## Scores Report Schema

Machine-readable scores produced by the reconciliation agent. Enables tracking health over time.

\`\`\`json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ScoresReport",
  "type": "object",
  "required": ["metadata", "dimension_scores", "overall_score", "dedup_stats"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["date", "project_path", "dimensions_analyzed", "stack"],
      "properties": {
        "date": { "type": "string", "format": "date" },
        "project_path": { "type": "string" },
        "dimensions_analyzed": { "type": "array", "items": { "type": "string" } },
        "stack": {
          "type": "object",
          "properties": {
            "languages": { "type": "array", "items": { "type": "string" } },
            "frameworks": { "type": "array", "items": { "type": "string" } }
          }
        },
        "weights": {
          "type": "object",
          "description": "Dimension weights used for overall score calculation",
          "additionalProperties": { "type": "number" }
        }
      }
    },
    "dimension_scores": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["dimension", "score", "findings_count", "by_severity"],
        "properties": {
          "dimension": { "type": "string" },
          "score": { "type": "number", "minimum": 0, "maximum": 10 },
          "findings_count": { "type": "integer" },
          "by_severity": {
            "type": "object",
            "properties": {
              "critical": { "type": "integer", "default": 0 },
              "high": { "type": "integer", "default": 0 },
              "medium": { "type": "integer", "default": 0 },
              "low": { "type": "integer", "default": 0 },
              "info": { "type": "integer", "default": 0 }
            }
          }
        }
      }
    },
    "overall_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 10,
      "description": "Weighted average of dimension scores"
    },
    "dedup_stats": {
      "type": "object",
      "required": ["total_raw_findings", "total_after_dedup", "merged_count"],
      "properties": {
        "total_raw_findings": { "type": "integer", "description": "Sum of findings across all dimensions before dedup" },
        "total_after_dedup": { "type": "integer", "description": "Findings count after cross-dimension dedup" },
        "merged_count": { "type": "integer", "description": "Number of findings merged during dedup" }
      }
    }
  }
}
\`\`\`
```

- [ ] **Step 3: Commit**

```bash
git add references/output-schemas.md
git commit -m "feat(schemas): add ScoresReport schema for numeric scoring"
```

---

### Task 2: Add CriticFeedback schema to output-schemas.md

**Files:**
- Modify: `references/output-schemas.md` (append after ScoresReport)

- [ ] **Step 1: Append CriticFeedback schema**

Add after the ScoresReport section:

```markdown
## Critic Feedback Schema

Structured feedback produced by report-critic and plan-critic agents.

\`\`\`json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CriticFeedback",
  "type": "object",
  "required": ["verdict", "target", "iteration", "issues"],
  "properties": {
    "verdict": {
      "type": "string",
      "enum": ["pass", "fail"],
      "description": "Overall verdict — pass means artifact is acceptable"
    },
    "target": {
      "type": "string",
      "enum": ["report", "plan"],
      "description": "Which artifact was reviewed"
    },
    "iteration": {
      "type": "integer",
      "minimum": 1,
      "description": "Which iteration of the feedback loop this is"
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["category", "severity", "description", "suggestion"],
        "properties": {
          "category": {
            "type": "string",
            "enum": ["score-calibration", "coverage-gap", "dedup-error", "actionability", "dependency-error", "effort-mismatch", "completeness-gap", "risk-gap", "ordering-error"],
            "description": "Type of issue found"
          },
          "severity": {
            "type": "string",
            "enum": ["blocking", "warning"],
            "description": "blocking = must fix before pass, warning = advisory"
          },
          "description": {
            "type": "string",
            "description": "What is wrong"
          },
          "suggestion": {
            "type": "string",
            "description": "How to fix it"
          },
          "context": {
            "type": "string",
            "description": "Optional: specific finding ID, dimension, or section reference",
            "nullable": true
          }
        }
      }
    }
  }
}
\`\`\`
```

- [ ] **Step 2: Commit**

```bash
git add references/output-schemas.md
git commit -m "feat(schemas): add CriticFeedback schema for critic agents"
```

---

### Task 3: Add CrossAnalysis schema to output-schemas.md

**Files:**
- Modify: `references/output-schemas.md` (append after CriticFeedback)

- [ ] **Step 1: Append CrossAnalysis schema**

```markdown
## Cross-Analysis Schema

Output of the deep cross-dimension analysis (Stage 6). Produced by the report-reconciler agent when re-dispatched with `--deep`.

\`\`\`json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CrossAnalysis",
  "type": "object",
  "required": ["metadata", "root_causes", "systemic_patterns", "combined_fixes"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["date", "project_path", "dimensions_analyzed"],
      "properties": {
        "date": { "type": "string", "format": "date" },
        "project_path": { "type": "string" },
        "dimensions_analyzed": { "type": "array", "items": { "type": "string" } }
      }
    },
    "root_causes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "description", "affected_dimensions", "related_finding_ids"],
        "properties": {
          "id": { "type": "string", "pattern": "^rc-\\d{3}$" },
          "title": { "type": "string", "maxLength": 100 },
          "description": { "type": "string" },
          "affected_dimensions": { "type": "array", "items": { "type": "string" } },
          "related_finding_ids": { "type": "array", "items": { "type": "string" } }
        }
      },
      "description": "Findings across dimensions that share a common root cause"
    },
    "systemic_patterns": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "description", "evidence"],
        "properties": {
          "title": { "type": "string" },
          "description": { "type": "string" },
          "evidence": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Finding IDs or file paths that support this pattern"
          }
        }
      },
      "description": "High-level systemic issues (e.g., lack of abstraction layer)"
    },
    "combined_fixes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "description", "addresses_root_causes", "estimated_effort"],
        "properties": {
          "title": { "type": "string" },
          "description": { "type": "string" },
          "addresses_root_causes": { "type": "array", "items": { "type": "string" }, "description": "Root cause IDs this fix addresses" },
          "estimated_effort": { "type": "string", "enum": ["trivial", "small", "medium", "large", "xl"] }
        }
      },
      "description": "Suggested fixes that address multiple dimensions simultaneously"
    }
  }
}
\`\`\`
```

- [ ] **Step 2: Commit**

```bash
git add references/output-schemas.md
git commit -m "feat(schemas): add CrossAnalysis schema for deep cross-dimension analysis"
```

---

### Task 4: Create analysis-draft.md template

**Files:**
- Create: `templates/analysis-draft.md`

- [ ] **Step 1: Create the template file**

```markdown
# Codebase Analysis Report{{#is_draft}} (DRAFT){{/is_draft}}

**Date**: {{date}}
**Project**: {{project_path}}
**Stack**: {{stack}}
**Dimensions analyzed**: {{dimensions_list}}

---

## Codebase Health Score: {{overall_score}}/10

| Dimension | Score | Findings | Crit | High | Med | Low | Info |
|-----------|-------|----------|------|------|-----|-----|------|
{{#dimension_scores}}
| {{dimension}} | {{score}}/10 | {{findings_count}} | {{critical}} | {{high}} | {{medium}} | {{low}} | {{info}} |
{{/dimension_scores}}

**Deduplication**: {{dedup_merged}} findings merged across dimensions ({{dedup_raw}} raw → {{dedup_final}} unique)

{{#weights_custom}}
**Custom weights applied**: {{weights_description}}
{{/weights_custom}}

---

## Cross-Cutting Observations

{{cross_cutting_observations}}

---

{{#dimension_sections}}

## {{dimension_name}} ({{score}}/10)

{{summary}}

### Top Findings

{{#top_findings}}
- **{{severity}}** — {{title}} (`{{file_path}}:{{line_start}}`)
  {{recommendation}}

{{/top_findings}}

{{#remaining_count}}
*...and {{remaining_count}} more findings. See per-dimension report for full details.*
{{/remaining_count}}

---

{{/dimension_sections}}

{{#is_draft}}
> **This is a draft report.** It will be finalized after review.
{{/is_draft}}
```

- [ ] **Step 2: Commit**

```bash
git add templates/analysis-draft.md
git commit -m "feat(templates): add unified analysis report template with scoring"
```

---

## Chunk 2: New Agent Definitions

### Task 5: Create report-reconciler agent

**Files:**
- Create: `agents/report-reconciler/AGENT.md`

- [ ] **Step 1: Create agent directory and file**

```yaml
---
name: report-reconciler
description: |
  Use this agent to reconcile findings from all dimension scanners into a unified,
  deduplicated, scored analysis report. Dispatched by the analyze-codebase orchestrator
  after all dimension scans complete (Stage 3), or re-dispatched with --deep for
  cross-dimension root cause analysis (Stage 6).

  <example>
  Context: Orchestrator has collected all 8 dimension findings
  user: "Analyze this codebase"
  assistant: "All scans complete. Dispatching report-reconciler to deduplicate and score."
  <commentary>
  The orchestrator dispatches report-reconciler with all findings arrays.
  The agent deduplicates, scores, and produces a unified draft report.
  </commentary>
  </example>

  <example>
  Context: User approved report and wants refactoring plans
  user: "Proceed to refactoring plans"
  assistant: "Dispatching report-reconciler with --deep for cross-dimension analysis."
  <commentary>
  Re-dispatched with --deep flag to perform root cause analysis across dimensions.
  Output is cross-analysis.json fed to the plan generator.
  </commentary>
  </example>

model: inherit
color: blue
tools: ["Read", "Write", "Grep", "Glob"]
---

You are a Report Reconciler. You receive findings from all dimension scanners and produce a unified, scored analysis report.

## Modes

You operate in one of two modes based on input:

### Mode 1: Reconcile (default)

**Input**: All dimension finding JSON arrays, stack info, project path, weights (optional)

**Process**:

#### Step 1 — Load Resources

Read:
1. `${CLAUDE_PLUGIN_ROOT}/skills/reconcile-report/SKILL.md` — the reconciliation workflow
2. `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md` — ScoresReport schema
3. `${CLAUDE_PLUGIN_ROOT}/templates/analysis-draft.md` — report template

#### Step 2 — Execute Reconciliation

Follow the `reconcile-report` sub-skill workflow with all findings.

#### Step 3 — Persist Draft

Write outputs:
- `.code-analysis/scan-reports/YYYY-MM-DD-{dimension}.json` — raw per-dimension findings
- `.code-analysis/reports/YYYY-MM-DD-analysis-draft.md` — unified scored report
- `.code-analysis/reports/YYYY-MM-DD-scores.json` — machine-readable scores

Create `.code-analysis/` and subdirectories if they do not exist.

#### Step 4 — Return Summary

Return to orchestrator:
- Overall score and per-dimension scores
- Dedup statistics
- Path to draft report

### Mode 2: Deep Cross-Analysis (`--deep`)

**Input**: All dimension findings (same as Mode 1) + `--deep` flag

**Process**:

#### Step 1 — Load Resources

Read:
1. `${CLAUDE_PLUGIN_ROOT}/skills/reconcile-report/SKILL.md` — cross-analysis section
2. `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md` — CrossAnalysis schema

#### Step 2 — Execute Deep Analysis

Follow the cross-analysis workflow in the sub-skill:
1. Identify shared root causes across dimensions
2. Detect systemic patterns
3. Suggest combined fixes

#### Step 3 — Return Cross-Analysis

Return CrossAnalysis JSON to the orchestrator (NOT persisted — used as input to plan generator).

## Revision Handling

If dispatched with critic feedback (from report-critic):
1. Read the feedback issues
2. Re-execute reconciliation addressing each blocking issue
3. Return revised report

## Notes

- This agent does NOT scan the codebase — it works from findings provided by the orchestrator
- Dedup is conservative: only merge findings with overlapping file+line ranges across dimensions
- Scores use the formula: base 10, deductions per severity (critical=-3, high=-2, medium=-1, low=-0.5, info=0), floor at 0
```

- [ ] **Step 2: Commit**

```bash
git add agents/report-reconciler/AGENT.md
git commit -m "feat(agents): add report-reconciler agent for dedup, scoring, and report assembly"
```

---

### Task 6: Create report-critic agent

**Files:**
- Create: `agents/report-critic/AGENT.md`

- [ ] **Step 1: Create agent directory and file**

```yaml
---
name: report-critic
description: |
  Use this agent to validate the quality of a reconciled analysis report.
  Dispatched by the analyze-codebase orchestrator after reconciliation (Stage 4).
  Returns structured feedback — never modifies the report directly.

  <example>
  Context: Orchestrator has a reconciled report ready for validation
  user: "Analyze this codebase"
  assistant: "Report reconciled. Dispatching report-critic for quality validation."
  <commentary>
  The orchestrator dispatches report-critic with the draft report and scores.
  The critic returns pass/fail verdict with structured issues.
  </commentary>
  </example>

model: inherit
color: orange
tools: ["Read", "Grep", "Glob"]
---

You are a Report Critic. You validate the quality of a reconciled codebase analysis report and return structured feedback.

## Input

You will receive:
- Path to the draft report (`.code-analysis/reports/YYYY-MM-DD-analysis-draft.md`)
- Path to the scores file (`.code-analysis/reports/YYYY-MM-DD-scores.json`)
- Path to the raw scan reports directory (`.code-analysis/scan-reports/`)
- Stack information (languages, frameworks)
- The project path being analyzed
- Iteration number (1-based)

## Process

### Step 1 — Load Resources

Read:
1. `${CLAUDE_PLUGIN_ROOT}/skills/critique-report/SKILL.md` — evaluation criteria and workflow
2. `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md` — CriticFeedback schema

### Step 2 — Execute Evaluation

Follow the `critique-report` sub-skill workflow.

### Step 3 — Return Feedback

Return a CriticFeedback JSON object to the orchestrator.

## Notes

- You MUST NOT modify the report — only return feedback
- You MUST NOT re-scan the codebase — work only from the provided artifacts
- On iteration > 1, you receive prior feedback to check if issues were addressed
- If all blocking issues are resolved, return verdict "pass" (warnings MAY remain)
```

- [ ] **Step 2: Commit**

```bash
git add agents/report-critic/AGENT.md
git commit -m "feat(agents): add report-critic agent for analysis report validation"
```

---

### Task 7: Create plan-critic agent

**Files:**
- Create: `agents/plan-critic/AGENT.md`

- [ ] **Step 1: Create agent directory and file**

```yaml
---
name: plan-critic
description: |
  Use this agent to validate the quality and feasibility of an orchestrator
  refactoring plan. Dispatched by the analyze-codebase orchestrator after plan
  generation (Stage 8). Returns structured feedback — never modifies the plan directly.

  <example>
  Context: Orchestrator has generated the master refactoring plan
  user: "Analyze this codebase"
  assistant: "Orchestrator plan generated. Dispatching plan-critic for validation."
  <commentary>
  The orchestrator dispatches plan-critic with the orchestrator plan and findings.
  The critic returns pass/fail verdict with structured issues.
  </commentary>
  </example>

model: inherit
color: red
tools: ["Read", "Grep", "Glob"]
---

You are a Plan Critic. You validate the quality and feasibility of an orchestrator refactoring plan and return structured feedback.

## Input

You will receive:
- The orchestrator plan (OrchestratorPlan JSON or rendered markdown)
- All per-dimension refactoring plans
- The reconciled scores report
- Cross-analysis results (if available)
- Stack information
- The project path
- Iteration number (1-based)

## Process

### Step 1 — Load Resources

Read:
1. `${CLAUDE_PLUGIN_ROOT}/skills/critique-plan/SKILL.md` — evaluation criteria and workflow
2. `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md` — CriticFeedback schema

### Step 2 — Execute Evaluation

Follow the `critique-plan` sub-skill workflow.

### Step 3 — Return Feedback

Return a CriticFeedback JSON object with `"target": "plan"` to the orchestrator.

## Notes

- You MUST NOT modify the plan — only return feedback
- You MUST NOT re-scan the codebase — work only from the provided artifacts
- On iteration > 1, you receive prior feedback to check if issues were addressed
- Focus on feasibility and correctness, not style
- If all blocking issues are resolved, return verdict "pass" (warnings MAY remain)
```

- [ ] **Step 2: Commit**

```bash
git add agents/plan-critic/AGENT.md
git commit -m "feat(agents): add plan-critic agent for refactoring plan validation"
```

---

## Chunk 3: New Sub-Skills

### Task 8: Create reconcile-report sub-skill

**Files:**
- Create: `skills/reconcile-report/SKILL.md`

- [ ] **Step 1: Create skill directory and file**

```yaml
---
name: reconcile-report
description: |
  Sub-skill for cross-dimension deduplication, scoring, and unified report assembly.
  Loaded by the report-reconciler agent.
---

# Reconcile Report

## Purpose

Deduplicate findings across dimensions, compute numeric scores, and produce a unified analysis report with a codebase health score.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `FINDINGS_BY_DIMENSION`: Object mapping dimension names to their findings arrays
- `STACK`: Detected language/framework
- `PROJECT_PATH`: Root directory of the project
- `WEIGHTS`: Optional object mapping dimension names to weight values (default: all 1.0)
- `CRITIC_FEEDBACK`: Optional CriticFeedback from a prior iteration (null on first run)

## Reconciliation Workflow

### Step 1 — Cross-Dimension Deduplication

For each pair of findings across different dimensions:

1. **Check file overlap**: Do they reference the same `file_path`?
2. **Check line overlap**: Do their `[line_start, line_end]` ranges overlap (within 5-line tolerance)?
3. **If both match**: Merge into a single finding:
   - Keep the higher severity
   - Combine dimension tags: `"dimensions": ["architecture", "patterns"]`
   - Merge recommendations (deduplicate identical ones)
   - Use the more specific description
   - Assign the merged finding to the dimension with the highest weight

**Conservative dedup rule**: Only merge when file AND line range overlap. Do NOT merge based on title similarity alone — false positives are worse than duplicates.

### Step 2 — Compute Dimension Scores

For each dimension, after dedup:

1. Count findings assigned to this dimension (including merged findings assigned here)
2. Apply deduction formula:
   ```
   score = max(0, 10 - sum(deductions))

   deductions per finding:
     critical = 3
     high     = 2
     medium   = 1
     low      = 0.5
     info     = 0
   ```
3. Round to 1 decimal place

**Edge case**: A dimension with zero findings (all clean) scores 10.0. A dimension with only `info` findings also scores 10.0. This is intended — info findings are observations, not problems.

### Step 3 — Compute Overall Score

```
overall = sum(dimension_score * weight) / sum(weights)
```

Round to 1 decimal place. If `--weights` not provided, all weights are 1.0 (simple average).

For partial `--weights` (e.g., only security:2 specified), unspecified dimensions default to 1.0.

### Step 4 — Identify Cross-Cutting Observations

Scan the deduplicated findings for patterns:
- Dimensions where score < 5.0 → flag as critical areas
- Dimensions with 0 findings → note as clean
- Clusters of findings in the same file across dimensions → note as hotspot files
- Significant score gaps between related dimensions (e.g., architecture 3/10 but patterns 9/10) → note inconsistency

Write 3-5 bullet points summarizing these observations.

### Step 5 — Assemble Report

Use the `analysis-draft.md` template:
1. Set `is_draft = true` for draft reports
2. For each dimension section, include top 5 findings by severity
3. If dimension has > 5 findings, show `remaining_count`
4. Include cross-cutting observations from Step 4

### Step 6 — Assemble Scores JSON

Produce `scores.json` matching the ScoresReport schema.

### Step 7 — Handle Critic Feedback (if present)

If `CRITIC_FEEDBACK` is provided:
1. Read each issue in the feedback
2. For `blocking` issues:
   - `score-calibration`: Re-check scoring formula application
   - `coverage-gap`: Note the gap in cross-cutting observations (cannot re-scan)
   - `dedup-error`: Undo or redo specific merges as suggested
   - `actionability`: Revise affected recommendations
3. For `warning` issues: Address if trivial, otherwise note in report
4. Re-run Steps 2-6 with corrections

## Cross-Analysis Workflow (--deep mode)

When invoked with `--deep`:

### Step 1 — Identify Shared Root Causes

For each cluster of findings across 2+ dimensions that affect the same files:
1. Analyze whether a single architectural/design issue could explain all of them
2. If yes, create a root cause entry with:
   - A descriptive title
   - Which dimensions are affected
   - Which finding IDs are related

### Step 2 — Detect Systemic Patterns

Look for:
- Files that appear in 3+ dimension findings → "hotspot" pattern
- Entire directories with consistent issues → "module-level" pattern
- Missing abstraction layers (architecture + testing + quality issues in same area)
- Dependency issues causing cascade effects (dependencies → performance → quality)

### Step 3 — Suggest Combined Fixes

For each root cause, propose a fix that addresses multiple dimensions:
- Title and description
- Which root causes it addresses
- Estimated effort

### Step 4 — Return CrossAnalysis JSON

Produce output matching the CrossAnalysis schema. Do NOT persist — return to orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Empty findings for a dimension | Score 10.0, skip from report sections |
| All dimensions empty | Score 10/10 overall, note codebase is clean |
| Dedup merges > 30% of findings | Log warning — may indicate dimension overlap, but proceed |
| Critic feedback references non-existent finding | Skip that feedback item, note in response |
| --deep with < 2 dimensions | Skip cross-analysis, return empty CrossAnalysis |

## Success Checklist

- [ ] All findings deduplicated across dimensions
- [ ] Per-dimension scores computed and valid (0-10)
- [ ] Overall score computed with correct weights
- [ ] Cross-cutting observations include 3-5 bullet points
- [ ] Draft report written using template
- [ ] scores.json matches ScoresReport schema
- [ ] Critic feedback addressed (if provided)
```

- [ ] **Step 2: Commit**

```bash
git add skills/reconcile-report/SKILL.md
git commit -m "feat(skills): add reconcile-report sub-skill with dedup, scoring, and cross-analysis"
```

---

### Task 9: Create critique-report sub-skill

**Files:**
- Create: `skills/critique-report/SKILL.md`

- [ ] **Step 1: Create skill directory and file**

```yaml
---
name: critique-report
description: |
  Sub-skill for evaluating the quality of a reconciled analysis report.
  Loaded by the report-critic agent.
---

# Critique Report

## Purpose

Evaluate a reconciled analysis report for quality, scoring accuracy, coverage, and actionability. Return structured feedback.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `DRAFT_REPORT_PATH`: Path to the draft report markdown
- `SCORES_PATH`: Path to the scores.json file
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/`
- `STACK`: Detected language/framework
- `PROJECT_PATH`: Root directory of the project
- `ITERATION`: Current iteration number (1-based)
- `PRIOR_FEEDBACK`: Previous CriticFeedback (null on first iteration)

## Evaluation Workflow

### Check 1 — Score Calibration

Read `scores.json` and verify:

1. **Formula correctness**: For each dimension, manually count findings by severity and verify:
   ```
   expected_score = max(0, 10 - (critical*3 + high*2 + medium*1 + low*0.5))
   ```
   Tolerance: ±0.1 (rounding)

2. **Cross-dimension consistency**: Flag if:
   - A dimension with more critical findings scores higher than one with fewer
   - Two dimensions have similar finding profiles but scores differ by > 2 points
   - Overall score does not match weighted average (tolerance ±0.1)

3. **Weight application**: If custom weights were used, verify they were applied correctly

**Issue category**: `score-calibration`
**Severity**: `blocking` if formula is wrong; `warning` if consistency concern

### Check 2 — Coverage Gaps

Read the scan reports and check for obvious gaps:

1. **Stack-based expectations**: Based on `STACK`:
   - Web app (React, .NET web) → SHOULD have security findings related to XSS, auth
   - API project → SHOULD have security findings related to injection, auth
   - Data project → SHOULD have performance findings related to data handling
   - If a dimension has 0 findings where findings are expected, flag

2. **Dimension balance**: If one dimension has 20+ findings and a related dimension has 0, flag (e.g., architecture has 20 issues but patterns has 0 — unlikely)

**Issue category**: `coverage-gap`
**Severity**: `warning` (critic cannot re-scan, but should flag for user awareness)

### Check 3 — Dedup Quality

Read the raw scan reports and the dedup stats in scores.json:

1. **Over-merging**: If dedup merged > 40% of total findings, flag as potential over-merging
2. **Under-merging**: Spot-check 5 random pairs of findings in the same file across dimensions — if any clearly refer to the same issue but were not merged, flag
3. **Severity preservation**: Verify merged findings kept the higher severity

**Issue category**: `dedup-error`
**Severity**: `blocking` if clear merge errors; `warning` if questionable

### Check 4 — Actionability

Read the draft report and check:

1. **Recommendations specificity**: Sample 5 findings — each recommendation MUST reference specific files, patterns, or actions (not "improve this" or "consider refactoring")
2. **Cross-cutting observations**: MUST contain 3-5 bullet points, MUST reference specific dimensions or files
3. **Top findings selection**: Each dimension section SHOULD show the highest-severity findings first

**Issue category**: `actionability`
**Severity**: `blocking` if recommendations are vague; `warning` if observations are thin

### Check 5 — Prior Feedback Resolution (iteration > 1)

If `PRIOR_FEEDBACK` is provided:
1. For each `blocking` issue in prior feedback, verify it was addressed
2. If a blocking issue persists, re-flag with escalated context
3. Accumulate all unresolved issues across iterations

**Issue category**: same as original issue
**Severity**: `blocking` if still unresolved

## Output

Produce CriticFeedback JSON matching the schema:
- `verdict`: "pass" if zero blocking issues, "fail" otherwise
- `target`: "report"
- `iteration`: current iteration number
- `issues`: array of all issues found (blocking and warning)

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Cannot read scores.json | Flag as blocking — scores file missing or malformed |
| Cannot read scan reports | Flag as blocking — raw data unavailable for validation |
| Draft report missing sections | Flag as blocking — report template not fully rendered |
| Iteration >= 3 with persistent blocking issues | Include all accumulated issues for user escalation |
```

- [ ] **Step 2: Commit**

```bash
git add skills/critique-report/SKILL.md
git commit -m "feat(skills): add critique-report sub-skill with 5-check evaluation workflow"
```

---

### Task 10: Create critique-plan sub-skill

**Files:**
- Create: `skills/critique-plan/SKILL.md`

- [ ] **Step 1: Create skill directory and file**

```yaml
---
name: critique-plan
description: |
  Sub-skill for evaluating the quality and feasibility of an orchestrator refactoring plan.
  Loaded by the plan-critic agent.
---

# Critique Plan

## Purpose

Evaluate an orchestrator refactoring plan for dependency correctness, effort realism, completeness, risk assessment, and ordering. Return structured feedback.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `ORCHESTRATOR_PLAN`: The master plan (OrchestratorPlan JSON or rendered markdown)
- `DIMENSION_PLANS`: All per-dimension refactoring plans
- `SCORES_REPORT`: The reconciled scores report
- `CROSS_ANALYSIS`: Cross-analysis results (null if not available)
- `STACK`: Detected language/framework
- `PROJECT_PATH`: Root directory of the project
- `ITERATION`: Current iteration number (1-based)
- `PRIOR_FEEDBACK`: Previous CriticFeedback (null on first iteration)

## Evaluation Workflow

### Check 1 — Dependency Correctness

1. **Phase ordering**: Verify that phases follow the expected pattern:
   - Phase 1: Security + quick wins
   - Phase 2: Architecture + dependencies + patterns
   - Phase 3: Quality + performance + testing + large tech debt
2. **File conflict detection**: For each pair of plans in the same phase, check if they modify the same files. If so, verify explicit ordering is defined within the phase.
3. **Cross-phase dependencies**: Verify that no plan in a later phase depends on a file that a same-phase or later-phase plan also modifies without ordering.

**Issue category**: `dependency-error`
**Severity**: `blocking` if executing the plan as-is would cause conflicts; `warning` if ordering is ambiguous

### Check 2 — Effort Realism

1. **Per-step effort**: Sample 5 plan steps and verify effort estimates are reasonable:
   - A step that modifies 1 file with a simple change SHOULD NOT be "large" or "xl"
   - A step that modifies 5+ files or introduces new patterns SHOULD NOT be "trivial" or "small"
2. **Total effort**: Verify the total effort estimate is consistent with the sum of per-phase estimates
3. **Phase balance**: If Phase 1 (quick wins) has more effort than Phase 3 (deep refactoring), flag

**Issue category**: `effort-mismatch`
**Severity**: `warning` (effort estimates are inherently approximate)

### Check 3 — Completeness

1. **Finding coverage**: Cross-reference the orchestrator plan's findings against the scores report:
   - All `critical` findings MUST be addressed in the plan
   - All `high` findings SHOULD be addressed
   - `medium` findings MAY be deferred but SHOULD be acknowledged
2. **Root cause coverage**: If cross-analysis is available, verify that identified root causes are addressed by combined fixes in the plan
3. **Missing dimensions**: If a dimension had findings but no plan steps address it, flag

**Issue category**: `completeness-gap`
**Severity**: `blocking` if critical findings are missed; `warning` if high findings are deferred without justification

### Check 4 — Risk Assessment

1. **Rollback strategy**: Each phase MUST have verification checks. Flag if any phase has no checks.
2. **High-risk steps**: Steps modifying core infrastructure, auth, or data schemas SHOULD be flagged as high-risk with specific mitigations
3. **Test dependency**: Verify that "run tests" appears in verification for every phase

**Issue category**: `risk-gap`
**Severity**: `blocking` if no verification strategy; `warning` if mitigations are thin

### Check 5 — Ordering Quality

1. **Quick wins first**: Verify Phase 1 items are genuinely low-effort and low-risk
2. **Foundation before dependents**: Architecture changes MUST precede quality/testing improvements that depend on them
3. **Security urgency**: All security findings MUST be in Phase 1 regardless of effort

**Issue category**: `ordering-error`
**Severity**: `blocking` if security is not in Phase 1; `warning` if ordering is suboptimal

### Check 6 — Prior Feedback Resolution (iteration > 1)

Same pattern as critique-report Check 5.

## Output

Produce CriticFeedback JSON:
- `verdict`: "pass" if zero blocking issues, "fail" otherwise
- `target`: "plan"
- `iteration`: current iteration number
- `issues`: all issues found

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Cannot read orchestrator plan | Flag as blocking |
| No per-dimension plans available | Flag as blocking |
| Cross-analysis not available | Skip root cause coverage check |
| Iteration >= 3 with persistent issues | Include all accumulated issues for user escalation |
```

- [ ] **Step 2: Commit**

```bash
git add skills/critique-plan/SKILL.md
git commit -m "feat(skills): add critique-plan sub-skill with 6-check evaluation workflow"
```

---

## Chunk 4: Modify Existing Files

### Task 11: Migrate existing agents to directory convention and update plugin.json

**Files:**
- Modify: `plugin.json`
- Move: `agents/code-analyzer.md` → `agents/code-analyzer/AGENT.md`
- Move: `agents/refactoring-planner.md` → `agents/refactoring-planner/AGENT.md`

- [ ] **Step 1: Read current plugin.json**

Run: Read `plugin.json`

- [ ] **Step 2: Migrate existing agents to directory convention**

The project CLAUDE.md requires the `directory + SKILL.md/AGENT.md` convention. Existing agents use flat files. Migrate them first:

```bash
mkdir -p agents/code-analyzer agents/refactoring-planner
mv agents/code-analyzer.md agents/code-analyzer/AGENT.md
mv agents/refactoring-planner.md agents/refactoring-planner/AGENT.md
```

- [ ] **Step 3: Update plugin.json**

Replace the entire content with:

```json
{
  "name": "code-analysis",
  "version": "0.1.0",
  "description": "Comprehensive codebase analysis across any language/framework — produces scored reports with critic validation and focused refactoring plans.",
  "author": {
    "name": "Vooban Developer Team",
    "email": "dev@vooban.com"
  },
  "keywords": [
    "dev",
    "analysis",
    "refactoring",
    "code-quality",
    "architecture",
    "security",
    "performance",
    "tech-debt",
    "scoring"
  ],
  "skills": "./skills",
  "agents": [
    "./agents/code-analyzer",
    "./agents/refactoring-planner",
    "./agents/report-reconciler",
    "./agents/report-critic",
    "./agents/plan-critic"
  ]
}
```

**Note**: All agents now use the directory convention (`agents/X/AGENT.md`) per the project CLAUDE.md convention.

- [ ] **Step 4: Commit**

```bash
git add plugin.json agents/
git commit -m "feat(plugin): migrate agents to directory convention, register 3 new agents, bump to v0.1.0"
```

---

### Task 12: Update refactoring-planner agent to accept critic feedback

**Files:**
- Modify: `agents/refactoring-planner/AGENT.md` (migrated from flat file in Task 11)

- [ ] **Step 1: Read current file**

Run: Read `agents/refactoring-planner/AGENT.md`

- [ ] **Step 2: Add critic feedback handling**

After the `## Input` section (after "Optionally: a date to use (default: latest available)"), add:

```markdown
- Optionally: critic feedback (CriticFeedback JSON from plan-critic agent)
- Optionally: cross-analysis results (CrossAnalysis JSON from report-reconciler --deep)
```

After Step 3 (Generate Per-Dimension Plans), add a new section before Step 4:

```markdown
### Step 3.5: Incorporate Cross-Analysis (if provided)

If cross-analysis results are available:
1. Read root causes and systemic patterns
2. For findings linked to root causes, adjust plan steps to address the root cause rather than individual symptoms
3. Add combined fix steps from the cross-analysis where they replace individual finding fixes
```

After Step 4 (Generate Orchestrator Plan), add:

```markdown
### Step 4.5: Address Critic Feedback (if provided)

If critic feedback is provided from a prior plan-critic evaluation:
1. Read each blocking issue
2. For `dependency-error`: Reorder phases or add explicit ordering
3. For `effort-mismatch`: Adjust effort estimates
4. For `completeness-gap`: Add missing plan steps for uncovered findings
5. For `risk-gap`: Add verification checks or rollback strategies
6. For `ordering-error`: Reorder steps as suggested
7. Re-generate the orchestrator plan with corrections
```

- [ ] **Step 3: Commit**

```bash
git add agents/refactoring-planner/AGENT.md
git commit -m "feat(agents): update refactoring-planner to accept critic feedback and cross-analysis"
```

---

### Task 13: Update refactor-plan skill to pass critic flags

**Files:**
- Modify: `skills/refactor-plan/SKILL.md`

- [ ] **Step 1: Read current file**

Run: Read `skills/refactor-plan/SKILL.md`

- [ ] **Step 2: Add new flags**

In the `### Optional Flags` section, after the `--priority` flag, add:

```markdown
- `--skip-critics` (optional): Skip the plan-critic feedback loop. Default: false.
- `--critic-iterations=N` (optional): Max critic feedback iterations. Default: 3.
```

**Note**: The `--draft-only` flag is orchestrator-only (`analyze-codebase`) and does not apply to `refactor-plan`, since `refactor-plan` always requires existing scan results and produces plans.

In the `## Execution` section, after "Dispatch the `refactoring-planner` agent with `$ARGUMENTS` as input.", add:

```markdown
If `--skip-critics` is NOT set:
1. After the refactoring-planner produces the orchestrator plan, dispatch the `plan-critic` agent
2. If the critic returns `"verdict": "fail"`, re-dispatch the `refactoring-planner` with the critic feedback
3. Repeat up to `--critic-iterations` times (default: 3)
4. If the critic still fails after max iterations, present all accumulated issues to the user
```

- [ ] **Step 3: Commit**

```bash
git add skills/refactor-plan/SKILL.md
git commit -m "feat(skills): add --skip-critics and --critic-iterations flags to refactor-plan"
```

---

## Chunk 5: Orchestrator Rewrite

### Task 14: Rewrite analyze-codebase orchestrator skill

**Files:**
- Modify: `skills/analyze-codebase/SKILL.md` (full rewrite)

- [ ] **Step 1: Read current file**

Run: Read `skills/analyze-codebase/SKILL.md`

- [ ] **Step 2: Replace entire content**

```yaml
---
name: analyze-codebase
description: |
  Use when the user asks to "analyze this codebase", "scan for issues",
  "find refactoring opportunities", "code analysis", "audit this project",
  or wants a comprehensive multi-dimension codebase analysis with refactoring plans.
  Also use when the user asks to "analyze architecture", "check code quality",
  "scan for security issues", "find tech debt", or similar dimension-specific requests.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, mcp__plugin_context7_context7__resolve-library-id, mcp__plugin_context7_context7__query-docs, mcp__claude_ai_Context7__resolve-library-id, mcp__claude_ai_Context7__query-docs
---

# Analyze Codebase — Orchestrator

Comprehensive codebase analysis across 8 dimensions with scoring, critic validation, and refactoring plans. Supports any language/framework.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Pipeline

\`\`\`
Stage 1:  Detect Stack (sequential)
    |
Stage 2:  Scan All Dimensions (ALL 8 in parallel)
    |
Stage 3:  Reconcile (report-reconciler agent — dedup, score, draft report)
    |         -> Auto-persist draft reports to disk
    |
Stage 4:  Critique Report (report-critic agent)
    |         -> Feedback loop: max N iterations, then surface to user
    |
Stage 5:  User Checkpoint (review scored report, approve/skip/re-scan)
    |         -> Finalize reports on disk (overwrite drafts)
    |
Stage 6:  Deep Cross-Analysis + Refactoring Plans (only if user approves at Stage 5)
    |         -> Cross-dimension root cause analysis
    |         -> Per-dimension refactoring plans
    |
Stage 7:  Orchestrator Plan Generation
    |
Stage 8:  Critique Plan (plan-critic agent)
    |         -> Feedback loop: max N iterations, then surface to user
    |
Stage 9:  User Approval Gate (mandatory)
    |
Stage 10: Persist All Final Outputs
\`\`\`

## Input

Target path: $ARGUMENTS (default: current working directory)

### Optional Flags

- `--dimensions=arch,quality,deps,patterns,testing,perf,security,debt` — restrict dimensions (default: all 8)
- `--stack=python|typescript|csharp|dart|rust|go` — override auto-detected language
- `--framework=react|dotnet|flutter|tauri|electron|maui` — override auto-detected framework
- `--weights=dim:N,...` — custom dimension weights for overall score (default: all 1.0). Partial overrides allowed (unspecified dimensions default to 1.0).
- `--critic-iterations=N` — max critic feedback loop iterations (default: 3)
- `--skip-critics` — bypass critic loops entirely (skip Stages 4 and 8)
- `--draft-only` — stop after Stage 3 (scan + reconcile + persist draft, no user interaction)

## Context Efficiency Rules

The orchestrator is a **thin dispatcher**. To minimize context consumption:

1. **MUST NOT read scanner sub-skills** (`scan-*/SKILL.md`) — subagents read them
2. **MUST NOT read reconciliation sub-skill** (`reconcile-report/SKILL.md`) — the reconciler agent reads it
3. **MUST NOT read critic sub-skills** (`critique-report/SKILL.md`, `critique-plan/SKILL.md`) — critic agents read them
4. **MUST NOT read output-schemas.md** — subagents and agents read what they need
5. **MUST NOT read language/framework profiles** — loaded by subagents
6. **MUST NOT read templates** — the reconciler and planner agents use them
7. **MAY read `analysis-dimensions.md`** in Stage 5 for severity definitions when presenting to user

The orchestrator handles: flag parsing, stack detection, agent dispatch, feedback loops, user checkpoints, and final persistence coordination.

## Execution Protocol

### Stage 1 — Detect Stack

Identify languages and frameworks by reading the project root for manifest files:

- `package.json` → TypeScript/JavaScript + React/Electron
- `*.csproj` / `*.sln` → C# + .NET/MAUI
- `Cargo.toml` → Rust + Tauri
- `pubspec.yaml` → Dart + Flutter
- `go.mod` → Go
- `pyproject.toml` / `requirements.txt` / `setup.py` → Python
- `tauri.conf.json` → Tauri

Check for multi-language projects (e.g., Tauri = Rust + TypeScript). Read `CLAUDE.md` if it exists. Apply `--stack` / `--framework` overrides.

**Output**: `STACK = { languages: [], frameworks: [] }`

### Stage 2 — Scan All Dimensions (Full Parallel)

Parse `--dimensions` flag. Default: all 8.

Dimension map: `arch` → architecture, `quality`, `deps` → dependencies, `patterns`, `testing`, `perf` → performance, `security`, `debt` → tech-debt.

**Dispatch ALL `code-analyzer` subagents in parallel** (no batching):

For each dimension, dispatch an Agent with:
\`\`\`
Analyze the codebase at [PROJECT_PATH] for the [DIMENSION] dimension.
Stack: [STACK.languages], Framework: [STACK.frameworks].
Return ONLY a structured JSON findings array. Each finding: { id, dimension, title, severity, location, description, recommendation, effort, tags }.
Include a summary header: { dimension, total, critical, high, medium, low, info }.
\`\`\`

Collect all findings arrays from subagent responses.

**Fallback**: If the platform limits concurrent agents, dispatch in batches of 4. Prefer full parallelism.

**IMPORTANT**: Findings MUST be kept as compact JSON — do NOT expand into verbose descriptions in the main context.

### Stage 3 — Reconcile (report-reconciler agent)

Dispatch the `report-reconciler` agent with:
- All dimension findings arrays
- Stack information
- Project path
- Weights from `--weights` flag (or default)

The agent will:
1. Deduplicate cross-dimension findings
2. Compute per-dimension scores (0-10) and overall weighted score
3. Produce unified draft report
4. Auto-persist draft to `.code-analysis/reports/YYYY-MM-DD-analysis-draft.md`
5. Auto-persist scores to `.code-analysis/reports/YYYY-MM-DD-scores.json`
6. Auto-persist raw scan reports to `.code-analysis/scan-reports/YYYY-MM-DD-{dimension}.json`

**If `--draft-only`**: Stop here. Present the overall score and dimension scores summary to the user. Exit.

### Stage 4 — Critique Report (report-critic agent)

**Skip if `--skip-critics` is set.**

Run the critic feedback loop:

\`\`\`
attempt = 0
max_iterations = --critic-iterations (default: 3)
loop:
  if attempt >= max_iterations:
    present all accumulated issues to user
    ask: proceed anyway or abort?
    break
  dispatch report-critic agent with:
    - draft report path
    - scores.json path
    - scan-reports directory path
    - stack, project path
    - iteration: attempt + 1
    - prior feedback (from previous iteration, null on first)
  if critic returns verdict "pass":
    break
  dispatch report-reconciler agent with:
    - same findings
    - critic feedback
  attempt++
\`\`\`

### Stage 5 — User Checkpoint ← CHECKPOINT

Present to the user:
1. Overall codebase health score
2. Per-dimension score table
3. Dedup statistics
4. Cross-cutting observations (from draft report)
5. Critic status (passed / passed with warnings / user-overridden)

Ask the user:
- **Proceed to refactoring plans?** (continues to Stage 6)
- **Stop here?** (finalize reports, skip Stages 6-10)
- **Re-scan specific dimensions?** (loop back to Stage 2 for those dimensions, then re-reconcile)

**CRITICAL**: MUST pause and wait for user confirmation.

**Finalize reports**: Rename draft to final (`analysis-draft.md` → `analysis.md`). `scores.json` requires no renaming — it is persisted in final form at Stage 3.

### Stage 6 — Deep Cross-Analysis + Refactoring Plans

**Only if user chose to proceed at Stage 5.**

#### Step 6a: Deep Cross-Analysis

Dispatch `report-reconciler` agent with `--deep` flag:
- All dimension findings
- Stack, project path

The agent returns CrossAnalysis JSON (root causes, systemic patterns, combined fixes). This is NOT persisted — used as input to planning.

#### Step 6b: Generate Refactoring Plans

Dispatch the `refactoring-planner` agent with:
- All dimension findings (excluding user-skipped dimensions and info-only dimensions)
- Cross-analysis results from Step 6a
- Stack, project path

The agent loads `generate-refactoring-plan/SKILL.md` internally — the orchestrator MUST NOT read it.

### Stage 7 — Orchestrator Plan Generation

The `refactoring-planner` agent (dispatched in Stage 6b) also generates the orchestrator plan as part of its workflow (Steps 3-4 in its agent definition). It loads `generate-orchestrator-plan/SKILL.md` internally — the orchestrator MUST NOT read it.

The orchestrator collects the master plan from the agent's output.

### Stage 8 — Critique Plan (plan-critic agent)

**Skip if `--skip-critics` is set.**

Run the same critic feedback loop pattern as Stage 4, but with:
- `plan-critic` agent instead of `report-critic`
- `refactoring-planner` agent as the producer (re-dispatched with critic feedback)
- Same max iterations from `--critic-iterations`

### Stage 9 — User Approval Gate ← MANDATORY GATE

Present to user:
- Execution phases with dimension assignments
- Dependency graph (Mermaid)
- Effort summary
- Verification strategy
- Critic status

**CRITICAL**: MUST NOT proceed to Stage 10 until user explicitly approves.

### Stage 10 — Persist All Final Outputs

Dispatch the `refactoring-planner` agent for persistence (Step 5 in its agent definition):
- It reads templates internally (`refactoring-plan.md`, `orchestrator-plan.md`) — the orchestrator MUST NOT read them
- It writes to `.code-analysis/plans/`:
  - `YYYY-MM-DD-{dimension}-plan.md` — per-dimension plans
  - `YYYY-MM-DD-orchestrator-plan.md` — master plan

Reports and scores were already persisted at Stage 3/5 — do NOT overwrite.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No project manifests found | Ask user for `--stack` and `--framework` |
| Context7 MCP unavailable | Skip library validation, note limitation |
| Dimension scan zero findings | Score 10.0, skip plan for that dimension |
| All dimensions clean | Score 10/10, congratulate user, skip Stages 6-10 |
| User skips all at Stage 5 | Finalize reports, end |
| Very large project (>5000 files) | Warn, suggest `--dimensions` to focus |
| Stage 3/5 directory has today's reports | Ask: overwrite or append timestamp suffix |
| Critic loop exhausted | Present all issues to user, ask proceed or abort |
| Platform limits concurrent agents | Fall back to batches of 4 |
| report-reconciler fails | Retry once, then surface error to user |
```

- [ ] **Step 3: Verify the rewrite covers all 10 stages**

Manually check: Stage 1 (detect), Stage 2 (parallel scan), Stage 3 (reconcile), Stage 4 (critique report), Stage 5 (user checkpoint), Stage 6 (deep cross-analysis + plans), Stage 7 (orchestrator plan), Stage 8 (critique plan), Stage 9 (user gate), Stage 10 (persist).

- [ ] **Step 4: Commit**

```bash
git add skills/analyze-codebase/SKILL.md
git commit -m "feat(skills): rewrite analyze-codebase as thin dispatcher with 10-stage pipeline"
```

---

## Chunk 6: Integration Verification

### Task 15: Verify all cross-references

**Files:**
- Read-only verification pass across all modified/created files

- [ ] **Step 1: Verify plugin.json agent paths resolve**

Run: Check that each agent directory contains an AGENT.md file:
```bash
cd /path/to/code-analysis
for agent in agents/code-analyzer/AGENT.md agents/refactoring-planner/AGENT.md agents/report-reconciler/AGENT.md agents/report-critic/AGENT.md agents/plan-critic/AGENT.md; do
  test -f "$agent" && echo "OK: $agent" || echo "MISSING: $agent"
done
```

Expected: All 5 show "OK"

- [ ] **Step 2: Verify skill directories have SKILL.md**

```bash
for skill in reconcile-report critique-report critique-plan; do
  test -f "skills/$skill/SKILL.md" && echo "OK: skills/$skill/SKILL.md" || echo "MISSING: skills/$skill/SKILL.md"
done
```

Expected: All 3 show "OK"

- [ ] **Step 3: Verify schema references**

Check that output-schemas.md contains all required schemas:
```bash
grep -c "## .* Schema" references/output-schemas.md
```

Expected: 7 (Finding, DimensionReport, RefactoringPlan, OrchestratorPlan, ScoresReport, CriticFeedback, CrossAnalysis)

- [ ] **Step 4: Verify template exists**

```bash
test -f "templates/analysis-draft.md" && echo "OK" || echo "MISSING"
```

Expected: "OK"

- [ ] **Step 5: Verify RFC 2119 usage**

Spot-check that all new files use RFC 2119 keywords (MUST, SHOULD, MAY) correctly and include the preamble where applicable.

```bash
grep -l "RFC 2119" skills/reconcile-report/SKILL.md skills/critique-report/SKILL.md skills/critique-plan/SKILL.md skills/analyze-codebase/SKILL.md
```

Expected: All 4 files listed

- [ ] **Step 6: Final commit (if any fixes needed)**

Stage only the specific files that were fixed, then commit:

```bash
git add <specific-files-that-were-fixed>
git commit -m "fix(plugin): resolve cross-reference issues from integration verification"
```

Only run if Steps 1-5 found issues that needed fixing. Stage specific files rather than using `git add -A`.

---

## Execution Summary

| Task | Component | Type | Dependencies |
|------|-----------|------|-------------|
| 1 | ScoresReport schema | New schema | None |
| 2 | CriticFeedback schema | New schema | None |
| 3 | CrossAnalysis schema | New schema | None |
| 4 | analysis-draft.md template | New template | Task 1 (score fields) |
| 5 | report-reconciler agent | New agent | Tasks 1, 3, 4 |
| 6 | report-critic agent | New agent | Task 2 |
| 7 | plan-critic agent | New agent | Task 2 |
| 8 | reconcile-report sub-skill | New skill | Tasks 1, 3 |
| 9 | critique-report sub-skill | New skill | Task 2 |
| 10 | critique-plan sub-skill | New skill | Task 2 |
| 11 | plugin.json update | Modify | Tasks 5, 6, 7 |
| 12 | refactoring-planner update | Modify | Tasks 2, 3 (schema formats) |
| 13 | refactor-plan skill update | Modify | Task 7 |
| 14 | analyze-codebase rewrite | Modify | All above |
| 15 | Integration verification | Verify | All above |
