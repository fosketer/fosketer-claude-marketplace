---
name: scan-quality
version: 0.7.0
description: |
  This skill should be used when detecting code duplication, complexity hotspots, dead code, naming inconsistencies,
  size violations, tech debt markers, deprecated APIs, legacy patterns, performance anti-patterns, and caching gaps.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Quality

## Purpose

Evaluate code quality across three sub-areas: **Code Health** (duplication, complexity, dead code, naming, size), **Tech Debt** (TODOs, deprecated APIs, legacy patterns, commented-out code), and **Performance** (N+1 queries, pagination, memory, rendering, caching).

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `MODE`: "plugin" when running in plugin analysis mode, absent otherwise
- `PLUGIN_PROFILES_DIR`: Path to `references/plugin-profiles/` (only when MODE=plugin)

### Mode Branch

If `MODE=plugin`: skip Steps 1–6 (general code quality). Execute Plugin Quality steps instead.

### Plugin Quality Steps (MODE=plugin only)

#### Step P1 — Map Markdown Files
1. Glob all `.md` files in plugin directory (exclude node_modules/, .git/)
2. Categorize: skills (skills/*/SKILL.md), agents (agents/*.md, agents/*/AGENT.md), reference docs, README

#### Step P2 — Check Word Counts
1. For each SKILL.md: count words in body (below frontmatter). Flag:
   - Below 500 words: severity **high** ("skill too thin")
   - Below 1,000: **medium** ("skill could be more detailed")
   - Above 3,000: **medium** ("skill may need splitting")
   - Above 5,000: **high** ("skill exceeds maximum")
2. For each agent: count words in system prompt body. Flag if > 5,000 words

#### Step P3 — Check Content Duplication
1. Read skill bodies and detect repeated instruction blocks across skills
2. Flag duplicated blocks > 5 lines appearing in 2+ skills
3. Severity: **medium** for duplication within same plugin

#### Step P4 — Check Markdown Quality
1. Grep for broken markdown: unclosed code fences, orphaned link references, inconsistent heading hierarchy
2. Severity: **low** for formatting issues

## Workflow

### Step 1 — Map Source Files

1. Use Glob to enumerate all source files matching the language profile's file extensions
2. Exclude test files, generated code, vendor/node_modules directories, and build output
3. Group files by module/directory for scoped analysis
4. Record total file count — if exceeding 500 files, select representative samples per module

### Step 2 — Check Code Duplication

1. For each module, Read files and identify repeated code blocks:
   - Blocks of **10+ consecutive lines** that appear in 2+ locations
   - Structural patterns (same function signature + body shape) appearing **3+ times**
2. Use Grep to search for distinctive lines from suspected duplicates across the codebase
3. For each duplicate found, record: locations, line ranges, approximate line count
4. Severity: **high** for blocks >20 lines duplicated 3+ times, **medium** for smaller duplicates

### Step 3 — Check Cyclomatic Complexity

1. Scan for complexity indicators using Grep:
   - **Nested conditionals**: `if/else/elif/switch/case/match` — use Grep with language-appropriate patterns
   - **Python**: `^\s{12,}(if |elif |else:|for |while )` (4+ nesting levels)
   - **TypeScript/JS**: Grep for `\?\s*.*\?` (nested ternaries), deep `if` nesting via indentation
   - **C#**: Grep for nested `if`/`switch` blocks via indentation depth
2. Read flagged files and count decision points per function:
   - Each `if`, `elif`/`else if`, `for`, `while`, `case`, `catch`, `&&`, `||` adds 1
   - Threshold: **>10** per function is **high** severity, **>20** is **critical**
3. Flag functions with excessive branching paths

### Step 4 — Check Dead Code

1. **Unused exports**: Grep for all `export` declarations (or language equivalent), then cross-reference with imports across the project. Exports never imported externally are candidates.
   - **Python**: Grep for definitions in `__init__.py` or `__all__`, cross-reference with `from X import`
   - **TypeScript/JS**: Grep for `export (const|function|class|interface|type)`, cross-reference with `import`
   - **C#**: Grep for `public (class|interface|enum|struct)`, cross-reference with `using` and direct references
2. **Unused imports**: Grep for import statements, then verify the imported symbol appears elsewhere in the file
3. **Unreachable branches**: Grep for patterns like `if (false)`, `if (true) { ... } else {`, `return` followed by code
4. Severity: **low** for unused imports, **medium** for unused exports, **high** for unreachable code

### Step 5 — Check Naming Conventions

1. Read the language profile's naming conventions section
2. Scan for violations using Grep:
   - **Python**: Classes MUST be PascalCase (`class [a-z]`), functions/variables MUST be snake_case (`def [A-Z]`)
   - **TypeScript/JS**: Classes MUST be PascalCase, variables/functions MUST be camelCase (`const [A-Z][A-Z]` for non-constants)
   - **C#**: Public members MUST be PascalCase, private fields SHOULD be `_camelCase`
3. Check consistency within the codebase — mixed conventions are worse than a non-standard but consistent convention
4. Severity: **low** for individual violations, **medium** for systematic inconsistency

