---
name: refactor-plan
version: 0.7.0
description: |
  This skill should be used when the user asks to "generate refactoring plans", "create a refactoring plan",
  "plan refactoring from analysis", or wants to produce refactoring plans from
  existing codebase analysis results without re-scanning.
allowed-tools: ["Read", "Write", "Glob", "Grep", "Agent"]
---

# Refactor Plan — Generate Refactoring Plans from Analysis

Generate refactoring plans from existing analysis findings without re-scanning the codebase.


## Prerequisites

The target project MUST have prior analysis results in `.code-analysis/scan-reports/`. Run the `analyze-codebase` skill first if no prior results exist.

Before dispatching the `refactoring-planner` agent, verify that the directory exists and contains at least one JSON report file. Use Glob to check for `{target_path}/.code-analysis/scan-reports/*.json`. If nothing is found, stop and tell the user:

> No analysis results found at `{target_path}/.code-analysis/scan-reports/`. Run `analyze-codebase {target_path}` first, then re-run `refactor-plan`.

## Input

Target path: $ARGUMENTS

If no argument provided, use the current working directory.

### Argument Parsing

Parse `$ARGUMENTS` left to right. The first token that does not start with `--` is the target path. All remaining tokens are flags.

Examples:

```
/myapp --priority=security-first
/myapp --from-analysis=2026-03-01 --dimensions=security,structure
/myapp --skip-critics
```

If the target path is relative, resolve it from the current working directory before passing it to the agent.

### Optional Flags

- `--from-analysis` (optional): Which analysis to use. Defaults to `latest`.
  - `latest` — use the most recent scan reports (highest-date directory or file prefix)
  - `YYYY-MM-DD` — use reports from a specific date; fail with a clear message if that date has no reports
- `--dimensions` (optional): Comma-separated list of dimensions to generate plans for. Defaults to all dimensions that have findings.
  - Valid values: `structure`, `quality`, `security`, `testing`. Aliases: `arch`→structure, `patterns`→structure, `deps`→testing+security, `perf`→quality, `debt`→quality
  - Any unrecognized dimension name SHOULD generate a warning, not a hard failure
- `--priority` (optional): Override the default phase assignment strategy.
  - `security-first` (default) — security in Phase 1, then structure, then rest
  - `architecture-first` — structure in Phase 1, security alongside
  - `quick-wins-first` — all low-effort findings in Phase 1 regardless of dimension
- `--skip-critics` (optional): Skip the plan-critic feedback loop. Default: false.
- `--critic-iterations=N` (optional): Max critic feedback iterations. Default: 3. Must be between 1 and 5 inclusive; values outside this range MUST be clamped with a warning.

## How This Skill Fits the Plugin Pipeline

This skill is the entry point for the planning stage of the `code-analysis` plugin workflow. The full pipeline is:

```
analyze-codebase  →  refactor-plan  →  (manual execution)
      ↓                   ↓
  scan-reports/       plans/
  scores.json         orchestrator-plan.md
  cross-analysis.json dimension-plan.md (one per dimension)
```

`refactor-plan` does not scan the codebase. It reads the outputs of `analyze-codebase` and delegates all plan generation work to the `refactoring-planner` agent. This agent in turn calls two sub-skills internally:

- `generate-refactoring-plan`: called once per dimension with findings; produces a `RefactoringPlan` JSON
- `generate-orchestrator-plan`: called once after all dimension plans are ready; produces the `OrchestratorPlan` JSON

This skill's only responsibilities are:
1. Validating prerequisites (scan reports exist)
2. Parsing and forwarding user arguments
3. Running the `plan-critic` feedback loop
4. Presenting the final summary

The `refactoring-planner` agent handles all file reads and writes. Do not read scan reports or write plan files directly from this skill.

### Output files written by the refactoring-planner

The agent writes the following files into the target project's `.code-analysis/plans/` directory:

| File | Contents |
|------|----------|
| `YYYY-MM-DD-{dimension}-plan.md` | Per-dimension refactoring plan (one file per dimension with findings) |
| `YYYY-MM-DD-orchestrator-plan.md` | Master sequenced execution plan with phase assignments and dependency graph |

If a `plans/` subdirectory does not yet exist, the agent creates it. Existing plan files for the same date are overwritten.

## Execution

### Phase 1 — Dispatch refactoring-planner

Dispatch the `refactoring-planner` agent with the resolved target path and all parsed flags as input.

