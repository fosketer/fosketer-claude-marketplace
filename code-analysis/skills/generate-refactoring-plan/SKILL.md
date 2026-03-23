---
name: generate-refactoring-plan
version: 0.7.0
description: |
  This skill should be used when generating a focused refactoring plan for a single dimension's findings
  as part of the analyze-codebase pipeline. Dispatched internally by the orchestrator — not for direct user invocation.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
  Use when the user asks to "generate refactoring plan", "create dimension-specific fix plan", or "produce actionable refactoring steps".
allowed-tools: ["Read", "Glob", "Grep"]
---

# Generate Refactoring Plan

## Purpose

Read one dimension's findings and produce a focused, actionable refactoring plan with prioritized steps, risk assessment, and verification criteria.


## Input

- `DIMENSION`: The dimension name (e.g., `"structure"`, `"quality"`)
- `FINDINGS`: Array of Finding objects from the corresponding scan skill (see the Finding schema in `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`)
- `STACK`: Detected language/framework object with `languages` and `frameworks` arrays
- `PROJECT_PATH`: Root directory of the project

Optional inputs:
- `CROSS_ANALYSIS`: CrossAnalysis JSON — when provided, root causes and combined fixes SHOULD override symptom-level steps
- `CRITIC_FEEDBACK`: CriticFeedback JSON from a prior `plan-critic` run — when provided, resolve all blocking issues before producing the plan

## Workflow

### Step 1 — Filter and Group Findings

1. Remove all findings with `severity == "info"` — they do not generate plan steps. Keep a count of removed findings to include in the plan summary.

2. If `CRITIC_FEEDBACK` is provided, check whether any blocking issues have category `completeness-gap`. If yes, restore any findings that were previously excluded if they are referenced in the critic issue's `context` field.

3. Group remaining findings by two axes:

   **File proximity**: Findings referencing the same file or the same module (same directory within `src/`) are co-located. Example: two quality findings in `src/api/handlers.ts` form one group.

   **Thematic similarity**: Findings sharing at least two tags (e.g., `["circular-dep", "coupling"]`) belong to the same group even if in different files.

4. A finding MAY appear in more than one candidate group. When building steps in Step 3, deduplicate by assigning each finding to the group where it has the most tag overlap; break ties by file proximity.

5. Each resulting group becomes one candidate refactoring step.

**Example**:

Input findings (security dimension):
```json
[
  { "id": "SEC-8f3a21-a1b2", "file_path": "src/auth/login.ts",
    "severity": "critical", "title": "SQL injection via raw query",
    "tags": ["owasp-a03", "injection"], "effort": "medium" },
  { "id": "SEC-8f3a21-b3c4", "file_path": "src/auth/register.ts",
    "severity": "high", "title": "No input sanitization on email field",
    "tags": ["owasp-a03", "injection"], "effort": "small" },
  { "id": "SEC-000000-d5e6", "file_path": null,
    "severity": "medium", "title": "Dependency lodash 4.17.11 has known CVE",
    "tags": ["cve", "dependency"], "effort": "trivial" }
]
```

After grouping:
- Group A: `SEC-8f3a21-a1b2` + `SEC-8f3a21-b3c4` (thematic — both `owasp-a03 + injection`)
- Group B: `SEC-000000-d5e6` (standalone — no overlap with others)

### Step 2 — Build Priority Matrix

For each finding (post-filter), compute:

| Factor | Scale | Derivation |
|--------|-------|------------|
| **Priority** | P1–P4 | P1 = `critical`, P2 = `high`, P3 = `medium`, P4 = `low` severity |
| **Effort** | trivial/small/medium/large/xl | Carry the `effort` field from the Finding |
| **Impact** | critical/high/medium/low | Match the severity level — same mapping as Priority |
| **Risk** | high/medium/low | Assess using the rules below |

Risk assignment rules:
- Changes to authentication, authorization, or session handling → `high`
- Changes to database schema, data migration, or ORM models → `high`
- Changes that affect public APIs or external contracts → `medium`
- Refactoring within a single module with test coverage → `low`
- Dependency version bumps with no API changes → `low`

If the risk cannot be determined from available context, default to `medium` and add the note "risk defaulted — verify before executing" to the step description.

Sort the matrix by: `Priority ASC`, then `Impact DESC`, then `Effort ASC`.

**Example priority matrix entry**:
```json
{
  "finding_id": "SEC-8f3a21-a1b2",
  "priority": 1,
  "effort": "medium",
  "impact": "critical",
  "risk": "high"
}
```

### Step 3 — Generate Steps

For each group produced in Step 1, produce one refactoring step with these fields:

1. **`order`**: Integer starting at 1. Determined by the ordering rules below — do not assign sequentially; sort first, then assign integers.

2. **`title`**: Imperative phrase under 100 characters. Describe the transformation, not the problem. Good: `"Parameterize raw SQL queries in auth/login.ts"`. Bad: `"Fix SQL injection"`.

3. **`description`**: Explain what to change, how to change it, and why. Reference findings by ID using the notation `[SEC-8f3a21-a1b2]`. Include code-level guidance where the change is non-trivial.

   Example description for the SQL injection group:
   > Replace the raw `db.query()` call in `src/auth/login.ts` (line 42) with a parameterized prepared statement [SEC-8f3a21-a1b2]. Apply the same fix to the email lookup in `src/auth/register.ts` (line 17) [SEC-8f3a21-b3c4]. Use the project's existing `db.prepare()` helper — see `src/db/client.ts` for the pattern.

