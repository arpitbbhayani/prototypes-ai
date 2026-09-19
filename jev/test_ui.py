"""Unit tests for ui.py presentation invariants.

Follows Section 15 of ape-cli-terminal-experience.
Run with pytest or python test_ui.py.
"""

from __future__ import annotations

import io
import os
import unittest
from unittest.mock import patch

import ui


class MockStream(io.StringIO):
    def __init__(self, is_tty_val: bool = True):
        super().__init__()
        self._is_tty = is_tty_val

    def isatty(self) -> bool:
        return self._is_tty


class TestUIDetection(unittest.TestCase):
    def setUp(self):
        ui.set_color(None)
        ui.set_quiet(False)
        ui.set_yes(False)

    def tearDown(self):
        ui.set_color(None)
        ui.set_quiet(False)
        ui.set_yes(False)

    def test_pipe_detection(self):
        pipe = MockStream(is_tty_val=False)
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(ui.is_tty(pipe))
            self.assertFalse(ui.color_enabled(pipe))
            g = ui.glyph("ok", stream=pipe)
            self.assertEqual(g, "[OK]")
            self.assertNotIn("\x1b", g)

    def test_tty_detection(self):
        tty = MockStream(is_tty_val=True)
        with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True):
            self.assertTrue(ui.is_tty(tty))
            self.assertTrue(ui.color_enabled(tty))
            g = ui.glyph("ok", stream=tty)
            self.assertIn("✓", g)
            self.assertIn("\x1b[38;5;71m", g)
            self.assertNotIn("[OK]", g)

    def test_no_color_env(self):
        tty = MockStream(is_tty_val=True)
        # NO_COLOR present and non-empty disables color
        with patch.dict(os.environ, {"NO_COLOR": "1", "TERM": "xterm-256color"}):
            self.assertFalse(ui.color_enabled(tty))
            g = ui.glyph("ok", stream=tty)
            self.assertEqual(g, "✓")  # Glyph is still Unicode, but no escapes

        # NO_COLOR empty does NOT disable color
        with patch.dict(os.environ, {"NO_COLOR": "", "TERM": "xterm-256color"}):
            self.assertTrue(ui.color_enabled(tty))

    def test_force_color_env(self):
        pipe = MockStream(is_tty_val=False)
        # FORCE_COLOR=1 enables color in pipe, but is_tty remains False
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}):
            self.assertFalse(ui.is_tty(pipe))
            self.assertTrue(ui.color_enabled(pipe))
            g = ui.glyph("ok", stream=pipe)
            self.assertIn("[OK]", g)
            self.assertIn("\x1b[38;5;71m", g)

        # FORCE_COLOR=0 disables color even on TTY
        tty = MockStream(is_tty_val=True)
        with patch.dict(os.environ, {"FORCE_COLOR": "0"}):
            self.assertFalse(ui.color_enabled(tty))

    def test_term_dumb(self):
        tty = MockStream(is_tty_val=True)
        with patch.dict(os.environ, {"TERM": "dumb"}):
            self.assertFalse(ui.color_enabled(tty))

    def test_set_color_override(self):
        tty = MockStream(is_tty_val=True)
        ui.set_color(False)
        self.assertFalse(ui.color_enabled(tty))
        self.assertEqual(ui.glyph("ok", stream=tty), "✓")

    def test_closed_stream_isatty(self):
        closed = io.StringIO()
        closed.close()
        self.assertFalse(ui.is_tty(closed))


class TestUILinesAndListings(unittest.TestCase):
    def setUp(self):
        ui.set_color(False)
        ui.set_quiet(False)

    def tearDown(self):
        ui.set_color(None)
        ui.set_quiet(False)

    def test_status_line_padding(self):
        out1 = MockStream(is_tty_val=True)
        out2 = MockStream(is_tty_val=True)
        ui._status("ok", "short", "detail", width=12, stream=out1)
        ui._status("ok", "longer_name", "detail", width=12, stream=out2)
        # Check alignment of detail
        lines1 = out1.getvalue().splitlines()[0]
        lines2 = out2.getvalue().splitlines()[0]
        self.assertEqual(lines1.index("detail"), lines2.index("detail"))

    def test_heading(self):
        out = MockStream(is_tty_val=True)
        ui.heading("tools selected", 3, stream=out)
        text = out.getvalue()
        self.assertTrue(text.startswith("\n"))
        self.assertIn("tools selected (3)", text)

    def test_rule_skipped_when_not_tty(self):
        pipe = MockStream(is_tty_val=False)
        ui.rule(stream=pipe)
        self.assertEqual(pipe.getvalue(), "")

        tty = MockStream(is_tty_val=True)
        ui.rule(stream=tty)
        self.assertTrue(len(tty.getvalue().strip()) > 0)

    def test_kv_line(self):
        out = MockStream(is_tty_val=True)
        ui.kv("harness", "claude -p", width=10, stream=out)
        self.assertEqual(out.getvalue(), "  harness:   claude -p\n")

    def test_table_formatting(self):
        rows = [
            ["read", "github.pulls", "List PRs", "ready"],
            ["write", "slack.messages", "Send message", "unauthorized"],
        ]
        out = MockStream(is_tty_val=True)
        ui.table(rows, color=(3, lambda c: "71" if c == "ready" else "167"), dims=(2,), stream=out)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("ready", lines[0])
        self.assertIn("unauthorized", lines[1])


