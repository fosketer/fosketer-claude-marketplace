> **DEPRECATED (v0.8.0):** This file is kept for human reference only. Agents MUST load
> role-specific fragments from `references/schemas/` instead. See:
> - `finding-schema.md` — scanners, reconciler
> - `scoring-schema.md` — scanners, reconciler
> - `reconciler-schema.md` — reconciler only
> - `critic-schema.md` — report-critic, plan-critic
> - `plan-schema.md` — refactoring-planner only

# Output Schemas

> schema_version: 0.8.0 — token optimization (split role-specific schemas, inline scoring, skip-clean dimensions); still reflects 8→4 dimension consolidation

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
          "enum": ["structure", "quality", "security", "testing", "manifest-structure", "skill-quality", "agent-design", "hook-correctness", "marketplace-consistency", "convention-adherence"]
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
