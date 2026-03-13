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
