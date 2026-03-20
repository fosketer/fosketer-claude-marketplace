---
name: scan-dependencies
description: |
  This skill should be used when auditing project dependencies for outdated versions, vulnerabilities, unused packages, duplicates, and version conflicts.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
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
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `MODE`: "plugin" when running in plugin analysis mode, absent otherwise
- `PLUGIN_PROFILES_DIR`: Path to `references/plugin-profiles/` (only when MODE=plugin)

### Mode Branch

If `MODE=plugin`: skip Steps 1–6 (package dependencies). Execute Plugin Dependencies steps instead.

### Plugin Dependencies Steps (MODE=plugin only)

#### Step P1 — Scan Cross-References
1. Grep all .md files for skill references by name (e.g., "invoke the writing-plans skill", "use superpowers:brainstorming")
2. Build a dependency graph: which skills reference which other skills/plugins

#### Step P2 — Scan @file Includes
1. Grep for @ file path references
2. Verify each referenced file exists (Glob)
3. Flag broken references: severity **high**

#### Step P3 — Scan MCP Server Dependencies
1. Read .claude-plugin/plugin.json for mcpServers declarations
2. Verify MCP server configurations are valid
3. Flag missing or misconfigured: severity **high**

#### Step P4 — Scan Intra-Plugin References
1. Grep for ${CLAUDE_PLUGIN_ROOT} usage in all files
2. Verify each path resolves to an existing file
3. Flag broken internal references: severity **high**

#### Step P5 — Produce Findings
Compile findings array with dimension: "dependencies".

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
  "id": "DEP-e7b4a1-3f2a",
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

Always populate `snippet` with the relevant code lines when `line_start` is provided.

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

3. ID = DEP-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored (e.g., 40-360 line shifts across iterations), breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = DEP-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `DEP-8f3a21-a1b2` and `DEP-8f3a21-a1b2-2` are carried forward, a new collision gets `DEP-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-dependencies.json
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
