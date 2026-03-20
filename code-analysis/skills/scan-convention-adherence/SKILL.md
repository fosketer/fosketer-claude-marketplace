---
name: scan-convention-adherence
description: |
  Use when detecting deprecated commands/ usage, @file anti-patterns, token budget violations, and drift from official Claude plugin conventions.
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

3. ID = CVN-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored, breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = CVN-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `CVN-8f3a21-a1b2` and `CVN-8f3a21-a1b2-2` are carried forward, a new collision gets `CVN-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-convention-adherence.json
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
