---
name: analyze-codebase
version: 0.7.0
description: |
  This skill should be used when the user asks to "analyze this codebase", "scan for issues",
  "find refactoring opportunities", "code analysis", "audit this project",
  or wants a comprehensive multi-dimension codebase analysis with refactoring plans.
  This skill should also be used when the user asks to "analyze architecture", "analyze structure", "check code quality",
  "scan for security issues", "find tech debt", or similar dimension-specific requests.
  When used with --plugin flag, analyzes Claude Code plugins across 8 plugin-specific
  dimensions including manifest structure, skill quality, agent design, and conventions.
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent", "AskUserQuestion", "mcp__claude_ai_Context7__resolve-library-id", "mcp__claude_ai_Context7__query-docs"]
---

# Analyze Codebase — Orchestrator

Comprehensive codebase analysis across 4 standard dimensions (structure, quality, security, testing) with scoring, critic validation, and refactoring plans. Supports any language/framework.


## Pipeline

```
Stage 1:  Detect Stack (sequential) — or Detect Plugin Structure when --plugin
    |
Stage 2:  Scan All Dimensions (ALL 4 in parallel, or 8 in --plugin mode)
    |
Stage 3:  Reconcile (report-reconciler agent — dedup, score, draft report)
    |         -> Auto-persist draft reports to disk
    |
Stage 4:  Critique Report (report-critic agent)
    |         -> Feedback loop: max N iterations, then surface to user
    |
Stage 5:  User Checkpoint (review scored report, approve/skip/re-scan)
    |         -> Finalize reports on disk (overwrite drafts)
    |
Stage 6:  Deep Cross-Analysis + Refactoring Plans (only if user approves at Stage 5)
    |         -> Cross-dimension root cause analysis
    |         -> Per-dimension refactoring plans
    |
Stage 7:  Orchestrator Plan Generation
    |
Stage 8:  Critique Plan (plan-critic agent)
    |         -> Feedback loop: max N iterations, then surface to user
    |
Stage 9:  User Approval Gate (mandatory)
    |
Stage 10: Persist All Final Outputs
```

## Input

Target path: $ARGUMENTS (default: current working directory)

### Optional Flags

- `--dimensions=struct,quality,security,testing` — restrict dimensions (default: all 4). Aliases: `arch`→structure, `patterns`→structure, `deps`→testing+security, `perf`→quality, `debt`→quality
- `--stack=python|typescript|csharp|dart|rust|go` — override auto-detected language
- `--framework=react|dotnet|flutter|tauri|electron|maui` — override auto-detected framework
- `--weights=dim:N,...` — custom dimension weights for overall score (default: all 1.0). Partial overrides allowed (unspecified dimensions default to 1.0).
- `--critic-iterations=N` — max critic feedback loop iterations (default: 3)
- `--skip-critics` — bypass critic loops entirely (skip Stages 4 and 8)
- `--draft-only` — stop after Stage 3 (scan + reconcile + persist draft, no user interaction)
- `--changed-files-hint=<comma-separated file paths>` — passed by ralph-loop to enable diff-scoped carry-forward. Optional. When absent, scanners do full scans.
- `--model=<model-spec>` — override model for agent dispatch. Accepts:
  - Blanket: `--model opus` (all stages use opus)
  - Per-stage: `--model scanning:haiku,critique:opus` (override specific stages)
  - Mixed: `--model opus,critique:sonnet` (blanket first, then per-stage overrides on top)
  - Valid model values: `haiku`, `sonnet`, `opus`, `inherit`
  - Stages: `scanning`, `reconciliation`, `critique`, `planning`
  - Unspecified stages fall through to config files or `inherit`
- `--plugin` — activate plugin analysis mode. Swaps dimension set to 8 plugin-specific dimensions (2 adapted standard + 6 new). Requires target to contain `.claude-plugin/plugin.json`.

## Context Efficiency Rules

The orchestrator is a **thin dispatcher**. To minimize context consumption:

1. **MUST NOT read scanner sub-skills** (`scan-*/SKILL.md`) — subagents read them
2. **MUST NOT read reconciliation sub-skill** (`reconcile-report/SKILL.md`) — the reconciler agent reads it
3. **MUST NOT read critic sub-skills** (`critique-report/SKILL.md`, `critique-plan/SKILL.md`) — critic agents read them
4. **MUST NOT read output-schemas.md** — subagents and agents read what they need
5. **MUST NOT read language/framework profiles** — loaded by subagents
6. **MUST NOT read templates** — the reconciler and planner agents use them
7. **MAY read `analysis-dimensions.md`** in Stage 5 for severity definitions when presenting to user

The orchestrator handles: flag parsing, stack detection, agent dispatch, feedback loops, user checkpoints, and final persistence coordination.

## Execution Protocol

### Stage 0 — Load Prior State

Before detecting the stack, check for previous scan data and user overrides:

1. **Previous scores** (delta analysis): Check if `.code-analysis/reports/*-scores.json` exists with an older date
   - If found: Load the most recent `scores.json` as `PREVIOUS_SCORES`
   - Pass `PREVIOUS_SCORES` to the reconciler in Stage 3 — it will generate the Run Delta section
   - If not found: `PREVIOUS_SCORES = null`

