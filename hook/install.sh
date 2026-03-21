#!/usr/bin/env bash
# Install the Prompt Patrol hook for Claude Code
#
# Usage:
#   ./install.sh <SERVER_URL> <API_KEY>
#
# Example:
#   ./install.sh http://localhost:8000 abc123def456...

set -euo pipefail

SERVER_URL="${1:?Usage: ./install.sh <SERVER_URL> <API_KEY>}"
API_KEY="${2:?Usage: ./install.sh <SERVER_URL> <API_KEY>}"

HOOK_DIR="$HOME/.prompt-review"
HOOK_SCRIPT="$HOOK_DIR/prompt_review_hook.py"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "=== Prompt Patrol Hook Installer ==="

# 1. Copy hook script
mkdir -p "$HOOK_DIR"
cp "$(dirname "$0")/prompt_review_hook.py" "$HOOK_SCRIPT"
chmod +x "$HOOK_SCRIPT"
echo "[OK] Hook script installed to $HOOK_SCRIPT"

# 2. Write environment config
cat > "$HOOK_DIR/env.sh" <<EOF
export PROMPT_REVIEW_URL="$SERVER_URL"
export PROMPT_REVIEW_API_KEY="$API_KEY"
EOF
echo "[OK] Environment config written to $HOOK_DIR/env.sh"

# 3. Show instructions for Claude Code settings
echo ""
echo "Add the following to $SETTINGS_FILE:"
echo ""
cat <<'JSONEOF'
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "source ~/.prompt-review/env.sh && python3 ~/.prompt-review/prompt_review_hook.py"
          }
        ]
      }
    ]
  }
}
JSONEOF
echo ""
echo "Or add PROMPT_REVIEW_URL and PROMPT_REVIEW_API_KEY to your shell profile."
echo ""
echo "Done! Prompts will be captured on your next Claude Code session."
