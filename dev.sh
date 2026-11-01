#!/bin/bash
# Infer layout + AI command from invocation name — works with symlinks:
#   dev_claude.sh  → full layout, claude
#   dev_gemini.sh  → full layout, agy (Antigravity CLI — replaced the Gemini CLI)
#   dev_plain.sh   → full layout, no AI pane
#   dev_lite.sh    → lite layout: claude + shell (lazygit: Alt+g popup)
#   dev.sh         → full layout, claude (default)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME=$(basename "$0" .sh)   # dev_claude / dev_gemini / dev_plain / dev_lite / dev
_suffix=${NAME#dev_}        # claude / gemini / plain / lite / dev (when called directly)
LAYOUT="full"
case "$_suffix" in
  dev|"") AI_CMD="claude" ;;
  plain|none) AI_CMD="none" ;;
  lite) AI_CMD="claude"; LAYOUT="lite" ;;
  gemini|agy) AI_CMD="agy" ;;
  *) AI_CMD="$_suffix" ;;
esac
# Session-name suffix: keep "_gemini" for the agy workspace so old sessions still match
TAG="$AI_CMD"; [ "$AI_CMD" = "agy" ] && TAG="gemini"

usage() {
  cat <<EOF
usage: ${NAME//_/-} [-c] [DIR [SESSION]] [-- AI_ARGS...]

  DIR        project directory (default: .)
  SESSION    tmux session name (default: folder name)
  -c         continue the most recent AI conversation (claude/agy --continue)
  -- ARGS    extra arguments passed to the AI CLI, e.g. -- --model opus
  -h         show this help

If SESSION already exists it is attached and all other options are ignored.
EOF
}

CONTINUE=0
POS=()
AI_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    -c|--continue) CONTINUE=1 ;;
    -h|--help) usage; exit 0 ;;
    --) shift; AI_ARGS=("$@"); break ;;
    -*) echo "error: unknown option '$1'" >&2; usage >&2; exit 1 ;;
    *) POS+=("$1") ;;
  esac
  shift
done

DIR="${POS[0]:-.}"

if [ ! -d "$DIR" ]; then
  echo "error: directory '$DIR' does not exist" >&2
  exit 1
fi
DIR=$(realpath "$DIR")

if [ -z "${POS[1]:-}" ]; then
  base=$(basename "$DIR" | tr '.:' '_')
  if [ "$LAYOUT" = "lite" ]; then SESSION="${base}_lite"
  elif [ "$AI_CMD" = "claude" ]; then SESSION="$base"
  else SESSION="${base}_${TAG}"
  fi
else
  SESSION="${POS[1]}"
fi

# Build the AI command line (args are shell-quoted for send-keys)
AI_LINE="$AI_CMD"
if [ "$CONTINUE" = 1 ]; then
  case "$AI_CMD" in
    claude|agy) AI_LINE+=" --continue" ;;
    *) echo "warning: -c is only supported for claude and agy — ignored" >&2 ;;
  esac
fi
for a in "${AI_ARGS[@]}"; do AI_LINE+=" $(printf '%q' "$a")"; done

command -v tmux &>/dev/null || { echo "error: tmux not found" >&2; exit 1; }
missing=()
if [ "$LAYOUT" = "full" ]; then
  for cmd in nvim python3; do
    command -v "$cmd" &>/dev/null || missing+=("$cmd")
  done
