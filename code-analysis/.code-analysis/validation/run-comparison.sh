#!/bin/bash
set -euo pipefail

PLUGIN_PATH="/Users/keven.foster/document-perso/local-claude-marketplace/code-analysis"
VALIDATION_DIR="$PLUGIN_PATH/.code-analysis/validation"
cd /Users/keven.foster/document-perso

echo "=== Sonnet vs Opus Scanner Validation ==="
echo "Commit: $(cd "$PLUGIN_PATH" && git log -1 --format='%h %s')"
echo ""

# Step 1: Run Opus scan
echo "[1/3] Running Opus scan..."
claude -p "Run /code-analysis:analyze-codebase --plugin --model scanning:opus --draft-only --skip-critics $PLUGIN_PATH" \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep,Agent" > /dev/null 2>&1

cp -r "$PLUGIN_PATH/.code-analysis/scan-reports" "$VALIDATION_DIR/opus-v080"
cp "$PLUGIN_PATH/.code-analysis/reports/"*scores.json "$VALIDATION_DIR/opus-v080-scores.json" 2>/dev/null || true
echo "  -> Opus results saved to $VALIDATION_DIR/opus-v080/"

# Step 2: Run Sonnet scan
echo "[2/3] Running Sonnet scan..."
claude -p "Run /code-analysis:analyze-codebase --plugin --model scanning:sonnet --draft-only --skip-critics $PLUGIN_PATH" \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep,Agent" > /dev/null 2>&1

cp -r "$PLUGIN_PATH/.code-analysis/scan-reports" "$VALIDATION_DIR/sonnet-v080"
cp "$PLUGIN_PATH/.code-analysis/reports/"*scores.json "$VALIDATION_DIR/sonnet-v080-scores.json" 2>/dev/null || true
echo "  -> Sonnet results saved to $VALIDATION_DIR/sonnet-v080/"

# Step 3: Compare
echo ""
echo "[3/3] Comparing results..."
echo ""
python3 "$VALIDATION_DIR/compare-results.py"
