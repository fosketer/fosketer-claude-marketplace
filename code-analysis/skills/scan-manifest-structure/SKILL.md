---
name: scan-manifest-structure
version: 0.7.0
description: |
  This skill should be used when the user asks to "validate plugin.json", "check plugin manifest",
  "verify plugin directory layout", or when validating Claude plugin manifest (plugin.json), directory layout,
  naming conventions, required files, and .claude-plugin/ placement.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Manifest Structure

## Purpose

Validate the structural integrity of a Claude plugin: the `.claude-plugin/plugin.json` manifest, directory layout, naming conventions, required files, and alignment with official plugin patterns.


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
6. Validate field formats when the field is present:
   - `version`: MUST follow semver format (`/^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$/`). Emit **high** if the value is present but does not match (e.g., `"v1.0"`, `"1.0"`, `"latest"`)
   - `description`: SHOULD be between 10 and 200 characters. Emit **info** if shorter than 10 characters (likely a placeholder). Emit **info** if longer than 200 characters (may be truncated in marketplace listings)
   - `author`: SHOULD be a non-empty string. MAY contain an email in angle brackets (`Author Name <email@example.com>`)
   - `keywords`: MUST be an array of strings if present. Each keyword SHOULD be lowercase and SHOULD NOT contain spaces (use hyphens instead). Emit **medium** if `keywords` is not an array. Emit **info** if any keyword contains uppercase letters or spaces
   - `license`: SHOULD be a valid SPDX identifier if present (e.g., `"MIT"`, `"Apache-2.0"`). Emit **info** if unrecognized
   - `homepage`, `repository`: SHOULD be valid URLs if present (starting with `https://` or `http://`). Emit **info** if malformed
7. Check for unknown top-level fields in plugin.json that are not part of the recognized schema (`name`, `version`, `description`, `author`, `keywords`, `license`, `homepage`, `repository`, `dependencies`, `hooks`, `mcp`). Emit **info** for each unknown field — "Unrecognized field in plugin.json: <field>"

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
   - `references/` — optional, commonly used for shared schemas and documentation
   - `mcp-servers/` — optional, note if present (indicates plugin bundles an MCP server)
   - `commands/` — **deprecated**, emit **info** finding if present: "commands/ directory is deprecated — migrate to skills/"
2. Check that `.claude-plugin/` is placed directly under `PROJECT_PATH` (not nested deeper)
3. Flag unexpected top-level directories that are neither conventional nor documented

Acceptable directory structures:

```text
# Standard plugin with skills and agents
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── my-skill/
│       └── SKILL.md
├── agents/
│   └── my-agent.md
├── references/
└── README.md

# Hooks-only plugin (no skills or agents required — see Step 4 exception)
git-hooks-plugin/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   ├── pre-commit.sh
│   └── post-checkout.sh
└── README.md

# Plugin bundling an MCP server
mcp-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── query-data/
│       └── SKILL.md
├── mcp-servers/
│   └── server.py
└── README.md
```

Unacceptable structures (emit findings):

```text
# BAD: .claude-plugin nested inside a subdirectory
my-plugin/
├── src/
│   └── .claude-plugin/    # WRONG — must be at PROJECT_PATH root
│       └── plugin.json
└── README.md

# BAD: Mixed flat files instead of organized directories
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skill-one.md           # WRONG — skills must be in skills/<name>/SKILL.md
├── skill-two.md
└── README.md
```

### Step 4 — Check Required Files

1. Check `README.md` exists in `PROJECT_PATH` — emit **medium** finding if absent
2. Glob for at least one `skills/*/SKILL.md` OR one `agents/*.md` OR one `agents/*/AGENT.md`
   - If none found AND `hooks/` directory exists: downgrade to **info** — "Plugin provides hooks only, no skills or agents"
   - If none found AND no `hooks/` directory: emit **high** finding — "Plugin has no skills, agents, or hooks"
3. If `version` field is present in plugin.json, check whether `package.json` also exists and whether versions are in sync (info-level divergence)
4. For each skill directory under `skills/`, verify the `SKILL.md` file contains valid YAML frontmatter (delimited by `---` markers). Emit **medium** if frontmatter is missing or unparseable
5. Check that `SKILL.md` frontmatter includes `name` and `version` fields. Emit **info** if either is absent

### Step 5 — Check for Hardcoded Absolute Paths and Path Detection

1. Grep all files under `PROJECT_PATH` for hardcoded absolute path patterns:
   - `/Users/`, `/home/`, `/root/`, `C:\\Users\\`, `C:/Users/`
