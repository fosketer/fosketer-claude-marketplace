# code-analysis

Comprehensive codebase analysis plugin for Claude Code. Scans any language/framework across 8 dimensions and produces focused refactoring plans with a master orchestrator plan.

## Architecture

```
/analyze [path]
    │
    ▼
Phase 1: Detect Stack ──── language-profiles/ + framework-profiles/
    │
    ▼
Phase 2: Scan Dimensions ─── 8 sub-skills (inline, sequential)
    │                         ├── scan-architecture
    │                         ├── scan-quality
    │                         ├── scan-dependencies
    │                         ├── scan-patterns
    │                         ├── scan-testing
    │                         ├── scan-performance
    │                         ├── scan-security
    │                         └── scan-tech-debt
    ▼
Phase 3: Generate Reports ── CHECKPOINT (user reviews)
    │
    ▼
Phase 4: Refactoring Plans ── one per dimension (generate-refactoring-plan)
    │
    ▼
Phase 5: Orchestrator Plan ── MANDATORY GATE (user approves)
    │
    ▼
Phase 6: Persist Outputs ─── .code-analysis/ in target project
```

## Supported Stacks

| Language | Framework |
|----------|-----------|
| Python | — |
| TypeScript | React, Electron |
| C# | .NET, MAUI |
| Dart | Flutter |
| Rust | Tauri |
| Go | — |

Multi-language projects (e.g., Tauri = Rust + TypeScript) are supported with multiple profile loading.

## Skills (User-Invocable)

### `analyze-codebase`

Run the full analysis pipeline. Scans the codebase, presents findings, generates refactoring plans.

Trigger phrases: "analyze this codebase", "scan for issues", "audit this project", "check code quality"

Arguments: `[path] [--dimensions=arch,quality,deps,patterns,testing,perf,security,debt] [--stack=python|typescript|csharp|dart|rust|go] [--framework=react|dotnet|flutter|tauri|electron|maui]`

### `refactor-plan`

Generate refactoring plans from existing analysis results without re-scanning.

Trigger phrases: "generate refactoring plans", "plan refactoring from analysis"

Arguments: `[path] [--from-analysis=latest|YYYY-MM-DD] [--dimensions=...] [--priority=security-first|architecture-first|quick-wins-first]`

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

## Output

All outputs are written to `.code-analysis/` in the analyzed project:

```
.code-analysis/
├── .gitignore                          # Ignores all by default
├── scan-reports/
│   ├── 2026-03-13-architecture.json
│   ├── 2026-03-13-quality.json
│   └── ...
├── reports/
│   ├── 2026-03-13-architecture-report.md
│   ├── 2026-03-13-quality-report.md
│   └── ...
└── plans/
    ├── 2026-03-13-architecture-plan.md
    ├── 2026-03-13-quality-plan.md
    ├── ...
    └── 2026-03-13-orchestrator-plan.md
```

## Agents

| Agent | Purpose |
|-------|---------|
| `code-analyzer` | Run a single dimension scan in isolation |
| `refactoring-planner` | Generate plans from existing findings |

## Context7 Integration

When Context7 MCP is available, the plugin validates:
- Detected framework versions against documentation
- Dependency versions for known issues
- Framework-specific patterns against current best practices

Gracefully degrades when Context7 is unavailable.

## Plugin Structure

```
code-analysis/
├── .claude-plugin/plugin.json
├── package.json
├── .releaserc.json
├── README.md
├── skills/            (12 skills including orchestrator + refactor-plan)
├── agents/            (2 agents)
├── references/        (analysis-dimensions, output-schemas, language/framework profiles)
└── templates/         (3 templates)
```
