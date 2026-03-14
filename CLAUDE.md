# CLAUDE.md — fosketer-claude-marketplace

## Overview

Local marketplace for Claude Code plugins. Registry for discovering, sharing, and installing plugins.
Repo: `fosketer/fosketer-claude-marketplace`

## Structure

```text
local-claude-marketplace/
├── .claude-plugin/
│   └── marketplace.json    # Central marketplace index
├── multi-angle-research/   # Research pipeline plugin
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── agents/
│   ├── skills/
│   ├── manifest.json
│   └── README.md
├── code-analysis/          # Codebase analysis plugin
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── agents/
│   ├── skills/
│   └── README.md
└── CLAUDE.md
```

## Commands

```bash
# Validate marketplace index
cat .claude-plugin/marketplace.json | jq .

# Check a plugin's manifest
cat <plugin-name>/.claude-plugin/plugin.json | jq .
```

## Conventions

- Plugin names MUST use kebab-case
- Each plugin directory MUST contain `.claude-plugin/plugin.json` and `README.md`
- Commit style: conventional commits (`feat(marketplace):`, `fix(plugin):`, `docs:`)
- Language: English for all code, commits, and technical content
