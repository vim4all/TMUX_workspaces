#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ALIASES=(
  "alias dev-claude='bash $SCRIPT_DIR/dev_claude.sh'"
  "alias dev-gemini='bash $SCRIPT_DIR/dev_gemini.sh'"
)

TARGET="${1:-$HOME/.bashrc}"

for alias_line in "${ALIASES[@]}"; do
  if grep -qF "$alias_line" "$TARGET" 2>/dev/null; then
    echo "already in $TARGET: $alias_line"
  else
    echo "$alias_line" >> "$TARGET"
    echo "added to $TARGET: $alias_line"
  fi
done

echo "done — run: source $TARGET"
