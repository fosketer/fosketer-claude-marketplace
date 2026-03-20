---
name: scan-agent-design
description: |
  Use when evaluating AGENT.md frontmatter format, example blocks, model/color validity, system prompt quality, and tool scoping in Claude plugins.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Agent Design

## Purpose

Evaluate the design quality of every agent definition in a Claude plugin: frontmatter validity, example block presence and format, model and color field correctness, system prompt quality, and tool scoping appropriateness.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

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
   - MUST use lowercase letters and hyphens only (`/^[a-z][a-z-]*[a-z]$/`) — **medium** if not
3. Validate `description` field:
   - MUST be present — **high** if missing
   - MUST contain at least one `<example>` block — **high** if absent (see Step 3 for detailed example validation)
4. Validate `model` field:
   - If present, MUST be one of: `inherit`, `sonnet`, `opus`, `haiku` — **high** if invalid value
   - If absent: **info** finding — "model not specified; will inherit from parent context"
5. Validate `color` field:
   - If present, MUST be one of: `blue`, `cyan`, `green`, `yellow`, `magenta`, `red` — **medium** if invalid value
   - If absent: **info** finding — "color not specified; default color will be used"

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

### Step 4 — Validate System Prompt Body

For each agent file:

1. Extract the body content (after the closing `---` of frontmatter)
2. Check that the body uses second-person voice — it SHOULD begin with "You are..." — emit **medium** finding if it does not
3. Check that the body is non-empty — emit **high** finding if the body has fewer than 50 words
4. Grep the body for first-person "I am..." or "I will..." constructs that suggest wrong-person narration — emit **info** per occurrence

### Step 5 — Validate Tool Scoping

For each agent file:

1. Check whether the frontmatter includes a `tools` array
2. If `tools` is absent: emit **medium** finding — "Agent does not declare a tools array — tool access is unrestricted"
3. If `tools` is an empty array (`[]`): emit **info** finding — "Agent declares no tools — verify this is intentional"
4. If `tools` contains every available tool or a wildcard: emit **medium** finding — "Agent tool list is overly broad — scope to tools the agent actually needs"
5. Cross-reference the tools listed against the agent's system prompt body — flag tools mentioned in the body but not in the `tools` array as **medium** ("Tool used in system prompt but not declared in tools array")

### Step 6 — Compare Against Official Plugins

1. Read `OFFICIAL_PLUGINS_INDEX_PATH` — parse JSON index of official plugin agent data
2. Compare example block count distribution against official agents — flag if this plugin's agents average fewer than the official median
3. Compare model selections against official defaults — flag unusual or uncommon selections as **info**
4. Read `PLUGIN_PROFILES_DIR/agent-conventions.md` for ground truth
5. Apply any profile overrides to promote or downgrade severity of existing findings

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "AGT-e7b4a1-3f2a",
  "dimension": "agent-design",
  "title": "Agent has fewer than 2 example blocks",
  "description": "The agent defined in agents/research-agent.md contains only 1 <example> block. At least 2 are required to demonstrate diverse usage patterns.",
  "severity": "high",
  "file_path": "agents/research-agent.md",
  "line_start": 4,
  "line_end": 18,
  "snippet": "description: |\n  <example>\n  Context: ...\n  </example>",
  "recommendation": "Add a second <example> block covering a different usage scenario, including context, user turn, assistant turn, and <commentary>",
  "effort": "low",
  "tags": ["agent-design", "examples", "frontmatter"]
}
```

Always populate `snippet` with the relevant lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No agent files found | Return single info finding, stop |
| Frontmatter YAML parse error | Emit high finding for that file, skip further checks for that file |
| Body is entirely frontmatter (no body section) | Emit high finding — "Agent file has no system prompt body" |
| `OFFICIAL_PLUGINS_INDEX_PATH` is null or unreadable | Skip Step 6 comparison, note as info finding |
| `PLUGIN_PROFILES_DIR/agent-conventions.md` not found | Skip profile override step, proceed without it |

## Success Checklist

- [ ] All agent files inventoried (both flat and directory-style)
- [ ] Frontmatter parsed and validated (name, description, model, color)
- [ ] Example block count and format validated (minimum 2, with context/user/assistant/<commentary>)
- [ ] System prompt body validated for second-person voice and minimum length
- [ ] Tool scoping checked (tools array present, not overly broad)
- [ ] Official plugins index consulted for pattern comparison
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "agent-design" and ID prefix AGT
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

3. ID = AGT-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored, breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = AGT-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `AGT-8f3a21-a1b2` and `AGT-8f3a21-a1b2-2` are carried forward, a new collision gets `AGT-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-agent-design.json
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
