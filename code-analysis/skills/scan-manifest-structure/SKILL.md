---
name: scan-manifest-structure
description: |
  Validate Claude plugin manifest (plugin.json), directory layout, naming conventions, required files, and .claude-plugin/ placement.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
---

# Scan Manifest Structure

## Purpose

Validate the structural integrity of a Claude plugin: the `.claude-plugin/plugin.json` manifest, directory layout, naming conventions, required files, and alignment with official plugin patterns.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the plugin being analyzed
- `STACK`: { languages: ["claude-plugin"], frameworks: [] }
- `PLUGIN_PROFILES_DIR`: Path to references/plugin-profiles/
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `OFFICIAL_PLUGINS_INDEX_PATH`: Path to official plugins comparison index JSON

## Workflow

### Step 1 — Read and Validate plugin.json

1. Read `PROJECT_PATH/.claude-plugin/plugin.json`
2. If not found: emit **critical** finding MNF — "Missing .claude-plugin/plugin.json" and abort further steps
3. Validate JSON is parseable — if not: emit **critical** finding and abort
4. Check required fields:
   - `name`: MUST be present — **high** if missing
5. Check recommended fields — **medium** if any of the following are missing:
   - `version`, `description`, `author`, `keywords`

### Step 2 — Validate Plugin Name Format

1. Extract `name` from plugin.json (skip if Step 1 found it missing)
2. Validate against kebab-case regex: `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`
3. If name does not match: emit **high** finding — "Plugin name does not follow kebab-case convention"
4. Check that the `name` value matches the plugin's directory basename — emit **medium** if they differ

### Step 3 — Validate Directory Layout

1. Glob for expected top-level directories within `PROJECT_PATH`:
   - `skills/` — expected, note if absent (info)
   - `agents/` — optional, note count if present
   - `hooks/` — optional, note if present
   - `commands/` — **deprecated**, emit **info** finding if present: "commands/ directory is deprecated — migrate to skills/"
2. Check that `.claude-plugin/` is placed directly under `PROJECT_PATH` (not nested deeper)
3. Flag unexpected top-level directories that are neither conventional nor documented

### Step 4 — Check Required Files

1. Check `README.md` exists in `PROJECT_PATH` — emit **medium** finding if absent
2. Glob for at least one `skills/*/SKILL.md` OR one `agents/*.md` OR one `agents/*/AGENT.md`
   - If none found: emit **high** finding — "Plugin has no skills or agents"
3. If `version` field is present in plugin.json, check whether `package.json` also exists and whether versions are in sync (info-level divergence)

### Step 5 — Check for Hardcoded Absolute Paths

1. Grep all files under `PROJECT_PATH` for hardcoded absolute path patterns:
   - `/Users/`, `/home/`, `/root/`, `C:\\Users\\`, `C:/Users/`
2. For each match: emit **high** finding — "Hardcoded absolute path detected — use \${CLAUDE_PLUGIN_ROOT} instead"
3. Exclude `.git/` and `node_modules/` from the search

### Step 6 — Compare Against Official Plugins

1. Read `OFFICIAL_PLUGINS_INDEX_PATH` — parse JSON index of official plugin structures
2. For each official plugin entry, compare:
   - Whether this plugin has the same mandatory top-level directories
   - Whether `.claude-plugin/plugin.json` placement is consistent
3. Flag structural divergences that differ from the majority of official plugins as **medium** — "Directory layout diverges from official plugin conventions"
4. Read `PLUGIN_PROFILES_DIR/plugin-structure.md` for ground truth on expected layout
5. Cross-reference any profile rules against current findings — promote or downgrade severity if profile overrides apply

### Step 7 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "MNF-e7b4a1-3f2a",
  "dimension": "manifest-structure",
  "title": "Plugin name does not follow kebab-case convention",
  "description": "The name field in .claude-plugin/plugin.json is 'MyPlugin', which does not match /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/",
  "severity": "high",
  "file_path": ".claude-plugin/plugin.json",
  "line_start": 3,
  "line_end": 3,
  "snippet": "\"name\": \"MyPlugin\"",
  "recommendation": "Rename to 'my-plugin' to follow kebab-case convention",
  "effort": "low",
  "tags": ["naming", "manifest", "kebab-case"]
}
```

Always populate `snippet` with the relevant lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| `.claude-plugin/plugin.json` does not exist | Emit critical finding, return early with that single finding |
| Invalid JSON in plugin.json | Emit critical finding, skip all further validation steps |
| `OFFICIAL_PLUGINS_INDEX_PATH` is null or unreadable | Skip Step 6 comparison, note as info finding |
| `PLUGIN_PROFILES_DIR/plugin-structure.md` not found | Skip profile cross-reference in Step 6, proceed without it |
| Plugin has no skills/ or agents/ directory at all | Emit high finding in Step 4, continue checking other dimensions |

## Success Checklist

- [ ] `.claude-plugin/plugin.json` read and validated (required + recommended fields)
- [ ] Plugin name validated against kebab-case regex
- [ ] Directory layout checked (skills/, agents/, hooks/, commands/ deprecated)
- [ ] Required files confirmed (README.md, at least one SKILL.md or agent .md)
- [ ] Hardcoded absolute paths scanned and flagged
- [ ] Official plugins index consulted for structural comparison
- [ ] Plugin profile ground truth applied
- [ ] All findings use dimension: "manifest-structure" and ID prefix MNF
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

3. ID = MNF-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored, breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = MNF-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `MNF-8f3a21-a1b2` and `MNF-8f3a21-a1b2-2` are carried forward, a new collision gets `MNF-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-manifest-structure.json
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
