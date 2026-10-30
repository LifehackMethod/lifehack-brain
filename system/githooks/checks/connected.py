#!/usr/bin/env python3
"""connected.py — pre-commit check 1, "Is it connected?" (v2 plan Phase 3b, fix F1).

A NEWLY ADDED tool (system/tools/, shared/), skill (.claude/skills/*/SKILL.md) or hook script
(system/hooks/*.sh) that nothing calls is refused. Reads the STAGED index only; existing files
are never checked (a gate must not block on old red). Reuses system/register/caller_lint.py's
judgment (ref_kind / instr_match / is_test_class / INVOKE_TOK) rather than re-deriving it.

"Calls" = the basename appears (a) in a wiring file (hooks.json, settings*.json,
registrations.json), (b) on an invocation-shaped line of another tracked/staged script,
(c) on an instruction line of a doc / SOP / skill, or anywhere in jobs.md / a SKILL.md;
a *.lib.sh is connected if sourced, a lib/*.py if imported. A skill is connected by being a skill
(frontmatter with name + description). Tests are exempt.
Escape: a header line `# not-wired-yet: <reason>` in the first 20 lines -> allowed, reported (warn).

Usage: connected.py [REPO_ROOT]   exit 0 pass / 1 refuse. Findings: `FINDING {json}` on stderr.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "register")))
import caller_lint as cl  # noqa: E402

WIRING = {"hooks.json", "settings.json", "settings.local.json", "registrations.json"}
MARKER = re.compile(r"not-wired-yet:\s*(\S.*)")


def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, errors="replace")
    return r.stdout


def kind_of(path):
    if re.match(r"\.claude/skills/[^/]+/SKILL\.md$", path):
        return "skill"
    if re.match(r"system/hooks/[^/]+\.sh$", path):
        return "hook"
    if re.match(r"(system/tools|shared)/.+\.(sh|py)$", path):
        return "tool"
    return None


FILES_MODE = False      # --files: read the disk instead of the git index (no git needed)


def staged_text(root, path):
    if FILES_MODE:
        try:
            return open(os.path.join(root, path), encoding="utf-8", errors="replace").read()
        except OSError:
            return ""
    return git(root, "show", ":" + path)


def grep_callers(root, path, needle):
    """git grep --cached lines, or (no git) a plain grep over the harness folder with the same 'p:n:text' shape."""
    if not FILES_MODE:
        return git(root, "grep", "--cached", "-n", "-I", "-F", "-e", needle, "--", ".", ":!" + path)
    r = subprocess.run(["grep", "-rnIF", "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude=" + os.path.basename(path), "-e", needle, "."],
                       cwd=root, capture_output=True, text=True, errors="replace")
    return "\n".join(l[2:] if l.startswith("./") else l for l in r.stdout.splitlines())


def called(root, path):
    """Return a short evidence string if something calls `path`, else None."""
    base = os.path.basename(path)
    stem = base[:-3] if base.endswith(".py") else None
    import_pat = (re.compile(r"\b(?:import\s+" + re.escape(stem) + r"\b|from\s+" + re.escape(stem)
                             + r"\s+import\b)") if stem else None)
    needle = stem or base
    out = grep_callers(root, path, needle)
    for ln in out.splitlines():
        try:
            p, _, text = ln.split(":", 2)
        except ValueError:
            continue
        if cl.is_test_class(p):
            continue
        pb, ext = os.path.basename(p), os.path.splitext(p)[1]
        if pb in WIRING and base in text:
            return "wired:" + p
        if pb == "jobs.md" and base in text:
            return "scheduled:" + p
        if ext == ".md":
            if "/skills/" in "/" + p and base in text:
                return "skill-referenced:" + p
            if cl.instr_match(text, base):
                return "cli-instructed:" + p
            continue
        if import_pat and ext == ".py":
            s = re.sub(r"\s+#.*$", "", text.strip())
            if not s.startswith("#") and import_pat.search(s):
                return "imported:" + p
        if base in text and cl.ref_kind(text, base, ".py" if ext == ".py" else ".sh") == "script-invoked":
            return "script-invoked:" + p
    return None


def check(root, files=None):
    if files is not None:        # --files: only paths INSIDE the harness folder have a kind; anything else is skipped
        rootp = os.path.realpath(root) + "/"
        added = ["A\t" + os.path.realpath(f)[len(rootp):] for f in files if os.path.realpath(f).startswith(rootp) and os.path.isfile(f)]
    else:
        added = git(root, "diff", "--cached", "--name-status", "--diff-filter=A").splitlines()
    refused, warned = [], []
    for ln in added:
        parts = ln.split("\t")
        if len(parts) < 2:
            continue
        path = parts[-1]
        k = kind_of(path)
        if not k or cl.is_test_class(path):
            continue
        body = staged_text(root, path)
        if MARKER.search("\n".join(body.splitlines()[:20])):
            warned.append(path)
            continue
        if k == "skill":
            if re.match(r"---\n(?:.*\n)*?name:.*\n(?:.*\n)*?description:", body) or \
               re.match(r"---\n(?:.*\n)*?description:.*\n(?:.*\n)*?name:", body):
                continue
            refused.append(path)
            continue
        if not called(root, path):
            refused.append(path)
    for p in refused:
        print(f'connected: REFUSED {p}: nothing calls this — wire it (hooks.json / a caller) or mark "# not-wired-yet: <why>"')
        print("FINDING " + json.dumps({"check": "connected", "path": p, "decision": "deny"}), file=sys.stderr)
    for p in warned:
        print(f"connected: warn {p}: marked not-wired-yet (allowed)")
        print("FINDING " + json.dumps({"check": "connected", "path": p, "decision": "warn"}), file=sys.stderr)
    return 1 if refused else 0


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--files":
        FILES_MODE = True
        sys.exit(check(os.path.realpath(os.path.join(HERE, "..", "..", "..")), sys.argv[2:]))
    root = sys.argv[1] if len(sys.argv) > 1 else git(".", "rev-parse", "--show-toplevel").strip()
    sys.exit(check(root))
