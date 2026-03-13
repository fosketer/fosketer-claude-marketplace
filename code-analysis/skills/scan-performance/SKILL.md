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
  "id": "perf-001",
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
