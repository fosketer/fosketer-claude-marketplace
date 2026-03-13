---
name: generate-refactoring-plan
description: |
  Generate a focused refactoring plan for a single dimension's findings.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
---

# Generate Refactoring Plan

## Purpose

Read one dimension's findings and produce a focused, actionable refactoring plan with prioritized steps, risk assessment, and verification criteria.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `DIMENSION`: The dimension name (e.g., "architecture", "quality")
- `FINDINGS`: Array of findings from the corresponding scan skill
- `STACK`: Detected language/framework
- `PROJECT_PATH`: Root directory of the project

## Workflow

### Step 1 — Filter and Group Findings

1. Remove `info`-severity findings — they do not generate plan steps
2. Group remaining findings by:
   - **File proximity** — findings in the same file or module
   - **Thematic similarity** — findings with shared tags
3. Each group becomes a candidate refactoring step

### Step 2 — Build Priority Matrix

For each finding, assess:

| Factor | Scale | Criteria |
|--------|-------|----------|
| **Priority** | P1–P4 | P1 = critical severity, P2 = high, P3 = medium, P4 = low |
| **Effort** | XS/S/M/L/XL | XS = 1 line, S = <1h, M = <4h, L = <1d, XL = >1d |
| **Impact** | high/medium/low | How much improvement fixing this delivers |
| **Risk** | high/medium/low | Likelihood of introducing regressions |

Sort the matrix by: Priority ASC, then Impact DESC, then Effort ASC.

### Step 3 — Generate Steps

For each group (from Step 1), produce a refactoring step:

1. **Title**: Short imperative description (e.g., "Extract shared interface from circular dependency")
2. **Description**: What to change and why — reference specific findings by ID
3. **Files affected**: List all files that MUST be modified
4. **Verification**: How to confirm the step was successful (specific command, test, or check)
5. **Estimated effort**: From the priority matrix

Steps MUST be ordered so that:
- Foundation changes come before dependent changes
- Low-risk changes come before high-risk ones within the same priority
- Steps within the same file are adjacent to minimize context-switching

### Step 4 — Risk Assessment

1. Assess **overall risk** for the plan: high/medium/low
2. Identify specific mitigations:
   - Which tests to run after each step
   - Which modules could be affected by regressions
   - Rollback strategy if a step fails
3. Flag any steps that SHOULD be reviewed by a human before execution

### Step 5 — Produce Plan

Compile the plan matching the refactoring plan schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`.

Return the plan object to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Zero findings after filtering | Return empty plan with note — dimension is clean |
| All findings are `info` severity | Return empty plan — no action needed |
| Cannot determine effort for a finding | Default to `M` (medium) with note |
| Findings reference deleted/moved files | Flag as stale, exclude from plan steps |
| >50 findings in one dimension | Group aggressively, limit to 20 steps max |

## Success Checklist

- [ ] All non-info findings addressed in at least one step
- [ ] Priority matrix complete for every finding
- [ ] Steps ordered by dependency, then priority
- [ ] Each step has verification criteria
- [ ] Risk assessment includes specific mitigations
- [ ] Plan matches the refactoring plan schema
- [ ] Plan returned to orchestrator
