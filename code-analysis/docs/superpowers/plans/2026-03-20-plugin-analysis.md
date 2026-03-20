# Plugin Analysis Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--plugin` mode to code-analysis that runs 10 plugin-specific dimensions (4 adapted + 6 new) against Claude Code plugins, with reference profiles and live comparison against official plugins.

**Architecture:** Single orchestrator with mode switch. `analyze-codebase` gains `--plugin` flag that swaps the dimension set and stack detection. Shared infrastructure (reconciler, critics, ralph-loop) works unchanged — the output schema just gets an extended dimension enum.

**Tech Stack:** Claude Code plugin system (markdown skills, markdown agents, JSON schemas). No runtime dependencies.

**Spec:** `docs/superpowers/specs/2026-03-20-plugin-analysis-design.md`

---

## Task 1: Extend Output Schemas

**Files:**
- Modify: `references/output-schemas.md:26` (Finding.dimension enum)
- Modify: `references/output-schemas.md:114` (DimensionReport.metadata.dimension enum)
- Modify: `references/output-schemas.md:192` (RefactoringPlan.metadata.dimension enum)

- [ ] **Step 1: Add new dimension values to Finding.dimension enum**

In `references/output-schemas.md`, line 26, extend the enum array:

```json
"enum": ["architecture", "quality", "dependencies", "patterns", "testing", "performance", "security", "tech-debt", "manifest-structure", "skill-quality", "agent-design", "hook-correctness", "marketplace-consistency", "convention-adherence"]
```

- [ ] **Step 2: Add same values to DimensionReport.metadata.dimension enum**

Line 114, same extension:

```json
"enum": ["architecture", "quality", "dependencies", "patterns", "testing", "performance", "security", "tech-debt", "manifest-structure", "skill-quality", "agent-design", "hook-correctness", "marketplace-consistency", "convention-adherence"]
```

- [ ] **Step 3: Add same values to RefactoringPlan.metadata.dimension enum**

Line 193, same extension:

```json
"enum": ["architecture", "quality", "dependencies", "patterns", "testing", "performance", "security", "tech-debt", "manifest-structure", "skill-quality", "agent-design", "hook-correctness", "marketplace-consistency", "convention-adherence"]
```

- [ ] **Step 4: Verify all three enums match**

Run:
```bash
grep -n '"enum":.*"architecture"' references/output-schemas.md
```
Expected: 3 lines, all containing the same 14-value enum.

- [ ] **Step 5: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/references/output-schemas.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): extend dimension enum with 6 plugin-specific dimensions"
```

---

## Task 2: Extend Analysis Dimensions Reference

**Files:**
- Modify: `references/analysis-dimensions.md:1-133`

- [ ] **Step 1: Add plugin-specific dimension definitions**

After the existing "8. Tech Debt" section (line 109), add:

```markdown
## Plugin-Specific Dimensions (--plugin mode)

The following dimensions are activated when `--plugin` flag is passed. They replace Architecture, Patterns, Performance, and Testing. Quality, Dependencies, Tech-debt, and Security are retained with adapted behavior.

### 5p. Manifest & Structure (`scan-manifest-structure`)

- **Purpose**: Validate plugin.json, directory layout, naming conventions
- **Checks**:
  - `plugin.json` in `.claude-plugin/` with required fields (name, description)
  - Plugin name is kebab-case (`/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`)
  - Required files present (README.md, at least one skill or agent)
  - Directory structure follows conventions (skills/, agents/, hooks/, commands/)
  - `${CLAUDE_PLUGIN_ROOT}` used for all intra-plugin paths in hooks/MCP configs
