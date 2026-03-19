# Finding ID Stability + Scanner Anchoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate finding churn and enable reliable delta tracking by replacing free-form IDs with deterministic fingerprints and adding carry-forward context to re-scans.

**Architecture:** Three layers of change: (1) output schema updates (Finding.id regex, previous_id, carry_forward_summary), (2) all 8 scan skills get ID generation + carry-forward protocol sections, (3) orchestrator + reconciler + ralph-loop get plumbing for CHANGED_FILES and carry-forward stats.

**Tech Stack:** Markdown skill files + JSON schema updates (no runtime code — prompt engineering changes)

**Spec:** `docs/superpowers/specs/2026-03-19-finding-id-stability-scanner-anchoring-design.md`

---

### Task 1: Update Output Schemas

**Files:**
- Modify: `references/output-schemas.md`

- [ ] **Step 1: Read the current Finding schema**

Read `references/output-schemas.md` and locate the Finding schema block. Note the current `id` pattern and the `required` array.

- [ ] **Step 2: Update Finding.id pattern**

Replace the old `id` pattern:
```
"pattern": "^[a-z-]+-\\d{3}$"
```
with the new combined fingerprint regex:
```
"pattern": "^[A-Z]{3,4}-(000000-0000-[0-9a-f]{4}|[0-9a-f]{6}-\\d{4})(-[2-9]\\d*)?$"
```

Update the description and examples:
```json
"id": {
  "type": "string",
  "pattern": "^[A-Z]{3,4}-(000000-0000-[0-9a-f]{4}|[0-9a-f]{6}-\\d{4})(-[2-9]\\d*)?$",
  "description": "Deterministic fingerprint: {DIM}-{file_hash6}-{line_bucket} for file findings, {DIM}-000000-0000-{title_hash4} for null-file findings. Collision suffix starts at -2.",
  "examples": ["ARCH-8f3a21-0370", "SEC-000000-0000-a7f2", "QUAL-8f3a21-0370-2"]
}
```

- [ ] **Step 3: Add Finding.previous_id field**

Add to the Finding properties block (NOT to the `required` array):
```json
"previous_id": {
  "type": ["string", "null"],
  "default": null,
  "description": "Set when a carried-forward finding's code shifted >10 lines, causing a new fingerprint. Links to the old ID for continuity tracking."
}
```

- [ ] **Step 4: Add DimensionReport.carry_forward_summary field**

Locate the DimensionReport schema. Add a new optional field:
```json
"carry_forward_summary": {
  "type": ["object", "null"],
  "default": null,
  "description": "Present when PREVIOUS_FINDINGS was provided to the scanner. Null on first-ever scan.",
  "properties": {
    "carried_forward": { "type": "integer", "description": "Total carried forward (includes unverified)" },
    "resolved": { "type": "integer" },
    "new": { "type": "integer" },
    "unverified": { "type": "integer", "default": 0, "description": "Subset not re-verified (tentative carry-forward)" },
    "resolved_ids": { "type": "array", "items": { "type": "string" } }
  }
}
```

- [ ] **Step 5: Add ScoresReport.scan_metadata field**

Locate the ScoresReport schema. Add:
```json
"scan_metadata": {
  "type": ["object", "null"],
  "default": null,
  "description": "Aggregated carry-forward statistics across dimensions.",
  "properties": {
    "carry_forward_stats": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "carried_forward": { "type": "integer" },
          "resolved": { "type": "integer" },
          "new": { "type": "integer" }
        }
      }
    }
  }
}
```

- [ ] **Step 6: Verify all schema changes**

Read the full `output-schemas.md` and verify: Finding.id regex updated, previous_id added, carry_forward_summary added, scan_metadata added. No `required` arrays broken.

- [ ] **Step 7: Commit**

```bash
git add references/output-schemas.md
git commit -m "feat(schemas): fingerprint-based Finding.id, previous_id, carry_forward_summary, scan_metadata"
```

---

### Task 2: Create Shared ID Generation + Carry-Forward Block

**Files:**
- This task creates the text block that will be appended to all 8 scan skills. Write it once, then paste it into each skill in Task 3.

- [ ] **Step 1: Create the shared text block**

This is the exact markdown to append to each `scan-*/SKILL.md`. Create a temporary reference file at `docs/superpowers/plans/_scan-skill-appendix.md`:

```markdown
## Finding ID Generation

You MUST generate deterministic finding IDs using this algorithm.
NEVER use sequential numbering (001, 002) or free-form IDs.

### For findings with a file_path:

1. Compute file_hash6 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{relative_file_path}').hexdigest()[:6])"
   ```

2. Compute line_bucket:
   floor(line_start / 10) * 10, zero-padded to 4 digits
   Examples: line 1 → 0000, line 47 → 0040, line 374 → 0370

3. ID = {DIM}-{file_hash6}-{line_bucket}

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{lowercase title}').hexdigest()[:4])"
   ```

2. ID = {DIM}-000000-0000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `QUAL-8f3a21-0370` and `QUAL-8f3a21-0370-2` are carried forward, a new collision gets `QUAL-8f3a21-0370-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-{DIMENSION}.json
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
           If shifted >10 lines, recompute fingerprint and set previous_id to old ID.
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
2. For each new finding: verify no duplicate with carried-forward findings (same file, overlapping 10-line range). If duplicate, skip. If new, generate fingerprint ID.

### Output

DimensionReport MUST include:
1. All carried-forward findings (original IDs)
2. All new findings (new fingerprint IDs)
3. carry_forward_summary: { carried_forward, resolved, new, unverified, resolved_ids }

### Constraints

- NEVER re-describe a carried-forward finding in different words
- NEVER assign a new ID to a carried-forward unchanged finding
- NEVER carry forward without checking CHANGED_FILES first (if available)
```

- [ ] **Step 2: Verify the reference file**

Read `docs/superpowers/plans/_scan-skill-appendix.md` and confirm completeness.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/_scan-skill-appendix.md
git commit -m "docs: create shared scan skill appendix for ID generation and carry-forward"
```

---

### Task 3: Append ID Generation + Carry-Forward to All 8 Scan Skills

**Files:**
- Modify: `skills/scan-architecture/SKILL.md`
- Modify: `skills/scan-quality/SKILL.md`
- Modify: `skills/scan-dependencies/SKILL.md`
- Modify: `skills/scan-patterns/SKILL.md`
- Modify: `skills/scan-testing/SKILL.md`
- Modify: `skills/scan-performance/SKILL.md`
- Modify: `skills/scan-security/SKILL.md`
- Modify: `skills/scan-tech-debt/SKILL.md`

Each scan skill needs the same two sections appended. The ONLY difference per skill is the `{DIM}` prefix used in examples.

- [ ] **Step 1: Read the shared appendix**

Read `docs/superpowers/plans/_scan-skill-appendix.md` for the text to append.

- [ ] **Step 2: Append to scan-architecture**

Read `skills/scan-architecture/SKILL.md`. Append the full shared block at the end. Replace `{DIM}` with `ARCH` in all examples and instructions.

Also update the Input section to include new parameters:
```markdown
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
```

- [ ] **Step 3: Append to scan-quality**

Same as Step 2 but for `skills/scan-quality/SKILL.md`. Replace `{DIM}` with `QUAL`.

- [ ] **Step 4: Append to scan-dependencies**

Same pattern. Replace `{DIM}` with `DEP`.

- [ ] **Step 5: Append to scan-patterns**

Replace `{DIM}` with `PAT`.

- [ ] **Step 6: Append to scan-testing**

Replace `{DIM}` with `TST`.

- [ ] **Step 7: Append to scan-performance**

Replace `{DIM}` with `PERF`.

- [ ] **Step 8: Append to scan-security**

Replace `{DIM}` with `SEC`.

