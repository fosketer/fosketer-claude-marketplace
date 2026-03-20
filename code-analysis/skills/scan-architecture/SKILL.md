---
name: scan-architecture
description: |
  Use when analyzing module structure, dependency graph, layering violations, and circular dependencies.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Architecture

## Purpose

Analyze the codebase's module structure, dependency graph, layering, and detect circular dependencies or boundary violations.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null

## Workflow

### Step 1 — Map Module Structure

1. Use Glob to enumerate top-level directories and identify module boundaries
2. Read the framework profile's "Architecture expectations" for expected structure
3. Document each module: name, purpose (inferred from naming/content), approximate file count
4. Flag unexpected top-level directories that don't match the framework's expected layout

### Step 2 — Build Dependency Graph

1. For each module, scan import/require/using/include statements:
   - **Python**: `import X`, `from X import Y` — use Grep with pattern `^(import |from \S+ import)`
   - **TypeScript/JS**: `import ... from`, `require(` — use Grep with pattern `(import .+ from|require\()`
   - **C#**: `using X;` — use Grep with pattern `^using \S+;`
   - **Rust**: `use X;`, `mod X;` — use Grep with pattern `^(use |mod )`
   - **Go**: `import "X"` or `import (` blocks — use Grep with pattern `import`
   - **Dart**: `import 'X';` — use Grep with pattern `^import `
2. Classify each dependency as: internal (same project), external (package), or standard library
3. Build a module-to-module adjacency list from internal dependencies

### Step 3 — Detect Layering Violations

1. Read the framework profile for expected dependency direction (e.g., presentation → business → data)
2. Check for reverse-direction imports (e.g., data layer importing from presentation)
3. Flag imports that bypass layers (e.g., presentation directly accessing data)
4. Severity: **critical** for reverse-direction, **high** for layer-skipping

### Step 4 — Detect Circular Dependencies

1. Using the adjacency list from Step 2, detect cycles using DFS
2. For each cycle found, record: modules involved, specific import paths
3. Severity: **critical** for all circular dependencies

### Step 5 — Assess Cohesion

1. For each module, check that files within it share a common concern
2. Flag modules with files that have widely divergent import patterns
3. Flag modules with mixed concerns (e.g., UI components alongside data access)
4. Severity: **medium**

### Step 6 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "ARCH-e7b4a1-3f2a",
  "dimension": "architecture",
  "title": "Circular dependency between modules X and Y",
  "description": "...",
  "severity": "critical",
  "file_path": "src/module_x/service.py",
  "line_start": 5,
  "line_end": 5,
  "snippet": "from module_y import SomeClass",
  "recommendation": "Extract shared interface to a common module",
  "effort": "medium",
  "tags": ["circular-dependency", "module-boundary"]
}
```

Always populate `snippet` with the relevant code lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No clear module structure | Report as info finding, suggest establishing boundaries |
| Framework not recognized | Use language profile only, skip framework-specific checks |
| Very large codebase (>1000 files) | Sample representative modules, note coverage limitation |
| Import syntax not detected | Fall back to file-level dependency analysis via directory co-location |

## Success Checklist

- [ ] Module structure mapped with names and purposes
- [ ] Dependency graph built from import analysis
- [ ] Layering violations detected and classified by severity
- [ ] Circular dependencies detected
- [ ] Cohesion assessed per module
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

3. ID = ARCH-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored (e.g., 40-360 line shifts across iterations), breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = ARCH-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `ARCH-8f3a21-a1b2` and `ARCH-8f3a21-a1b2-2` are carried forward, a new collision gets `ARCH-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-architecture.json
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
