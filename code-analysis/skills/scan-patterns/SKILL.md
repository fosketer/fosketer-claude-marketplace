---
name: scan-patterns
description: |
  This skill should be used when detecting design patterns, anti-patterns, pattern consistency, framework idiom adherence, and error handling patterns.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Patterns

## Purpose

Identify design patterns in use, detect anti-patterns, evaluate pattern consistency across the codebase, check framework idiom adherence, and assess error handling patterns.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null

## Workflow

### Step 1 — Scan for Design Pattern Indicators

1. Use Grep to detect structural indicators of common design patterns:
   - **Repository pattern**: Grep for `Repository` in class/interface names, files named `*repository*`, `*repo*`
   - **Factory pattern**: Grep for `Factory`, `create`, `build` in class names; static methods returning instances
   - **Observer pattern**: Grep for `EventEmitter`, `subscribe`, `on(`, `addEventListener`, `publish`, `notify`
   - **Strategy pattern**: Grep for interfaces/abstract classes with single method + multiple implementations in same directory
   - **Dependency Injection**: Grep for `@Injectable`, `@Inject`, `IServiceCollection`, `container.register`, constructor parameters matching interface names
   - **CQRS**: Grep for `Command`, `Query`, `Handler` class name suffixes; separate read/write models
   - **Mediator**: Grep for `Mediator`, `IMediator`, `MediatR`, `Send(`, `Publish(`
   - **Singleton**: Grep for `getInstance`, `static instance`, `@Singleton`, private constructors
2. Read matched files to confirm pattern usage (not just naming coincidence)
3. Record each confirmed pattern: name, locations, approximate usage count

### Step 2 — Detect Anti-Patterns

1. **God class**: Read files flagged in scan-quality for size. Grep for classes with >10 public methods or >15 dependencies (imports/injections). Severity: **high**
2. **Spaghetti code**: Grep for deeply nested callbacks (>3 levels), excessive `goto`/`break`/`continue`, functions calling many unrelated functions. Severity: **high**
3. **Golden hammer**: Check if a single library/pattern is used for everything (e.g., Redux for local component state, ORM for raw SQL queries). Cross-reference dependency usage with context. Severity: **medium**
4. **Magic numbers/strings**: Grep for numeric literals (excluding 0, 1, -1) and string literals in conditionals and assignments:
   - `if \(.* == \d{2,}` or `if \(.* === ['"]` (non-trivial comparisons)
   - Skip constants, enums, and configuration files
   - Severity: **low** for isolated cases, **medium** for systematic use
5. **Shotgun surgery**: Identify cases where a single conceptual change requires edits across many files. Grep for the same domain term appearing in >5 different modules without a shared abstraction. Severity: **medium**
6. **Primitive obsession**: Grep for function signatures with >3 parameters of the same primitive type (string, int, bool). Severity: **low**

### Step 3 — Check Pattern Consistency

1. For each design pattern detected in Step 1, check if the same problem is solved differently elsewhere:
   - If Repository pattern is used for some data access but raw queries elsewhere, flag inconsistency
   - If DI is used in some modules but manual instantiation in others, flag inconsistency
   - If some API endpoints use middleware/decorators while others inline the same logic, flag inconsistency
2. Check error handling consistency (detailed in Step 5)
3. Severity: **medium** for inconsistencies — consistency matters more than which pattern is chosen

### Step 4 — Check Framework Idiom Adherence

1. Read the framework profile's "Idiomatic patterns" and "Anti-patterns" sections
2. For each listed idiom, Grep for adherence or violation:
   - **React**: Grep for class components (anti-pattern if hooks are used elsewhere), direct DOM manipulation, state mutation
   - **Express/Fastify**: Grep for error handling middleware placement, route organization
   - **Django**: Grep for fat views (logic should be in models/services), raw SQL in views
   - **ASP.NET**: Grep for service registration patterns, middleware order, controller responsibilities
   - **FastAPI**: Grep for dependency injection usage, Pydantic model usage, sync vs async consistency
3. Use Context7 MCP (resolve-library-id then query-docs) to validate current best practices when the framework profile may be outdated
4. Severity: **medium** for idiom violations, **high** for deprecated/unsafe patterns

### Step 5 — Assess Error Handling Patterns

1. Grep for error handling constructs:
   - **Python**: `try/except`, `raise`, custom exception classes
   - **TypeScript/JS**: `try/catch`, `.catch(`, `throw new`, custom error classes
   - **C#**: `try/catch`, `throw`, custom exception classes, `Result<T>` pattern
   - **Rust**: `Result<T, E>`, `unwrap()`, `expect()`, `?` operator
   - **Go**: `if err != nil`, custom error types
2. Check for consistency:
   - Are custom exceptions/errors defined and used consistently?
   - Is error handling centralized (middleware/global handler) or scattered?
   - Are errors swallowed silently (empty catch blocks)?
3. Flag issues:
   - **Empty catch/except blocks**: Severity **high** — errors silently swallowed
   - **Generic catch-all** (`except Exception`, `catch (Exception e)`) without re-throw: Severity **medium**
   - **Mixed error strategies** (exceptions + result types + error codes) without clear boundaries: Severity **medium**
   - **Rust `unwrap()`/`expect()` in non-test code**: Severity **medium**

### Step 6 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "PAT-e7b4a1-3f2a",
  "dimension": "patterns",
  "title": "God class detected: ApplicationService",
  "description": "ApplicationService has 23 public methods, 18 injected dependencies, and handles user management, notifications, and billing in a single class.",
  "severity": "high",
  "file_path": "src/services/application_service.py",
  "line_start": 1,
  "line_end": 487,
  "snippet": "class ApplicationService:\n    def __init__(self, user_repo, billing_repo, notification_service, ...):",
  "recommendation": "Split into focused services: UserService, BillingService, NotificationService",
  "effort": "high",
  "tags": ["anti-pattern", "god-class", "single-responsibility"]
}
```

Always populate `snippet` with the relevant code lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Framework profile not available | Skip idiom checks (Step 4), proceed with language-level pattern detection |
| Context7 unavailable | Skip best-practice validation, rely on framework profile only |
| No clear patterns detected | Report as info finding — codebase may be too small or procedural in style |
| Mixed frameworks in project | Apply each framework's idioms to its respective files only |
| Metaprogramming or code generation | Exclude generated files from anti-pattern detection, note limitation |

## Success Checklist

- [ ] Design patterns identified with locations and usage counts
- [ ] Anti-patterns detected and classified by severity
- [ ] Pattern consistency evaluated across modules
- [ ] Framework idiom adherence checked against profile
- [ ] Error handling patterns assessed for consistency and completeness
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

2. Compute title_hash4 — normalize the finding title (lowercase, strip whitespace) and hash:
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

3. ID = PAT-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored (e.g., 40-360 line shifts across iterations), breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = PAT-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `PAT-8f3a21-a1b2` and `PAT-8f3a21-a1b2-2` are carried forward, a new collision gets `PAT-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-patterns.json
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
           Since IDs use title_hash (not line numbers), the ID remains stable across line shifts.
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
2. For each new finding: verify no duplicate with carried-forward findings (same file and same or equivalent title). If duplicate, skip. If new, generate fingerprint ID.

### Output

DimensionReport MUST include:
1. All carried-forward findings (original IDs)
2. All new findings (new fingerprint IDs)
3. carry_forward_summary: { carried_forward, resolved, new, unverified, resolved_ids }

### Constraints

- NEVER re-describe a carried-forward finding in different words
- NEVER assign a new ID to a carried-forward unchanged finding
- NEVER carry forward without checking CHANGED_FILES first (if available)