- [ ] **Step 9: Append to scan-tech-debt**

Replace `{DIM}` with `DEBT`.

- [ ] **Step 10: Verify all 8 skills**

For each scan skill, verify:
- Input section has `SCAN_REPORTS_DIR` and `CHANGED_FILES` parameters
- "Finding ID Generation" section present with correct DIM prefix
- "Carry-Forward Protocol" section present
- No broken markdown formatting

- [ ] **Step 11: Commit**

```bash
git add skills/scan-architecture/SKILL.md skills/scan-quality/SKILL.md \
  skills/scan-dependencies/SKILL.md skills/scan-patterns/SKILL.md \
  skills/scan-testing/SKILL.md skills/scan-performance/SKILL.md \
  skills/scan-security/SKILL.md skills/scan-tech-debt/SKILL.md
git commit -m "feat(scan-skills): add fingerprint ID generation and carry-forward protocol to all 8 dimensions"
```

---

### Task 4: Update Orchestrator (analyze-codebase)

**Files:**
- Modify: `skills/analyze-codebase/SKILL.md`

- [ ] **Step 1: Read the current orchestrator**

Read `skills/analyze-codebase/SKILL.md` and locate the Optional Flags section and Stage 2.

- [ ] **Step 2: Add --changed-files-hint flag**

In the Optional Flags section (after `--draft-only`), add:
```markdown
- `--changed-files-hint=<comma-separated file paths>` — passed by ralph-loop to enable diff-scoped carry-forward. Optional. When absent, scanners do full scans.
```

- [ ] **Step 3: Update Stage 2 dispatch**

In Stage 2, find the code-analyzer agent dispatch section. After the existing dispatch parameters (DIMENSION, STACK, etc.), append two new parameters to the agent prompt. The exact text to add to the dispatch block:

```markdown
Additional parameters for each code-analyzer agent:
- SCAN_REPORTS_DIR: ".code-analysis/scan-reports"
  (Path hint — the scanner loads its own previous findings from this directory.
   The orchestrator MUST NOT read scan reports itself.)
- CHANGED_FILES: <array of relative file paths, or null>
  (If --changed-files-hint flag was provided, split the comma-separated value
   into an array and pass it here. If the flag was not provided, pass null.
   Scanners use this for diff-scoped carry-forward.)
```

Do NOT restructure the existing dispatch format — only append these two parameters to it.

- [ ] **Step 4: Verify**

Read the updated orchestrator and confirm:
- New flag in Optional Flags section
- Stage 2 passes SCAN_REPORTS_DIR and CHANGED_FILES
- No other stages modified

- [ ] **Step 5: Commit**

```bash
git add skills/analyze-codebase/SKILL.md
git commit -m "feat(orchestrator): add --changed-files-hint flag and pass SCAN_REPORTS_DIR to scanners"
```

---

### Task 5: Update Reconciler (reconcile-report)

**Files:**
- Modify: `skills/reconcile-report/SKILL.md`

- [ ] **Step 1: Read the current reconciler**

Read `skills/reconcile-report/SKILL.md`. Locate Step 4d (Delta Analysis) and the Success Checklist.

- [ ] **Step 2: Update Step 4d Delta Analysis**

Replace the existing delta analysis instructions with the fingerprint-aware version:

```markdown
### Step 4d — Delta Analysis (if PREVIOUS_SCORES provided)

With fingerprint-based IDs, delta analysis is reliable:

- **Resolved**: IDs in PREVIOUS_SCORES but not in current → genuinely fixed
- **New**: IDs in current but not in PREVIOUS_SCORES → genuinely new
- **Unchanged**: IDs present in both → persistent issues

**Handling merged IDs:**
During dedup (Step 1), findings may be merged. To handle resolved_ids from
carry_forward_summary correctly:
1. Build mapping: {original_scanner_id → merged_id} from dedup table
2. Check both original and merged IDs when computing deltas
3. A finding is "resolved" if its scanner ID is in carry_forward_summary.resolved_ids,
   even if PREVIOUS_SCORES stored a different merged ID
4. Include both scanner ID and mapped merged ID in resolved_finding_ids

**Old-format detection:** If ANY finding ID in PREVIOUS_SCORES matches `^[a-z-]+-\d{3}$`
(old sequential format), treat the entire previous report as old-format and skip delta
comparison (all findings treated as "new").
```

