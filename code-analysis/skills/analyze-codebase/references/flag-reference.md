# Flag Reference — analyze-codebase

## Dimension Aliases

When parsing the `--dimensions` flag, apply the following alias expansion:

| Alias | Expands to |
|-------|-----------|
| `struct` | `structure` |
| `arch` | `structure` |
| `patterns` | `structure` |
| `perf` | `quality` |
| `debt` | `quality` |
| `deps` | `security` + `testing` (both added if not already present) |

All other values are treated as literal dimension names. Unrecognized values SHOULD generate a warning, not a hard failure.

## Model-Passing Syntax (`--model`)

The `--model` flag controls which model is used for each stage of the pipeline. It accepts:

- **Blanket override**: `--model opus` — all stages use opus
- **Per-stage override**: `--model scanning:haiku,critique:opus` — override specific stages only
- **Mixed**: `--model opus,critique:sonnet` — blanket first, then per-stage overrides on top

Valid model values: `haiku`, `sonnet`, `opus`, `inherit`

Stage keys:
| Key | Controls |
|-----|---------|
| `scanning` | All scanner subagents (Stage 2) |
| `reconciliation` | report-reconciler agent (Stages 3, 6a) |
| `critique` | report-critic and plan-critic agents (Stages 4, 8) |
| `planning` | refactoring-planner agent (Stages 6b, 7, 10) |

Unspecified stages fall through to config files or `inherit` (use the default model for the current session).

When passing model to an agent dispatch, only include the `model` parameter if the resolved value is not `"inherit"`.