2. For each match: emit **high** finding — "Hardcoded absolute path detected — use \${CLAUDE_PLUGIN_ROOT} instead"
3. Exclude `.git/`, `node_modules/`, and binary files from the search
4. Verify correct `${CLAUDE_PLUGIN_ROOT}` usage across plugin files. Grep for the following patterns:
   - `${CLAUDE_PLUGIN_ROOT}/references/` — valid, standard reference path
   - `${CLAUDE_PLUGIN_ROOT}/skills/` — valid, cross-skill reference
   - `${CLAUDE_PLUGIN_ROOT}/agents/` — valid, agent reference
   - `${CLAUDE_PLUGIN_ROOT}/hooks/` — valid, hooks reference
   - `${CLAUDE_PLUGIN_ROOT}/mcp-servers/` — valid, MCP server reference
5. Flag malformed plugin root references as **medium**:
   - `$CLAUDE_PLUGIN_ROOT` without braces — MUST use `${CLAUDE_PLUGIN_ROOT}`
   - `${CLAUDE_PLUGIN_ROOT}` pointing to paths outside the plugin tree (e.g., `${CLAUDE_PLUGIN_ROOT}/../../other-plugin/`)
   - Relative paths that assume a specific working directory instead of using `${CLAUDE_PLUGIN_ROOT}` (e.g., `./references/` in a SKILL.md that should be `${CLAUDE_PLUGIN_ROOT}/references/`)
6. Count total `${CLAUDE_PLUGIN_ROOT}` references and report as info-level metadata in findings

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

## Edge Cases

### Hooks-Only Plugins

Some plugins provide only Git hooks or lifecycle hooks without any skills or agents. For these plugins:
- The `hooks/` directory MUST exist and contain at least one hook file
- Step 4 MUST NOT emit a high-severity finding for missing skills/agents — downgrade to **info**
- Verify that hook files are executable (`chmod +x`) — emit **medium** if not

### Plugins Bundling MCP Servers

Plugins MAY include an `mcp-servers/` directory containing one or more MCP server implementations. When this directory is present:
- Check that `plugin.json` includes an `mcp` top-level field describing the server configuration. Emit **medium** if the directory exists but the `mcp` field is absent
- Verify the MCP server entry point file exists at the path declared in `plugin.json`'s `mcp` field
- Check for a `requirements.txt` (Python) or `package.json` (Node.js) within `mcp-servers/` if the server has dependencies. Emit **info** if dependencies appear to be missing

### Multi-Language Plugins

Plugins MAY contain files in multiple languages (e.g., Python MCP server alongside Markdown skills). When mixed languages are detected:
- Do NOT flag the presence of multiple languages as a structural issue
- Verify that each language ecosystem's dependency file is present where expected (e.g., `requirements.txt` for Python files, `package.json` for JavaScript/TypeScript files)
- Check that `.gitignore` covers build artifacts for all detected languages. Emit **info** if common ignore patterns appear to be missing (e.g., `__pycache__/`, `node_modules/`, `dist/`)

### Monorepo-Style Plugin Collections

When `PROJECT_PATH` appears to be part of a larger monorepo (parent directory contains multiple sibling plugin directories):
- Validate only the plugin at `PROJECT_PATH` — do NOT traverse into sibling plugins
- Check that `.claude-plugin/plugin.json` references are self-contained and do not depend on sibling plugin paths
- Emit **medium** if any file references a sibling plugin via relative path (e.g., `../other-plugin/skills/`)

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| `.claude-plugin/plugin.json` does not exist | Emit critical finding, return early with that single finding |
| Invalid JSON in plugin.json | Emit critical finding, skip all further validation steps |
| `OFFICIAL_PLUGINS_INDEX_PATH` is null or unreadable | Skip Step 6 comparison, note as info finding |
| `PLUGIN_PROFILES_DIR/plugin-structure.md` not found | Skip profile cross-reference in Step 6, proceed without it |
| Plugin has no skills/ or agents/ directory at all | Emit high finding in Step 4 (unless hooks-only plugin), continue checking other dimensions |
| `mcp-servers/` exists but `mcp` field is absent in plugin.json | Emit medium finding, continue validation |
| Mixed-language plugin detected | Validate each language ecosystem independently, do not flag as structural issue |

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

## Self-Scoring & Persistence (v0.8.0)

After generating all findings, compute and include the dimension score in the response:

1. Count findings by severity (exclude info): critical, high, medium, low
2. Compute raw penalty: `raw = 3×critical + 2×high + 1×medium + 0.5×low`
3. Compute score: `score = max(1.0, 10 - min(raw, 9))`
4. Include in response header alongside findings:
   ```json
   { "dimension": "manifest-structure", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-manifest-structure.json` (overwrite if same date exists)
