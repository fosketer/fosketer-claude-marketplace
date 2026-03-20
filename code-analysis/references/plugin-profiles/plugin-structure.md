# Plugin Structure Reference Profile

Ground truth for plugin directory layout, manifest schema, naming conventions, path references, and auto-discovery rules. Derived from official `plugin-dev` plugin conventions.

---

## 1. Canonical Directory Layout

Every Claude Code plugin follows this organizational pattern:

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # Required: Plugin manifest (MUST be here)
├── commands/                 # Slash commands (.md files)
├── agents/                   # Subagent definitions (.md files)
├── skills/                   # Agent skills (subdirectories with SKILL.md)
│   └── skill-name/
│       └── SKILL.md
├── hooks/
│   └── hooks.json            # Event handler configuration
├── .mcp.json                 # MCP server definitions
└── scripts/                  # Helper scripts and utilities
```

### Critical Layout Rules

1. **Manifest location**: `plugin.json` MUST be in `.claude-plugin/` directory. Claude Code will not recognize a plugin without this file in the correct location.
2. **Component directories**: All component directories (`commands/`, `agents/`, `skills/`, `hooks/`) MUST be at plugin root level, NOT nested inside `.claude-plugin/`.
3. **Optional components**: Only create directories for components the plugin actually uses. An empty `agents/` directory is worse than no directory.
4. **Naming convention**: Use kebab-case for all directory and file names throughout the plugin.

### Minimal Plugin Layout

Single command with no dependencies:

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json    # Just the name field
└── commands/
    └── hello.md       # Single command
```

### Full-Featured Plugin Layout

Complete plugin with all component types:

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/              # User-facing commands
├── agents/                # Specialized subagents
├── skills/                # Auto-activating skills
├── hooks/                 # Event handlers
│   ├── hooks.json
│   └── scripts/
├── .mcp.json              # External integrations
└── scripts/               # Shared utilities
```

### Skill-Focused Plugin Layout

Plugin providing only skills (no commands or agents):

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    ├── skill-one/
    │   └── SKILL.md
    └── skill-two/
        └── SKILL.md
```

---

## 2. Plugin Manifest (plugin.json) Schema

Located at `.claude-plugin/plugin.json`. Defines plugin metadata and configuration.

### 2.1 Required Fields

```json
{
  "name": "plugin-name"
}
```

Only `name` is strictly required for a plugin to function.

### 2.2 Name Validation

**Regex**: `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`

**Rules**:
- Must start with a lowercase letter
- Lowercase letters, numbers, and hyphens only
- No spaces, underscores, or special characters
- Must end with a letter or number (not a hyphen)
- Must be unique across all installed plugins

**Valid examples**: `api-tester`, `code-review`, `git-workflow-automation`, `test-runner`

**Invalid examples**:
- `API Tester` — contains uppercase and space
- `code_review` — underscore not allowed
- `-git-workflow` — starts with hyphen
- `test-` — ends with hyphen
- `t` — too short, must start with letter then have a segment

### 2.3 Recommended Metadata Fields

```json
{
  "name": "code-review-assistant",
  "version": "1.0.0",
  "description": "Automates code review with style checks and suggestions",
  "author": {
    "name": "Jane Developer",
    "email": "jane@example.com",
    "url": "https://janedeveloper.com"
  },
  "homepage": "https://docs.example.com/code-review",
  "repository": "https://github.com/janedev/code-review-assistant",
  "license": "MIT",
  "keywords": ["code-review", "automation", "quality", "ci-cd"]
}
```

#### version

- **Format**: Semantic versioning `MAJOR.MINOR.PATCH`
- **Default**: `"0.1.0"` if not specified
- **Pre-release**: `"1.0.0-alpha.1"`, `"1.0.0-beta.2"`, `"1.0.0-rc.1"`
- **Invalid**: `"1.0"` (missing PATCH), `"v1.0.0"` (v prefix not standard)
- MAJOR = incompatible/breaking changes; MINOR = backward-compatible new features; PATCH = bug fixes

#### description

- **Length**: 50–200 characters recommended
- Focus on what the plugin does, not how
- Use active voice
- Mention key features or benefits

#### author

Object form (preferred):
```json
{ "name": "Name", "email": "a@b.com", "url": "https://..." }
```
String form (alternative):
```json
"Jane Developer <jane@example.com> (https://janedeveloper.com)"
```

#### keywords

- Use 5–10 keywords
- Include functionality categories (`testing`, `debugging`, `documentation`, `deployment`)
- Add technology names (`typescript`, `python`, `docker`, `aws`)
- Include workflow terms (`ci-cd`, `code-review`, `git-workflow`)
- Avoid duplicating the plugin name

### 2.4 Optional Component Path Overrides

Custom paths supplement (do not replace) the default directories.

```json
{
  "name": "plugin-name",
  "commands": "./custom-commands",
  "agents": ["./agents", "./specialized-agents"],
  "hooks": "./config/hooks.json",
  "mcpServers": "./.mcp.json"
}
```

