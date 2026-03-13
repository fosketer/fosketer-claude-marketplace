# fosketer-claude-marketplace

A local marketplace for discovering, sharing, and installing Claude Code plugins.

## Structure

```
plugins/           # Plugin registry — one directory per plugin
  <plugin-name>/
    manifest.json  # Plugin metadata (name, version, description, author, tags)
    README.md      # Usage instructions and screenshots
marketplace.json   # Central registry index (auto-generated)
```

## Usage

### Browsing plugins

Browse the `plugins/` directory or check `marketplace.json` for the full index.

### Installing a plugin

```bash
# Clone the marketplace
git clone git@github.com:fosketer/fosketer-claude-marketplace.git

# Add a plugin to your Claude Code settings
# In ~/.claude/settings.json, add the plugin path to permissionsTool or install via CLI
```

### Publishing a plugin

1. Create a directory under `plugins/<your-plugin-name>/`
2. Add a `manifest.json` with required fields
3. Add a `README.md` with usage instructions
4. Submit a PR

## Manifest schema

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "What this plugin does",
  "author": "github-username",
  "tags": ["devops", "productivity"],
  "source": "https://github.com/user/repo",
  "minClaudeCodeVersion": "1.0.0"
}
```
