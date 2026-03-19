# Spec B: Finding ID Stability + Scanner Determinism Anchoring

**Date:** 2026-03-19
**Status:** Approved
**Scope:** `references/output-schemas.md`, all 8 `skills/scan-*/SKILL.md`, `skills/analyze-codebase/SKILL.md`, `skills/reconcile-report/SKILL.md`, `skills/ralph-loop/SKILL.md`
**Depends on:** None (Spec A is independent, but benefits from stable IDs)
**Motivation:** Session evidence showed that LLM-based scanners produce different findings on identical code across runs. v0.2.4 scan produced `ARCH-001` through `ARCH-014`; v0.2.5 scan of the same codebase produced `arch-001` through `arch-014` — different case, numbering, and content. This causes finding churn, plan staleness, unreliable delta tracking, and the Sisyphus effect ("fix 5, 3 new appear").

## Problem Statement

Two coupled issues:

### Finding ID Instability

Each `code-analyzer` agent independently assigns finding IDs. There is no stable ID contract. Consequences:
- `completed_finding_ids` in loop-state becomes invalid after a re-scan
- Delta tracking (`new_finding_ids`, `resolved_finding_ids`) is unreliable — "resolved" findings may just have a different ID
- Cross-session continuity is broken

### Scanner Non-Determinism

LLM-based scanners are inherently non-deterministic. Scanning the same codebase twice produces different findings. Session evidence:
- "Re-scan found significantly different results. 4 stale removed, 3 new ones found" — with zero code changes
- "New findings appeared while fixed ones are gone" — after fixing findings, re-scan found entirely different issues
- "The plan is stale (references resolved findings ARCH-001, ARCH-N02 and misses new findings ARCH-011)" — plan invalidated mid-loop

## Design

### Part 1: Deterministic Finding IDs

#### 1.1 Fingerprint Format

Replace free-form IDs with content-based fingerprints:

```
{DIM}-{file_hash6}-{line_bucket}
```

| Component | Computation | Example |
|-----------|-------------|---------|
| `DIM` | Fixed uppercase prefix per dimension | `ARCH` |
| `file_hash6` | First 6 hex chars of `SHA-256(relative_file_path)` | `8f3a21` |
| `line_bucket` | `floor(line_start / 10) * 10`, zero-padded to 4 digits | `0370` |

#### 1.2 Dimension Prefix Mapping

| Dimension | Prefix |
|-----------|--------|
| architecture | `ARCH` |
| quality | `QUAL` |
| dependencies | `DEP` |
| patterns | `PAT` |
| testing | `TST` |
| performance | `PERF` |
| security | `SEC` |
| tech-debt | `DEBT` |

#### 1.3 Examples

| Finding | File | line_start | ID |
|---------|------|-----------|-----|
| monitor.rs complexity | `rust/src/monitor.rs` | 1 | `ARCH-e7b4a1-0000` |
| git.rs complexity | `rust/src/git.rs` | 1 | `ARCH-3c9f82-0000` |
| Redis KEYS scan | `rust/src/storage/redis_store.rs` | 129 | `PERF-c4d7e2-0120` |
| Router handle_message | `rust/src/bot/router.rs` | 374 | `ARCH-8f3a21-0370` |
| Same file, nearby line | `rust/src/bot/router.rs` | 377 | `ARCH-8f3a21-0370` (same bucket) |
| No kustomize structure | (null) | null | `ARCH-000000-0000-a7f2` |

#### 1.4 Edge Cases

**Null file_path (e.g., "no kustomize structure"):**
```
{DIM}-000000-0000-{title_hash4}

title_hash4 = first 4 hex chars of SHA-256(lowercase title)
Example: SEC-000000-0000-a7f2
```

**Collision (two findings in same 10-line bucket):**
If a scanner produces two findings with identical fingerprints, append `-2`, `-3` suffix.

On a **fresh scan** (no PREVIOUS_FINDINGS): the first finding (by severity DESC, then title alphabetical ASC) gets the bare fingerprint:
```
QUAL-8f3a21-0370      (first finding, higher severity)
QUAL-8f3a21-0370-2    (second finding, same bucket)
```

On a **carry-forward re-scan**: carried-forward findings **always keep their existing ID**, regardless of severity rank. New findings in the same bucket are assigned suffixes starting from the highest existing suffix + 1. This preserves ID stability across scans:
```
QUAL-8f3a21-0370      (carried forward from previous scan, keeps bare ID)
QUAL-8f3a21-0370-2    (new finding in same bucket, gets next suffix)
```

**Moved code (>10 lines):**
Code that moves beyond the 10-line bucket boundary gets a new fingerprint. The carry-forward mechanism (Part 2) handles continuity: the scanner sets `previous_id` on the finding to link to the old fingerprint. The reconciler uses `previous_id` to track the finding as "moved" rather than "new + resolved."

#### 1.5 Schema Change

In `references/output-schemas.md`, update the Finding.id pattern.

There are two valid formats — file-path findings and null-file findings — validated by separate patterns:

**File-path findings:**
```
"^[A-Z]{3,4}-[0-9a-f]{6}-\\d{4}(-[2-9]\\d*)?$"
```
- `[A-Z]{3,4}` — dimension prefix (ARCH, QUAL, DEP, PAT, TST, PERF, SEC, DEBT)
- `-[0-9a-f]{6}` — file path hash (non-zero)
- `-\\d{4}` — line bucket
- `(-[2-9]\\d*)?` — optional collision suffix (starts at 2, never 1)

**Null-file findings (file_hash = 000000):**
```
"^[A-Z]{3,4}-000000-0000-[0-9a-f]{4}(-[2-9]\\d*)?$"
```
- `000000-0000` — signals no file path
- `-[0-9a-f]{4}` — title hash (required for null-file findings)
- `(-[2-9]\\d*)?` — optional collision suffix

**Combined regex** (for schema validators that need a single pattern):
```
"^[A-Z]{3,4}-(000000-0000-[0-9a-f]{4}|[0-9a-f]{6}-\\d{4})(-[2-9]\\d*)?$"
```

This ensures title_hash4 only appears when file_hash is `000000`, and collision suffixes start at `-2` (the bare ID is always the first finding).

#### 1.6 Scan Skill Instruction Block

Append to each `scan-*/SKILL.md`:

```markdown
## Finding ID Generation

You MUST generate deterministic finding IDs using this algorithm.
NEVER use sequential numbering (001, 002) or free-form IDs.

### For findings with a file_path:

1. Compute file_hash6 (use python3 for cross-platform portability):
   python3 -c "import hashlib; print(hashlib.sha256(b'{relative_file_path}').hexdigest()[:6])"

2. Compute line_bucket:
   floor(line_start / 10) * 10, zero-padded to 4 digits
   Examples: line 1 → 0000, line 47 → 0040, line 374 → 0370

3. ID = {DIM}-{file_hash6}-{line_bucket}

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   python3 -c "import hashlib; print(hashlib.sha256(b'{lowercase title}').hexdigest()[:4])"

2. ID = {DIM}-000000-0000-{title_hash4}

### Collision resolution:

If two findings produce the same ID, sort by severity (critical > high > medium
> low > info) then by title (alphabetical). The first gets the bare ID. Subsequent
findings append -2, -3, etc.
```

### Part 2: Carry-Forward Context (Scanner Anchoring)

#### 2.1 Orchestrator Changes (analyze-codebase Stage 2)

The orchestrator remains a thin dispatcher. It does **not** read previous scan reports (that would violate the context efficiency rule). Instead, each scanner agent loads its own previous findings.

**Orchestrator changes are minimal:**

```markdown
## Stage 2 — Dispatch Dimension Scanners (updated)

For each dimension in --dimensions:

1. Dispatch code-analyzer agent with parameters:
   - DIMENSION: dimension name
   - STACK: detected stack
   - SCAN_REPORTS_DIR: ".code-analysis/scan-reports" (path hint, not content)
   - CHANGED_FILES: array of relative paths or null

2. CHANGED_FILES is computed by the orchestrator only when provided
   via the --changed-files-hint flag (used by ralph-loop):
   - If flag is present → split comma-separated value into array
   - If flag is absent → null (scanner will do full scan)
```

**New orchestrator flag** (add to Optional Flags section of analyze-codebase SKILL.md):

```
--changed-files-hint=<comma-separated file paths>
  Passed by ralph-loop to enable diff-scoped carry-forward.
  Optional. When absent, scanners do full scans.
```

Each scanner agent is responsible for finding and reading its own previous scan report from `SCAN_REPORTS_DIR`. This keeps the orchestrator thin and avoids loading 8 large JSON files into the orchestrator's context.

#### 2.2 Scan Skill Carry-Forward Protocol

Append to each `scan-*/SKILL.md`, after the Finding ID Generation section:

```markdown
## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

### Phase 1 — Verify Previous Findings

For each finding in PREVIOUS_FINDINGS, in order:

A. If CHANGED_FILES is provided AND finding.file_path is NOT in CHANGED_FILES:
   → CARRY FORWARD unchanged. Copy the finding exactly (same ID, same severity,
     same description, same line numbers). Do NOT re-read the file.
     Do NOT re-evaluate. This is an optimization: unchanged files cannot have
     resolved findings.

B. If finding.file_path IS in CHANGED_FILES, OR if CHANGED_FILES is null:
   → Read the file at finding.file_path around lines finding.line_start
     to finding.line_end
   → Determine: does the issue described in finding.description still exist?

     If YES (issue persists):
       → Carry forward with SAME ID
       → Update line_start/line_end if code shifted
       → If code shifted >10 lines from original, recompute the fingerprint
         (new line_bucket). Note the old ID in a "previous_id" field.

     If NO (issue resolved):
       → Do NOT include in output
       → Add to resolved_ids list

     If FILE DELETED:
       → Do NOT include in output
       → Add to resolved_ids list

### Cost Note on CHANGED_FILES=null

When CHANGED_FILES is null, Phase 1 re-reads every file referenced by previous findings,
and Phase 2 scans the full codebase. This can be MORE expensive than a fresh scan without
carry-forward. For this reason:
- ralph-loop SHOULD always provide CHANGED_FILES (via git diff)
- Full-codebase scans (initial /analyze-codebase) pass CHANGED_FILES=null, which is
  acceptable because there are no PREVIOUS_FINDINGS on first scan
- If PREVIOUS_FINDINGS has >30 findings and CHANGED_FILES is null, the scanner MAY
  skip Phase 1 verification and carry all findings forward tentatively (marking them
  as "unverified" in carry_forward_summary). This prevents token explosion on large
  codebases.

### Phase 2 — Discover New Findings

After verifying all previous findings (or carrying them forward tentatively):

1. Determine scan scope:
   - If CHANGED_FILES is provided: scan ONLY those files for new issues
   - If CHANGED_FILES is null: scan the full codebase

2. For each new finding discovered:
   - Verify it does not duplicate a carried-forward finding
     (same file, overlapping lines within 10-line range)
   - If duplicate → skip (already covered by carried-forward finding)
   - If genuinely new → generate a fingerprint ID per the ID generation rules

### Output

Your DimensionReport output MUST include:

1. All carried-forward findings (with original IDs)
2. All new findings (with new fingerprint IDs)
3. A carry_forward_summary object:

   {
     "carried_forward": <count of findings carried forward>,
     "resolved": <count of findings verified as resolved>,
     "new": <count of genuinely new findings>,
     "resolved_ids": ["ARCH-8f3a21-0370", ...]
   }

### Constraints

- NEVER re-describe a carried-forward finding in different words.
  Copy the title, description, and recommendation verbatim unless the
  code change warrants an update.
- NEVER assign a new ID to a finding that was carried forward unchanged.
- NEVER carry forward a finding without checking CHANGED_FILES first
  (if CHANGED_FILES is available).
```

#### 2.3 Reconciler Changes (reconcile-report)

Updates to `skills/reconcile-report/SKILL.md`:

**Data flow for carry_forward_summary:**

Each scanner agent writes its `DimensionReport` (with `carry_forward_summary`) to `.code-analysis/scan-reports/`. The reconciler reads these scan reports as its input (it already does this — no change to data flow). The reconciler extracts `carry_forward_summary` from each `DimensionReport` and aggregates them into `ScoresReport.scan_metadata`.

