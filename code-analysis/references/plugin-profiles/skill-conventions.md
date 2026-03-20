# Skill Conventions Reference Profile

Ground truth for SKILL.md structure, frontmatter schema, body style, progressive disclosure, and supporting resource organization. Derived from official `plugin-dev` skill-development skill conventions.

---

## 1. Skill File Location

Every skill in a plugin lives in its own subdirectory under `skills/`:

```
plugin-name/
└── skills/
    └── skill-name/
        ├── SKILL.md         # Required — exact filename
        ├── references/      # Optional — documentation loaded as needed
        ├── examples/        # Optional — working code examples
        ├── scripts/         # Optional — executable utilities
        └── assets/          # Optional — output files (templates, images)
```

**The file MUST be named `SKILL.md`** — not `README.md`, `SKILL.md.txt`, `skill.md` (lowercase), or any other variant. Auto-discovery scans for subdirectories containing exactly `SKILL.md`.

**Directory name**: Use kebab-case. The directory name becomes the skill's identifier. Example: `skills/api-testing/SKILL.md`.

---

## 2. SKILL.md Frontmatter

Every `SKILL.md` begins with a YAML frontmatter block delimited by `---`.

### 2.1 Required Frontmatter Fields

```yaml
---
name: skill-name
description: This skill should be used when the user asks to "specific phrase 1", "specific phrase 2", "specific phrase 3". Include exact phrases users would say that should trigger this skill.
---
```

Both `name` and `description` are required. A SKILL.md missing either field is non-compliant.

### 2.2 Optional Frontmatter Fields

```yaml
---
name: skill-name
description: This skill should be used when...
version: 0.1.0
allowed-tools: ["Read", "Grep", "Bash"]
---
```

- `version`: Semantic versioning string (`MAJOR.MINOR.PATCH`). Recommended.
- `allowed-tools`: Array of tool names to restrict skill tool access.

### 2.3 Name Field Rules

- **Format**: kebab-case (lowercase letters, numbers, hyphens)
- Must match the skill's directory name by convention
- Descriptive and topic-focused
- Good examples: `api-testing`, `error-handling`, `database-migrations`, `pdf-editor`
- Bad examples: `helper`, `utils`, `misc`, `skill1`

### 2.4 Description Field Rules — Critical

The description field determines when Claude Code activates the skill. It is the most important field in the frontmatter.

**Person**: Always third-person — "This skill should be used when the user asks to..."
- Correct: `"This skill should be used when the user asks to 'create a hook'..."`
- Wrong: `"Use this skill when you want to create a hook"`
- Wrong: `"Load when user needs hook help"`
- Wrong: `"Provides hook guidance"` (no trigger phrases, no third person)

**Format**: Must include specific quoted trigger phrases that users would actually say.

```yaml
description: This skill should be used when the user asks to "create a hook", "add a PreToolUse hook", "validate tool use", "implement prompt-based hooks", "use ${CLAUDE_PLUGIN_ROOT}", "set up event-driven automation", "block dangerous commands", or mentions hook events (PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification).
```

**Length**: Under 1,024 characters. Keep it dense with trigger phrases rather than prose explanation.

**Specificity**: Each trigger phrase must be concrete and concrete enough to distinguish this skill from others. Vague phrases like "working with code" or "help with files" fail.

**Coverage**: Cover multiple phrasings of the same intent. Users ask for the same thing many ways.

**Good description example**:
```yaml
description: This skill should be used when the user asks to "rotate a PDF", "flip a PDF", "convert PDF pages", "edit a PDF file", "extract pages from PDF", or needs guidance on PDF manipulation tasks.
```

**Bad description examples**:
```yaml
description: Provides guidance for working with PDFs.
# Wrong: vague, no trigger phrases, not third person

description: Use this skill when working with PDF files.
# Wrong: second person "Use this skill", no specific triggers

description: Load when user needs PDF help.
# Wrong: not third person format, vague
```

