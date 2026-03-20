---
name: scan-performance
description: |
  Detect N+1 queries, missing pagination, unbounded collections, frontend re-render triggers, and caching gaps.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
---

# Scan Performance

## Purpose

Analyze the codebase for performance anti-patterns including N+1 queries, missing pagination, unbounded collections, frontend rendering inefficiencies, bundle size concerns, and caching gaps.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null

## Workflow

### Step 1 — Scan Data Access Patterns

1. Detect N+1 query patterns by searching for ORM/database calls inside loops using Grep:
   - **Python (Django/SQLAlchemy)**: `for .+ in .+:` followed by `.objects.`, `.query.`, `.filter(`, `.get(`
   - **TypeScript (Prisma/TypeORM)**: `for .+ of .+` or `.forEach(` followed by `.find(`, `.findOne(`, `await prisma.`
   - **C# (EF Core)**: `foreach .+ in .+` followed by `.Include(`, `.Where(`, `.FirstOrDefault(`, `_context.`
   - **Go**: `for .+ range .+` followed by `.Query(`, `.QueryRow(`, `db.`
2. Detect missing eager loading: ORM queries that access related entities without `.Include()`, `.select_related()`, `.prefetch_related()`, or equivalent
3. Severity: **critical** for N+1 inside request handlers, **high** for N+1 in background jobs

### Step 2 — Check API Endpoints for Pagination

1. Identify list/collection endpoints using Grep:
   - **REST**: route handlers with `GET` + plural nouns (e.g., `/users`, `/orders`, `/items`)
   - **GraphQL**: resolver functions returning arrays
2. Check whether return-all patterns exist: `.FindAll()`, `.ToList()`, `.fetchAll()`, `SELECT * FROM` without `LIMIT`
3. Flag endpoints that return unbounded collections without `skip`/`take`, `limit`/`offset`, or cursor-based pagination
4. Severity: **high**

### Step 3 — Analyze Memory Patterns

1. Grep for unbounded collection growth inside loops:
   - **Python**: `.append(` inside `for`/`while` without size check
   - **TypeScript/JS**: `.push(` inside `for`/`while`/`.forEach(` without size check
   - **C#**: `.Add(` inside `foreach`/`for`/`while` without capacity or limit
   - **Go**: `append(` inside `for` without capacity pre-allocation
2. Grep for large in-memory data loading: reading entire files or result sets into memory (`readFileSync`, `File.ReadAllText`, `.read()`, `StreamReader` without buffering)
3. Severity: **high** for unbounded growth in request paths, **medium** for batch jobs

### Step 4 — Check Frontend Rendering (if React/Flutter)

Skip this step if FRAMEWORK_PROFILE does not indicate a frontend framework.

1. **React-specific** — Grep for re-render triggers:
   - Inline object/array literals in JSX props: `prop={[`, `prop={{` (creates new reference each render)
   - Missing `React.memo` on components receiving complex props
   - Missing `useMemo`/`useCallback` for expensive computations or callback props
   - State updates that trigger full tree re-renders (context value changes without memoization)
2. **Flutter-specific** — Grep for:
   - `setState` in large widget trees without granular `StatefulWidget` decomposition
   - Missing `const` constructors on stateless widgets
3. Severity: **medium** for missing memoization, **high** for context re-render storms

### Step 5 — Analyze Imports for Bundle Impact

Skip this step if STACK does not include a frontend JavaScript/TypeScript framework.

1. Grep for barrel imports that prevent tree-shaking:
   - `import * from` or `import * as`
   - Named imports from known large libraries without subpath: `import { x } from 'lodash'` instead of `import x from 'lodash/x'`
   - `import` of entire icon libraries (`@mui/icons-material`, `react-icons`)
2. Grep for dynamic import opportunities: large imports used only in specific routes/conditions that SHOULD use `React.lazy()` or dynamic `import()`
3. Severity: **medium** for barrel imports, **high** for large library full-imports

### Step 6 — Check Caching Patterns

1. Identify expensive operations — repeated DB/API calls for the same data:
   - Grep for identical query patterns called in multiple request handlers
   - Grep for external HTTP calls (`fetch(`, `HttpClient`, `requests.get`) without caching layer
2. Check for missing cache usage: look for cache infrastructure (Redis, `IMemoryCache`, `lru_cache`, `@cache`) and whether hot-path endpoints use it
3. Check for synchronous blocking in async contexts using Grep:
   - **Python**: `open(`, `os.path.`, `time.sleep(` inside `async def`
   - **C#**: `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` inside `async Task`
   - **TypeScript**: `fs.readFileSync`, `execSync` in async handlers
4. Severity: **high** for sync blocking in async, **medium** for missing cache on repeated queries

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "PERF-e7b4a1-3f2a",
  "dimension": "performance",
  "title": "N+1 query in OrderController.getOrders()",
  "description": "...",
  "severity": "critical",
  "file_path": "src/controllers/order_controller.py",
  "line_start": 87,
  "line_end": 92,
  "snippet": "for order in orders:\n    items = order.items.all()",
  "recommendation": "Use select_related() or prefetch_related() to eager-load items",
  "effort": "low",
  "tags": ["n-plus-one", "orm", "database"]
}
```

Always populate `snippet` with the relevant code lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No database/ORM layer detected | Skip Steps 1-2, note absence in findings |
| No frontend framework detected | Skip Steps 4-5, note backend-only analysis |
| Multi-language monorepo | Run language-specific patterns for each detected language |
| Very large codebase (>1000 files) | Sample request handlers and hot-path modules, note coverage limitation |
| ORM not recognized | Fall back to raw SQL pattern detection (`SELECT`, `INSERT`, `UPDATE`) |

## Success Checklist

- [ ] Data access patterns scanned for N+1 queries
- [ ] List endpoints checked for pagination
- [ ] Memory growth patterns analyzed
- [ ] Frontend rendering issues checked (if applicable)
- [ ] Import patterns analyzed for bundle impact (if applicable)
- [ ] Caching gaps and sync-in-async blocking detected
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

3. ID = PERF-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored (e.g., 40-360 line shifts across iterations), breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = PERF-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `PERF-8f3a21-a1b2` and `PERF-8f3a21-a1b2-2` are carried forward, a new collision gets `PERF-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-performance.json
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
