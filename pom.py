#!/usr/bin/env python3
"""pom — minimal Pomodoro timer for the terminal."""

import os
import sys
import time
import select
import shutil
import argparse
from dataclasses import dataclass
from typing import Optional

try:
    import termios, tty  # noqa: F401
    HAS_RAW = True
except ImportError:
    HAS_RAW = False  # Windows / non-tty fallback

WORK_MIN         = 25
SHORT_BREAK_MIN  = 5
LONG_BREAK_MIN   = 15
LONG_BREAK_EVERY = 4

# ── ANSI ──────────────────────────────────────────────────────────────────────
RESET       = "\033[0m"
BOLD        = "\033[1m"
DIM         = "\033[2m"
RED         = "\033[31m"
GREEN       = "\033[32m"
BLUE        = "\033[34m"
YELLOW      = "\033[33m"
CYAN        = "\033[36m"
HOME        = "\033[H"
CLEAR       = "\033[2J\033[H"
ERASE_DOWN  = "\033[J"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


# ── Stats ──────────────────────────────────────────────────────────────────────
@dataclass
class Stats:
    work_done:      int = 0
    work_skipped:   int = 0
    breaks_done:    int = 0
    breaks_skipped: int = 0
    work_secs:      int = 0
    break_secs:     int = 0


# ── Helpers ────────────────────────────────────────────────────────────────────
def cols() -> int:
    return shutil.get_terminal_size().columns


def fmt(seconds: int) -> str:
    m, s = divmod(max(seconds, 0), 60)
    return f"{m:02d}:{s:02d}"


# ── tmux status bar ────────────────────────────────────────────────────────────
# The current phase is written (tmux-formatted) to STATUS_FILE for status-right.
# It is rewritten at least once a second, so a stale mtime means pom isn't running.
STATUS_FILE = os.path.expanduser("~/.cache/pom/status")
_status_last = ("", 0.0)


def write_status(text: str) -> None:
    global _status_last
    now = time.monotonic()
    if text == _status_last[0] and now - _status_last[1] < 1.0:
        return
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        with open(STATUS_FILE, "w") as f:
            f.write(text)
        _status_last = (text, now)
    except OSError:
        pass


def clear_status() -> None:
    try:
        os.remove(STATUS_FILE)
    except OSError:
        pass


def read_key(timeout: float = 0.25) -> Optional[str]:
    """Return one keypress (including escape sequences) within *timeout* seconds, or None."""
    if not HAS_RAW or not sys.stdin.isatty():
        time.sleep(timeout)
        return None
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)  # type: ignore[name-defined]
    try:
        tty.setraw(fd)            # type: ignore[name-defined]
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            return None
        ch = os.read(fd, 1).decode("utf-8", errors="replace")
        if ch == "\x1b":
            r2, _, _ = select.select([fd], [], [], 0.04)
            if r2:
                rest = os.read(fd, 8).decode("utf-8", errors="replace")
                return "\x1b" + rest
        return ch
    except Exception:
        time.sleep(timeout)
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)  # type: ignore[name-defined]


# ── Display ────────────────────────────────────────────────────────────────────
def render(
    label: str,
    color: str,
    elapsed: int,
    total: int,
    paused: bool,
    stats: Stats,
    menu: bool = False,
) -> None:
    w         = max(cols() - 4, 10)
    filled    = round(elapsed / total * w) if total else w
    pct       = round(elapsed / total * 100) if total else 100
    remaining = max(total - elapsed, 0)

    b_filled = color + "█" * filled       + RESET
    b_empty  = DIM   + "░" * (w - filled) + RESET
    status   = f"{YELLOW}{BOLD} ⏸  PAUSED {RESET}" if paused else f"{DIM} running {RESET}"

    mini = (
        f"{DIM}✓ {stats.work_done} done"
        + (f"  ✗ {stats.work_skipped} skipped" if stats.work_skipped else "")
        + (f"  ☕ {stats.breaks_done} breaks"   if stats.breaks_done  else "")
        + RESET
    )

    if menu:
        keys = (
            f"  {YELLOW}{BOLD}  q{RESET}{DIM} quit and show stats"
            f"    n{RESET}{DIM} skip to next phase"
            f"    p / Space{RESET}{DIM} resume{RESET}"
        )
    else:
        keys = f"  {DIM}p/Space  pause    n  skip    q  quit{RESET}"

    out = (
        f"\n"
        f"  {color}{BOLD}{label}{RESET}  {status}\n"
        f"\n"
        f"  {b_filled}{b_empty}\n"
        f"\n"
        f"  {BOLD}{fmt(remaining)}{RESET}  {DIM}{pct}% elapsed{RESET}\n"
        f"\n"
        f"{keys}\n"
        f"\n"
        f"  {mini}\n"
        f"{ERASE_DOWN}"
    )
    print(HOME + out, end="", flush=True)


def show_stats(stats: Stats) -> None:
    work_m,  work_s  = divmod(stats.work_secs,  60)
    break_m, break_s = divmod(stats.break_secs, 60)

    print(CLEAR, end="", flush=True)
    print(f"\n  {BOLD}🍅  Pomodoro — session summary{RESET}\n")

    if not (stats.work_done or stats.work_skipped):
        print(f"  {DIM}No sessions recorded.{RESET}\n")
        return

    rows = [
        (GREEN, "Work completed",   stats.work_done,      str(stats.work_done)),
        (DIM,   "Work skipped",     stats.work_skipped,   str(stats.work_skipped)),
        (BLUE,  "Breaks completed", stats.breaks_done,    str(stats.breaks_done)),
        (DIM,   "Breaks skipped",   stats.breaks_skipped, str(stats.breaks_skipped)),
        (CYAN,  "Total focus time", stats.work_secs,      f"{work_m}m {work_s:02d}s"),
        (DIM,   "Total break time", stats.break_secs,     f"{break_m}m {break_s:02d}s"),
    ]
    for color, label, raw, val in rows:
        if not raw:
            continue
        print(f"  {color}{label:<22}{RESET}  {BOLD}{val}{RESET}")

    total_secs = stats.work_secs + stats.break_secs
    pct_focus  = round(stats.work_secs / total_secs * 100) if total_secs else 0
    print(f"\n  {DIM}Focus ratio  {RESET}{BOLD}{pct_focus}%{RESET}\n")


# ── Start / config screen ─────────────────────────────────────────────────────
# (label, min, max) — Sessions: 0 = infinite
_FIELDS = [
    ("Work duration",  1, 120),
    ("Short break",    1,  60),
    ("Long break",     1,  60),
    ("Sessions",       0,  99),
]


def render_start(vals: list, sel: int) -> None:
    lines = [f"\n  {BOLD}🍅  Pomodoro Timer{RESET}\n\n"]
    for i, (label, _, _) in enumerate(_FIELDS):
        v    = vals[i]
        disp = ("∞" if v == 0 else str(v)) + (" min" if i < 3 else "")
        if i == sel:
            lines.append(f"  {CYAN}{BOLD}▶  {label:<18}{RESET}  {CYAN}{BOLD}{disp}{RESET}\n")
        else:
            lines.append(f"     {DIM}{label:<18}{RESET}  {disp}\n")
    lines.append(
        f"\n  {DIM}↑ ↓  select"
        f"    ← → or - +  adjust"
        f"    Enter / Space  start"
        f"    q  quit{RESET}\n"
    )
    print(HOME + "".join(lines) + ERASE_DOWN, end="", flush=True)


def start_screen(work: int, short: int, long: int, count: int) -> Optional[tuple]:
    """
    Interactive pre-start screen.
    Returns (work, short, long, count) or None if the user quits.
    """
    vals = [work, short, long, count]
    mins = [f[1] for f in _FIELDS]
    maxs = [f[2] for f in _FIELDS]
    sel  = 0

    print(CLEAR, end="", flush=True)
    render_start(vals, sel)

    while True:
        key = read_key(0.5)
        if key is None:
            continue
        if key in ("\r", "\n", " "):
            return tuple(vals)
        if key in ("q", "\x03"):
            return None

        prev_sel, prev_vals = sel, vals[:]
        if key in ("\x1b[A", "k"):
            sel = (sel - 1) % len(_FIELDS)
        elif key in ("\x1b[B", "j"):
            sel = (sel + 1) % len(_FIELDS)
        elif key in ("\x1b[C", "+", "="):
            vals[sel] = min(vals[sel] + 1, maxs[sel])
        elif key in ("\x1b[D", "-"):
            vals[sel] = max(vals[sel] - 1, mins[sel])

        if sel != prev_sel or vals != prev_vals:
            render_start(vals, sel)


# ── Core countdown ─────────────────────────────────────────────────────────────
def countdown(
    label: str,
    color: str,
    total_seconds: int,
    stats: Stats,
    is_work: bool,
) -> str:
    """
    Runs one timed phase.  Returns 'done' | 'skip' | 'quit'.
    """
    print(CLEAR, end="", flush=True)
    status_color = "#f38ba8" if is_work else ("#89b4fa" if color == BLUE else "#a6e3a1")
    status_word  = "work" if is_work else "break"
    start        = time.monotonic()
    pause_start: Optional[float] = None
    paused_total = 0.0
    menu_open    = False
    last_state   = (-1, False, False)  # (remaining, paused, menu_open) — seed forces first render

    while True:
        now       = time.monotonic()
        elapsed   = int((pause_start if pause_start else now) - start - paused_total)
        remaining = max(total_seconds - elapsed, 0)
        paused    = pause_start is not None

        state = (remaining, paused, menu_open)
        if state != last_state:
            render(label, color, elapsed, total_seconds,
                   paused=paused, stats=stats, menu=menu_open)
            last_state = state
        icon = "⏸" if paused else "●"
        write_status(f"#[fg={status_color}]{icon} {status_word} {fmt(remaining)}")

        if remaining == 0 and not paused:
            print(HOME, end="")
            print(f"\n  {color}{BOLD}✓  {label} — done!{RESET}  \a\n", flush=True)
            time.sleep(0.8)
            if is_work:
                stats.work_done += 1
                stats.work_secs += elapsed
            else:
                stats.breaks_done += 1
                stats.break_secs  += elapsed
            return "done"

        key = read_key(0.25)
        if key is None:
            continue

        if key in (" ", "p"):
            menu_open = False
            if pause_start is not None:
                paused_total += time.monotonic() - pause_start
                pause_start = None
            else:
                pause_start = time.monotonic()

        elif key == "q":
            if not menu_open:
                if not paused:
                    pause_start = time.monotonic()
                menu_open = True
            else:
                if is_work:
                    stats.work_secs    += elapsed
                    stats.work_skipped += 1
                else:
                    stats.break_secs     += elapsed
                    stats.breaks_skipped += 1
                return "quit"

        elif key == "\x03":
            if is_work:
                stats.work_secs  += elapsed
            else:
                stats.break_secs += elapsed
            return "quit"

        elif key in ("n", "s"):
            if is_work:
                stats.work_skipped += 1
                stats.work_secs    += elapsed
            else:
                stats.breaks_skipped += 1
                stats.break_secs     += elapsed
            return "skip"


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        prog="pom",
        description="Pomodoro timer — p pause · n skip · q quit",
    )
    ap.add_argument("-w", "--work",  type=int, default=WORK_MIN,        metavar="MIN",
                    help=f"work duration (default {WORK_MIN})")
    ap.add_argument("-s", "--short", type=int, default=SHORT_BREAK_MIN,  metavar="MIN",
                    help=f"short break (default {SHORT_BREAK_MIN})")
    ap.add_argument("-l", "--long",  type=int, default=LONG_BREAK_MIN,   metavar="MIN",
                    help=f"long break (default {LONG_BREAK_MIN})")
    ap.add_argument("-n", "--count", type=int, default=0,                metavar="N",
                    help="sessions to run (0 = infinite)")
    args = ap.parse_args()

    stats = Stats()
    print(HIDE_CURSOR, end="", flush=True)

    try:
        cfg = start_screen(args.work, args.short, args.long, args.count)
        if cfg is None:
            return

        work_m, short_m, long_m, count = cfg
        session = 0

        while True:
            session += 1
            if count and session > count:
                break

            result = countdown(f"Work  #{session}", RED, work_m * 60, stats, is_work=True)
            if result == "quit":
                break

            if session % LONG_BREAK_EVERY == 0:
                blabel = f"Long break  (after session {session})"
                bcolor = BLUE
                bdur   = long_m * 60
            else:
                blabel = f"Short break  (after session {session})"
                bcolor = GREEN
                bdur   = short_m * 60

            result = countdown(blabel, bcolor, bdur, stats, is_work=False)
            if result == "quit":
                break

        if count and session > count:
            print(CLEAR, end="", flush=True)
            print(f"\n  {GREEN}{BOLD}🎉  All {count} sessions complete!{RESET}\n")
            time.sleep(0.8)

    finally:
        clear_status()
        print(SHOW_CURSOR, end="", flush=True)
        show_stats(stats)


if __name__ == "__main__":
    main()
