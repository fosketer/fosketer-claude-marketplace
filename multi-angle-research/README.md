# Multi-Angle Research Plugin

Structured multi-angle research pipeline for Claude Code. Runs a 5-phase workflow — intake, parallel brainstorm, plan, execute, and document — to produce comprehensive research on any topic.

## Installation

Add this plugin to your Claude Code workspace:

```bash
claude plugin add /path/to/local-claude-marketplace/plugins/multi-angle-research
```

Or add to your `.claude/settings.json`:

```json
{
  "plugins": [
    "/path/to/local-claude-marketplace/plugins/multi-angle-research"
  ]
}
```

## Usage

```
/research <topic>
```

Example:

```
/research impact of AI on software engineering hiring practices
```

## Workflow Overview

### Phase 0: Intake & Angle Discovery
- Gathers context: motivation, prior knowledge, desired output
- Adaptive follow-up questions based on your answers
- Generates 2-5 diverse research angles (conventional, cross-disciplinary, decision-focused, etc.)
- You confirm or modify the proposed angles

### Phase 1: Parallel Brainstorming
- Spawns parallel brainstormer agents — one per angle
- Each brainstormer explores its angle in depth (questions, hypotheses, sub-topics)
- Optional quality gate via critic agent (3+ angles)
- Synthesis agent merges findings, identifies convergence/divergence, ranks directions
- You select which direction(s) to pursue

### Phase 2: Plan
- Planner agent creates a detailed research plan (objectives, methodology, tasks)
- You approve before execution begins

### Phase 3: Execute
- Parallel researcher agents gather web sources, data, and evidence
- Analyst agent identifies patterns, contradictions, and key insights

### Phase 4: Document
- Parallel angle-writer agents produce focused briefs (1500-2500 words each)
- Writer agent compiles the final comprehensive report with perspectives compared
- All sources collected in a references file

## Output Structure

```
research-projects/<topic-slug>/
  README.md                        # Project overview and status
  00-intake/
    context.md                     # Your answers and inferred preferences
    angles.md                      # Proposed research angles
  01-brainstorm/
    angle-<label>.md               # Per-angle brainstorm (one per angle)
    critique.md                    # Quality assessment (if 3+ angles)
    synthesis.md                   # Cross-angle synthesis
    selected-directions.md         # Your chosen direction(s)
  02-plan/
    research-plan.md               # Detailed research plan
  03-findings/
    sources.md                     # All sources with attribution
    analysis.md                    # Structured analysis
    data/                          # Raw data files
  04-report/
    report.md                      # Final comprehensive report
    references.md                  # All cited sources
    angle-briefs/
      <label>-brief.md            # Per-angle standalone briefs
```

## Agents

| Agent | Phase | Role |
|-------|-------|------|
| angle-generator | 0 | Proposes diverse research angles |
| brainstormer | 1 | Deep exploration per angle (parallel) |
| critic | 1 | Quality gate for brainstorms (3+ angles) |
| synthesis | 1 | Cross-angle merge and direction ranking |
| planner | 2 | Detailed research plan creation |
| researcher | 3 | Web research execution (parallel) |
| analyst | 3 | Findings analysis and pattern detection |
| angle-writer | 4 | Perspective-specific briefs (parallel) |
| writer | 4 | Final merged report compilation |