2. **Override file** (false positive suppression): Check if `.code-analysis/overrides.json` exists
   - If found: Load and pass as `OVERRIDES` to the reconciler in Stage 3
   - If not found: `OVERRIDES = null`
   - Create the file with empty arrays if the user wants to add overrides later — do NOT create it automatically

3. **Model resolution** (per-stage model map): Resolve model overrides per `${CLAUDE_PLUGIN_ROOT}/skills/analyze-codebase/references/model-resolution.md`.

### Stage 1 — Detect Stack

Identify languages and frameworks by reading the project root for manifest files:

- `package.json` → TypeScript/JavaScript + React/Electron
- `*.csproj` / `*.sln` → C# + .NET/MAUI
- `Cargo.toml` → Rust + Tauri
- `pubspec.yaml` → Dart + Flutter
- `go.mod` → Go
- `pyproject.toml` / `requirements.txt` / `setup.py` → Python
- `tauri.conf.json` → Tauri

Check for multi-language projects (e.g., Tauri = Rust + TypeScript). Read `CLAUDE.md` if it exists. Apply `--stack` / `--framework` overrides.

**Output**: `STACK = { languages: [], frameworks: [] }`

**When `--plugin` is set:** Stage 1 becomes Detect Plugin Structure. Follow `${CLAUDE_PLUGIN_ROOT}/skills/analyze-codebase/references/plugin-mode.md` — Stage 1 section.

### Stage 2 — Scan All Dimensions (Full Parallel)

Parse `--dimensions` flag. Default: all 4.

Dimension map: `struct` → structure, `quality`, `security`, `testing`. Backwards-compat aliases: `arch` → structure, `patterns` → structure, `deps` → (adds both security + testing if not already present), `perf` → quality, `debt` → quality.

When `--plugin` is set, use plugin dimension map and validation from `${CLAUDE_PLUGIN_ROOT}/skills/analyze-codebase/references/plugin-mode.md` — Plugin Dimension Map section.

**Dispatch ALL `code-analyzer` subagents in parallel** (no batching):

For each dimension, dispatch an Agent with:
```
Analyze the codebase at [PROJECT_PATH] for the [DIMENSION] dimension.
Stack: [STACK.languages], Framework: [STACK.frameworks].
Return ONLY a structured JSON findings array. Each finding: { id, dimension, title, severity, location, description, recommendation, effort, tags }.
Include a summary header: { dimension, total, critical, high, medium, low, info }.
```

Collect all findings arrays from subagent responses.

Additional parameters for each code-analyzer agent:
- SCAN_REPORTS_DIR: ".code-analysis/scan-reports"
  (Path hint — the scanner loads its own previous findings from this directory.
   The orchestrator MUST NOT read scan reports itself.)
- CHANGED_FILES: <array of relative file paths, or null>
  (If --changed-files-hint flag was provided, split the comma-separated value
   into an array and pass it here. If the flag was not provided, pass null.
   Scanners use this for diff-scoped carry-forward.)
- Model: `MODEL_MAP.scanning` (pass as `model` parameter if not "inherit")

**Fallback**: If the platform limits concurrent agents, dispatch in batches of 4. Prefer full parallelism.

**IMPORTANT**: Findings MUST be kept as compact JSON — do NOT expand into verbose descriptions in the main context.

**When `--plugin` is set:** Follow plugin dispatch parameters and message template from `${CLAUDE_PLUGIN_ROOT}/skills/analyze-codebase/references/plugin-mode.md` — Stage 2 section.

### Stage 3 — Reconcile (report-reconciler agent)

Dispatch the `report-reconciler` agent with:
- All dimension findings arrays
- Stack information
- Project path
- Weights from `--weights` flag (or default)
- `PREVIOUS_SCORES` from Stage 0 (null if first scan)
- `OVERRIDES` from Stage 0 (null if no override file)
- Model: `MODEL_MAP.reconciliation` (pass as `model` parameter if not "inherit")

The agent will:
1. Deduplicate cross-dimension findings
2. Compute per-dimension scores (0-10) and overall weighted score
3. Produce unified draft report
4. Auto-persist draft to `.code-analysis/reports/YYYY-MM-DD-analysis-draft.md`
5. Auto-persist scores to `.code-analysis/reports/YYYY-MM-DD-scores.json`
6. Auto-persist raw scan reports to `.code-analysis/scan-reports/YYYY-MM-DD-{dimension}.json`

**If `--draft-only`**: Stop here. Present the overall score and dimension scores summary to the user. Exit.

### Stage 4 — Critique Report (report-critic agent)

**Skip if `--skip-critics` is set.**

Run the critic feedback loop:

```
attempt = 0
max_iterations = --critic-iterations (default: 3)
loop:
  if attempt >= max_iterations:
    present all accumulated issues to user
    ask: proceed anyway or abort?
    break
  dispatch report-critic agent with:
    - draft report path
    - scores.json path
    - scan-reports directory path
    - stack, project path
    - iteration: attempt + 1
    - prior feedback (from previous iteration, null on first)
    - model: MODEL_MAP.critique (pass as `model` parameter if not "inherit")
  if critic returns verdict "pass":
    break
  dispatch report-reconciler agent with:
    - same findings
    - critic feedback
    - model: MODEL_MAP.reconciliation (pass as `model` parameter if not "inherit")
  attempt++
```

