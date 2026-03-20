---
name: scan-marketplace-consistency
description: |
  Use when checking marketplace.json registry alignment, version consistency across plugin.json and package.json, cross-plugin naming conflicts, and README presence.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Marketplace Consistency

## Purpose

Verify that a Claude plugin is correctly registered in its parent marketplace, that metadata is consistent between registry and manifest, that version fields are in sync, and that naming conflicts with sibling plugins are absent.

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

Using the marketplace entry found in Step 2:

1. Compare `description` field:
   - If description in marketplace.json differs from description in plugin.json: emit **medium** finding — "Plugin description in marketplace.json does not match plugin.json"
   - Include both values in the finding description for easy comparison
2. Compare `name` field:
   - If name in marketplace entry differs from plugin.json `name`: emit **high** finding — "Plugin name mismatch between marketplace.json and plugin.json"
3. Compare any `tags` or `keywords` fields if both sources provide them:
   - Significant divergence (different items): **info** finding

### Step 4 — Check Version Consistency

1. Read `PROJECT_PATH/.claude-plugin/plugin.json` — extract `version` field (may be absent)
2. Read `PROJECT_PATH/package.json` (if it exists) — extract `version` field
3. If both `plugin.json` and `package.json` have version fields:
   - If versions differ: emit **medium** finding — "Version mismatch between plugin.json and package.json"
4. If marketplace.json entry has a `version` field:
   - Compare against plugin.json version — if they differ: emit **medium** finding — "Version in marketplace.json does not match plugin.json"
5. If no version field exists in plugin.json: emit **info** finding — "plugin.json has no version field — consider adding semantic versioning"

### Step 5 — Check for Cross-Plugin Naming Conflicts

1. Glob sibling plugin directories: `PROJECT_PATH/../*/` (all directories at the same level as this plugin)
2. For each sibling: read its `.claude-plugin/plugin.json` and extract the `name` field
3. Compare against this plugin's `name`:
   - Exact match: emit **high** finding — "Naming conflict: another plugin has the same name"
   - Similar name (same prefix or 1-character edit distance): emit **info** finding — "Potential naming conflict with sibling plugin '{sibling_name}'"
4. Collect all skill names from `PROJECT_PATH/skills/*/SKILL.md` frontmatter
5. Check whether any sibling plugin has skills with identical names — emit **medium** finding if duplicates found

### Step 6 — Check README Presence and Content

1. Check whether `PROJECT_PATH/README.md` exists
2. If absent: emit **medium** finding — "README.md is missing"
3. If present: read the file and check it is non-empty (more than 10 lines of meaningful content)
4. If README is effectively empty (< 10 non-blank lines): emit **medium** finding — "README.md exists but contains insufficient content"

### Step 7 — Apply Profile Ground Truth

1. Read `PLUGIN_PROFILES_DIR/marketplace-conventions.md` for ground truth on marketplace registration requirements
2. Apply any profile rules that promote or downgrade severity of existing findings

### Step 8 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

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

3. ID = MKT-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored, breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = MKT-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `MKT-8f3a21-a1b2` and `MKT-8f3a21-a1b2-2` are carried forward, a new collision gets `MKT-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-marketplace-consistency.json
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
