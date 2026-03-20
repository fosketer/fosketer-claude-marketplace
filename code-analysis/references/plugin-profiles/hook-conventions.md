# Hook Conventions Reference Profile

Ground truth for hooks.json plugin format, valid events, hook types, matcher syntax, path rules, security constraints, and execution behavior. Derived from official `plugin-dev` hook-development skill conventions.

---

## 1. Plugin hooks.json Format

Plugins define hooks in `hooks/hooks.json` using the **plugin wrapper format**. This is distinct from the user settings format.

### 1.1 Plugin Wrapper Format (Required for Plugins)

```json
{
  "description": "Brief explanation of hooks (optional)",
  "hooks": {
    "PreToolUse": [...],
    "Stop": [...],
    "SessionStart": [...]
  }
}
```

**Key rules**:
- The `"hooks"` wrapper object is **required** for plugin format
- Event names go inside `"hooks"`, not at the top level
- `"description"` field is optional
- This is the **only correct format** for `hooks/hooks.json` in a plugin

### 1.2 Settings Format (Direct — for User Settings Only)

For reference: the user settings format places events directly at the top level. **Do not use this format in plugin hooks.json files.**

```json
{
  "PreToolUse": [...],
  "Stop": [...]
}
```

### 1.3 Full Plugin hooks.json Example

```json
{
  "description": "Validation hooks for code quality",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/validate.sh",
            "timeout": 30
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Verify task completion: tests run, build succeeded, questions answered. Return 'approve' to stop or 'block' with reason to continue."
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-context.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

---

## 2. The 9 Valid Hook Events

| Event | When It Fires | Primary Use Cases |
|-------|--------------|-------------------|
| `PreToolUse` | Before any tool runs | Validate, approve, deny, or modify tool calls |
| `PostToolUse` | After tool completes | React to results, feedback, logging |
| `Stop` | When main agent considers stopping | Validate task completeness |
| `SubagentStop` | When a subagent considers stopping | Validate subagent task completion |
| `SessionStart` | When Claude Code session begins | Load context, set environment variables |
| `SessionEnd` | When session ends | Cleanup, logging, state preservation |
| `UserPromptSubmit` | When user submits a prompt | Add context, validate, or block prompts |
| `PreCompact` | Before context compaction | Preserve critical information |
| `Notification` | When Claude sends notifications | Logging, external integrations |

**Exactly these 9 event names are valid**. Any other event name is invalid and will be ignored or cause errors.

---

## 3. Hook Types

### 3.1 Prompt-Based Hooks (Recommended)

Use LLM-driven decision making for context-aware validation.

```json
{
  "type": "prompt",
  "prompt": "Evaluate if this tool use is appropriate: $TOOL_INPUT",
  "timeout": 30
}
```

**Supported events**: Stop, SubagentStop, UserPromptSubmit, PreToolUse

**Benefits**:
- Context-aware decisions based on natural language reasoning
- Flexible evaluation logic without bash scripting
- Better edge case handling
- Easier to maintain and extend

**When to use**: Complex validation logic, judgment calls, context-dependent decisions.

### 3.2 Command Hooks

Execute bash commands for deterministic checks.

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
  "timeout": 60
}
```

**Use for**:
- Fast deterministic validations
- File system operations
- External tool integrations
- Performance-critical checks

**When to use**: Binary checks, performance-critical paths, integrations with external tools that have CLIs.

### 3.3 Default Timeouts

| Hook Type | Default Timeout |
|-----------|----------------|
| Command hook | 60 seconds |
| Prompt hook | 30 seconds |

Always set explicit `"timeout"` values for command hooks in production plugins.

---

## 4. Hook Event Structure

Each event in the `"hooks"` object contains an array of hook definitions. Each definition has a `"matcher"` and a nested `"hooks"` array:

```json
{
  "EventName": [
    {
      "matcher": "MatchPattern",
      "hooks": [
        {
          "type": "prompt|command",
          "prompt": "...",     // for prompt type
          "command": "...",    // for command type
          "timeout": 30        // optional
        }
      ]
    }
  ]
}
```

Note the nested use of `"hooks"` key at two levels:
1. Top-level `"hooks"` wrapper (plugin format)
2. Per-event `"hooks"` array (individual hook definitions)

---

## 5. Matcher Syntax

Matchers filter which tool calls or events trigger the hook.

### 5.1 Match Patterns

**Exact match** — single tool name:
```json
"matcher": "Write"
```

**Multiple tools** — pipe-separated:
```json
"matcher": "Read|Write|Edit"
```

**Wildcard** — all tools/events:
```json
"matcher": "*"
```

**Regex patterns**:
```json
"matcher": "mcp__.*__delete.*"
```

### 5.2 Common Matcher Patterns

```json
// All MCP tools
"matcher": "mcp__.*"

// Specific plugin's MCP tools
"matcher": "mcp__plugin_asana_.*"

// All file operations
"matcher": "Read|Write|Edit"

// Bash commands only
"matcher": "Bash"

// All destructive MCP operations
"matcher": "mcp__.*__delete.*"
```

