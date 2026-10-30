#!/bin/bash
# tmux status-right segment for pom.py: prints the current phase if pom is running.
# pom rewrites the file every second, so anything older than 5s is a dead timer.
f="$HOME/.cache/pom/status"
[ -f "$f" ] || exit 0
age=$(( $(date +%s) - $(stat -c %Y "$f") ))
[ "$age" -le 5 ] && printf '%s  ' "$(cat "$f")"
