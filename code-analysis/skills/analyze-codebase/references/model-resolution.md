# Model Resolution Algorithm

Resolve which model each pipeline stage uses. Build a `MODEL_MAP` with 4 stage keys: `scanning`, `reconciliation`, `critique`, `planning`.

## Resolution Order

Highest priority wins:

1. `--model` CLI flag
2. Project config: `.code-analysis/config.json` → `models.*`
3. Global config: `~/.claude/code-analysis-config.json` → `models.*`
4. Default: `"inherit"` (omit `model` parameter — agent inherits parent model)

## Resolution Steps

1. Initialize stage keys with smart defaults:
   - `scanning`: `"inherit"` — validated: Sonnet diverges on security dimension (2.0 point gap vs Opus); progressive escalation handles cost optimization instead
   - `reconciliation`: `"inherit"` — cross-dimension reasoning benefits from session model
   - `critique`: `"sonnet"` — checklist validation and formula verification; validated equivalent to Opus
   - `planning`: `"inherit"` — complex dependency analysis benefits from session model
2. If global config exists and contains valid JSON with a `models` key, merge its values (stage-level merge)
3. If project config exists and contains valid JSON with a `models` key, merge its values on top
4. If `--model` flag is present:
   - Tokenize by comma. For each token:
     - If token contains `:` (e.g., `scanning:haiku`): set that stage key
     - If token has no `:` (e.g., `opus`): set ALL 4 stage keys to that value (blanket)
   - Apply blanket values before per-stage values within the same flag
5. Validate all resolved values are in `{haiku, sonnet, opus, inherit}`. If any invalid value found, abort with: `"Invalid model '{value}' for stage '{stage}'. Valid values: haiku, sonnet, opus, inherit"`
6. If a config file exists but contains malformed JSON, abort with: `"Malformed JSON in config file: {path}"`

## Model Quality Floor

Haiku MUST NOT be used as a default for any stage. When `--model haiku` is explicitly
provided by the user, it is honored (user override takes precedence), but the plugin's
own defaults never go below Sonnet.

## MODEL_MAP Structure

Result: `MODEL_MAP = { scanning: "...", reconciliation: "...", critique: "...", planning: "..." }`

Use `MODEL_MAP` at every agent dispatch site. If a stage's value is `"inherit"`, omit the `model` parameter from the Agent tool call (preserving current behavior). Otherwise, pass the resolved model name as the `model` parameter.
