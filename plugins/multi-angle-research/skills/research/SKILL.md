---
name: research
description: Brainstorm, plan, execute, and document a research project on any topic. Starts with structured intake, spawns parallel angle-specific brainstormers, and produces both angle-specific briefs and a merged final report.
allowed-tools: Agent, Read, Write, Bash, WebSearch, WebFetch, Glob, Grep, AskUserQuestion
---

# Research Planning & Execution Skill

You are orchestrating a structured, multi-angle research workflow. The user wants to research: **$ARGUMENTS**

## Setup

1. Create a slug from the topic (lowercase, hyphens, max 50 chars)
2. Create the project directory structure:

```
research-projects/<topic-slug>/
  00-intake/
  01-brainstorm/
  02-plan/
  03-findings/
    data/
  04-report/
    angle-briefs/
  README.md
```

3. Write an initial `README.md` with the topic, date, and status "In Progress"

---

## Phase 0: Intake & Angle Discovery

### Step 0.1 — Core Intake

Use AskUserQuestion to ask the user these 3 questions (in a single prompt):

> I'd like to understand your research needs before diving in. Please answer these questions:
>
> 1. **Context & motivation**: What prompted this research? What situation is driving this need?
> 2. **Prior knowledge**: What do you already know about this topic? What have you explored or ruled out?
> 3. **Desired output**: What will you use the research for? (Decision-making, presentation, implementation, learning, something else?)

### Step 0.2 — Adaptive Follow-up

Read the user's Round 1 answers. Based on what they revealed, select 1-2 follow-up questions from this pool:

| If Round 1 reveals... | Follow-up question |
|---|---|
| Decision-making context | "What are the key criteria for your decision? Any dealbreakers?" |
| Implementation intent | "What constraints exist? (Budget, timeline, tech stack, team size...)" |
| Vague/broad topic | "Can you narrow the scope? What specific aspect matters most?" |
| Deep existing knowledge | "What gaps remain? What would change your current thinking?" |
| Learning/exploration intent | "Prefer broad coverage of many angles, or deep investigation of fewer?" |
| Organizational context mentioned | "Who is the audience? What level of detail do they need?" |

If Round 1 answers are already rich and specific, you may skip this step.

Use AskUserQuestion to ask the selected follow-up(s).

### Step 0.3 — Save Intake Context

Write ALL intake answers to `00-intake/context.md` with this structure:

```markdown
# Research Intake: <Topic>
Date: <date>

## Context & Motivation
<user's answer>

## Prior Knowledge
<user's answer>

## Desired Output
<user's answer>

## Additional Context
<follow-up answers, if any>

## Inferred Preferences
- Depth vs breadth: <inferred from answers>
- Angle count: <recommended number based on answers>
- Key constraints: <summarized>
```

### Step 0.4 — Generate Angles

Spawn an **angle-generator** agent:
> Research topic: "$ARGUMENTS"
> Intake context file: research-projects/<topic-slug>/00-intake/context.md
> Output file: research-projects/<topic-slug>/00-intake/angles.md
>
> Read the intake context, then propose distinct research angles for this topic. Follow your diversity heuristics and adapt the angle count to the user's depth/breadth preference.

### Step 0.5 — User Confirms Angles

Read the generated `angles.md`. Present the proposed angles to the user with AskUserQuestion:

> Based on your context, I've identified these research angles:
>
> [List each angle with its name and 1-sentence description]
>
> Would you like to:
> - **Proceed** with these angles as-is
> - **Modify** any angles (add, remove, or adjust)
> - **Change the number** of angles (currently N)

Apply any user modifications to `angles.md` before proceeding.

---

## Phase 1: Parallel Brainstorming

### Step 1.1 — Parallel Brainstormers

Read the confirmed angles from `00-intake/angles.md`. For EACH angle, spawn a **brainstormer** agent **in parallel**:

> Research topic: "$ARGUMENTS"
> Assigned angle: <angle-label> — <angle-name>
> Angle description: <angle-description>
> Angle position: Angle <N> of <M>
> Intake context file: research-projects/<topic-slug>/00-intake/context.md
> Output file: research-projects/<topic-slug>/01-brainstorm/angle-<angle-label>.md
>
> Read the intake context, then brainstorm in depth from your assigned angle. Stay focused on YOUR angle — other brainstormers are covering other perspectives. Connect ideas back to the user's stated motivation and constraints.

Launch ALL brainstormer agents simultaneously.

### Step 1.2 — Critique (Optional Quality Gate)

If there are 3 or more angles, spawn a **critic** agent after all brainstormers complete:

> Research topic: "$ARGUMENTS"
> Intake context: research-projects/<topic-slug>/00-intake/context.md
> Angle definitions: research-projects/<topic-slug>/00-intake/angles.md
> Brainstorm directory: research-projects/<topic-slug>/01-brainstorm/
> Output file: research-projects/<topic-slug>/01-brainstorm/critique.md
>
> Read the intake context, angle definitions, and all angle brainstorm files. Evaluate each brainstorm for depth, relevance to its assigned angle, coverage, and differentiation from other angles.

