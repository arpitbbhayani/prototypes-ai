"""Unit tests verifying terminal presentation invariants from ape-cli-terminal-experience."""

import io
import os
import sys
import pytest
import ui


class FakeStream(io.StringIO):
    def __init__(self, tty=False):
        super().__init__()
        self._tty = tty

    def isatty(self):
        return self._tty


@pytest.fixture(autouse=True)
def clean_env():
    # Save original env
    orig_env = dict(os.environ)
    os.environ["TERM"] = "xterm-256color"
    ui.set_color(None)
    ui.set_quiet(False)
    ui.set_yes(False)
    yield
    # Restore original env
    os.environ.clear()
    os.environ.update(orig_env)
    ui.set_color(None)
    ui.set_quiet(False)
    ui.set_yes(False)


def test_detection_piped():
    stream = FakeStream(tty=False)
    ui.ok("operation passed", stream=stream)
    output = stream.getvalue()
    assert "\x1b" not in output
    assert "[OK]" in output
    assert "✓" not in output


def test_detection_tty():
    stream = FakeStream(tty=True)
    ui.ok("operation passed", stream=stream)
    output = stream.getvalue()
    assert "\x1b[38;5;71m" in output
    assert "✓" in output
    assert "[OK]" not in output


def test_no_color_env():
    # NO_COLOR=1 disables colour
    os.environ["NO_COLOR"] = "1"
    stream = FakeStream(tty=True)
    ui.ok("check", stream=stream)
    out = stream.getvalue()
    assert "\x1b" not in out
    assert "✓" in out  # Glyph stays unicode on TTY! Only colour is disabled

    # NO_COLOR="" (empty string) does NOT disable colour per spec
    os.environ["NO_COLOR"] = ""
    stream2 = FakeStream(tty=True)
    ui.ok("check", stream=stream2)
    assert "\x1b[38;5;71m" in stream2.getvalue()


def test_force_color_piped():
    # FORCE_COLOR=1 colors pipe, but glyph remains bracketed because stream is not TTY
    os.environ["FORCE_COLOR"] = "1"
    stream = FakeStream(tty=False)
    ui.ok("piped colored", stream=stream)
    out = stream.getvalue()
    assert "\x1b[38;5;71m" in out
    assert "[OK]" in out
    assert "✓" not in out


def test_status_width_padding():
    stream = FakeStream(tty=False)
    ui.ok("short", "detail1", width=15, stream=stream)
    ui.ok("much longer msg", "detail2", width=15, stream=stream)
    lines = stream.getvalue().strip().split("\n")
    # Details should align at the exact same column
    idx1 = lines[0].index("detail1")
    idx2 = lines[1].index("detail2")
    assert idx1 == idx2


def test_rule_skipped_when_not_tty():
    stream = FakeStream(tty=False)
    ui.rule(stream=stream)
    assert stream.getvalue() == ""

    # Even with FORCE_COLOR=1, rule should be skipped in a pipe
    os.environ["FORCE_COLOR"] = "1"
    stream_fc = FakeStream(tty=False)
    ui.rule(stream=stream_fc)
    assert stream_fc.getvalue() == ""


def test_prompt_no_input_on_eof():
    # Exhausted stdin raises NoInput when no default is provided
    sys.stdin = io.StringIO("")
    with pytest.raises(ui.NoInput):
        ui.prompt("Required question")


def test_prompt_default_on_eof():
    sys.stdin = io.StringIO("")
    val = ui.prompt("Question with default", default="fallback")
    assert val == "fallback"


def test_yes_flag_skips_prompts():
    ui.set_yes(True)
    # Stdin is closed / empty
    sys.stdin = io.StringIO("")
    assert ui.prompt("Question", default="def") == "def"
    assert ui.confirm("Confirm dangerous action", default=False) is True
