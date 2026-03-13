---
name: scan-dependencies
description: |
  Audit project dependencies for outdated versions, vulnerabilities, unused packages, duplicates, and version conflicts.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
---

# Scan Dependencies

## Purpose

Audit the project's dependency manifests to identify outdated packages, known vulnerabilities, unused dependencies, duplicate packages serving the same purpose, and version conflicts.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)

## Workflow

### Step 1 — Locate and Read Manifests

1. Use Glob to find all dependency manifests in the project:
   - **Python**: `**/requirements*.txt`, `**/pyproject.toml`, `**/setup.py`, `**/setup.cfg`, `**/Pipfile`, `**/pixi.toml`
   - **TypeScript/JS**: `**/package.json` (exclude `node_modules/`)
   - **C#**: `**/*.csproj`, `**/Directory.Packages.props`, `**/global.json`
   - **Rust**: `**/Cargo.toml`
   - **Go**: `**/go.mod`, `**/go.sum`
   - **Dart**: `**/pubspec.yaml`
2. Read each manifest and extract: package name, declared version/range, whether it is a dev/test dependency
3. Build a consolidated dependency list with source manifest path for each entry

### Step 2 — Cross-Reference Imports Against Declarations

1. Grep all source files for import/require/using statements (reuse patterns from scan-architecture)
2. Map each imported package to its manifest declaration
3. Identify **unused dependencies**: declared in manifest but never imported in any source file
   - MUST exclude runtime-only dependencies that are not imported (e.g., plugins, CLI tools, type stubs)
   - For TypeScript: check both `import` statements and `/// <reference types="..." />`
   - For Python: check both `import X` and `from X import Y`, account for namespace differences (e.g., `python-dateutil` imports as `dateutil`)
4. Severity: **medium** for unused dependencies (they add install weight and attack surface)

### Step 3 — Check for Outdated Dependencies

1. Use Context7 MCP (resolve-library-id then query-docs) to look up current stable versions for key dependencies
2. If Context7 is unavailable or returns no results, use Bash to run ecosystem-specific audit commands:
   - **Node.js**: `npm outdated --json` (if package-lock.json exists)
   - **Python**: `pip list --outdated --format=json` (if virtual environment is available)
   - **C#**: `dotnet list package --outdated --format json` (if SDK is available)
3. Compare declared versions against latest stable versions
4. Classify by staleness:
   - **1 major version behind**: **medium** severity
   - **2+ major versions behind**: **high** severity
   - **Minor/patch behind only**: **low** severity
5. SHOULD note dependencies pinned to exact versions vs. ranges

### Step 4 — Check for Known Vulnerabilities

1. Use Context7 MCP to query for known security advisories on detected dependencies
2. If Context7 is unavailable, use Bash to run ecosystem-specific audit commands:
   - **Node.js**: `npm audit --json` (if package-lock.json exists)
   - **Python**: `pip-audit --format=json` or `safety check --json` (if available)
   - **C#**: `dotnet list package --vulnerable --format json` (if SDK is available)
3. For each vulnerability found, record: CVE ID (if available), affected package, severity from advisory, fixed version
4. Severity: Map from advisory severity — **critical**, **high**, **medium**, **low**

### Step 5 — Detect Duplicate Dependencies

1. Check for multiple packages serving the same purpose:
   - **HTTP clients**: `axios` + `node-fetch` + `got` (JS/TS); `requests` + `httpx` + `urllib3` (Python)
   - **Testing**: `jest` + `mocha` + `vitest` (JS/TS); `pytest` + `unittest` + `nose` (Python)
   - **Validation**: `joi` + `zod` + `yup` (JS/TS); `pydantic` + `marshmallow` + `cerberus` (Python)
   - **Logging**: `winston` + `pino` + `bunyan` (JS/TS); `logging` + `loguru` + `structlog` (Python)
   - **ORM**: `typeorm` + `prisma` + `sequelize` (JS/TS); `sqlalchemy` + `django.db` + `peewee` (Python)
2. Read the language profile for known duplicate-purpose groups
3. Severity: **low** for potential duplicates (may be intentional), **medium** if both are imported in similar contexts

### Step 6 — Detect Version Conflicts

1. For monorepos or multi-manifest projects, check if the same package is declared at different versions across manifests
2. For Node.js: check `package.json` across workspace packages for mismatched versions
3. For Python: check for conflicting version specifiers across `requirements*.txt` files
4. For C#: check for version mismatches when `Directory.Packages.props` is not used (central package management)
5. Severity: **high** for conflicting ranges that cannot resolve, **medium** for mismatched but compatible versions

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "deps-001",
  "dimension": "dependencies",
  "title": "Known vulnerability in lodash@4.17.15",
  "description": "CVE-2021-23337: lodash 4.17.15 is vulnerable to command injection via template(). Fixed in 4.17.21.",
  "severity": "high",
  "file_path": "package.json",
  "line_start": 12,
  "line_end": 12,
  "snippet": "\"lodash\": \"^4.17.15\"",
  "recommendation": "Upgrade lodash to >=4.17.21",
  "effort": "low",
  "tags": ["vulnerability", "CVE-2021-23337", "npm"]
}
```

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No manifest files found | Report as critical finding — project has no declared dependencies |
| Context7 unavailable | Fall back to local CLI audit tools; if also unavailable, skip version/vulnerability checks and note limitation |
| CLI audit tools not installed | Skip automated audit, rely on manifest version analysis only, note limitation |
| Lock file missing | Note as medium finding (non-reproducible builds), proceed with manifest versions |
| Private/internal packages | Skip version and vulnerability checks for packages from private registries |
| Monorepo with workspace protocol | Treat workspace references as internal, not external dependencies |

## Success Checklist

- [ ] All dependency manifests located and parsed
- [ ] Consolidated dependency list built with source paths
- [ ] Unused dependencies identified via import cross-reference
- [ ] Outdated dependencies checked against latest stable versions
- [ ] Known vulnerabilities queried (via Context7 or CLI audit)
- [ ] Duplicate-purpose packages detected
- [ ] Version conflicts across manifests identified
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator
