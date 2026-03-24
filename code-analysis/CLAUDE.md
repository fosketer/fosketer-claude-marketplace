# CLAUDE.md — code-analysis plugin

## Overview

Claude Code plugin for comprehensive codebase analysis across 4 standard dimensions (structure, quality, security, testing) and 6 plugin-specific dimensions. Produces scored reports with critic validation and focused refactoring plans.

Repo: `fosketer/fosketer-claude-marketplace` (subdirectory: `code-analysis/`)
Version: 0.8.2

## Plugin Quality Scores

All 4 target dimensions at **10.0/10** (2026-03-23). Follow the conventions below to maintain them.

Run `code-analysis:analyze-codebase --plugin --dimensions=skl,agt,cvn,quality` to verify.

## Skill Conventions (skill-quality dimension)

- **Frontmatter required fields**: `name`, `description` — plus `version` (semver) and `allowed-tools` (JSON array)
- **name**: kebab-case, must match parent directory name exactly
- **description**: starts with `This skill should be used when...` — include quoted trigger phrases (e.g., `"scan for issues"`)
- **Frontmatter size**: max 1,024 characters
- **Body word count**: 1,500–2,000 words. If above, extract sections to `references/` subdirectory with conditional load instructions
- **No `@file` references** in SKILL.md bodies — use `${CLAUDE_PLUGIN_ROOT}/path` instead
- **Progressive disclosure**: large reference material goes in `skills/<name>/references/`, not inline
- **allowed-tools**: scoped to what the skill actually needs — no overly broad or empty arrays

## Agent Conventions (agent-design dimension)

- **Frontmatter required fields**: `name`, `description`, `model`, `color`, `tools`
- **name**: kebab-case
- **description**: starts with `Use this agent when...` — include 2+ `<example>` blocks with Context/user/assistant/commentary
- **System prompt**: second-person voice ("You are a...")
- **Quality Standards section**: required — concrete, measurable criteria for output validation
- **Colors**: must be distinct across all agents — check existing colors before adding a new agent
- **Tool scoping**: read-only agents (critics) get `["Read", "Grep", "Glob"]`; write-capable agents add `["Write"]`

### Current agent colors

| Agent | Color |
|-------|-------|
| code-analyzer | cyan |
| report-reconciler | blue |
| refactoring-planner | magenta |
| report-critic | green |
| plan-critic | yellow |

## Convention Adherence Rules (convention-adherence dimension)

- **No `commands/` directory** — deprecated
- **No `templates/` at plugin root** — templates go in skill-level `references/` subdirectories
- **Canonical directories only**: `skills/`, `agents/`, `hooks/`, `scripts/`, `references/`, `.claude-plugin/`
- **All names kebab-case**: directories, files, frontmatter `name` fields
- **allowed-tools format**: JSON array in every SKILL.md frontmatter, consistent capitalization (`Read`, `Write`, `Grep`, `Glob`, `Bash`)
- **Version field**: present in every SKILL.md frontmatter, all matching the same semver
- **Trigger phrases**: no identical quoted phrases across skills. Keep Jaccard overlap below 0.50 between any two skill descriptions
- **plugin.json**: `name` must match marketplace entry, version must match across plugin.json

## Quality Rules (quality dimension)

- **No duplicated blocks across files** — extract shared content to `references/` (e.g., `self-scoring-protocol.md`, `produce-findings-template.md`)
- **Consistent heading hierarchy**: all peer steps at the same heading level (don't mix `###` and `####` for steps)
- **One bullet per line**: never concatenate multiple `- ` items on a single markdown line
- **Heading structure**: H2 for sections, H3 for steps, H4 only for sub-items within a step

## Commands

```bash
# Self-analyze (all 4 scored dimensions)
/code-analysis:analyze-codebase --plugin --dimensions=skl,agt,cvn,quality

# Single dimension check
/code-analysis:analyze-codebase --plugin --dimensions=quality --draft-only

# Improve scores iteratively
/code-analysis:ralph-loop --targets="skl:10,agt:10,cvn:10,quality:10" --plugin

# Validate after changes
/code-analysis:analyze-codebase --plugin --dimensions=skl,agt,cvn,quality --draft-only
```

## Adding New Components

### New skill

1. Create `skills/<name>/SKILL.md` with required frontmatter
2. Target 1,500–2,000 words — extract to `references/` if over
3. End with self-scoring pointer: `Follow the protocol in ${CLAUDE_PLUGIN_ROOT}/references/self-scoring-protocol.md`
4. Run skill-quality scan to verify

### New agent

1. Create `agents/<name>/AGENT.md` with required frontmatter
2. Pick a unique color (check table above)
3. Include 2+ examples and a Quality Standards section
4. Run agent-design scan to verify

### New reference file

1. Place in the consuming skill's `references/` directory
2. Add a conditional load instruction in the skill's SKILL.md body
3. Never place at plugin root — use skill-level or plugin-level `references/`