---

## 3. SKILL.md Body Requirements

### 3.1 Writing Style

**Use imperative/infinitive form throughout the body** — verb-first instructions, never second person.

Correct (imperative):
```markdown
To create a hook, define the event type.
Configure the MCP server with authentication.
Validate settings before use.
Parse the frontmatter using sed.
```

Incorrect (second person):
```markdown
You should create a hook by defining the event type.
You need to configure the MCP server.
You must validate settings.
```

**Rationale**: The body is consumed by another Claude instance. Imperative form is direct, unambiguous, and consistent.

### 3.2 Length Targets

| Target | Words |
|--------|-------|
| Ideal | 1,500–2,000 words |
| Acceptable maximum | 5,000 words |
| Warning zone | >3,000 words without `references/` |
| Hard limit | 5,000 words in `SKILL.md` |

Keep SKILL.md lean. Move detailed content to `references/` files. A 8,000-word SKILL.md is a compliance failure regardless of quality.

### 3.3 Required Body Sections

A compliant SKILL.md body answers these questions:

1. **What is this skill?** — A few sentences describing purpose (overview section)
2. **When is it used?** — Reference the frontmatter description; may elaborate inline
3. **How should Claude use it?** — Step-by-step workflow in imperative form; references to bundled resources

### 3.4 Body Structure Pattern

```markdown
# Skill Name

## Overview

[2–4 sentences describing purpose and key capabilities]

## [Core Concept 1]

[Essential instructions in imperative form]

## [Core Concept 2]

[Essential instructions]

## [Workflow / Process Steps]

[Numbered steps in imperative form]

## Additional Resources

### Reference Files

For detailed patterns and techniques, consult:
- **`references/patterns.md`** — Common patterns
- **`references/advanced.md`** — Advanced use cases

### Example Files

Working examples in `examples/`:
- **`examples/template.sh`** — Working example
```

### 3.5 Cross-References Rule

**Reference supporting files by relative path only — never by `@file` syntax.**

Correct:
```markdown
- **`references/patterns.md`** — Detailed patterns
- **`scripts/validate.sh`** — Validation utility
```

Incorrect:
```markdown
@references/patterns.md
See @skill-name for details
```

All referenced files must actually exist at the specified paths. A SKILL.md referencing a nonexistent file is non-compliant.

---

## 4. Progressive Disclosure System

Skills use a three-level loading system to manage context window efficiently:

| Level | Content | When Loaded | Size |
|-------|---------|-------------|------|
| 1 | Metadata (name + description) | Always in context | ~100 words |
| 2 | SKILL.md body | When skill triggers | <5,000 words |
| 3 | Bundled resources (references, scripts) | As needed by Claude | Unlimited* |

*Scripts can be executed without loading into context window.

**Design implication**: SKILL.md should contain only what Claude needs every time the skill activates. Move detailed, reference-heavy content to `references/` so it loads only when needed.

---

## 5. Supporting Directory Conventions

### 5.1 `references/`

Documentation intended to be loaded into context as needed.

**When to include**: For documentation Claude should reference while working; for detailed content that would bloat SKILL.md.

**Examples**:
- `references/patterns.md` — Common implementation patterns
- `references/api-reference.md` — API specifications
- `references/schema.md` — Database or data schemas
- `references/advanced.md` — Advanced techniques
- `references/migration.md` — Migration guides

**Size**: Each reference file can be large (2,000–5,000+ words). This is appropriate because they load only on demand.

**Anti-duplication rule**: Information should live in either SKILL.md or references files, not both. Prefer references for detailed material.

**Large files**: If any reference file exceeds ~10,000 words, include grep search patterns in SKILL.md to help Claude find relevant sections.

### 5.2 `examples/`

Working, complete, runnable code or configuration examples.

**When to include**: When users can directly copy or adapt the example.

**Examples**:
- `examples/validate-write.sh` — Complete bash hook script
- `examples/hooks-config.json` — Working hooks.json
- `examples/migration-template.sql` — Database migration template

**Requirements**: Examples must be complete and working. Broken or incomplete examples are worse than no examples.

### 5.3 `scripts/`

Executable utilities for repeated operations.

**When to include**: When the same code is rewritten repeatedly, or deterministic reliability is needed.

**Examples**:
- `scripts/validate-hook-schema.sh` — Validate hooks.json structure
- `scripts/rotate_pdf.py` — PDF rotation
- `scripts/parse-frontmatter.sh` — Parse YAML frontmatter

**Requirements**: Scripts must be executable and documented. Include usage comments at the top of each script.

**Benefits**: Token-efficient (may execute without loading into context); deterministic; reusable.

### 5.4 `assets/`

Files used in output, not loaded into context.

**When to include**: When the skill produces files that users copy or modify (templates, images, fonts, boilerplate).

**Examples**:
- `assets/logo.png` — Brand asset
- `assets/slides.pptx` — PowerPoint template
- `assets/frontend-template/` — HTML/React boilerplate directory

---

## 6. SKILL.md Reference Pattern

SKILL.md MUST explicitly reference all bundled resources so Claude knows they exist. An unreferenced `references/` directory is a compliance failure.

Correct pattern:
```markdown
## Additional Resources

### Reference Files

For detailed patterns and techniques, consult:
- **`references/patterns.md`** — Common patterns with 8+ proven examples
- **`references/advanced.md`** — Advanced techniques

### Example Files

Working examples in `examples/`:
- **`examples/script.sh`** — Complete working example

### Utility Scripts

- **`scripts/validate.sh`** — Validation utility (run before deployment)
```

---

## 7. Validation Checklist

Use this checklist when scanning a skill for compliance:

**Structure**:
- [ ] Skill lives in `skills/<skill-name>/SKILL.md` (exact filename `SKILL.md`)
- [ ] Skill directory uses kebab-case name
- [ ] All supporting directories (`references/`, `examples/`, `scripts/`) are documented in SKILL.md

**Frontmatter**:
- [ ] `name` field present and uses kebab-case
- [ ] `description` field present
- [ ] Description starts with "This skill should be used when..."  (third person)
- [ ] Description includes specific quoted trigger phrases
- [ ] Description is under 1,024 characters
- [ ] `version` present in semver format if specified

**Body**:
- [ ] Uses imperative/infinitive form throughout (no "you should", "you need to")
- [ ] Body is 1,500–2,000 words (ideally), under 5,000 words (required)
- [ ] All referenced files (`references/`, `examples/`, `scripts/`) actually exist
- [ ] No `@file` cross-reference syntax
- [ ] Contains "Additional Resources" section listing all bundled files

**Progressive disclosure**:
- [ ] Core concepts in SKILL.md; detailed docs in `references/`
- [ ] No duplication between SKILL.md and reference files
- [ ] Examples are complete and functional
- [ ] Scripts are executable

---

## 8. Common Non-Compliance Patterns

| Issue | Severity | Description |
|-------|----------|-------------|
| Wrong filename (`README.md` instead of `SKILL.md`) | Critical | Skill will not auto-discover |
| Missing `name` frontmatter | Critical | Skill invalid |
| Missing `description` frontmatter | Critical | Skill never activates |
| Second-person body (`"You should..."`) | Major | Violates writing style convention |
| Description not in third person | Major | Reduces trigger reliability |
| No trigger phrases in description | Major | Skill rarely activates |
| SKILL.md over 5,000 words | Major | Context window bloat |
| References exist but not mentioned in SKILL.md | Major | Claude doesn't know they exist |
| Non-existent files referenced | Major | Breaks Claude's workflow |
| `@file` syntax for cross-references | Minor | Non-standard, use relative paths |
| No `version` field | Minor | Recommended but not required |
| SKILL.md 2,000–3,000 words with no `references/` | Minor | May benefit from extraction |