### Step 6 — Check File and Function Sizes

1. Use Bash to count lines per file: files exceeding **300 lines** are flagged
2. Read flagged files and identify individual functions/methods:
   - Functions exceeding **50 lines** are flagged as **medium** severity
   - Functions exceeding **100 lines** are flagged as **high** severity
3. Check parameter counts per function:
   - **>5 parameters**: **medium** severity
   - **>8 parameters**: **high** severity
   - Use Grep with patterns like `def \w+\(` (Python) or `function \w+\(` (JS/TS) then count commas

### Sub-Section: Tech Debt

#### Step 7 — Grep for TODO Markers

1. Grep across all source files (excluding `node_modules`, `dist`, `bin`, `obj`, vendor directories) for debt markers:
   - Patterns: `TODO`, `FIXME`, `HACK`, `XXX`, `WORKAROUND`, `TEMPORARY`, `TECH.?DEBT`
2. Categorize each marker:
   - **FIXME/HACK/XXX**: Known defects or workarounds — severity **high**
   - **TODO**: Planned improvements — severity **medium**
   - **WORKAROUND/TEMPORARY**: Intentional shortcuts awaiting resolution — severity **medium**
3. Count totals per category and per module/directory
4. Flag files with more than 5 markers as high-debt hotspots

#### Step 8 — Scan for Deprecated API Usage

Scan using language-specific and framework-specific Grep patterns:

1. **Python**:
   - `@deprecated`, `warnings.warn(.*DeprecationWarning`, `distutils.` (removed in 3.12), `imp.` (use `importlib`), `optparse.` (use `argparse`), `unittest.makeSuite`
2. **TypeScript/JavaScript**:
   - `substr(` (use `slice`), `__defineGetter__`, `__defineSetter__`, `escape(` / `unescape(`, `document.write(`
3. **C#**:
   - `[Obsolete`, `WebClient` (use `HttpClient`), `BinaryFormatter`, `JavaScriptSerializer` (use `System.Text.Json`), `Startup.cs` patterns replaced by minimal APIs in .NET 6+
4. **Go**:
   - `ioutil.` (deprecated in Go 1.16, use `io`/`os`), `golang.org/x/net/context` (use standard `context`)
5. **Dart/Flutter**:
   - `@deprecated`, `@Deprecated(`, `FlatButton` (use `TextButton`), `RaisedButton` (use `ElevatedButton`)
6. Severity: **high** for deprecated APIs with security implications, **medium** for all others

#### Step 9 — Detect Legacy Patterns

Scan for patterns that have modern replacements based on LANGUAGE_PROFILE:

1. **JavaScript/TypeScript**:
   - `var ` declarations (use `const`/`let`) — Grep `^\s*var `
   - Callback-based async (use `async`/`await`) — Grep `.then(.*\.then(` (nested promise chains)
   - `require(` in TypeScript files (use ES `import`)
   - `module.exports` in TypeScript files
2. **Python**:
   - `%s` / `% ` string formatting (use f-strings) — Grep `['"].*%[sd]`
   - `.format(` where f-string is simpler
   - `print` statements without `(` (Python 2 syntax)
   - `type(x) == ` or `type(x) is ` (use `isinstance()`)
3. **C#**:
   - `string.Format(` (use string interpolation `$"..."`)
   - `Task.Run(() => ` wrapping synchronous code in controllers
   - Manual `IDisposable` patterns where `using` declaration suffices
4. Severity: **low** for style preferences, **medium** for patterns with functional improvements

#### Step 10 — Find Commented-Out Code Blocks

1. Grep for multi-line comment blocks that contain code patterns:
   - Blocks of 3+ consecutive commented lines containing code syntax (assignments, function calls, imports, conditionals)
   - **Python**: consecutive `#` lines with code patterns (not docstrings)
   - **TypeScript/JS**: `/* ... */` blocks or consecutive `//` lines with code patterns
   - **C#**: `/* ... */` blocks or consecutive `//` lines with code patterns
2. Exclude license headers, documentation comments, and intentional examples
3. Severity: **low** for small blocks (3-10 lines), **medium** for large blocks (>10 lines)

### Sub-Section: Performance

#### Step 11 — Scan Data Access Patterns

1. Detect N+1 query patterns by searching for ORM/database calls inside loops using Grep:
   - **Python (Django/SQLAlchemy)**: `for .+ in .+:` followed by `.objects.`, `.query.`, `.filter(`, `.get(`
   - **TypeScript (Prisma/TypeORM)**: `for .+ of .+` or `.forEach(` followed by `.find(`, `.findOne(`, `await prisma.`
   - **C# (EF Core)**: `foreach .+ in .+` followed by `.Include(`, `.Where(`, `.FirstOrDefault(`, `_context.`
   - **Go**: `for .+ range .+` followed by `.Query(`, `.QueryRow(`, `db.`
2. Detect missing eager loading: ORM queries that access related entities without `.Include()`, `.select_related()`, `.prefetch_related()`, or equivalent
3. Severity: **critical** for N+1 inside request handlers, **high** for N+1 in background jobs

#### Step 12 — Check API Endpoints for Pagination