- **Severity**: critical (invalid plugin.json — plugin won't load), high (missing required files), medium (naming violations)

### 6p. Skill Quality (`scan-skill-quality`)

- **Purpose**: SKILL.md frontmatter quality, description triggers, progressive disclosure
- **Checks**:
  - Frontmatter has required fields (name, description)
  - Frontmatter total < 1,024 chars
  - Description starts with "Use when..." and uses third person
  - Description contains trigger phrases, not workflow summaries
  - Body word count between 1,000–3,000 (warning), outside 500–5,000 (high)
  - Progressive disclosure: heavy content in references/, not inlined
  - Resource dirs (references/, examples/, scripts/) are organized
  - `allowed-tools` lists only necessary tools
- **Severity**: critical (missing SKILL.md), high (bad triggers, word count extremes), medium (style, disclosure)

### 7p. Agent Design (`scan-agent-design`)

- **Purpose**: AGENT.md frontmatter, example blocks, system prompt quality
- **Checks**:
  - Frontmatter has required fields (name, description, model, color)
  - Name: lowercase, hyphens, 3–50 chars
  - Description includes 2–4 `<example>` blocks with Context/user/assistant/commentary
  - Model is valid (inherit/sonnet/opus/haiku)
  - Color is valid (blue/cyan/green/yellow/magenta/red)
  - Tools array scoped appropriately (not empty, not overly broad)
  - System prompt uses second person ("You are...")
- **Severity**: critical (missing AGENT.md in agents/ dir), high (no example blocks, invalid model/color), medium (style, tool scoping)

### 8p. Hook Correctness (`scan-hook-correctness`)

- **Purpose**: hooks.json schema, event names, matcher patterns, script existence
- **Checks**:
  - hooks.json uses plugin wrapper format (`{"hooks": {...}}`)
  - All event names valid: PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification
  - Matcher patterns are valid regex
  - Referenced scripts exist at declared paths
  - Scripts use `${CLAUDE_PLUGIN_ROOT}` for paths, not hardcoded
  - No hardcoded credentials in hook scripts
- **Severity**: critical (invalid JSON schema), high (invalid events, missing scripts), medium (path issues)

### 9p. Marketplace Consistency (`scan-marketplace-consistency`)

- **Purpose**: Registry alignment, version consistency
- **Checks**:
  - Plugin listed in parent marketplace.json (if marketplace detected)
  - Version in plugin.json matches package.json (if both exist)
  - Description in marketplace.json matches plugin.json
  - No naming conflicts with sibling plugins in same marketplace
  - README.md exists and is non-empty
- **Severity**: high (version mismatch, missing from registry), medium (description drift, missing README)

### 10p. Convention Adherence (`scan-convention-adherence`)

- **Purpose**: Deprecated patterns, token budgets, official plugin pattern drift
- **Checks**:
  - `commands/` directory usage (deprecated — should be skills)
  - `@file` references in skill cross-references (anti-pattern — burns context)
  - Skill description > 1,024 chars (token budget violation)
  - Drift from official plugin patterns (directory structure, frontmatter style, naming)
  - Duplicate functionality detection across skills within same plugin
- **Severity**: high (deprecated commands/ with no skill equivalent), medium (convention drift, @file usage)
```

- [ ] **Step 2: Add plugin-specific priority tier rules**

After the existing Priority Tier Assignment table (line 132), add:

```markdown
### Plugin-Specific Priority Tiers (--plugin mode)

When `MODE=plugin`, the following rules take precedence over the general rules above for the 6 new plugin dimensions. For the 4 adapted dimensions (quality, dependencies, tech-debt, security), the general rules apply unchanged.

| Tier | Assignment Rule |
|------|-----------------|
| `immediate` | Security: hardcoded secrets in hooks. Manifest: invalid plugin.json (plugin won't load) |
| `sprint-1` | Broken dependencies (unresolved `@file`, missing referenced skills). Hook schema errors. Marketplace version mismatch |
| `sprint-2` | Skill quality issues (bad description triggers, missing examples). Agent design issues (no `<example>` blocks). Convention drift from official patterns |
| `backlog` | Word count outside targets. Minor naming inconsistencies. Deprecated commands/ still present but functional |
```

- [ ] **Step 3: Verify the document reads correctly**

Read the full file and verify no formatting issues.

- [ ] **Step 4: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/references/analysis-dimensions.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): add 6 plugin-specific dimensions and priority tiers to analysis-dimensions reference"
```

---

## Task 3: Create Plugin Reference Profiles

**Files:**
- Create: `references/plugin-profiles/plugin-structure.md`
- Create: `references/plugin-profiles/skill-conventions.md`
- Create: `references/plugin-profiles/agent-conventions.md`
- Create: `references/plugin-profiles/hook-conventions.md`
- Create: `references/plugin-profiles/marketplace-conventions.md`

These profiles are the static ground truth for plugin analysis. Content is derived from the official `plugin-dev` plugin at `~/.claude/plugins/cache/claude-plugins-official/plugin-dev/`.

- [ ] **Step 1: Create plugin-structure.md**

Content must cover:
- Canonical directory layout (`skills/`, `agents/`, `hooks/`, `commands/` (deprecated), `.claude-plugin/plugin.json`)
- `plugin.json` schema: required fields (`name`), recommended (`version`, `description`, `author`, `keywords`), optional path overrides
- Name regex: `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`
- `.claude-plugin/` MUST be the location (not root)
- `${CLAUDE_PLUGIN_ROOT}` usage rules

- [ ] **Step 2: Create skill-conventions.md**

Content must cover:
- SKILL.md location: `skills/<name>/SKILL.md`
- Frontmatter: `name` (required, kebab-case), `description` (required, "Use when..." third-person, <1,024 chars total), optional `allowed-tools`, `version`
- Body: imperative/infinitive form, 1,500–2,000 words target, max 5,000
- Supporting dirs: `references/`, `examples/`, `scripts/`, `assets/`
- Progressive disclosure: heavy content in supporting files, not inlined
- Cross-references: by skill name only, never `@file`

- [ ] **Step 3: Create agent-conventions.md**

Content must cover:
- Agent file: `agents/<name>.md` or `agents/<name>/AGENT.md`
- Frontmatter: `name` (3–50 chars, lowercase+hyphens), `description` (with 2–4 `<example>` blocks), `model` (inherit/sonnet/opus/haiku), `color` (blue/cyan/green/yellow/magenta/red), optional `tools` array
- `<example>` block format: Context, user, assistant, `<commentary>`
- System prompt: second person ("You are...")
- Color semantics: blue/cyan=analysis, green=generation, yellow=validation, red=security, magenta=creative

- [ ] **Step 4: Create hook-conventions.md**

Content must cover:
- Plugin format: `hooks/hooks.json` with wrapper `{"hooks": {...}}`
- 9 valid events: PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification
- Hook types: `prompt` (inline prompt) and `command` (shell)
- Matcher syntax
- `${CLAUDE_PLUGIN_ROOT}` required for all paths
- Security: no hardcoded credentials, HTTPS/WSS for external
- All hooks run in parallel — design for independence

- [ ] **Step 5: Create marketplace-conventions.md**

Content must cover:
- `marketplace.json` schema: `name`, `owner` (name, email), `plugins` array
- Each plugin entry: `name`, `source` (relative path), `description`
- Version consistency: plugin.json version ↔ package.json version
- Naming: no conflicts between sibling plugins
- Required per-plugin files: README.md, `.claude-plugin/plugin.json`

- [ ] **Step 6: Verify all 5 profiles exist**

```bash
ls references/plugin-profiles/
```
Expected: `agent-conventions.md`, `hook-conventions.md`, `marketplace-conventions.md`, `plugin-structure.md`, `skill-conventions.md`

- [ ] **Step 7: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/references/plugin-profiles/
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): add 5 plugin reference profiles derived from official plugin-dev conventions"
```

---

## Task 4: Create 6 New Scan Skills

**Files:**
- Create: `skills/scan-manifest-structure/SKILL.md`
- Create: `skills/scan-skill-quality/SKILL.md`
- Create: `skills/scan-agent-design/SKILL.md`
- Create: `skills/scan-hook-correctness/SKILL.md`
- Create: `skills/scan-marketplace-consistency/SKILL.md`
- Create: `skills/scan-convention-adherence/SKILL.md`

Each skill follows the exact same contract as existing scan skills. Input: `PROJECT_PATH`, `STACK`, `PLUGIN_PROFILES_DIR`, `SCAN_REPORTS_DIR`, `CHANGED_FILES`, `OFFICIAL_PLUGINS_INDEX_PATH`. Output: `DimensionReport` JSON.

- [ ] **Step 1: Create scan-manifest-structure/SKILL.md**

Frontmatter:
```yaml
---
name: scan-manifest-structure
description: |
  Validate Claude plugin manifest (plugin.json), directory layout, naming conventions,
  required files, and .claude-plugin/ placement.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
---
```

Workflow steps:
1. Read `.claude-plugin/plugin.json` — validate JSON, check required fields (name), recommended fields (version, description, author, keywords)
2. Validate name against kebab-case regex
3. Glob for expected directories: `skills/`, `agents/`, `hooks/`, `commands/` — flag `commands/` as deprecated
4. Check required files: README.md, at least one SKILL.md or agent .md
5. Grep for hardcoded absolute paths (should use `${CLAUDE_PLUGIN_ROOT}`)
6. Read `OFFICIAL_PLUGINS_INDEX_PATH` — compare directory structure against official plugins
7. Produce findings array

- [ ] **Step 2: Create scan-skill-quality/SKILL.md**

Frontmatter:
```yaml
---
name: scan-skill-quality
description: |
  Evaluate SKILL.md frontmatter quality, description triggers, word counts,
  progressive disclosure, and resource organization in Claude plugins.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
---
```

Workflow steps:
1. Glob `skills/*/SKILL.md` — inventory all skills
2. For each SKILL.md: read and parse YAML frontmatter
3. Validate: `name` present, `description` present, starts with "Use when...", third person, <1,024 chars
4. Count body words (below frontmatter `---`). Flag if outside 1,000–3,000 range
5. Check for `@file` references in body (anti-pattern)
6. Check `allowed-tools` — flag if missing when skill uses tools, or overly broad
7. Glob for supporting dirs (references/, examples/, scripts/) — flag large inline content that should be in supporting files
8. Read `OFFICIAL_PLUGINS_INDEX_PATH` — compare word count distribution, description patterns against official skills
9. Read `PLUGIN_PROFILES_DIR/skill-conventions.md` for ground truth
10. Produce findings array

- [ ] **Step 3: Create scan-agent-design/SKILL.md**

Frontmatter:
```yaml
---
name: scan-agent-design
description: |
  Evaluate AGENT.md frontmatter format, example blocks, model/color validity,
  system prompt quality, and tool scoping in Claude plugins.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
---
```

Workflow steps:
1. Glob `agents/*.md` and `agents/*/AGENT.md` — inventory all agents
2. For each agent: read and parse YAML frontmatter
3. Validate: `name` (3–50 chars, lowercase+hyphens), `description` (has `<example>` blocks), `model` (inherit/sonnet/opus/haiku), `color` (blue/cyan/green/yellow/magenta/red)
4. Count `<example>` blocks — flag if < 2
5. Validate example format: Context, user, assistant, `<commentary>`
6. Check system prompt body uses second person
7. Check `tools` array scoping — flag if empty or overly broad
8. Read `OFFICIAL_PLUGINS_INDEX_PATH` — compare patterns against official agents
9. Read `PLUGIN_PROFILES_DIR/agent-conventions.md` for ground truth
10. Produce findings array

- [ ] **Step 4: Create scan-hook-correctness/SKILL.md**

Frontmatter:
```yaml
---
name: scan-hook-correctness
description: |
  Validate hooks.json schema, event names, matcher patterns, script existence,
  and security in Claude plugin hook configurations.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
---
```

Workflow steps:
1. Glob `hooks/hooks.json` — if not found, return empty findings (hooks are optional)
2. Read and validate JSON structure — must be `{"hooks": {...}}` wrapper format
3. For each event key: validate against the 9 valid events
4. For each hook entry: check `type` (prompt or command), validate `matcher` regex
5. For command hooks: verify referenced scripts exist (Glob)
6. Grep all hook scripts for hardcoded paths (should use `${CLAUDE_PLUGIN_ROOT}`)
7. Grep for credential patterns in hook scripts
8. Read `PLUGIN_PROFILES_DIR/hook-conventions.md` for ground truth
9. Produce findings array

- [ ] **Step 5: Create scan-marketplace-consistency/SKILL.md**

Frontmatter:
```yaml
---
name: scan-marketplace-consistency
description: |
  Check marketplace.json registry alignment, version consistency across
  plugin.json and package.json, cross-plugin naming conflicts, and README presence.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
---
```

Workflow steps:
1. Detect parent marketplace: check if `../marketplace.json` or `../../.claude-plugin/marketplace.json` exists
2. If no marketplace found: return single info finding ("No parent marketplace detected")
3. Read marketplace.json — find entry matching this plugin's name
4. If not listed: critical finding
5. Compare: description in marketplace.json vs plugin.json
6. Compare: version in plugin.json vs package.json (if package.json exists)
7. Glob sibling plugin dirs — check for naming conflicts
8. Check README.md exists and is non-empty
9. Read `PLUGIN_PROFILES_DIR/marketplace-conventions.md` for ground truth
10. Produce findings array

- [ ] **Step 6: Create scan-convention-adherence/SKILL.md**

Frontmatter:
```yaml
---
name: scan-convention-adherence
description: |
  Detect deprecated commands/ usage, @file anti-patterns, token budget violations,
  and drift from official Claude plugin conventions.
  Sub-skill of analyze-codebase — executed inline by the orchestrator in --plugin mode.
---
```

Workflow steps:
1. Glob `commands/*.md` — flag each as deprecated (should be skills)
2. Grep all `.md` files for `@file` or `@path` references in skill cross-references (anti-pattern)
3. For each SKILL.md: check frontmatter description length against 1,024 char budget
4. Read `OFFICIAL_PLUGINS_INDEX_PATH` — build a structural comparison:
   - Compare directory layout (skills count, agents count, hooks presence) against official plugins
   - Compare naming patterns (skill names, agent names) against official conventions
   - Flag significant divergence as "convention drift"
5. Check for duplicate functionality: skills with overlapping trigger descriptions
6. Read all reference profiles from `PLUGIN_PROFILES_DIR` for ground truth
7. Produce findings array

- [ ] **Step 7: Verify all 6 new skill dirs exist**

```bash
ls skills/scan-manifest-structure/ skills/scan-skill-quality/ skills/scan-agent-design/ skills/scan-hook-correctness/ skills/scan-marketplace-consistency/ skills/scan-convention-adherence/
```
Expected: each contains `SKILL.md`

- [ ] **Step 8: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/scan-manifest-structure/ code-analysis/skills/scan-skill-quality/ code-analysis/skills/scan-agent-design/ code-analysis/skills/scan-hook-correctness/ code-analysis/skills/scan-marketplace-consistency/ code-analysis/skills/scan-convention-adherence/
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): add 6 new plugin-specific scan skills"
```

---

## Task 5: Adapt 4 Existing Scan Skills for Plugin Mode

**Files:**
- Modify: `skills/scan-quality/SKILL.md`
- Modify: `skills/scan-dependencies/SKILL.md`
- Modify: `skills/scan-tech-debt/SKILL.md`
- Modify: `skills/scan-security/SKILL.md`

Each skill gains a MODE check at the top of the Workflow section and an alternative plugin code path.

- [ ] **Step 1: Add plugin mode to scan-quality**

After the Input section, add a MODE branch:

```markdown
### Mode Branch

If `MODE=plugin`:
- Skip Steps 1–6 (general code quality). Execute Plugin Quality steps instead.

### Plugin Quality Steps (MODE=plugin only)

#### Step P1 — Map Markdown Files

1. Glob all `.md` files in the plugin directory (exclude `node_modules/`, `.git/`)
2. Categorize: skills (skills/*/SKILL.md), agents (agents/*.md, agents/*/AGENT.md), reference docs, README

