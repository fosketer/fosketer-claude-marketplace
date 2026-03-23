---
name: scan-skill-quality
version: 0.7.0
description: |
  This skill should be used when evaluating SKILL.md frontmatter quality, description triggers, word counts, progressive disclosure, and resource organization in Claude plugins.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Skill Quality

## Purpose

Evaluate the quality of every SKILL.md in a Claude plugin: frontmatter completeness, description trigger phrasing, body word counts, progressive disclosure practices, allowed-tools scoping, and whether large inline content has been appropriately externalized.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the plugin being analyzed
- `STACK`: { languages: ["claude-plugin"], frameworks: [] }
- `PLUGIN_PROFILES_DIR`: Path to references/plugin-profiles/
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `OFFICIAL_PLUGINS_INDEX_PATH`: Path to official plugins comparison index JSON

## Workflow

### Step 1 — Inventory All Skills

1. Glob `PROJECT_PATH/skills/*/SKILL.md` — collect all skill files
2. If no SKILL.md files found: return a single **info** finding — "No SKILL.md files found in skills/" and stop
3. Record the total count for comparison against official plugins later

### Step 2 — Parse and Validate Frontmatter

For each SKILL.md discovered in Step 1:

1. Read the file and extract YAML frontmatter (content between the first `---` delimiters)
2. Validate `name` field:
   - MUST be present — **high** if missing
   - MUST match kebab-case: `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/` — **medium** if not
   - SHOULD match the parent directory name — **info** if they differ
3. Validate `description` field:
   - MUST be present — **high** if missing
   - MUST start with "Use when..." or "This skill should be used when..." — **medium** if not
   - MUST be written in third person (no first-person "I" subject) — **medium** if violated
   - Total frontmatter length (name + description + any other fields) MUST be < 1,024 chars — **high** if exceeded

### Step 3 — Count Body Words and Check Size

For each SKILL.md:

1. Extract the body (content after the closing `---` of frontmatter)
2. Count words in the body
3. Apply thresholds:
   - **Target range**: 1,500–2,000 words — no finding
   - **Outside range** (< 1,500 or > 2,000): **medium** finding — "Skill body word count outside target range (target: 1,500–2,000)"
   - **Below 500 words**: **high** finding — "Skill body is too short to be useful (< 500 words)"
   - **Above 5,000 words**: **high** finding — "Skill body is excessively long (> 5,000 words) — split or extract to supporting files"

### Step 4 — Check for @file Anti-Pattern

For each SKILL.md:

1. Grep the body for `@file` references (e.g., `@path/to/file.md`, `@references/`)
2. For each match: emit **high** finding — "@file reference in SKILL.md body burns context on every invocation"
3. Recommendation: "Move referenced content to supporting files in references/ or examples/ and instruct the skill to Read them conditionally"

### Step 5 — Validate allowed-tools

For each SKILL.md:

1. Check whether the frontmatter includes an `allowed-tools` field
2. If the skill body mentions using tools (Read, Grep, Glob, Bash, Edit, Write) AND `allowed-tools` is absent: emit **medium** finding — "Skill uses tools but does not declare allowed-tools"
3. If `allowed-tools` contains `"*"` or an excessively broad list (all tools when only 1-2 are needed): emit **medium** finding — "allowed-tools is overly broad — scope to tools actually used"
4. If `allowed-tools` is present but empty (`[]`): emit **info** finding — "allowed-tools is empty — verify this skill intentionally uses no tools"

### Step 6 — Check Supporting File Organization

For each SKILL.md:

1. Check sibling supporting directories: `references/`, `examples/`, `scripts/`
2. Grep the SKILL.md body for large inline content candidates:
   - Code blocks longer than 30 lines
   - Tables with more than 15 rows
   - JSON or YAML blocks larger than 20 lines
3. For each large inline content block found: emit **medium** finding — "Large inline content block should be extracted to a supporting file in references/ or examples/"
4. Check if supporting directories exist but are empty: emit **info** finding per empty directory

### Step 7 — Compare Against Official Plugins

1. Read `OFFICIAL_PLUGINS_INDEX_PATH` — parse JSON index of official plugin skill data
2. Extract word count distribution and description trigger patterns from official plugins
3. Compare this plugin's skill word counts against official median:
   - If average word count is less than 50% of official median: **medium** finding — "Skill bodies are significantly shorter than official plugins"
4. Compare description trigger phrasing against official patterns — flag systematic divergence as **info**
5. Read `PLUGIN_PROFILES_DIR/skill-conventions.md` for ground truth
6. Apply any profile overrides to promote or downgrade severity of existing findings

### Step 8 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "SKL-e7b4a1-3f2a",
  "dimension": "skill-quality",
  "title": "Skill description does not start with 'Use when...'",
  "description": "The description field in skills/analyze-repo/SKILL.md starts with 'Analyzes the repository...' instead of the required trigger phrase 'Use when...' or 'This skill should be used when...'",
  "severity": "medium",
  "file_path": "skills/analyze-repo/SKILL.md",
  "line_start": 3,
  "line_end": 4,
  "snippet": "description: |\n  Analyzes the repository structure...",
  "recommendation": "Rewrite the description to start with 'Use when you need to analyze the repository structure...'",
  "effort": "low",
  "tags": ["frontmatter", "description", "trigger-phrase"]
}
```

Always populate `snippet` with the relevant lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No SKILL.md files found | Return single info finding, stop |
| Frontmatter YAML parse error | Emit high finding for that file, skip further checks for that file |
| `OFFICIAL_PLUGINS_INDEX_PATH` is null or unreadable | Skip Step 7 comparison, note as info finding |
| `PLUGIN_PROFILES_DIR/skill-conventions.md` not found | Skip profile override step, proceed without it |
| Body word count tool unavailable | Estimate from file size (bytes / 5) with a note that it is approximate |

## Success Checklist

- [ ] All SKILL.md files inventoried
- [ ] Frontmatter parsed and validated (name, description, trigger phrase, char budget)
- [ ] Body word counts checked against thresholds (target 1,500–2,000)
- [ ] @file anti-patterns detected and flagged
- [ ] allowed-tools validated for presence and scope
- [ ] Large inline content blocks identified for extraction
- [ ] Official plugins index consulted for word count and pattern comparison
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "skill-quality" and ID prefix SKL
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
