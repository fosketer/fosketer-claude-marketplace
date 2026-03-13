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
