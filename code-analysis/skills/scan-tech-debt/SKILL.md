---
name: scan-tech-debt
description: |
  This skill should be used when detecting TODO markers, deprecated API usage, legacy patterns, migration opportunities, and commented-out code.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Tech Debt

## Purpose

Analyze the codebase for accumulated technical debt including TODO markers, deprecated API usage, legacy patterns with modern replacements, migration opportunities, removable compatibility shims, and commented-out code blocks.

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

If `MODE=plugin`:
- Execute Step 1 (TODO markers) normally but scoped to `.md` and `.sh` files
- Skip Steps 2–4 (language-specific deprecated APIs). Execute Plugin Tech Debt steps instead.

### Plugin Tech Debt Steps (MODE=plugin only)

#### Step P1 — Detect Deprecated commands/ Usage
1. Glob commands/*.md — each file is a finding
2. Severity: **high** if command has no equivalent skill, **medium** if skill equivalent exists
3. Recommendation: "Migrate command to skills/<name>/SKILL.md per plugin-dev conventions"

#### Step P2 — Detect Legacy Format Patterns
1. Grep for manifest.json at plugin root (legacy — should be .claude-plugin/plugin.json)
2. Grep for disable-model-invocation in skill frontmatter (legacy command field)
3. Grep for argument-hint in skill frontmatter (command-era field)
4. Severity: **medium** for each legacy pattern

#### Step P3 — Detect Stale Documentation
1. Check if README.md references a version that doesn't match plugin.json version
2. Check for references to removed skills/agents (Grep for names, Glob to verify existence)
3. Severity: **low** for stale docs

## Workflow

### Step 1 — Grep for TODO Markers

1. Grep across all source files (excluding `node_modules`, `dist`, `bin`, `obj`, vendor directories) for debt markers:
   - Patterns: `TODO`, `FIXME`, `HACK`, `XXX`, `WORKAROUND`, `TEMPORARY`, `TECH.?DEBT`
2. Categorize each marker:
   - **FIXME/HACK/XXX**: Known defects or workarounds — severity **high**
   - **TODO**: Planned improvements — severity **medium**
   - **WORKAROUND/TEMPORARY**: Intentional shortcuts awaiting resolution — severity **medium**
3. Count totals per category and per module/directory
4. Flag files with more than 5 markers as high-debt hotspots

### Step 2 — Scan for Deprecated API Usage

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

### Step 3 — Detect Legacy Patterns

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

### Step 4 — Check for Migration Opportunities

1. Read project configuration files to detect current versions:
   - `package.json` (Node/TypeScript), `*.csproj` (C#), `pyproject.toml` / `setup.py` (Python), `go.mod` (Go), `pubspec.yaml` (Dart)
2. Check framework version against FRAMEWORK_PROFILE for known migration paths:
   - React class components in React 16+ projects (migrate to hooks)
   - .NET 6/7 projects that could target .NET 8/9 (LTS benefits)
   - Python 3.9/3.10 projects that could use 3.11/3.12 features (performance, `tomllib`, `ExceptionGroup`)
3. Identify compatibility shims and polyfills that MAY be removable:
   - `core-js` polyfills for features supported by minimum browser targets
   - `.browserslistrc` / `targets` entries for EOL browsers
   - Python `__future__` imports no longer needed for minimum version
   - `six` library usage (Python 2 compatibility)
4. Severity: **medium** for version upgrade opportunities, **low** for removable polyfills

### Step 5 — Detect Pinned Dependency Versions

1. Scan dependency files for pinned versions that SHOULD be reviewed:
   - `package.json`: exact versions without `^` or `~` (intentional but worth auditing)
   - `requirements.txt` / `Pipfile`: pinned to specific minor/patch without range
   - `*.csproj`: `Version="x.y.z"` without floating range
2. Flag dependencies pinned to versions more than 2 major versions behind current (if detectable from package metadata)
3. Severity: **low** for auditing reminders, **medium** for significantly outdated pins

### Step 6 — Find Commented-Out Code Blocks

1. Grep for multi-line comment blocks that contain code patterns:
   - Blocks of 3+ consecutive commented lines containing code syntax (assignments, function calls, imports, conditionals)
   - **Python**: consecutive `#` lines with code patterns (not docstrings)
   - **TypeScript/JS**: `/* ... */` blocks or consecutive `//` lines with code patterns
   - **C#**: `/* ... */` blocks or consecutive `//` lines with code patterns
2. Exclude license headers, documentation comments, and intentional examples
3. Severity: **low** for small blocks (3-10 lines), **medium** for large blocks (>10 lines)

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "DEBT-e7b4a1-3f2a",
  "dimension": "tech-debt",
  "title": "23 TODO/FIXME markers in auth module",
  "description": "...",
  "severity": "medium",
  "file_path": "src/auth/",
  "line_start": null,
  "line_end": null,
  "snippet": "# TODO: implement token refresh\n# FIXME: race condition on concurrent login",
  "recommendation": "Triage markers: convert FIXMEs to tracked issues, resolve or remove stale TODOs",
  "effort": "medium",
  "tags": ["todo-markers", "debt-hotspot"]
}
```

Always populate `snippet` with the relevant code lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| Language/framework version not detectable | Skip migration opportunity checks, note limitation |
| No dependency manifest found | Skip pinned version checks |
| Very large codebase (>1000 files) | Sample high-traffic modules first, note coverage limitation |
| Mixed language monorepo | Run language-specific patterns for each detected language independently |
| Comment style ambiguous (code vs documentation) | Err on the side of inclusion, add `"confidence": "low"` note |

## Success Checklist

- [ ] TODO/FIXME/HACK/XXX markers counted and categorized
- [ ] Deprecated API usage detected per language and framework
- [ ] Legacy patterns with modern replacements identified
- [ ] Migration opportunities assessed from version analysis
- [ ] Compatibility shims and removable polyfills flagged
- [ ] Pinned dependency versions audited
- [ ] Commented-out code blocks detected
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
