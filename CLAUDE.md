# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Personal tmux environment bootstrap: session-launcher scripts and a self-contained Pomodoro timer (`pom.py`).

## Scripts

| Script | AI assistant | Default session name |
|--------|-------------|----------------------|
| `dev_1.sh` | `claude` | `dev_session` |
| `dev_claude.sh` | `claude` | `<folder-name>` |
| `dev_gemini.sh` | `gemini` | `<folder-name>_gemini` |

```bash
bash dev_1.sh [DIR [SESSION]]        # dir defaults to cwd
bash dev_claude.sh [DIR [SESSION]]
bash dev_gemini.sh [DIR [SESSION]]
```

If the named session already exists the script attaches (or `switch-client` when inside tmux) and exits. Both windows open in the resolved absolute path of `DIR`.

## Layout (Window 1 — `code`)

```
┌──────────────────┬───────────┐
│                  │  AI CLI   │
│   nvim (~65%)    │  (~35%)   │
│                  ├───────────┤
├──────────────────┤  pom.py   │
│  terminal (~30%) │  (~25%)   │
└──────────────────┴───────────┘
```

Pane numbering: 1 = nvim, 2 = top-right (AI), 3 = bottom-left (shell), 4 = bottom-right (pom).  
nvim restores `Session.vim` if present in the project directory, otherwise opens `.`.

**Window 2 — `repl`**: ipython (falls back to python3) + shell scratch, both in `DIR`.

## pom.py

Standalone Python 3 Pomodoro timer — no dependencies beyond stdlib. Launched by the session scripts as `python3 '$SCRIPT_DIR/pom.py'`.

**Start screen** (interactive config before the first session):
- `↑`/`↓` or `k`/`j` — move between settings
- `←`/`→` or `-`/`+` — adjust value
- `Enter`/`Space` — start
- `q` — quit

**During a session:**
- `p`/`Space` — pause/resume
- `n`/`s` — skip to next phase
- `q` — open quit menu (second `q` confirms)

CLI flags set the initial values shown on the start screen:

```bash
python3 pom.py -w 25 -s 5 -l 15 -n 4   # 4 sessions, custom durations
```

### pom.py internals

- `read_key()` — puts stdin into raw mode per-call via `termios`/`tty`, reads up to 9 bytes to capture full escape sequences (arrow keys = `\x1b[A/B/C/D`). Uses `os.read(fd, …)` directly to bypass Python's buffered `TextIOWrapper`.
- `countdown()` — tracks `last_state = (remaining, paused, menu_open)` and only redraws when state changes (≈ once/second), not on every poll cycle.
- `render_start()` — uses `HOME + ERASE_DOWN` (not `CLEAR`) to overwrite in-place without flicker.
