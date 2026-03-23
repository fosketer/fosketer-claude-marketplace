---
name: critique-report
version: 0.7.0
description: |
  This skill should be used when evaluating the quality of a reconciled analysis report.
  Loaded by the report-critic agent.
allowed-tools: ["Read", "Grep", "Glob"]
---

# Critique Report

## Purpose

Evaluate a reconciled analysis report for quality, scoring accuracy, coverage, and actionability. Return structured feedback.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `DRAFT_REPORT_PATH`: Path to the draft report markdown
- `SCORES_PATH`: Path to the `scores.json` file
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/`
- `STACK`: Detected language/framework
- `PROJECT_PATH`: Root directory of the project
- `ITERATION`: Current iteration number (1-based)
- `PRIOR_FEEDBACK`: Previous `CriticFeedback` (null on first iteration)

## Evaluation Workflow

Work through all five checks sequentially. Collect all issues before producing output — do not short-circuit on the first blocking issue. All checks MUST be executed unless explicitly stated to skip.

### Check 1 — Score Calibration

Read `scores.json` at `SCORES_PATH`. If the file cannot be read, raise a blocking `score-calibration` issue and skip this check's remaining steps.

**Formula verification**:

For each entry in `dimension_scores`, read the corresponding raw scan report from `SCAN_REPORTS_DIR/{dimension}-report.json` and count findings by severity. Then verify:

```
expected_score = max(1.0, 10 - min(critical*3 + high*2 + medium*1 + low*0.5, 9))
```

Compare `expected_score` with `dimension_scores[].score`. Tolerance: ±0.1 (rounding). If a dimension's score deviates by more than 0.1, raise a blocking `score-calibration` issue.

**Example**:
```
structure dimension raw findings: 2 critical, 3 high, 1 medium, 0 low
Penalty = 2*3 + 3*2 + 1*1 + 0*0.5 = 6 + 6 + 1 = 13 → min(13, 9) = 9
Expected score = max(1.0, 10 - 9) = max(1.0, 1) = 1.0