fi
[ "$AI_CMD" != "none" ] && ! command -v "$AI_CMD" &>/dev/null && missing+=("$AI_CMD")
[ ${#missing[@]} -gt 0 ] && echo "warning: command(s) not found: ${missing[*]}" >&2

attach() {
  if [ -n "$TMUX" ]; then
    tmux switch-client -t "$SESSION"
  else
    tmux attach -t "$SESSION"
  fi
}

# "=" forces an exact name match (otherwise "DCR" would match "DCR_lite")
if tmux has-session -t "=$SESSION" 2>/dev/null; then
  echo "session '$SESSION' already exists — attaching"
  attach
  exit 0
fi

COLS=${COLUMNS:-$(tput cols 2>/dev/null || echo 220)}
ROWS=${LINES:-$(tput lines 2>/dev/null || echo 50)}

IS_GIT=0
git -C "$DIR" rev-parse --is-inside-work-tree &>/dev/null && IS_GIT=1

# ── Lite layout: just the AI CLI and a shell
if [ "$LAYOUT" = "lite" ]; then
  # ┌──────────────────────────────┐
  # │  claude             (~75%)   │
  # ├──────────────────────────────┤
  # │  shell              (~25%)   │
  # └──────────────────────────────┘
  tmux new-session -d -s "$SESSION" -n claude -x $COLS -y $ROWS -c "$DIR"
  # Killing this session drops back to the launching shell, not another session
  tmux set -t "$SESSION" detach-on-destroy on
  PANE_AI=$(tmux display-message -p -t "$SESSION:claude" '#{pane_id}')
  tmux split-window -v -t "$PANE_AI" -l $(( ROWS * 25 / 100 )) -c "$DIR"
  tmux send-keys -t "$PANE_AI" "$AI_LINE" C-m
  tmux select-pane -t "$PANE_AI"
  # No git window: lazygit is a popup on Alt+g (see ~/.tmux.conf)
  attach
  exit 0
fi

# ── Window 1: code
if [ "$AI_CMD" = "none" ]; then
  # ┌──────────────────────────────┐
  # │                              │
  # │   nvim (~70%)                │
  # │                              │
  # ├──────────────────────────────┤
  # │  terminal (~30%)             │
  # └──────────────────────────────┘
  tmux new-session -d -s "$SESSION" -n code -x $COLS -y $ROWS -c "$DIR"
  PANE_NVIM=$(tmux display-message -p -t "$SESSION:code" '#{pane_id}')
  tmux split-window -v -t "$PANE_NVIM" -l $(( ROWS * 30 / 100 )) -c "$DIR"
else
  # ┌──────────────────┬───────────┐
  # │                  │           │
  # │   nvim (~65%)    │  AI CLI   │
  # │                  │  (~35%)   │
  # ├──────────────────┤           │
  # │  terminal (~30%) │           │
  # └──────────────────┴───────────┘
  tmux new-session -d -s "$SESSION" -n code -x $COLS -y $ROWS -c "$DIR"
  PANE_NVIM=$(tmux display-message -p -t "$SESSION:code" '#{pane_id}')
  PANE_AI=$(tmux split-window   -h -t "$PANE_NVIM" -l $(( COLS * 35 / 100 )) -c "$DIR" -P -F '#{pane_id}')
  tmux split-window -v -t "$PANE_NVIM" -l $(( ROWS * 30 / 100 )) -c "$DIR"
  tmux send-keys -t "$PANE_AI"  "$AI_LINE" C-m
fi
# Pomodoro lives in the tmux status bar: prefix + P opens it (see ~/.tmux.conf)
tmux send-keys -t "$PANE_NVIM" '[ -f Session.vim ] && nvim -S || nvim .' C-m
tmux select-pane -t "$PANE_NVIM"

# ── Window 2: repl
# ┌──────────────────────────────┐
# │  ipython / python3  (~65%)   │
# ├──────────────────────────────┤
# │  shell scratch      (~35%)   │
# └──────────────────────────────┘
tmux new-window -d -t "$SESSION" -n repl -c "$DIR"
PANE_REPL=$(tmux display-message -p -t "$SESSION:repl" '#{pane_id}')
tmux split-window -v -t "$PANE_REPL" -l $(( ROWS * 35 / 100 )) -c "$DIR"
tmux send-keys -t "$PANE_REPL" "command -v ipython >/dev/null && ipython || python3" C-m

# ── Window 3: git (only inside a git repo)
if [ "$IS_GIT" = 1 ]; then
  tmux new-window -d -t "$SESSION" -n git -c "$DIR"
  tmux send-keys -t "$SESSION:git" "lazygit 2>/dev/null || git status" C-m
fi

# ── Window 4: openocd (only when run_openocd.sh exists in project dir)
# ┌──────────────────────────────┐
# │  OpenOCD server     (~65%)   │
# ├──────────────────────────────┤
# │  flash / gdb shell  (~35%)   │
# └──────────────────────────────┘
if [[ -f "$DIR/run_openocd.sh" ]]; then
  tmux new-window -d -t "$SESSION" -n openocd -c "$DIR"
  PANE_OCD=$(tmux display-message -p -t "$SESSION:openocd" '#{pane_id}')
  tmux split-window -v -t "$PANE_OCD" -l $(( ROWS * 35 / 100 )) -c "$DIR"
  tmux send-keys -t "$PANE_OCD" "bash run_openocd.sh" C-m
fi

tmux select-window -t "$SESSION:code"
attach