Skip this step if there are only 2 angles (low-complexity research).

### Step 1.3 — Synthesis

After brainstormers (and optionally critic) complete, spawn a **synthesis** agent:

> Research topic: "$ARGUMENTS"
> Intake context: research-projects/<topic-slug>/00-intake/context.md
> Brainstorm directory: research-projects/<topic-slug>/01-brainstorm/
> Output file: research-projects/<topic-slug>/01-brainstorm/synthesis.md
>
> Read the intake context, all angle brainstorm files, and the critique (if it exists). Merge findings into a cross-angle synthesis with convergence, divergence, evaluation matrix, and ranked recommended directions.

### Step 1.4 — Select Direction(s)

Read `synthesis.md`. Present the top recommended directions to the user using AskUserQuestion:

> Here's what emerged from the multi-angle brainstorm:
>
> **Convergence**: [key themes appearing across angles]
>
> **Top Recommended Directions**:
> [List each direction with source angles and brief description]
>
> Which direction(s) would you like to pursue? You can select one or combine elements from multiple directions.

Save the user's selection to `01-brainstorm/selected-directions.md`.

---

## Phase 2: Plan

### Step 2.1 — Create Research Plan

Spawn a **planner** agent:
> Research topic: "$ARGUMENTS"
> Selected direction(s): [read from selected-directions.md]
> Intake context: research-projects/<topic-slug>/00-intake/context.md
> Read the brainstorm context from: research-projects/<topic-slug>/01-brainstorm/
> Output file: research-projects/<topic-slug>/02-plan/research-plan.md
>
> Read the intake context to understand the user's motivation and constraints. Create a detailed research plan including:
> - Research objectives (3-5 clear objectives)
> - Methodology (how each objective will be investigated)
> - Scope and boundaries (what's in and out of scope)
> - Key questions to answer
> - Expected deliverables
> - Research tasks breakdown (numbered list of concrete tasks)

### Step 2.2 — User Approval

Present the research plan to the user using AskUserQuestion. Ask if they want to proceed, modify the plan, or adjust scope. Do not continue to Phase 3 until the user approves.

---

## Phase 3: Execute

### Step 3.1 — Research

Read the research plan and identify the concrete research tasks. For each task (or group of related tasks), spawn a **researcher** agent:
> Research task: [specific task from the plan]
> Project directory: research-projects/<topic-slug>/03-findings/
> Write sources and findings to: research-projects/<topic-slug>/03-findings/sources.md (append)
> Save any data to: research-projects/<topic-slug>/03-findings/data/
>
> Execute this research task. Search the web, gather information, and document your findings with proper source attribution. Include URLs and dates for all sources.

Launch multiple researcher agents in parallel when tasks are independent.

### Step 3.2 — Analyze

After all researcher agents complete, spawn an **analyst** agent:
> Research topic: "$ARGUMENTS"
> Read all findings from: research-projects/<topic-slug>/03-findings/
> Read the research plan from: research-projects/<topic-slug>/02-plan/research-plan.md
> Output file: research-projects/<topic-slug>/03-findings/analysis.md
>
> Analyze all gathered findings. Identify patterns, contradictions, key insights, and gaps. Map findings back to the research objectives. Provide a structured analysis that will serve as the foundation for the final report.

---

## Phase 4: Document

### Step 4.1 — Angle-Specific Briefs

Read the selected directions from `01-brainstorm/selected-directions.md`. For each selected angle, spawn an **angle-writer** agent **in parallel**:

> Research topic: "$ARGUMENTS"
> Assigned angle: <angle-label> — <angle-name>
> Angle description: <angle-description>
> Intake context: research-projects/<topic-slug>/00-intake/context.md
> Angle brainstorm: research-projects/<topic-slug>/01-brainstorm/angle-<angle-label>.md
> Findings directory: research-projects/<topic-slug>/03-findings/
> Analysis: research-projects/<topic-slug>/03-findings/analysis.md
> Output file: research-projects/<topic-slug>/04-report/angle-briefs/<angle-label>-brief.md
>
> Write a focused 1500-2500 word brief from this angle's perspective. Include strengths, blind spots, and angle-specific recommendations.

Launch ALL angle-writer agents simultaneously.

### Step 4.2 — Final Report

After angle briefs are complete, spawn a **writer** agent:
> Research topic: "$ARGUMENTS"
> Read ALL project files from: research-projects/<topic-slug>/
> Angle briefs directory: research-projects/<topic-slug>/04-report/angle-briefs/
> Output file: research-projects/<topic-slug>/04-report/report.md
> References file: research-projects/<topic-slug>/04-report/references.md
>
> Write a comprehensive research report. Include the "Perspectives Compared" section that summarizes how different angles contributed different insights. Reference the angle-specific briefs. Also create a references.md with all sources cited.

### Step 4.3 — Finalize

Update the project `README.md` with:
- Final status: "Completed"
- Summary of findings
- Research angles used
- Links to all project files (including angle briefs)
- Date completed

Present the final report location to the user and offer to make any revisions. Mention that angle-specific briefs are available for deeper perspective on each research angle.
