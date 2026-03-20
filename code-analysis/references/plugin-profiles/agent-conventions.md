# Agent Conventions Reference Profile

Ground truth for agent file location, frontmatter schema, description format, system prompt design, color semantics, and tool access rules. Derived from official `plugin-dev` agent-development skill conventions.

---

## 1. Agent File Locations

Agents live in the `agents/` directory at the plugin root. Two valid file structures are supported:

### Flat file (preferred for simple agents)

```
plugin-name/
└── agents/
    ├── code-reviewer.md
    ├── test-generator.md
    └── security-analyzer.md
```

### Subdirectory format (for agents with supporting files)

```
plugin-name/
└── agents/
    └── code-reviewer/
        └── AGENT.md
```

**Auto-discovery**: All `.md` files in `agents/` are automatically discovered and loaded. For the subdirectory format, the file must be named `AGENT.md`.

**Namespacing**:
- Single plugin, flat file: `agent-name`
- With subdirectories: `plugin:subdir:agent-name`

---

## 2. Agent File Format

Every agent file is a Markdown file with YAML frontmatter followed by the system prompt body.

```markdown
---
name: agent-identifier
description: Use this agent when [triggering conditions]. Examples:

<example>
Context: [Situation description]
user: "[User request]"
assistant: "[How assistant should respond and use this agent]"
<commentary>
[Why this agent should be triggered]
</commentary>
</example>

<example>
[Additional example...]
</example>

model: inherit
color: blue
tools: ["Read", "Write", "Grep"]
---

You are [agent role description]...

**Your Core Responsibilities:**
1. [Responsibility 1]
2. [Responsibility 2]

**Analysis Process:**
[Step-by-step workflow]

**Output Format:**
[What to return]
```

---

## 3. Frontmatter Fields

### 3.1 `name` (required)

Agent identifier used for namespacing and invocation.

**Format**: lowercase letters, numbers, and hyphens only
**Length**: 3–50 characters
**Pattern**: Must start AND end with an alphanumeric character (not a hyphen)

**Valid examples**:
- `code-reviewer`
- `test-generator`
- `api-docs-writer`
- `security-analyzer`
- `api-analyzer-v2`

**Invalid examples**:
- `helper` — acceptable length but too generic (not a format error, but a quality issue)
- `-agent-` — starts and ends with hyphen
- `my_agent` — underscores not allowed
- `ag` — too short (< 3 characters)
- `code reviewer` — space not allowed

**Regex**: `/^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/` (3–50 chars, start/end alphanumeric)

### 3.2 `description` (required)

Defines when Claude should trigger this agent. **This is the most critical field** — it controls automatic triggering.

**Validation rules**:
- Length: 10–5,000 characters
- Must include triggering conditions starting with "Use this agent when..."
- Must include `<example>` blocks (at least one, ideally 2–4)
- Best practice: 200–1,000 characters of prose + 2–4 `<example>` blocks

**Format**:
```
Use this agent when [conditions]. Examples:

<example>
Context: [Scenario description]
user: "[What user says]"
assistant: "[How Claude should respond]"
<commentary>
[Why this agent is appropriate for this case]
</commentary>
</example>

[Additional examples...]
```

**Each `<example>` block must contain**:
1. `Context:` — situation description
2. `user:` — the user's message (quoted)
3. `assistant:` — how Claude should respond (including indicating it will use this agent)
4. `<commentary>...</commentary>` — explanation of why agent triggers

**Best practices for examples**:
- Include 2–4 concrete examples
- Show both proactive and reactive triggering patterns
- Cover different phrasings of the same intent
- Explain reasoning in commentary
- Be specific about when NOT to use the agent

**Example of a compliant description**:
```yaml
description: Use this agent when the user asks to review a pull request, check code quality, or analyze PR changes. Examples:

<example>
Context: User has created a PR and wants quality review
user: "Can you review PR #123 for code quality?"
assistant: "I'll use the pr-quality-reviewer agent to analyze the PR."
<commentary>
PR review request triggers the pr-quality-reviewer agent.
</commentary>
</example>

<example>
Context: After writing a function, a proactive review is warranted
user: "Please write a function that checks if a number is prime"
assistant: "Here is the function: [writes function]. Now let me use the code-reviewer agent to review it."
<commentary>
Code was written and task completed — proactive review is appropriate.
</commentary>
</example>
```

