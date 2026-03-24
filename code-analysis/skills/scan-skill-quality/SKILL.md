---
name: scan-skill-quality
version: 0.8.0
description: |
  This skill should be used when the user asks to "evaluate SKILL.md quality", "check skill descriptions",
  "validate progressive disclosure", or when evaluating SKILL.md frontmatter quality, description triggers,
  word counts, progressive disclosure, and resource organization in Claude plugins.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Skill Quality

## Purpose

Evaluate the quality of every SKILL.md in a Claude plugin: frontmatter completeness, description trigger phrasing, body word counts, progressive disclosure practices, allowed-tools scoping, and whether large inline content has been appropriately externalized.


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
2. If the YAML block fails to parse (invalid syntax, unclosed quotes, bad indentation): emit **high** finding for that file and skip remaining checks for it
3. Validate **required** fields — `name` and `description`:
   - Both MUST be present — **high** if either is missing
4. Validate **recommended** fields — `version` and `allowed-tools`:
   - `version`, if present, MUST follow semver `MAJOR.MINOR.PATCH` (pre-release suffixes permitted) — **medium** if malformed
   - `version` absent: emit **info** finding — "No version field; recommended for change tracking"
   - `allowed-tools`, if present, MUST be a JSON array of strings — **medium** if malformed
5. Validate `name` field format:
   - MUST match kebab-case regex: `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/` — **medium** if not
   - MUST NOT use generic identifiers (`helper`, `utils`, `misc`, `skill1`) — **medium** if detected
   - SHOULD match the parent directory name — **info** if they differ
6. Validate `description` field — trigger phrase analysis:
   - MUST start with "Use when..." or "This skill should be used when..." — **medium** if not
   - MUST be written in third person (no first-person "I" subject, no second-person "you" address) — **medium** if violated
   - MUST contain at least one specific quoted trigger phrase (text in double quotes representing user intent) — **medium** if absent
   - SHOULD contain three or more distinct trigger phrases to cover phrasing variations — **info** if fewer
   - MUST NOT use vague trigger phrases like "working with code", "help with files", or "general tasks" — **medium** if detected
   - Total frontmatter character length (all fields combined) MUST be < 1,024 chars — **high** if exceeded

**Good vs bad description examples for reference during analysis**:

Good — dense trigger phrases, third person, specific intent:
```yaml
description: This skill should be used when the user asks to "scan skill quality", "validate SKILL.md", "check frontmatter compliance", or "audit plugin skills".
```

Bad — vague, no triggers, wrong person:
```yaml
description: Provides guidance for working with skills.
# No trigger phrases, not third person, too vague to activate reliably
```

Bad — second person, missing quoted triggers:
```yaml
description: Use this skill when you want to check skill files.
# Second person "you", no specific quoted trigger phrases
```

### Step 3 — Count Body Words and Check Size

For each SKILL.md:

