---
name: scan-hook-correctness
version: 0.8.0
description: |
  This skill should be used when the user asks to "validate hooks.json", "check hook event names",
  "verify hook script paths", or when validating hooks.json schema, event names, matcher patterns,
  script existence, and security in Claude plugin hook configurations.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Hook Correctness

## Purpose

Validate the hook configuration of a Claude plugin: schema correctness, event name validity, matcher patterns, referenced script existence, and security issues in hook scripts.


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
   - If event names appear at the top level (settings format in a plugin file): emit **critical** — "hooks.json uses settings format instead of plugin wrapper format"
4. Validate the value of `"hooks"` is an object (not an array or primitive)
5. If a `"description"` field is present at the top level, validate it is a string — emit **medium** if it is another type
6. Reject JSON with trailing commas or comments (common copy-paste errors) — emit **critical** if the parser fails for this reason
7. For each event key in `"hooks"`, validate the value is an array — emit **high** if it is a bare object or primitive

### Step 3 — Validate Event Names

1. For each key in the `"hooks"` object, validate it against the **exactly 9** valid event names:
   - `PreToolUse` — before any tool runs (validation, approval, denial, input modification)
   - `PostToolUse` — after a tool completes (result inspection, feedback, logging)
   - `Stop` — when the main agent considers stopping (task completeness validation)
   - `SubagentStop` — when a subagent considers stopping (subagent task validation)
   - `SessionStart` — when a session begins (context loading, environment setup)
   - `SessionEnd` — when a session ends (cleanup, logging, state preservation)
   - `UserPromptSubmit` — when the user submits a prompt (context injection, prompt validation)
   - `PreCompact` — before context compaction (preserving critical information)
   - `Notification` — when Claude sends notifications (logging, external integrations)
2. Event name matching is **case-sensitive**: `"pretooluse"`, `"PRETOOLUSE"`, `"preToolUse"` are all invalid. Check for common near-misses (`"BeforeToolUse"`, `"OnToolCall"`, `"PreTool"`, `"SessionStop"`, `"AgentStop"`) and include a suggestion for the likely intended event
3. For each key that does not match a valid event: emit **high** finding — "Invalid hook event name: '{key}' — not a recognized Claude hook event"
4. Note the valid events detected for Step 9 reporting

### Step 4 — Validate Hook Entries

For each valid event key in `"hooks"`:

1. Each array element MUST be an object containing `"matcher"` (string) and `"hooks"` (array) — emit **high** if either is missing or wrong type
2. Validate `"matcher"` patterns:
   - Exact tool name: `"Write"`, `"Bash"` — verify casing matches built-in tool names
   - Pipe-separated: `"Read|Write|Edit"` — validate each segment is non-empty
   - Wildcard: `"*"` — valid for all events
   - Regex: `"mcp__.*__delete.*"` — attempt compilation; emit **medium** if invalid
   - Known built-in tool names for casing validation: `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `Skill`, `Agent`, `NotebookEdit`, `TodoWrite`
   - Matchers are **case-sensitive** — emit **medium** for likely casing errors on known tool names (e.g., `"write"` instead of `"Write"`)
3. For each inner hook entry in the `"hooks"` array, validate:
   - `type` field MUST be present and MUST be one of: `"prompt"`, `"command"` — **high** if missing or invalid
   - For `"prompt"` type: `prompt` field SHOULD be a non-empty string — **medium** if absent or empty
   - For `"prompt"` type: validate the event supports prompt hooks (only `PreToolUse`, `Stop`, `SubagentStop`, `UserPromptSubmit`). Emit **high** on unsupported events (e.g., `SessionStart`, `PostToolUse`)
   - For `"command"` type: `command` field MUST be a non-empty string — **high** if absent or empty
   - `timeout` field: if present, validate it is a positive number — **medium** if negative, zero, or non-numeric
4. Flag hook entries with both `prompt` and `command` fields as **medium** — "Hook entry has both 'prompt' and 'command' — only one type per entry"

### Step 5 — Verify Referenced Scripts Exist and Have Correct Permissions

For each hook entry with `type: "command"`:

1. Extract the `command` field value
2. Strip the interpreter prefix (`bash`, `python3`, `node`, `sh`) if present, then extract the script path token
3. Resolve `${CLAUDE_PLUGIN_ROOT}` to `PROJECT_PATH` for validation
4. Glob or check whether the resolved script path exists on disk
5. If the script does not exist: emit **high** finding — "Hook command references a script that does not exist: '{path}'"
6. If the script exists, verify it has execute permission when invoked directly (without an interpreter prefix). Emit **medium** — "Hook script '{path}' is not executable — add execute permission or use an explicit interpreter"
7. If the script has a shebang line, verify it is consistent with the interpreter prefix in the command field. Emit **low** if mismatched (e.g., command uses `python3` but shebang is `#!/bin/bash`)
8. Validate command paths use `${CLAUDE_PLUGIN_ROOT}` — emit **high** for hardcoded absolute paths (`/Users/`, `/home/`, `C:\`) and **medium** for relative paths (`./scripts/`) that omit the variable

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

### Step 8 — Check Hook Scripts for Security Issues

For each hook script identified in Step 6:

1. **Command injection vectors**: Grep for patterns constructing shell commands from unvalidated input:
   - `eval "$(...)"`, `eval "$(cat)"`, `` eval `...` `` — emit **critical** — "Unsafe eval of external input in hook script"
   - Unquoted variable expansion in command position (`$tool_name`, `$file_path` without quotes) — emit **high** — "Unquoted variable in shell command — potential command injection"
   - Backtick substitution with unsanitized input — emit **high**
2. **Environment variable exposure**: Grep for patterns leaking variables to external services:
   - `curl`/`wget` including `$CLAUDE_*` or `$API_KEY` in URLs or headers — emit **high** — "Environment variable exposed in external HTTP request"
   - Logging (`echo`, `printf`) of `$CLAUDE_PROJECT_DIR`, session IDs, or credential variables — emit **medium** — "Sensitive variable logged in hook script"
3. **Unsafe bash practices**: Check for defensive shell settings:
   - Absence of `set -euo pipefail` in bash scripts — emit **low** — "Hook script missing defensive shell settings (set -euo pipefail)"
4. **Network security**: Grep for plain HTTP URLs (`http://`) — emit **medium** — "Hook script uses HTTP instead of HTTPS for external request"
5. **Path traversal**: Grep for `tool_input` fields used without `..` traversal checks — emit **medium** — "Hook script does not validate against path traversal before using input"

### Step 9 — Apply Profile Ground Truth

1. Read `PLUGIN_PROFILES_DIR/hook-conventions.md` for ground truth on hook patterns
2. Apply any profile rules that promote or downgrade severity of existing findings
3. Note any additional hook patterns required by the profile that are absent

### Step 10 — Produce Findings

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
| Hook script has no execute permission | Emit medium finding with remediation advice |
| `PLUGIN_PROFILES_DIR/hook-conventions.md` not found | Skip profile override step, proceed without it |

## Success Checklist

- [ ] hooks.json detected (or absence noted)
- [ ] Schema validated: JSON parseable, wrapper format, `"description"` type
- [ ] All event names validated against the 9 valid events (case-sensitive)
- [ ] Hook entry structure validated: `"matcher"` + nested `"hooks"` array
- [ ] Matcher patterns validated (casing, regex, pipe segments)
- [ ] Hook type, prompt/command fields, and timeout validated
- [ ] Prompt hooks restricted to supported events
- [ ] Referenced scripts verified to exist with correct permissions
- [ ] Hook scripts scanned for hardcoded paths and credential patterns
- [ ] Hook scripts scanned for command injection, env variable exposure, unsafe practices
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "hook-correctness" and ID prefix HKC
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
   { "dimension": "hook-correctness", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-hook-correctness.json` (overwrite if same date exists)
