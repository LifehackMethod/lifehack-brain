#!/usr/bin/env python3
"""test_check_no_internal_leakage.py -- the guard rails for issue #59's fix.

WHY THIS FILE EXISTS. check_no_internal_leakage.py used to carry the operator's identity as
six literal regex patterns and, because a pattern-matcher self-flags on its own patterns,
it exempted its own directory from its own content scan. The one file guaranteed to contain
the identity was the one file the scanner could never read, and a whole-tree scan reported
CLEAN on 2026-08-15 for exactly that reason. The fix moved rule 3 out to the shipping
lane's out-of-repo identity file and deleted the exemption.

Every property that fix depends on is fragile in a specific, nameable way, and each one has
a test below:
  1. NO IDENTITY -> EXIT 2, NOT EXIT 0. The whole failure mode being fixed is a scanner
     that reports clean because it has nothing to look for. If this test ever goes green on
     exit 0, the fix has inverted into the bug.
  2. IT STILL CATCHES A REAL LEAK. A scanner that catches nothing passes every other test
     in this file.
  3. THE TERM IS NEVER PRINTED. Findings go into a PUBLIC build log and a PUBLIC artifact.
     A gate that prints what it found has moved the leak, not closed it.
  4. THE SCANNER'S OWN FILE SCANS CLEAN. This is what makes deleting the .github/ exemption
     safe, and it rests on the `[-]` character class in the operator-drive-cloudstorage
     pattern. Someone will eventually "tidy" that to a bare `-`; this test is why that
     shows up as a red test instead of a mysteriously red CI on an unrelated PR.

⛔ NO REAL IDENTITY IS IN THIS FILE. The terms below are invented for this test and are
asserted, at run time, to appear nowhere in the scanner. That assertion is not decoration:
a test whose fixture collides with real repo content proves nothing about either.
"""
import json
import os
import subprocess
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
SCANNER = os.path.join(HERE, "check_no_internal_leakage.py")
SCANNER_RELPATH = ".github/scripts/check_no_internal_leakage.py"

# Invented. Not a person. Chosen to be absent from this repo -- see test_fixture_is_inert.
FAKE_TERMS = ["Quilfeather", "Vronsketch", "quilfeather.v@example.invalid"]

_failures = []


def report(label, passed, detail=""):
    print("  [{}] {}{}".format("PASS" if passed else "FAIL", label,
                               (" -- " + detail) if detail else ""))
    if not passed:
        _failures.append(label)


_SANDBOX_NOTES = None  # a REAL, EMPTY directory -- see run_scanner


def run_scanner(args, env=None):
    """Returns (returncode, stdout+stderr). Runs from REPO_ROOT so git-backed modes work.

    ⚠ THE ENV SCRUB IS LOAD-BEARING. Left alone, brain_root's resolver would fall through
    $LIFEHACK_ROOT to the persisted ~/.config/lifehack/brain-root and find the operator's
    REAL identity file -- which would make these results machine-dependent and would put a
    real term inside a test run. $LIFEHACK_ROOT is pointed at a real but EMPTY directory
    (a nonexistent one is ignored by the resolver, which is the trap), and $SHIP_IDENTITY
    is dropped."""
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


