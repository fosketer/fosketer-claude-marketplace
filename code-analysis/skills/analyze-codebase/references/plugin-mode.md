# Plugin Mode

Activate plugin analysis mode with `--plugin`. Swap the dimension set to 8 plugin-specific dimensions (2 adapted standard + 6 new). Require target to contain `.claude-plugin/plugin.json`.

## Stage 1 — Detect Plugin Structure

When `--plugin` is set, Stage 1 becomes **Detect Plugin Structure**:

1. Verify `.claude-plugin/plugin.json` exists — abort with error if missing: "Target directory is not a Claude plugin (no .claude-plugin/plugin.json found)"
2. Read `plugin.json` — extract name, version, description
3. Glob `skills/*/SKILL.md` — count and list skills
4. Glob `agents/*.md` and `agents/*/AGENT.md` — count and list agents
5. Glob `hooks/hooks.json` — note if hooks exist
6. Glob `commands/*.md` — note if deprecated commands exist
7. Detect parent marketplace: check `../.claude-plugin/marketplace.json`
8. Build official plugins comparison index (see below)
9. Output: `STACK = { languages: ["claude-plugin"], frameworks: [] }`, `PLUGIN_INVENTORY`, `OFFICIAL_PLUGINS_INDEX_PATH`

### Build Official Plugins Index

1. Read `~/.claude/plugins/cache/claude-plugins-official/` directory listing
2. For each official plugin, find the active version dir and catalog: skill count, agent count, hook presence, frontmatter patterns, word count ranges
3. Create directory if absent: `mkdir -p .code-analysis/plugin-analysis-cache`
4. Write index to `.code-analysis/plugin-analysis-cache/official-plugins-index.json`
5. Add `.code-analysis/plugin-analysis-cache/` to `.gitignore` if not already present (runtime cache, not committed)

## Plugin Dimension Map

Plugin dimensions: `quality`, `security`, `mnf` → manifest-structure, `skl` → skill-quality, `agt` → agent-design, `hkc` → hook-correctness, `mkt` → marketplace-consistency, `cvn` → convention-adherence. Default: all 8.

Dimensions NOT available in plugin mode: structure, testing.

**Validation**: If `--plugin` is set and `--dimensions` contains a non-plugin dimension (struct, testing), abort with: `"Dimension '{name}' is not available in plugin mode. Valid plugin dimensions: quality, security, mnf, skl, agt, hkc, mkt, cvn"`

## Stage 2 — Plugin Dispatch

Parse `--dimensions` flag using plugin dimension map. Default: all 8.

Dispatch ALL `code-analyzer` subagents in parallel with additional parameters:
- MODE: "plugin"
- PLUGIN_PROFILES_DIR: `${CLAUDE_PLUGIN_ROOT}/references/plugin-profiles/`
- OFFICIAL_PLUGINS_INDEX_PATH: path from Stage 1 step 8d
- SCAN_REPORTS_DIR: ".code-analysis/scan-reports"
- CHANGED_FILES: from --changed-files-hint or null
- Model: `MODEL_MAP.scanning`

### Plugin Dispatch Message Template

```
Analyze the plugin at [PROJECT_PATH] for the [DIMENSION] dimension.
Mode: plugin
Plugin Profiles Dir: ${CLAUDE_PLUGIN_ROOT}/references/plugin-profiles/
Official Plugins Index Path: [OFFICIAL_PLUGINS_INDEX_PATH]
Return ONLY a structured JSON findings array.
```
