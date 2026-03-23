---
name: scan-convention-adherence
version: 0.7.0
description: |
  This skill should be used when detecting deprecated commands/ usage, @file anti-patterns, token budget violations, and drift from official Claude plugin conventions.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Convention Adherence

## Purpose

Detect drift from official Claude plugin conventions: deprecated directory structures, @file anti-patterns, description token budget violations, duplicate skill functionality, and structural divergence from official plugin patterns.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the plugin being analyzed
- `STACK`: { languages: ["claude-plugin"], frameworks: [] }
- `PLUGIN_PROFILES_DIR`: Path to references/plugin-profiles/
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `OFFICIAL_PLUGINS_INDEX_PATH`: Path to official plugins comparison index JSON

## Workflow

### Step 1 — Detect Deprecated commands/ Directory

1. Glob `PROJECT_PATH/commands/*.md` — collect all command files
2. For each file found: emit **medium** finding — "Deprecated commands/ entry: '{filename}' should be migrated to skills/"
3. If the `commands/` directory exists but is empty: emit **info** finding — "Empty commands/ directory present — consider removing it"
4. Record the total count of deprecated command files for Step 4 structural comparison

### Step 2 — Detect @file Anti-Patterns in Markdown Files

1. Glob all `*.md` files under `PROJECT_PATH` (exclude `.git/`, `node_modules/`)
2. Grep each file for `@file` reference patterns (e.g., `@path/to/file`, `@references/`, `@examples/`)
3. Focus specifically on SKILL.md and AGENT.md files — @file in cross-references burns context on every invocation
4. For each match in a SKILL.md or AGENT.md: emit **high** finding — "@file anti-pattern in skill/agent cross-reference burns context"
5. For each match in other .md files (README, docs): emit **info** finding — "@file reference in documentation (lower priority)"
6. Recommendation: "Replace @file references with instructions for the skill to Read the file conditionally when needed"

### Step 3 — Check Frontmatter Description Token Budget

1. Glob `PROJECT_PATH/skills/*/SKILL.md` and `PROJECT_PATH/agents/*.md` and `PROJECT_PATH/agents/*/AGENT.md`
2. For each file: read and extract YAML frontmatter
3. Compute total frontmatter character count (all frontmatter fields combined)
4. Apply the 1,024 character budget:
   - If total frontmatter length > 1,024 chars: emit **high** finding — "SKILL.md frontmatter exceeds 1,024 character budget ({actual} chars)"
   - If total frontmatter length is 900–1,024 chars: emit **medium** finding — "SKILL.md frontmatter is approaching the 1,024 character limit ({actual} chars)"
5. For description field specifically — if description alone exceeds 800 chars: emit **info** finding as an early warning

### Step 4 — Compare Against Official Plugin Conventions

1. Read `OFFICIAL_PLUGINS_INDEX_PATH` — parse JSON index of official plugin data
2. Build structural comparison between this plugin and official plugins:

   a. **Skill count**: compare this plugin's skill count against official plugin median
      - If this plugin has fewer than 30% of the official median skill count: emit **medium** finding — "Plugin has significantly fewer skills than official plugins"

   b. **Agent count**: compare agent count against official plugin distribution
      - Outlier counts (0 agents when most official plugins have agents, or vice versa): emit **info** finding

   c. **Hook adoption**: compare hooks presence against official plugin patterns
      - If official plugins commonly use hooks but this plugin has none: emit **info** finding

   d. **Directory naming**: compare directory names against official conventions
      - Unexpected directory names not found in official plugins: emit **medium** finding — "Unexpected directory '{name}' — not present in official plugin conventions"

3. Flag significant structural divergence as **medium** — "Convention drift: plugin structure diverges significantly from official plugin patterns"
4. Record specific divergences in the finding description with concrete comparisons

### Step 5 — Check for Duplicate Skill Functionality

1. Glob `PROJECT_PATH/skills/*/SKILL.md` — collect all skill files
2. For each SKILL.md: read the `description` field from frontmatter
3. Compare description trigger phrases across all skills:
   - Skills with near-identical trigger phrases (>70% word overlap): emit **medium** finding — "Potential duplicate skill functionality: '{skill-a}' and '{skill-b}' have overlapping trigger descriptions"
4. Compare skill names for overlapping semantic intent:
   - Example: `scan-quality` and `check-quality` at the same level — emit **info** finding

### Step 6 — Apply Profile Ground Truth

1. Read ALL profiles from `PLUGIN_PROFILES_DIR`:
   - `plugin-structure.md`
   - `skill-conventions.md`
   - `agent-conventions.md`
   - `hook-conventions.md`
   - `marketplace-conventions.md`
   - Any other `.md` files in the directory
2. For each profile loaded: apply any convention rules that add new findings or promote/downgrade severity of existing findings
3. If a profile explicitly lists a pattern as acceptable, downgrade any matching finding to **info**

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "CVN-e7b4a1-3f2a",
  "dimension": "convention-adherence",
  "title": "Deprecated commands/ entry: 'search.md' should be migrated to skills/",
  "description": "commands/search.md uses the deprecated commands/ directory pattern. Claude plugins should define all callable units as skills in the skills/ directory. The commands/ pattern is no longer part of the official plugin convention.",
  "severity": "medium",
  "file_path": "commands/search.md",
  "line_start": null,
  "line_end": null,
  "snippet": null,
  "recommendation": "Move commands/search.md to skills/search/SKILL.md and update the frontmatter to match the SKILL.md format",
  "effort": "medium",
  "tags": ["deprecated", "commands", "convention-drift"]
}
```

Always populate `snippet` with the relevant lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No SKILL.md or agent files found | Note as info, skip frontmatter budget and duplicate checks |
| Frontmatter YAML parse error in a file | Emit info finding for that file, skip further checks for that file |
| `OFFICIAL_PLUGINS_INDEX_PATH` is null or unreadable | Skip Step 4 comparison, note as info finding |
| Profile file not found in PLUGIN_PROFILES_DIR | Skip that profile's rules, continue with remaining profiles |
| @file Grep finds binary files | Skip binary files, analyze text files only |

## Success Checklist

- [ ] Deprecated commands/ files detected and flagged
- [ ] @file anti-patterns scanned across all .md files
- [ ] Frontmatter character budget checked against 1,024 char limit
- [ ] Official plugins index consulted for structural comparison (skill/agent/hook counts, directory naming)
- [ ] Duplicate skill functionality checked via description overlap
- [ ] All profiles from PLUGIN_PROFILES_DIR loaded and applied
- [ ] All findings use dimension: "convention-adherence" and ID prefix CVN
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
