# Performance Analysis Patterns

Per-language grep patterns for Steps 11-15 of the scan-quality workflow.

## Step 11 — Data Access Patterns (N+1 Queries)

1. Detect N+1 query patterns by searching for ORM/database calls inside loops using Grep:
   - **Python (Django/SQLAlchemy)**: `for .+ in .+:` followed by `.objects.`, `.query.`, `.filter(`, `.get(`
   - **TypeScript (Prisma/TypeORM)**: `for .+ of .+` or `.forEach(` followed by `.find(`, `.findOne(`, `await prisma.`
   - **C# (EF Core)**: `foreach .+ in .+` followed by `.Include(`, `.Where(`, `.FirstOrDefault(`, `_context.`
   - **Go**: `for .+ range .+` followed by `.Query(`, `.QueryRow(`, `db.`
2. Detect missing eager loading: ORM queries that access related entities without `.Include()`, `.select_related()`, `.prefetch_related()`, or equivalent
3. Severity: **critical** for N+1 inside request handlers, **high** for N+1 in background jobs

## Step 12 — API Endpoints for Pagination

1. Identify list/collection endpoints using Grep:
   - **REST**: route handlers with `GET` + plural nouns (e.g., `/users`, `/orders`, `/items`)
   - **GraphQL**: resolver functions returning arrays
2. Check whether return-all patterns exist: `.FindAll()`, `.ToList()`, `.fetchAll()`, `SELECT * FROM` without `LIMIT`
3. Flag endpoints that return unbounded collections without `skip`/`take`, `limit`/`offset`, or cursor-based pagination
4. Severity: **high**

## Step 13 — Memory Patterns

1. Grep for unbounded collection growth inside loops:
   - **Python**: `.append(` inside `for`/`while` without size check
   - **TypeScript/JS**: `.push(` inside `for`/`while`/`.forEach(` without size check
   - **C#**: `.Add(` inside `foreach`/`for`/`while` without capacity or limit
   - **Go**: `append(` inside `for` without capacity pre-allocation
2. Grep for large in-memory data loading: reading entire files or result sets into memory (`readFileSync`, `File.ReadAllText`, `.read()`, `StreamReader` without buffering)
3. Severity: **high** for unbounded growth in request paths, **medium** for batch jobs

## Step 14 — Frontend Rendering (if React/Flutter)

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

## Step 15 — Caching Patterns

1. Identify expensive operations — repeated DB/API calls for the same data:
   - Grep for identical query patterns called in multiple request handlers
   - Grep for external HTTP calls (`fetch(`, `HttpClient`, `requests.get`) without caching layer
2. Check for missing cache usage: look for cache infrastructure (Redis, `IMemoryCache`, `lru_cache`, `@cache`) and whether hot-path endpoints use it
3. Check for synchronous blocking in async contexts using Grep:
   - **Python**: `open(`, `os.path.`, `time.sleep(` inside `async def`
   - **C#**: `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` inside `async Task`
   - **TypeScript**: `fs.readFileSync`, `execSync` in async handlers
4. Severity: **high** for sync blocking in async, **medium** for missing cache on repeated queries
