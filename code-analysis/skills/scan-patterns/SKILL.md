---
name: scan-patterns
description: |
  Detect design patterns, anti-patterns, pattern consistency, framework idiom adherence, and error handling patterns.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
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
  "id": "pattern-001",
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
