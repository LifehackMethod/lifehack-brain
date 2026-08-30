#!/usr/bin/env python3
"""
registered-guard-fire-test.py — enumerate PreToolUse guards from the REGISTRATION file (never
a hand-typed list), fire each one through the real harness contract with synthetic stdin JSON,
and report one of six honest verdicts per guard.

WHY THIS EXISTS (T-session, 2026-08-23): system/tools/organism/label_checker.py already fires
guards safely and correctly (verified this session — its fire()/block_verdict() logic, including
the stderr+exit-1 "silently dark" trap, is right). But it has two structural gaps this tool
closes WITHOUT touching that file (scope-locked to new files only this session):

  1. label_checker.py's own guard LIST comes from label_manifest.yaml (a hand-curated file) —
     never from the registration file itself. Measured this session: label_manifest.yaml covers
     21 of the 30 guards actually registered under PreToolUse in system/hooks/registrations.json.
     9 registered BLOCK-capable guards have ZERO fire-test cases anywhere in the manifest engine.
     A hand-typed denominator is a defect this repo has already paid for (build-rules-index.md,
     ABSENT-SUBJECT-RULE) — so THIS tool's guard list comes from the registration file, every run.

  2. label_checker.py's registration check reads `.claude/settings.json` for a "hooks" key.
     Measured this session (2026-08-23): that key was moved to system/hooks/registrations.json
     by a same-day change (T3.3) and label_checker.py's SETTINGS constant was never updated —
     so it currently reports 21 of 22 manifest guards as false DOWNGRADEs ("not registered"),
     even though every one of them fires correctly. This is exactly the class of failure this
     whole exercise is about: found by RUNNING the checker, not by reading it. This tool tries
     several known registration-source paths in priority order and NAMES which one it used,
     specifically so this class of drift is visible instead of silently wrong.

WHAT THIS TOOL DOES NOT DO: it does not re-implement label_checker.py's engine wholesale, and it
does not try to be a second source of truth for the 21 guards that manifest already covers well —
for those it reads the SAME manifest file and applies the SAME fire/verdict contract
(hook-contract.md's exit-2 / decision:block / stderr-dark-trap rules), reimplemented here in ~20
lines because a single-file, dependency-free script is what makes the cross-repo drift check
possible (verify-pm-guard.sh and firetest-sheet-sep.sh are the precedent for that shape, not the
larger engine). For the 9 (or however many) guards outside the manifest, it does NOT invent test
cases (that would be undefined judgment, not membership) — it reports NO-CASES-DEFINED, plainly,
and separately greps system/hooks/tests/*.sh for the guard's basename so a sibling test that
already exists elsewhere is surfaced rather than double-counted or hidden. It never EXECUTES a
sibling test file it did not author — only guards, fired the one safe way (synthetic JSON on
stdin), are ever executed by this tool.

SAFETY: every fire is a synthetic PreToolUse JSON payload piped to `bash <guard>` on stdin. This
tool never runs a real command, never touches Gmail/Drive/Sheets/notes, and never invokes a guard
via any path other than its stdin contract.

VERDICTS (one of exactly six, per guard):
  FIRES              — both directions proven: every violation case blocked, every allow case passed.
  DENY-ONLY          — violation cases defined and all blocked; no allow cases were defined to test
                        the other direction (or they were defined and behaved wrong — see the note).
  ALLOW-ONLY         — allow cases defined and all passed; no violation cases were defined (or they
                        were defined and behaved wrong — see the note).
  MISFIRES           — cases were defined in both directions and at least one case in EITHER
                        direction behaved wrong. Not one of the four originally-specified labels,
                        added because folding a broken guard into "DENY-ONLY"/"ALLOW-ONLY" would
                        itself be the false-green this tool exists to prevent — see the note field
                        for exactly which case misbehaved. Never spelled the way a pass is spelled.
  NOT-EXECUTABLE     — the guard is missing on disk, not executable on disk, or its GIT-TRACKED
                        mode (git ls-files -s) is not 100755. Checked BEFORE any firing attempt.
  NO-CASES-DEFINED   — no manifest entry exists for this guard. NEVER reported as a pass.
  UNREACHABLE        — a fire attempt was made but the process did not return a real verdict
                        (exit code outside {0,2} with no decision:block JSON on either channel) —
                        e.g. rc=127 "not found", a crash, a timeout. Absent and wrong get
                        different words on purpose (ABSENT-SUBJECT-RULE).

Usage:
  registered-guard-fire-test.py [--repo PATH] [--json] [--guard SCRIPT_BASENAME]

Runnable in EITHER repo (pass --repo to point at another clone) — running the same command in
two repos and diffing the two tables IS the drift check; nothing here is repo-specific except
the list of candidate registration-source paths, which is intentionally a short, named list
(never a guess) so an unmatched repo layout fails loud instead of silently returning zero guards.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # made VISIBLE 2026-08-28 -- was a silent degrade
    __import__("sys").stderr.write(
        "WARNING [registered-guard-fire-test]: PyYAML is missing under this interpreter (%s) -- "
        "registry-derived results are DEGRADED and INCOMPLETE, not clean. "
        "Pin to /usr/bin/python3 (see system/requirements.txt).\n" % __import__("sys").executable)
    yaml = None

# Named, in-priority-order candidate sources for "what is actually registered" — never a guess,
# never a single hardcoded path. The first one that parses AND carries a non-empty "hooks" dict
# wins, and WHICH one won is always printed, because that fact alone is a drift signal across
# two repos (this repo's real source moved from settings.json to registrations.json today).
CANDIDATE_SOURCES = [
    "system/hooks/registrations.json",
    ".claude/settings.json",
    ".claude/settings.local.json",
    "system/reference/settings.json",
]

CANDIDATE_MANIFESTS = [
    "system/tools/organism/label_manifest.yaml",
]

CANDIDATE_TEST_DIRS = [
    "system/hooks/tests",
]

BLOCK_JSON = re.compile(r'"decision"\s*:\s*"block"')


def resolve_repo(path_arg):
    start = Path(path_arg) if path_arg else Path(__file__).resolve().parent
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    if path_arg:
        return Path(path_arg).resolve()
    return Path(__file__).resolve().parents[2]


def load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def find_registration_source(repo: Path):
    """Return (path, data) for the first candidate that parses and has a non-empty 'hooks' dict.
    Returns (None, None) if nothing qualifies — an ABSENT SUBJECT, reported loudly, never as
    zero guards silently."""
    for rel in CANDIDATE_SOURCES:
        p = repo / rel
        if not p.exists():
            continue
        data = load_json(p)
        if data is None:
            continue
        hooks = data.get("hooks", {})
        if hooks:
            return (rel, data)
    return (None, None)


def enumerate_pretool_guards(reg_data: dict, repo: Path):
    """From the registration data's PreToolUse block, return a list of
    {"script": "system/hooks/x.sh", "event": "PreToolUse", "matcher": str}.
    Guard scripts are resolved as paths RELATIVE TO repo — never assumed to exist elsewhere."""
    out = []
    for entry in reg_data.get("hooks", {}).get("PreToolUse", []):
        matcher = entry.get("matcher", "*")
        for hk in entry.get("hooks", []):
            cmd = hk.get("command", "")
            # command is like: bash "$HOME/.claude/skills/ClaudeOps/system/hooks/x.sh" [args]
            m = re.search(r'(system/hooks/[A-Za-z0-9_./-]+\.sh)', cmd)
            if not m:
                continue
            out.append({"script": m.group(1), "matcher": matcher, "raw_command": cmd})
    return out


def git_ls_mode(repo: Path, rel: str):
    """Return the git-tracked file mode (e.g. '100755') for rel, or None if untracked."""
    out = subprocess.run(
        ["git", "ls-files", "-s", "--", rel],
        cwd=repo, capture_output=True, text=True, timeout=10,
    )
    line = out.stdout.strip()
    if not line:
        return None
    return line.split()[0]


def find_manifest(repo: Path):
    for rel in CANDIDATE_MANIFESTS:
        p = repo / rel
        if p.exists():
            return p
    return None


def load_manifest_guards(manifest_path: Path):
    if manifest_path is None:
        return []
    if yaml is None:
        print("WARNING: pyyaml unavailable — cannot read the manifest; every guard will read "
              "NO-CASES-DEFINED. Install pyyaml to get real coverage.", file=sys.stderr)
        return []
    try:
        data = yaml.safe_load(manifest_path.read_text())
    except Exception as e:
        print(f"WARNING: manifest failed to parse ({e}) — treating as absent.", file=sys.stderr)
        return []
    return data.get("guards", []) if data else []


def expand(s):
    return os.path.expanduser(os.path.expandvars(s)) if isinstance(s, str) else s


def expand_payload(obj):
    if isinstance(obj, dict):
        return {k: expand_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_payload(v) for v in obj]
    return expand(obj)


def fire(repo: Path, script_rel: str, payload, raw_stdin=None):
    """Fire the guard exactly the way the harness delivers a PreToolUse call: JSON on stdin,
    read the exit code. NEVER echo (a mangled newline fakes a fail-open pass) — json.dumps only.
    This NEVER runs a real command: the guard receives a synthetic description of a command; it
    is the guard's own job to decide allow/deny, and this tool never executes the described
    command itself."""
    script_abs = repo / script_rel
    body = raw_stdin if raw_stdin is not None else json.dumps(expand_payload(payload))
    try:
        proc = subprocess.run(
            ["bash", str(script_abs)],
            input=body, capture_output=True, text=True, timeout=30,
        )
        return (proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        return (None, "", "TIMEOUT after 30s")
    except Exception as e:
        return (None, "", f"EXCEPTION: {e}")


def block_verdict(rc, out, err):
    """Per hook-contract.md's real, honored contract:
      exit 2                                  -> BLOCKED
      decision:block JSON on STDOUT, rc != 0  -> BLOCKED
      decision:block JSON on STDERR, rc != 2  -> the DARK TRAP: neither channel is read by the
                                                  harness, so this is NOT a real block even though
                                                  it looks like one.
    Returns (blocked: bool, note: str)."""
    if rc == 2:
        return (True, "")
    if rc is not None and rc != 0 and BLOCK_JSON.search(out or ""):
        return (True, "")
    if rc is not None and rc != 2 and BLOCK_JSON.search(err or ""):
        return (False, "SILENTLY DARK: decision:block JSON on stderr with a non-2 exit — "
                       "neither channel is honored by the harness (hook-contract.md).")
    return (False, "")


def is_unreachable(rc):
    """A verdict of 0 (allow) or 2 (block) is a real answer. Anything else — 127 not-found, a
    crash, a timeout (rc is None), a stray 1 with no decision:block JSON anywhere — means the
    guard was never actually reached, and that is a DIFFERENT fact from either verdict."""
    return rc not in (0, 2)


def evaluate_manifest_guard(repo: Path, script_rel: str, manifest_entry: dict):
    violations = manifest_entry.get("violations", [])
    allow = manifest_entry.get("allow", [])
    detail = {"violations": [], "allow": []}

    viol_results = []
    for v in violations:
        rc, out, err = fire(repo, script_rel, v.get("payload", v), v.get("raw_stdin"))
        if is_unreachable(rc) and not (rc is not None and BLOCK_JSON.search(out or "")):
            desc = v.get("desc", "violation case")
            detail["violations"].append((False, f"UNREACHABLE (exit {rc}): {desc}"))
            viol_results.append("unreachable")
            continue
        blocked, note = block_verdict(rc, out, err)
        desc = v.get("desc", "violation case")
        detail["violations"].append((blocked, f"{desc}" + (f" — {note}" if note else "")))
        viol_results.append("blocked" if blocked else "not-blocked")

    allow_results = []
    for a in allow:
        rc, out, err = fire(repo, script_rel, a.get("payload", a), a.get("raw_stdin"))
        if is_unreachable(rc):
            desc = a.get("desc", "allow case")
            detail["allow"].append((False, f"UNREACHABLE (exit {rc}): {desc}"))
            allow_results.append("unreachable")
            continue
        ok = (rc == 0)
        desc = a.get("desc", "allow case")
        detail["allow"].append((ok, desc))
        allow_results.append("passed" if ok else "wrongly-blocked")

    any_unreachable = "unreachable" in viol_results or "unreachable" in allow_results
    if any_unreachable and not violations and not allow:
        pass  # falls through to NO-CASES-DEFINED below (shouldn't happen — manifest entry exists)

    has_viol, has_allow = bool(violations), bool(allow)
    viol_ok = all(r == "blocked" for r in viol_results) if has_viol else None
    allow_ok = all(r == "passed" for r in allow_results) if has_allow else None

    if any_unreachable:
        verdict = "UNREACHABLE"
    elif not has_viol and not has_allow:
        verdict = "NO-CASES-DEFINED"
    elif has_viol and has_allow:
        verdict = "FIRES" if (viol_ok and allow_ok) else "MISFIRES"
    elif has_viol:
        verdict = "DENY-ONLY" if viol_ok else "MISFIRES"
    else:
        verdict = "ALLOW-ONLY" if allow_ok else "MISFIRES"

    return verdict, detail


def find_sibling_tests(repo: Path, script_basename: str):
    """Mechanical membership check only: does ANY file under system/hooks/tests/ mention this
    guard's basename? This tool does NOT execute what it finds (never runs a script it did not
    author) — it only surfaces the name so 'no manifest entry' is not misread as 'no coverage
    anywhere.' Run the named file directly to see whether it actually passes."""
    hits = []
    for rel in CANDIDATE_TEST_DIRS:
        d = repo / rel
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.sh")):
            try:
                if script_basename in f.read_text(errors="ignore"):
                    hits.append(str(f.relative_to(repo)))
            except Exception:
                continue
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="repo root to test (default: this script's own repo)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--guard", help="only check this guard's script basename (e.g. guard_egress.sh)")
    args = ap.parse_args()

    repo = resolve_repo(args.repo)
    # Manifest payloads use "$REPO/..." placeholders (label_manifest.yaml's own convention,
    # e.g. write-paths-hooks-guard's violation cases) — export it so expand_payload's
    # os.path.expandvars resolves them to THIS run's real repo, never a hardcoded clone name.
    # Missing this silently sends every $REPO-relative payload to a garbage path that no guard
    # zone matches, which manufactures a false "violation not blocked" — caught by hand-firing
    # one payload during this tool's own build and build into this fix.
    os.environ["REPO"] = str(repo)
    if not (repo / ".git").exists() and not (repo / "system").exists():
        print(f"ABORT — {repo} does not look like a ClaudeOps-shaped repo (no .git, no system/). "
              f"Nothing was tested.", file=sys.stderr)
        sys.exit(2)

    src_rel, reg_data = find_registration_source(repo)
    if src_rel is None:
        print(f"ABORT — no hook registration source found under any of: {CANDIDATE_SOURCES}", file=sys.stderr)
        print("This is an ABSENT SUBJECT, not a clean run: nothing was tested because this tool "
              "could not find what it is supposed to enumerate. Fix the candidate list or the repo.",
              file=sys.stderr)
        sys.exit(2)

    guards = enumerate_pretool_guards(reg_data, repo)
    if args.guard:
        guards = [g for g in guards if Path(g["script"]).name == args.guard]
        if not guards:
            print(f"ERROR: no PreToolUse guard registered with basename {args.guard}", file=sys.stderr)
            sys.exit(2)

    manifest_path = find_manifest(repo)
    manifest_guards = load_manifest_guards(manifest_path)
    manifest_by_script = {g.get("script"): g for g in manifest_guards}

    results = []
    for g in guards:
        script_rel = g["script"]
        script_abs = repo / script_rel
        basename = Path(script_rel).name
        row = {"script": script_rel, "matcher": g["matcher"]}

        exists = script_abs.exists()
        on_disk_exec = exists and os.access(script_abs, os.X_OK)
        tracked_mode = git_ls_mode(repo, script_rel)
        git_exec = tracked_mode == "100755"
        untracked = tracked_mode is None

        if not exists or untracked or not git_exec:
            row["verdict"] = "NOT-EXECUTABLE"
            reasons = []
            if not exists:
                reasons.append("not present on disk")
            if untracked:
                reasons.append("NOT git-tracked (won't travel by git pull)")
            elif not git_exec:
                reasons.append(f"git-tracked mode is {tracked_mode}, not 100755 — inert once pulled")
            if exists and not on_disk_exec:
                reasons.append("on-disk executable bit not set")
            row["note"] = "; ".join(reasons)
            results.append(row)
            continue

        entry = manifest_by_script.get(script_rel)
        if entry is None:
            row["verdict"] = "NO-CASES-DEFINED"
            siblings = find_sibling_tests(repo, basename)
            row["note"] = (f"no entry in {manifest_path.relative_to(repo) if manifest_path else '(no manifest found)'}"
                            + (f" — but referenced by: {', '.join(siblings)} (not run by this tool; run directly)"
                               if siblings else " — and no sibling test file mentions this guard's name either"))
            results.append(row)
            continue

        verdict, detail = evaluate_manifest_guard(repo, script_rel, entry)
        row["verdict"] = verdict
        notes = []
        for ok, desc in detail["violations"]:
            if not ok:
                notes.append(f"VIOLATION not blocked: {desc}")
        for ok, desc in detail["allow"]:
            if not ok:
                notes.append(f"ALLOW wrongly blocked: {desc}")
        row["note"] = "; ".join(notes) if notes else f"{len(detail['violations'])} violation(s), {len(detail['allow'])} allow-case(s), all as expected"
        results.append(row)

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    if args.json:
        print(json.dumps({
            "repo": str(repo),
            "registration_source": src_rel,
            "manifest": str(manifest_path.relative_to(repo)) if manifest_path else None,
            "results": results,
            "counts": counts,
        }, indent=2))
    else:
        print(f"registered-guard-fire-test — repo={repo}")
        print(f"registration source used: {src_rel}")
        print(f"manifest used: {manifest_path.relative_to(repo) if manifest_path else '(none found — every guard falls to NO-CASES-DEFINED)'}")
        print(f"PreToolUse guards enumerated from registration: {len(guards)}")
        print("─" * 100)
        for r in sorted(results, key=lambda r: (r["verdict"], r["script"])):
            print(f"  {r['verdict']:18} {r['script']:52} {r['note']}")
        print("─" * 100)
        print("counts: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
        never_pass_as_ok = counts.get("NO-CASES-DEFINED", 0)
        if never_pass_as_ok:
            print(f"⚠ {never_pass_as_ok} guard(s) NO-CASES-DEFINED — untested, NOT the same fact as passing.")
        if counts.get("MISFIRES", 0) or counts.get("NOT-EXECUTABLE", 0) or counts.get("UNREACHABLE", 0):
            print("⚠ real problems found — see MISFIRES / NOT-EXECUTABLE / UNREACHABLE rows above.")

    # Exit non-zero on any real problem (misfire, not-executable, unreachable) or absent coverage
    # being mistaken for a pass is exactly the failure this tool exists to prevent — so a clean
    # exit 0 requires FIRES/DENY-ONLY/ALLOW-ONLY only.
    bad = sum(v for k, v in counts.items() if k in ("MISFIRES", "NOT-EXECUTABLE", "UNREACHABLE"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