**Important**: Matchers are **case-sensitive**. `"write"` will not match `"Write"`.

---

## 6. `${CLAUDE_PLUGIN_ROOT}` — Required for All Paths

All paths in hook commands **MUST** use `${CLAUDE_PLUGIN_ROOT}`. This is not optional.

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh"
}
```

**Why required**: Plugins install in different locations per user, OS, and installation method. Hardcoded absolute paths break across environments.

**Forbidden path patterns**:
- Hardcoded absolute: `"/Users/name/plugins/my-plugin/scripts/validate.sh"` — FORBIDDEN
- Relative from cwd: `"./scripts/validate.sh"` — UNRELIABLE in hook context
- Home directory: `"~/plugins/validate.sh"` — FORBIDDEN

**Correct patterns**:
- `"bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh"` — correct
- `"python3 ${CLAUDE_PLUGIN_ROOT}/scripts/process.py"` — correct
- `"node ${CLAUDE_PLUGIN_ROOT}/servers/server.js"` — correct

---

## 7. Hook Output Formats

### 7.1 Standard Output (All Hooks)

```json
{
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "Message for Claude"
}
```

- `continue`: If `false`, halt processing (default `true`)
- `suppressOutput`: Hide output from transcript (default `false`)
- `systemMessage`: Message shown to Claude as additional context

### 7.2 PreToolUse Output

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow|deny|ask",
    "updatedInput": {"field": "modified_value"}
  },
  "systemMessage": "Explanation for Claude"
}
```

- `permissionDecision`: `"allow"` approves; `"deny"` blocks; `"ask"` prompts user
- `updatedInput`: Optional modified tool input parameters

### 7.3 Stop / SubagentStop Output

```json
{
  "decision": "approve|block",
  "reason": "Explanation",
  "systemMessage": "Additional context"
}
```

- `decision`: `"approve"` allows stopping; `"block"` continues the agent with reason
- `reason`: Explanation shown to the agent when blocking

### 7.4 Exit Codes (Command Hooks)

| Exit Code | Behavior |
|-----------|----------|
| `0` | Success — stdout shown in transcript |
| `2` | Blocking error — stderr fed back to Claude |
| Other | Non-blocking error |

---

## 8. Hook Input Format (stdin)

All hooks receive JSON via stdin with these common fields:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/current/working/dir",
  "permission_mode": "ask|allow",
  "hook_event_name": "PreToolUse"
}
```

**Event-specific additional fields**:

| Event | Additional Fields |
|-------|------------------|
| PreToolUse / PostToolUse | `tool_name`, `tool_input`, `tool_result` |
| UserPromptSubmit | `user_prompt` |
| Stop / SubagentStop | `reason` |

Access in prompt hooks: `$TOOL_INPUT`, `$TOOL_RESULT`, `$USER_PROMPT`

---

## 9. Available Environment Variables (Command Hooks)

| Variable | Description | Always Available |
|----------|-------------|-----------------|
| `$CLAUDE_PROJECT_DIR` | Project root path | Yes |
| `$CLAUDE_PLUGIN_ROOT` | Plugin directory | Yes |
| `$CLAUDE_CODE_REMOTE` | Set if running in remote context | When remote |
| `$CLAUDE_ENV_FILE` | Path to persist env vars | SessionStart only |

**SessionStart special capability**: Persist environment variables for the session:
```bash
echo "export PROJECT_TYPE=nodejs" >> "$CLAUDE_ENV_FILE"
```

---

## 10. Security Rules

### 10.1 No Hardcoded Credentials

Never hardcode API keys, passwords, tokens, or secrets in hook commands or prompts.

Wrong:
```json
{"command": "bash script.sh --api-key abc123secret"}
```

Correct:
```json
{"command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/script.sh"}
```
(script reads credentials from environment variables)

### 10.2 HTTPS/WSS Only for External Calls

If hook scripts make network calls, use HTTPS or WSS. HTTP or WS is not permitted in production hooks.

### 10.3 Input Validation in Command Hooks

Always validate inputs before using them:

```bash
#!/bin/bash
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name')

