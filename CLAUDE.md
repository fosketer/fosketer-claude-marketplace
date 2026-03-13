# CLAUDE.md — fosketer-claude-marketplace

## Overview

This is a local marketplace for Claude Code plugins. It serves as a registry for discovering, sharing, and installing plugins.

## Structure

- `plugins/` — One directory per plugin, each containing a `manifest.json` and `README.md`
- `marketplace.json` — Auto-generated central index of all plugins

## Conventions

- Plugin names MUST use kebab-case
- Each plugin directory MUST contain `manifest.json` and `README.md`
- Commit style: conventional commits (`feat(marketplace):`, `fix(plugin):`, `docs:`)
- Language: English for all code, commits, and technical content
