---
name: scan-architecture
description: |
  Analyze module structure, dependency graph, layering violations, and circular dependencies.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
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
  "id": "arch-001",
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
