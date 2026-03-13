# Codebase Analysis Report{{#is_draft}} (DRAFT){{/is_draft}}

**Date**: {{date}}
**Project**: {{project_path}}
**Stack**: {{stack}}
**Dimensions analyzed**: {{dimensions_list}}

---

## Codebase Health Score: {{overall_score}}/10

| Dimension | Score | Findings | Crit | High | Med | Low | Info |
|-----------|-------|----------|------|------|-----|-----|------|
{{#dimension_scores}}
| {{dimension}} | {{score}}/10 | {{findings_count}} | {{critical}} | {{high}} | {{medium}} | {{low}} | {{info}} |
{{/dimension_scores}}

**Deduplication**: {{dedup_merged}} findings merged across dimensions ({{dedup_raw}} raw → {{dedup_final}} unique)

{{#weights_custom}}
**Custom weights applied**: {{weights_description}}
{{/weights_custom}}

---

## Cross-Cutting Observations

{{cross_cutting_observations}}

---

{{#dimension_sections}}

## {{dimension_name}} ({{score}}/10)

{{summary}}

### Top Findings

{{#top_findings}}
- **{{severity}}** — {{title}} (`{{file_path}}:{{line_start}}`)
  {{recommendation}}

{{/top_findings}}

{{#remaining_count}}
*...and {{remaining_count}} more findings. See per-dimension report for full details.*
{{/remaining_count}}

---

{{/dimension_sections}}

{{#is_draft}}
> **This is a draft report.** It will be finalized after review.
{{/is_draft}}
