---
name: critique-plan
version: 0.8.0
description: |
  This skill should be used when the user asks to "validate the refactoring plan", "critique the orchestrator plan",
  "check plan feasibility", or when evaluating the quality and feasibility of an orchestrator refactoring plan.
  Loaded by the plan-critic agent.
allowed-tools: ["Read", "Grep", "Glob"]
---

# Critique Plan

## Purpose

Evaluate an orchestrator refactoring plan for dependency correctness, effort realism, completeness, risk assessment, and ordering. Return structured feedback.


## Input

- `ORCHESTRATOR_PLAN`: The master plan (`OrchestratorPlan` JSON or rendered markdown)
- `DIMENSION_PLANS`: All per-dimension `RefactoringPlan` objects
- `SCORES_REPORT`: The reconciled `ScoresReport` JSON
- `CROSS_ANALYSIS`: `CrossAnalysis` JSON (null if not available)
- `STACK`: Detected language/framework
- `PROJECT_PATH`: Root directory of the project
- `ITERATION`: Current iteration number (1-based)
- `PRIOR_FEEDBACK`: Previous `CriticFeedback` (null on first iteration)

## Evaluation Workflow

Work through all six checks sequentially. Collect all issues before producing output — do not short-circuit on the first blocking issue.

### Check 1 — Dependency Correctness

**Phase ordering verification**:

Verify that the orchestrator plan's phases follow the expected structure:
- Phase 1 MUST contain `security` if a non-empty security plan exists
- Phase 2 SHOULD contain `structure`
- Phase 3 SHOULD contain `quality` and `testing`

For each deviation from these rules, create an issue with category `dependency-error`.

**File conflict detection**:

For each pair of dimension plans assigned to the same phase:
1. Build the file set for each plan (union of `files_affected` across all steps)
2. Compute the intersection
3. If non-empty: verify that the orchestrator plan defines explicit ordering for these plans within the phase (check `execution_phases[].plans` — earlier index = executes first)
4. If no explicit ordering exists, raise a `dependency-error` warning

**Cross-phase dependency verification**:

For each directed edge in the dependency graph (parse the Mermaid `mermaid_code`):
- Verify that the source node's phase number is strictly less than the target node's phase number
- If A → B but A and B are in the same phase: raise `dependency-error` blocking
- If A → B but A is in a later phase than B: raise `dependency-error` blocking

**Example blocking issue**:
```json
{
  "category": "dependency-error",
  "severity": "blocking",
  "description": "quality plan is in Phase 1, but structure plan (which quality depends on) is in Phase 2. Executing quality refactoring before structure creates a foundation conflict.",
  "suggestion": "Move quality to Phase 3 or move structure to Phase 1.",
  "context": "structure → quality edge in dependency_graph"
}
```

**Issue category**: `dependency-error`
**Severity**: `blocking` if executing the plan as-is would cause conflicts; `warning` if ordering is ambiguous

### Check 2 — Effort Realism

**Per-step effort spot-check**:

Select up to 5 plan steps from the dimension plans (prefer steps with the most files_affected). For each:

1. Count the files in `files_affected`
2. Assess the step description for complexity indicators (new abstractions, API changes, data migrations, etc.)
3. Apply the realism rules:
   - 1 file, cosmetic change (rename, reformat) → MUST be `trivial` or `small`; `large` or `xl` is unrealistic
   - 5+ files, introduces new pattern or abstraction → MUST NOT be `trivial` or `small`
   - Steps involving database schema or public API changes → MUST be at least `medium`

**Total effort consistency**:

Sum the effort estimates from all dimension plans using this mapping:
- trivial = 0.25h, small = 0.75h, medium = 2.5h, large = 6h, xl = 12h

Compare the computed total with `total_effort_estimate` in the orchestrator plan. If the stated estimate is more than 50% lower than the computed sum, raise an `effort-mismatch` warning.

**Phase balance check**:

If Phase 1 (quick wins) has a higher total effort than Phase 3 (deep refactoring), flag as an `effort-mismatch` warning — Phase 1 is supposed to be lightweight. Exception: if the security dimension alone accounts for Phase 1's effort, the imbalance is acceptable.