**In Step 4d (Delta Analysis):**

```markdown
### Step 4d — Delta Analysis (updated)

With fingerprint-based IDs, delta analysis is now reliable:

- **Resolved**: IDs in PREVIOUS_SCORES findings but not in current → genuinely fixed
- **New**: IDs in current but not in PREVIOUS_SCORES → genuinely new issues
- **Unchanged**: IDs present in both → persistent issues

**Handling merged IDs in delta tracking:**
During dedup (Step 1), findings may be merged. A merged finding gets assigned to
one dimension's ID. The `resolved_ids` from scanner carry_forward_summary use
the scanner's original fingerprint IDs. To reconcile:
1. Build a mapping: {original_scanner_id → merged_id} from the dedup table
2. When computing deltas, check both original and merged IDs
3. A finding is "resolved" if its original scanner ID is in carry_forward_summary.resolved_ids,
   even if the previous ScoresReport stored a different merged ID for it
4. Include both the scanner ID and any mapped merged ID in resolved_finding_ids

Note: previous "new" findings that were actually re-discovered variants of existing
issues no longer occur because carry-forward preserves IDs.
```

**New field in ScoresReport — aggregated from scanner DimensionReports:**

```markdown
### scan_metadata (new, optional)

The reconciler reads carry_forward_summary from each DimensionReport
(already available as input) and aggregates into ScoresReport:

"scan_metadata": {
  "carry_forward_stats": {
    "architecture": {
      "carried_forward": 8,
      "resolved": 3,
      "new": 2
    },
    "quality": {
      "carried_forward": 15,
      "resolved": 0,
      "new": 0
    }
  }
}
```

Add this to the reconciler's **Success Checklist**:
- `[ ] scan_metadata.carry_forward_stats aggregated from DimensionReport.carry_forward_summary (if any scanner provided it)`

#### 2.4 Ralph-Loop Integration

Updates to `skills/ralph-loop/SKILL.md`:

**Step 7 (Re-scan) — Pass CHANGED_FILES:**

```markdown
### Step 7 — Re-scan (updated)

Before invoking analyze-codebase:

1. Compute changed files since last scan:
   git diff --name-only {last_commit_sha}..HEAD

2. Pass as hint to the orchestrator:
   /analyze-codebase --dimensions=DIMENSION --draft-only --skip-critics \
     --changed-files-hint="{comma-separated file list}"

This enables diff-scoped carry-forward: unchanged files' findings are
carried forward without re-reading, dramatically reducing re-scan cost.
```

**completed_finding_ids now reliable:**

With stable fingerprint IDs, the `completed_finding_ids` array in loop-state remains valid across re-scans. When a carried-forward finding's ID matches one in `completed_finding_ids`, it means the finding was resolved in a prior iteration but the re-scan confirmed it's still gone.

### Part 3: Output Schema Updates

#### 3.1 Finding Schema (output-schemas.md)

Add/update these fields in the Finding properties block:

```json
{
  "id": {
    "type": "string",
    "pattern": "^[A-Z]{3,4}-(000000-0000-[0-9a-f]{4}|[0-9a-f]{6}-\\d{4})(-[2-9]\\d*)?$",
    "description": "Deterministic fingerprint: {DIM}-{file_hash6}-{line_bucket} for file findings, {DIM}-000000-0000-{title_hash4} for null-file findings. Collision suffix starts at -2.",
    "examples": ["ARCH-8f3a21-0370", "SEC-000000-0000-a7f2", "QUAL-8f3a21-0370-2"]
  },
  "previous_id": {
    "type": ["string", "null"],
    "default": null,
    "description": "Set when a carried-forward finding's code shifted >10 lines, causing a new fingerprint. Links to the old ID for continuity tracking."
  }
}
```

`previous_id` is NOT in the `required` array — it is optional and defaults to null. It MUST be accepted by schema validators (add to `properties` block, not to `required`). Validators using `additionalProperties: false` must include this field in the properties list.

#### 3.2 DimensionReport Schema (output-schemas.md)

