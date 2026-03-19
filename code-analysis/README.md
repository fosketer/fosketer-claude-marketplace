# code-analysis

Comprehensive codebase analysis plugin for Claude Code. Scans any language/framework across 8 dimensions, produces scored reports with critic validation, and generates focused refactoring plans. Includes an iterative fix loop (ralph-loop) that implements fixes and re-scans until a target score is reached.

## Quick Start

```bash
# Full analysis (all 8 dimensions)
/analyze-codebase

# Single dimension
/analyze-codebase --dimensions=security

# Automated fix loop (scan → fix → re-scan until score >= 8/10)
/code-analysis:ralph-loop perf 8 --completion-promise "SCORE_REACHED" --max-iterations 4
```

## Architecture

```
/analyze-codebase [path]
    │
Stage 1:  Detect Stack ──────── language-profiles/ + framework-profiles/
    │
Stage 2:  Scan Dimensions ───── 8 code-analyzer agents in PARALLEL
    │                            ├── scan-architecture
    │                            ├── scan-quality
    │                            ├── scan-dependencies
    │                            ├── scan-patterns
    │                            ├── scan-testing
    │                            ├── scan-performance
    │                            ├── scan-security
    │                            └── scan-tech-debt
    │
Stage 3:  Reconcile ─────────── report-reconciler agent (dedup, score, draft)
    │
Stage 4:  Critique Report ───── report-critic agent (max 3 iterations)
    │
Stage 5:  User Checkpoint ───── review scored report, approve/skip/re-scan
    │
Stage 6:  Deep Cross-Analysis ─ root cause clustering across dimensions
    │
Stage 7:  Refactoring Plans ─── per-dimension + orchestrator plan
    │
Stage 8:  Critique Plans ────── plan-critic agent (max 3 iterations)
    │
Stage 9:  User Approval Gate ── mandatory before execution
    │
Stage 10: Persist Outputs ───── .code-analysis/ in target project
```

## Scoring System

Each dimension gets a 1.0–10.0 score:

```
raw = 3 × critical + 2 × high + 1 × medium + 0.5 × low
score = max(1.0, 10 - min(raw, 9))
```

- **10.0** = clean (zero findings or info-only)
- **1.0** = needs attention (raw penalty ≥ 9)
- **Overall** = weighted average of all dimensions

Scores track across runs with delta analysis (new/resolved/unchanged findings).

## Finding IDs (v0.3.0)

Findings use deterministic fingerprint IDs instead of sequential numbering:

```
{DIM}-{file_hash6}-{line_bucket}

Examples:
  ARCH-8f3a21-0370     (file-path finding)
  SEC-000000-0000-a7f2  (null file_path finding)
  QUAL-8f3a21-0370-2    (collision suffix)
```

This ensures the same finding in the same location gets the same ID across scans, enabling reliable delta tracking and cross-session continuity.

## Ralph-Loop (Iterative Fix Loop)

Automates the scan → fix → re-scan cycle for one dimension:

```
/code-analysis:ralph-loop <dimension> <target-score> --completion-promise "SCORE_REACHED" --max-iterations <N>
```

**How it works:**
1. Scans the dimension and generates a refactoring plan
2. Selects 3-5 findings per iteration (XS effort first)
3. Implements fixes via subagent-driven development
4. Commits to main
5. Re-scans with carry-forward (only changed files re-evaluated)
6. Loops until score >= target

**Crash recovery (v0.3.0):** State is checkpointed after each phase (scanning → planning → implementing → committed → rescanning). On restart, the loop resumes from the last completed phase — no re-scanning or re-implementing.

**Carry-forward (v0.3.0):** Re-scans pass `--changed-files-hint` so unchanged files' findings are carried forward without re-reading, reducing token cost by ~70%.

**Dimension flags:**

| Flag | Dimension | Typical Strategy |
|------|-----------|-----------------|
| `arch` | Architecture | Fewest findings, fastest win |
| `debt` | Tech-debt | Many XS/S effort items |
| `security` | Security | Critical findings clear fast |
| `perf` | Performance | Mostly medium items |
| `patterns` | Patterns | Many low-effort structural fixes |
| `deps` | Dependencies | Cargo.toml / package.json updates |
| `quality` | Quality | Largest batch, do after structural fixes |
| `testing` | Testing | Largest effort, do last |

## Analysis Dimensions

| Dimension | Checks |
|-----------|--------|
| **Architecture** | Module structure, dependency graph, layering violations, circular deps |
| **Quality** | Duplication, complexity, dead code, naming conventions |
| **Dependencies** | Outdated, vulnerable, unused, conflicting packages |
| **Patterns** | Design patterns, anti-patterns, framework idiom adherence |
| **Testing** | Coverage gaps, assertion quality, missing edge cases, flaky tests |
| **Performance** | N+1 queries, re-renders, memory leaks, bundle size |
| **Security** | OWASP top 10, hardcoded secrets, injection, auth gaps |
| **Tech Debt** | TODOs, deprecated APIs, legacy patterns, migration opportunities |

## Supported Stacks

| Language | Frameworks |
|----------|-----------|
| Python | — |
| TypeScript | React, Electron |
| C# | .NET, MAUI |
| Dart | Flutter |
| Rust | Tauri |
| Go | — |

