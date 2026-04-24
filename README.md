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
dev-claude [DIR [SESSION]]   # Claude as AI assistant
dev-gemini [DIR [SESSION]]   # Gemini as AI assistant
```

`DIR` defaults to the current directory. `SESSION` defaults to the folder name (`dev-gemini` appends `_gemini`). If the session already exists, the script attaches to it instead of creating a new one.

## Layout

**Window 1 — `code`**

```
┌──────────────────┬───────────┐
│                  │  AI CLI   │
│   nvim (~65%)    │  (~35%)   │
│                  ├───────────┤
├──────────────────┤  pom.py   │
│  terminal (~30%) │  (~25%)   │
└──────────────────┴───────────┘
```

nvim restores `Session.vim` if present, otherwise opens the project directory.

**Window 2 — `repl`**: ipython (falls back to python3) + shell scratch.

## Pomodoro (`pom.py`)

Launched automatically in the bottom-right pane.

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