**Path rules for all component fields**:
- Must be relative to plugin root
- Must start with `./`
- Cannot use absolute paths (`/Users/...`)
- Cannot use parent directory navigation (`../`)
- Forward slashes only (no backslashes)
- Support arrays for multiple locations

**Valid path examples**:
- `"./commands"` — correct
- `"./src/commands"` — correct
- `"./configs/hooks.json"` — correct

**Invalid path examples**:
- `"/Users/name/commands"` — absolute path
- `"commands"` — missing `./` prefix
- `"../shared/commands"` — parent traversal
- `".\\commands"` — backslash

**Merge behavior**: Components from default directories AND custom paths all load. Name conflicts cause errors. There is no overwriting — all discovered components register.

### 2.5 Complete Manifest Example

```json
{
  "name": "enterprise-devops",
  "version": "2.3.1",
  "description": "Comprehensive DevOps automation for enterprise CI/CD pipelines",
  "author": {
    "name": "DevOps Team",
    "email": "devops@company.com",
    "url": "https://company.com/devops"
  },
  "homepage": "https://docs.company.com/plugins/devops",
  "repository": {
    "type": "git",
    "url": "https://github.com/company/devops-plugin.git"
  },
  "license": "Apache-2.0",
  "keywords": [
    "devops", "ci-cd", "automation", "kubernetes", "docker", "deployment"
  ],
  "commands": ["./commands", "./admin-commands"],
  "agents": "./specialized-agents",
  "hooks": "./config/hooks.json",
  "mcpServers": "./.mcp.json"
}
```

---

## 3. Component Organization

### 3.1 Commands

- **Location**: `commands/` directory at plugin root
- **Format**: Markdown files (`.md`) with YAML frontmatter
- **Auto-discovery**: All `.md` files in `commands/` load automatically
- **Naming**: kebab-case file names (`code-review.md` → `/code-review` command)

```
commands/
├── review.md        # becomes /review command
├── test.md          # becomes /test command
└── deploy.md        # becomes /deploy command
```

### 3.2 Agents

- **Location**: `agents/` directory at plugin root
- **Format**: Markdown files (`.md`) with YAML frontmatter
- **Auto-discovery**: All `.md` files in `agents/` load automatically
- **Naming**: kebab-case, describe the role (`code-reviewer.md`, `test-generator.md`)

### 3.3 Skills

- **Location**: `skills/` directory at plugin root; each skill in its own subdirectory
- **Required file**: `SKILL.md` (exactly this name — not `README.md` or other names)
- **Auto-discovery**: All subdirectories containing `SKILL.md` load automatically
- **Supporting dirs**: Each skill can have `references/`, `examples/`, `scripts/`, `assets/` subdirectories

```
skills/
├── api-testing/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── test-runner.py
│   └── references/
│       └── api-spec.md
└── database-migrations/
    ├── SKILL.md
    └── examples/
        └── migration-template.sql
```

### 3.4 Hooks

- **Location**: `hooks/hooks.json` (default) or inline in `plugin.json`
- **Format**: JSON configuration defining event handlers
- **Auto-registration**: Hooks register automatically when plugin enables
- **Scripts**: Store hook scripts in `hooks/scripts/`

### 3.5 MCP Servers

- **Location**: `.mcp.json` at plugin root or inline in `plugin.json`
- **Auto-start**: Servers start automatically when plugin enables

---

## 4. `${CLAUDE_PLUGIN_ROOT}` Usage Rules

### 4.1 What It Is

`${CLAUDE_PLUGIN_ROOT}` is an environment variable that expands to the absolute path of the plugin's root directory at runtime. It is the canonical way to reference files within a plugin from scripts, hooks, and MCP server commands.

### 4.2 Why It Is Required

Plugins install in different locations depending on:
- Installation method (marketplace, local, npm)
- Operating system conventions
- User preferences

Hardcoded paths break across environments. `${CLAUDE_PLUGIN_ROOT}` resolves correctly regardless of install location.

### 4.3 Where to Use It

- Hook command paths: `"command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh"`
- MCP server command arguments: `"args": ["${CLAUDE_PLUGIN_ROOT}/servers/server.js"]`
- Script execution references
- Resource file paths referenced from component files

### 4.4 What Never to Use Instead

- Hardcoded absolute paths: `"command": "/Users/name/plugins/my-plugin/scripts/run.sh"` — FORBIDDEN
- Relative paths from working directory: `"command": "./scripts/run.sh"` — UNRELIABLE in hooks
- Home directory shortcuts: `~/plugins/...` — FORBIDDEN

### 4.5 Usage Contexts

**In JSON configuration (hooks, MCP servers)**:
```json
"command": "${CLAUDE_PLUGIN_ROOT}/scripts/tool.sh"
```

**In component files (commands, agents, skills markdown)**:
```markdown
Reference scripts at: ${CLAUDE_PLUGIN_ROOT}/scripts/helper.py
```

