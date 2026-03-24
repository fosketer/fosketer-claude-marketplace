# CriticFeedback Output Examples

## Fail Example

```json
{
  "verdict": "fail",
  "target": "report",
  "iteration": 1,
  "issues": [
    {
      "category": "score-calibration",
      "severity": "blocking",
      "description": "Architecture score in scores.json is 2.5, but formula yields 1.0 for the observed finding profile (2 critical, 3 high, 1 medium).",
      "suggestion": "Recompute the structure score using: max(1.0, 10 - min(2*3 + 3*2 + 1*1, 9)) = 1.0",
      "context": "structure dimension"
    },
    {
      "category": "coverage-gap",
      "severity": "warning",
      "description": "Project uses Express.js but security dimension has 0 findings. Expected at least auth/injection findings for an API project.",
      "suggestion": "Re-run scan-security with express-specific rules, or manually verify the security scan output.",
      "context": "security dimension"
    }
  ]
}
```