The `refactoring-planner` agent will:
1. Load existing scan reports from `.code-analysis/scan-reports/`
2. Generate per-dimension refactoring plans by calling the `generate-refactoring-plan` sub-skill for each dimension
3. Combine them into a master orchestrator plan using the `generate-orchestrator-plan` sub-skill
4. Write all plan files to `.code-analysis/plans/`

Do not read the scan reports before dispatching. The agent handles all file access.

### Phase 2 — Critic feedback loop (unless --skip-critics)

After the `refactoring-planner` completes and returns an orchestrator plan:

1. Dispatch the `plan-critic` agent, passing:
   - The orchestrator plan (OrchestratorPlan JSON)
   - All per-dimension plans (array of RefactoringPlan JSON objects)
   - The reconciled scores report (read from `.code-analysis/scan-reports/scores.json`)
   - Cross-analysis results if available at `.code-analysis/scan-reports/cross-analysis.json` (pass null otherwise)
   - `ITERATION: 1`
   - `PRIOR_FEEDBACK: null`

2. Inspect the critic's `CriticFeedback` response:

   **If `verdict == "pass"`**: The plan is acceptable. Proceed to presenting the summary.

   **If `verdict == "fail"`**:
   - Collect all blocking issues from `feedback.issues`
   - Re-dispatch the `refactoring-planner` with the original inputs plus `CRITIC_FEEDBACK: <feedback JSON>`
   - Increment iteration counter
   - Re-dispatch the `plan-critic` with `ITERATION: N` and `PRIOR_FEEDBACK: <previous feedback>`

3. Repeat step 2 up to `--critic-iterations` times (default: 3).

4. If the critic still returns `verdict == "fail"` after the maximum number of iterations, do NOT silently accept the plan. Instead:
   - Present all accumulated blocking issues to the user as a numbered list
   - Show the last version of the plan
   - Ask the user whether to accept the plan as-is or make manual corrections

### Example: critic feedback loop (iteration 2)

```
Iteration 1: plan-critic returns fail
  issues:
    - { category: "ordering-error", severity: "blocking",
        description: "SEC findings in Phase 2, not Phase 1",
        suggestion: "Move scan-security to Phase 1" }

→ Re-dispatch refactoring-planner with critic feedback
→ refactoring-planner corrects phase assignment for scan-security

Iteration 2: plan-critic returns pass
  issues: []

→ Plan accepted, proceed to summary
```

### Phase 3 — Present summary

After the critic loop completes (pass or escalation to user), output:

- Number of dimensions planned
- Total findings covered by the plan
- Execution phases (phase number, name, dimensions included, estimated effort)
- File paths of all written plan files
- Whether the plan passed the critic on the first attempt or required iterations
- Any warning-severity issues from the final critic pass (list them even if verdict is pass)

Example summary:

```
Refactoring plans generated for /myapp

Dimensions planned: 3 (security, structure, quality)
Total findings addressed: 31

Execution phases:
  Phase 1 — Security (security): ~0.5d
  Phase 2 — Foundation (structure): ~1.5d
  Phase 3 — Deep Refactoring (quality): ~2d

Plans written:
  .code-analysis/plans/2026-03-20-security-plan.md
  .code-analysis/plans/2026-03-20-structure-plan.md
  .code-analysis/plans/2026-03-20-quality-plan.md
  .code-analysis/plans/2026-03-20-orchestrator-plan.md

Critic: passed on iteration 1
Warnings: none
```

## Relationship Between Flags and Agent Behavior

For details on how flags affect agent behavior, Read `${CLAUDE_PLUGIN_ROOT}/skills/refactor-plan/references/flag-behavior.md`

## Edge Cases

### No findings after filtering

If all scan reports contain only `info`-severity findings, the refactoring-planner will return empty per-dimension plans. In this case:
- Do not write empty plan files
- Report: "Codebase is clean — no non-info findings require planning."

## Error Handling

| Scenario | Resolution |
|----------|------------|
| No `.code-analysis/scan-reports/` directory | Stop. Tell user to run `analyze-codebase` first. |
| scores.json missing or unreadable | Warn; proceed with plan generation, but note critic will skip score-based checks. |
| refactoring-planner agent fails | Surface the error message to the user; do not silently retry more than once. |
| plan-critic agent fails (not verdict=fail, but actual agent error) | Skip remaining critic iterations; present plan with a note that critic validation was skipped due to an agent error. |
| `--critic-iterations=0` | Clamp to 1 with warning. Zero iterations is equivalent to `--skip-critics`. |
| Plan files already exist for the target date | Overwrite them; include a note in the summary that prior plan files were replaced. |
