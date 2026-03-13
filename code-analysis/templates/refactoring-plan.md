# Refactoring Plan: {{dimension_name}}

**Date**: {{date}}
**Project**: {{project_path}}
**Findings addressed**: {{findings_count}}

---

## Summary

{{summary}}

---

## Priority Matrix

| # | Finding | Priority | Effort | Impact | Risk |
|---|---------|----------|--------|--------|------|
{{#priority_matrix}}
| {{order}} | {{finding_title}} ({{finding_id}}) | {{priority}} | {{effort}} | {{impact}} | {{risk}} |
{{/priority_matrix}}

---

## Steps

{{#steps}}

### Step {{order}}: {{title}}

{{description}}

**Files affected**:
{{#files_affected}}
- `{{.}}`
{{/files_affected}}

**Verification**:
{{verification}}

**Estimated effort**: {{estimated_effort}}

---

{{/steps}}

## Risk Assessment

**Overall risk**: {{overall_risk}}

### Mitigations

{{#mitigations}}
- {{.}}
{{/mitigations}}

---

## Verification Checklist

- [ ] All steps executed in order
- [ ] Each step verified before proceeding
- [ ] No regressions introduced
- [ ] Tests pass after all changes
