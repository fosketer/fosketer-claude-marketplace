# Marketplace Conventions Reference Profile

Ground truth for `marketplace.json` schema, plugin entry format, version consistency, naming collision rules, and required per-plugin files. Derived from official `plugin-dev` conventions and the `fosketer-claude-marketplace` implementation.

---

## 1. Marketplace Index File

The marketplace index file lives at `.claude-plugin/marketplace.json` at the marketplace root.

```
marketplace-root/
├── .claude-plugin/
│   └── marketplace.json    # Central marketplace index (required)
├── plugin-one/             # Plugin directory
│   ├── .claude-plugin/
│   │   └── plugin.json
│   └── README.md
└── plugin-two/
    ├── .claude-plugin/
    │   └── plugin.json
    └── README.md
```

---

## 2. marketplace.json Schema

### 2.1 Full Schema

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "marketplace-name",
  "owner": {
    "name": "Owner Name",
    "email": "owner@example.com"
  },
  "plugins": [
    {
      "name": "plugin-name",
      "source": "./plugin-directory",
      "description": "Brief description of plugin purpose"
    }
  ]
}
```

### 2.2 Top-Level Fields

#### `$schema` (recommended)

```json
"$schema": "https://anthropic.com/claude-code/marketplace.schema.json"
```

The JSON Schema reference for validation tooling. Include for IDE support and validation.

#### `name` (required)

The marketplace identifier.

**Format**: kebab-case
**Rules**:
- Lowercase letters, numbers, and hyphens only
- Must be unique (identifies this marketplace instance)
- Use owner prefix convention: `owner-marketplace-name` or `owner-claude-marketplace`

**Examples**:
- `"fosketer-claude-marketplace"` — correct
- `"my-plugins"` — acceptable
- `"My Plugins"` — wrong (spaces, uppercase)

#### `owner` (required)

Object identifying the marketplace owner.

```json
{
  "owner": {
    "name": "Marketplace Owner",
    "email": "owner@example.com"
  }
}
```

**Fields**:
- `name` (required): Human-readable owner name (individual or organization)
- `email` (required): Contact email for the marketplace

Both `name` and `email` are required in the `owner` object.

#### `plugins` (required)

Array of plugin entry objects. May be empty `[]` but the field must be present.

---

## 3. Plugin Entry Format

Each entry in the `plugins` array describes one plugin registered in the marketplace.

```json
{
  "name": "plugin-name",
  "source": "./plugin-directory",
  "description": "Brief description of plugin purpose and key features"
}
```

### 3.1 `name` (required)

The plugin's identifier as it appears in the marketplace.

**Rules**:
- Must match the `name` field in the plugin's own `.claude-plugin/plugin.json`
- Must be unique within the marketplace — no two plugins may share the same name
- Format: kebab-case, matching the plugin name regex `/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/`

**Name collision rule**: If two plugins have the same `name` in `marketplace.json`, the marketplace is invalid. Each plugin name must be globally unique within the registry.

### 3.2 `source` (required)

Relative path from the marketplace root to the plugin directory.

**Rules**:
- Must be a relative path starting with `./`
- Points to the plugin root directory (not to `.claude-plugin/plugin.json` directly)
- The referenced directory must exist and contain `.claude-plugin/plugin.json`
- No absolute paths
- No parent directory navigation (`../`)

**Valid examples**:
- `"./multi-angle-research"` — correct
- `"./code-analysis"` — correct
- `"./plugins/my-plugin"` — correct (subdirectory)

**Invalid examples**:
- `"/Users/name/plugins/my-plugin"` — absolute path
- `"my-plugin"` — missing `./` prefix
- `"../external-plugin"` — parent traversal

### 3.3 `description` (required)

Human-readable description of the plugin for marketplace display.

**Requirements**:
- Must be present for every plugin entry
- Should match or be derived from the description in `plugin.json`
- Concise but informative (50–200 characters recommended)
- Active voice, focused on what the plugin does

**Example**:
```json
"description": "Structured multi-angle research pipeline — intake, parallel brainstorm, plan, execute, and document research on any topic"
```

---

## 4. Complete marketplace.json Example

Based on the `fosketer-claude-marketplace` implementation:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "fosketer-claude-marketplace",
  "owner": {
    "name": "fosketer",
    "email": "marketplace@fosketer.dev"
  },
  "plugins": [
    {
      "name": "multi-angle-research",
      "source": "./multi-angle-research",
      "description": "Structured multi-angle research pipeline — intake, parallel brainstorm, plan, execute, and document research on any topic"
    },
    {
      "name": "code-analysis",
      "source": "./code-analysis",
      "description": "Multi-dimensional codebase analysis — structure, quality, security, and testing scans with scored reports, critic validation, and refactoring plan generation"
    }
  ]
}
```

---

## 5. Required Per-Plugin Files

Every plugin registered in a marketplace MUST have these files:

### 5.1 `.claude-plugin/plugin.json` (required)

The plugin manifest at `.claude-plugin/plugin.json` relative to the plugin root.

Required fields:
- `name` — must match the marketplace entry's `name`
- `version` — must be present (recommended; critical for version consistency)

Recommended fields:
- `description` — should match or align with marketplace entry description
- `author` with `name` and `email`
- `keywords`

### 5.2 `README.md` (required)

A `README.md` at the plugin root directory.

Must include:
- Plugin purpose and overview
- Installation instructions
- Usage examples
- Any required environment variables

A plugin without `README.md` is non-compliant with marketplace conventions.

---

## 6. Version Consistency Rules

Version numbers must be consistent across all files that declare them.

### 6.1 Files That Declare Version

For a typical marketplace plugin, version appears in:
1. `.claude-plugin/plugin.json` — `"version"` field (primary source of truth)
2. `package.json` — `"version"` field (if JavaScript/Node.js plugin)

### 6.2 Consistency Requirement

The `version` value in `plugin.json` MUST match the `version` in `package.json` when both files exist.

**Compliant**:
```json
// .claude-plugin/plugin.json
{ "name": "my-plugin", "version": "1.2.0" }

// package.json
{ "name": "@scope/my-plugin", "version": "1.2.0" }
```

**Non-compliant**:
```json
// .claude-plugin/plugin.json
{ "name": "my-plugin", "version": "1.2.0" }

// package.json
{ "name": "@scope/my-plugin", "version": "1.1.0" }  // Different!
```

### 6.3 Version Format

All version fields must use semantic versioning: `MAJOR.MINOR.PATCH`.

- `"1.0.0"` — correct
- `"0.1.0"` — correct (initial development)
- `"1.0"` — wrong (missing PATCH)
- `"v1.0.0"` — wrong (v prefix)

---

## 7. Naming Collision Rules

### 7.1 Uniqueness Within the Marketplace

No two plugins in `plugins` array may share the same `name`. The name is used as the unique identifier for installation and conflict detection.

**Detection**: Compare the `name` field of every entry in `plugins` array. Any duplicate is a collision violation.

### 7.2 Consistency Between Marketplace and Plugin Manifest

The `name` in the marketplace entry MUST match the `name` in the plugin's `.claude-plugin/plugin.json`.

**Compliant**:
```json
// marketplace.json entry
{ "name": "code-analysis", "source": "./code-analysis" }

// code-analysis/.claude-plugin/plugin.json
{ "name": "code-analysis" }
```

**Non-compliant**:
```json
// marketplace.json entry
{ "name": "code-analysis", "source": "./code-analysis" }

// code-analysis/.claude-plugin/plugin.json
{ "name": "codeanalysis" }  // Name mismatch!
```

### 7.3 Source Path Resolution

The `source` path in the marketplace entry must resolve to a directory that exists and contains `.claude-plugin/plugin.json`. A source path that cannot be resolved is a broken reference.

---

## 8. Marketplace Structure Validation Rules

### 8.1 marketplace.json Validation

- Valid JSON syntax (no trailing commas, no comments)
- `name` field present at top level
- `owner` object present with `name` and `email`
- `plugins` array present (may be empty)
- Each plugin entry has `name`, `source`, and `description`
- No duplicate plugin names in `plugins` array

### 8.2 Per-Plugin Validation

For each entry in `plugins`:

1. `source` path resolves to an existing directory
2. Directory contains `.claude-plugin/plugin.json`
3. Directory contains `README.md`
4. Plugin's `plugin.json` `name` matches marketplace entry `name`
5. If `package.json` exists, `version` matches `plugin.json` version

---

## 9. Validation Checklist

**marketplace.json file**:
- [ ] File exists at `.claude-plugin/marketplace.json` in marketplace root
- [ ] Valid JSON (no syntax errors)
- [ ] `$schema` field present (recommended)
- [ ] `name` field present and kebab-case
- [ ] `owner.name` present (string)
- [ ] `owner.email` present (string)
- [ ] `plugins` array present

**Per plugin entry in `plugins` array**:
- [ ] `name` field present and kebab-case
- [ ] `source` field present, starts with `./`, no absolute paths
- [ ] `description` field present and non-empty
- [ ] No duplicate `name` values across all entries

**Per referenced plugin directory**:
- [ ] `source` path directory exists
- [ ] `.claude-plugin/plugin.json` exists in the directory
- [ ] `README.md` exists in the directory
- [ ] Plugin `plugin.json` `name` matches marketplace entry `name`
- [ ] `plugin.json` version matches `package.json` version if `package.json` exists

---

## 10. Common Non-Compliance Patterns

| Issue | Severity | Description |
|-------|----------|-------------|
| `marketplace.json` not in `.claude-plugin/` | Critical | Wrong location for marketplace index |
| `owner` field absent | Critical | Required field missing |
| `owner.email` absent | Critical | Required sub-field missing |
| `plugins` array absent | Critical | Required field missing |
| Plugin entry missing `name` | Critical | Required entry field |
| Plugin entry missing `source` | Critical | Required entry field |
| Duplicate plugin names in array | Critical | Name collision |
| `source` is absolute path | Critical | Must be relative with `./` |
| Plugin manifest `name` mismatches marketplace entry `name` | Critical | Version/name inconsistency |
| Plugin `plugin.json` version mismatches `package.json` version | Major | Version inconsistency |
| Missing `README.md` in plugin directory | Major | Required per-plugin file |
| `source` path does not exist | Major | Broken reference |
| Plugin directory missing `.claude-plugin/plugin.json` | Major | Required per-plugin file |
| `description` absent from plugin entry | Minor | Required for marketplace display |
| `$schema` absent | Minor | Recommended for IDE support |
| Plugin description doesn't match `plugin.json` description | Minor | Inconsistency between declarations |