```markdown
DimensionReport.carry_forward_summary (new, optional):
  type: object or null
  properties:
    carried_forward: { type: integer }
    resolved: { type: integer }
    new: { type: integer }
    resolved_ids: { type: array, items: { type: string } }
  description: >
    Present when PREVIOUS_FINDINGS was provided to the scanner.
    Null on first-ever scan of a dimension.
```

#### 3.3 ScoresReport Schema (output-schemas.md)

```markdown
ScoresReport.scan_metadata (new, optional):
  type: object or null
  properties:
    carry_forward_stats:
      type: object
      additionalProperties:
        type: object
        properties:
          carried_forward: { type: integer }
          resolved: { type: integer }
          new: { type: integer }
  description: >
    Aggregated carry-forward statistics across all dimensions.
    Enables quality audit dashboards to show finding churn metrics.
```

### Backwards Compatibility

| Scenario | Behavior |
|----------|----------|
| Old scan reports (sequential IDs) | Treated as `PREVIOUS_FINDINGS = null` on next scan. First post-upgrade scan generates fingerprints; subsequent scans carry forward. |
| Old loop-state.md (old IDs in completed_finding_ids) | IDs won't match new fingerprints. On first re-scan, loop detects no matches and effectively resets tracking. One-time cost. |
| Mixed old/new reports in `.code-analysis/` | Reconciler handles both ID formats. Delta analysis detects old-format reports by checking if ANY finding ID matches `^[a-z-]+-\d{3}$` (the old schema pattern). If detected, the entire report is treated as old-format and delta comparison is skipped (all findings are treated as "new" since IDs cannot be correlated). |
| Scanners that fail to compute hashes | Fallback: scanner can use `{DIM}-000000-{line_bucket}` format (zero file hash, normal line bucket). These are valid fingerprints but will collide with null-file findings if line_bucket is `0000`. Carry-forward treats zero-hash IDs as unstable (no matching). The reconciler accepts them. |

### Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `references/output-schemas.md` | Schema update | Finding.id regex, Finding.previous_id, DimensionReport.carry_forward_summary, ScoresReport.scan_metadata |
| `skills/scan-architecture/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/scan-quality/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/scan-dependencies/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/scan-patterns/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/scan-testing/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/scan-performance/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/scan-security/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/scan-tech-debt/SKILL.md` | Append sections | Finding ID Generation + Carry-Forward Protocol |
| `skills/analyze-codebase/SKILL.md` | Modify Stage 2 | Load PREVIOUS_FINDINGS, pass CHANGED_FILES to scanners |
| `skills/reconcile-report/SKILL.md` | Modify Step 4d | Reliable delta analysis, carry_forward_stats aggregation |
| `skills/ralph-loop/SKILL.md` | Modify Step 7 | Compute and pass CHANGED_FILES hint |

### Expected Impact

| Metric | Before (session evidence) | After (estimated) |
|--------|--------------------------|-------------------|
| Finding churn per re-scan | 3-5 spurious new findings | 0-1 genuinely new |
| Plan staleness events per dimension | 2-3 | 0 |
| Delta tracking reliability | Unreliable (IDs shift) | Reliable (fingerprints stable) |
| Re-scan token cost | Full scan (~100K tokens) | Carry-forward (~30K tokens) |
| Iterations for architecture 1.0→10.0 | 6 iterations | ~3-4 (predictable progression) |
| Total sessions needed per dimension | 11 (with crashes/restarts) | ~2-3 |
| Wall-clock time per dimension | ~9 hours | ~3-4 hours |

### Verification

1. **ID stability test**: Scan a dimension. Make no code changes. Re-scan. Verify 100% of findings have identical IDs.
2. **Carry-forward test**: Scan. Fix one finding. Re-scan. Verify the fixed finding appears in `resolved_ids` and all other findings are carried forward with same IDs.
3. **Diff-scope test**: Scan. Modify one file. Re-scan with CHANGED_FILES. Verify only that file's findings are re-evaluated; others are carried forward without file reads.
4. **Collision test**: Create two findings in the same file within 10 lines. Verify the second gets a `-2` suffix.
5. **Null file_path test**: Verify findings without file_path get `{DIM}-000000-0000-{title_hash4}` IDs.
6. **Backwards compat test**: Run with old scan reports present. Verify first scan generates fingerprints and subsequent scans carry forward.
