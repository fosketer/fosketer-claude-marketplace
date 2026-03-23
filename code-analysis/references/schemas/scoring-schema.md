# Scoring Schemas

> Extracted from output-schemas.md for role-specific loading.

> schema_version: 0.8.0

## Scoring Formula

`raw = 3×critical + 2×high + 1×medium + 0.5×low`

`score = max(1.0, 10 - min(raw, 9))`

Info-severity findings are excluded from scoring.

## Scores Report Schema

Machine-readable scores produced by the reconciliation agent. Enables tracking health over time.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ScoresReport",
  "type": "object",
  "required": ["metadata", "dimension_scores", "overall_score", "dedup_stats"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["date", "project_path", "dimensions_analyzed", "stack"],
      "properties": {
        "date": { "type": "string", "format": "date" },
        "project_path": { "type": "string" },
        "dimensions_analyzed": { "type": "array", "items": { "type": "string" } },
        "stack": {
          "type": "object",
          "properties": {
            "languages": { "type": "array", "items": { "type": "string" } },
            "frameworks": { "type": "array", "items": { "type": "string" } }
          }
        },
        "weights": {
          "type": "object",
          "description": "Dimension weights used for overall score calculation",
          "additionalProperties": { "type": "number" }
        }
      }
    },
    "dimension_scores": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["dimension", "score", "findings_count", "by_severity", "by_effort", "iteration_estimates"],
        "properties": {
          "dimension": { "type": "string" },
          "score": { "type": "number", "minimum": 0, "maximum": 10 },
          "findings_count": { "type": "integer" },
          "by_severity": {
            "type": "object",
            "properties": {
              "critical": { "type": "integer", "default": 0 },
              "high": { "type": "integer", "default": 0 },
              "medium": { "type": "integer", "default": 0 },
              "low": { "type": "integer", "default": 0 },
              "info": { "type": "integer", "default": 0 }
            }
          },
          "by_effort": {
            "type": "object",
            "description": "Count of scoreable findings (excluding info) by effort level",
            "properties": {
              "trivial": { "type": "integer", "default": 0 },
              "small": { "type": "integer", "default": 0 },
              "medium": { "type": "integer", "default": 0 },
              "large": { "type": "integer", "default": 0 },
              "xl": { "type": "integer", "default": 0 }
            }
          },
          "iteration_estimates": {
            "type": "object",
            "description": "Ralph-loop iteration estimates for reaching target scores",
            "required": ["true_raw", "quick_win", "full_quality", "perfect"],
            "properties": {
              "true_raw": {
                "type": "number",
                "minimum": 0,
                "description": "Unclipped penalty: 3×crit + 2×high + 1×med + 0.5×low. Unlike score (which floors at 1.0), true_raw reveals actual penalty magnitude."
              },
              "quick_win": { "$ref": "#IterationTarget", "description": "Estimate to reach 5/10" },
              "full_quality": { "$ref": "#IterationTarget", "description": "Estimate to reach 8/10" },
              "perfect": { "$ref": "#IterationTarget", "description": "Estimate to reach 10/10" }
            }
          }
        }
      }
    },
    "overall_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 10,
      "description": "Weighted average of dimension scores"
    },
    "dedup_stats": {
      "type": "object",
      "required": ["total_raw_findings", "total_after_dedup", "merged_count"],
      "properties": {
        "total_raw_findings": { "type": "integer", "description": "Sum of findings across all dimensions before dedup" },
        "total_after_dedup": { "type": "integer", "description": "Findings count after cross-dimension dedup" },
        "merged_count": { "type": "integer", "description": "Number of findings merged during dedup" }
      }
    },
    "scan_metadata": {
      "type": ["object", "null"],
      "default": null,
      "description": "Aggregated carry-forward statistics across dimensions.",
      "properties": {
        "carry_forward_stats": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "carried_forward": { "type": "integer" },
              "resolved": { "type": "integer" },
              "new": { "type": "integer" }
            }
          }
        }
      }
    }
  }
}
```

## IterationTarget Schema

Sub-schema for ralph-loop iteration estimates within each dimension score entry.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "IterationTarget",
  "type": "object",
  "required": ["target_score", "estimated_iterations", "range"],
  "properties": {
    "target_score": {
      "type": "number",
      "enum": [5, 8, 10],
      "description": "Target dimension score"
    },
    "estimated_iterations": {
      "type": "integer",
      "minimum": 0,
      "description": "Estimated ralph-loop iterations to reach target. 0 if already at or above target."
    },
    "range": {
      "type": "array",
      "items": { "type": "integer", "minimum": 0 },
      "minItems": 2,
      "maxItems": 2,
      "description": "Uncertainty range [low, high]. [0, 0] if already at target."
    }
  }
}
```

## Run Delta Schema

Output of Step 4d in reconciliation. Produced when PREVIOUS_SCORES is available.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RunDelta",
  "type": "object",
  "required": ["previous_date", "new_finding_ids", "resolved_finding_ids", "unchanged_count", "score_deltas"],
  "properties": {
    "previous_date": {
      "type": "string",
      "format": "date",
      "description": "Date of the previous scan run"
    },
    "new_finding_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Finding IDs present in current run but not in previous"
    },
    "resolved_finding_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Finding IDs present in previous run but not in current"
    },
    "unchanged_count": {
      "type": "integer",
      "description": "Count of findings present in both runs"
    },
    "score_deltas": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["dimension", "previous_score", "current_score", "delta"],
        "properties": {
          "dimension": { "type": "string" },
          "previous_score": { "type": "number" },
          "current_score": { "type": "number" },
          "delta": { "type": "number", "description": "current_score - previous_score" }
        }
      }
    }
  }
}
```
