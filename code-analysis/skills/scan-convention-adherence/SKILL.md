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

Detect drift from official Claude plugin conventions: deprecated structures, @file anti-patterns, token budget violations, duplicate functionality, and divergence from official plugin patterns.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are interpreted as described in RFC 2119.

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
7. Validate cross-reference format — relative paths in bold backtick format (e.g., **`references/patterns.md`**) rather than `@references/patterns.md`

### Step 3 — Check Frontmatter Fields Against Profile Conventions

1. Glob `PROJECT_PATH/skills/*/SKILL.md` and `PROJECT_PATH/agents/*.md` and `PROJECT_PATH/agents/*/AGENT.md`
2. For each file: read and extract YAML frontmatter
3. Compute total frontmatter character count (all frontmatter fields combined)
4. Apply the 1,024 character budget:
   - If total frontmatter length > 1,024 chars: emit **high** finding — "SKILL.md frontmatter exceeds 1,024 character budget ({actual} chars)"
   - If total frontmatter length is 900–1,024 chars: emit **medium** finding — "SKILL.md frontmatter is approaching the 1,024 character limit ({actual} chars)"
5. For description field specifically — if description alone exceeds 800 chars: emit **info** finding as an early warning
6. Validate per-profile frontmatter requirements:

   a. **Skill frontmatter** (from `skill-conventions.md`):
      - `name` MUST be present, kebab-case, matching directory name
      - `description` MUST start with "This skill should be used when..." and include quoted trigger phrases — missing triggers is **high**
      - `version` SHOULD be present in semver format
      - `allowed-tools` MUST be a JSON array if present (e.g., `["Read", "Grep", "Bash"]`)
      - Missing `name` or `description` is **critical** — skip further checks for that file

   b. **Agent frontmatter** (from `agent-conventions.md`):
      - `name` MUST be 3–50 chars, lowercase/hyphens, start and end alphanumeric
      - `description` MUST start with "Use this agent when..." with at least one `<example>` block containing `Context:`, `user:`, `assistant:`, `<commentary>`
      - `model` MUST be `inherit`, `sonnet`, `opus`, or `haiku` — unjustified `opus`: emit **info**
      - `color` MUST be `blue`, `cyan`, `green`, `yellow`, `magenta`, or `red`
      - `tools`, if present, MUST be a JSON array

   c. **Manifest fields** (from `plugin-structure.md` and `marketplace-conventions.md`):
      - `plugin.json` `name` MUST match regex `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`
      - `version` MUST follow semver if present — `"1.0"` or `"v1.0.0"` are non-compliant
      - Component path overrides MUST use `./` prefix relative paths
      - Marketplace entry `name` MUST match `plugin.json` `name`; `plugin.json` `version` MUST match `package.json` `version` when both exist

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

   e. **Manifest completeness**: compare `plugin.json` field coverage against official plugins
      - If this plugin omits more than two of `description`, `author`, `keywords`, `homepage`: emit **info** finding — "Plugin manifest lacks metadata fields common in official plugins ({missing_fields})"

   f. **Progressive disclosure adoption**: check skills with >2,000 words in SKILL.md body
      - If no `references/` directory exists alongside a verbose SKILL.md: emit **medium** finding — "SKILL.md exceeds 2,000 words without references/ — use progressive disclosure"

   g. **Supporting directory documentation**: verify `references/`, `examples/`, `scripts/`, `assets/` directories are mentioned in their parent SKILL.md
      - Unreferenced supporting directory: emit **medium** finding — "Supporting directory '{dir}' exists but is not referenced in SKILL.md"

3. Flag significant structural divergence as **medium** — "Convention drift: plugin structure diverges significantly from official plugin patterns"
4. Record specific divergences in the finding description with concrete comparisons

### Step 5 — Check for Duplicate Skill Functionality

1. Glob `PROJECT_PATH/skills/*/SKILL.md` — collect all skill files
2. For each SKILL.md: read the `description` field from frontmatter
3. Extract trigger phrases from each description — identify quoted phrases and key verb-noun pairs
4. Compare trigger phrases across all skill pairs using Jaccard similarity scoring:

   a. **Tokenize**: split each description into normalized lowercase words, removing stop words (a, the, is, when, this, should, be, used)
   b. **Compute Jaccard similarity**: for each pair (A, B), calculate `|A ∩ B| / |A ∪ B|`
   c. **Severity thresholds**:
      - Jaccard > 0.70: emit **medium** — "Overlapping trigger descriptions: '{skill-a}' and '{skill-b}' (score: {score})"
      - Jaccard 0.50–0.70: emit **info** — "Moderate overlap between '{skill-a}' and '{skill-b}' (score: {score})"
      - Jaccard < 0.50: no finding
   d. **Quoted phrase collision**: extract double-quoted phrases from each description; if two skills share an identical quoted trigger phrase, emit **high** regardless of Jaccard score — "Identical trigger phrase '{phrase}' in '{skill-a}' and '{skill-b}' — one skill will shadow the other"

