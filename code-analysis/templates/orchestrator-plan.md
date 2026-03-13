# Orchestrator Refactoring Plan

**Date**: {{date}}
**Project**: {{project_path}}
**Dimensions analyzed**: {{dimensions_list}}
**Stack**: {{stack}}

---

## Executive Summary

{{executive_summary}}

---

## Execution Phases

{{#phases}}

### Phase {{phase}}: {{name}}

{{description}}

**Plans included**:
{{#plans}}
- `{{dimension}}` — {{summary}} ({{findings_count}} findings, effort: {{effort}})
{{/plans}}

**Rationale**: {{rationale}}

**Verification**:
{{#checks}}
- [ ] {{.}}
{{/checks}}

---

{{/phases}}

## Dependency Graph

```mermaid
{{mermaid_code}}
```

## Effort Summary

| Phase | Dimension | Findings | Effort |
|-------|-----------|----------|--------|
{{#effort_rows}}
| {{phase}} | {{dimension}} | {{findings_count}} | {{effort}} |
{{/effort_rows}}
| **Total** | | **{{total_findings}}** | **{{total_effort}}** |

---

## Verification Strategy

{{#verification_phases}}

### Phase {{phase}} Verification

{{#checks}}
- [ ] {{.}}
{{/checks}}

{{/verification_phases}}

## Next Steps

1. Review this plan with the team
2. Execute phases in order — do NOT skip ahead
3. Verify each phase before proceeding to the next
4. Re-run analysis after completion to measure improvement
