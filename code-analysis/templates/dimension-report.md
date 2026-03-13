# {{dimension_name}} Analysis Report

**Date**: {{date}}
**Project**: {{project_path}}
**Stack**: {{stack}}
**Duration**: {{duration_seconds}}s

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | {{critical_count}} |
| High     | {{high_count}} |
| Medium   | {{medium_count}} |
| Low      | {{low_count}} |
| Info     | {{info_count}} |
| **Total** | **{{total_count}}** |

---

## Findings

{{#findings}}

### {{id}}: {{title}}

- **Severity**: {{severity}}
- **File**: `{{file_path}}:{{line_start}}`
- **Effort**: {{effort}}
- **Tags**: {{tags}}

{{description}}

{{#snippet}}
```{{language}}
{{snippet}}
```
{{/snippet}}

**Recommendation**: {{recommendation}}

---

{{/findings}}

## Dimension-Specific Notes

{{notes}}
