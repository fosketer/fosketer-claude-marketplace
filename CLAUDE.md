# CLAUDE.md — fosketer-claude-marketplace

## Overview

This is a local marketplace for Claude Code plugins. It serves as a registry for discovering, sharing, and installing plugins.

## Structure

- `<plugin-name>/` — One directory per plugin at the repo root, each containing `.claude-plugin/plugin.json` and `README.md`
- `.claude-plugin/marketplace.json` — Central marketplace index of all plugins

## Conventions

- Plugin names MUST use kebab-case
- Each plugin directory MUST contain `manifest.json` and `README.md`
- Commit style: conventional commits (`feat(marketplace):`, `fix(plugin):`, `docs:`)
- Language: English for all code, commits, and technical content
