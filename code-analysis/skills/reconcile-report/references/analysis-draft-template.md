# Codebase Analysis Report{{#is_draft}} (DRAFT){{/is_draft}}

**Date**: {{date}}
**Project**: {{project_path}}
**Stack**: {{stack}}
**Dimensions analyzed**: {{dimensions_list}}

---

## Codebase Health Score: {{overall_score}}/10

| Dimension | Score | True Raw | Findings | Crit | High | Med | Low | Info | Est. Iterations (8/10) |
|-----------|-------|----------|----------|------|------|-----|-----|------|------------------------|
{{#dimension_scores}}
| {{dimension}} | {{score}}/10 | {{true_raw}} | {{findings_count}} | {{critical}} | {{high}} | {{medium}} | {{low}} | {{info}} | {{full_quality_iterations}} |
{{/dimension_scores}}

**Deduplication**: {{dedup_merged}} findings merged across dimensions ({{dedup_raw}} raw → {{dedup_final}} unique)

{{#weights_custom}}
**Custom weights applied**: {{weights_description}}
{{/weights_custom}}

---

## Cross-Cutting Observations

{{cross_cutting_observations}}

---

## Ralph-Loop Effort Estimates

| Dimension | True Raw | Score | Quick Win (5/10) | Full Quality (8/10) | Perfect (10/10) |
|-----------|----------|-------|------------------|---------------------|-----------------|
{{#dimension_scores}}
| {{dimension}} | {{true_raw}} | {{score}}/10 | {{quick_win_range}} | {{full_quality_range}} | {{perfect_range}} |
{{/dimension_scores}}

{{#floor_dimensions}}
> **Floor-dimension note**: {{dimension}} scores {{score}}/10 (floor) but has `true_raw={{true_raw}}` — the score hides a penalty of {{true_raw}} vs the cap of 9. Iteration estimates reflect the actual effort needed, not just the displayed score.
{{/floor_dimensions}}

**Recommended ralph-loop order** (sorted by full_quality iterations ascending — fewest iterations first):
{{recommended_ralph_order}}

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
