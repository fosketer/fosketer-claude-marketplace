---
name: refactor-plan
description: |
  This skill should be used when the user asks to "generate refactoring plans", "create a refactoring plan",
  "plan refactoring from analysis", or wants to produce refactoring plans from
  existing codebase analysis results without re-scanning.
  Replaces the deprecated /refactor-plan command.
allowed-tools: Read, Write, Glob, Grep, Agent
---

# Refactor Plan — Generate Refactoring Plans from Analysis

Generate refactoring plans from existing analysis findings without re-scanning the codebase.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

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
/myapp --from-analysis=2026-03-01 --dimensions=security,architecture
/myapp --skip-critics
```

If the target path is relative, resolve it from the current working directory before passing it to the agent.

### Optional Flags

- `--from-analysis` (optional): Which analysis to use. Defaults to `latest`.
  - `latest` — use the most recent scan reports (highest-date directory or file prefix)
  - `YYYY-MM-DD` — use reports from a specific date; fail with a clear message if that date has no reports
- `--dimensions` (optional): Comma-separated list of dimensions to generate plans for. Defaults to all dimensions that have findings.
  - Valid values: `architecture`, `quality`, `dependencies`, `patterns`, `testing`, `performance`, `security`, `tech-debt`
  - Any unrecognized dimension name SHOULD generate a warning, not a hard failure
- `--priority` (optional): Override the default phase assignment strategy.
  - `security-first` (default) — security in Phase 1, then architecture, then rest
  - `architecture-first` — architecture in Phase 1, security and deps in Phase 2
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

You do not need to read the scan reports yourself before dispatching. The agent handles all file access.

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

Dimensions planned: 4 (security, architecture, quality, tech-debt)
Total findings addressed: 31

Execution phases:
  Phase 1 — Quick Wins & Security (security, tech-debt quick): ~0.5d
  Phase 2 — Foundation (architecture): ~1.5d
  Phase 3 — Deep Refactoring (quality, tech-debt deep): ~2d

Plans written:
  .code-analysis/plans/2026-03-20-security-plan.md
  .code-analysis/plans/2026-03-20-architecture-plan.md
  .code-analysis/plans/2026-03-20-quality-plan.md
  .code-analysis/plans/2026-03-20-tech-debt-plan.md
  .code-analysis/plans/2026-03-20-orchestrator-plan.md

Critic: passed on iteration 1
Warnings: none
```

## Relationship Between Flags and Agent Behavior

Understanding how flags affect the agents helps debug unexpected plan outputs.

### --from-analysis

This flag is passed directly to the `refactoring-planner` agent as the `DATE_FILTER` input. The agent uses it to select which set of JSON report files to load from `.code-analysis/scan-reports/`. Report files are named with a `YYYY-MM-DD-` prefix; the agent selects files whose prefix matches the requested date.

When `latest` is used (the default), the agent picks the highest date prefix present in the directory. If two scans were run on the same date, the agent loads the most recently modified files.

### --dimensions

This flag causes the agent to skip plan generation for dimensions not listed. However, the agent still loads all scan reports to build the orchestrator plan's dependency graph correctly — it only omits per-dimension plans for excluded dimensions. This means the orchestrator plan may reference fewer dimensions than the full analysis covered.

When the `plan-critic` runs, it will check whether excluded dimensions have findings in `scores.json`. If they do, it will raise a `completeness-gap` warning. This is expected behavior when `--dimensions` is used intentionally to focus on a subset.

### --priority and critic ordering checks

The `--priority` flag affects only the `generate-orchestrator-plan` sub-skill's phase assignment logic. The `plan-critic` agent is aware of the active priority override and adjusts its ordering checks accordingly: for example, with `--priority=architecture-first`, the critic will not flag architecture being in Phase 1 as an ordering error.

The one exception is the security rule: `plan-critic` ALWAYS flags security being outside Phase 1 regardless of the `--priority` setting. This check cannot be overridden.

## Edge Cases

### No findings after filtering

If all scan reports contain only `info`-severity findings, the refactoring-planner will return empty per-dimension plans. In this case:
- Do not write empty plan files
- Report: "Codebase is clean — no non-info findings require planning."

### Specific date requested but not found

If `--from-analysis=2026-01-15` is given and no reports exist for that date:
- List available report dates from `.code-analysis/scan-reports/` using Glob
- Report the available dates and ask the user to choose one or use `latest`

### Dimensions filter results in empty set

If `--dimensions=testing` is given but the `testing` scan report has zero findings:
- Warn the user that the selected dimension has no actionable findings
- Offer to plan for all available dimensions instead

### --priority=quick-wins-first with critical security findings

Even when `quick-wins-first` is set, security findings classified as `critical` severity MUST be surfaced prominently. The refactoring-planner will still include them in Phase 1 because the `security-first` rule overrides effort-based sorting for critical findings. If the user's chosen strategy conflicts with this, issue a warning in the summary.

## Error Handling

| Scenario | Resolution |
|----------|------------|
| No `.code-analysis/scan-reports/` directory | Stop. Tell user to run `analyze-codebase` first. |
| scores.json missing or unreadable | Warn; proceed with plan generation, but note critic will skip score-based checks. |
| refactoring-planner agent fails | Surface the error message to the user; do not silently retry more than once. |
| plan-critic agent fails (not verdict=fail, but actual agent error) | Skip remaining critic iterations; present plan with a note that critic validation was skipped due to an agent error. |
| `--critic-iterations=0` | Clamp to 1 with warning. Zero iterations is equivalent to `--skip-critics`. |
| Plan files already exist for the target date | Overwrite them; include a note in the summary that prior plan files were replaced. |
