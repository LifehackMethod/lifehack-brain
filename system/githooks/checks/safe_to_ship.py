#!/usr/bin/env python3
"""safe_to_ship.py -- pre-commit check 4, "Is it safe to ship?" (v2 plan Phase 3b, fix F4).

Reads the STAGED index only (added lines + staged file modes); old content is never rescanned.

Part A, private material: runs the SAME rule engine CI runs, .github/scripts/check_no_internal_leakage.py
  (imported, not copied: path denylist, home paths, Drive mounts, email addresses, the private repo URL,
  session URLs, operator identity, third-party-name / billing heuristics). A new rule goes into THAT file,
  so CI and pre-commit share one list. Fail closed: if the operator-identity tier cannot be compiled the
  scan did not happen, so the commit is refused.
Part B, exec bit: a staged system/hooks/*.sh or system/githooks/ script (not tests/) whose INDEX mode is
  100644 is refused; the fix is `git update-index --chmod=+x <path>`.

Usage: safe_to_ship.py [REPO_ROOT]   exit 0 pass / 1 refuse.
Output: `file:line  [rule]` lines on stdout, one `FINDING {json}` per finding on stderr (check "safe_to_ship").
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCANNER_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".github", "scripts"))
HOOK_RE = re.compile(r"^system/hooks/[^/]+\.sh$")
GITHOOK_RE = re.compile(r"^system/githooks/(?!tests/)(?:[^/]+/)*[^/.]*(?:\.sh|\.py)?$")
HEADER_RE = re.compile(r"^::error file=(?P<f>.*?),line=(?P<l>\d+)::\[(?P<r>[^\]]+)\]")
HEADER_NOLINE_RE = re.compile(r"^::error file=(?P<f>.*?)::\[(?P<r>[^\]]+)\]")


def git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                          errors="replace").stdout


def emit(findings):
    for f in findings:
        loc = f["path"] + (":" + str(f["line"]) if f.get("line") else "")
        print("REFUSED  {}  [{}]  {}".format(loc, f["rule"], f.get("fix", "")))
        print("FINDING " + json.dumps({"check": "safe_to_ship", "decision": "deny", **f}), file=sys.stderr)


def part_a(root):
    sys.path.insert(0, SCANNER_DIR)
    try:
        import check_no_internal_leakage as leak
    except Exception as e:  # fail closed
        return [{"path": SCANNER_DIR, "rule": "scanner-unavailable", "fix": "cannot import: %s" % e}]
    try:
        leak.install_identity_patterns()
    except leak.IdentityUnavailable as e:
        return [{"path": "(identity tier)", "rule": "cannot-evaluate",
                 "fix": "operator-identity rules not compilable, scan did not run: %s" % str(e)[:160]}]
    diff = git(root, "diff", "--cached", "--unified=0", "--no-color", "--no-renames", "--diff-filter=AM")
    file_diffs = leak.parse_unified_diff(diff)
    whole = {p: "\n".join(t for _, t in lines) for p, lines in file_diffs}
    out = []
    for v in leak.scan_files(file_diffs, whole, frozenset(leak.DESK_PERSONA_CANDIDATES)):
        m = HEADER_RE.match(v)
        if m:
            out.append({"path": m["f"], "line": int(m["l"]), "rule": m["r"]})
            continue
        m = HEADER_NOLINE_RE.match(v)
        if m:
            out.append({"path": m["f"], "rule": m["r"]})
    return out


def part_b(root):
    out = []
    names = git(root, "diff", "--cached", "--name-only", "--no-renames", "--diff-filter=AM").splitlines()
    for p in names:
        if not (HOOK_RE.match(p) or GITHOOK_RE.match(p)):
            continue
        ls = git(root, "ls-files", "-s", "--", p).split()
        if ls and ls[0] == "100644":
            out.append({"path": p, "rule": "exec-bit-missing",
                        "fix": "git update-index --chmod=+x " + p})
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else git(".", "rev-parse", "--show-toplevel").strip()
    findings = part_b(root) + part_a(root)
    emit(findings)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
