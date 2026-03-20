---
name: scan-quality
description: |
  This skill should be used when detecting code duplication, complexity hotspots, dead code, naming inconsistencies, and size violations.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Quality

## Purpose

Evaluate code quality by detecting duplication, excessive complexity, dead code, naming convention violations, and file/function size violations across the codebase.

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

### Step 7 — Produce Findings

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

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Language naming conventions not in profile | Infer from majority usage in codebase, report as info |
| Generated code flagged as duplicate | Exclude files matching common generation patterns (*.generated.*, *.g.cs, *_pb2.py) |
| Very large files (>2000 lines) | Read in chunks using offset/limit, note partial analysis |
| Mixed languages in project | Apply each language's rules to its own files only |
| No functions detected (declarative code) | Skip complexity and size checks, note as info finding |

## Success Checklist

- [ ] Source files mapped and filtered (excluding tests, generated, vendor)
- [ ] Code duplication detected with locations and line counts
- [ ] Cyclomatic complexity assessed per function with thresholds applied
- [ ] Dead code candidates identified (unused exports, imports, unreachable branches)
- [ ] Naming convention adherence checked against language profile
- [ ] File and function size violations flagged with severity
- [ ] Parameter count violations flagged
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
