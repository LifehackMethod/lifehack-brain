#!/usr/bin/env python3
"""test_line_boundary_bypass_scrub.py -- adversarial fixture harness for the line-boundary
hole in scrub.py, the shipping lane's own tree-walker.

WHY THIS FILE EXISTS. scrub.py compiles the operator-identity ("2-private") tier the same
way check_no_internal_leakage.py does: one term-per-line in an out-of-repo identity file,
via `identity_rules.compile_term()`, one `re.escape(term)` regex per term with a literal
space where a multi-word term (e.g. a full name) has a space. `hits_for_rule()` runs
`rx.finditer(text)` over the WHOLE staged file text, not a per-line loop -- but a term
whose two words are separated by an actual line-boundary byte in the scanned file is no
longer the same bytes as `re.escape("First Last")` describes (a literal space), so the
regex fails to match the split text regardless of finditer's scope. This is the SAME root
cause as the check_no_internal_leakage.py hole (see test_line_boundary_bypass.py, its
sibling in .github/scripts/), reached through a different interface: scrub.py takes
--manifest/--tree/--identity/--selftest, not --scan-file/--as-path.

⛔ THIS HARNESS ASSERTS THE CORRECT (DESIRED) BEHAVIOR, NOT TODAY'S BUGGY ONE -- every
split-term case below expects the file to come back NOT-CLEAN, the same way an intact term
does. Run against TODAY's unmodified scrub.py, the split-term assertions are EXPECTED TO
FAIL (red). A separate task fixes the scanner; when it does, this file goes green with NO
EDITS.

⛔ ALSO COVERS: scrub.py's `refuse-rules.json` DOES carry a Windows-drive-path rule
(`path-home-windows`, tier 1-identity, no "to") that check_no_internal_leakage.py's
GENERIC_CONTENT_PATTERNS has NO equivalent of at all -- so the two gates are NOT
symmetric on that one shape. This file's Windows-path cases assert scrub.py's actual
(already-correct) behavior as a CONTROL, not a red case -- see WINDOWS-PATH section below.

⛔ NO REAL IDENTITY IS IN THIS FILE. FAKE_TERM below is invented for this test.

Idiom matches scrub.py's own --selftest and test_check_no_internal_leakage.py: no
unittest, a procedural main() with a report(label, passed, detail) tally, and a nonzero
process exit on any failure so run-all-tests.sh's plain `python3 <file>` / exit-code
contract keeps working unmodified.

⚠ FIXTURE PLACEMENT. scrub.py's `--manifest` containment check requires every listed path
to resolve INSIDE REPO_ROOT (the real git clone), so this harness's fixture files live in a
tempdir created with `dir=HERE` (system/shipping-lane/), exactly the way scrub.py's own
--selftest does it (see `fixture_root = tempfile.mkdtemp(dir=HERE, ...)`), and are removed
in a `finally` block. Nothing here is committed.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.realpath(os.path.join(HERE, "..", ".."))
SCRUB = os.path.join(HERE, "scrub.py")

FAKE_TERM = "Bramblecross Thistlewood"
FIRST, LAST = FAKE_TERM.split(" ")

_failures = []


def report(label, passed, detail=""):
    print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                               (" -- " + detail) if detail else ""))
    if not passed:
        _failures.append(label)


def write_identity(path, terms):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# invented test identity -- nobody real is in this file\n")
        for t in terms:
            fh.write(t + "\n")


def run_scrub(manifest, identity, staging, sandbox_notes, extra_env=None):
    e = dict(os.environ)
    e.pop("SHIP_IDENTITY", None)
    e["LIFEHACK_ROOT"] = sandbox_notes
    if extra_env:
        e.update(extra_env)
    args = [sys.executable, SCRUB, "--manifest", manifest, "--identity", identity,
            "--staging", staging, "--json"]
    p = subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT, env=e)
    return p.returncode, p.stdout, p.stderr


def rel(p):
    return os.path.relpath(p, REPO_ROOT)


def main():
    print("test_line_boundary_bypass_scrub.py -- attacking scrub.py")
    print("(RED FIRST: split-term cases are EXPECTED TO FAIL against unfixed code -- see "
          "module docstring)")
    scrub_src = open(SCRUB, encoding="utf-8").read()

    print("\nFIXTURE HYGIENE")
    collisions = [t for t in (FAKE_TERM, FIRST, LAST) if t.lower() in scrub_src.lower()]
    report("the invented term appears nowhere in scrub.py", not collisions,
           "collides: {}".format(collisions))

    boundary_cases = {
        "lf": "\n",
        "crlf": "\r\n",
        "u2028_line_separator": "\u2028",
        "u2029_paragraph_separator": "\u2029",
        "vtab_0x0b": "\v",
        "formfeed_0x0c": "\f",
        "nel_0x85": "\x85",
    }

    with tempfile.TemporaryDirectory() as td:
        sandbox_notes = os.path.join(td, "empty-notes-root")
        os.makedirs(sandbox_notes)
        idf = os.path.join(td, "ship-identity.md")
        write_identity(idf, [FAKE_TERM])

        fixture_root = tempfile.mkdtemp(dir=HERE, prefix=".line-boundary-fixtures-")
        try:
            def write_fixture(relpath, text):
                p = os.path.join(fixture_root, relpath)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(text)
                return p

            files = {}
            files["control: intact term, one line"] = (
                write_fixture("control_intact.md",
                              "signed off by {} on Tuesday\n".format(FAKE_TERM)), True)
            files["control: genuinely clean file"] = (
                write_fixture("control_clean.md",
                              "nothing sensitive is written in this file at all.\n"), False)
            for name, sep in boundary_cases.items():
                files["split: {}".format(name)] = (
                    write_fixture("split_{}.md".format(name),
                                  "signed off by {}{}{} on Tuesday\n".format(
                                      FIRST, sep, LAST)), True)
            files["split: hard wrap + indent"] = (
                write_fixture("hard_wrap.md",
                              "signed off by {}\n    {} on Tuesday\n".format(
                                  FIRST, LAST)), True)
            files["split: paragraph break"] = (
                write_fixture("paragraph_break.md",
                              "signed off by {}\n\n{} on Tuesday\n".format(
                                  FIRST, LAST)), True)
            _B = chr(92)   # built at runtime; a literal would flag this file. See sibling harness.
            # WINDOWS-PATH -- refuse-rules.json's path-home-windows rule already covers
            # this shape, so this is a CONTROL (expected NOT-CLEAN today), not a red case.
            files["windows drive-letter path (control -- already caught)"] = (
                write_fixture("windows_drive.md",
                              "cd C:" + _B + "Users" + _B + FIRST + _B
                              + "project\n"), True)
            # No refuse rule covers a bare backslash/UNC path without a drive letter +
            # "Users" -- this one really is expected-missed by scrub.py too.
            files["bare backslash / UNC path"] = (
                write_fixture("backslash_unc.md",
                              "see " + _B + _B + "fileserver" + _B + FIRST + _B
                              + "Documents" + _B + "notes.txt\n"), True)

            manifest = os.path.join(fixture_root, "manifest.txt")
            with open(manifest, "w", encoding="utf-8") as fh:
                fh.write("# line-boundary-bypass manifest\n")
                for path, _expected in files.values():
                    fh.write(rel(path) + "\n")

            staging = tempfile.mkdtemp(prefix="line-boundary-bypass-staging-")
            rc, out, err = run_scrub(manifest, idf, staging, sandbox_notes)
            if rc == 2:
                report("scrub.py ran to completion (not CANNOT EVALUATE)", False,
                       "exit 2: {}".format(err.strip()[:400]))
                print("\nRED: scrub.py refused to evaluate -- see detail above")
                return 1

            try:
                report_obj = json.loads(out)
            except json.JSONDecodeError as e:
                report("scrub.py --json produced parseable JSON", False,
                       "{}: {!r}".format(e, out[:400]))
                return 1

            by_source = {f["source"]: f for f in report_obj["files"]}
            table = []
            for label, (path, expected_not_clean) in files.items():
                source = rel(path)
                f = by_source.get(source)
                if f is None:
                    report(label, False, "no report entry for {!r}".format(source))
                    table.append((label, expected_not_clean, None, "MISSING"))
                    continue
                actually_not_clean = (f["status"] != "CLEAN")
                report("{} -> expect {} (exit-status NOT-CLEAN={})".format(
                           label, "NOT-CLEAN" if expected_not_clean else "CLEAN",
                           expected_not_clean),
                       actually_not_clean == expected_not_clean,
                       "got status={}".format(f["status"]))
                table.append((label, expected_not_clean, actually_not_clean, f["status"]))

            print("\nSUMMARY TABLE -- case -> current behaviour -> expected after fix")
            print("  {:55s} {:10s} {}".format("case", "current", "expected"))
            for label, expected, actual, status in table:
                exp = "NOT-CLEAN" if expected else "CLEAN"
                flag = "" if actual == expected else "  <-- RED (hole)"
                print("  {:55s} {:10s} {}{}".format(label, status, exp, flag))
        finally:
            import shutil
            shutil.rmtree(fixture_root, ignore_errors=True)

    print()
    if _failures:
        print("RED: {} case(s) failed -- {}".format(len(_failures), ", ".join(_failures)))
        return 1
    print("GREEN: every case matched expected (correct) behavior.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
