---
name: scan-testing
version: 0.7.0
description: |
  This skill should be used when the user asks to "check test coverage", "find flaky tests", "analyze test quality",
  "scan for test isolation issues", or when analyzing test coverage gaps, assertion quality, test isolation,
  and flaky test indicators.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
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

### Sub-Section: Dependency Hygiene

#### Step 7 — Locate and Read Manifests

1. Use Glob to find all dependency manifests in the project:
   - **Python**: `**/requirements*.txt`, `**/pyproject.toml`, `**/setup.py`, `**/setup.cfg`, `**/Pipfile`, `**/pixi.toml`
   - **TypeScript/JS**: `**/package.json` (exclude `node_modules/`)
   - **C#**: `**/*.csproj`, `**/Directory.Packages.props`, `**/global.json`
   - **Rust**: `**/Cargo.toml`
   - **Go**: `**/go.mod`, `**/go.sum`
   - **Dart**: `**/pubspec.yaml`
2. Read each manifest and extract: package name, declared version/range, whether it is a dev/test dependency
3. Build a consolidated dependency list with source manifest path for each entry

#### Step 8 — Cross-Reference Imports Against Declarations

1. Grep all source files for import/require/using statements
2. Map each imported package to its manifest declaration
3. Identify **unused dependencies**: declared in manifest but never imported in any source file
   - MUST exclude runtime-only dependencies that are not imported (e.g., plugins, CLI tools, type stubs)
   - For TypeScript: check both `import` statements and `/// <reference types="..." />`
   - For Python: check both `import X` and `from X import Y`, account for namespace differences (e.g., `python-dateutil` imports as `dateutil`)
4. Severity: **medium** for unused dependencies (they add install weight and attack surface)

#### Step 9 — Check for Outdated Dependencies

1. Use Context7 MCP (resolve-library-id then query-docs) to look up current stable versions for key dependencies
2. If Context7 is unavailable, use Bash to run ecosystem-specific audit commands:
   - **Node.js**: `npm outdated --json` (if package-lock.json exists)
   - **Python**: `pip list --outdated --format=json` (if virtual environment is available)
   - **C#**: `dotnet list package --outdated --format json` (if SDK is available)
3. Compare declared versions against latest stable versions
4. Classify by staleness:
   - **1 major version behind**: **medium** severity
   - **2+ major versions behind**: **high** severity
   - **Minor/patch behind only**: **low** severity

#### Step 10 — Detect Duplicate Dependencies

1. Check for multiple packages serving the same purpose:
   - **HTTP clients**: `axios` + `node-fetch` + `got` (JS/TS); `requests` + `httpx` + `urllib3` (Python)
   - **Testing**: `jest` + `mocha` + `vitest` (JS/TS); `pytest` + `unittest` + `nose` (Python)
   - **Validation**: `joi` + `zod` + `yup` (JS/TS); `pydantic` + `marshmallow` + `cerberus` (Python)
   - **Logging**: `winston` + `pino` + `bunyan` (JS/TS); `logging` + `loguru` + `structlog` (Python)
   - **ORM**: `typeorm` + `prisma` + `sequelize` (JS/TS); `sqlalchemy` + `django.db` + `peewee` (Python)
2. Read the language profile for known duplicate-purpose groups
3. Severity: **low** for potential duplicates (may be intentional), **medium** if both are imported in similar contexts

#### Step 11 — Detect Version Conflicts

1. For monorepos or multi-manifest projects, check if the same package is declared at different versions across manifests
2. For Node.js: check `package.json` across workspace packages for mismatched versions
3. For Python: check for conflicting version specifiers across `requirements*.txt` files
4. For C#: check for version mismatches when `Directory.Packages.props` is not used (central package management)
5. Severity: **high** for conflicting ranges that cannot resolve, **medium** for mismatched but compatible versions

### Step 12 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "TST-e7b4a1-3f2a",
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
| No manifest files found | Report as critical finding — project has no declared dependencies |
| Context7 unavailable | Fall back to local CLI audit tools; if also unavailable, skip version checks and note limitation |
| CLI audit tools not installed | Skip automated audit, rely on manifest version analysis only, note limitation |
| Lock file missing | Note as medium finding (non-reproducible builds), proceed with manifest versions |
| Private/internal packages | Skip version checks for packages from private registries |
| Monorepo with workspace protocol | Treat workspace references as internal, not external dependencies |

## Success Checklist

- [ ] Coverage command executed and percentage parsed (or unavailability finding created)
- [ ] Test files discovered and counted
- [ ] Test-to-code ratio computed
- [ ] Public APIs mapped to corresponding test files
- [ ] Assertion quality analyzed (empty and trivial assertions flagged)
- [ ] Edge case coverage checked per tested API
- [ ] Isolation issues detected (shared state, global mocks)
- [ ] Flakiness indicators identified
- [ ] All dependency manifests located and parsed
- [ ] Unused dependencies identified via import cross-reference
- [ ] Outdated dependencies checked against latest stable versions
- [ ] Duplicate-purpose packages detected
- [ ] Version conflicts across manifests identified
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
