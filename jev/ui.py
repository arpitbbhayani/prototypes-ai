"""Terminal presentation: colours, glyphs, prompts, listings, and the spinner.

Python 3.10+ (PEP 604 unions). No external dependencies.
Adheres to the ape-cli-terminal-experience specification.
"""

from __future__ import annotations

import getpass
import itertools
import os
import re
import shutil
import sys
import threading
import time
from contextlib import contextmanager

_ACCENT, _OK, _ERR, _WARN, _INFO, _DIM, _FAINT = "208", "71", "167", "179", "110", "245", "240"
_forced: bool | None = None
_quiet = False
_assume_yes = False


class Cancelled(Exception):
    """The user declined. Not an error -- exit 0."""


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
    if os.environ.get("NO_COLOR"):            # present and non-empty -- the spec
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


# --- lines ------------------------------------------------------------------

_GLYPHS = {
    "ok": ("✓", "[OK]", _OK),
    "err": ("✗", "[FAIL]", _ERR),
    "warn": ("!", "[WARN]", _WARN),
    "info": ("·", "[INFO]", _INFO),
    "step": ("›", ">", _ACCENT),
}


def glyph(role: str, stream=None) -> str:
    """Shape follows the terminal; colour follows the palette. Two questions."""
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


def heading(text: str, count: int | None = None, *, stream=None) -> None:
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
    stream = stream or sys.stdout
    if _quiet or not is_tty(stream):          # a terminal question, not a colour one
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

def widths(rows: list[list[object]]) -> list[int]:
    """Column widths over the whole batch -- never format a row in isolation."""
    return [max(len(str(c)) for c in col) for col in zip(*rows)] if rows else []


def row(cells: list[object], column_widths: list[int], *, color=None, dims=(), stream=None) -> str:
    """One listing row as a string, so the plain listing and the TUI stay in sync.

    `color` is (index, fn) for the single column that carries colour, where fn(cell)
    returns a palette code or None. `dims` are the indices to dim.
    """
    out = []
    last = len(cells) - 1
    for i, cell in enumerate(cells):
        text = str(cell)
        if i != last and i < len(column_widths):
            text = text.ljust(column_widths[i])
        if color and i == color[0]:
            code = color[1](str(cell))
            text = paint(text, code, stream=stream) if code else text
        elif i in dims:
            text = dim(text, stream=stream)
        out.append(text)
    return "  " + "  ".join(out)


def table(rows: list[list[object]], *, color=None, dims=(), stream=None) -> None:
    stream = stream or sys.stdout
    w = widths(rows)
    for cells in rows:
        print(row(cells, w, color=color, dims=dims, stream=stream), file=stream, flush=True)


# --- prompts ----------------------------------------------------------------

def prompt(text: str, default: str = "") -> str:
    """Ask a question. Returns the answer stripped, or `default` on Enter.

    Never raises EOFError: with a default it takes it, without one it raises NoInput.
    """
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
    """Yes/no. Anything destructive or outward-facing passes default=False.

    `--yes` answers yes -- it exists to unblock automation. A gate too dangerous for
    `--yes` needs its own explicit flag, not a default of no.
    """
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


def mask(value: str) -> str:
    if not value:
        return ""
    return "*" * len(value) if len(value) <= 8 else f"{value[:4]}...{value[-4:]}"


def secret(label: str, current: str = "") -> str:
    """Prompt for a secret. The existing value echoes masked, with a keep affordance."""
    if _assume_yes:
        return current
    suffix = f" {dim(f'[{mask(current)}, Enter to keep]')}" if current else ""
    try:
        answer = getpass.getpass(f"{glyph('step')} {label}{suffix}: ").strip()
    except EOFError:
        print(file=sys.stderr)
        if current:
            return current
        raise NoInput(label) from None
    return answer or current


def menu(title: str, rows: list[tuple[str, str]], *, default: int = 1) -> int:
    """Numbered menu over (label, detail) rows. Returns the 1-based choice."""
    heading(title)
    w = max((len(label) for label, _ in rows), default=0)
    for i, (label, detail) in enumerate(rows, 1):
        line = f"  {accent(f'{i}.')} {label.ljust(w)}"
        if detail:
            line += f"  {dim(detail)}"
        print(line, flush=True)
    while True:
        answer = prompt(f"pick [1-{len(rows)}]", str(default))
        if answer.isdigit() and 1 <= int(answer) <= len(rows):
            return int(answer)
        warn(f"pick a number between 1 and {len(rows)}")


def keep_all_but(count: int, *, noun: str = "items") -> list[int]:
    """Multi-select by exception. Enter keeps all, digits drop rows, n aborts.

    Returns the 1-based indices to keep. Raises Cancelled on abort or an empty result.
    """
    hint("Enter accepts all; list numbers to drop (e.g. 2,3); n aborts")
    answer = prompt("keep all?")
    if answer.lower() in ("n", "no"):
        raise Cancelled("cancelled")
    dropped = {int(d) for d in re.findall(r"\d+", answer)}
    kept = [i for i in range(1, count + 1) if i not in dropped]
    if not kept:
        raise Cancelled(f"all {count} {noun} were dropped -- nothing left to run")
    return kept


# --- spinner ----------------------------------------------------------------

_FRAMES, _INTERVAL = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", 0.08


class Spinner:
    def __init__(self, message: str, *, quiet: bool | None = None, stream=None):
        self.message, self.stream = message, stream or sys.stderr
        self.quiet = _quiet if quiet is None else quiet
        self.animated = not self.quiet and is_tty(self.stream)   # a TTY, not colour
        self._stop = threading.Event()
        self._thread = None
        self._started = 0.0

    def _spin(self):
        for frame in itertools.cycle(_FRAMES):
            if self._stop.is_set():
                return
            elapsed = time.monotonic() - self._started
            timer = f" ({elapsed:.0f}s)" if elapsed >= 1 else ""
            # Truncate: a wrapped line cannot be erased with one \r.
            room = max(8, shutil.get_terminal_size((80, 24)).columns - len(timer) - 3)
            message = self.message
            if len(message) > room:
                message = message[:room - 1] + "…"
            self.stream.write(f"\r{accent(frame, stream=self.stream)} {message}"
                              f"{dim(timer, stream=self.stream)}")
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

    def _erase(self):
        if not self.animated:
            return
        width = shutil.get_terminal_size((80, 24)).columns
        self.stream.write("\r" + " " * (width - 1) + "\r")
        self.stream.flush()

    def stop(self, final: str | None = None, role: str = "ok"):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._erase()
        if final and not self.quiet:
            elapsed = time.monotonic() - self._started
            _status(role, final, f"({elapsed:.1f}s)" if elapsed >= 1.0 else "",
                    stream=self.stream)

    def update(self, message: str):
        if self.animated:
            self._erase()
        self.message = message


@contextmanager
def spinner(message: str, *, done: str | None = None, quiet: bool | None = None, stream=None):
    sp = Spinner(message, quiet=quiet, stream=stream).start()
    try:
        yield sp
    except BaseException:
        sp.stop()      # erase before the traceback lands
        raise
    else:
        sp.stop(done)


# --- exit codes: mapped in one place ----------------------------------------

def run(main, codes: dict[type[Exception], int] | None = None) -> int:
    """Wrap the top-level entry point. `codes` maps exception types to exit codes.

    Usage: sys.exit(ui.run(main, {StoreMissing: 1, ConnectorError: 2}))
    """
    try:
        return main() or 0
    except KeyboardInterrupt:
        print(file=sys.stderr)          # the spinner cleared its own line already
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
        raise                            # unmapped means a bug: let it traceback
