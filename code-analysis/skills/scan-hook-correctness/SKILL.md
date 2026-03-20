---
name: scan-hook-correctness
description: |
  Use when validating hooks.json schema, event names, matcher patterns, script existence, and security in Claude plugin hook configurations.
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

3. ID = HKC-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored, breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = HKC-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `HKC-8f3a21-a1b2` and `HKC-8f3a21-a1b2-2` are carried forward, a new collision gets `HKC-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-hook-correctness.json
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