**In executed scripts**:
```bash
#!/bin/bash
# ${CLAUDE_PLUGIN_ROOT} is available as an environment variable
source "${CLAUDE_PLUGIN_ROOT}/lib/common.sh"
```

---

## 5. File Naming Conventions

### 5.1 Component Files

| Component | Format | Example |
|-----------|--------|---------|
| Commands | `kebab-case.md` | `code-review.md`, `run-tests.md` |
| Agents | `kebab-case.md` | `test-generator.md`, `code-reviewer.md` |
| Skills | `kebab-case/` directory | `api-testing/`, `error-handling/` |
| Skill file | Always `SKILL.md` | `skills/api-testing/SKILL.md` |
| Hooks config | `hooks.json` | `hooks/hooks.json` |
| MCP config | `.mcp.json` | `.mcp.json` |
| Manifest | `plugin.json` | `.claude-plugin/plugin.json` |

### 5.2 Supporting Files

- Scripts: descriptive kebab-case with extension (`validate-input.sh`, `generate-report.py`)
- Documentation: kebab-case markdown (`api-reference.md`, `migration-guide.md`)
- Configuration: standard names (`hooks.json`, `.mcp.json`, `plugin.json`)

### 5.3 Naming Length Guidelines

- Commands: 2–3 words (`review-pr`, `run-ci`, `api-docs`)
- Agents: describe role clearly (`code-reviewer`, `test-generator`, `performance-analyzer`)
- Skills: topic-focused (`error-handling`, `api-design`, `database-migrations`)

---

## 6. Auto-Discovery Mechanism

Claude Code automatically discovers and loads components following this sequence:

1. **Plugin manifest**: Reads `.claude-plugin/plugin.json` when plugin enables
2. **Commands**: Scans `commands/` directory for `.md` files
3. **Agents**: Scans `agents/` directory for `.md` files
4. **Skills**: Scans `skills/` for subdirectories containing `SKILL.md`
5. **Hooks**: Loads configuration from `hooks/hooks.json` or manifest inline field
6. **MCP servers**: Loads configuration from `.mcp.json` or manifest inline field

**Custom paths supplement defaults**: Components in both default directories and custom paths declared in `plugin.json` will load. Custom paths do not replace the defaults.

**Discovery timing**: Components register at plugin installation; become available when plugin is enabled. Changes take effect on next Claude Code session — no hot-reload during active session.

---

## 7. Manifest Validation Rules

Claude Code validates the manifest on plugin load:

**Syntax validation**:
- Must be valid JSON (no syntax errors, no trailing commas)
- All field types must be correct (string where string expected, etc.)

**Field validation**:
- `name` field must be present and match regex `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`
- `version` must follow semantic versioning if present
- All paths must be relative with `./` prefix
- URLs must be valid if present

**Component validation**:
- Referenced paths must exist
- Hook and MCP configurations must be valid JSON
- No circular dependencies allowed

---

## 8. Compliance Checklist

Use this checklist when scanning a plugin for structural compliance:

**Manifest**:
- [ ] `.claude-plugin/plugin.json` exists at plugin root
- [ ] `name` field present and matches `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`
- [ ] `version` follows `MAJOR.MINOR.PATCH` if present
- [ ] All component paths use `./` relative notation
- [ ] No absolute paths anywhere in manifest

**Directory structure**:
- [ ] Component directories are at plugin root (not inside `.claude-plugin/`)
- [ ] All directory and file names use kebab-case
- [ ] Each skill subdirectory contains `SKILL.md` (not README.md or other name)
- [ ] `hooks/hooks.json` uses the plugin wrapper format `{"hooks": {...}}`

**Path references**:
- [ ] All intra-plugin paths in hooks/MCP use `${CLAUDE_PLUGIN_ROOT}`
- [ ] No hardcoded absolute paths in any configuration
- [ ] No `~/` or relative-from-cwd paths in hook commands

**Naming**:
- [ ] Plugin name is unique and descriptive
- [ ] Component names follow kebab-case conventions
- [ ] No generic names like `utils`, `misc`, `temp`

---

## 9. Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|---|---|---|
| `plugin.json` at root (not in `.claude-plugin/`) | Claude Code won't find the manifest | Move to `.claude-plugin/plugin.json` |
| `agents/` inside `.claude-plugin/` | Auto-discovery won't work | Place at plugin root |
| `name: "My Plugin"` | Fails name regex | Use `"my-plugin"` |
| `"command": "/Users/x/scripts/run.sh"` | Breaks on other machines | Use `${CLAUDE_PLUGIN_ROOT}/scripts/run.sh` |
| `"hooks": "hooks/hooks.json"` | Missing `./` prefix | Use `"./hooks/hooks.json"` |
| Skill file named `README.md` | Auto-discovery requires `SKILL.md` | Rename to `SKILL.md` |
| `version: "1.0"` | Not semver | Use `"1.0.0"` |
| Empty component directories | Noise, no benefit | Only create directories actually used |
