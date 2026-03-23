# Iteration Estimation Algorithm

Estimate how many ralph-loop iterations each dimension needs to reach three target scores. Run this after computing the dimension score in Step 2.

## 2b.1 — Aggregate Findings by Effort

For each dimension, count scoreable findings (severity != `info`, excluding `wont_fix`) by effort level:
```
by_effort = { trivial: 0, small: 0, medium: 0, large: 0, xl: 0 }
```
Count each finding's `effort` field into the corresponding bucket.

## 2b.2 — Compute true_raw

```
true_raw = 3 × criticals + 2 × highs + 1 × mediums + 0.5 × lows
```

This is the **unclipped** penalty — it is NOT capped at 9 like the score formula. `true_raw` reveals the actual penalty magnitude: two dimensions both scoring 1.0 may have `true_raw` of 9 vs 50, requiring very different effort.

## 2b.3 — Compute Iteration Estimates for Each Target

Three targets: `quick_win` (5/10), `full_quality` (8/10), `perfect` (10/10).

For each target:
```
target_raw = 10 - target_score           # e.g., 10 - 8 = 2
raw_to_remove = max(0, true_raw - target_raw)

# If dimension already at or above target, estimated = 0
if raw_to_remove == 0:
    estimated = 0
    range = [0, 0]
else:
    # Effort cost: how many "iteration slots" each effort level consumes
    EFFORT_COST = { trivial: 0.20, small: 0.25, medium: 0.40, large: 0.67, xl: 1.00 }

    scoreable_findings = sum(by_effort.values())
    total_cost = sum(by_effort[level] × EFFORT_COST[level] for level in EFFORT_COST)
    findings_per_iter = scoreable_findings / total_cost
    avg_penalty = true_raw / scoreable_findings
    raw_per_iter = findings_per_iter × avg_penalty

    estimated = ceil(1.4 × raw_to_remove / raw_per_iter)
    estimated = max(1, min(estimated, scoreable_findings))
    range = [max(1, estimated - 1), estimated + 1]
```

**Edge cases**:
- If `scoreable_findings == 0`: all estimates are 0 (nothing to fix)
- If dimension already at or above target score: `estimated = 0`, `range = [0, 0]`

## 2b.4 — Store Results

Attach to each dimension score entry:
```json
{
  "by_effort": { "trivial": 2, "small": 3, "medium": 1, "large": 0, "xl": 0 },
  "iteration_estimates": {
    "true_raw": 12.5,
    "quick_win":    { "target_score": 5,  "estimated_iterations": 3, "range": [2, 4] },
    "full_quality": { "target_score": 8,  "estimated_iterations": 5, "range": [4, 6] },
    "perfect":      { "target_score": 10, "estimated_iterations": 7, "range": [6, 8] }
  }
}
```
