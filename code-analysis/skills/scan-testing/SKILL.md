---
name: scan-testing
description: |
  Analyze test coverage gaps, assertion quality, test isolation, and flaky test indicators.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
---

# Scan Testing

## Purpose

Analyze the codebase's test suite for coverage gaps, assertion quality, isolation issues, and flakiness indicators.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null

## Workflow

### Step 0 — Measure Actual Coverage

Run the language-appropriate coverage command from the LANGUAGE_PROFILE's "Coverage Measurement" section:

1. Execute the coverage command in `PROJECT_PATH` using Bash
2. Parse the output file to extract the line/branch coverage percentage:
   - **Python**: Read `coverage.json` → `totals.percent_covered`
   - **Rust**: Read `tarpaulin-report.json` → top-level `coverage`
   - **TypeScript**: Read `coverage-summary.json` → `total.lines.pct`
3. Map the coverage percentage to a finding using the severity thresholds from the LANGUAGE_PROFILE:
   - < 40% → critical, effort: large
   - 40–60% → high, effort: medium
   - 60–75% → medium, effort: small
   - 75–90% → low, effort: trivial
   - ≥ 90% → info only
4. If the coverage tool fails to run, is not installed, or produces no output: create a **medium** finding:
   `"Coverage measurement unavailable — install [tool name from profile]"`
   **Do NOT silently skip.** Do NOT assign a score without a measurement.
5. The coverage finding MUST rank above all other testing findings in severity ordering.

### Step 1 — Discover Test Files

1. Use Glob to locate test files by convention:
   - `**/*test*.*`, `**/*spec*.*`, `**/__tests__/**`, `**/tests/**`, `**/test/**`
   - Match framework-specific patterns from the FRAMEWORK_PROFILE (e.g., `*.test.tsx` for React, `test_*.py` for Python)
2. Count test files vs source files to compute the test-to-code ratio
3. Flag projects with ratio below 0.3 as **high** severity, below 0.5 as **medium**

### Step 2 — Map Test-to-Source Coverage

1. For each source file containing public APIs (classes, functions, endpoints), search for a corresponding test file
   - **Python**: Match `src/module/service.py` to `tests/test_service.py` or `tests/module/test_service.py`
   - **TypeScript/JS**: Match `src/service.ts` to `src/service.test.ts`, `src/service.spec.ts`, or `__tests__/service.test.ts`
   - **C#**: Match `Src/Service.cs` to `Tests/ServiceTests.cs` or `Tests/ServiceTest.cs`
   - **Go**: Match `service.go` to `service_test.go` (same package)
   - **Dart**: Match `lib/service.dart` to `test/service_test.dart`
2. Identify public functions/classes without any corresponding test using Grep:
   - **Python**: `^(def |class )` in source, cross-reference with test imports and test method names
   - **TypeScript/JS**: `^export (function|class|const)` — cross-reference with test file imports
   - **C#**: `public (class|void|async|Task|static)` — cross-reference with test class references
3. Severity: **high** for untested public API endpoints, **medium** for untested utility functions

### Step 3 — Analyze Assertion Quality

1. Within each test file, scan for assertion patterns using Grep:
   - **Python**: `assert `, `self.assert`, `pytest.raises`
   - **TypeScript/JS**: `expect(`, `assert.`, `should.`
   - **C#**: `Assert.`, `Should()`, `.Verify(`
   - **Go**: `t.Error`, `t.Fatal`, `assert.`, `require.`
2. Flag test functions with zero assertions — Grep for test function definitions and check that at least one assertion exists between the function start and the next function start
3. Flag trivial assertions: `assert True`, `assert 1 == 1`, `expect(true).toBe(true)`, `Assert.True(true)`
4. Severity: **high** for no assertions, **medium** for trivial-only assertions

### Step 4 — Check for Edge Cases

1. Scan test files for null/empty/boundary test patterns using Grep:
   - Null checks: `null`, `None`, `nil`, `undefined`
   - Empty checks: `""`, `''`, `[]`, `{}`, `empty`, `Empty`
   - Boundary checks: `0`, `-1`, `MAX`, `MIN`, `boundary`, `edge`
2. For each tested public API, check whether edge case patterns appear in its tests
3. Flag APIs with tests that only cover the happy path (no null/empty/boundary assertions)
4. Severity: **medium**

### Step 5 — Detect Isolation Issues

1. Scan for shared mutable state using Grep:
   - **Python**: module-level mutable variables referenced in tests, `global` keyword in test files
   - **TypeScript/JS**: `let` at module scope in test files, missing `beforeEach` reset
   - **C#**: `static` mutable fields in test classes, missing `[SetUp]`/`[TestInitialize]` reset
2. Detect order-dependent tests: test files that rely on execution order (e.g., test B references data created in test A)
3. Detect global mocks that leak: `mock.patch` at module level without corresponding unpatch, `jest.mock` without `jest.restoreAllMocks`
4. Severity: **high** for shared mutable state, **medium** for global mock leaks

### Step 6 — Check for Flakiness Indicators

