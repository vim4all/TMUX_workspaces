# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Personal tmux environment bootstrap: session-launcher scripts and a self-contained Pomodoro timer (`pom.py`).

## Scripts

All scripts are symlinks to `dev.sh`; behaviour is inferred from the invoked filename.

| Script | Layout | AI assistant | Default session name |
|--------|--------|-------------|----------------------|
| `dev.sh` / `dev_claude.sh` | full | `claude` | `<folder-name>` |
| `dev_gemini.sh` | full | `agy` (Antigravity CLI; the Gemini CLI no longer signs in personal accounts) | `<folder-name>_gemini` |
| `dev_plain.sh` | full | none | `<folder-name>_none` |
| `dev_lite.sh` | lite | `claude` | `<folder-name>_lite` |

```bash
bash dev_claude.sh [-c] [DIR [SESSION]] [-- AI_ARGS...]   # dir defaults to cwd
```

`-c` appends `--continue` to the claude/agy command; args after `--` are shell-quoted and appended to the AI command. If the named session already exists (exact match) the script attaches (or `switch-client` when inside tmux) and exits, ignoring other options. All windows open in the resolved absolute path of `DIR`. Panes are targeted by pane ID, not index.

## Lite layout

Window `claude`: AI CLI (~75%) above a shell (~25%). No git window — lazygit is a tmux popup on `Alt+g`. The session sets `detach-on-destroy on` (overriding the global `off`), so killing it returns to the launching shell instead of switching to another session.

## Full layout (Window 1 — `code`)

```
┌──────────────────┬───────────┐
│                  │           │
│   nvim (~65%)    │  AI CLI   │
│                  │  (~35%)   │
├──────────────────┤           │
│  terminal (~30%) │           │
└──────────────────┴───────────┘
```

`dev_plain.sh` drops the AI pane (nvim above terminal).  
nvim restores `Session.vim` if present in the project directory, otherwise opens `.`.

**Window 2 — `repl`**: ipython (falls back to python3) + shell scratch, both in `DIR`.

**Window 3 — `git`**: lazygit, only inside a git repo. **Window 4 — `openocd`**: only when `run_openocd.sh` exists in `DIR`.

## pom.py

Standalone Python 3 Pomodoro timer — no dependencies beyond stdlib. Not part of the dev layouts: `~/.tmux.conf` binds `prefix + P` to a popup attached to a global `pom` session. `countdown()` writes the phase as a tmux-formatted string to `~/.cache/pom/status` at least once a second (`write_status()`); `pom-status.sh` prints it for `status-right` only if the file is ≤5s old. `main()` removes the file on exit.

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
