# Flag Behavior and Agent Interaction

Understand how flags affect the agents to debug unexpected plan outputs.

## --from-analysis

Pass this flag directly to the `refactoring-planner` agent as the `DATE_FILTER` input. The agent uses it to select which set of JSON report files to load from `.code-analysis/scan-reports/`. Report files are named with a `YYYY-MM-DD-` prefix; the agent selects files whose prefix matches the requested date.

When `latest` is used (the default), the agent picks the highest date prefix present in the directory. If two scans were run on the same date, the agent loads the most recently modified files.

## --dimensions

This flag causes the agent to skip plan generation for dimensions not listed. However, the agent still loads all scan reports to build the orchestrator plan's dependency graph correctly — it only omits per-dimension plans for excluded dimensions. This means the orchestrator plan may reference fewer dimensions than the full analysis covered.

When the `plan-critic` runs, it will check whether excluded dimensions have findings in `scores.json`. If they do, it will raise a `completeness-gap` warning. This is expected behavior when `--dimensions` is used intentionally to focus on a subset.

## --priority and critic ordering checks

The `--priority` flag affects only the `generate-orchestrator-plan` sub-skill's phase assignment logic. The `plan-critic` agent is aware of the active priority override and adjusts its ordering checks accordingly: for example, with `--priority=architecture-first`, the critic will not flag structure being in Phase 1 as an ordering error.

The one exception is the security rule: `plan-critic` ALWAYS flags security being outside Phase 1 regardless of the `--priority` setting. This check cannot be overridden.

## Edge Cases for Flag Combinations

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
