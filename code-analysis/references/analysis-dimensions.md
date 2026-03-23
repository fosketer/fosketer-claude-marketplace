# Analysis Dimensions

> The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

Reference for the 4 standard scan dimensions used by the code-analysis plugin. Each dimension has a description, what it checks, severity levels, and language-specific considerations.

> **v0.7.0 migration**: 8 standard dimensions consolidated to 4. Migration table:
>
> | Old Dimension | New Dimension | Notes |
> |---------------|---------------|-------|
> | architecture | structure | Merged with patterns |
> | patterns | structure | Merged with architecture |
> | quality | quality | Absorbed tech-debt + performance |
> | tech-debt | quality | Absorbed into quality |
> | performance | quality | Absorbed into quality |
> | dependencies | security + testing | CVE checks → security; hygiene → testing |
> | testing | testing | Absorbed dependency hygiene |
> | security | security | Absorbed CVE vulnerability checks |

## Dimensions

### 1. Structure (`scan-structure`)

- **Purpose**: Module structure, dependency graph, layering violations, circular dependencies, design patterns, anti-patterns, pattern consistency, framework idiom adherence, error handling patterns
- **Checks**:
  - Module boundary violations (cross-layer imports)
  - Circular dependency detection
  - Dependency direction (outer -> inner only)
  - Package/namespace cohesion
  - Entry point clarity
  - Configuration separation
  - Design pattern detection (repository, factory, observer, strategy, DI, CQRS, mediator)
  - Anti-pattern detection (god class, spaghetti, golden hammer, magic numbers, shotgun surgery)
  - Pattern consistency (same problem solved differently across codebase)
  - Framework idiom adherence
  - Error handling patterns (consistent or mixed)
- **Severity**: critical (circular deps, layer violations), high (anti-patterns in core, inconsistency, cohesion issues), medium (naming, missing patterns, idiom violations)

### 2. Quality (`scan-quality`)

- **Purpose**: Code duplication, complexity, dead code, naming conventions, tech debt, performance anti-patterns
- **Checks**:
  - Duplicated code blocks (>10 lines or 3+ occurrences)
  - Cyclomatic complexity (>10 per function = warning, >20 = critical)
  - Dead code (unreachable branches, unused exports, unused imports)
  - Naming convention consistency (casing, prefixes)
  - File length (>300 lines = warning, >500 = high)
  - Function length (>50 lines = warning, >100 = high)
  - Parameter count (>5 = warning, >8 = high)
  - TODO/FIXME/HACK/XXX comments with age
  - Deprecated API usage (framework and language)
  - Legacy patterns that have modern replacements
  - Commented-out code blocks
  - N+1 query patterns (ORM loops)
  - Missing pagination on list endpoints
  - Unbounded collections in memory
  - Frontend re-render triggers (missing memo, unstable refs)
  - Bundle size concerns (large imports, no tree-shaking)
  - Missing caching for expensive operations
  - Synchronous blocking in async contexts
- **Severity**: critical (dead code in production paths, N+1 in hot paths, memory leaks), high (complexity, duplication, deprecated security APIs, missing pagination), medium (naming, length, TODOs, legacy patterns, bundle size)

### 3. Security (`scan-security`)

- **Purpose**: OWASP top 10, secrets, injection, auth gaps, CVE vulnerabilities
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
  - Known CVE vulnerabilities in dependencies
- **Severity**: critical (secrets, injection, auth bypass, known CVEs), high (XSS, CSRF), medium (logging, headers)

### 4. Testing (`scan-testing`)

- **Purpose**: Coverage gaps, test quality, missing edge cases, dependency hygiene
- **Checks**:
  - Untested public APIs/endpoints
  - Test-to-code ratio
  - Assertion quality (meaningful vs trivial)
  - Missing edge case tests (null, empty, boundary)
  - Test isolation (shared state, order-dependent)
  - Integration test coverage for external dependencies
  - Flaky test indicators (timeouts, sleep, race conditions)
  - Outdated dependencies (minor, major)
  - Unused dependencies (declared but never imported)
  - Duplicate dependencies (same purpose, different packages)
  - Version conflicts (peer dependency mismatches)
  - License compatibility
- **Severity**: critical (untested critical paths), high (missing integration tests, major outdated, unused deps), medium (assertion quality, minor outdated)

## Plugin-Specific Dimensions (--plugin mode)

These 6 dimensions are activated only when `MODE=plugin`. They validate Claude plugin structure, metadata, and marketplace consistency in addition to the standard dimensions. In plugin mode, 2 of the 4 standard dimensions are used (`quality` and `security`), giving a total of 8 dimensions.

### 5p. Manifest & Structure (`scan-manifest-structure`)