1. Extract the body: all content after the closing `---` delimiter of the frontmatter block. The frontmatter consists of exactly two `---` lines; the body begins on the line following the second `---`.
2. Count words in the body. "Body" includes all prose, headings, list items, and text inside code blocks. Exclude:
   - The frontmatter block itself (between the two `---` delimiters)
   - Fenced code block delimiters (the ` ``` ` lines themselves, but count the code content within)
   - Pure whitespace lines
3. For multi-part SKILL.md files that contain both instructional prose and large embedded JSON/YAML examples: count all words including those inside code blocks. Large examples inflate word count and SHOULD be extracted to supporting files regardless.
4. Apply thresholds:
   - **Target range**: 1,500–2,000 words — no finding
   - **Outside range** (< 1,500 or > 2,000): **medium** finding — "Skill body word count outside target range (target: 1,500–2,000)"
   - **Below 500 words**: **high** finding — "Skill body is too short to be useful (< 500 words)"
   - **Above 3,000 words without a `references/` directory**: **medium** finding — "Skill body exceeds 3,000 words with no references/ directory — extract detailed content"
   - **Above 5,000 words**: **high** finding — "Skill body is excessively long (> 5,000 words) — split or extract to supporting files"
5. Include the exact word count in every finding's `description` field for actionability

### Step 4 — Check for @file Anti-Pattern and Validate Progressive Disclosure

For each SKILL.md:

1. Grep the body for `@file` references using the pattern `@[a-zA-Z0-9_./-]+` (e.g., `@path/to/file.md`, `@references/`, `@skill-name`)
2. For each match: emit **high** finding — "@file reference in SKILL.md body burns context on every invocation"
3. Recommendation: "Move referenced content to supporting files in references/ or examples/ and instruct the skill to Read them conditionally"
4. Validate progressive disclosure compliance — check that the three-level loading model is respected:
   - **Level 1 (metadata)**: Verify frontmatter description is self-contained and does not depend on body content to determine activation
   - **Level 2 (body)**: Verify the body contains only what Claude needs on every invocation. Detect inline content that belongs at Level 3 by scanning for these patterns:
     - Configuration templates or schema definitions embedded directly in the body (detect by fenced blocks with `json`, `yaml`, `toml`, `xml` language hints exceeding 15 lines)
     - API endpoint listings or parameter tables exceeding 10 rows
     - Step-by-step tutorials longer than 500 words that serve reference rather than procedural purposes
   - **Level 3 (bundled resources)**: If the skill directory contains `references/` or `examples/`, verify the SKILL.md body includes conditional load instructions (e.g., "Read `references/patterns.md` when..." or "Consult `references/advanced.md` for...")
5. For Level 2 violations (content that belongs at Level 3): emit **medium** finding — "Inline content better suited to references/ — extract to preserve progressive disclosure"

### Step 5 — Validate allowed-tools

For each SKILL.md:

1. Check whether the frontmatter includes an `allowed-tools` field
2. If the skill body mentions using tools (Read, Grep, Glob, Bash, Edit, Write) AND `allowed-tools` is absent: emit **medium** finding — "Skill uses tools but does not declare allowed-tools"
3. If `allowed-tools` contains `"*"` or an excessively broad list (all tools when only 1-2 are needed): emit **medium** finding — "allowed-tools is overly broad — scope to tools actually used"
4. If `allowed-tools` is present but empty (`[]`): emit **info** finding — "allowed-tools is empty — verify this skill intentionally uses no tools"

### Step 6 — Check Supporting File Organization

For each SKILL.md:

1. Check sibling supporting directories: `references/`, `examples/`, `scripts/`, `assets/`
2. Grep the SKILL.md body for large inline content candidates using these detection patterns:
   - **Code blocks**: Count lines between matching ` ``` ` fences. Flag blocks longer than 30 lines.
   - **Tables**: Count rows containing `|` pipe characters in contiguous sequences. Flag tables with more than 15 data rows (excluding the header separator row).
   - **JSON or YAML blocks**: Identify fenced blocks with `json`, `yaml`, or `yml` language hints. Flag blocks larger than 20 lines.
   - **Repeated patterns**: Detect three or more structurally similar code blocks (same language hint, similar length) that could be consolidated into a single reference file with sections.
3. For each large inline content block found: emit **medium** finding — "Large inline content block should be extracted to a supporting file in references/ or examples/"
4. Check if supporting directories exist but are empty: emit **info** finding per empty directory
5. Verify that every existing supporting directory is referenced in the SKILL.md body. An unreferenced `references/` or `examples/` directory is a compliance failure — emit **medium** finding: "Supporting directory exists but is not referenced in SKILL.md body"
6. Verify that every file path referenced in SKILL.md actually exists on disk. A reference to a nonexistent file: emit **high** finding — "Referenced supporting file does not exist"

**When `references/` is needed**: Create a `references/` directory when the SKILL.md body exceeds 2,000 words and contains detailed reference material (API specs, schema definitions, pattern catalogs, configuration templates) that Claude does not need on every invocation. The `references/` directory enables Level 3 progressive disclosure — content loads only when Claude determines it is needed.

**Naming conventions for supporting files**:
- Use kebab-case with `.md` extension for documentation: `patterns.md`, `api-reference.md`, `advanced-techniques.md`
- Use descriptive kebab-case with appropriate extension for scripts: `validate-schema.sh`, `parse-frontmatter.py`
- Use purpose-first naming: `output-schemas.md` not `schemas-for-output.md`
- Avoid generic names: `notes.md`, `misc.md`, `temp.md` — **info** finding if detected

### Step 7 — Compare Against Official Plugins

1. Read `OFFICIAL_PLUGINS_INDEX_PATH` — parse JSON index of official plugin skill data
2. Extract word count distribution and description trigger patterns from official plugins
3. Compare this plugin's skill word counts against official median:
   - If average word count is less than 50% of official median: **medium** finding — "Skill bodies are significantly shorter than official plugins"
4. Compare description trigger phrasing against official patterns — flag systematic divergence as **info**
5. Read `PLUGIN_PROFILES_DIR/skill-conventions.md` for ground truth
6. Apply any profile overrides to promote or downgrade severity of existing findings

### Step 8 — Produce Findings

Follow the produce-findings template at `${CLAUDE_PLUGIN_ROOT}/references/produce-findings-template.md`. Use ID prefix `SKL-` and dimension `"skill-quality"`.

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
- [ ] Frontmatter parsed and validated (required: name, description; recommended: version, allowed-tools)
- [ ] Description trigger phrases analyzed (person, specificity, quoted triggers, vagueness)
- [ ] Body word counts checked against thresholds (target 1,500–2,000)
- [ ] @file anti-patterns detected and flagged
- [ ] Progressive disclosure levels validated (metadata, body, bundled resources)
- [ ] allowed-tools validated for presence and scope
- [ ] Large inline content blocks identified for extraction (code, tables, JSON/YAML)
- [ ] Supporting file organization verified (existence, references, naming conventions)
- [ ] Official plugins index consulted for word count and pattern comparison
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "skill-quality" and ID prefix SKL
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
   { "dimension": "skill-quality", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-skill-quality.json` (overwrite if same date exists)
