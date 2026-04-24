#!/bin/bash
DIR="${1:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Validate directory
if [ ! -d "$DIR" ]; then
  echo "error: directory '$DIR' does not exist" >&2
  exit 1
fi
DIR=$(realpath "$DIR")
SESSION="${2:-$(basename "$DIR")}"

# ── Check required tools
missing=()
for cmd in nvim claude python3; do
  command -v "$cmd" &>/dev/null || missing+=("$cmd")
done
[ -f "$SCRIPT_DIR/pom.py" ] || missing+=("pom.py")
if [ ${#missing[@]} -gt 0 ]; then
  echo "warning: command(s) not found: ${missing[*]}" >&2
fi

# ── Reuse existing session if present
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "session '$SESSION' already exists — attaching"
  if [ -n "$TMUX" ]; then
    tmux switch-client -t "$SESSION"
  else
    tmux attach -t "$SESSION"
  fi
  exit 0
fi

COLS=${COLUMNS:-$(tput cols 2>/dev/null || echo 220)}
ROWS=${LINES:-$(tput lines 2>/dev/null || echo 50)}

# ── Window 1: code
# ┌──────────────────┬───────────┐
# │                  │  claude   │
# │   nvim (~65%)    │  (~35%)   │
# │                  ├───────────┤
# ├──────────────────┤  pom      │
# │  terminal (~30%) │           │
# └──────────────────┴───────────┘
tmux new-session -d -s "$SESSION" -n code -x $COLS -y $ROWS -c "$DIR"
tmux split-window -h -t "$SESSION:code"   -l $(( COLS * 35 / 100 ))  # pane 2 → right
tmux split-window -v -t "$SESSION:code.1" -l $(( ROWS * 30 / 100 ))  # pane 1 → top-left, pane 3 → bottom-left
tmux split-window -v -t "$SESSION:code.3" -l $(( ROWS * 25 / 100 ))  # pane 3 → top, pane 4 → pom (bottom-right)
tmux send-keys -t "$SESSION:code.1" '[ -f Session.vim ] && nvim -S || nvim .' C-m
tmux send-keys -t "$SESSION:code.3" "claude" C-m
tmux send-keys -t "$SESSION:code.4" "python3 '$SCRIPT_DIR/pom.py'" C-m
tmux select-pane -t "$SESSION:code.1"

# ── Window 2: repl
# ┌──────────────────────────────┐
# │  ipython / python3  (~65%)   │
# ├──────────────────────────────┤
# │  shell scratch      (~35%)   │
# └──────────────────────────────┘
tmux new-window -t "$SESSION" -n repl -c "$DIR"
tmux split-window -v -t "$SESSION:repl" -l $(( ROWS * 35 / 100 ))
tmux send-keys -t "$SESSION:repl.1" "ipython 2>/dev/null || python3" C-m

tmux select-window -t "$SESSION:code"
if [ -n "$TMUX" ]; then
  tmux switch-client -t "$SESSION"
else
  tmux attach -t "$SESSION"
fi
