---
name: scan-hook-correctness
description: |
  This skill should be used when validating hooks.json schema, event names, matcher patterns, script existence, and security in Claude plugin hook configurations.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Hook Correctness

## Purpose

Validate the hook configuration of a Claude plugin: schema correctness, event name validity, matcher patterns, referenced script existence, and security issues in hook scripts.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

**Note:** This skill does NOT use `OFFICIAL_PLUGINS_INDEX_PATH`. That parameter may be null or absent and MUST be ignored.

## Input

- `PROJECT_PATH`: Root directory of the plugin being analyzed
- `STACK`: { languages: ["claude-plugin"], frameworks: [] }
- `PLUGIN_PROFILES_DIR`: Path to references/plugin-profiles/
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `OFFICIAL_PLUGINS_INDEX_PATH`: **Not used by this skill.** This parameter is accepted for interface consistency but MUST be ignored.

## Workflow

### Step 1 — Detect hooks.json

1. Glob `PROJECT_PATH/hooks/hooks.json`
2. If not found: hooks are optional in Claude plugins — return empty findings array (no issues)
3. If found: proceed to Step 2

### Step 2 — Validate hooks.json Schema

1. Read `PROJECT_PATH/hooks/hooks.json`
2. Validate the file is parseable JSON — if not: emit **critical** finding — "hooks.json is not valid JSON" and stop
3. Validate top-level structure is an object with a `"hooks"` key:
   - `{ "hooks": { ... } }` is the required wrapper format
   - If the structure is a bare array or missing the `"hooks"` key: emit **high** finding — "hooks.json must use the {\"hooks\": {...}} wrapper format"
4. Validate the value of `"hooks"` is an object (not an array or primitive)

### Step 3 — Validate Event Names

1. For each key in the `"hooks"` object, validate it against the 9 valid event names:
   - `PreToolUse`
   - `PostToolUse`
   - `Stop`
   - `SubagentStop`
   - `SessionStart`
   - `SessionEnd`
   - `UserPromptSubmit`
   - `PreCompact`
   - `Notification`
2. For each key that does not match a valid event: emit **high** finding — "Invalid hook event name: '{key}' — not a recognized Claude hook event"
3. Note the valid events detected for Step 8 reporting

### Step 4 — Validate Hook Entries

For each valid event key in `"hooks"`:

1. Read the hook entries array (or single entry) for that event
2. For each hook entry, validate:
   - `type` field MUST be present and MUST be one of: `"prompt"`, `"command"` — **high** if missing or invalid
   - `matcher` field: if present, validate it is a valid regex — attempt to parse it as a regex pattern; emit **medium** if it cannot be compiled
   - For `"prompt"` type: `prompt` field SHOULD be present — **medium** if absent
   - For `"command"` type: `command` field MUST be present — **high** if absent
3. Flag hook entries with both `prompt` and `command` fields as **medium** — "Hook entry has both 'prompt' and 'command' fields — only one type is valid per entry"

### Step 5 — Verify Referenced Scripts Exist

For each hook entry with `type: "command"`:

1. Extract the `command` field value
2. Parse the script path from the command (first token before any arguments)
3. Glob or check whether the script path resolves relative to `PROJECT_PATH`
4. If the script does not exist: emit **high** finding — "Hook command references a script that does not exist: '{path}'"
5. Note: paths using `${CLAUDE_PLUGIN_ROOT}` are expected — resolve them relative to `PROJECT_PATH` for validation

### Step 6 — Check Hook Scripts for Hardcoded Paths

1. Collect all script paths referenced in `command` hook entries (Step 5)
2. Glob all scripts under `PROJECT_PATH/hooks/` (shell scripts, Python scripts, etc.)
3. For each script file found: Grep for hardcoded absolute path patterns:
   - `/Users/`, `/home/`, `/root/`, `C:\\Users\\`, `C:/Users/`
4. For each match: emit **high** finding — "Hardcoded absolute path in hook script — use \${CLAUDE_PLUGIN_ROOT} instead"

### Step 7 — Check Hook Scripts for Credential Patterns

For each hook script identified in Step 6:

1. Grep for credential patterns:
   - `API_KEY\s*=\s*["']`, `password\s*=\s*["']`, `secret\s*=\s*["']`, `token\s*=\s*["']`
   - `AKIA[0-9A-Z]{16}` (AWS access key), `sk-[a-zA-Z0-9]{20,}` (OpenAI key)
   - `-----BEGIN (RSA |EC )?PRIVATE KEY-----`
2. Exclude known safe patterns: environment variable reads (`$ENV_VAR`, `os.environ`, `process.env`)
3. For each confirmed credential pattern: emit **critical** finding — "Hardcoded credential detected in hook script"

### Step 8 — Apply Profile Ground Truth

1. Read `PLUGIN_PROFILES_DIR/hook-conventions.md` for ground truth on hook patterns
2. Apply any profile rules that promote or downgrade severity of existing findings
3. Note any additional hook patterns required by the profile that are absent

### Step 9 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "HKC-e7b4a1-3f2a",
  "dimension": "hook-correctness",
  "title": "Invalid hook event name: 'OnToolCall'",
  "description": "hooks.json contains an event key 'OnToolCall' which is not a recognized Claude hook event. Valid events are: PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification.",
  "severity": "high",
  "file_path": "hooks/hooks.json",
  "line_start": 5,
  "line_end": 5,
  "snippet": "\"OnToolCall\": [...]",
  "recommendation": "Replace 'OnToolCall' with the correct event name, likely 'PreToolUse' or 'PostToolUse'",
  "effort": "low",
  "tags": ["hooks", "event-name", "schema"]
}
```

Always populate `snippet` with the relevant lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| `hooks/hooks.json` not found | Return empty findings array (hooks are optional) |
| Invalid JSON in hooks.json | Emit critical finding, stop further validation |
| Command hook references a script with `${CLAUDE_PLUGIN_ROOT}` | Resolve to PROJECT_PATH for existence check |
| Hook script is binary or non-text | Skip script content checks for that file, note as info |
| `PLUGIN_PROFILES_DIR/hook-conventions.md` not found | Skip profile override step, proceed without it |

## Success Checklist

- [ ] hooks.json detected (or absence noted — no finding needed)
- [ ] hooks.json validated as JSON with correct wrapper format
- [ ] All event names validated against the 9 valid Claude hook events
- [ ] Hook entry type, matcher, and command/prompt fields validated
- [ ] Referenced script files verified to exist
- [ ] Hook scripts scanned for hardcoded absolute paths
- [ ] Hook scripts scanned for credential patterns
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "hook-correctness" and ID prefix HKC
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