**Issue category**: `effort-mismatch`
**Severity**: `warning` (effort estimates are inherently approximate; never raise blocking for effort alone)

### Check 3 — Completeness

**Finding coverage**:

Read `SCORES_REPORT.dimension_scores` and extract each dimension's `by_severity` counts. For each dimension with a non-empty plan:

1. Count the number of unique finding IDs referenced across all steps in that dimension's plan
2. Compare against the dimension's `findings_count` in `SCORES_REPORT` (subtract `info`-severity count)
3. Apply these rules:
   - All `critical` findings MUST appear in at least one plan step — raise `completeness-gap` blocking if any are absent
   - All `high` findings SHOULD appear — raise `completeness-gap` warning if >20% are absent
   - `medium` findings MAY be deferred — raise `completeness-gap` warning only if all medium findings in a dimension are absent

To find which findings are uncovered, look for finding IDs from the scan reports that do not appear in any step's description. Use the `[FINDING-ID]` notation in step descriptions as the reference mechanism.

**Root cause coverage** (skip if `CROSS_ANALYSIS` is null):

For each root cause in `CROSS_ANALYSIS.root_causes`, check whether the orchestrator plan contains a step that addresses the root cause (look for the root cause ID referenced in any step description). If a root cause with `critical` or `high` severity findings is not addressed, raise a `completeness-gap` blocking issue.

**Missing dimension check**:

If a dimension appears in `DIMENSIONS_ANALYZED` but has no plan steps and its `findings_count` in `SCORES_REPORT` is > 0, raise a `completeness-gap` warning. This indicates the plan generator may have silently skipped the dimension.

**Example blocking issue**:
```json
{
  "category": "completeness-gap",
  "severity": "blocking",
  "description": "Finding SEC-8f3a21-a1b2 (critical: SQL injection in auth/login.ts) is not referenced in any plan step.",
  "suggestion": "Add a step in the security plan that addresses SEC-8f3a21-a1b2 with a specific parameterized query fix.",
  "context": "SEC-8f3a21-a1b2"
}
```

**Issue category**: `completeness-gap`
**Severity**: `blocking` if critical findings are missed; `warning` otherwise

### Check 4 — Risk Assessment

**Phase verification coverage**:

Read `ORCHESTRATOR_PLAN.verification_strategy`. For each phase that contains at least one dimension plan:
- Verify that a `VerificationEntry` exists for that phase
- Verify that `checks` has at least 2 items
- Verify that at least one check mentions running tests (look for keywords: `test`, `spec`, `pytest`, `jest`, `rspec`, etc.)

If any phase has no verification entry, raise a `risk-gap` blocking issue.

**High-risk step mitigations**:

Scan dimension plans for steps whose `title` or `description` contains keywords: `auth`, `authentication`, `session`, `schema`, `migration`, `database`, `api`, `contract`, `public`. For each such step:
- Verify that the dimension plan's `risk_assessment.mitigation` array contains at least one item referencing that step (by step order number or keyword match)
- If not, raise a `risk-gap` warning

**Test dependency check**:

For every phase in `verification_strategy.checks`, verify that at least one check includes a runnable test command. Generic phrases like "ensure tests pass" without a command SHOULD be flagged as a warning (not blocking): `"Verification check for Phase N says 'ensure tests pass' — recommend specifying the exact test command"`.

**Issue category**: `risk-gap`
**Severity**: `blocking` if any phase has no verification; `warning` if mitigations are present but thin

### Check 5 — Ordering Quality

**Quick wins validation**:

For each plan in Phase 1, verify:
- The plan's `risk_assessment.overall_risk` is `low` or `medium` (high-risk plans in Phase 1 are suspicious unless they are security)
- The majority of steps have effort `trivial` or `small`

Exception: the `security` plan MAY have high risk in Phase 1 — this is expected.

**Foundation before dependents**:

For each edge `A → B` in the dependency graph where A is a structure plan:
- Verify A is in an earlier phase than B
- If A and B are in the same phase, verify A has a lower index in `execution_phases[].plans`

**Security urgency**:

If `security` appears in `DIMENSIONS_ANALYZED` and a non-empty `security` plan exists, verify it is assigned to Phase 1. This check MUST be performed regardless of `PRIORITY_OVERRIDE`. Failure is always blocking.

**Example blocking issue**:
```json
{
  "category": "ordering-error",
  "severity": "blocking",
  "description": "The security plan is assigned to Phase 2. Security findings must always be in Phase 1.",
  "suggestion": "Move the security plan to Phase 1. Shift structure to Phase 2 if needed.",
  "context": "security plan in execution_phases[1]"
}
```

**Issue category**: `ordering-error`
**Severity**: `blocking` if security is not in Phase 1; `warning` if other ordering is suboptimal

### Check 6 — Prior Feedback Resolution (iteration > 1)

Skip this check if `ITERATION == 1` or `PRIOR_FEEDBACK` is null.

For each issue in `PRIOR_FEEDBACK.issues` where `severity == "blocking"`:
1. Determine whether the issue has been resolved in the updated plan:
   - `dependency-error`: verify the phase assignment or ordering was corrected
   - `completeness-gap`: verify the missing finding now appears in a step
   - `risk-gap`: verify the missing verification entry was added
   - `ordering-error`: verify the phase assignment was corrected
2. If the issue persists, re-raise it with the same category and severity, and prepend to the description: `"[UNRESOLVED from iteration {N}] "`
3. If the issue was partially addressed (e.g., added a verification entry but it has only 1 check instead of 2), re-raise as a `warning` instead of `blocking` with context noting the partial resolution.

Accumulate all unresolved issues alongside any new issues found in the current pass.

## Output

Produce a `CriticFeedback` JSON object matching the schema in `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "verdict": "pass",
  "target": "plan",
  "iteration": 1,
  "issues": []
}
```

Rules:
- `verdict == "pass"` if and only if `issues` contains zero items with `severity == "blocking"`
- `verdict == "fail"` if any blocking issue exists
- Warning-severity issues do not affect verdict but MUST still be included in `issues`
- `iteration` MUST match the input `ITERATION` value
- `target` MUST be `"plan"`

**Example pass with warnings**:
```json
{
  "verdict": "pass",
  "target": "plan",
  "iteration": 2,
  "issues": [
    {
      "category": "effort-mismatch",
      "severity": "warning",
      "description": "Step 3 of the quality plan modifies 1 file but is estimated as 'large'. This seems high.",
      "suggestion": "Consider reducing to 'medium' unless there are significant hidden dependencies.",
      "context": "quality plan, step 3"
    }
  ]
}
```

## Error Handling

| Scenario | Resolution |
|----------|------------|
| Cannot parse `ORCHESTRATOR_PLAN` as JSON or markdown | Raise a blocking `dependency-error`: `"Orchestrator plan is unreadable — cannot validate."` Set `verdict: "fail"`. |
| `DIMENSION_PLANS` is empty or null | Raise a blocking `completeness-gap`: `"No per-dimension plans provided — cannot check coverage."` |
| `SCORES_REPORT` is null | Skip Check 3 completeness coverage; note in issues array as a warning: `"scores.json unavailable — completeness check skipped."` |
| `CROSS_ANALYSIS` is null | Skip root cause coverage check in Check 3. Not an error. |
| Mermaid code in dependency graph is malformed | Skip cross-phase edge verification in Check 1; raise `dependency-error` warning: `"Dependency graph Mermaid code is invalid — manual verification of phase ordering recommended."` |
| `ITERATION >= 3` and blocking issues persist | Include all accumulated issues in the output. Add a top-level note in the first issue's `description`: `"[MAX ITERATIONS REACHED] These issues require human intervention."` |
| A dimension in DIMENSION_PLANS is not in ORCHESTRATOR_PLAN | Raise `completeness-gap` warning: `"Dimension '{name}' has a refactoring plan but is not referenced in any execution phase."` |
