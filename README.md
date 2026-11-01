# tmux-workspaces

Personal tmux session launcher with a built-in Pomodoro timer.

## Setup

Run once to install shell aliases:

```bash
bash ~/.config/tmux_workspaces/init_aliases.sh
source ~/.bashrc
```

## Usage

```bash
dev-claude [-c] [DIR [SESSION]] [-- AI_ARGS]   # full layout, Claude as AI assistant
dev-gemini [-c] [DIR [SESSION]] [-- AI_ARGS]   # full layout, Antigravity CLI (agy) as AI assistant
dev-plain  [DIR [SESSION]]                     # full layout, no AI pane
dev-lite   [-c] [DIR [SESSION]] [-- AI_ARGS]   # just Claude + a shell
```

`DIR` defaults to the current directory. `SESSION` defaults to the folder name (`dev-gemini` appends `_gemini`, `dev-lite` appends `_lite`). If the session already exists, the script attaches to it instead of creating a new one.

- `-c` — continue the most recent conversation (`claude --continue` / `agy --continue`)
- `-- ARGS` — extra arguments passed to the AI CLI, e.g. `dev-lite -- --model opus`
- `-h` — help

## Lite layout (`dev-lite`)

```
┌──────────────────────────────┐
│  claude             (~75%)   │
├──────────────────────────────┤
│  shell              (~25%)   │
└──────────────────────────────┘
```

No git window — open lazygit as a popup with `Alt+g`.

## Full layout

**Window 1 — `code`**

```
┌──────────────────┬───────────┐
│                  │           │
│   nvim (~65%)    │  AI CLI   │
│                  │  (~35%)   │
├──────────────────┤           │
│  terminal (~30%) │           │
└──────────────────┴───────────┘
```

nvim restores `Session.vim` if present, otherwise opens the project directory.

**Window 2 — `repl`**: ipython (falls back to python3) + shell scratch.

## Pomodoro (`pom.py`)

One global timer in the tmux session `pom`, shown in the tmux status bar (via `pom-status.sh`).
`prefix + P` opens it in a popup; `prefix + C-d` hides the popup and the timer keeps running.

| Key | Action |
|-----|--------|
| `↑`/`↓` / `k`/`j` | navigate settings |
| `←`/`→` / `-`/`+` | adjust value |
| `Enter`/`Space` | start |
| `p`/`Space` | pause / resume |
| `n`/`s` | skip to next phase |
| `q` | quit menu (`q` again to confirm) |

CLI flags:

```bash
python3 pom.py -w 25 -s 5 -l 15 -n 4
```
