#!/usr/bin/env python3
"""pre-commit check 3, "Is it a copy?" (v2 plan 3b). Refuses a STAGED NEW file that is a second copy of
  (a) a shared tool  -- the register's shared-tool list, distinctive-vs-generic naming and the thin-wrapper
      exemption are REUSED from system/hooks/lib/build_mode.py, not re-implemented here;
  (b) a rulebook     -- a new *.md named like a system/sops/*-sop.md (or the security canon) or more than
      80% identical lines to a system/sops/*.md.
Only NEW files (added, or renamed while the source still exists). Thin wrappers and _retired-*/archive dirs
are exempt. Exit 1 on refuse, else 0. Run from inside the repo; reads the index, not the work tree.
"""
import collections, importlib.util, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
THRESH = 0.8
MIN_LINES = 8          # below this, only an exact match counts as a content copy
CANON = ("system/security-canon.md",)


def load_bm():
    spec = importlib.util.spec_from_file_location(
        "build_mode", os.path.join(HERE, "..", "..", "hooks", "lib", "build_mode.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git(*a):
    return subprocess.run(("git",) + a, capture_output=True, check=True).stdout


def staged_new():
    parts = git("diff", "--cached", "--name-status", "-M", "--diff-filter=AR", "-z").decode("utf-8", "replace").split("\0")
    out, i = [], 0
    while i < len(parts) and parts[i]:
        if parts[i].startswith("R"):
            old, new = parts[i + 1], parts[i + 2]
            i += 3
            if subprocess.run(["git", "cat-file", "-e", ":" + old], capture_output=True).returncode == 0:
                out.append(new)       # source still in the index: the rename made a copy
        else:
            out.append(parts[i + 1]); i += 2
    return out


def exempt_dir(path):
    return any(re.match(r"(_retired-.*|_?archive.*)$", seg, re.I) for seg in path.split("/")[:-1])


def lines(text):
    return [l.strip() for l in text.splitlines() if l.strip()]


def similar(a, b):
    la, lb = lines(a), lines(b)
    if not la or not lb:
        return 0.0
    if la == lb:
        return 1.0
    if min(len(la), len(lb)) < MIN_LINES:
        return 0.0
    return sum((collections.Counter(la) & collections.Counter(lb)).values()) / max(len(la), len(lb))


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None


def main():
    files = sys.argv[2:] if len(sys.argv) > 2 and sys.argv[1] == "--files" else None    # --files P...: no git, read the disk
    top = os.path.realpath(os.path.join(HERE, "..", "..", "..")) if files else git("rev-parse", "--show-toplevel").decode().strip()
    new = [os.path.realpath(p) for p in files if os.path.isfile(p)] if files else staged_new()
    if not new:
        return 0
    bm = load_bm()
    try:
        shared = bm.shared_names(top)       # {basename: '/shared/...'}
    except Exception as e:
        sys.stderr.write("is_copy: cannot read the register (%s); shared-tool half skipped\n" % e)
        shared = {}
    shared_txt = {sp: t for sp in shared.values() for t in [read(os.path.join(top, sp.lstrip("/")))] if t is not None}
    newset = set(new)
    rulebooks = []
    sopdir = os.path.join(top, "system", "sops")
    if os.path.isdir(sopdir):
        rulebooks += ["system/sops/" + f for f in sorted(os.listdir(sopdir)) if f.endswith(".md")]
    rulebooks += [c for c in CANON if os.path.isfile(os.path.join(top, c))]
    rulebooks = [r for r in rulebooks if r not in newset]   # only rulebooks that already exist
    findings = []
    for path in new:
        if files and path.startswith(top + "/"):
            path = path[len(top) + 1:]           # a file inside the harness gets the same repo-relative rules as a staged one
        if exempt_dir(path) or path.startswith("shared/"):
            continue
        text = read(os.path.join(top, path)) if files else git("show", ":" + path).decode("utf-8", "replace")
        if text is None:
            continue
        base = os.path.basename(path)
        hit = None
        if path.endswith(".md"):
            for rb in rulebooks:
                if base == os.path.basename(rb) and (base.endswith("-sop.md") or rb in CANON):
                    hit = (rb, "same name as the rulebook"); break
                if similar(text, read(os.path.join(top, rb)) or "") > THRESH:
                    hit = (rb, "near-duplicate content"); break
        elif not bm.is_thin_wrapper(text):
            for sp, st in shared_txt.items():
                same_name = base == os.path.basename(sp)
                if same_name and not bm.is_generic(base):
                    hit = (sp, "distinctive shared name"); break
                if similar(text, st) > THRESH:      # generic name or renamed: content must really match
                    hit = (sp, "same content under " + ("a generic name" if same_name else "another name")); break
        if hit:
            findings.append((path, hit))
    for path, (sp, why) in findings:
        sys.stderr.write("is_copy: REFUSED %s: copy of %s — use it, don't copy it\n" % (path, sp))
        sys.stderr.write("FINDING " + json.dumps({"check": "is_copy", "path": path, "copy_of": sp, "reason": why}) + "\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