- [ ] **Step 3: Add scan_metadata aggregation to Step 6**

In Step 6 (Assemble Scores JSON), add:

```markdown
6b. If any DimensionReport contains a `carry_forward_summary`, aggregate into
    `scan_metadata.carry_forward_stats` in the ScoresReport:
    For each dimension with carry_forward_summary:
      scan_metadata.carry_forward_stats[dimension] = {
        carried_forward, resolved, new
      }
```

- [ ] **Step 4: Update Success Checklist**

Add to the checklist:
```markdown
- [ ] scan_metadata.carry_forward_stats aggregated from DimensionReport.carry_forward_summary (if any scanner provided it)
- [ ] Old-format PREVIOUS_SCORES detected and delta comparison skipped if applicable
```

- [ ] **Step 5: Verify**

Read the updated reconciler and confirm Step 4d, Step 6, and Success Checklist are all updated.

- [ ] **Step 6: Commit**

```bash
git add skills/reconcile-report/SKILL.md
git commit -m "feat(reconciler): fingerprint-aware delta analysis and carry_forward_stats aggregation"
```

---

### Task 6: Update Ralph-Loop (Step 7 CHANGED_FILES)

**Files:**
- Modify: `skills/ralph-loop/SKILL.md`

- [ ] **Step 1: Read the current ralph-loop Step 7**

Read `skills/ralph-loop/SKILL.md` and locate Step 7 (Re-scan).

- [ ] **Step 2: Update Step 7 to pass CHANGED_FILES**

Replace the current Step 7 re-scan invocation:
```
/analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics
```
with:
```markdown
### Step 7 — Re-scan

1. Compute changed files since last commit:
   ```bash
   git diff --name-only {last_commit_sha}..HEAD
   ```

2. Run the re-scan with changed files hint:
   ```
   /analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics \
     --changed-files-hint="{comma-separated file list from step 1}"
   ```

This enables diff-scoped carry-forward: unchanged files' findings are
carried forward without re-reading, reducing re-scan token cost.
```

- [ ] **Step 3: Verify**

Read the updated Step 7 and confirm the git diff and --changed-files-hint are both present.

- [ ] **Step 4: Commit**

```bash
git add skills/ralph-loop/SKILL.md
git commit -m "feat(ralph-loop): pass CHANGED_FILES hint to orchestrator for diff-scoped re-scans"
```

---

### Task 7: Clean Up and Final Review

**Files:**
- Remove: `docs/superpowers/plans/_scan-skill-appendix.md` (temporary reference file)
- Review: all modified files

- [ ] **Step 1: Delete the temporary appendix file**

```bash
git rm docs/superpowers/plans/_scan-skill-appendix.md
```

- [ ] **Step 2: Full review of all changes**

Read each modified file and verify consistency:
- `references/output-schemas.md`: Finding.id regex, previous_id, carry_forward_summary, scan_metadata
- All 8 `skills/scan-*/SKILL.md`: ID Generation + Carry-Forward sections with correct DIM prefix
- `skills/analyze-codebase/SKILL.md`: --changed-files-hint flag, Stage 2 passes SCAN_REPORTS_DIR
- `skills/reconcile-report/SKILL.md`: Step 4d delta, Step 6 aggregation, Success Checklist
- `skills/ralph-loop/SKILL.md`: Step 7 passes CHANGED_FILES

- [ ] **Step 3: Commit cleanup**

```bash
git rm docs/superpowers/plans/_scan-skill-appendix.md
git commit -m "chore(code-analysis): remove temporary appendix file after scan skill updates"
```
