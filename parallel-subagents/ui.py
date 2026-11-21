"""Terminal presentation: colours, glyphs, prompts, listings, and the spinner.

Follows the ape-cli-terminal-experience style (Claude Code aesthetic):
mostly grey, muted 256-colour accents, one line per fact, braille spinner on stderr,
and plain-text fallback when piped.

Python 3.10+ (PEP 604 unions). No external dependencies.
"""

import getpass
import itertools
import os
import re
import shutil
import sys
import threading
import time
from contextlib import contextmanager

# 256-colour palette: muted variants, deliberate semantics
_ACCENT = "208"  # amber: voice, prompts, commands, active selection
_OK = "71"       # muted green: passed, created, settled success
_ERR = "167"     # muted red: failure, high risk
_WARN = "179"    # muted amber-yellow: worth knowing, medium risk
_INFO = "110"    # muted blue: neutral narration, low risk
_DIM = "245"     # secondary text, labels, units
_FAINT = "240"   # rules, separators, chrome

_forced: bool | None = None
_quiet = False
_assume_yes = False


class Cancelled(Exception):
    """The user declined or aborted. Not an error -- exit 0."""


class NoInput(Exception):
    """stdin is exhausted and the question has no safe default."""


def init() -> None:
    """Line-buffer stdout so it interleaves in order with unbuffered stderr."""
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass


def set_color(enabled: bool | None) -> None:
    global _forced
    _forced = enabled


def set_quiet(enabled: bool) -> None:
    """--quiet: suppress narration. Errors and warnings still print."""
    global _quiet
    _quiet = enabled


def set_yes(enabled: bool) -> None:
    """--yes: never block on a prompt."""
    global _assume_yes
    _assume_yes = enabled


# --- detection: colour and terminal are different questions ------------------

def is_tty(stream=None) -> bool:
    """True when `stream` is a real terminal, regardless of colour settings."""
    stream = stream or sys.stdout
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def color_enabled(stream=None) -> bool:
    if _forced is not None:
        return _forced
    if os.environ.get("NO_COLOR"):            # present and non-empty -- standard spec
        return False
    force = os.environ.get("FORCE_COLOR")
    if force is not None:                     # 0/false disable, anything else enables
        return force not in ("0", "false")
    if os.environ.get("TERM") == "dumb":
        return False
    return is_tty(stream)


def paint(text: str, code: str, *, bold: bool = False, stream=None) -> str:
    if not text or not color_enabled(stream):
        return text
    prefix = "\033[1m" if bold else ""
    return f"{prefix}\033[38;5;{code}m{text}\033[0m"


def dim(t: str, **kw) -> str:
    return paint(t, _DIM, **kw)


def faint(t: str, **kw) -> str:
    return paint(t, _FAINT, **kw)


def accent(t: str, **kw) -> str:
    return paint(t, _ACCENT, **kw)


def strong(t: str, **kw) -> str:
    return f"\033[1m{t}\033[0m" if color_enabled(kw.get("stream")) else t


def ok_text(t: str, **kw) -> str:
    return paint(t, _OK, **kw)


def warn_text(t: str, **kw) -> str:
    return paint(t, _WARN, **kw)


def err_text(t: str, **kw) -> str:
    return paint(t, _ERR, **kw)


def info_text(t: str, **kw) -> str:
    return paint(t, _INFO, **kw)


# --- line grammar -----------------------------------------------------------

_GLYPHS = {
    "ok": ("✓", "[OK]", _OK),
    "err": ("✗", "[FAIL]", _ERR),
    "warn": ("!", "[WARN]", _WARN),
    "info": ("·", "[INFO]", _INFO),
    "step": ("›", ">", _ACCENT),
}


def glyph(role: str, stream=None) -> str:
    """Shape follows the terminal; colour follows the palette."""
    mark, fallback, code = _GLYPHS[role]
    return paint(mark if is_tty(stream) else fallback, code, stream=stream)


def _status(role: str, message: str, detail: str = "", *, width: int = 0, stream=None) -> None:
    stream = stream or sys.stdout
    line = f"{glyph(role, stream)} {message.ljust(width) if width else message}"
    if detail:
        line += f"  {dim(detail, stream=stream)}"
    print(line, file=stream, flush=True)


def ok(m: str, d: str = "", **kw) -> None:
    if not _quiet:
        _status("ok", m, d, **kw)


def info(m: str, d: str = "", **kw) -> None:
    if not _quiet:
        _status("info", m, d, **kw)


def step(m: str, d: str = "", **kw) -> None:
    if not _quiet:
        _status("step", m, d, **kw)


def err(m: str, d: str = "", **kw) -> None:
    kw.setdefault("stream", sys.stderr)
    _status("err", m, d, **kw)


def warn(m: str, d: str = "", **kw) -> None:
    kw.setdefault("stream", sys.stderr)
    _status("warn", m, d, **kw)


def heading(text: str, count: int | str | None = None, *, stream=None) -> None:
    """Bold title, blank line above. The count is dim and parenthesised."""
    stream = stream or sys.stdout
    if _quiet:
        return
    line = strong(text, stream=stream)
    if count is not None:
        line += f" {dim(f'({count})', stream=stream)}"
    print(file=stream)
    print(line, file=stream, flush=True)


def rule(stream=None) -> None:
    """Horizontal separator, skipped in pipes and quiet mode."""
    stream = stream or sys.stdout
    if _quiet or not is_tty(stream):
        return
    width = min(shutil.get_terminal_size((80, 24)).columns, 80)
    print(faint("─" * width, stream=stream), file=stream, flush=True)


