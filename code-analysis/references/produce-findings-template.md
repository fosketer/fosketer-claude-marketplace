# Produce Findings Template

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/schemas/finding-schema.md`.

## Required Fields

Every finding MUST include: `id`, `dimension`, `title`, `severity`, `description`, `recommendation`, `effort`, `tags`.

Optional fields: `file_path`, `line_start`, `line_end`, `snippet`, `previous_id`.

## Example Finding

```json
{
  "id": "DIM-e7b4a1-3f2a",
  "dimension": "<dimension-name>",
  "title": "Short descriptive title",
  "severity": "medium",
  "file_path": "path/to/file.ext",
  "line_start": 42,
  "line_end": 57,
  "snippet": "relevant code or content lines",
  "description": "What is wrong and why it matters",
  "recommendation": "Specific action to fix the issue",
  "effort": "small",
  "tags": ["category-tag"]
}
```

## Rules

- Always populate `snippet` with the relevant code lines when `file_path` and `line_start` are provided.
- Use the dimension-specific ID prefix (e.g., `STRC-`, `QUAL-`, `SEC-`, `TEST-`, `MNF-`, `SKL-`, `AGT-`, `HKC-`, `MKT-`, `CVN-`).
- Return the findings array to the orchestrator.