scores.json says structure score = 2.5 → deviation = 1.5 → BLOCKING
```

**Cross-dimension consistency** (skip if `dimensions_analyzed` has < 2 entries):

Flag if either of these is true:
- A dimension with more `critical` findings than another dimension scores *higher* than that dimension (same penalty formula applies — more criticals should mean lower score)
- Two dimensions have the same `by_severity` profile but their scores differ by > 2.0

**Weight application**:

If `scores.json.metadata.weights` is present and non-empty, verify that `overall_score` equals the weighted average of `dimension_scores[].score` using those weights. Tolerance: ±0.1.

If no weights field is present, verify that `overall_score` equals the simple mean of `dimension_scores[].score`. Tolerance: ±0.1.

**Iteration estimates validation**:

For each dimension in `dimension_scores`, validate the `iteration_estimates` sub-object:

1. `true_raw` MUST equal `3 × critical + 2 × high + 1 × medium + 0.5 × low` from the raw scan report. Tolerance: ±0.1.

2. `estimated_iterations` MUST equal 0 when the dimension's `score` is already at or above the target score for that `IterationTarget`. Example: if dimension score is 8.5, then `full_quality.estimated_iterations` (target 8) MUST be 0.

3. For every `IterationTarget` (`quick_win`, `full_quality`, `perfect`):
   - `range[0] <= range[1]` — lower bound must not exceed upper bound
   - `range[0] >= 0` — no negative iteration counts

4. `by_effort` counts MUST sum to `findings_count` minus the count of `info`-severity findings. Info findings are excluded from scoring and effort tracking.

**Issue category**: `score-calibration`
**Severity**: `blocking` if formula is wrong or `true_raw` deviates; `warning` for consistency concerns or iteration estimate anomalies

### Check 2 — Coverage Gaps

Read the scan reports from `SCAN_REPORTS_DIR`. Only evaluate dimensions listed in `scores.json.metadata.dimensions_analyzed` — do not flag missing dimensions that were intentionally excluded from the scan.

**Stack-based expectations**:

Based on `STACK.frameworks` and `STACK.languages`, check for expected findings:

| Stack indicator | Expected findings |
|-----------------|-------------------|
| `react`, `vue`, `angular`, `next` | `security` should have XSS-related findings; flag if 0 security findings for client-side web apps |
| Any web framework (`express`, `django`, `rails`, `fastapi`) | `security` should have auth/injection findings; flag if 0 |
| ORM usage detected (`sequelize`, `prisma`, `sqlalchemy`) | `security` should have SQL safety findings; flag if 0 |
| Data-heavy project (many CSV/Parquet/SQL files in codebase) | `performance` should have data-handling findings; flag if 0 |
| `jest`, `pytest`, `rspec`, `go test` present | `testing` dimension should have been analyzed; if it was and has 0 findings, consider flagging |

For each flagged case, raise a `coverage-gap` warning. This check is advisory — the critic cannot re-scan, so the verdict is always `warning`, never `blocking`.

**Dimension balance** (skip entirely if < 2 dimensions were analyzed):

Among analyzed dimensions only, flag if one dimension has 20+ findings while a semantically related analyzed dimension has 0. Related pairs:
- `structure` ↔ `quality` (high structure issues with zero quality issues is suspicious)
- `quality` ↔ `testing` (many quality issues with zero testing issues suggests test scan may have been shallow)
- `security` ↔ `testing` (security CVE findings with zero testing/dependency-hygiene findings is worth flagging)

**Issue category**: `coverage-gap`
**Severity**: always `warning`

### Check 3 — Dedup Quality

Read the raw scan reports from `SCAN_REPORTS_DIR` and compare against `scores.json.dedup_stats`.

**Over-merging check**:

```
merge_rate = merged_count / total_raw_findings
```

If `merge_rate > 0.40` (40%), raise a `dedup-error` warning: the reconciler may have merged distinct findings that happen to share a file. To confirm: spot-check 3 merged findings from the same file across different dimensions — if they describe clearly different problems (e.g., one is a null-check issue, one is an auth bypass), the merge was incorrect.

**Under-merging check** (skip if < 2 dimensions were analyzed):

Retrieve up to 5 pairs of findings that share the same `file_path` across two different dimensions. For each pair:
- Read both finding descriptions
- If both describe the same root problem (same line range AND same issue type), and they were NOT merged, raise a `dedup-error` warning

Heuristic: findings are likely the same issue if their `file_path` is identical, their `line_start` values differ by ≤ 3 lines, and their descriptions contain the same keyword (e.g., both mention `"null dereference"` or `"missing authentication"`).

**Severity preservation**:

If a merged finding exists (indicated by a finding with `previous_id` set, or by examining dedup notes in the report), verify that the merged result carries the highest severity of the contributing findings. For example, if a `critical` security finding and a `high` quality finding were merged, the result MUST be `critical`. If any merged finding has a lower severity than any of its sources, raise a `dedup-error` blocking issue.

**Issue category**: `dedup-error`
**Severity**: `blocking` if severity was downgraded during merge; `warning` for over/under-merging suspicion

### Check 4 — Actionability

Read the draft report at `DRAFT_REPORT_PATH`. If the file cannot be read, raise a blocking `actionability` issue.

**Recommendations specificity** (sample 5 findings):

Select 5 findings from the report, preferring `critical` and `high` severity. For each finding's recommendation text, check for vague language:
- Vague (blocking): `"improve this"`, `"consider refactoring"`, `"review this area"`, `"address this issue"`, `"fix as needed"`
- Acceptable: references a specific file, function name, pattern name, library API, or command

If a recommendation does not reference at least one specific file path, function name, or action, raise an `actionability` blocking issue.

**Example**:

Vague: `"Consider improving the authentication handling in the app."`
Specific: `"Replace the custom JWT decode in src/auth/middleware.ts line 34 with the project's existing verifyToken() helper to ensure signature validation."`

**Cross-cutting observations**:

The draft report MUST contain a cross-cutting observations section. Verify:
- Section exists (look for a heading containing `"cross"` or `"observations"` or `"systemic"`, case-insensitive)
- Contains 3–5 bullet points
- Each bullet point references at least one specific dimension name, file path, or finding ID

If the section is absent, raise a blocking `actionability` issue.
If the section has fewer than 3 bullets, raise a warning.
If bullets are generic (no specific references), raise a blocking issue.

**Top findings ordering**:

For each dimension section in the draft report, verify that findings are presented in severity order: `critical` first, then `high`, `medium`, `low`, `info`. If a `medium` finding appears before a `high` finding in the same section, raise an `actionability` warning.

**Issue category**: `actionability`
**Severity**: `blocking` if recommendations are vague or cross-cutting section is absent/generic; `warning` if ordering is off or observations are thin

### Check 5 — Prior Feedback Resolution (iteration > 1)

Skip this check if `ITERATION == 1` or `PRIOR_FEEDBACK` is null.

For each issue in `PRIOR_FEEDBACK.issues` where `severity == "blocking"`:

1. Determine whether the issue has been resolved:
   - `score-calibration` blocking: re-run the formula check for the affected dimension — if score now matches, resolved
   - `dedup-error` blocking: check if the severity of the flagged finding now matches the highest-severity source
   - `actionability` blocking: re-check the specific finding's recommendation for specific file/function references
   - Other blocking categories: apply judgment based on the issue's `suggestion` field

2. If the issue persists unchanged, re-raise it with the same category and `severity: "blocking"`, prepending `"[UNRESOLVED from iteration {N}]"` to the `description`.

3. If the issue was partially addressed (the specific problem was fixed but a related problem introduced), re-raise as a `warning` with context explaining the partial resolution.

4. If the issue is resolved, do not include it in the output.

After processing prior feedback, continue with any new issues found during the current evaluation pass. Combine all issues — resolved issues are omitted, unresolved issues carry forward, new issues are appended.

**Issue category**: same as original issue
**Severity**: `blocking` if still unresolved

## Output

Produce a `CriticFeedback` JSON object matching the schema in `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "verdict": "pass",
  "target": "report",
  "iteration": 1,
  "issues": []
}
```

Rules:
- `verdict == "pass"` if and only if `issues` contains zero items with `severity == "blocking"`
- `verdict == "fail"` if any blocking issue exists
- Warning-severity issues do not affect verdict but MUST be included in `issues`
- `iteration` MUST match the input `ITERATION` value
- `target` MUST be `"report"`

**Example fail output**:
```json
{
  "verdict": "fail",
  "target": "report",
  "iteration": 1,
  "issues": [
    {
      "category": "score-calibration",
      "severity": "blocking",
      "description": "Architecture score in scores.json is 2.5, but formula yields 1.0 for the observed finding profile (2 critical, 3 high, 1 medium).",
      "suggestion": "Recompute the structure score using: max(1.0, 10 - min(2*3 + 3*2 + 1*1, 9)) = 1.0",
      "context": "structure dimension"
    },
    {
      "category": "coverage-gap",
      "severity": "warning",
      "description": "Project uses Express.js but security dimension has 0 findings. Expected at least auth/injection findings for an API project.",
      "suggestion": "Re-run scan-security with express-specific rules, or manually verify the security scan output.",
      "context": "security dimension"
    }
  ]
}
```

## Error Handling

| Scenario | Resolution |
|----------|------------|
| Cannot read `scores.json` | Raise blocking `score-calibration`: `"scores.json missing or unreadable at {SCORES_PATH}."` Skip Checks 1, 3 (partially). |
| Cannot read any scan report in `SCAN_REPORTS_DIR` | Raise blocking `score-calibration`: `"Raw scan reports unavailable — formula verification and dedup checks skipped."` |
| Draft report missing expected sections | Raise blocking `actionability`: `"Draft report at {DRAFT_REPORT_PATH} is missing required sections: {list}."` |
| Dimension in scores.json has no matching scan report file | Skip formula check for that dimension; raise warning `score-calibration`: `"No scan report found for dimension '{name}' — formula check skipped."` |
| `ITERATION >= 3` and blocking issues persist | Include all accumulated unresolved blocking issues. Add to the first blocking issue's description: `"[MAX ITERATIONS REACHED] These issues require human intervention — the reconciler cannot automatically resolve them."` |
| Draft report path does not exist | Raise blocking `actionability`: `"Draft report not found at {DRAFT_REPORT_PATH}."` Set `verdict: "fail"` and return immediately. |
| `dimensions_analyzed` in scores.json is empty | Raise blocking `score-calibration`: `"dimensions_analyzed is empty — report appears to cover no dimensions."` |