#### Step P2 — Check Word Counts

1. For each SKILL.md: count words in body (below frontmatter). Flag:
   - Below 500 words: severity **high** ("skill too thin")
   - Below 1,000: **medium** ("skill could be more detailed")
   - Above 3,000: **medium** ("skill may need splitting")
   - Above 5,000: **high** ("skill exceeds maximum")
2. For each agent: count words in system prompt body. Flag if > 5,000 words

#### Step P3 — Check Content Duplication

1. Read skill bodies and detect repeated instruction blocks across skills
2. Flag duplicated blocks > 5 lines appearing in 2+ skills
3. Severity: **medium** for duplication within same plugin

#### Step P4 — Check Markdown Quality

1. Grep for broken markdown: unclosed code fences, orphaned link references, inconsistent heading hierarchy
2. Severity: **low** for formatting issues
```

- [ ] **Step 2: Add plugin mode to scan-dependencies**

After the Input section, add:

```markdown
### Mode Branch

If `MODE=plugin`:
- Skip Steps 1–6 (package dependencies). Execute Plugin Dependencies steps instead.

### Plugin Dependencies Steps (MODE=plugin only)

#### Step P1 — Scan Cross-References

1. Grep all `.md` files for skill references by name (e.g., "invoke the writing-plans skill", "use superpowers:brainstorming")
2. Build a dependency graph: which skills reference which other skills/plugins

