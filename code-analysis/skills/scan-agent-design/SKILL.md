---
name: scan-agent-design
version: 0.8.0
description: |
  This skill should be used when the user asks to "evaluate agent definitions", "check AGENT.md format",
  "validate agent example blocks", or when evaluating AGENT.md frontmatter format, example blocks,
  model/color validity, system prompt quality, and tool scoping in Claude plugins.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Agent Design

## Purpose

Evaluate the design quality of every agent definition in a Claude plugin: frontmatter validity, example block presence and format, model and color field correctness, system prompt quality, and tool scoping appropriateness.


## Input

- `PROJECT_PATH`: Root directory of the plugin being analyzed
- `STACK`: { languages: ["claude-plugin"], frameworks: [] }
- `PLUGIN_PROFILES_DIR`: Path to references/plugin-profiles/
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `OFFICIAL_PLUGINS_INDEX_PATH`: Path to official plugins comparison index JSON

## Workflow

### Step 1 — Inventory All Agents

1. Glob `PROJECT_PATH/agents/*.md` — collect flat agent files
2. Glob `PROJECT_PATH/agents/*/AGENT.md` — collect directory-style agent files
3. Combine both lists, deduplicating by resolved path
4. If no agent files found: return a single **info** finding — "No agent files found in agents/" and stop

### Step 2 — Parse and Validate Frontmatter

For each agent file discovered in Step 1:

1. Read the file and extract YAML frontmatter (content between the first `---` delimiters)
2. Validate `name` field:
   - MUST be present — **high** if missing
   - MUST be 3–50 characters long — **medium** if outside range
   - MUST use lowercase letters, numbers, and hyphens only — **medium** if not
   - MUST start and end with an alphanumeric character (pattern: `/^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/`) — **medium** if not
3. Validate `description` field:
   - MUST be present — **high** if missing
   - MUST begin with triggering conditions (e.g., "Use this agent when...") — **medium** if absent
   - MUST contain at least one `<example>` block — **high** if absent (see Step 3 for detailed example validation)
4. Validate `model` field:
   - If present, MUST be one of: `inherit`, `sonnet`, `opus`, `haiku` — **high** if invalid value
   - If absent: **info** finding — "model not specified; will inherit from parent context"
5. Validate `color` field:
   - If present, MUST be one of: `blue`, `cyan`, `green`, `yellow`, `magenta`, `red` — **medium** if invalid value
   - If absent: **info** finding — "color not specified; default color will be used"

**Compliant frontmatter example:**

```yaml
name: code-reviewer
description: Use this agent when the user asks to review code quality or analyze changes.

<example>
Context: User requests code review
user: "Review this function for quality issues"
assistant: "I'll use the code-reviewer agent to analyze the function."
<commentary>Direct review request triggers the agent.</commentary>
</example>

model: inherit
color: blue
tools: ["Read", "Grep", "Glob"]
```

**Non-compliant frontmatter examples:**

```yaml
# Missing name, vague description, invalid model and color
description: Helps with stuff.
model: gpt-4
color: orange
```

```yaml
# Name starts with hyphen, no examples in description, overly generic
name: -my_helper-
description: This agent reviews code.
model: inherit
color: blue
```

### Step 3 — Validate Example Blocks

For each agent file:

1. Count `<example>` blocks in the `description` field or body
2. If fewer than 2 `<example>` blocks: emit **high** finding — "Agent has fewer than 2 example blocks (found: N)"
3. For each `<example>` block, validate the required structure:
   - MUST contain a context statement (e.g., "Context:", "When:", or equivalent introductory sentence)
   - MUST contain a `user:` turn
   - MUST contain an `assistant:` turn
   - SHOULD contain a `<commentary>` block explaining the agent's reasoning — **info** if absent
4. Validate that example `user:` turns are natural-language requests (not commands or code) — **info** if they appear mechanical
5. Validate that examples cover diverse scenarios — emit **info** if all examples share identical phrasing patterns

**Well-formed example block:**

```
<example>
Context: User has finished writing a new module and wants feedback
user: "Can you check this parser module for code quality issues?"
assistant: "I'll use the code-reviewer agent to analyze the parser module."
<commentary>
Explicit review request on a specific module triggers the code-reviewer agent.
</commentary>
</example>
```

**Malformed example blocks (each triggers a finding):**

```
<example>
user: "review code"
</example>
# Missing Context, missing assistant turn, missing commentary
# user turn is terse and mechanical — emit info finding
```

```
<example>
Context: User wants a review
assistant: "I'll review the code."
</example>
# Missing user turn — emit medium finding
```

### Step 4 — Validate System Prompt Body

For each agent file:

1. Extract the body content (after the closing `---` of frontmatter)
2. Check that the body uses second-person voice — it SHOULD begin with "You are..." — emit **medium** finding if it does not
3. Check that the body is non-empty — emit **high** finding if the body has fewer than 50 words
4. Grep the body for first-person "I am..." or "I will..." constructs that suggest wrong-person narration — emit **info** per occurrence
5. Validate structural sections — apply the following heuristics:
   - Check for an output format section (heading or bold text containing "Output Format", "Return Format", or "Response Structure") — emit **medium** if absent
   - Check for a quality standards section ("Quality Standards", "Quality Criteria", or equivalent) — emit **info** if absent
   - Check for a responsibilities or workflow section ("Responsibilities", "Process", "Workflow") — emit **medium** if absent
   - Check for edge-case or error-handling guidance — emit **info** if absent
6. Validate voice consistency throughout the body — scan for mixed voice patterns where second-person ("You") and first-person ("I") co-occur, indicating incomplete editing — emit **medium** per file if detected

### Step 5 — Validate Tool Scoping

For each agent file:

1. Check whether the frontmatter includes a `tools` array
2. If `tools` is absent: emit **medium** finding — "Agent does not declare a tools array — tool access is unrestricted"
3. If `tools` is an empty array (`[]`): emit **info** finding — "Agent declares no tools — verify this is intentional"
4. If `tools` contains every available tool or a wildcard: emit **medium** finding — "Agent tool list is overly broad — scope to tools the agent actually needs"
5. Cross-reference the tools listed against the agent's system prompt body — flag tools mentioned in the body but not in the `tools` array as **medium** ("Tool used in system prompt but not declared in tools array")
6. Detect common over-broad patterns and emit **medium** findings:
   - Read-only analysis agent that includes `Write` or `Bash` — "Write-capable tools granted to a read-only agent; restrict to `[\"Read\", \"Grep\", \"Glob\"]`"
   - Agent body contains no file-modification language but declares `Write` — "Write tool declared but system prompt implies read-only behavior"
   - Agent that lists `Bash` without explicit shell-command guidance in the body — "Bash tool granted without usage constraints in the system prompt"
7. Detect common under-scoped patterns and emit **info** findings:
   - Agent body references searching or grepping files but `Grep` is not in the `tools` array — "System prompt references search operations but Grep is not declared"
   - Agent body references reading files but `Read` is not in the `tools` array — "System prompt references file reading but Read is not declared"

### Step 6 — Validate Color Semantics

For each agent file that declares a `color` field:

1. Infer the agent's primary role from its `name`, `description`, and system prompt body
2. Cross-reference the declared color against the semantic color table:
   - `blue` — analysis, review, investigation, research
   - `cyan` — data processing, secondary analysis, transformation
   - `green` — generation, building, creation, success-oriented tasks
   - `yellow` — validation, linting, quality checks, caution
   - `red` — security review, critical operations, high-stakes decisions
   - `magenta` — documentation, creative generation, explanation
3. Emit **info** finding if the color does not align with the agent's inferred role — e.g., a security-focused agent colored `green` or a code-generation agent colored `red`
4. Across the full plugin, check for color uniqueness — if all agents share the same color value, emit **medium** finding: "All agents use the same color — assign distinct colors to aid visual identification"
5. SHOULD NOT assign `red` to non-security, non-critical agents — emit **info** if `red` is used for routine tasks

### Step 7 — Compare Against Official Plugins

1. Read `OFFICIAL_PLUGINS_INDEX_PATH` — parse JSON index of official plugin agent data
2. Compare example block count distribution against official agents — flag if this plugin's agents average fewer than the official median
3. Compare model selections against official defaults — flag unusual or uncommon selections as **info**
4. Read `PLUGIN_PROFILES_DIR/agent-conventions.md` for ground truth
5. Apply any profile overrides to promote or downgrade severity of existing findings

### Step 8 — Produce Findings

Follow the produce-findings template at `${CLAUDE_PLUGIN_ROOT}/references/produce-findings-template.md`. Use ID prefix `AGT-` and dimension `"agent-design"`.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No agent files found | Return single info finding, stop |
| Frontmatter YAML parse error | Emit high finding for that file, skip further checks for that file |
| Body is entirely frontmatter (no body section) | Emit high finding — "Agent file has no system prompt body" |
| `OFFICIAL_PLUGINS_INDEX_PATH` is null or unreadable | Skip Step 7 comparison, note as info finding |
| `PLUGIN_PROFILES_DIR/agent-conventions.md` not found | Skip profile override step, proceed without it |

## Success Checklist

- [ ] All agent files inventoried (both flat and directory-style)
- [ ] Frontmatter parsed and validated (name, description, model, color)
- [ ] Example block count and format validated (minimum 2, with context/user/assistant/<commentary>)
- [ ] System prompt body validated for second-person voice, minimum length, and structural sections
- [ ] Tool scoping checked (tools array present, not overly broad, not under-scoped)
- [ ] Color semantics validated (role alignment, cross-agent uniqueness)
- [ ] Official plugins index consulted for pattern comparison
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "agent-design" and ID prefix AGT
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
   { "dimension": "agent-design", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-agent-design.json` (overwrite if same date exists)
