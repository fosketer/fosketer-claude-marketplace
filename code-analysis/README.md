# code-analysis

Comprehensive codebase analysis plugin for Claude Code. Scans any language/framework across 4 standard dimensions (plus 6 plugin-analysis dimensions with `--plugin`), produces scored reports with critic validation, and generates focused refactoring plans. Includes an iterative fix loop (ralph-loop) that implements fixes and re-scans until a target score is reached.

## Quick Start

```bash
# Full analysis (all 4 standard dimensions)
/analyze-codebase

# Single dimension
/analyze-codebase --dimensions=security

# Automated fix loop (scan → fix → re-scan until score >= 8/10)
/code-analysis:ralph-loop quality 8 --completion-promise "SCORE_REACHED" --max-iterations 4
```

## Architecture

```
/analyze-codebase [path]
    │
Stage 1:  Detect Stack ──────── language-profiles/ + framework-profiles/
    │
Stage 2:  Scan Dimensions ───── 4 code-analyzer agents in PARALLEL
    │                            ├── scan-structure (arch + patterns)
    │                            ├── scan-quality (quality + tech-debt + perf)
    │                            ├── scan-security (security + CVE checks)
    │                            └── scan-testing (testing + dep hygiene)
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
- **true_raw** = unclipped penalty (not capped at 9), reveals actual magnitude behind floor scores
- **Iteration estimates** = predicted ralph-loop iterations to reach 5/10, 8/10, or 10/10 per dimension

Scores track across runs with delta analysis (new/resolved/unchanged findings). Iteration estimates help prioritize which dimensions to ralph-loop first by showing effort efficiency — dimensions with fewer estimated iterations yield faster score improvements.

## Finding IDs (v0.5.0)

Findings use deterministic fingerprint IDs instead of sequential numbering:

```
{DIM}-{file_hash6}-{title_hash4}

Examples:
  ARCH-8f3a21-a1b2     (file-path finding)
  SEC-000000-a7f2      (null file_path finding)
  QUAL-8f3a21-a1b2-2   (collision suffix)
```

IDs use a title hash (not line numbers) so the same finding keeps the same ID even when code is refactored and lines shift. This ensures reliable delta tracking and cross-session continuity.

## Ralph-Loop (Iterative Fix Loop)

Automates the scan → fix → re-scan cycle for one dimension:

```
/code-analysis:ralph-loop <dimension> <target-score> --completion-promise "SCORE_REACHED" --max-iterations <N>
```

**Multi-dimension** (v0.4.0) — scan multiple dimensions together, fix with per-dimension targets:

```
/code-analysis:ralph-loop --targets="structure:8,quality:9" --completion-promise "SCORE_REACHED" --max-iterations 10
```

All target dimensions are scanned together each iteration, so cross-cutting findings (god structs, race conditions spanning multiple concerns) are caught. Findings are prioritized by a gap-weighted algorithm — dimensions furthest from target get fixed first.

**How it works:**
1. Scans the dimension and generates a refactoring plan
2. Selects 3-5 findings per iteration (XS effort first)
3. Implements fixes via subagent-driven development
4. Commits to main
5. Re-scans with carry-forward (only changed files re-evaluated)
6. Loops until score >= target
7. **Multi-dimension:** When using `--targets`, all dimensions are scanned together and findings are selected across dimensions using gap-weighted priority

**Crash recovery (v0.3.0):** State is checkpointed after each phase (scanning → planning → implementing → committed → rescanning). On restart, the loop resumes from the last completed phase — no re-scanning or re-implementing.

**Carry-forward (v0.3.0):** Re-scans pass `--changed-files-hint` so unchanged files' findings are carried forward without re-reading, reducing token cost by ~70%.

**Dimension flags:**

| Flag | Dimension | Aliases | Typical Strategy |
|------|-----------|---------|-----------------|
| `structure` | Structure | arch, patterns | Module structure, patterns, anti-patterns |
| `quality` | Quality | debt, perf | Duplication, complexity, tech debt, performance |
| `security` | Security | — | OWASP top 10, secrets, CVE checks |
| `testing` | Testing | deps | Coverage, test quality, dependency hygiene |

## Analysis Dimensions

| Dimension | Checks |
|-----------|--------|
| **Structure** | Module structure, dependency graph, layering violations, circular deps, design patterns, anti-patterns, framework idioms |
| **Quality** | Duplication, complexity, dead code, naming, TODOs, deprecated APIs, N+1 queries, bundle size, caching |
| **Security** | OWASP top 10, hardcoded secrets, injection, auth gaps, known CVEs |
| **Testing** | Coverage gaps, assertion quality, edge cases, flaky tests, outdated/unused deps |

### Plugin Analysis Dimensions (`--plugin`)

| Dimension | Checks |
|-----------|--------|
| **Manifest Structure** | plugin.json validation, directory layout, naming, required files |
| **Skill Quality** | Frontmatter completeness, description triggers, word counts, allowed-tools |
| **Agent Design** | AGENT.md format, examples, model/color validity, system prompt quality |
| **Hook Correctness** | hooks.json schema, event names, matcher patterns, script existence |
| **Marketplace Consistency** | Registry alignment, version consistency, cross-plugin naming |
| **Convention Adherence** | Deprecated patterns, @file anti-patterns, token budget violations |

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
  --dimensions=structure,quality,security,testing
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
│   ├── 2026-03-19-structure.json
│   ├── 2026-03-19-quality.json
│   └── ...
├── reports/
│   ├── 2026-03-19-analysis-draft.md
│   ├── 2026-03-19-analysis.md
│   └── 2026-03-19-scores.json
└── plans/
    ├── 2026-03-19-structure-plan.md
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
| `scan-*` (10) | No | 4 standard + 6 plugin dimension scan sub-skills |
| `reconcile-report` | No | Dedup and scoring sub-skill |
| `critique-report` | No | Report validation sub-skill |
| `critique-plan` | No | Plan validation sub-skill |
| `generate-refactoring-plan` | No | Per-dimension plan generation |
| `generate-orchestrator-plan` | No | Master plan generation |

## Dependencies

**Required:**
- [superpowers](https://github.com/anthropics/claude-code-plugins) (>=5.0.0) — ralph-loop uses `superpowers:brainstorming`, `superpowers:writing-plans`, and `superpowers:subagent-driven-development`

**Optional:**
- [Context7 MCP](https://github.com/upstash/context7) — when available, scanners validate framework versions, dependency issues, and patterns against current documentation. **Gracefully degrades when unavailable.**

## Plugin Structure

```
code-analysis/
├── .claude-plugin/plugin.json    # v0.7.0
├── skills/                       # 18 skills
│   ├── analyze-codebase/         # Orchestrator (10-stage pipeline)
│   ├── ralph-loop/               # Iterative fix loop with crash recovery
│   ├── refactor-plan/            # Plan generation from existing analysis
│   ├── scan-structure/           # } 4 standard dimension
│   ├── scan-quality/             # } scan sub-skills with
│   ├── scan-security/            # } fingerprint IDs and
│   ├── scan-testing/             # } carry-forward protocol
│   ├── scan-manifest-structure/  # } 6 plugin-analysis
│   ├── scan-skill-quality/       # } dimensions (--plugin)
│   ├── scan-agent-design/        # }
│   ├── scan-hook-correctness/    # }
│   ├── scan-marketplace-consistency/ # }
│   ├── scan-convention-adherence/# }
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
│   ├── analysis-dimensions.md    # 4 standard + 6 plugin dimensions, severity scale, priority tiers
│   ├── output-schemas.md         # Finding, DimensionReport, ScoresReport, etc.
│   ├── language-profiles/        # Python, TypeScript, C#, Dart, Rust, Go
│   └── framework-profiles/       # React, .NET, Flutter, Tauri, Electron, MAUI
├── templates/                    # Report and plan markdown templates
└── docs/superpowers/
    ├── specs/                    # Approved design specs
    └── plans/                    # Implementation plans