# Validate tool name format
if [[ ! "$tool_name" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo '{"decision": "deny", "reason": "Invalid tool name"}' >&2
  exit 2
fi
```

### 10.4 Quote All Bash Variables

```bash
# Correct: quoted
echo "$file_path"
cd "$CLAUDE_PROJECT_DIR"

# Wrong: unquoted (injection risk)
echo $file_path
cd $CLAUDE_PROJECT_DIR
```

### 10.5 Path Traversal Prevention

```bash
file_path=$(echo "$input" | jq -r '.tool_input.file_path')

# Deny path traversal
if [[ "$file_path" == *".."* ]]; then
  echo '{"decision": "deny", "reason": "Path traversal detected"}' >&2
  exit 2
fi
```

### 10.6 Log Sanitization

Do not log sensitive information (environment variables, credentials, user prompt content) from hooks.

---

## 11. Parallel Execution Behavior

All matching hooks run **in parallel**. This is a fundamental constraint of the hooks system.

```json
{
  "PreToolUse": [
    {
      "matcher": "Write",
      "hooks": [
        {"type": "command", "command": "check1.sh"},   // Runs in parallel
        {"type": "command", "command": "check2.sh"},   // Runs in parallel
        {"type": "prompt", "prompt": "Validate..."}    // Runs in parallel
      ]
    }
  ]
}
```

**Design implications**:
- Hooks do not see each other's output
- Execution order is non-deterministic
- Design each hook to be independent
- Do not rely on one hook's result in another

---

## 12. Hook Lifecycle Rules

### 12.1 Hooks Load at Session Start

Changes to `hooks/hooks.json` do NOT take effect during an active session. To apply hook changes:
1. Edit hook configuration or scripts
2. Exit the Claude Code session
3. Restart: `claude` or `cc`
4. New hook configuration loads on next session

**Cannot hot-swap hooks** — this is a hard architectural constraint, not a bug.

### 12.2 Plugin Hooks Merge with User Hooks

Plugin hooks merge with the user's own hooks and run in parallel. They do not override or replace user hooks.

### 12.3 Validation at Startup

Hooks are validated when Claude Code starts:
- Invalid JSON in `hooks.json` causes loading failure
- Missing scripts cause warnings
- Syntax errors reported in debug mode

---

## 13. Proven Hook Patterns

### Pattern: Security Validation (PreToolUse)

```json
{
  "PreToolUse": [{
    "matcher": "Write|Edit",
    "hooks": [{
      "type": "prompt",
      "prompt": "File path: $TOOL_INPUT.file_path. Verify: 1) Not in /etc or system directories 2) Not .env or credentials 3) Path doesn't contain '..' traversal. Return 'approve' or 'deny'."
    }]
  }]
}
```

### Pattern: Test Enforcement (Stop)

```json
{
  "Stop": [{
    "matcher": "*",
    "hooks": [{
      "type": "prompt",
      "prompt": "Review transcript. If code was modified (Write/Edit tools used), verify tests were executed. If no tests were run, block with reason 'Tests must be run after code changes'."
    }]
  }]
}
```

### Pattern: Context Loading (SessionStart)

```json
{
  "SessionStart": [{
    "matcher": "*",
    "hooks": [{
      "type": "command",
      "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/load-context.sh"
    }]
  }]
}
```

### Pattern: MCP Operation Monitoring (PreToolUse)

```json
{
  "PreToolUse": [{
    "matcher": "mcp__.*__delete.*",
    "hooks": [{
      "type": "prompt",
      "prompt": "Deletion operation detected. Verify: Is this deletion intentional? Can it be undone? Are there backups? Return 'approve' only if safe."
    }]
  }]
}
```

---

## 14. Validation Checklist

**Format**:
- [ ] Plugin hooks.json uses wrapper format: `{"hooks": {"EventName": [...]}}`
- [ ] `"hooks"` wrapper key is present (not events at top level)
- [ ] `"description"` field, if present, is a string

**Event names**:
- [ ] All event names are from the 9 valid events exactly
- [ ] No typos in event names (case-sensitive: `PreToolUse` not `pretooluse`)

**Hook definitions**:
- [ ] Each event entry has `"matcher"` and `"hooks"` array
- [ ] Each hook has `"type"` field (`"prompt"` or `"command"`)
- [ ] Prompt hooks have `"prompt"` field (string)
- [ ] Command hooks have `"command"` field (string)

**Paths**:
- [ ] All command paths use `${CLAUDE_PLUGIN_ROOT}` (not hardcoded absolute paths)
- [ ] No `~/` paths in commands
- [ ] No `./` relative paths in hook commands (use `${CLAUDE_PLUGIN_ROOT}` instead)

**Security**:
- [ ] No hardcoded credentials in commands or prompts
- [ ] No HTTP URLs (only HTTPS/WSS for external calls)
- [ ] Bash scripts quote all variables
- [ ] Bash scripts validate input before use

**JSON validity**:
- [ ] Valid JSON (no syntax errors, no trailing commas, no comments)
- [ ] All strings properly quoted
- [ ] Arrays and objects properly closed

---

## 15. Common Non-Compliance Patterns

| Issue | Severity | Description |
|-------|----------|-------------|
| Events at top level (settings format in plugin file) | Critical | Plugin format requires `{"hooks": {...}}` wrapper |
| Invalid event name (e.g., `"BeforeToolUse"`) | Critical | Only 9 valid event names exist |
| Hardcoded absolute path in command | Critical | Breaks on any other installation |
| `~/` path in command | Critical | Breaks in non-interactive contexts |
| Hardcoded credentials in command string | Critical | Security violation |
| Missing `"hooks"` wrapper | Critical | Plugin format requirement |
| `"type"` field absent | Major | Hook type required |
| Prompt hook on unsupported event | Major | Prompt type only for: Stop, SubagentStop, UserPromptSubmit, PreToolUse |
| Non-quoted variables in bash scripts | Major | Injection risk |
| No timeout on long-running command hooks | Minor | May block Claude Code sessions |
| HTTP URL in hook script | Minor | Should use HTTPS |
| Logging sensitive information | Minor | Security hygiene |
