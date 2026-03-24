# OrchestratorPlan JSON Skeleton

```json
{
  "metadata": {
    "date": "<today ISO date>",
    "project_path": "<PROJECT_PATH>",
    "dimensions_analyzed": ["<DIMENSIONS_ANALYZED>"],
    "stack": { "languages": [...], "frameworks": [...] }
  },
  "execution_phases": [
    {
      "phase": 1,
      "name": "Quick Wins & Security",
      "description": "Addresses all critical security findings and low-effort improvements.",
      "plans": ["security"],
      "rationale": "Security findings are always urgent and must be addressed first."
    }
  ],
  "dependency_graph": {
    "mermaid_code": "graph TD\n    ..."
  },
  "verification_strategy": [ ... ],
  "total_effort_estimate": "..."
}
```
