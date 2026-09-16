#!/usr/bin/env python3
"""check_drift.py — the register's ON-COMMIT RUNNER (Feature B3.2, enforcement-layer
Phase 2 plan). Calls `generate.py` by its CLI only — this file never imports or edits it
(nor `schema_v1.py` / `harvest.py` / `validate_register.py` / `omission_check.py` /
`caller_lint.py`).

D5 (Enver, 2026-09-15): the runner is ON-COMMIT — every commit regenerates the wiring from
the register and runs the FAST checks, refusing the commit on drift. The slow caller lint
(measured 8,247-8,362 ms, ~99% of `generate.py`'s runtime — see the plan's Discoveries,
"Runner cost, measured for D5") is deliberately EXCLUDED here (`--no-caller-lint`) and
instead runs in GitHub CI (`.github/workflows/register-drift.yml`), which can afford the
cost a human waiting on `git commit` cannot.

⛔ CORRECTED 2026-09-15, after a real Verify (b) FAILURE the lead reproduced (a planted
" #drift" suffix on a hook command was NOT caught). ROOT CAUSE, diagnosed against commit
`ce3e77e`: the first version of this tool called `harvest.py` FRESH, against the very
STAGED tree it was checking, before diffing. But `harvest.py` has no independent source
for a hook row's identity -- `hook_surfaces()` / `parse_hook_file()` read hook rows
straight OUT of `.claude/settings.json` and `hooks/hooks.json` themselves (there is no
separate hooks manifest on disk). So harvesting the STAGED (possibly hand-edited) copy of
those files and feeding the result straight back into `generate.py` is circular: whatever
a hand-edit changed becomes the new "truth" the harvester reports, and `generate.py`
dutifully reproduces exactly that edit. Confirmed empirically (scratchpad
`B3.2-drift-diagnosis.md`): a command-text edit round-tripped byte-for-byte once a test
artifact (a missing trailing newline) was corrected out of the way; a matcher-grouping
edit happened to be caught only as a side effect of a DIFFERENT rows' grouping, not
because the check validated the matcher itself. Both are the same underlying defect --
the checker had no fixed point external to the files it was checking.

THE FIX: the register is now a COMMITTED file, `system/register/register.jsonl` --
constraint 0.5 ("Register ... text, diffable, correctable" -- a human-openable file, which
only makes sense if one is actually persisted) plus the plan's own B1/B2 framing ("one
register reproduces all wiring") read literally: the register is the fixed point, and
`harvest.py` is the BOOTSTRAP/UPDATE tool a maintainer runs BY HAND when they intend to
change what is registered (see `FIX_COMMAND` below) -- never something this on-commit
checker invokes itself. Drift is now: does `generate.py` on the STAGED register (whatever
this commit says it is, register change included) reproduce the STAGED wiring EXACTLY? A
hand-edit to `.claude/settings.json` / `hooks/hooks.json` with no matching register change
now has a real, external reference to disagree with, so it is caught regardless of
formatting or which specific field changed. Adding/removing a governed script with no
register update is still caught too, but by `generate.py`'s OWN omission check (a fresh
disk walk cross-referenced against the SAME loaded register rows, `omission_check.py`,
already wired into `generate.py` -- Feature B1.4) -- nothing here duplicates that logic; a
second `harvest.py` call for that purpose would just reintroduce the same circularity for
no benefit, since the omission check already does not need a fresh harvest to work.

METHOD: this tool never touches the real working tree. It reads the CURRENTLY STAGED
INDEX (`git write-tree`, which is exactly what `git commit` is about to record) into a
throwaway checkout (`git archive | tar -x`) -- this necessarily includes whatever this
commit says `system/register/register.jsonl` is, register changes included -- then runs
`generate.py` against THAT checkout's copy of the register, and diffs the two governed
files' STAGED content (`git show :<path>`, read from the index directly) against what the
generator would install. Nothing here writes into the real repo; the temp checkout is
discarded (`shutil.rmtree`) on every exit path, pass or fail.

`--no-cache` on the generate call, on purpose: the plugin-cache-divergence check is a
same-content WARN inside `generate.py` (Feature B1.3), an orthogonal concern to wiring
drift, and reading a real, version-matched cache directory would make this tool's speed
and determinism depend on whether that cache happens to be present and current on this
machine. Skipping it keeps the on-commit path fast and self-contained; the cache-
divergence warning still fires in the normal (non-drift-check) uses of `generate.py` (its
own CLI, and the CI workflow).

⛔ SECOND CORRECTION 2026-09-15 (same day, after the fix above shipped). This tool refused
EVERY commit, independent of anything a given commit actually changed: `generate.py`'s exit
code conflated a PRIVATE target's own broken path (a private-repo hook file legitimately
deleted on THIS machine's `~/.claude/skills/ClaudeOps` checkout, commit `9aad44f`, with the
committed register not yet refreshed to match) into the SAME exit code this PUBLIC repo's
commit gate reads. A public commit gate must not depend on the private repo's live disk
state on whatever machine happens to run it. FIX: `generate.py` gained an additive,
backward-compatible `--targets {all,public}` flag (default "all", unchanged behavior
everywhere else); this tool now passes `--targets public`, which downgrades a REFUSED
PRIVATE target to a named, non-blocking WARN inside `generate.py`'s own report (still
visible in `gen_text` below) instead of refusing the whole run. This tool's OWN drift diff
(the `GOVERNED_FILES` loop, below) is unaffected — it only ever compared the two PUBLIC
wiring files anyway.

FAIL CLOSED, on purpose, matching this repo's existing `system/githooks/pre-commit`
precedent for a load-bearing check (gitleaks, check_no_internal_leakage.py): any internal
failure -- `git write-tree` refusing (e.g. unmerged paths), the archive step failing, a
missing sibling script, the committed register itself missing from the staged tree --
REFUSES the commit rather than silently letting it through. A drift checker that could not
check is not a drift checker that passed.

Usage:
    python3 check_drift.py [--repo-root PATH] [--severity {warn,refuse}] [--quiet]

Exit codes: 0 = no drift (or nothing to compare); 1 = drift found, or the check itself
could not complete (both are refusals -- see FAIL CLOSED above); each is distinguished in
the printed message, never in the exit code (a git hook only ever sees one bit).

Instrumentation for Verify (c), "the runner doesn't double-fire" -- inert unless a test
sets $LHB_DRIFT_COUNTER_FILE, so production runs never touch anything the flag doesn't
name: each invocation appends one line to that file. Not a feature; a way to prove, from
outside, how many times one `git commit` actually invoked this tool.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Two-repo governed pair this tool exists to protect (generate.py's own SURFACE_TARGETS
# "settings"/"plugin" rows -- the only two files `install_into_repo()` ever writes).
GOVERNED_FILES = (
    os.path.join(".claude", "settings.json"),
    os.path.join("hooks", "hooks.json"),
)

# The committed register -- the fixed point this whole check depends on. Relative to the
# repo root, same spelling on disk and inside the staged-tree checkout.
REGISTER_REL_PATH = os.path.join("system", "register", "register.jsonl")


def _counter_tick():
    path = os.environ.get("LHB_DRIFT_COUNTER_FILE")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{os.getpid()}\n")
    except OSError:
        pass  # instrumentation must never be why a commit fails


def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, **kwargs)


def _git_toplevel():
    out = _run(["git", "rev-parse", "--show-toplevel"])
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace").strip()


def _git_write_tree(repo_root):
    out = _run(["git", "write-tree"], cwd=repo_root)
    if out.returncode != 0:
        return None, out.stderr.decode("utf-8", "replace")
    return out.stdout.decode("utf-8", "replace").strip(), None


def _git_show_staged(repo_root, rel_path):
    """Return the INDEX content of rel_path as bytes, or None if it is not staged
    (unborn path, or genuinely absent -- both treated the same by the caller: nothing
    to compare)."""
    out = _run(["git", "show", f":{rel_path}"], cwd=repo_root)
    if out.returncode != 0:
        return None
    return out.stdout


def _materialize_tree(repo_root, tree_sha, dest_dir):
    archive = _run(["git", "archive", "--format=tar", tree_sha], cwd=repo_root)
    if archive.returncode != 0:
        return archive.stderr.decode("utf-8", "replace")
    extract = subprocess.run(
        ["tar", "-xf", "-", "-C", dest_dir],
        input=archive.stdout,
        capture_output=True,
    )
    if extract.returncode != 0:
        return extract.stderr.decode("utf-8", "replace")
    return None


def _read_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


# The legitimate way to CHANGE what is registered: re-derive the committed register from
# an intentional disk state (harvest.py, run BY HAND, never by this checker), regenerate
# the wiring to match it, then commit the register change and the regenerated wiring
# together. This is deliberately a two-file, one-commit workflow -- a wiring edit with no
# matching register edit is exactly the drift this tool exists to refuse.
FIX_COMMAND = (
    "python3 system/register/harvest.py --out system/register/register.jsonl && "
    "python3 system/register/generate.py system/register/register.jsonl "
    "--out /tmp/lhb-gen-out --install-root ."
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo-root", default=None,
                   help="repo root to check (default: `git rev-parse --show-toplevel` "
                        "from the current directory -- correct for a pre-commit hook, "
                        "which git always runs with cwd at the worktree root)")
    p.add_argument("--severity", choices=("warn", "refuse"), default="warn",
                   help="forwarded to generate.py's omission check (Feature B1.4; Enver's "
                        "ruling, 2026-09-15: default WARN). 'refuse' makes an omission "
                        "finding (a governed-folder script with no register row) refuse "
                        "the commit through generate.py's own exit code -- this tool adds "
                        "no separate omission logic, and no separate harvest, of its own.")
    p.add_argument("--quiet", action="store_true",
                   help="suppress the pass-through generate.py report on a clean pass "
                        "(always shown on drift/refusal)")
    args = p.parse_args(argv)

    _counter_tick()

    repo_root = args.repo_root or _git_toplevel()
    if not repo_root:
        print("  ⛔ check_drift.py: could not resolve the repo root "
              "(`git rev-parse --show-toplevel` failed). Refusing.", file=sys.stderr)
        return 1
    repo_root = os.path.abspath(repo_root)

    generate_py = os.path.join(THIS_DIR, "generate.py")
    if not os.path.isfile(generate_py):
        print(f"  ⛔ check_drift.py: {generate_py} is missing. The drift check "
              "cannot run. Refusing (fail closed).", file=sys.stderr)
        return 1

    tree_sha, err = _git_write_tree(repo_root)
    if tree_sha is None:
        print("  ⛔ check_drift.py: `git write-tree` failed on the staged index "
              "(unmerged paths?). Refusing.", file=sys.stderr)
        if err:
            print(err, file=sys.stderr)
        return 1

    staged_before = {
        rel: _git_show_staged(repo_root, rel.replace(os.sep, "/"))
        for rel in GOVERNED_FILES
    }
    staged_register = _git_show_staged(repo_root, REGISTER_REL_PATH.replace(os.sep, "/"))
    if staged_register is None:
        print(f"  ⛔ check_drift.py: {REGISTER_REL_PATH} is not staged/committed. "
              "The register is this tool's fixed point -- without it there is nothing "
              "independent to check the wiring against. Refusing (fail closed).",
              file=sys.stderr)
        return 1

    tmp_dir = tempfile.mkdtemp(prefix="lhb-drift-")
    try:
        materialize_err = _materialize_tree(repo_root, tree_sha, tmp_dir)
        if materialize_err:
            print("  ⛔ check_drift.py: could not materialize the staged tree "
                  "into a scratch checkout. Refusing.", file=sys.stderr)
            print(materialize_err, file=sys.stderr)
            return 1

        register_path = os.path.join(tmp_dir, REGISTER_REL_PATH)
        if not os.path.isfile(register_path):
            print(f"  ⛔ check_drift.py: {REGISTER_REL_PATH} did not materialize "
                  "into the staged-tree checkout. Refusing.", file=sys.stderr)
            return 1

        gen_out_dir = os.path.join(tmp_dir, "_lhb_gen_out")
        generate_result = _run([
            sys.executable, generate_py,
            register_path,
            "--no-caller-lint",
            "--no-cache",
            "--severity", args.severity,
            "--out", gen_out_dir,
            "--install-root", tmp_dir,
            "--public-root", tmp_dir,
            # B3.2 fix, 2026-09-15: this is a PUBLIC repo commit gate. It must
            # refuse on PUBLIC wiring drift (the thing it exists for) but must
            # NOT refuse because the PRIVATE repo's checkout on THIS machine
            # is stale or incomplete (this tool does not even pass
            # --private-root -- it relies on generate.py's own default,
            # `~/.claude/skills/ClaudeOps`, live on whatever machine runs
            # this hook). A REFUSED private target becomes a named, printed
            # WARN inside generate.py's own report (see gen_text below) --
            # never a reason to block a public commit.
            "--targets", "public",
        ])
        gen_text = (generate_result.stdout.decode("utf-8", "replace")
                    + generate_result.stderr.decode("utf-8", "replace"))

        if generate_result.returncode != 0:
            print("  ⛔ COMMIT REFUSED — generate.py refused against the staged "
                  "register (schema problem, a broken PUBLIC path, or an omission "
                  "at --severity refuse). A private-target path issue alone would "
                  "NOT trigger this (see --targets public above) -- this is a real "
                  "public-repo finding.", file=sys.stderr)
            print(gen_text, file=sys.stderr)
            print("", file=sys.stderr)
            print(f"  Fix: {FIX_COMMAND}", file=sys.stderr)
            print("", file=sys.stderr)
            return 1

        drifted = []
        for rel in GOVERNED_FILES:
            before = staged_before[rel]
            after = _read_bytes(os.path.join(tmp_dir, rel))
            if before != after:
                drifted.append(rel)

        if drifted:
            print("  ⛔ COMMIT REFUSED — the staged wiring has drifted from what "
                  "the committed register (system/register/register.jsonl, as staged) "
                  "generates.", file=sys.stderr)
            print("", file=sys.stderr)
            print("  Drifting file(s):", file=sys.stderr)
            for rel in drifted:
                print(f"      {rel.replace(os.sep, '/')}", file=sys.stderr)
            print("", file=sys.stderr)
            print("  Either the wiring was hand-edited without updating the register, or "
                  "a governed script changed without re-harvesting. Fix:", file=sys.stderr)
            print(f"      {FIX_COMMAND}", file=sys.stderr)
            print("  Then re-stage the register AND the two files it rewrote, and commit "
                  "again.", file=sys.stderr)
            print("", file=sys.stderr)
            return 1

        # A non-blocking private-target finding (targets=public mode, above)
        # is real information — a stale private row a maintainer should still
        # refresh — even though it never refuses this PUBLIC commit. Surface
        # it on the OK path too (never only on failure), always (not gated on
        # --quiet): a WARN nobody sees is the exact "reported success while
        # producing nothing observable" failure shape hook-sop.md's own
        # DO-NOT-BUILD register warns against.
        if "WARN — non-blocking private-target" in gen_text:
            warn_start = gen_text.index("WARN — non-blocking private-target")
            print(gen_text[warn_start:].rstrip())
            print("")

        # S1/K1 (2026-09-16): surface the switch's ALARM and NOTICE on the OK
        # path too — the drift check itself must alarm loudly when a suspension
        # has expired (Enver's stamped constraint), and a legitimately-honored
        # one must be visible. generate.py prints each section ending with a
        # blank line; slice marker -> next "\n\n" to avoid printing unrelated
        # sections.
        for marker in ("ALARM — register suspension", "NOTICE — register-declared suspension"):
            if marker in gen_text:
                start = gen_text.index(marker)
                end = gen_text.find("\n\n", start)
                section = gen_text[start:] if end == -1 else gen_text[start:end]
                print(section.rstrip())
                print("")

        if not args.quiet:
            print("  check_drift.py: OK — staged wiring matches the committed "
                  "register.")
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
