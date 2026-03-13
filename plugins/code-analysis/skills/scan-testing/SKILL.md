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

## Workflow

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
  "id": "test-001",
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

- [ ] Test files discovered and counted
- [ ] Test-to-code ratio computed
- [ ] Public APIs mapped to corresponding test files
- [ ] Assertion quality analyzed (empty and trivial assertions flagged)
- [ ] Edge case coverage checked per tested API
- [ ] Isolation issues detected (shared state, global mocks)
- [ ] Flakiness indicators identified
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator
