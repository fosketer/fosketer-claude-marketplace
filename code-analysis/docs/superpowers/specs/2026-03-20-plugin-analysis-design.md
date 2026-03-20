# Plugin Analysis Mode — Design Spec

**Date:** 2026-03-20
**Status:** Approved
**Version target:** 0.6.0

## Overview

Extend the existing code-analysis plugin to support analyzing and refactoring Claude Code plugins. Activated via `--plugin` flag on `analyze-codebase` and `ralph-loop`. Uses a hybrid dimension set: 4 adapted general dimensions + 6 new plugin-specific dimensions (10 total). Leverages official Claude plugins from `~/.claude/plugins/cache/claude-plugins-official/` as both static reference profiles and live comparison targets.

## Approach

Single orchestrator with mode switch (Approach B). The `analyze-codebase` skill gains a `--plugin` flag that routes to plugin-specific dimension routing. No separate entry point — the existing pipeline (reconciler, critics, refactoring planner, ralph-loop) works unchanged since the output schema is dimension-agnostic.

## Dimension Model (--plugin mode)

10 dimensions total when `--plugin` is active.

### Adapted General Dimensions (4)

| # | Dimension | ID Prefix | Adaptation |
|---|-----------|-----------|------------|
| 1 | Quality | `QLT` | Scope to `.md` files, check word counts against skill/agent targets, detect markdown issues |
| 2 | Dependencies | `DEP` | Scan for skill/plugin/agent cross-references, `@file` includes, MCP server declarations, check all references resolve |
| 3 | Tech-debt | `TDT` | Flag `commands/` usage as deprecated, detect legacy patterns per plugin-dev conventions |
| 4 | Security | `SEC` | Focus on hook scripts, `${CLAUDE_PLUGIN_ROOT}` misuse, hardcoded paths, credential patterns in `.local.md` |

### New Plugin-Specific Dimensions (6)

| # | Dimension | ID Prefix | Scope |
|---|-----------|-----------|-------|
| 5 | Manifest & Structure | `MNF` | plugin.json validity, dir layout, naming conventions (kebab-case), required files, `.claude-plugin/` placement |
| 6 | Skill Quality | `SKL` | SKILL.md frontmatter (description triggers, third-person, <1,024 chars), word count (1,500–2,000 body), progressive disclosure, resource organization, `allowed-tools` appropriateness |
| 7 | Agent Design | `AGT` | AGENT.md frontmatter (name format, `<example>` blocks, model/color validity), system prompt quality, tool scoping |
| 8 | Hook Correctness | `HKC` | hooks.json schema (plugin wrapper format), valid event names, matcher patterns, script existence, security |
| 9 | Marketplace Consistency | `MKT` | marketplace.json registry alignment, version consistency across plugin.json/package.json, cross-plugin naming conflicts, missing README |
| 10 | Convention Adherence | `CVN` | Deprecated commands/ usage, `@file` anti-patterns in cross-references, token budget violations, official plugin pattern drift |

### Dimensions Skipped in --plugin Mode

Architecture, Patterns, Performance, Testing — not applicable to Claude plugin structure.

## Pipeline Changes

### analyze-codebase/SKILL.md

- Accepts `--plugin` flag
- Stage 1 becomes **Detect Plugin Structure**: reads `plugin.json`, inventories skills/agents/hooks/commands, identifies parent marketplace, builds official plugins comparison index
- Stage 2 dispatches 10 plugin dimensions (all in parallel) instead of 8 general dimensions
- Stages 3–8 unchanged — shared infrastructure is dimension-agnostic

### ralph-loop/SKILL.md

- Accepts `--plugin` flag (positional or within `--targets`)
- Passes flag through to `analyze-codebase` on each iteration
- Dimension names in targets use new enum values
- Example: `ralph-loop --plugin --targets skill-quality:8,convention-adherence:7`

### 4 Adapted Scan Skills

Each gains a `MODE` check. When `MODE=plugin`:
- `scan-quality` — scopes to `.md` files, checks word counts against skill/agent conventions
- `scan-dependencies` — scans for `@file` references, skill cross-references by name, MCP server declarations, validates all references resolve
- `scan-tech-debt` — flags `commands/` as deprecated, detects legacy format usage per plugin-dev conventions
- `scan-security` — focuses on hook scripts, `${CLAUDE_PLUGIN_ROOT}` misuse, hardcoded paths, credential patterns

### code-analyzer Agent

Modified to handle plugin dimensions in its dispatch logic. No new agents needed.

## Reference Profiles

### Static Profiles (new `references/plugin-profiles/`)

| File | Content |
|------|---------|
| `plugin-structure.md` | Canonical directory layout, plugin.json schema, required vs optional files, naming rules |
| `skill-conventions.md` | SKILL.md frontmatter rules, description format, word count targets, progressive disclosure patterns, resource dir conventions |
| `agent-conventions.md` | AGENT.md frontmatter rules, `<example>` block format, model/color semantics, system prompt structure, tool scoping guidelines |
| `hook-conventions.md` | hooks.json schema (plugin wrapper vs settings direct), valid events enum, matcher patterns, `${CLAUDE_PLUGIN_ROOT}` requirements, security rules |
| `marketplace-conventions.md` | marketplace.json schema, version consistency rules (plugin.json ↔ package.json), naming collision rules |

Derived from the official `plugin-dev` plugin documentation.

### Live Comparison Against Official Plugins

During Stage 1, the orchestrator:
1. Reads `~/.claude/plugins/cache/claude-plugins-official/` to discover installed official plugins
2. Builds a comparison index: for each official plugin, catalogs skill count, agent count, frontmatter patterns, directory structure, word counts
3. Passes this index to the 6 new scan skills as `OFFICIAL_PLUGINS_INDEX`

Used by:
- **Skill Quality** — compares description style, word count distribution against official skills
- **Agent Design** — compares example block patterns, model choices against official agents
- **Convention Adherence** — detects drift from official plugin patterns
- **Manifest & Structure** — compares directory layout against official plugins

The 4 adapted dimensions do not use the live index — they rely on their reference profiles.

## Output Schema Extensions

### Dimension Enum (extended)

Existing: `architecture`, `quality`, `dependencies`, `patterns`, `testing`, `performance`, `security`, `tech-debt`

Added: `manifest-structure`, `skill-quality`, `agent-design`, `hook-correctness`, `marketplace-consistency`, `convention-adherence`

### ID Prefixes

| Dimension | Prefix |
|-----------|--------|
| manifest-structure | `MNF` |
| skill-quality | `SKL` |
| agent-design | `AGT` |
| hook-correctness | `HKC` |
| marketplace-consistency | `MKT` |
| convention-adherence | `CVN` |

### Priority Tier Rules (plugin-specific)

| Tier | Rules |
|------|-------|
| `immediate` | Security: hardcoded secrets in hooks. Manifest: invalid plugin.json (plugin won't load) |
| `sprint-1` | Broken dependencies (unresolved `@file`, missing referenced skills). Hook schema errors. Marketplace version mismatch |
| `sprint-2` | Skill quality issues (bad description triggers, missing examples). Agent design issues (no `<example>` blocks). Convention drift from official patterns |
| `backlog` | Word count outside targets. Minor naming inconsistencies. Deprecated commands/ still present but functional |

### Templates

No new templates needed. Existing `dimension-report.md`, `analysis-draft.md`, `refactoring-plan.md`, and `orchestrator-plan.md` are dimension-agnostic.

## File Structure (changes only)

```
code-analysis/
├── skills/
│   ├── analyze-codebase/SKILL.md          # MODIFIED — --plugin flag, dimension routing
│   ├── ralph-loop/SKILL.md                # MODIFIED — --plugin flag passthrough
│   ├── scan-quality/SKILL.md              # MODIFIED — plugin code path
│   ├── scan-dependencies/SKILL.md         # MODIFIED — plugin code path
│   ├── scan-tech-debt/SKILL.md            # MODIFIED — plugin code path
│   ├── scan-security/SKILL.md             # MODIFIED — plugin code path
│   ├── scan-manifest-structure/SKILL.md   # NEW
│   ├── scan-skill-quality/SKILL.md        # NEW
│   ├── scan-agent-design/SKILL.md         # NEW
│   ├── scan-hook-correctness/SKILL.md     # NEW
│   ├── scan-marketplace-consistency/SKILL.md  # NEW
│   ├── scan-convention-adherence/SKILL.md # NEW
├── references/
│   ├── plugin-profiles/                   # NEW directory
│   │   ├── plugin-structure.md            # NEW
│   │   ├── skill-conventions.md           # NEW
│   │   ├── agent-conventions.md           # NEW
│   │   ├── hook-conventions.md            # NEW
│   │   └── marketplace-conventions.md     # NEW
│   ├── analysis-dimensions.md             # MODIFIED — add 6 new dimensions
│   ├── output-schemas.md                  # MODIFIED — extend dimension enum
├── agents/
│   ├── code-analyzer.md                   # MODIFIED — handle plugin dimensions
│   ├── code-analyzer/AGENT.md             # MODIFIED — plugin dimension dispatching
├── .claude-plugin/plugin.json             # MODIFIED — bump to 0.6.0
├── package.json                           # MODIFIED — bump to 0.6.0
```

## Version

Minor bump: 0.5.0 → 0.6.0 (new functionality, no breaking changes to existing general analysis).
