# Reconciler Schemas

> Extracted from output-schemas.md. Loaded by report-reconciler agent only.

> schema_version: 0.8.0

## Cross-Analysis Schema

Output of the deep cross-dimension analysis (Stage 6). Produced by the report-reconciler agent when re-dispatched with `--deep`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CrossAnalysis",
  "type": "object",
  "required": ["metadata", "root_causes", "systemic_patterns", "combined_fixes"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["date", "project_path", "dimensions_analyzed"],
      "properties": {
        "date": { "type": "string", "format": "date" },
        "project_path": { "type": "string" },
        "dimensions_analyzed": { "type": "array", "items": { "type": "string" } }
      }
    },
    "root_causes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "description", "affected_dimensions", "related_finding_ids"],
        "properties": {
          "id": { "type": "string", "pattern": "^rc-\\d{3}$" },
          "title": { "type": "string", "maxLength": 100 },
          "description": { "type": "string" },
          "affected_dimensions": { "type": "array", "items": { "type": "string" } },
          "related_finding_ids": { "type": "array", "items": { "type": "string" } }
        }
      },
      "description": "Findings across dimensions that share a common root cause"
    },
    "systemic_patterns": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "description", "evidence"],
        "properties": {
          "title": { "type": "string" },
          "description": { "type": "string" },
          "evidence": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Finding IDs or file paths that support this pattern"
          }
        }
      },
      "description": "High-level systemic issues (e.g., lack of abstraction layer)"
    },
    "combined_fixes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "description", "addresses_root_causes", "estimated_effort"],
        "properties": {
          "title": { "type": "string" },
          "description": { "type": "string" },
          "addresses_root_causes": { "type": "array", "items": { "type": "string" }, "description": "Root cause IDs this fix addresses" },
          "estimated_effort": { "type": "string", "enum": ["trivial", "small", "medium", "large", "xl"] }
        }
      },
      "description": "Suggested fixes that address multiple dimensions simultaneously"
    }
  }
}
```

## Root Cause Cluster Schema

Output of Step 4b in reconciliation. One entry per hot module (file appearing in ≥ 3 findings across ≥ 2 dimensions).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RootCauseCluster",
  "type": "object",
  "required": ["cluster_id", "file_path", "finding_ids", "dimension_count", "aggregate_effort", "summary"],
  "properties": {
    "cluster_id": {
      "type": "string",
      "pattern": "^C\\d+$",
      "description": "Short cluster identifier, e.g. 'C1', 'C2'"
    },
    "file_path": {
      "type": "string",
      "description": "Relative path to the hot module"
    },
    "finding_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "IDs of all findings touching this module"
    },
    "dimension_count": {
      "type": "integer",
      "minimum": 2,
      "description": "Number of distinct dimensions with findings in this module"
    },
    "aggregate_effort": {
      "type": "string",
      "enum": ["trivial", "small", "medium", "large", "xl"],
      "description": "Largest individual effort in the cluster"
    },
    "summary": {
      "type": "string",
      "description": "One-sentence remediation recommendation for this hot module"
    }
  }
}
```

## Override File Schema

User-managed file at `.code-analysis/overrides.json`. Controls which findings are suppressed or deprioritized.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "OverrideFile",
  "type": "object",
  "properties": {
    "false_positives": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Finding IDs to exclude entirely from report and score",
      "default": []
    },
    "wont_fix": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Finding IDs to keep in report with [WONT-FIX] tag but exclude from score",
      "default": []
    },
    "notes": {
      "type": "object",
      "additionalProperties": { "type": "string" },
      "description": "Human-readable justification per finding ID",
      "default": {}
    }
  }
}
```

**Example**:
```json
{
  "false_positives": ["sec-010"],
  "wont_fix": ["qual-007"],
  "notes": {
    "sec-010": "IDOR risk accepted — job IDs are UUIDs in prod, not sequential",
    "qual-007": "Intentional casing — matches external enum spec"
  }
}
```