**Non-compliant description examples**:
```yaml
description: Helps with code review tasks.
# Wrong: no triggering conditions, no examples, too vague

description: Use when needed.
# Wrong: no specifics, no examples

description: This is a code review agent that reviews code.
# Wrong: no "Use this agent when...", no examples
```

### 3.3 `model` (required)

Which LLM model the agent should use.

**Valid values**:
- `inherit` — Use same model as parent Claude Code instance (recommended default)
- `sonnet` — Claude Sonnet (balanced capability and speed)
- `opus` — Claude Opus (most capable, most expensive)
- `haiku` — Claude Haiku (fast, cheap, lower capability)

**Recommendation**: Use `inherit` unless the agent specifically requires a model's unique capabilities. Hardcoding a model reduces flexibility and may increase costs.

**When to use specific models**:
- `opus`: Complex reasoning tasks, nuanced judgment, security review
- `haiku`: Simple, deterministic classification tasks where speed matters
- `sonnet`: Moderate complexity tasks with balanced performance requirements

### 3.4 `color` (required)

Visual identifier for the agent in the Claude Code UI.

**Valid values**: `blue`, `cyan`, `green`, `yellow`, `magenta`, `red`

**Color semantics**:

| Color | Semantic Use |
|-------|-------------|
| `blue` | Analysis, review, investigation |
| `cyan` | Analysis (secondary), data processing |
| `green` | Generation, success-oriented tasks, creative building |
| `yellow` | Validation, caution, quality checks |
| `red` | Security, critical operations, high-stakes decisions |
| `magenta` | Creative tasks, documentation generation, transformation |

**Guidelines**:
- Choose distinct colors for different agents within the same plugin
- Use consistent colors for similar agent types across plugins
- Do not give all agents the same color — defeats the visual purpose

### 3.5 `tools` (optional)

Restrict agent to a specific set of tools (principle of least privilege).

**Format**: Array of tool name strings.

```yaml
tools: ["Read", "Write", "Grep"]
```

**Default**: If omitted, agent has access to all tools.

**Common tool sets by purpose**:
- Read-only analysis: `["Read", "Grep", "Glob"]`
- Code generation: `["Read", "Write", "Grep", "Glob"]`
- Testing: `["Read", "Bash", "Grep"]`
- Full access: Omit the field entirely

**Best practice**: Limit tools to the minimum needed. An agent that only reads files should not have `Write` or `Bash` access.

---

## 4. System Prompt Design (Body)

The markdown body below the frontmatter becomes the agent's system prompt. **Write in second person, addressing the agent directly.**

### 4.1 Required Writing Style

- Use second person: "You are...", "You will...", "Your responsibilities..."
- Do NOT use first person: "I am...", "I will..."
- Be specific about responsibilities
- Provide step-by-step process
- Define output format explicitly

### 4.2 System Prompt Length

| Target | Characters |
|--------|-----------|
| Recommended | 500–3,000 characters |
| Minimum | 20 characters |
| Maximum | 10,000 characters |

### 4.3 Standard System Prompt Structure

```markdown
You are [role] specializing in [domain].

**Your Core Responsibilities:**
1. [Primary responsibility]
2. [Secondary responsibility]
3. [Additional responsibilities...]

**Analysis Process:**
1. [Step one]
2. [Step two]
3. [Step three]

**Quality Standards:**
- [Standard 1]
- [Standard 2]

**Output Format:**
Provide results in this format:
- [What to include]
- [How to structure]

**Edge Cases:**
Handle these situations:
- [Edge case 1]: [How to handle]
- [Edge case 2]: [How to handle]
```

### 4.4 System Prompt Best Practices

**DO:**
- Write in second person throughout
- Be specific about responsibilities and scope
- Provide explicit step-by-step process
- Define output format (what to return and how to structure it)
- Include quality standards
- Address edge cases and error handling
- Keep under 10,000 characters

**DON'T:**
- Write in first person ("I am...", "I will...")
- Be vague or generic ("help with tasks")
- Omit process steps (leave agent to figure out approach)
- Leave output format undefined
- Skip quality guidance
- Ignore error cases and edge conditions