#### Step P2 — Scan @file Includes

1. Grep for `@` file path references (e.g., `@skills/writing-plans/SKILL.md`)
2. Verify each referenced file exists at the declared path (Glob)
3. Flag broken references: severity **high**

#### Step P3 — Scan MCP Server Dependencies

1. Read `.claude-plugin/plugin.json` for `mcpServers` declarations
2. Verify MCP server configurations are valid
3. Flag missing or misconfigured servers: severity **high**

#### Step P4 — Scan Intra-Plugin References

1. Grep for `${CLAUDE_PLUGIN_ROOT}` usage in all files
2. Verify each path resolves to an existing file
3. Flag broken internal references: severity **high**

#### Step P5 — Produce Findings

Compile findings array with `dimension: "dependencies"`.
```

- [ ] **Step 3: Add plugin mode to scan-tech-debt**

After the Input section, add:

```markdown
### Mode Branch

If `MODE=plugin`:
- Execute Steps 1 (TODO markers) normally but scoped to `.md` and `.sh` files
- Skip Steps 2–4 (language-specific deprecated APIs). Execute Plugin Tech Debt steps instead.

### Plugin Tech Debt Steps (MODE=plugin only)

#### Step P1 — Detect Deprecated commands/ Usage

1. Glob `commands/*.md` — each file is a finding
2. Severity: **high** if the command has no equivalent skill, **medium** if a skill equivalent exists
3. Recommendation: "Migrate command to skills/<name>/SKILL.md per plugin-dev conventions"

