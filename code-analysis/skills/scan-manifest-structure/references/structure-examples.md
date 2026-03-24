# Plugin Directory Structure Examples

## Acceptable Structures

```text
# Standard plugin with skills and agents
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── my-skill/
│       └── SKILL.md
├── agents/
│   └── my-agent.md
├── references/
└── README.md

# Hooks-only plugin (no skills or agents required — see Step 4 exception)
git-hooks-plugin/
├── .claude-plugin/
│   └── plugin.json
├── hooks/
│   ├── pre-commit.sh
│   └── post-checkout.sh
└── README.md

# Plugin bundling an MCP server
mcp-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── query-data/
│       └── SKILL.md
├── mcp-servers/
│   └── server.py
└── README.md
```

## Unacceptable Structures (emit findings)

```text
# BAD: .claude-plugin nested inside a subdirectory
my-plugin/
├── src/
│   └── .claude-plugin/    # WRONG — must be at PROJECT_PATH root
│       └── plugin.json
└── README.md

# BAD: Mixed flat files instead of organized directories
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── skill-one.md           # WRONG — skills must be in skills/<name>/SKILL.md
├── skill-two.md
└── README.md
```
