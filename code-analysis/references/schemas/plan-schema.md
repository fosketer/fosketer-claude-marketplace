# Plan Schemas

> Extracted from output-schemas.md. Loaded by refactoring-planner agent only.

> schema_version: 0.8.0

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