def kv(label: str, value: str, *, width: int = 0, stream=None) -> None:
    stream = stream or sys.stdout
    if _quiet:
        return
    text = f"{label}:".ljust(width) if width else f"{label}:"
    print(f"  {dim(text, stream=stream)} {value}", file=stream, flush=True)


def bullet(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if _quiet:
        return
    print(f"  {faint('·', stream=stream)} {text}", file=stream, flush=True)


def hint(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if _quiet:
        return
    print(file=stream)
    print(dim(text, stream=stream), file=stream, flush=True)


def command(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if _quiet:
        return
    print(f"  {accent(text, stream=stream)}", file=stream, flush=True)


# --- listings: one formatter, shared with the TUI ---------------------------

def widths(rows: list[list[str]]) -> list[int]:
    """Column widths over the whole batch -- never format a row in isolation."""
    return [max(len(str(c)) for c in col) for col in zip(*rows)] if rows else []


def row(cells: list[str], col_widths: list[int], *, color=None, dims=(), stream=None) -> str:
    """Format one listing row as a string.

    `color` is (index, fn) where fn(cell) returns a palette code or None.
    `dims` is a tuple/list of column indices to render in dim grey.
    """
    out = []
    last = len(cells) - 1
    for i, cell in enumerate(cells):
        text = str(cell)
        if i != last and i < len(col_widths):
            text = text.ljust(col_widths[i])
        if color and i == color[0]:
            code = color[1](str(cell))
            text = paint(text, code, stream=stream) if code else text
        elif i in dims:
            text = dim(text, stream=stream)
        out.append(text)
    return "  " + "  ".join(out)


def table(rows: list[list[str]], *, color=None, dims=(), stream=None) -> None:
    stream = stream or sys.stdout
    w = widths(rows)
    for cells in rows:
        print(row(cells, w, color=color, dims=dims, stream=stream), file=stream, flush=True)


# --- prompts ----------------------------------------------------------------

def prompt(text: str, default: str = "") -> str:
    """Ask a question. Returns stripped answer, or default on Enter."""
    if _assume_yes:
        return default
    suffix = f" {dim(f'[{default}]')}" if default else ""
    try:
        answer = input(f"{glyph('step')} {text}{suffix}: ").strip()
    except EOFError:
        print(file=sys.stderr)
        if default:
            return default
        raise NoInput(text) from None
    return answer or default


def confirm(question: str, *, default: bool = False) -> bool:
    """Yes/no confirmation. --yes answers True."""
    if _assume_yes:
        return True
    marks = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"{glyph('step')} {question} {dim(marks)} ").strip().lower()
        except EOFError:
            print(file=sys.stderr)
            raise NoInput(question) from None
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        warn("answer y or n")


# --- spinner ----------------------------------------------------------------

_FRAMES, _INTERVAL = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", 0.08


class Spinner:
    def __init__(self, message: str, *, quiet: bool | None = None, stream=None):
        self.message = message
        self.stream = stream or sys.stderr
        self.quiet = _quiet if quiet is None else quiet
        self.animated = not self.quiet and is_tty(self.stream)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = 0.0

    def _spin(self) -> None:
        for frame in itertools.cycle(_FRAMES):
            if self._stop.is_set():
                return
            elapsed = time.monotonic() - self._started
            timer = f" ({elapsed:.0f}s)" if elapsed >= 1.0 else ""
            cols = shutil.get_terminal_size((80, 24)).columns
            room = max(8, cols - len(timer) - 3)
            msg = self.message
            if len(msg) > room:
                msg = msg[:room - 1] + "…"
            self.stream.write(f"\r{accent(frame, stream=self.stream)} {msg}{dim(timer, stream=self.stream)}")
            self.stream.flush()
            self._stop.wait(_INTERVAL)

    def start(self):
        self._started = time.monotonic()
        if self.animated:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        elif not self.quiet:
            print(f"{self.message}...", file=self.stream, flush=True)
        return self

    def _erase(self) -> None:
        if not self.animated:
            return
        width = shutil.get_terminal_size((80, 24)).columns
        self.stream.write("\r" + " " * (width - 1) + "\r")
        self.stream.flush()

    def stop(self, final: str | None = None, role: str = "ok") -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._erase()
        if final and not self.quiet:
            elapsed = time.monotonic() - self._started
            _status(role, final, f"({elapsed:.1f}s)" if elapsed >= 1.0 else "", stream=self.stream)

    def update(self, message: str) -> None:
        if self.animated:
            self._erase()
        self.message = message


@contextmanager
def spinner(message: str, *, done: str | None = None, quiet: bool | None = None, stream=None):
    sp = Spinner(message, quiet=quiet, stream=stream).start()
    try:
        yield sp
    except BaseException:
        sp.stop()
        raise
    else:
        sp.stop(done)


# --- exit codes: mapped in one place ----------------------------------------

def run(main, codes: dict | None = None) -> int:
    """Wrap top-level entry point. Handles Ctrl-C, Cancelled, and NoInput."""
    init()
    try:
        return main() or 0
    except KeyboardInterrupt:
        print(file=sys.stderr)
        warn("interrupted")
        return 130
    except Cancelled as e:
        info(str(e) or "cancelled")
        return 0
    except NoInput as e:
        err("this command needs an answer and stdin is exhausted", str(e))
        hint("run it interactively, or pass --yes to accept the defaults")
        return 1
    except Exception as e:
        for kind, code in (codes or {}).items():
            if isinstance(e, kind):
                err(str(e))
                return code
        raise