5. Compare skill names for overlapping semantic intent — skills sharing the same primary verb or noun (e.g., `scan-quality` / `check-quality`): emit **info** finding
6. Apply the same Jaccard comparison to agent descriptions; agents with identical `<example>` user prompts: emit **medium**

### Step 6 — Cross-File Consistency Validation

Perform cross-file consistency checks across all skills and agents in the plugin:

1. **`allowed-tools` format**: collect `allowed-tools` from every SKILL.md; verify all use JSON array syntax `["Read", "Grep"]` not YAML list syntax. Mixed formats: emit **medium** finding
2. **Version field presence**: if any SKILL.md includes `version`, ALL MUST include it. Mixed presence: emit **info** finding
3. **Description person**: all skill descriptions MUST use "This skill should be used when..." and all agent descriptions MUST use "Use this agent when...". A single deviation: emit **medium** finding
4. **Tool name capitalization**: tool names in `allowed-tools` and agent `tools` MUST use official casing (`Read` not `read`, `Bash` not `bash`). Incorrect casing: emit **medium** finding
5. **Naming uniformity**: all skill directory names and agent file names MUST use kebab-case. Underscores, camelCase, or uppercase: emit **high** finding

### Step 7 — Apply Profile Ground Truth

1. Read ALL profiles from `PLUGIN_PROFILES_DIR`:
   - `plugin-structure.md`
   - `skill-conventions.md`
   - `agent-conventions.md`
   - `hook-conventions.md`
   - `marketplace-conventions.md`
   - Any other `.md` files in the directory
2. For each profile loaded: apply any convention rules that add new findings or promote/downgrade severity of existing findings
3. If a profile explicitly lists a pattern as acceptable, downgrade any matching finding to **info**
4. Apply profile-specific drift detection:

   a. **Skill body drift**: Grep SKILL.md bodies for "you should", "you need to", "you must", "you can" — each match is **medium** (imperative voice violation)
   b. **Agent body drift**: Grep agent bodies for first-person ("I am...", "I will...") — each match is **medium** (must use second-person)
   c. **Hook format drift**: verify `hooks/hooks.json` uses plugin wrapper format `{"hooks": {...}}`; verify event names are from the 9 valid events; verify command paths use `${CLAUDE_PLUGIN_ROOT}`
   d. **Marketplace drift**: verify `marketplace.json` `name` matches `plugin.json` `name`; verify `source` paths use `./` prefix; verify no duplicate plugin names

### Step 8 — Produce Findings

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
| No SKILL.md or agent files found | Note as info, skip frontmatter, duplicate, and cross-file checks |
| Frontmatter YAML parse error | Emit info finding, skip further checks for that file |
| `OFFICIAL_PLUGINS_INDEX_PATH` null or unreadable | Skip Step 4, note as info |
| Profile file not found | Skip that profile's rules, continue with others |
| @file Grep finds binary files | Skip binary files |
| Only one skill in the plugin | Skip Jaccard comparison, continue remaining checks |
| `hooks/hooks.json` absent | Skip hook drift checks, note as info if official plugins use hooks |
| `marketplace.json` absent | Skip marketplace drift checks |

## Success Checklist

- [ ] Deprecated commands/ files detected and flagged
- [ ] @file anti-patterns scanned across all .md files with cross-reference format validation
- [ ] Frontmatter fields validated per profile category (skill, agent, manifest)
- [ ] Frontmatter character budget checked against 1,024 char limit
- [ ] Official plugins index consulted for structural comparison and progressive disclosure adoption
- [ ] Supporting directories verified as referenced in parent SKILL.md
- [ ] Duplicate functionality checked via Jaccard overlap and quoted phrase collision
- [ ] Cross-file consistency validated (allowed-tools format, version, description person, tool casing, naming)
- [ ] All profiles loaded and drift patterns applied per category
- [ ] All findings use dimension: "convention-adherence" and ID prefix CVN
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)