---

## 5. Color Semantics Reference

Consistent color usage helps users understand an agent's role at a glance:

```
blue   → Analysis, review, investigation, research
cyan   → Data analysis, processing, transformation
green  → Code generation, building, creation, success paths
yellow → Validation, linting, quality checks, caution
red    → Security review, critical operations, blocking
magenta → Documentation, creative generation, explanation
```

**Example assignments for a code-analysis plugin**:
- `code-reviewer` → `blue` (review/analysis)
- `test-generator` → `green` (generation)
- `security-analyzer` → `red` (security)
- `quality-checker` → `yellow` (validation)
- `docs-writer` → `magenta` (creative/documentation)

---

## 6. AI-Assisted Agent Creation

Use this prompt pattern when generating agents programmatically. This is the exact system prompt used by Claude Code's agent generation feature:

```
Create an agent configuration based on this request: "[USER DESCRIPTION]"

Requirements:
1. Extract core intent and responsibilities
2. Design expert persona for the domain
3. Create comprehensive system prompt with:
   - Clear behavioral boundaries
   - Specific methodologies
   - Edge case handling
   - Output format
4. Create identifier (lowercase, hyphens, 3-50 chars)
5. Write description with triggering conditions
6. Include 2-3 <example> blocks showing when to use

Return JSON with:
{
  "identifier": "agent-name",
  "whenToUse": "Use this agent when... Examples: <example>...</example>",
  "systemPrompt": "You are..."
}
```

Convert JSON output to agent file format with frontmatter after generation.

**Key principles for AI-generated system prompts**:
- Be specific rather than generic
- Include concrete examples where they clarify behavior
- Balance comprehensiveness with clarity — every instruction must add value
- Ensure agent can handle variations of the core task
- Make agent proactive in seeking clarification when needed
- Build in self-correction mechanisms

---

## 7. Validation Checklist

**Frontmatter structure**:
- [ ] `name` field present, 3–50 characters, lowercase/hyphens only
- [ ] `name` starts and ends with alphanumeric character
- [ ] `description` field present, starts with "Use this agent when..."
- [ ] `description` contains at least one `<example>` block
- [ ] Each `<example>` has `Context:`, `user:`, `assistant:`, `<commentary>`
- [ ] `model` field present (`inherit`, `sonnet`, `opus`, or `haiku`)
- [ ] `color` field present (one of: `blue`, `cyan`, `green`, `yellow`, `magenta`, `red`)
- [ ] `tools` field, if present, is an array of valid tool name strings

**System prompt body**:
- [ ] Written in second person ("You are...", "You will...")
- [ ] Not in first person ("I am...", "I will...")
- [ ] Includes clear responsibilities section
- [ ] Includes process/workflow steps
- [ ] Defines output format
- [ ] 20–10,000 characters in length

**Quality**:
- [ ] Agent name is descriptive, not generic (not `helper`, `agent`, `assistant`)
- [ ] Color is appropriate for agent's semantic role
- [ ] Tools are restricted to minimum needed (least privilege)
- [ ] 2–4 examples covering different triggering scenarios
- [ ] Examples include both proactive and reactive patterns if applicable

---

## 8. Common Non-Compliance Patterns

| Issue | Severity | Description |
|-------|----------|-------------|
| Missing `name` field | Critical | Agent invalid, won't load |
| Missing `description` field | Critical | Agent never triggers |
| No `<example>` blocks in description | Major | Poor trigger reliability |
| `model` field absent | Major | Required field missing |
| `color` field absent | Major | Required field missing |
| Invalid color value | Major | Must be one of 6 valid values |
| First-person system prompt | Major | Violates second-person convention |
| Name < 3 characters | Major | Fails length validation |
| Name starts/ends with hyphen | Major | Fails pattern validation |
| Underscore in name | Major | Only hyphens allowed |
| Description has no trigger conditions | Major | Agent description non-functional |
| All agents same color in plugin | Minor | Defeats visual identification purpose |
| Generic name like `helper` | Minor | Not a format error but a quality issue |
| `model: opus` without justification | Minor | Unnecessary cost escalation |
| Overly broad tool access | Minor | Violates least-privilege principle |