### Stage 5 — User Checkpoint ← CHECKPOINT

Present to the user:
1. Overall codebase health score
2. Per-dimension score table (including True Raw and Est. Iterations columns)
3. Dedup statistics
4. Ralph-loop iteration estimates table (3 targets per dimension)
5. Recommended ralph-loop order (dimensions sorted by full_quality iterations ascending)
6. Cross-cutting observations (from draft report)
7. Critic status (passed / passed with warnings / user-overridden)

Ask the user:
- **Proceed to refactoring plans?** (continues to Stage 6)
- **Stop here?** (finalize reports, skip Stages 6-10)
- **Re-scan specific dimensions?** (loop back to Stage 2 for those dimensions, then re-reconcile)

**CRITICAL**: MUST pause and wait for user confirmation.

**Finalize reports**: Rename draft to final (`analysis-draft.md` → `analysis.md`). `scores.json` requires no renaming — it is persisted in final form at Stage 3.

### Stage 6 — Deep Cross-Analysis + Refactoring Plans

**Only if user chose to proceed at Stage 5.**

#### Step 6a: Deep Cross-Analysis

Dispatch `report-reconciler` agent with `--deep` flag:
- All dimension findings
- Stack, project path
- Model: `MODEL_MAP.reconciliation` (pass as `model` parameter if not "inherit")

The agent returns CrossAnalysis JSON (root causes, systemic patterns, combined fixes). This is NOT persisted — used as input to planning.

#### Step 6b: Generate Refactoring Plans

Dispatch the `refactoring-planner` agent with:
- All dimension findings (excluding user-skipped dimensions and info-only dimensions)
- Cross-analysis results from Step 6a
- Stack, project path
- Model: `MODEL_MAP.planning` (pass as `model` parameter if not "inherit")

The agent loads `generate-refactoring-plan/SKILL.md` internally — the orchestrator MUST NOT read it.

### Stage 7 — Orchestrator Plan Generation

The `refactoring-planner` agent (dispatched in Stage 6b) also generates the orchestrator plan as part of its workflow (Steps 3-4 in its agent definition). It loads `generate-orchestrator-plan/SKILL.md` internally — the orchestrator MUST NOT read it.

The orchestrator collects the master plan from the agent's output.

### Stage 8 — Critique Plan (plan-critic agent)

**Skip if `--skip-critics` is set.**

Run the same critic feedback loop pattern as Stage 4, but with:
- `plan-critic` agent instead of `report-critic`
- `refactoring-planner` agent as the producer (re-dispatched with critic feedback)
- Model for plan-critic: `MODEL_MAP.critique` (pass as `model` parameter if not "inherit")
- Model for refactoring-planner re-dispatch: `MODEL_MAP.planning` (pass as `model` parameter if not "inherit")
- Same max iterations from `--critic-iterations`

### Stage 9 — User Approval Gate ← MANDATORY GATE

Present to user:
- Execution phases with dimension assignments
- Dependency graph (Mermaid)
- Effort summary
- Verification strategy
- Critic status

**CRITICAL**: MUST NOT proceed to Stage 10 until user explicitly approves.

### Stage 10 — Persist All Final Outputs

Dispatch the `refactoring-planner` agent for persistence (Step 5 in its agent definition):
- Model: `MODEL_MAP.planning` (pass as `model` parameter if not "inherit")
- It reads templates internally (`refactoring-plan.md`, `orchestrator-plan.md`) — the orchestrator MUST NOT read them
- It writes to `.code-analysis/plans/`:
  - `YYYY-MM-DD-{dimension}-plan.md` — per-dimension plans
  - `YYYY-MM-DD-orchestrator-plan.md` — master plan

Reports and scores were already persisted at Stage 3/5 — do NOT overwrite.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No project manifests found | Ask user for `--stack` and `--framework` |
| Context7 MCP unavailable | Skip library validation, note limitation |
| Dimension scan zero findings | Score 10.0, skip plan for that dimension |
| All dimensions clean | Score 10/10, congratulate user, skip Stages 6-10 |
| User skips all at Stage 5 | Finalize reports, end |
| Very large project (>5000 files) | Warn, suggest `--dimensions` to focus |
| Stage 3/5 directory has today's reports | If `--draft-only` is set: always overwrite (automated context, no user to ask). Otherwise: ask user to overwrite or append timestamp suffix |
| `.code-analysis/overrides.json` references non-existent finding ID | Log warning in report: "Override ID X not found in current findings"; proceed normally |
| Previous scores.json found but dimensions don't match | Generate partial delta (compare matching dimensions only), note discrepancy. If previous scores use old 8-dim names, skip delta (backwards compat). |
| Critic loop exhausted | Present all issues to user, ask proceed or abort |
| Platform limits concurrent agents | Fall back to batches of 4 |
| report-reconciler fails | Retry once, then surface error to user |
