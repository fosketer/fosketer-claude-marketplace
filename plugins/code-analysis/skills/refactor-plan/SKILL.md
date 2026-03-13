---
name: refactor-plan
description: |
  Use when the user asks to "generate refactoring plans", "create a refactoring plan",
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

## Input

Target path: $ARGUMENTS

If no argument provided, use the current working directory.

### Optional Flags

- `--from-analysis` (optional): Which analysis to use. Defaults to `latest`.
  - `latest` — use the most recent scan reports
  - `YYYY-MM-DD` — use reports from a specific date
- `--dimensions` (optional): Comma-separated list of dimensions to generate plans for. Defaults to all dimensions that have findings.
- `--priority` (optional): Override the default phase assignment strategy.
  - `security-first` (default) — security in Phase 1, then architecture, then rest
  - `architecture-first` — architecture in Phase 1, security and deps in Phase 2
  - `quick-wins-first` — all low-effort findings in Phase 1 regardless of dimension
- `--skip-critics` (optional): Skip the plan-critic feedback loop. Default: false.
- `--critic-iterations=N` (optional): Max critic feedback iterations. Default: 3.

## Execution

Dispatch the `refactoring-planner` agent with `$ARGUMENTS` as input.

If `--skip-critics` is NOT set:
1. After the refactoring-planner produces the orchestrator plan, dispatch the `plan-critic` agent
2. If the critic returns `"verdict": "fail"`, re-dispatch the `refactoring-planner` with the critic feedback
3. Repeat up to `--critic-iterations` times (default: 3)
4. If the critic still fails after max iterations, present all accumulated issues to the user

If no prior analysis is found at the target path, inform the user and suggest running the `analyze-codebase` skill first.