1. Grep for timing-dependent patterns in test files:
   - `sleep(`, `setTimeout(`, `Thread.Sleep(`, `Task.Delay(`, `time.sleep(`
   - `waitFor(`, `waitUntil(`, `Eventually(` without reasonable timeout
2. Grep for race condition indicators:
   - Shared file I/O in tests without unique temp paths
   - Network calls in unit tests (HTTP clients, socket references)
   - Date/time-dependent assertions (`Date.now`, `datetime.now`, `DateTime.Now`)
3. Severity: **high** for sleep-based waits in unit tests, **medium** for time-dependent assertions

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "TST-e7b4a1-0000",
  "dimension": "testing",
  "title": "Untested public API: UserService.createUser()",
  "description": "...",
  "severity": "high",
  "file_path": "src/services/user_service.py",
  "line_start": 42,
  "line_end": 42,
  "snippet": "def createUser(self, data: UserInput) -> User:",
  "recommendation": "Add unit tests covering happy path, null input, and duplicate user scenarios",
  "effort": "medium",
  "tags": ["missing-test", "public-api"]
}
```

Always populate `snippet` with the relevant code lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No test files found | Report as critical finding; recommend establishing a test suite |
| Test framework not recognized | Use generic assertion patterns (`assert`, `expect`), note detection limitation |
| Very large test suite (>500 test files) | Sample representative modules, note coverage limitation |
| Non-standard test file naming | Fall back to Grep for assertion keywords across all non-source files |
| Monorepo with multiple test roots | Discover each test root independently and merge results |

## Success Checklist

- [ ] Coverage command executed and percentage parsed (or unavailability finding created)
- [ ] Test files discovered and counted
- [ ] Test-to-code ratio computed
- [ ] Public APIs mapped to corresponding test files
- [ ] Assertion quality analyzed (empty and trivial assertions flagged)
- [ ] Edge case coverage checked per tested API
- [ ] Isolation issues detected (shared state, global mocks)
- [ ] Flakiness indicators identified
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Finding ID Generation

You MUST generate deterministic finding IDs using this algorithm.
NEVER use sequential numbering (001, 002) or free-form IDs.

### For findings with a file_path:

1. Compute file_hash6 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{relative_file_path}').hexdigest()[:6])"
   ```

2. Compute line_bucket:
   floor(line_start / 10) * 10, zero-padded to 4 digits
   Examples: line 1 → 0000, line 47 → 0040, line 374 → 0370

3. ID = TST-{file_hash6}-{line_bucket}

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{lowercase title}').hexdigest()[:4])"
   ```

2. ID = TST-000000-0000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `TST-8f3a21-0370` and `TST-8f3a21-0370-2` are carried forward, a new collision gets `TST-8f3a21-0370-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-testing.json
```
Sort by filename date prefix, take most recent. Parse its `findings` array as PREVIOUS_FINDINGS. If no file found, PREVIOUS_FINDINGS = null.

### Phase 1 — Verify Previous Findings

For each finding in PREVIOUS_FINDINGS, in order:

A. If CHANGED_FILES is provided AND finding.file_path is NOT in CHANGED_FILES:
   → CARRY FORWARD unchanged. Copy the finding exactly (same ID, same severity,
     same description, same line numbers). Do NOT re-read the file.

B. If finding.file_path IS in CHANGED_FILES, OR if CHANGED_FILES is null:
   → Read the file at finding.file_path around finding.line_start to finding.line_end
   → Does the issue described in finding.description still exist?
     YES → carry forward with SAME ID. Update line numbers if code shifted.
           If shifted >10 lines, recompute fingerprint and set previous_id to old ID.
     NO (resolved) → add to resolved_ids list. Do NOT include in output.
     FILE DELETED → add to resolved_ids list. Do NOT include in output.

### Cost Note on CHANGED_FILES=null

When CHANGED_FILES is null, Phase 1 re-reads every file referenced by previous findings,
and Phase 2 scans the full codebase. This can be MORE expensive than a fresh scan.
- ralph-loop SHOULD always provide CHANGED_FILES (via `git diff --name-only`)
- Initial `/analyze-codebase` scans pass CHANGED_FILES=null, which is acceptable because
  there are no PREVIOUS_FINDINGS on first scan
- If PREVIOUS_FINDINGS has >30 findings and CHANGED_FILES is null, the scanner MAY skip
  Phase 1 verification and carry all findings forward tentatively. In this case, set
  `unverified` in carry_forward_summary to the count of tentatively carried findings.
  Note: `unverified` is a **subset** of `carried_forward` (not additive).

### Phase 2 — Discover New Findings

1. Scan scope: CHANGED_FILES if provided, otherwise full codebase
2. For each new finding: verify no duplicate with carried-forward findings (same file, overlapping 10-line range). If duplicate, skip. If new, generate fingerprint ID.

### Output

DimensionReport MUST include:
1. All carried-forward findings (original IDs)
2. All new findings (new fingerprint IDs)
3. carry_forward_summary: { carried_forward, resolved, new, unverified, resolved_ids }

### Constraints

- NEVER re-describe a carried-forward finding in different words
- NEVER assign a new ID to a carried-forward unchanged finding
- NEVER carry forward without checking CHANGED_FILES first (if available)