```

## Changelog

### v0.7.0 (2026-03-23)
- **Dimension consolidation**: 8 standard dimensions merged to 4 (structure, quality, security, testing)
- **Progressive disclosure**: 4 skills extract detailed content to references/ directories
- **Plugin mode**: Drops from 10 to 8 dimensions (quality + security + 6 plugin dims)
- **Backwards-compat aliases**: Old dimension names (arch, patterns, deps, perf, debt) still work

### v0.6.0 (2026-03-20)
- **Plugin analysis mode**: `--plugin` flag enables 10-dimension analysis for Claude Code plugins
- **6 new plugin dimensions**: manifest-structure, skill-quality, agent-design, hook-correctness, marketplace-consistency, convention-adherence
- **Official plugins index**: Builds comparison baseline from installed official plugins
- **Plugin profiles**: Reference profiles for each plugin dimension in `references/plugin-profiles/`

### v0.5.0 (2026-03-19)
- **Plugin scanner infrastructure**: 6 new scan-* skills for plugin-specific dimensions
- **Agent directory format**: All agents migrated to `agents/{name}/AGENT.md` convention
- **Model override**: `--model` flag for per-stage model selection (scanning, reconciliation, critique, planning)
- **Config files**: `.code-analysis/config.json` and `~/.claude/code-analysis-config.json` for persistent settings

### v0.4.0 (2026-03-19)
- **Multi-dimension ralph-loop**: `--targets="arch:8,patterns:9"` runs multiple dimensions in one loop with per-dimension target scores
- **Cross-dimension scanning**: All target dimensions scanned together each iteration, catching cross-cutting findings
- **Gap-weighted batch selection**: Findings prioritized by dimension gap — furthest from target gets fixed first

### v0.3.1 (2026-03-19)
- **Iteration estimates**: Ralph-loop effort predictions (5/10, 8/10, 10/10 targets) per dimension
- **true_raw exposure**: Unclipped penalty reveals actual magnitude behind floor scores (1.0)
- **Effort distribution**: `by_effort` field tracks findings by effort level in scores.json
- **Critic validation**: Report critic validates iteration estimate consistency and formula correctness

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
