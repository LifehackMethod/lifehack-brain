#!/usr/bin/env python3
"""check_drift.py — the register's ON-COMMIT RUNNER (Feature B3.2, enforcement-layer
Phase 2 plan). Calls `harvest.py` and `generate.py` by their CLI only — this file never
imports or edits either (they, `schema_v1.py`, `validate_register.py`, `omission_check.py`
and `caller_lint.py` are a parallel helper's territory during this build window).

D5 (Enver, 2026-09-15): the runner is ON-COMMIT — every commit regenerates the wiring from
the register and runs the FAST checks, refusing the commit on drift. The slow caller lint
(measured 8,247-8,362 ms, ~99% of `generate.py`'s runtime — see the plan's Discoveries,
"Runner cost, measured for D5") is deliberately EXCLUDED here (`--no-caller-lint`) and
instead runs in GitHub CI (`.github/workflows/register-drift.yml`), which can afford the
cost a human waiting on `git commit` cannot.

WHAT "DRIFT" MEANS HERE: the two files the generator is the ONLY allowed writer of --
`.claude/settings.json` and `hooks/hooks.json` (`generate.py`'s own `install_into_repo()`
docstring) -- diverging from what the register would regenerate for them right now. That
happens two ways: (a) someone hand-edits one of those files directly, or (b) a governed
script is added/moved/deleted on disk without re-running the generator. Either way the
committed wiring would stop matching the source of truth the moment this commit lands.

METHOD: this tool never touches the real working tree. It reads the CURRENTLY STAGED
INDEX (`git write-tree`, which is exactly what `git commit` is about to record) into a
throwaway checkout, harvests + generates THERE, and diffs the two governed files' STAGED
content (`git show :<path>`, read from the index directly -- not the temp copy, which is
merely a vehicle for path resolution) against what the generator would install. Nothing
here writes into the real repo; the temp checkout is discarded (`shutil.rmtree`) on every
exit path, pass or fail.

`--no-cache` on both calls, on purpose: the plugin-cache-divergence check is a same-content
WARN inside `generate.py` (Feature B1.3), an orthogonal concern to wiring drift, and reading
a real, version-matched cache directory would make this tool's speed and determinism depend
on whether that cache happens to be present and current on this machine. Skipping it keeps
the on-commit path fast and self-contained; the cache-divergence warning still fires in the
normal (non-drift-check) uses of `generate.py` (its own CLI, and the CI workflow).

FAIL CLOSED, on purpose, matching this repo's existing `system/githooks/pre-commit`
precedent for a load-bearing check (gitleaks, check_no_internal_leakage.py): any internal
failure -- `git write-tree` refusing (e.g. unmerged paths), the archive step failing, a
missing sibling script -- REFUSES the commit rather than silently letting it through. A
drift checker that could not check is not a drift checker that passed.

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


FIX_COMMAND = (
    "python3 system/register/harvest.py --out /tmp/lhb-register.jsonl && "
    "python3 system/register/generate.py /tmp/lhb-register.jsonl "
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
                        "finding refuse the commit through generate.py's own exit code -- "
                        "this tool adds no separate omission logic of its own.")
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

    harvest_py = os.path.join(THIS_DIR, "harvest.py")
    generate_py = os.path.join(THIS_DIR, "generate.py")
    for script in (harvest_py, generate_py):
        if not os.path.isfile(script):
            print(f"  ⛔ check_drift.py: {script} is missing. The drift check "
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

    tmp_dir = tempfile.mkdtemp(prefix="lhb-drift-")
    try:
        materialize_err = _materialize_tree(repo_root, tree_sha, tmp_dir)
        if materialize_err:
            print("  ⛔ check_drift.py: could not materialize the staged tree "
                  "into a scratch checkout. Refusing.", file=sys.stderr)
            print(materialize_err, file=sys.stderr)
            return 1

        register_path = os.path.join(tmp_dir, "_lhb_register.jsonl")
        harvest_out = _run([
            sys.executable, harvest_py,
            "--public-root", tmp_dir,
            "--no-cache",
            "--out", register_path,
        ])
        if harvest_out.returncode != 0:
            print("  ⛔ check_drift.py: harvest.py failed against the staged tree. "
                  "Refusing.", file=sys.stderr)
            print(harvest_out.stdout.decode("utf-8", "replace"), file=sys.stderr)
            print(harvest_out.stderr.decode("utf-8", "replace"), file=sys.stderr)
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
        ])
        gen_text = (generate_result.stdout.decode("utf-8", "replace")
                    + generate_result.stderr.decode("utf-8", "replace"))

        if generate_result.returncode != 0:
            print("  ⛔ COMMIT REFUSED — generate.py refused against the staged "
                  "wiring (schema problem, a broken path, or an omission at "
                  "--severity refuse).", file=sys.stderr)
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
                  "the register would generate.", file=sys.stderr)
            print("", file=sys.stderr)
            print("  Drifting file(s):", file=sys.stderr)
            for rel in drifted:
                print(f"      {rel.replace(os.sep, '/')}", file=sys.stderr)
            print("", file=sys.stderr)
            print(f"  Fix: {FIX_COMMAND}", file=sys.stderr)
            print("  Then re-stage the two files it rewrote and commit again.",
                  file=sys.stderr)
            print("", file=sys.stderr)
            return 1

        if not args.quiet:
            print("  check_drift.py: OK — staged wiring matches the register.")
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
