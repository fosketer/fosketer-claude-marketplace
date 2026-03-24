---
name: scan-marketplace-consistency
version: 0.8.0
description: |
  This skill should be used when the user asks to "check marketplace registration", "verify version consistency",
  "validate marketplace.json alignment", or when checking marketplace.json registry alignment, version consistency
  across plugin.json and package.json, cross-plugin naming conflicts, and README presence.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Marketplace Consistency

## Purpose

Verify that a Claude plugin is correctly registered in its parent marketplace, that metadata is consistent between registry and manifest, that version fields are in sync, and that naming conflicts with sibling plugins are absent.


**Note:** This skill does NOT use `OFFICIAL_PLUGINS_INDEX_PATH`. That parameter may be null or absent and MUST be ignored.

## Input

- `PROJECT_PATH`: Root directory of the plugin being analyzed
- `STACK`: { languages: ["claude-plugin"], frameworks: [] }
- `PLUGIN_PROFILES_DIR`: Path to references/plugin-profiles/
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `OFFICIAL_PLUGINS_INDEX_PATH`: **Not used by this skill.** This parameter is accepted for interface consistency but MUST be ignored.

## Workflow

### Step 1 — Detect Parent Marketplace

1. Check whether `PROJECT_PATH/../.claude-plugin/marketplace.json` exists (Glob for it)
2. If it does not exist: return a single **info** finding — "No parent marketplace detected — marketplace consistency checks skipped" and stop
3. If it exists: proceed to Step 2

### Step 2 — Read marketplace.json and Locate Plugin Entry

1. Read `PROJECT_PATH/../.claude-plugin/marketplace.json`
2. Validate the file is parseable JSON — if not: emit **high** finding — "marketplace.json is not valid JSON" and stop
3. Read `PROJECT_PATH/.claude-plugin/plugin.json` to get the plugin's `name` field
4. Search the marketplace `plugins` array (or equivalent registry structure) for an entry matching this plugin's name
5. If no entry found: emit **high** finding — "Plugin is not listed in the parent marketplace.json"
6. If found: proceed to metadata comparison in Step 3

### Step 3 — Compare Metadata: marketplace.json vs plugin.json

Using the marketplace entry found in Step 2, perform a field-by-field comparison against the plugin manifest. Each field has its own divergence detection rule.

#### 3a — `name` field

Compare the `name` value in the marketplace entry against `name` in plugin.json using exact string equality (case-sensitive).

- Exact match: no finding.
- Case-only difference (e.g., `Code-Analysis` vs `code-analysis`): emit **high** finding — "Plugin name casing mismatch between marketplace.json and plugin.json". Kebab-case is the canonical form; the marketplace entry MUST match the plugin manifest exactly.
- Completely different value: emit **high** finding — "Plugin name mismatch between marketplace.json and plugin.json". Include both values verbatim.

#### 3b — `description` field

Compare `description` in both sources. Apply the following divergence detection rules:

- If the marketplace description is a strict substring of the plugin.json description (or vice versa): emit **medium** finding — "Plugin description is a truncated version in one source". This commonly occurs when an author updates the plugin manifest but forgets the marketplace entry.
- If both descriptions exist but differ in wording beyond trivial whitespace: emit **medium** finding — "Plugin description in marketplace.json does not match plugin.json". Include both values in the finding description for easy comparison.
- If the marketplace entry has a description but plugin.json does not (or vice versa): emit **medium** finding — "Description present in one source but missing in the other".

#### 3c — `author` field

Compare `author` (or `maintainer`) if present in both sources.

- If both exist and differ: emit **info** finding — "Author metadata diverges between marketplace.json and plugin.json".
- If the marketplace entry specifies an author but plugin.json omits it: no finding (marketplace MAY carry additional metadata).

#### 3d — `tags` / `keywords` field

Compare `tags` or `keywords` arrays if both sources provide them.

- Compute the symmetric difference (items in one array but not the other).
- If the symmetric difference is non-empty: emit **info** finding — "Tag/keyword sets diverge between marketplace.json and plugin.json". List the differing items.
- If one source has tags and the other does not: emit **info** finding — "Tags present in one source but absent in the other".

#### 3e — `path` or `directory` field

If the marketplace entry contains a `path` or `directory` field pointing to the plugin location:

- Verify the path resolves to `PROJECT_PATH` relative to the marketplace root. If it does not: emit **high** finding — "Marketplace entry path does not resolve to the actual plugin directory".

### Step 4 — Check Version Consistency

Validate that version strings are consistent across all three potential sources: `plugin.json`, `package.json`, and the marketplace entry.

1. Read `PROJECT_PATH/.claude-plugin/plugin.json` — extract `version` field (may be absent).
2. Read `PROJECT_PATH/package.json` (if it exists) — extract `version` field.
3. If the marketplace entry has a `version` field, extract it as the third source.
4. For each pair of sources where both have a version field, compare using exact string equality:
   - `plugin.json` vs `package.json`: if versions differ, emit **medium** finding — "Version mismatch between plugin.json and package.json".
   - `plugin.json` vs marketplace entry: if versions differ, emit **medium** finding — "Version in marketplace.json does not match plugin.json".
   - `package.json` vs marketplace entry: if versions differ, emit **info** finding — "Version in marketplace.json does not match package.json".
5. If all three sources exist and all three disagree (three distinct version strings): escalate to **high** finding — "Three-way version mismatch across plugin.json, package.json, and marketplace.json". This indicates a release process failure.
6. Validate that each version string follows semantic versioning (MAJOR.MINOR.PATCH). If a version field exists but is not valid semver: emit **info** finding — "Version field does not follow semantic versioning format".
7. If no version field exists in plugin.json: emit **info** finding — "plugin.json has no version field — consider adding semantic versioning".

### Step 5 — Check for Cross-Plugin Naming Conflicts

1. Glob sibling plugin directories: `PROJECT_PATH/../*/` (all directories at the same level as this plugin).
2. For each sibling that contains `.claude-plugin/plugin.json`: read the file and extract the `name` field.
3. Compare each sibling name against this plugin's `name` using the following tiered approach:
   - **Exact match** (case-sensitive): emit **high** finding — "Naming conflict: another plugin has the same name '{sibling_name}'".
   - **Case-insensitive match** (e.g., `Code-Analysis` vs `code-analysis`): emit **high** finding — "Case-insensitive naming conflict with '{sibling_name}'".
   - **Levenshtein edit distance of 1** (single insertion, deletion, or substitution): emit **medium** finding — "Near-duplicate plugin name: '{plugin_name}' vs '{sibling_name}' (edit distance 1)".
   - **Shared prefix of 70% or more of the shorter name's length** (e.g., `code-analysis` and `code-analysis-pro`): emit **info** finding — "Potential naming conflict with sibling plugin '{sibling_name}' — shared prefix detected".
   - Edit distance of 2 or more with no shared prefix above threshold: no finding.
4. Collect all skill names from `PROJECT_PATH/skills/*/SKILL.md` frontmatter (the `name` field in the YAML block).
5. For each sibling plugin, collect its skill names from `<sibling>/skills/*/SKILL.md` frontmatter.
6. Compare skill name sets: if any skill name appears in both this plugin and a sibling, emit **medium** finding — "Skill name collision: skill '{skill_name}' exists in both '{plugin_name}' and '{sibling_name}'". Include the directory paths of both conflicting skills.

### Step 6 — Check README Presence and Content

1. Check whether `PROJECT_PATH/README.md` exists
2. If absent: emit **medium** finding — "README.md is missing"
3. If present: read the file and check it is non-empty (more than 10 lines of meaningful content)
4. If README is effectively empty (< 10 non-blank lines): emit **medium** finding — "README.md exists but contains insufficient content"

### Step 7 — Apply Profile Ground Truth

1. Read `PLUGIN_PROFILES_DIR/marketplace-conventions.md` for ground truth on marketplace registration requirements
2. Apply any profile rules that promote or downgrade severity of existing findings

### Step 8 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/schemas/finding-schema.md`:

```json
{
  "id": "MKT-e7b4a1-3f2a",
  "dimension": "marketplace-consistency",
  "title": "Plugin description in marketplace.json does not match plugin.json",
  "description": "The description registered in marketplace.json ('Analyzes codebases') differs from the description in .claude-plugin/plugin.json ('Analyze and improve codebases with multi-dimensional scanning'). The marketplace entry should be kept in sync with the plugin manifest.",
  "severity": "medium",
  "file_path": ".claude-plugin/plugin.json",
  "line_start": 4,
  "line_end": 4,
  "snippet": "\"description\": \"Analyze and improve codebases with multi-dimensional scanning\"",
  "recommendation": "Update marketplace.json to reflect the current description from plugin.json, or vice versa",
  "effort": "low",
  "tags": ["marketplace", "metadata", "consistency"]
}
```

Always populate `snippet` with the relevant lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Common Marketplace Misconfigurations

The following patterns occur frequently and SHOULD be checked proactively:

1. **Stale marketplace entry after plugin rename.** A plugin directory is renamed (e.g., `code-scanner` to `code-analysis`) but marketplace.json still references the old name and path. Symptoms: Step 2 fails to find the entry, and a ghost entry persists.

2. **Description drift after iterative development.** The plugin.json description is updated during development, but the marketplace entry retains the original one-liner. Symptoms: Step 3b detects substring or wording divergence.

3. **Version bump in package.json only.** Running `npm version patch` updates package.json but not plugin.json or the marketplace entry. Symptoms: Step 4 detects a two-way or three-way version mismatch.

4. **Duplicate plugin name across forks.** Two plugins forked from the same template retain the template's default name. Symptoms: Step 5 detects an exact name match between siblings.

5. **Missing path field in marketplace entry.** The marketplace entry omits the `path` or `directory` field, making automated resolution impossible. Symptoms: Step 3e cannot validate path resolution.

6. **Empty or placeholder README.** A plugin is registered with a README.md containing only a template heading. Symptoms: Step 6 detects fewer than 10 non-blank lines.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No parent marketplace.json detected | Return single info finding, stop |
| marketplace.json is invalid JSON | Emit high finding, stop |
| plugin.json is missing or invalid | Emit critical finding referencing manifest-structure dimension, stop |
| `package.json` does not exist | Skip version cross-check against package.json (Step 4) |
| Sibling plugin has no `.claude-plugin/plugin.json` | Skip that sibling in naming conflict check |
| `PLUGIN_PROFILES_DIR/marketplace-conventions.md` not found | Skip profile override step, proceed without it |

## Success Checklist

- [ ] Parent marketplace.json detected (or absence noted — single info finding)
- [ ] Plugin entry found in marketplace registry
- [ ] Description and name metadata compared between marketplace.json and plugin.json
- [ ] Version consistency checked across plugin.json and package.json
- [ ] Cross-plugin naming conflicts checked among siblings
- [ ] README.md presence and content verified
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "marketplace-consistency" and ID prefix MKT
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
   { "dimension": "marketplace-consistency", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-marketplace-consistency.json` (overwrite if same date exists)