Multi-language projects (e.g., Tauri = Rust + TypeScript) supported with multiple profile loading.

## Flags Reference

```
/analyze-codebase [path]
  --dimensions=arch,quality,deps,patterns,testing,perf,security,debt
  --stack=python|typescript|csharp|dart|rust|go
  --framework=react|dotnet|flutter|tauri|electron|maui
  --weights=security:2,architecture:1.5,...
  --critic-iterations=N          (default: 3)
  --skip-critics                 (bypass Stages 4 and 8)
  --draft-only                   (stop after Stage 3)
  --changed-files-hint=file1,file2,...  (diff-scoped carry-forward)
```

## Output Structure

```
.code-analysis/
├── .gitignore
├── overrides.json               # Optional: false_positives + wont_fix
├── scan-reports/
│   ├── 2026-03-19-architecture.json
│   ├── 2026-03-19-quality.json
│   └── ...
├── reports/
│   ├── 2026-03-19-analysis-draft.md
│   ├── 2026-03-19-analysis.md
│   └── 2026-03-19-scores.json
└── plans/
    ├── 2026-03-19-architecture-plan.md
    ├── 2026-03-19-quality-plan.md
    ├── ...
    └── 2026-03-19-orchestrator-plan.md
```

**Overrides file** (`.code-analysis/overrides.json`):
- `false_positives`: excluded from report and score entirely
- `wont_fix`: tagged in report, excluded from score calculation

## Agents

| Agent | Purpose |
|-------|---------|
| `code-analyzer` | Run a single dimension scan in isolation |
| `refactoring-planner` | Generate plans from existing findings |
| `report-reconciler` | Dedup, scoring, draft report assembly |
| `report-critic` | Validate report quality (score calibration, coverage, actionability) |
| `plan-critic` | Validate plan feasibility (dependencies, effort, completeness, risk) |

## Skills

| Skill | User-Invocable | Purpose |
|-------|---------------|---------|
| `analyze-codebase` | Yes | Full 10-stage analysis pipeline |
| `refactor-plan` | Yes | Generate plans from existing analysis |
| `ralph-loop` | Yes | Iterative scan-fix-rescan loop |
| `scan-*` (8) | No | Dimension-specific scan sub-skills |
| `reconcile-report` | No | Dedup and scoring sub-skill |
| `critique-report` | No | Report validation sub-skill |
| `critique-plan` | No | Plan validation sub-skill |
| `generate-refactoring-plan` | No | Per-dimension plan generation |
| `generate-orchestrator-plan` | No | Master plan generation |

## Context7 Integration

When Context7 MCP is available, scanners validate:
- Detected framework versions against documentation
- Dependency versions for known issues
- Framework-specific patterns against current best practices

Gracefully degrades when Context7 is unavailable.

## Plugin Structure

```
code-analysis/
├── .claude-plugin/plugin.json    # v0.3.0
├── skills/                       # 16 skills
│   ├── analyze-codebase/         # Orchestrator (10-stage pipeline)
│   ├── ralph-loop/               # Iterative fix loop with crash recovery
│   ├── refactor-plan/            # Plan generation from existing analysis
│   ├── scan-architecture/        # } 8 dimension scan
│   ├── scan-quality/             # } sub-skills with
│   ├── scan-dependencies/        # } fingerprint IDs
│   ├── scan-patterns/            # } and carry-forward
│   ├── scan-testing/             # } protocol
│   ├── scan-performance/         # }
│   ├── scan-security/            # }
│   ├── scan-tech-debt/           # }
│   ├── reconcile-report/         # Dedup + scoring
│   ├── critique-report/          # Report validation
│   ├── critique-plan/            # Plan validation
│   ├── generate-refactoring-plan/
│   └── generate-orchestrator-plan/
├── agents/                       # 5 agents
│   ├── code-analyzer/
│   ├── refactoring-planner/
│   ├── report-reconciler/
│   ├── report-critic/
│   └── plan-critic/
├── references/
│   ├── analysis-dimensions.md    # 8 dimensions, severity scale, priority tiers
│   ├── output-schemas.md         # Finding, DimensionReport, ScoresReport, etc.
│   ├── language-profiles/        # Python, TypeScript, C#, Dart, Rust, Go
│   └── framework-profiles/       # React, .NET, Flutter, Tauri, Electron, MAUI
├── templates/                    # Report and plan markdown templates
└── docs/superpowers/
    ├── specs/                    # Approved design specs
    └── plans/                    # Implementation plans
```

## Changelog

### v0.3.0 (2026-03-19)
- **Finding ID stability**: Deterministic fingerprint IDs (`{DIM}-{hash}-{line}`) replace sequential numbering
- **Scanner anchoring**: Carry-forward protocol verifies previous findings instead of scanning from scratch
- **Crash recovery**: Phase-based checkpointing in ralph-loop enables session resume
- **Diff-scoped re-scans**: `--changed-files-hint` flag reduces re-scan cost by ~70%

### v0.2.5
- Ralph-loop uses subagent-driven-development
- Agent name resolution fixes
- Context clearing between ralph-loop iterations

### v0.2.0
- 10-stage pipeline redesign (from 6 phases)
- Numeric scoring (1.0–10.0) with critic validation
- Report-reconciler, report-critic, plan-critic agents
- Ralph-loop for iterative dimension improvement
