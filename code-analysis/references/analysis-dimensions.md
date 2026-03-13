# Analysis Dimensions

> The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

Reference for the 8 scan dimensions used by the code-analysis plugin. Each dimension has a description, what it checks, severity levels, and language-specific considerations.

## Dimensions

### 1. Architecture (`scan-architecture`)

- **Purpose**: Module structure, dependency graph, layering violations, circular dependencies
- **Checks**:
  - Module boundary violations (cross-layer imports)
  - Circular dependency detection
  - Dependency direction (outer -> inner only)
  - Package/namespace cohesion
  - Entry point clarity
  - Configuration separation
- **Severity**: critical (circular deps, layer violations), high (cohesion issues), medium (naming)

### 2. Quality (`scan-quality`)

- **Purpose**: Code duplication, complexity, dead code, naming conventions
- **Checks**:
  - Duplicated code blocks (>10 lines or 3+ occurrences)
  - Cyclomatic complexity (>10 per function = warning, >20 = critical)
  - Dead code (unreachable branches, unused exports, unused imports)
  - Naming convention consistency (casing, prefixes)
  - File length (>300 lines = warning, >500 = high)
  - Function length (>50 lines = warning, >100 = high)
  - Parameter count (>5 = warning, >8 = high)
- **Severity**: critical (dead code in production paths), high (complexity, duplication), medium (naming, length)

### 3. Dependencies (`scan-dependencies`)

- **Purpose**: Outdated, vulnerable, unused, conflicting packages
- **Checks**:
  - Outdated dependencies (minor, major, security-critical)
  - Known vulnerabilities (CVE database via Context7 when available)
  - Unused dependencies (declared but never imported)
  - Duplicate dependencies (same purpose, different packages)
  - Version conflicts (peer dependency mismatches)
  - License compatibility
- **Severity**: critical (known CVEs), high (major outdated, unused), medium (minor outdated)

### 4. Patterns (`scan-patterns`)

- **Purpose**: Design pattern usage, anti-patterns, consistency
- **Checks**:
  - Design pattern detection (repository, factory, observer, strategy, DI, CQRS, mediator)
  - Anti-pattern detection (god class, spaghetti, golden hammer, magic numbers, shotgun surgery)
  - Pattern consistency (same problem solved differently across codebase)
  - Framework idiom adherence
  - Error handling patterns (consistent or mixed)
- **Severity**: critical (anti-patterns in core), high (inconsistency), medium (missing patterns)

### 5. Testing (`scan-testing`)

- **Purpose**: Coverage gaps, test quality, missing edge cases
- **Checks**:
  - Untested public APIs/endpoints
  - Test-to-code ratio
  - Assertion quality (meaningful vs trivial)
  - Missing edge case tests (null, empty, boundary)
  - Test isolation (shared state, order-dependent)
  - Integration test coverage for external dependencies
  - Flaky test indicators (timeouts, sleep, race conditions)
- **Severity**: critical (untested critical paths), high (missing integration tests), medium (assertion quality)

### 6. Performance (`scan-performance`)

- **Purpose**: N+1 queries, re-renders, memory leaks, bundle size
- **Checks**:
  - N+1 query patterns (ORM loops)
  - Missing pagination on list endpoints
  - Unbounded collections in memory
  - Frontend re-render triggers (missing memo, unstable refs)
  - Bundle size concerns (large imports, no tree-shaking)
  - Missing caching for expensive operations
  - Synchronous blocking in async contexts
- **Severity**: critical (N+1 in hot paths, memory leaks), high (missing pagination, re-renders), medium (bundle size)

### 7. Security (`scan-security`)

- **Purpose**: OWASP top 10, secrets, injection, auth gaps
- **Checks**:
  - Hardcoded secrets (API keys, passwords, tokens)
  - SQL/NoSQL injection vectors
  - XSS vulnerabilities (unsanitized output)
  - CSRF protection gaps
  - Authentication bypass risks
  - Authorization gaps (missing role checks)
  - Insecure deserialization
  - Path traversal
  - SSRF vectors
  - Sensitive data in logs
- **Severity**: critical (secrets, injection, auth bypass), high (XSS, CSRF), medium (logging, headers)

### 8. Tech Debt (`scan-tech-debt`)

- **Purpose**: TODOs, deprecated APIs, migration opportunities
- **Checks**:
  - TODO/FIXME/HACK/XXX comments with age
  - Deprecated API usage (framework and language)
  - Legacy patterns that have modern replacements
  - Migration opportunities (framework version upgrades)
  - Compatibility shims that can be removed
  - Pinned versions that should be unpinned
- **Severity**: critical (deprecated security APIs), high (deprecated core APIs), medium (TODOs, legacy patterns)

## Severity Scale

| Level | Description | Action Required |
|-------|-------------|-----------------|
| critical | Active risk or breakage | Immediate fix required |
| high | Significant quality/maintainability impact | Fix in current sprint |
| medium | Improvement opportunity | Plan for near-term |
| low | Nice-to-have | Backlog |
| info | Observation, no action needed | Informational only |