4. **`files_affected`**: Array of relative paths from project root. Include all files that MUST be touched, including test files that need updating.

5. **`verification`**: A specific, runnable check. Prefer commands over prose. Examples:
   - `"Run: npm run test:security — all auth tests must pass"`
   - `"Run: sqlmap -u http://localhost:3000/login --forms — no injection found"`
   - `"Run: tsc --noEmit — zero type errors"`

   If no automated check exists, specify the manual review: `"Code review: confirm no raw string interpolation in db.query() calls in src/auth/"`.

6. **`estimated_effort`**: Take the maximum effort from the priority matrix entries in this group's findings. Rationale: a group containing one `medium` and one `small` finding takes at least `medium` effort.

**Ordering rules for steps**:
- Foundation changes precede dependent changes (e.g., extract an interface before refactoring all its consumers)
- Within the same priority level, low-risk steps precede high-risk steps
- Steps affecting the same file MUST be adjacent (minimize context-switching)
- If `CROSS_ANALYSIS` is provided and a combined fix addresses multiple findings from this dimension, generate a single combined step and note the root cause ID it addresses

### Step 4 — Risk Assessment

Compile an overall risk assessment for the entire plan:

1. **`overall_risk`**:
   - `high` if any step has risk `high`
   - `medium` if any step has risk `medium` and none are `high`
   - `low` if all steps are risk `low`

2. **`mitigation`**: Array of specific mitigation actions. Each item MUST name a concrete action, not a principle. Examples of acceptable mitigations:
   - `"Run npm test after step 1 — covers 85% of auth module"`
   - `"Create a git branch before starting step 3 — database schema changes"`
   - `"Deploy to staging and smoke-test login flow before merging step 2"`
   - `"Steps 2 and 4 modify UserRepository — human review required before merging"`

3. Flag any steps touching authentication, payments, or data persistence as requiring human review before execution. Add `"[HUMAN REVIEW REQUIRED]"` at the start of those steps' titles in the mitigation list.

### Step 5 — Handle Cross-Analysis Input

If `CROSS_ANALYSIS` is provided:

1. For each root cause in `cross_analysis.root_causes` that lists findings from this dimension in `related_finding_ids`:
   - Replace individual finding steps with a single combined step that addresses the root cause
   - Set the combined step's description to reference the root cause ID and explain the systemic fix
   - Set `estimated_effort` to the maximum of all replaced steps' efforts

2. For each combined fix in `cross_analysis.combined_fixes` that addresses a root cause from step 1:
   - Use the `combined_fixes[].description` as the basis for the step description
   - Reference the finding IDs being superseded

3. Ensure no finding is left without coverage. If a finding from this dimension is not covered by any combined fix, it MUST still generate its own step.

### Step 6 — Produce Plan

Compile the plan as a `RefactoringPlan` object matching the schema in `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "metadata": {
    "date": "<today ISO date>",
    "dimension": "<DIMENSION>",
    "project_path": "<PROJECT_PATH>"
  },
  "summary": "<2-4 sentence human summary>",
  "priority_matrix": [ ... ],
  "steps": [ ... ],
  "risk_assessment": {
    "overall_risk": "<high|medium|low>",
    "mitigation": [ ... ]
  }
}
```

The `summary` field MUST mention: the number of actionable findings, the highest severity found, and the estimated total effort for the dimension.

Example summary:
> 3 actionable security findings (1 critical, 1 high, 1 medium). The critical SQL injection in auth/login.ts must be addressed immediately and requires medium effort. Remaining fixes are low-to-medium effort. Overall plan estimated at 1 developer day.

Return the plan object to the calling orchestrator. Do not write the file yourself — the `refactoring-planner` agent handles persistence.

## Error Handling

| Scenario | Resolution |
|----------|------------|
| Zero findings after filtering info | Return a plan object with empty `steps` and `priority_matrix`; set `summary` to `"No actionable findings — dimension is clean."` |
| All findings are `info` severity | Same as zero findings after filtering |
| Cannot determine effort for a finding | Default to `medium` and append `"(effort defaulted)"` to the step description |
| Findings reference deleted or moved files | Verify with Glob. If the file is absent, flag the finding as stale in the step description: `"[STALE: file not found — verify path before executing]"`. Include the step but mark it for human review. |
| >50 findings in one dimension | Group aggressively: merge all findings in the same module into single steps. Enforce a maximum of 20 steps. Add a note to the plan summary: `"High finding volume — steps are aggregated by module. Review individual findings in the scan report for full detail."` |
| CRITIC_FEEDBACK references findings not in FINDINGS | Log a warning in the plan summary; do not fail. The scan report may have been regenerated. |
| Cross-analysis combined fix covers findings from multiple dimensions | Only include the portion of that fix that addresses findings from the current DIMENSION. The orchestrator plan will handle the cross-dimension coordination. |

## Success Checklist

- [ ] All non-info findings addressed in at least one step
- [ ] Priority matrix complete for every finding
- [ ] Steps ordered by dependency, then priority, then risk
- [ ] Steps affecting the same file are adjacent
- [ ] Each step has a specific, runnable verification criterion
- [ ] Risk assessment includes concrete, named mitigation actions
- [ ] High-risk steps are flagged for human review
- [ ] Plan matches the RefactoringPlan schema
- [ ] Plan returned to orchestrator (not written to disk)