#### Step P2 — Detect Legacy Format Patterns

1. Grep for `manifest.json` at plugin root (legacy — should be `.claude-plugin/plugin.json`)
2. Grep for `disable-model-invocation` in skill frontmatter (legacy command field in skills)
3. Grep for `argument-hint` in skill frontmatter (command-era field)
4. Severity: **medium** for each legacy pattern

#### Step P3 — Detect Stale Documentation

1. Check if README.md references a version that doesn't match plugin.json version
2. Check for references to removed skills/agents (Grep for names, Glob to verify existence)
3. Severity: **low** for stale docs
```

- [ ] **Step 4: Add plugin mode to scan-security**

After the Input section, add:

```markdown
### Mode Branch

If `MODE=plugin`:
- Execute Step 1 (hardcoded secrets) normally but scoped to all plugin files
- Skip Steps 2–5 (injection, XSS, CSRF, auth). Execute Plugin Security steps instead.

### Plugin Security Steps (MODE=plugin only)

#### Step P1 — Scan Hook Scripts for Credentials

1. Glob `hooks/**/*.sh`, `hooks/**/*.js`, `hooks/**/*.py`
2. Grep for secret patterns: API_KEY, password, token, secret assignments
3. Grep for hardcoded URLs with credentials
4. Severity: **critical** for confirmed secrets

#### Step P2 — Validate ${CLAUDE_PLUGIN_ROOT} Usage

1. Grep all hook scripts and MCP configs for hardcoded absolute paths
2. Flag any path that should use `${CLAUDE_PLUGIN_ROOT}` instead
3. Severity: **high** for hardcoded paths (portability and security risk)

#### Step P3 — Check .local.md Credential Exposure

