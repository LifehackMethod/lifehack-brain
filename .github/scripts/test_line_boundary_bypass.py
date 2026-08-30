#!/usr/bin/env python3
"""test_line_boundary_bypass.py -- adversarial fixture harness for the line-boundary hole
in check_no_internal_leakage.py.

WHY THIS FILE EXISTS. check_no_internal_leakage.py matches every rule -- including the
operator-identity tier compiled from a multi-word term such as a full name -- with
`re.escape(term)` against text that has already been through `text.splitlines()`. Python's
`str.splitlines()` breaks a string on EVERY Unicode line-boundary code point, not just
`\\n`: LF, CRLF, VT (0x0B), FF (0x0C), NEL (0x85), LINE SEPARATOR (U+2028) and PARAGRAPH
SEPARATOR (U+2029) all split. A literal multi-word identity term (an identity-file line
reading "Firstname Lastname", compiled with a literal space between the words) is matched
as ONE regex against ONE line at a time. Insert any line-boundary character between the
two words and the term is no longer whole on any single line the scanner ever looks at.

⛔ THIS HARNESS ASSERTS THE CORRECT (DESIRED) BEHAVIOR, NOT TODAY'S BUGGY ONE -- every
split-term case below expects the scan to CATCH the split term (exit 1), the same way an
intact term does. Run against TODAY's unmodified check_no_internal_leakage.py, the
split-term assertions are EXPECTED TO FAIL (red). That is the deliverable: a harness that
has only ever passed proves nothing about whether it points at real ground. A separate
task fixes the scanner; when it does, this file goes green with NO EDITS.

⛔ NO REAL IDENTITY IS IN THIS FILE. FAKE_TERM below is invented for this test (see
test_fixture_is_inert, which asserts it appears nowhere in the scanner's own source).

Idiom matches test_check_no_internal_leakage.py: no unittest, a procedural main() with a
report(label, passed, detail) tally, and a nonzero process exit on any failure so
run-all-tests.sh's plain `python3 <file>` / exit-code contract keeps working unmodified.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
SCANNER = os.path.join(HERE, "check_no_internal_leakage.py")

# Invented two-word identity term -- a plausible "Firstname Lastname" shape, chosen absent
# from the scanner's own source (asserted below).
FAKE_TERM = "Bramblecross Thistlewood"
FIRST, LAST = FAKE_TERM.split(" ")

_SANDBOX_NOTES = None
_failures = []


def report(label, passed, detail=""):
    print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                               (" -- " + detail) if detail else ""))
    if not passed:
        _failures.append(label)


def run_scanner(args, env=None):
    e = dict(os.environ)
    e.pop("SHIP_IDENTITY", None)
    e["LIFEHACK_ROOT"] = _SANDBOX_NOTES
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, SCANNER] + args, capture_output=True, text=True,
                       cwd=REPO_ROOT, env=e)
    return p.returncode, p.stdout + p.stderr


def write_identity(path, terms):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# invented test identity -- nobody real is in this file\n")
        for t in terms:
            fh.write(t + "\n")


def scan_text(td, idf, text, label):
    """Write `text` to a fixture file, scan it, return (rc, out)."""
    p = os.path.join(td, "probe_{}.md".format(label))
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return run_scanner(["--identity", idf, "--scan-file", p,
                        "--as-path", "docs/probe_{}.md".format(label)])


# case name -> the literal boundary text inserted between FIRST and LAST
BOUNDARY_CASES = {
    "lf": "\n",
    "crlf": "\r\n",
    "u2028_line_separator": "\u2028",
    "u2029_paragraph_separator": "\u2029",
    "vtab_0x0b": "\v",
    "formfeed_0x0c": "\f",
    "nel_0x85": "\x85",
}


def main():
    global _SANDBOX_NOTES
    print("test_line_boundary_bypass.py -- attacking check_no_internal_leakage.py")
    print("(RED FIRST: split-term cases are EXPECTED TO FAIL against unfixed code -- see "
          "module docstring)")
    scanner_src = open(SCANNER, encoding="utf-8").read()

    with tempfile.TemporaryDirectory() as td:
        _SANDBOX_NOTES = os.path.join(td, "empty-notes-root")
        os.makedirs(_SANDBOX_NOTES)
        idf = os.path.join(td, "ship-identity.md")
        write_identity(idf, [FAKE_TERM])

        print("\nFIXTURE HYGIENE")
        collisions = [t for t in (FAKE_TERM, FIRST, LAST) if t.lower() in scanner_src.lower()]
        report("the invented term appears nowhere in the scanner", not collisions,
               "collides: {}".format(collisions))

        table = []  # (case, expected_caught, actually_caught, rc)

        print("\nCONTROLS -- must stay green no matter what the split cases do")
        rc, out = scan_text(td, idf, "signed off by {} on Tuesday\n".format(FAKE_TERM),
                            "control_intact")
        report("CONTROL: intact term on one line -> caught (exit 1)", rc == 1,
               "got exit {}".format(rc))
        table.append(("control: intact term, one line", True, rc == 1, rc))

        rc, out = scan_text(td, idf, "nothing sensitive is written in this file at all.\n",
                            "control_clean")
        report("CONTROL: genuinely clean file -> passes (exit 0)", rc == 0,
               "got exit {}".format(rc))
        table.append(("control: genuinely clean file", False, rc == 1, rc))

        print("\nLINE-BOUNDARY SPLITS -- expect CAUGHT (exit 1), same as an intact term")
        for name, sep in BOUNDARY_CASES.items():
            text = "signed off by {}{}{} on Tuesday\n".format(FIRST, sep, LAST)
            rc, out = scan_text(td, idf, text, name)
            report("split by {} ({!r}) -> should be caught (exit 1)".format(name, sep),
                   rc == 1, "got exit {}".format(rc))
            table.append(("split: {}".format(name), True, rc == 1, rc))

        print("\nHARD WRAP -- newline + leading indentation on the continuation")
        text = "signed off by {}\n    {} on Tuesday\n".format(FIRST, LAST)
        rc, out = scan_text(td, idf, text, "hard_wrap")
        report("hard-wrapped continuation -> should be caught (exit 1)", rc == 1,
               "got exit {}".format(rc))
        table.append(("split: hard wrap + indent", True, rc == 1, rc))

        print("\nPARAGRAPH BREAK -- a full blank line between the two halves")
        text = "signed off by {}\n\n{} on Tuesday\n".format(FIRST, LAST)
        rc, out = scan_text(td, idf, text, "paragraph_break")
        report("paragraph-break split -> should be caught (exit 1)", rc == 1,
               "got exit {}".format(rc))
        table.append(("split: paragraph break", True, rc == 1, rc))

        print("\nWINDOWS-PATH SHAPES -- a different hole: GENERIC_CONTENT_PATTERNS only "
              "has home-path-generic, '(?:/Users/|/home/)[A-Za-z0-9._-]+', which never "
              "matches a backslash path -- there is no Windows-path rule here at all")
        # ⛔ THE BACKSLASH IS BUILT AT RUNTIME, NEVER WRITTEN AS A LITERAL. A file that
        # spells out C:\Users\<name> or a UNC path FLAGS ITSELF against the very rules it
        # tests, and then no commit containing this file can pass the gate. Same trap the
        # baseline suite documents for operator-drive-cloudstorage and solves by generating
        # its terms; here the separator is generated instead. Runtime value is identical.
        _B = chr(92)
        text = "cd C:" + _B + "Users" + _B + FIRST + _B + "project\n"
        rc, out = scan_text(td, idf, text, "windows_drive_path")
        report("Windows drive-letter path (C:\\Users\\...) -> should be caught (exit 1)",
               rc == 1, "got exit {}".format(rc))
        table.append(("windows drive-letter path", True, rc == 1, rc))

        text = "see " + _B + _B + "fileserver" + _B + FIRST + _B + "Documents" + _B + "notes.txt\n"
        rc, out = scan_text(td, idf, text, "backslash_unc_path")
        report("bare backslash/UNC path -> should be caught (exit 1)", rc == 1,
               "got exit {}".format(rc))
        table.append(("bare backslash / UNC path", True, rc == 1, rc))

        print("\nSUMMARY TABLE -- case -> current behaviour -> expected after fix")
        print("  {:38s} {:10s} {}".format("case", "current", "expected"))
        for label, expected, actual, rc in table:
            cur = "CAUGHT" if actual else "MISSED"
            exp = "CAUGHT" if expected else "MISSED (control)"
            flag = "" if actual == expected else "  <-- RED (hole)"
            print("  {:38s} {:10s} {} (exit {}){}".format(label, cur, exp, rc, flag))

    print()
    if _failures:
        print("RED: {} case(s) failed -- {}".format(len(_failures), ", ".join(_failures)))
        return 1
    print("GREEN: every case matched expected (correct) behavior.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