class TestUIPrompts(unittest.TestCase):
    def setUp(self):
        ui.set_color(False)
        ui.set_yes(False)

    def tearDown(self):
        ui.set_yes(False)

    def test_prompt_default_on_enter(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(ui.prompt("name", default="alice"), "alice")

    def test_prompt_no_input_on_eof(self):
        with patch("builtins.input", side_effect=EOFError):
            with self.assertRaises(ui.NoInput):
                ui.prompt("name")

    def test_prompt_default_on_eof(self):
        with patch("builtins.input", side_effect=EOFError):
            self.assertEqual(ui.prompt("name", default="bob"), "bob")

    def test_confirm_cases(self):
        with patch("builtins.input", return_value="y"):
            self.assertTrue(ui.confirm("proceed?"))
        with patch("builtins.input", return_value=""):
            self.assertFalse(ui.confirm("proceed?", default=False))
            self.assertTrue(ui.confirm("proceed?", default=True))

    def test_mask(self):
        self.assertEqual(ui.mask("short"), "*****")
        self.assertEqual(ui.mask("12345678"), "********")
        self.assertEqual(ui.mask("123456789"), "1234...6789")

    def test_keep_all_but(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(ui.keep_all_but(4), [1, 2, 3, 4])
        with patch("builtins.input", return_value="2, 4"):
            self.assertEqual(ui.keep_all_but(4), [1, 3])
        with patch("builtins.input", return_value="n"):
            with self.assertRaises(ui.Cancelled):
                ui.keep_all_but(4)
        with patch("builtins.input", return_value="1, 2, 3, 4"):
            with self.assertRaises(ui.Cancelled):
                ui.keep_all_but(4)

    def test_assume_yes(self):
        ui.set_yes(True)
        # With assume_yes, input() is never called
        self.assertEqual(ui.prompt("test", "default_val"), "default_val")
        self.assertTrue(ui.confirm("proceed?", default=False))


class TestUISpinnerAndRun(unittest.TestCase):
    def setUp(self):
        ui.set_color(False)
        ui.set_quiet(False)

    def test_spinner_on_pipe(self):
        pipe = MockStream(is_tty_val=False)
        with ui.spinner("Working", stream=pipe):
            pass
        output = pipe.getvalue()
        self.assertIn("Working...", output)
        self.assertNotIn("\r", output)

    def test_spinner_quiet(self):
        pipe = MockStream(is_tty_val=False)
        ui.set_quiet(True)
        with ui.spinner("Working", stream=pipe):
            pass
        self.assertEqual(pipe.getvalue(), "")

    def test_run_codes(self):
        class CustomError(Exception):
            pass

        def ok_fn():
            return 0

        def error_fn():
            raise CustomError("failed")

        def ctrl_c_fn():
            raise KeyboardInterrupt()

        self.assertEqual(ui.run(ok_fn), 0)
        self.assertEqual(ui.run(error_fn, {CustomError: 42}), 42)
        self.assertEqual(ui.run(ctrl_c_fn), 130)

    def test_cli_flags_survival(self):
        import main1
        args1 = main1.parse_args(["--json", "judge"])
        self.assertTrue(getattr(args1, "json", False))

        args2 = main1.parse_args(["judge", "--json"])
        self.assertTrue(getattr(args2, "json", False))

        args3 = main1.parse_args(["--no-color", "docket"])
        self.assertTrue(getattr(args3, "no_color", False))

        args4 = main1.parse_args(["docket", "--no-color"])
        self.assertTrue(getattr(args4, "no_color", False))


if __name__ == "__main__":
    unittest.main()
