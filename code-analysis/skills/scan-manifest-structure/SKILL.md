---
name: scan-manifest-structure
description: |
  This skill should be used when validating Claude plugin manifest (plugin.json), directory layout, naming conventions, required files, and .claude-plugin/ placement.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Manifest Structure

## Purpose

Validate the structural integrity of a Claude plugin: the `.claude-plugin/plugin.json` manifest, directory layout, naming conventions, required files, and alignment with official plugin patterns.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the plugin being analyzed
- `STACK`: { languages: ["claude-plugin"], frameworks: [] }
- `PLUGIN_PROFILES_DIR`: Path to references/plugin-profiles/
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `OFFICIAL_PLUGINS_INDEX_PATH`: Path to official plugins comparison index JSON

## Workflow

### Step 1 — Read and Validate plugin.json

1. Read `PROJECT_PATH/.claude-plugin/plugin.json`
2. If not found: emit **critical** finding MNF — "Missing .claude-plugin/plugin.json" and abort further steps
3. Validate JSON is parseable — if not: emit **critical** finding and abort
4. Check required fields:
   - `name`: MUST be present — **high** if missing
5. Check recommended fields — **medium** if any of the following are missing:
   - `version`, `description`, `author`, `keywords`

### Step 2 — Validate Plugin Name Format

1. Extract `name` from plugin.json (skip if Step 1 found it missing)
2. Validate against kebab-case regex: `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`
3. If name does not match: emit **high** finding — "Plugin name does not follow kebab-case convention"
4. Check that the `name` value matches the plugin's directory basename — emit **medium** if they differ

### Step 3 — Validate Directory Layout

1. Glob for expected top-level directories within `PROJECT_PATH`:
   - `skills/` — expected, note if absent (info)
   - `agents/` — optional, note count if present
   - `hooks/` — optional, note if present
   - `commands/` — **deprecated**, emit **info** finding if present: "commands/ directory is deprecated — migrate to skills/"
2. Check that `.claude-plugin/` is placed directly under `PROJECT_PATH` (not nested deeper)
3. Flag unexpected top-level directories that are neither conventional nor documented

### Step 4 — Check Required Files

1. Check `README.md` exists in `PROJECT_PATH` — emit **medium** finding if absent
2. Glob for at least one `skills/*/SKILL.md` OR one `agents/*.md` OR one `agents/*/AGENT.md`
   - If none found: emit **high** finding — "Plugin has no skills or agents"
3. If `version` field is present in plugin.json, check whether `package.json` also exists and whether versions are in sync (info-level divergence)

### Step 5 — Check for Hardcoded Absolute Paths

1. Grep all files under `PROJECT_PATH` for hardcoded absolute path patterns:
   - `/Users/`, `/home/`, `/root/`, `C:\\Users\\`, `C:/Users/`
2. For each match: emit **high** finding — "Hardcoded absolute path detected — use \${CLAUDE_PLUGIN_ROOT} instead"
3. Exclude `.git/` and `node_modules/` from the search

### Step 6 — Compare Against Official Plugins

1. Read `OFFICIAL_PLUGINS_INDEX_PATH` — parse JSON index of official plugin structures
2. For each official plugin entry, compare:
   - Whether this plugin has the same mandatory top-level directories
   - Whether `.claude-plugin/plugin.json` placement is consistent
3. Flag structural divergences that differ from the majority of official plugins as **medium** — "Directory layout diverges from official plugin conventions"
4. Read `PLUGIN_PROFILES_DIR/plugin-structure.md` for ground truth on expected layout
5. Cross-reference any profile rules against current findings — promote or downgrade severity if profile overrides apply

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "MNF-e7b4a1-3f2a",
  "dimension": "manifest-structure",
  "title": "Plugin name does not follow kebab-case convention",
  "description": "The name field in .claude-plugin/plugin.json is 'MyPlugin', which does not match /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/",
  "severity": "high",
  "file_path": ".claude-plugin/plugin.json",
  "line_start": 3,
  "line_end": 3,
  "snippet": "\"name\": \"MyPlugin\"",
  "recommendation": "Rename to 'my-plugin' to follow kebab-case convention",
  "effort": "low",
  "tags": ["naming", "manifest", "kebab-case"]
}
```

Always populate `snippet` with the relevant lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| `.claude-plugin/plugin.json` does not exist | Emit critical finding, return early with that single finding |
| Invalid JSON in plugin.json | Emit critical finding, skip all further validation steps |
| `OFFICIAL_PLUGINS_INDEX_PATH` is null or unreadable | Skip Step 6 comparison, note as info finding |
| `PLUGIN_PROFILES_DIR/plugin-structure.md` not found | Skip profile cross-reference in Step 6, proceed without it |
| Plugin has no skills/ or agents/ directory at all | Emit high finding in Step 4, continue checking other dimensions |

## Success Checklist

- [ ] `.claude-plugin/plugin.json` read and validated (required + recommended fields)
- [ ] Plugin name validated against kebab-case regex
- [ ] Directory layout checked (skills/, agents/, hooks/, commands/ deprecated)
- [ ] Required files confirmed (README.md, at least one SKILL.md or agent .md)
- [ ] Hardcoded absolute paths scanned and flagged
- [ ] Official plugins index consulted for structural comparison
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "manifest-structure" and ID prefix MNF
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