1. Identify list/collection endpoints using Grep:
   - **REST**: route handlers with `GET` + plural nouns (e.g., `/users`, `/orders`, `/items`)
   - **GraphQL**: resolver functions returning arrays
2. Check whether return-all patterns exist: `.FindAll()`, `.ToList()`, `.fetchAll()`, `SELECT * FROM` without `LIMIT`
3. Flag endpoints that return unbounded collections without `skip`/`take`, `limit`/`offset`, or cursor-based pagination
4. Severity: **high**

#### Step 13 — Analyze Memory Patterns

1. Grep for unbounded collection growth inside loops:
   - **Python**: `.append(` inside `for`/`while` without size check
   - **TypeScript/JS**: `.push(` inside `for`/`while`/`.forEach(` without size check
   - **C#**: `.Add(` inside `foreach`/`for`/`while` without capacity or limit
   - **Go**: `append(` inside `for` without capacity pre-allocation
2. Grep for large in-memory data loading: reading entire files or result sets into memory (`readFileSync`, `File.ReadAllText`, `.read()`, `StreamReader` without buffering)
3. Severity: **high** for unbounded growth in request paths, **medium** for batch jobs

#### Step 14 — Check Frontend Rendering (if React/Flutter)

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

#### Step 15 — Check Caching Patterns

1. Identify expensive operations — repeated DB/API calls for the same data:
   - Grep for identical query patterns called in multiple request handlers
   - Grep for external HTTP calls (`fetch(`, `HttpClient`, `requests.get`) without caching layer
2. Check for missing cache usage: look for cache infrastructure (Redis, `IMemoryCache`, `lru_cache`, `@cache`) and whether hot-path endpoints use it
3. Check for synchronous blocking in async contexts using Grep:
   - **Python**: `open(`, `os.path.`, `time.sleep(` inside `async def`
   - **C#**: `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` inside `async Task`
   - **TypeScript**: `fs.readFileSync`, `execSync` in async handlers
4. Severity: **high** for sync blocking in async, **medium** for missing cache on repeated queries

### Step 16 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "QUAL-e7b4a1-3f2a",
  "dimension": "quality",
  "title": "Duplicated validation logic across 3 modules",
  "description": "The email validation block (15 lines) is copy-pasted in user_service.py, auth_handler.py, and registration.py",
  "severity": "high",
  "file_path": "src/services/user_service.py",
  "line_start": 42,
  "line_end": 57,
  "snippet": "def validate_email(email):\n    if not re.match(r'...',  email): ...",
  "recommendation": "Extract to a shared validation utility module",
  "effort": "low",
  "tags": ["duplication", "DRY-violation"]
}
```

Always populate `snippet` with the relevant code lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Severity Guidelines

When assigning severity to performance findings, consider the execution context:

- **critical**: Unbounded resource consumption in request-handling paths that could cause OOM or service degradation under normal load
- **high**: N+1 queries in list endpoints, missing pagination on user-facing APIs, synchronous blocking in async hot paths
- **medium**: Missing memoization in frequently-rendered components, cache-eligible operations without caching
- **low**: Minor optimization opportunities (e.g., pre-allocating slice capacity in Go)

Performance findings should always include the execution frequency context in the description (per-request, per-page-load, per-batch-run, startup-only).

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Language naming conventions not in profile | Infer from majority usage in codebase, report as info |
| Generated code flagged as duplicate | Exclude files matching common generation patterns (*.generated.*, *.g.cs, *_pb2.py) |
| Very large files (>2000 lines) | Read in chunks using offset/limit, note partial analysis |
| Mixed languages in project | Apply each language's rules to its own files only |
| No functions detected (declarative code) | Skip complexity and size checks, note as info finding |
| Language/framework version not detectable | Skip migration opportunity checks, note limitation |
| No dependency manifest found | Skip pinned version checks |
| Comment style ambiguous (code vs documentation) | Err on the side of inclusion, add `"confidence": "low"` note |
| No database/ORM layer detected | Skip Steps 11-12, note absence in findings |
| No frontend framework detected | Skip Step 14, note backend-only analysis |
| ORM not recognized | Fall back to raw SQL pattern detection (`SELECT`, `INSERT`, `UPDATE`) |

## Success Checklist

- [ ] Source files mapped and filtered (excluding tests, generated, vendor)
- [ ] Code duplication detected with locations and line counts
- [ ] Cyclomatic complexity assessed per function with thresholds applied
- [ ] Dead code candidates identified (unused exports, imports, unreachable branches)
- [ ] Naming convention adherence checked against language profile
- [ ] File and function size violations flagged with severity
- [ ] Parameter count violations flagged
- [ ] TODO/FIXME/HACK/XXX markers counted and categorized
- [ ] Deprecated API usage detected per language and framework
- [ ] Legacy patterns with modern replacements identified
- [ ] Commented-out code blocks detected
- [ ] Data access patterns scanned for N+1 queries
- [ ] List endpoints checked for pagination
- [ ] Memory growth patterns analyzed
- [ ] Frontend rendering issues checked (if applicable)
- [ ] Caching gaps and sync-in-async blocking detected
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