def main():
    global _SANDBOX_NOTES
    print("test_check_no_internal_leakage.py")
    scanner_src = open(SCANNER, encoding="utf-8").read()

    with tempfile.TemporaryDirectory() as td:
        _SANDBOX_NOTES = os.path.join(td, "empty-notes-root")
        os.makedirs(_SANDBOX_NOTES)
        idf = os.path.join(td, "ship-identity.md")
        write_identity(idf, FAKE_TERMS)

        # ------------------------------------------------- the fixture is genuinely inert
        print("\nFIXTURE HYGIENE")
        collisions = [t for t in FAKE_TERMS if t.lower() in scanner_src.lower()]
        report("the invented terms appear nowhere in the scanner", not collisions,
               "collides: {}".format(collisions))

        # ------------------------------------------------- 1. fail loudly, never silently
        print("\nFAIL-CLOSED -- the half that matters most")
        rc, out = run_scanner(["--identity", os.path.join(td, "does-not-exist.md"),
                               "--scan-file", SCANNER, "--as-path", SCANNER_RELPATH])
        report("a missing identity file -> exit 2, NOT exit 0", rc == 2, "got exit {}".format(rc))
        report("...and the refusal says the run was not a clean scan",
               "CANNOT EVALUATE" in out and "NOT a clean scan" in out)
        report("...and it names how to fix it on a runner", "SHIP_IDENTITY" in out)
        # the ONLY "CLEAN" allowed in that output is identity_rules' own warning about what
        # a missing identity file would otherwise cause -- never this script's own verdict.
        report("...and it never prints its own clean verdict",
               "NO-INTERNAL-LEAKAGE: clean" not in out and "0 BLOCKING" not in out)

        empty = os.path.join(td, "empty-identity.md")
        with open(empty, "w") as fh:
            fh.write("# only a comment\n\n")
        rc, out = run_scanner(["--identity", empty, "--scan-file", SCANNER,
                               "--as-path", SCANNER_RELPATH])
        report("an identity file with no usable terms -> exit 2", rc == 2,
               "got exit {}".format(rc))

        rc, out = run_scanner(["--identity", os.path.join(td, "does-not-exist.md"),
                               "--whole-tree"])
        report("whole-tree mode fails closed the same way", rc == 2, "got exit {}".format(rc))

        # ------------------------------------------------- 2. it still catches a real leak
        print("\nDETECTION -- a scanner that catches nothing passes every other test")
        leak = os.path.join(td, "planted.md")
        with open(leak, "w", encoding="utf-8") as fh:
            fh.write("# notes\nsigned off by {} on Tuesday\n".format(FAKE_TERMS[0]))
        rc, out = run_scanner(["--identity", idf, "--scan-file", leak,
                               "--as-path", "docs/planted.md"])
        report("a planted identity term -> exit 1 (FLAGGED)", rc == 1, "got exit {}".format(rc))
        report("...and the finding uses an OPAQUE rule id", "operator-identity-" in out)

        # the same term inside an email local-part -- a bounded word rule alone cannot see
        # this (the character to its left is alphanumeric), which is why load_identity_
        # patterns() emits a second, email-shaped rule per word term.
        leak2 = os.path.join(td, "planted2.md")
        with open(leak2, "w", encoding="utf-8") as fh:
            fh.write("contact: x{}99@corp.example\n".format(FAKE_TERMS[1].lower()))
        rc, out = run_scanner(["--identity", idf, "--scan-file", leak2,
                               "--as-path", "docs/planted2.md"])
        report("a term buried in an email local-part -> exit 1", rc == 1,
               "got exit {}".format(rc))

        # the generic tier must keep working independently of the identity tier
        leak3 = os.path.join(td, "planted3.md")
        with open(leak3, "w", encoding="utf-8") as fh:
            # ⚠ ASSEMBLED, NOT WRITTEN WHOLE, for the same reason the scanner's own
            # cloud-drive pattern uses a `[-]` class: a positive fixture for a home-path
            # rule, written as one literal, makes THIS FILE trip that rule the moment it is
            # committed. Split across the concatenation, no line here contains the shape.
            fh.write("cd /Users/" + "somebodyelse/project\n")
        rc, out = run_scanner(["--identity", idf, "--scan-file", leak3,
                               "--as-path", "docs/planted3.md"])
        report("the generic home-path rule still fires", rc == 1 and "home-path-generic" in out,
               "got exit {}".format(rc))

        rc, out = run_scanner(["--identity", idf, "--scan-file", leak3,
                               "--as-path", "migration-audit/x.md"])
        report("the path denylist still fires", rc == 1 and "migration-audit-dir" in out,
               "got exit {}".format(rc))

        # ------------------------------------------------- 3. the term is never printed
        print("\nREDACTION -- the log and the artifact are PUBLIC")
        rc, out = run_scanner(["--identity", idf, "--scan-file", leak,
                               "--as-path", "docs/planted.md"])
        report("the matched term is NOT echoed into the output",
               FAKE_TERMS[0].lower() not in out.lower())
        report("...it is replaced by an explicit marker", "[REDACTED]" in out)
        report("...and surrounding context survives, so it is still findable",
               "on Tuesday" in out)

        # ⚠ THE REGRESSION THAT ALMOST SHIPPED. Two terms on one line produce two findings.
        # Redacting each finding against only ITS OWN rule leaves the other term visible in
        # that finding, and the two printed lines reassemble the full name. See
        # redact_spans() -- it applies every identity rule to every evidence line.
        leak_pair = os.path.join(td, "planted_pair.md")
        with open(leak_pair, "w", encoding="utf-8") as fh:
            fh.write("signed off by {} {} on Tuesday\n".format(FAKE_TERMS[0], FAKE_TERMS[1]))
        rc, out = run_scanner(["--identity", idf, "--scan-file", leak_pair,
                               "--as-path", "docs/planted_pair.md"])
        report("two terms on one line -> both flagged", rc == 1 and out.count("::error") == 2,
               "exit {}".format(rc))
        report("...and NEITHER term survives in ANY of the printed findings",
               FAKE_TERMS[0].lower() not in out.lower()
               and FAKE_TERMS[1].lower() not in out.lower())

        # ...and the same for whole-tree mode's finding dicts, which are what gets
        # serialized into the uploaded JSON artifact. Driven in-process (scan_whole_tree
        # takes its own file list) so the test never has to add an untracked file to the
        # real checkout just to be scanned.
        planted_rel = "__leak_probe_test__.md"
        planted_abs = os.path.join(REPO_ROOT, planted_rel)
        sys.path.insert(0, HERE)
        import check_no_internal_leakage as chk           # noqa: E402
        try:
            with open(planted_abs, "w", encoding="utf-8") as fh:
                fh.write("owner: {}\n".format(FAKE_TERMS[0]))
            cwd = os.getcwd()
            os.chdir(REPO_ROOT)
            try:
                chk.install_identity_patterns(idf)
                result = chk.scan_whole_tree(scan_root_paths=[planted_rel])
            finally:
                os.chdir(cwd)
            blob = json.dumps(result)
            report("whole-tree catches a planted leak", len(result["blocking"]) >= 1,
                   "{} blocking".format(len(result["blocking"])))
            report("the serialized report does NOT carry the term",
                   FAKE_TERMS[0].lower() not in blob.lower())
            report("...it carries the redaction marker instead", "[REDACTED]" in blob)
        finally:
            if os.path.exists(planted_abs):
                os.remove(planted_abs)

        # ------------------------------------------------- 4. the scanner self-scans clean
        print("\nSELF-SCAN -- what makes deleting the .github/ exemption safe")
        rc, out = run_scanner(["--identity", idf, "--scan-file", SCANNER,
                               "--as-path", SCANNER_RELPATH])
        report("the scanner's own source scans CLEAN (no .github/ exemption needed)",
               rc == 0, "exit {}: {}".format(rc, out.strip()[:400]))
        report("...specifically: operator-drive-cloudstorage does not match its own "
               "pattern line (the `[-]` class -- do not 'tidy' it)",
               "operator-drive-cloudstorage" not in out)

        # ...and so must THIS file: a test full of positive fixtures is the next most
        # likely thing in .github/ to self-flag now that the exemption is gone.
        #
        # ⚠ SCANNED AGAINST A THIRD-PARTY IDENTITY (idf2), NOT ITS OWN (idf), AND THAT IS
        # NOT A DODGE. This file necessarily CONTAINS FAKE_TERMS -- they are its fixtures --
        # so scanning it against an identity made of FAKE_TERMS asks "does the fixture
        # contain the fixture?", which is trivially yes and tells us nothing. The real
        # question is the one CI actually asks: does this file contain SOMEONE'S identity
        # terms? idf2's terms are unrelated to everything here, which is the honest form of
        # that question. (Verified separately against the machine's real identity file: also
        # clean.)
        #
        # ⭐ idf2's TERMS ARE GENERATED, NOT TYPED, and that is the whole trick. Any term
        # written literally here would, by existing on this line, be found on this line --
        # the file would flag itself against its own fixture no matter which words were
        # chosen. Random tokens are the only identity guaranteed to be absent from a file
        # that has to contain its own fixtures.
        idf2 = os.path.join(td, "other-identity.md")
        rnd = uuid.uuid4().hex[:10]
        write_identity(idf2, ["Zq" + rnd, "Vx" + rnd, "a.b" + rnd + "@example.invalid"])
        rc, out = run_scanner(["--identity", idf2, "--scan-file", os.path.abspath(__file__),
                               "--as-path", ".github/scripts/" + os.path.basename(__file__)])
        report("this test file scans CLEAN too", rc == 0,
               "exit {}: {}".format(rc, out.strip()[:400]))

        for wf in sorted(os.listdir(os.path.join(REPO_ROOT, ".github", "workflows"))):
            rel = ".github/workflows/" + wf
            rc, out = run_scanner(["--identity", idf, "--scan-file",
                                   os.path.join(REPO_ROOT, rel), "--as-path", rel])
            report("{} scans CLEAN".format(rel), rc == 0, "exit {}".format(rc))

        # ------------------------------------------------- no identity literal survives
        print("\nNO IDENTITY LITERAL IS LEFT IN THE SCANNER")
        # The deleted rules were named operator-email-*/operator-name-*/operator-github-*.
        # Their ABSENCE is the acceptance criterion of issue #59; rule 3 now has exactly one
        # id shape and it is generated, not written.
        for dead in ("operator-email-primary", "operator-email-any", "operator-name-",
                     "operator-github-handle"):
            report("no {!r} remains".format(dead), dead not in scanner_src)
        # the exemption must be gone as CODE. It is still discussed in a comment on purpose
        # -- deleting a guard without leaving the reasoning behind is how it gets re-added.
        live = [ln for ln in scanner_src.splitlines()
                if ln.startswith("CONTENT_SCAN_EXCLUDE_PREFIX")]
        report("the .github/ content-scan exemption is gone as executable code", not live,
               "still assigned at: {}".format(live))

    print("")
    if _failures:
        print("FAIL -- {} check(s): {}".format(len(_failures), "; ".join(_failures)))
        return 1
    print("PASS -- every check green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
