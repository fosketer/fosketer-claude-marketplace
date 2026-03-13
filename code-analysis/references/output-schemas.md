# Output Schemas

> The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

JSON schemas for all structured outputs produced by the code-analysis plugin. All scan skills and plan generators MUST conform to these schemas.

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
      "description": "Unique identifier: {dimension}-{sequential_number}, e.g. 'architecture-003'",
      "pattern": "^[a-z-]+-\\d{3}$"
    },
    "dimension": {
      "type": "string",
      "enum": ["architecture", "quality", "dependencies", "patterns", "testing", "performance", "security", "tech-debt"],
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
      "description": "Relevant code snippet (max 10 lines). Null if not applicable.",
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
          "enum": ["architecture", "quality", "dependencies", "patterns", "testing", "performance", "security", "tech-debt"]
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
    }
  }
}
```

## Refactoring Plan Schema

Output of the plan generator for a single dimension's findings.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RefactoringPlan",
  "type": "object",
  "required": ["metadata", "summary", "priority_matrix", "steps", "risk_assessment"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["date", "dimension", "project_path"],
      "properties": {
        "date": {
          "type": "string",
          "format": "date"
        },
        "dimension": {
          "type": "string",
          "enum": ["architecture", "quality", "dependencies", "patterns", "testing", "performance", "security", "tech-debt"]
        },
        "project_path": {
          "type": "string"
        }
      }
    },
    "summary": {
      "type": "string",
      "description": "Human-readable summary of the refactoring plan (2-4 sentences)"
    },
    "priority_matrix": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["finding_id", "priority", "effort", "impact", "risk"],
        "properties": {
          "finding_id": {
            "type": "string",
            "description": "References a Finding.id"
          },
          "priority": {
            "type": "integer",
            "minimum": 1,
            "description": "Execution priority (1 = highest)"
          },
          "effort": {
            "type": "string",
            "enum": ["trivial", "small", "medium", "large", "xl"]
          },
          "impact": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low"],
            "description": "Expected positive impact of fixing this finding"
          },
          "risk": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Risk of introducing regressions when fixing"
          }
        }
      }
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["order", "title", "description", "files_affected", "verification", "estimated_effort"],
        "properties": {
          "order": {
            "type": "integer",
            "minimum": 1
          },
          "title": {
            "type": "string",
            "maxLength": 100
          },
          "description": {
            "type": "string",
            "description": "Step-by-step instructions for the refactoring"
          },
          "files_affected": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Relative paths from project root"
          },
          "verification": {
            "type": "string",
            "description": "How to verify this step was completed correctly"
          },
          "estimated_effort": {
            "type": "string",
            "enum": ["trivial", "small", "medium", "large", "xl"]
          }
        }
      }
    },
    "risk_assessment": {
      "type": "object",
      "required": ["overall_risk", "mitigation"],
      "properties": {
        "overall_risk": {
          "type": "string",
          "enum": ["high", "medium", "low"]
        },
        "mitigation": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Risk mitigation strategies (e.g. 'Run full test suite after step 3')"
        }
      }
    }
  }
}
```

## Orchestrator Plan Schema

Output of the orchestrator that combines multiple dimension plans into a sequenced execution plan.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "OrchestratorPlan",
  "type": "object",
  "required": ["metadata", "execution_phases", "dependency_graph", "verification_strategy", "total_effort_estimate"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["date", "project_path", "dimensions_analyzed", "stack"],
      "properties": {
        "date": {
          "type": "string",
          "format": "date"
        },
        "project_path": {
          "type": "string"
        },
        "dimensions_analyzed": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Which dimensions were included in this orchestration"
        },
        "stack": {
          "type": "object",
          "properties": {
            "languages": { "type": "array", "items": { "type": "string" } },
            "frameworks": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    },
    "execution_phases": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["phase", "name", "description", "plans", "rationale"],
        "properties": {
          "phase": {
            "type": "integer",
            "minimum": 1
          },
          "name": {
            "type": "string",
            "description": "Phase name, e.g. 'Critical Security Fixes'"
          },
          "description": {
            "type": "string"
          },
          "plans": {
            "type": "array",
            "items": { "type": "string" },
            "description": "References to RefactoringPlan dimensions included in this phase"
          },
          "rationale": {
            "type": "string",
            "description": "Why these plans are grouped and ordered this way"
          }
        }
      }
    },
    "dependency_graph": {
      "type": "object",
      "required": ["mermaid_code"],
      "properties": {
        "mermaid_code": {
          "type": "string",
          "description": "Mermaid diagram showing phase dependencies and execution order"
        }
      }
    },
    "verification_strategy": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["phase", "checks"],
        "properties": {
          "phase": {
            "type": "integer"
          },
          "checks": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Verification steps to run after completing this phase"
          }
        }
      }
    },
    "total_effort_estimate": {
      "type": "string",
      "description": "Human-readable total effort estimate, e.g. '3-5 developer days'"
    }
  }
}
```

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
        "required": ["dimension", "score", "findings_count", "by_severity"],
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
    }
  }
}
```

## Critic Feedback Schema

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
