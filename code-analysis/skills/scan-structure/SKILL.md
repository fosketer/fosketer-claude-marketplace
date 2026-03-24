---
name: scan-structure
version: 0.8.0
description: |
  This skill should be used when the user asks to "analyze module structure", "find circular dependencies",
  "check layering violations", "detect anti-patterns", or when analyzing module structure, dependency graph,
  layering violations, circular dependencies, design patterns, anti-patterns, pattern consistency,
  framework idiom adherence, and error handling patterns.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Structure

## Purpose

Analyze the codebase's module structure, dependency graph, layering, circular dependencies, design patterns, anti-patterns, pattern consistency, framework idiom adherence, and error handling patterns.


## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null

## Workflow

### Part A — Module Structure

#### Step 1 — Map Module Structure

1. Use Glob to enumerate top-level directories and identify module boundaries
2. Read the framework profile's "Architecture expectations" for expected structure
3. Document each module: name, purpose (inferred from naming/content), approximate file count
4. Flag unexpected top-level directories that don't match the framework's expected layout

#### Step 2 — Build Dependency Graph

1. For each module, scan import/require/using/include statements:
   - **Python**: `import X`, `from X import Y` — use Grep with pattern `^(import |from \S+ import)`
   - **TypeScript/JS**: `import ... from`, `require(` — use Grep with pattern `(import .+ from|require\()`
   - **C#**: `using X;` — use Grep with pattern `^using \S+;`
   - **Rust**: `use X;`, `mod X;` — use Grep with pattern `^(use |mod )`
   - **Go**: `import "X"` or `import (` blocks — use Grep with pattern `import`
   - **Dart**: `import 'X';` — use Grep with pattern `^import `
2. Classify each dependency as: internal (same project), external (package), or standard library
3. Build a module-to-module adjacency list from internal dependencies

#### Step 3 — Detect Layering Violations

1. Read the framework profile for expected dependency direction (e.g., presentation → business → data)
2. Check for reverse-direction imports (e.g., data layer importing from presentation)
3. Flag imports that bypass layers (e.g., presentation directly accessing data)
4. Severity: **critical** for reverse-direction, **high** for layer-skipping

#### Step 4 — Detect Circular Dependencies

1. Using the adjacency list from Step 2, detect cycles using DFS
2. For each cycle found, record: modules involved, specific import paths
3. Severity: **critical** for all circular dependencies

#### Step 5 — Assess Cohesion

1. For each module, check that files within it share a common concern
2. Flag modules with files that have widely divergent import patterns
3. Flag modules with mixed concerns (e.g., UI components alongside data access)
4. Severity: **medium**

### Part B — Design Patterns

#### Step 6 — Scan for Design Pattern Indicators

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

#### Step 7 — Detect Anti-Patterns

1. **God class**: Read files flagged for size. Grep for classes with >10 public methods or >15 dependencies (imports/injections). Severity: **high**
2. **Spaghetti code**: Grep for deeply nested callbacks (>3 levels), excessive `goto`/`break`/`continue`, functions calling many unrelated functions. Severity: **high**
3. **Golden hammer**: Check if a single library/pattern is used for everything (e.g., Redux for local component state, ORM for raw SQL queries). Cross-reference dependency usage with context. Severity: **medium**
4. **Magic numbers/strings**: Grep for numeric literals (excluding 0, 1, -1) and string literals in conditionals and assignments:
   - `if \(.* == \d{2,}` or `if \(.* === ['"]` (non-trivial comparisons)
   - Skip constants, enums, and configuration files
   - Severity: **low** for isolated cases, **medium** for systematic use
5. **Shotgun surgery**: Identify cases where a single conceptual change requires edits across many files. Grep for the same domain term appearing in >5 different modules without a shared abstraction. Severity: **medium**
6. **Primitive obsession**: Grep for function signatures with >3 parameters of the same primitive type (string, int, bool). Severity: **low**

#### Step 8 — Check Pattern Consistency

1. For each design pattern detected in Step 6, check if the same problem is solved differently elsewhere:
   - If Repository pattern is used for some data access but raw queries elsewhere, flag inconsistency
   - If DI is used in some modules but manual instantiation in others, flag inconsistency
   - If some API endpoints use middleware/decorators while others inline the same logic, flag inconsistency
2. Check error handling consistency (detailed in Step 10)
3. Severity: **medium** for inconsistencies — consistency matters more than which pattern is chosen

#### Step 9 — Check Framework Idiom Adherence

1. Read the framework profile's "Idiomatic patterns" and "Anti-patterns" sections
2. For each listed idiom, Grep for adherence or violation:
   - **React**: Grep for class components (anti-pattern if hooks are used elsewhere), direct DOM manipulation, state mutation
   - **Express/Fastify**: Grep for error handling middleware placement, route organization
   - **Django**: Grep for fat views (logic should be in models/services), raw SQL in views
   - **ASP.NET**: Grep for service registration patterns, middleware order, controller responsibilities
   - **FastAPI**: Grep for dependency injection usage, Pydantic model usage, sync vs async consistency
3. Use Context7 MCP (resolve-library-id then query-docs) to validate current best practices when the framework profile may be outdated
4. Severity: **medium** for idiom violations, **high** for deprecated/unsafe patterns

#### Step 10 — Assess Error Handling Patterns

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

### Part C — Produce Findings

#### Step 11 — Produce Findings

Follow the produce-findings template at `${CLAUDE_PLUGIN_ROOT}/references/produce-findings-template.md`. Use ID prefix `STRC-` and dimension `"structure"`.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No clear module structure | Report as info finding, suggest establishing boundaries |
| Framework not recognized | Use language profile only, skip framework-specific checks |
| Very large codebase (>1000 files) | Sample representative modules, note coverage limitation |
| Import syntax not detected | Fall back to file-level dependency analysis via directory co-location |
| Framework profile not available | Skip idiom checks (Step 9), proceed with language-level pattern detection |
| Context7 unavailable | Skip best-practice validation, rely on framework profile only |
| No clear patterns detected | Report as info finding — codebase may be too small or procedural in style |
| Mixed frameworks in project | Apply each framework's idioms to its respective files only |
| Metaprogramming or code generation | Exclude generated files from anti-pattern detection, note limitation |

## Success Checklist

- [ ] Module structure mapped with names and purposes
- [ ] Dependency graph built from import analysis
- [ ] Layering violations detected and classified by severity
- [ ] Circular dependencies detected
- [ ] Cohesion assessed per module
- [ ] Design patterns identified with locations and usage counts
- [ ] Anti-patterns detected and classified by severity
- [ ] Pattern consistency evaluated across modules
- [ ] Framework idiom adherence checked against profile
- [ ] Error handling patterns assessed for consistency and completeness
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)

## Self-Scoring & Persistence (v0.8.0)

After generating all findings, compute and include the dimension score in the response:

1. Count findings by severity (exclude info): critical, high, medium, low
2. Compute raw penalty: `raw = 3×critical + 2×high + 1×medium + 0.5×low`
3. Compute score: `score = max(1.0, 10 - min(raw, 9))`
4. Include in response header alongside findings:
   ```json
   { "dimension": "structure", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-structure.json` (overwrite if same date exists)