- **Purpose**: Validate plugin.json, directory layout, naming conventions
- **Checks**:
  - `plugin.json` present in `.claude-plugin/` with all required fields
  - Plugin name uses kebab-case
  - Required files present (README.md, at least one skill or agent)
  - Directory conventions followed (skills in `skills/`, agents in `agents/`)
  - `${CLAUDE_PLUGIN_ROOT}` used for all internal path references
- **Severity**: critical (invalid plugin.json), high (missing required files), medium (naming violations)

### 6p. Skill Quality (`scan-skill-quality`)

- **Purpose**: SKILL.md frontmatter quality, description triggers, progressive disclosure
- **Checks**:
  - Frontmatter contains all required fields
  - Description under 1,024 characters
  - Description starts with "Use when..." in third person
  - Trigger phrases describe invocation context, not workflow summaries
  - Word count target 1,500–2,000 words (medium severity outside range, high below 500 or above 5,000)
  - Progressive disclosure present (summary → detail → examples)
  - Resource directories referenced where appropriate
  - `allowed-tools` scoped to actual needs
- **Severity**: critical (missing SKILL.md), high (bad triggers, word count extremes), medium (style, disclosure)

### 7p. Agent Design (`scan-agent-design`)

- **Purpose**: AGENT.md frontmatter, example blocks, system prompt quality
- **Checks**:
  - Required fields present: name, description, model, color
  - Name 3–50 characters, lowercase letters and hyphens only
  - 2–4 `<example>` blocks, each with Context, user, assistant, and commentary
  - Model value is one of: inherit, sonnet, opus, haiku
  - Color value is one of: blue, cyan, green, yellow, magenta, red
  - Tool scoping avoids over-broad permissions
  - System prompt written in second person
- **Severity**: critical (missing AGENT.md), high (no examples, invalid model/color), medium (style, scoping)

### 8p. Hook Correctness (`scan-hook-correctness`)

- **Purpose**: hooks.json schema, event names, matcher patterns, script existence
- **Checks**:
  - hooks.json uses plugin wrapper format: `{"hooks": {...}}`
  - Event names are one of the 9 valid Claude hook events
  - Matcher patterns are valid regular expressions
  - Referenced scripts exist on disk
  - `${CLAUDE_PLUGIN_ROOT}` used for all script paths
  - No credentials or secrets embedded in hook definitions
- **Severity**: critical (invalid JSON), high (invalid events, missing scripts), medium (path issues)

### 9p. Marketplace Consistency (`scan-marketplace-consistency`)

- **Purpose**: Registry alignment, version consistency
- **Checks**:
  - Plugin listed in `.claude-plugin/marketplace.json`
  - Version in `plugin.json` matches `package.json` (when present)
  - Description in registry matches `plugin.json`
  - No naming conflicts with other registered plugins
  - README.md exists and is non-empty
- **Severity**: high (version mismatch, missing from registry), medium (description drift, missing README)

### 10p. Convention Adherence (`scan-convention-adherence`)

- **Purpose**: Deprecated patterns, token budgets, official plugin pattern drift
- **Checks**:
  - `commands/` directory deprecated — no equivalent skill/agent replacement
  - `@file` anti-patterns in skill descriptions
  - Skill or agent description exceeds 1,024 characters
  - Significant drift from official Claude plugin patterns
  - Duplicate functionality with another registered plugin
- **Severity**: high (deprecated commands/ with no equivalent), medium (drift, @file patterns)

## Severity Scale

| Level | Description | Action Required |
|-------|-------------|-----------------|
| critical | Active risk or breakage | Immediate fix required |
| high | Significant quality/maintainability impact | Fix in current sprint |
| medium | Improvement opportunity | Plan for near-term |
| low | Nice-to-have | Backlog |
| info | Observation, no action needed | Informational only |

## Priority Tier Assignment

Every finding MUST be assigned a `priority_tier` during reconciliation using these rules:

| Tier | Assignment Rule |
|------|-----------------|
| `immediate` | Security critical (any), injection/auth-bypass/hardcoded-secrets findings |
| `sprint-1` | All other critical findings, security high, structure critical |
| `sprint-2` | High severity (non-security), medium severity (structural) |
| `backlog` | Medium severity (style/naming), low, info |

**Application order**: Apply the first matching rule top-to-bottom. Security dimension findings use the top two tiers preferentially.

### Plugin-Specific Priority Tiers (--plugin mode)

When `MODE=plugin`, these rules take precedence for the 6 plugin-specific dimensions. Adapted general dimensions continue to use the general rules above.

| Tier | Plugin-Mode Assignment Rule |
|------|-----------------------------|
| `immediate` | Security: hardcoded secrets in hooks. Manifest: invalid plugin.json |
| `sprint-1` | Broken dependencies, hook schema errors, marketplace version mismatch |
| `sprint-2` | Skill quality issues, agent design issues, convention drift |
| `backlog` | Word count outside targets, minor naming violations, deprecated commands/ still functional |