1. Grep for `.local.md` patterns — verify they're in `.gitignore`
2. Check if any `.local.md` files are tracked in git
3. Severity: **critical** for tracked credential files

#### Step P4 — Check MCP Security

1. Read MCP server configs for non-HTTPS/WSS URLs
2. Flag HTTP/WS connections: severity **high**
3. Check for hardcoded auth tokens in MCP configs: severity **critical**
```

- [ ] **Step 5: Add MODE and PLUGIN_PROFILES_DIR to Input sections**

In each of the 4 files, add to the Input section:

```markdown
- `MODE`: "plugin" when running in plugin analysis mode, absent otherwise
- `PLUGIN_PROFILES_DIR`: Path to `references/plugin-profiles/` (only when MODE=plugin)
```

- [ ] **Step 6: Verify all 4 files have the MODE branch**

```bash
grep -l "MODE=plugin" skills/scan-quality/SKILL.md skills/scan-dependencies/SKILL.md skills/scan-tech-debt/SKILL.md skills/scan-security/SKILL.md
```
Expected: all 4 files listed

- [ ] **Step 7: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/scan-quality/SKILL.md code-analysis/skills/scan-dependencies/SKILL.md code-analysis/skills/scan-tech-debt/SKILL.md code-analysis/skills/scan-security/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): add plugin mode branch to 4 adapted scan skills"
```

---

## Task 6: Update code-analyzer Agent

**Files:**
- Modify: `agents/code-analyzer.md`
- Modify: `agents/code-analyzer/AGENT.md`

Both files have identical content. Update both to stay in sync (pre-existing tech debt — both must match).

- [ ] **Step 1: Add plugin dimensions to Input section**

In the Input section (line 47), extend the dimension list:

```markdown
- A dimension to scan (architecture, quality, dependencies, patterns, testing, performance, security, tech-debt, manifest-structure, skill-quality, agent-design, hook-correctness, marketplace-consistency, convention-adherence)
```

- [ ] **Step 2: Add MODE to Input section**

After the stack information bullet, add:

```markdown
- MODE (optional): "plugin" when running in plugin analysis mode
- PLUGIN_PROFILES_DIR (when MODE=plugin): path to plugin reference profiles
- OFFICIAL_PLUGINS_INDEX_PATH (when MODE=plugin): path to official plugins comparison index JSON
```

- [ ] **Step 3: Add plugin branch to Step 2 (Load Resources)**

After the existing Step 2 content, add:

```markdown
**When MODE=plugin:**

Read ONLY the files needed for THIS dimension:
1. `${CLAUDE_PLUGIN_ROOT}/skills/scan-{dimension}/SKILL.md` — the scan workflow
2. `${CLAUDE_PLUGIN_ROOT}/references/plugin-profiles/{relevant-profile}.md` — instead of language/framework profiles

Profile mapping:
- manifest-structure → `plugin-structure.md`
- skill-quality → `skill-conventions.md`
- agent-design → `agent-conventions.md`
- hook-correctness → `hook-conventions.md`
- marketplace-consistency → `marketplace-conventions.md`
- convention-adherence → all profiles
- quality, dependencies, tech-debt, security → no profile needed (adapted dimensions use their scan skill's built-in plugin logic)

Do NOT load language-profiles or framework-profiles in plugin mode.
```

- [ ] **Step 4: Add plugin branch to Step 3 (Execute Scan)**

After the existing Step 3 content, add:

```markdown
**When MODE=plugin:**

Follow the sub-skill's workflow with:
- `PROJECT_PATH`: The target path
- `STACK`: `{ languages: ["claude-plugin"], frameworks: [] }`
- `MODE`: "plugin"
- `PLUGIN_PROFILES_DIR`: Provided by orchestrator
- `OFFICIAL_PLUGINS_INDEX_PATH`: Provided by orchestrator (may be null for adapted dimensions)
```

- [ ] **Step 5: Add plugin example to description**

In the frontmatter description, add a new example block:

```yaml
  <example>
  Context: Orchestrator dispatches plugin analysis scans
  user: "Analyze this Claude plugin"
  assistant: "I'll dispatch code-analyzer agents for each plugin dimension."
  <commentary>
  Plugin mode — the orchestrator passes MODE=plugin and plugin-specific inputs.
  The agent loads plugin profiles instead of language/framework profiles.
  </commentary>
  </example>
```

- [ ] **Step 6: Verify both agent files are identical**

```bash
diff agents/code-analyzer.md agents/code-analyzer/AGENT.md
```
Expected: no differences

