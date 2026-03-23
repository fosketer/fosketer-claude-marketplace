# Finding & Dimension Report Schemas

> Extracted from output-schemas.md for role-specific loading. Canonical source for finding structure.

> schema_version: 0.8.0

> The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Finding Schema

Each individual finding produced by a scan dimension.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Finding",
  "type": "object",
  "required": ["id", "dimension", "title", "description", "severity", "recommendation", "effort"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[A-Z]{3,4}-(000000-[0-9a-f]{4}|[0-9a-f]{6}-[0-9a-f]{4})(-[2-9]\\d*)?$",
      "description": "Deterministic fingerprint: {DIM}-{file_hash6}-{title_hash4} for file findings, {DIM}-000000-{title_hash4} for null-file findings. Collision suffix starts at -2.",
      "examples": ["STRC-8f3a21-a1b2", "SEC-000000-a7f2", "QUAL-8f3a21-a1b2-2"]
    },
    "dimension": {
      "type": "string",
      "enum": ["structure", "quality", "security", "testing", "manifest-structure", "skill-quality", "agent-design", "hook-correctness", "marketplace-consistency", "convention-adherence"],
      "description": "The scan dimension that produced this finding"
    },
    "title": {
      "type": "string",
      "description": "Short summary (under 80 chars)",
      "maxLength": 80
    },
    "description": {
      "type": "string",
      "description": "Detailed explanation of the finding and why it matters"
    },
    "severity": {
      "type": "string",
      "enum": ["critical", "high", "medium", "low", "info"],
      "description": "Impact severity per the severity scale in analysis-dimensions.md"
    },
    "file_path": {
      "type": "string",
      "description": "Relative path from project root to the affected file. Null for project-wide findings.",
      "nullable": true
    },
    "line_start": {
      "type": "integer",
      "description": "Starting line number. Null if file-level or project-wide.",
      "nullable": true
    },
    "line_end": {
      "type": "integer",
      "description": "Ending line number. Null if file-level or project-wide.",
      "nullable": true
    },
    "snippet": {
      "type": "string",
      "description": "Relevant code snippet (max 10 lines). REQUIRED when line_start is not null — include lines [line_start-1, line_end+1] for context, trim trailing whitespace. Set to '[binary/minified — snippet omitted]' for binary or minified files. May remain null ONLY when file_path is null (project-wide finding).",
      "nullable": true
    },
    "recommendation": {
      "type": "string",
      "description": "Actionable fix or improvement suggestion"
    },
    "effort": {
      "type": "string",
      "enum": ["trivial", "small", "medium", "large", "xl"],
      "description": "Estimated effort to resolve: trivial (<15min), small (<1h), medium (<4h), large (<1d), xl (>1d)"
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Optional tags for grouping: e.g. ['owasp-a01', 'react', 'n-plus-one']",
      "default": []
    },
    "priority_tier": {
      "type": "string",
      "enum": ["immediate", "sprint-1", "sprint-2", "backlog"],
      "description": "Action priority tier assigned during reconciliation per the rules in analysis-dimensions.md. Null before reconciliation."
    },
    "previous_id": {
      "type": ["string", "null"],
      "default": null,
      "description": "Set when a carried-forward finding's code shifted >10 lines, causing a new fingerprint. Links to the old ID for continuity tracking."
    }
  }
}
```

## Dimension Report Schema

Output of a single scan dimension execution.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "DimensionReport",
  "type": "object",
  "required": ["metadata", "summary", "findings"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["date", "dimension", "project_path", "stack", "duration_seconds"],
      "properties": {
        "date": {
          "type": "string",
          "format": "date",
          "description": "ISO 8601 date of the scan"
        },
        "dimension": {
          "type": "string",
          "enum": ["structure", "quality", "security", "testing", "manifest-structure", "skill-quality", "agent-design", "hook-correctness", "marketplace-consistency", "convention-adherence"]
        },
        "project_path": {
          "type": "string",
          "description": "Absolute path to the scanned project root"
        },
        "stack": {
          "type": "object",
          "description": "Detected tech stack",
          "properties": {
            "languages": { "type": "array", "items": { "type": "string" } },
            "frameworks": { "type": "array", "items": { "type": "string" } }
          }
        },
        "duration_seconds": {
          "type": "number",
          "description": "Wall-clock time for this scan dimension"
        }
      }
    },
    "summary": {
      "type": "object",
      "required": ["total_findings", "by_severity"],
      "properties": {
        "total_findings": { "type": "integer" },
        "by_severity": {
          "type": "object",
          "properties": {
            "critical": { "type": "integer", "default": 0 },
            "high": { "type": "integer", "default": 0 },
            "medium": { "type": "integer", "default": 0 },
            "low": { "type": "integer", "default": 0 },
            "info": { "type": "integer", "default": 0 }
          }
        }
      }
    },
    "findings": {
      "type": "array",
      "items": { "$ref": "#Finding" },
      "description": "All findings, ordered by severity (critical first) then by file path"
    },
    "carry_forward_summary": {
      "type": ["object", "null"],
      "default": null,
      "description": "Present when PREVIOUS_FINDINGS was provided to the scanner. Null on first-ever scan.",
      "properties": {
        "carried_forward": { "type": "integer", "description": "Total carried forward (includes unverified)" },
        "resolved": { "type": "integer" },
        "new": { "type": "integer" },
        "unverified": { "type": "integer", "default": 0, "description": "Subset not re-verified (tentative carry-forward)" },
        "resolved_ids": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```
