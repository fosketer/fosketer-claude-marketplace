# Critic Feedback Schema

> Extracted from output-schemas.md. Loaded by report-critic and plan-critic agents.

> schema_version: 0.8.0

Structured feedback produced by report-critic and plan-critic agents.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CriticFeedback",
  "type": "object",
  "required": ["verdict", "target", "iteration", "issues"],
  "properties": {
    "verdict": {
      "type": "string",
      "enum": ["pass", "fail"],
      "description": "Overall verdict — pass means artifact is acceptable"
    },
    "target": {
      "type": "string",
      "enum": ["report", "plan"],
      "description": "Which artifact was reviewed"
    },
    "iteration": {
      "type": "integer",
      "minimum": 1,
      "description": "Which iteration of the feedback loop this is"
    },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["category", "severity", "description", "suggestion"],
        "properties": {
          "category": {
            "type": "string",
            "enum": ["score-calibration", "coverage-gap", "dedup-error", "actionability", "dependency-error", "effort-mismatch", "completeness-gap", "risk-gap", "ordering-error"],
            "description": "Type of issue found"
          },
          "severity": {
            "type": "string",
            "enum": ["blocking", "warning"],
            "description": "blocking = must fix before pass, warning = advisory"
          },
          "description": {
            "type": "string",
            "description": "What is wrong"
          },
          "suggestion": {
            "type": "string",
            "description": "How to fix it"
          },
          "context": {
            "type": "string",
            "description": "Optional: specific finding ID, dimension, or section reference",
            "nullable": true
          }
        }
      }
    }
  }
}
```