- [ ] **Step 7: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/agents/code-analyzer.md code-analysis/agents/code-analyzer/AGENT.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): add plugin mode to code-analyzer agent with profile mapping"
```

---

## Task 7: Update analyze-codebase Orchestrator

**Files:**
- Modify: `skills/analyze-codebase/SKILL.md`

- [ ] **Step 1: Update description in frontmatter**

Extend the description to include plugin triggers:

```yaml
description: |
  Use when the user asks to "analyze this codebase", "scan for issues",
  "find refactoring opportunities", "code analysis", "audit this project",
  or wants a comprehensive multi-dimension codebase analysis with refactoring plans.
  Also use when the user asks to "analyze architecture", "check code quality",
  "scan for security issues", "find tech debt", or similar dimension-specific requests.
  When used with --plugin flag, analyzes Claude Code plugins across 10 plugin-specific
  dimensions including manifest structure, skill quality, agent design, and conventions.
```

- [ ] **Step 2: Add --plugin flag to Optional Flags section**

After the existing flags (line 68), add:

```markdown
- `--plugin` — activate plugin analysis mode. Swaps dimension set to 10 plugin-specific dimensions (4 adapted + 6 new). Requires target to contain `.claude-plugin/plugin.json`.
```

- [ ] **Step 3: Add plugin dimension map**

After the existing dimension map (line 144), add:

```markdown
When `--plugin` is set, dimension map changes to:
Plugin dimensions: `quality`, `deps` → dependencies, `debt` → tech-debt, `security`, `mnf` → manifest-structure, `skl` → skill-quality, `agt` → agent-design, `hkc` → hook-correctness, `mkt` → marketplace-consistency, `cvn` → convention-adherence. Default: all 10.

Dimensions NOT available in plugin mode: architecture, patterns, performance, testing.
```

- [ ] **Step 4: Add plugin branch to Stage 1**

After the existing Stage 1 content, add:

```markdown
**When `--plugin` is set:**

Stage 1 becomes **Detect Plugin Structure**:

1. Verify `.claude-plugin/plugin.json` exists — abort with error if missing: "Target directory is not a Claude plugin (no .claude-plugin/plugin.json found)"
2. Read `plugin.json` — extract name, version, description
3. Glob `skills/*/SKILL.md` — count and list skills
4. Glob `agents/*.md` and `agents/*/AGENT.md` — count and list agents
5. Glob `hooks/hooks.json` — note if hooks exist
6. Glob `commands/*.md` — note if deprecated commands exist
7. Detect parent marketplace: check `../.claude-plugin/marketplace.json`
8. Build official plugins comparison index:
   a. Read `~/.claude/plugins/cache/claude-plugins-official/` directory listing
   b. For each official plugin, find the active version dir and catalog: skill count, agent count, hook presence, frontmatter patterns, word count ranges
   c. Write index to `.code-analysis/plugin-analysis-cache/official-plugins-index.json`
9. Output: `STACK = { languages: ["claude-plugin"], frameworks: [] }`, `PLUGIN_INVENTORY`, `OFFICIAL_PLUGINS_INDEX_PATH`
```

- [ ] **Step 5: Add plugin branch to Stage 2**

After the existing Stage 2 dispatch block, add:

```markdown
**When `--plugin` is set:**

Parse `--dimensions` flag using plugin dimension map. Default: all 10.

Dispatch ALL `code-analyzer` subagents in parallel with:
```
Analyze the plugin at [PROJECT_PATH] for the [DIMENSION] dimension.
Mode: plugin
Plugin Profiles Dir: ${CLAUDE_PLUGIN_ROOT}/references/plugin-profiles/
Official Plugins Index Path: [OFFICIAL_PLUGINS_INDEX_PATH]
Return ONLY a structured JSON findings array.
```

Additional parameters for each code-analyzer agent:
- MODE: "plugin"
- PLUGIN_PROFILES_DIR: "${CLAUDE_PLUGIN_ROOT}/references/plugin-profiles/"
- OFFICIAL_PLUGINS_INDEX_PATH: path from Stage 1 step 8c
- SCAN_REPORTS_DIR: ".code-analysis/scan-reports"
- CHANGED_FILES: from --changed-files-hint or null
- Model: `MODEL_MAP.scanning`
```

- [ ] **Step 6: Verify the skill reads correctly**

Read the full file and check no formatting issues or conflicts with existing content.

- [ ] **Step 7: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/analyze-codebase/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): add --plugin flag to analyze-codebase orchestrator with plugin stage logic"
```

---

## Task 8: Update ralph-loop

**Files:**
- Modify: `skills/ralph-loop/SKILL.md`

- [ ] **Step 1: Update description in frontmatter**

Extend to mention plugin mode:

```yaml
description: |
  Use when iteratively improving codebase dimension scores to target thresholds
  using analyze-codebase + ralph-loop. Supports single-dimension (positional args)
  or multi-dimension (--targets flag) with per-dimension target scores.
  Applies when the user wants to fix findings across one or more dimensions,
  run a score improvement loop, or automate refactoring until quality thresholds are reached.
  Supports --plugin flag for Claude Code plugin analysis dimensions.
```

- [ ] **Step 2: Add --plugin flag to Input Parsing**

In the single-dimension and multi-dimension usage blocks, add `[--plugin]`:

```bash
/code-analysis:ralph-loop <dimension> <target> [--plugin] [--max-iterations N] [--model <model-spec>]
/code-analysis:ralph-loop --targets="skl:8,cvn:7" --plugin [--max-iterations N] [--model <model-spec>]
```

- [ ] **Step 3: Add plugin shorthands to Parsing rules**

After the existing shorthand line (line 38), add:

```markdown
- Plugin dimension shorthand (requires `--plugin`): `mnf` → manifest-structure, `skl` → skill-quality, `agt` → agent-design, `hkc` → hook-correctness, `mkt` → marketplace-consistency, `cvn` → convention-adherence
- When `--plugin` is set, only plugin-valid dimensions are accepted: quality, deps/dependencies, debt/tech-debt, security, mnf/manifest-structure, skl/skill-quality, agt/agent-design, hkc/hook-correctness, mkt/marketplace-consistency, cvn/convention-adherence
- Non-plugin dimensions (arch, patterns, perf, testing) with `--plugin` flag → error: "Dimension '{name}' is not available in plugin mode"
```

- [ ] **Step 4: Add --plugin passthrough to analyze-codebase invocations**

Find all places where ralph-loop invokes `analyze-codebase` (scanning and rescanning phases) and add:

```markdown
When `--plugin` is set, pass `--plugin` to all `/analyze-codebase` invocations.
```

- [ ] **Step 5: Add --plugin to state file**

In the State File section, add a `mode` field:

```markdown
mode: plugin  # only present when --plugin was passed
```

- [ ] **Step 6: Verify the skill reads correctly**

Read and verify formatting.

- [ ] **Step 7: Commit**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/skills/ralph-loop/SKILL.md
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "feat(code-analysis): add --plugin flag to ralph-loop with plugin dimension shorthands"
```

---

## Task 9: Version Bump and Final Verification

**Files:**
- Modify: `.claude-plugin/plugin.json:3` (version)
- Modify: `package.json:3` (version)

- [ ] **Step 1: Bump plugin.json version**

Change `"version": "0.5.0"` to `"version": "0.6.0"` in `.claude-plugin/plugin.json`.

- [ ] **Step 2: Bump package.json version**

Change version in `package.json` if it tracks the plugin version. (Currently `"version": "0.0.0"` with `"private": true` — leave as-is if it's a placeholder, or update to `"0.6.0"` to match.)

- [ ] **Step 3: Update plugin.json keywords**

Add `"plugin-analysis"` to the keywords array.

- [ ] **Step 4: Verify full file inventory**

```bash
ls skills/scan-manifest-structure/SKILL.md skills/scan-skill-quality/SKILL.md skills/scan-agent-design/SKILL.md skills/scan-hook-correctness/SKILL.md skills/scan-marketplace-consistency/SKILL.md skills/scan-convention-adherence/SKILL.md references/plugin-profiles/plugin-structure.md references/plugin-profiles/skill-conventions.md references/plugin-profiles/agent-conventions.md references/plugin-profiles/hook-conventions.md references/plugin-profiles/marketplace-conventions.md
```
Expected: all 11 new files exist

- [ ] **Step 5: Verify dimension enums are consistent**

```bash
grep -c '"manifest-structure"' references/output-schemas.md
```
Expected: 3 (one per schema)

- [ ] **Step 6: Verify no broken references**

```bash
grep -r 'scan-manifest-structure\|scan-skill-quality\|scan-agent-design\|scan-hook-correctness\|scan-marketplace-consistency\|scan-convention-adherence' skills/analyze-codebase/SKILL.md references/analysis-dimensions.md
```
Expected: references exist in both files

- [ ] **Step 7: Commit version bump**

```bash
git -C /Users/keven.foster/document-perso/local-claude-marketplace add code-analysis/.claude-plugin/plugin.json code-analysis/package.json
git -C /Users/keven.foster/document-perso/local-claude-marketplace commit -m "chore(code-analysis): bump version to 0.6.0 for plugin analysis mode"
```

---

## Task Dependencies

```
Task 1 (schemas) ──────────────────────┐
Task 2 (dimensions ref) ──────────────┤
Task 3 (plugin profiles) ─────────────┤── All independent, can run in parallel
                                       │
Task 4 (6 new scan skills) ───────────┤── Depends on Task 3 (reads profiles)
Task 5 (4 adapted scan skills) ───────┤── Independent of Task 4
Task 6 (code-analyzer agent) ─────────┤── Depends on Tasks 4+5 (dispatches them)
Task 7 (orchestrator) ────────────────┤── Depends on Task 6 (dispatches agent)
Task 8 (ralph-loop) ──────────────────┤── Depends on Task 7 (invokes orchestrator)
Task 9 (version bump) ────────────────┘── Depends on all above
```

**Parallel batch 1:** Tasks 1, 2, 3 (all independent)
**Parallel batch 2:** Tasks 4, 5 (both depend only on Task 3)
**Sequential:** Task 6 → Task 7 → Task 8 → Task 9
