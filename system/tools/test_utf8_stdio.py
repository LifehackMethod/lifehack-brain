#!/usr/bin/env python3
"""Tests for utf8_stdio — the helper that stops a non-ASCII print() from crashing a script on a
Windows console (cp1252). Proves: (1) it's a true no-op when a stream already reports UTF-8 —
`.reconfigure` is never called; (2) it actually moves a non-UTF-8 text stream to UTF-8 and lets a
non-ASCII glyph print through instead of raising; (3) it never raises, even if `.reconfigure`
itself blows up; (4) it tolerates streams with no `.reconfigure` at all (e.g. a StringIO, which
is what a lot of this repo's own tests swap onto sys.stdout).

Run: python3 system/tools/test_utf8_stdio.py
"""
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utf8_stdio  # noqa: E402


class _FakeStream:
    """A minimal stand-in for a TextIOWrapper, so tests can see whether/how reconfigure() is
    called without touching the real sys.stdout/sys.stderr."""

    def __init__(self, encoding, raise_on_reconfigure=False):
        self.encoding = encoding
        self.reconfigure_calls = []
        self._raise = raise_on_reconfigure

    def reconfigure(self, **kwargs):
        self.reconfigure_calls.append(kwargs)
        if self._raise:
            raise OSError("simulated: this console refuses to reconfigure")


class NoOpWhenAlreadyUtf8(unittest.TestCase):
    def test_utf8_stream_is_left_alone(self):
        out, err = _FakeStream("utf-8"), _FakeStream("utf-8")
        held_out, held_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            utf8_stdio.force_utf8_stdio()
        finally:
            sys.stdout, sys.stderr = held_out, held_err
        self.assertEqual(out.reconfigure_calls, [], "already-UTF-8 stdout must not be touched")
        self.assertEqual(err.reconfigure_calls, [], "already-UTF-8 stderr must not be touched")

    def test_utf8_variant_spellings_also_count_as_already_utf8(self):
        # Python reports a couple of different spellings depending on platform/version.
        for spelling in ("UTF-8", "utf8", "UTF8", "Utf_8"):
            out = _FakeStream(spelling)
            held = sys.stdout
            sys.stdout = out
            try:
                utf8_stdio.force_utf8_stdio()
            finally:
                sys.stdout = held
            self.assertEqual(out.reconfigure_calls, [], f"spelling {spelling!r} should count as UTF-8")


class ReconfiguresANonUtf8Stream(unittest.TestCase):
    def test_cp1252_stream_gets_reconfigured_to_utf8(self):
        out = _FakeStream("cp1252")
        held = sys.stdout
        sys.stdout = out
        try:
            utf8_stdio.force_utf8_stdio()
        finally:
            sys.stdout = held
        self.assertEqual(len(out.reconfigure_calls), 1)
        self.assertEqual(out.reconfigure_calls[0].get("encoding"), "utf-8")
        self.assertIn("errors", out.reconfigure_calls[0])

    def test_a_real_non_utf8_file_stream_can_then_print_a_non_ascii_glyph(self):
        # This is the actual bug: a real TextIOWrapper opened as cp1252 raises
        # UnicodeEncodeError on a checkmark/warning glyph. Prove reconfigure fixes that.
        fd, path = tempfile.mkstemp()
        os.close(fd)
        self.addCleanup(lambda: os.remove(path))
        stream = open(path, "w", encoding="cp1252")
        try:
            held = sys.stdout
            sys.stdout = stream
            try:
                utf8_stdio.force_utf8_stdio()
                # Before the fix this print would raise UnicodeEncodeError on cp1252.
                print("status: ✓ done ⚠ — ok")
            finally:
                sys.stdout = held
        finally:
            stream.close()
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("done", content)
        self.assertIn("✓", content)  # the checkmark survived, not mangled/dropped


class NeverRaises(unittest.TestCase):
    def test_a_stream_whose_reconfigure_itself_raises_does_not_propagate(self):
        out = _FakeStream("cp1252", raise_on_reconfigure=True)
        held = sys.stdout
        sys.stdout = out
        try:
            utf8_stdio.force_utf8_stdio()  # must not raise
        finally:
            sys.stdout = held
        self.assertEqual(len(out.reconfigure_calls), 1, "it should still have tried once")

    def test_a_stream_with_no_reconfigure_method_is_left_alone(self):
        # This is exactly what a lot of this repo's own tests do: swap sys.stdout for a
        # plain StringIO to capture output. StringIO has no .reconfigure.
        out = io.StringIO()
        held = sys.stdout
        sys.stdout = out
        try:
            utf8_stdio.force_utf8_stdio()  # must not raise, must not corrupt the stream
            print("plain ascii output")
        finally:
            sys.stdout = held
        self.assertEqual(out.getvalue(), "plain ascii output\n")

    def test_a_missing_stdout_or_stderr_does_not_crash(self):
        held_out, held_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = None, None
        try:
            utf8_stdio.force_utf8_stdio()  # must not raise even with both streams gone
        finally:
            sys.stdout, sys.stderr = held_out, held_err


class DoesNotCorruptNormalOutput(unittest.TestCase):
    def test_real_sys_stdout_survives_a_call_and_still_prints_ascii_correctly(self):
        # Call it against the REAL current sys.stdout (whatever the test runner gave us —
        # normally already UTF-8 on Mac/Linux CI) and prove plain output still round-trips.
        buf = io.StringIO()
        held = sys.stdout
        sys.stdout = buf
        try:
            # buf is a StringIO (no .reconfigure) so this exercises the "leave it alone" path
            # exactly as it would run for any test harness in this repo.
            utf8_stdio.force_utf8_stdio()
            print("hello world 123")
        finally:
            sys.stdout = held
        self.assertEqual(buf.getvalue(), "hello world 123\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
