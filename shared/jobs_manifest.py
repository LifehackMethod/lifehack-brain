#!/usr/bin/env python3
"""jobs_manifest.py — the ONE reader that joins the shared job table with YOUR personal one.

The plugin ships `system/jobs.md` (the shared jobs, the same for everyone) and `system/job-names.txt`
beside it. Jobs that belong to one person (their own desks, their own scripts) do NOT go in the plugin:
they go in that person's personal code folder, in the same two formats:

    <personal-code>/jobs.md          a ```jobs``` block, same nine columns as system/jobs.md
    <personal-code>/job-names.txt    `<job> = <plain name>` lines, same as system/job-names.txt

<personal-code> is found through `shared/personal_code_root.py` (the ~/.config/lifehack/personal-code
pointer); nothing here names anyone's folder. A missing personal file means "no personal jobs" — a new
student has nothing to set up, and every scheduler entry point behaves exactly as before.

Rules (one place, so pulse.sh, job-run.sh, install-schedulers.sh and health_line.py all agree):
  * shared rows + personal rows; on a NAME CLASH the personal row wins and a WARNING names the job
    (stderr), so a person can override a shared job's schedule without editing the plugin;
  * only the ```jobs``` block is joined. The ```crontab``` block (Linux/Windows OS schedule) stays the
    shared file's own;
  * personal job names come first in the joined names file, so a personal plain name wins too.

Which personal file (in order):
  (1) $LIFEHACK_PERSONAL_JOBS_FILE when set (a test seam; set it EMPTY to mean "no personal file");
  (2) none, when $LIFEHACK_JOBS_FILE or $PULSE_CONFIG is set: those are test seams that plant a whole
      manifest, and a planted manifest must stand alone (a real personal job must never leak into a test);
  (3) <personal-code>/jobs.md, when the personal code folder resolves and the file exists;
  (4) otherwise none. A pointer naming a folder that is gone is reported (stderr) and treated as none.

When there is no personal file the shared path is used AS IS (no copy is made). When there is one, the
joined table is written once per content to a private cache folder
(${LIFEHACK_JOBS_MERGED_DIR:-~/.cache/lifehack/jobs-merged}/<hash>/{jobs.md,job-names.txt}) and that path
is used, so the bash readers keep reading one ordinary file.

CLI (what the bash entry points call):
    python3 shared/jobs_manifest.py --manifest <shared jobs.md>   # prints the path to read
    python3 shared/jobs_manifest.py --personal                    # prints the personal jobs.md, or nothing
"""
import argparse
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import personal_code_root  # noqa: E402

FENCE_OPEN = "```jobs"
FENCE_CLOSE = "```"
KEEP_CACHES = 6


def _warn(msg):
    try:
        print("[jobs_manifest] " + msg, file=sys.stderr)
    except Exception:  # allow-silence: stderr itself is unwritable, so there is no channel left to report on
        pass


def resolve_personal_jobs(env=None):
    """Path of the personal jobs.md to join, or None. See the module docstring for the order."""
    env = os.environ if env is None else env
    if "LIFEHACK_PERSONAL_JOBS_FILE" in env:
        p = env.get("LIFEHACK_PERSONAL_JOBS_FILE") or ""
        return p if p and os.path.isfile(p) else None
    if env.get("LIFEHACK_JOBS_FILE") or env.get("PULSE_CONFIG"):
        return None
    source, root = personal_code_root.resolve_personal_code_root()
    if source == "pointer-missing":
        _warn("your personal code pointer names a folder that is not there (%s); personal jobs skipped" % root)
        return None
    if not root:
        return None
    p = os.path.join(root, "jobs.md")
    return p if os.path.isfile(p) else None


def _row_name(line):
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    return s.split("|", 1)[0].strip() or None


def jobs_block_lines(text):
    """The lines inside every ```jobs block (comments kept), CR stripped."""
    out, inb = [], False
    for ln in text.splitlines():
        ln = ln.rstrip("\r")
        if ln == FENCE_OPEN:
            inb = True
            continue
        if inb and ln == FENCE_CLOSE:
            inb = False
            continue
        if inb:
            out.append(ln)
    return out


def merge_text(shared_text, personal_text, personal_label="personal jobs.md"):
    """-> (joined manifest text, [warnings]). The shared text is kept line for line, minus any shared row a
    personal row overrides; the personal block's lines are inserted just before the shared block's closing fence."""
    personal = jobs_block_lines(personal_text)
    pnames = [n for n in (_row_name(l) for l in personal) if n]
    pset = set(pnames)
    warnings = []
    seen = set()
    for n in pnames:
        if n in seen:
            warnings.append("personal row '%s' appears twice in %s; the LAST one is used" % (n, personal_label))
        seen.add(n)
    out, inb, inserted = [], False, False
    for ln in shared_text.splitlines():
        bare = ln.rstrip("\r")
        if bare == FENCE_OPEN and not inserted:
            inb = True
            out.append(bare)
            continue
        if inb and bare == FENCE_CLOSE:
            out.append("# ── personal rows (from %s) ──" % personal_label)
            out.extend(personal)
            out.append(bare)
            inb, inserted = False, True
            continue
        if inb:
            n = _row_name(bare)
            if n and n in pset:
                warnings.append("personal row '%s' overrides the shared row of the same name" % n)
                continue
        out.append(bare)
    if not inserted:   # the shared file has no jobs block at all: give the personal rows one of their own
        out += ["", FENCE_OPEN, "# ── personal rows (from %s) ──" % personal_label] + personal + [FENCE_CLOSE]
    # A duplicated personal name: keep only its LAST row (the shared readers take the first match).
    if len(seen) != len(pnames):
        last = {}
        for i, ln in enumerate(out):
            n = _row_name(ln)
            if n in pset:
                last[n] = i
        out = [ln for i, ln in enumerate(out) if not (_row_name(ln) in pset and last.get(_row_name(ln)) != i)]
    return "\n".join(out) + "\n", warnings


def _read(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def merge_names(shared_names_text, personal_names_text):
    """Personal lines first (job-run.sh takes the first `<job> = ` match), then the shared ones."""
    parts = [t for t in (personal_names_text, shared_names_text) if t]
    return "".join(t if t.endswith("\n") else t + "\n" for t in parts)


def _cache_root(env):
    return env.get("LIFEHACK_JOBS_MERGED_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "lifehack", "jobs-merged")


def _atomic_write(path, text):
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def effective_manifest(shared_path, env=None):
    """The path every reader should open: `shared_path` itself when there is no personal file, else the joined copy."""
    env = os.environ if env is None else env
    personal = resolve_personal_jobs(env)
    if not personal:
        return shared_path
    shared_text = _read(shared_path)
    personal_text = _read(personal)
    names_text = merge_names(_read(os.path.join(os.path.dirname(os.path.abspath(shared_path)), "job-names.txt")),
                             _read(os.path.join(os.path.dirname(personal), "job-names.txt")))
    joined, warnings = merge_text(shared_text, personal_text, personal)
    for w in warnings:
        _warn(w)
    h = hashlib.sha256((joined + "\0" + names_text).encode("utf-8")).hexdigest()[:16]
    root = _cache_root(env)
    d = os.path.join(root, h)
    try:
        os.makedirs(d, mode=0o700, exist_ok=True)
        mp = os.path.join(d, "jobs.md")
        if _read(mp) != joined:
            _atomic_write(mp, joined)
        np_ = os.path.join(d, "job-names.txt")
        if _read(np_) != names_text:
            _atomic_write(np_, names_text)
        _prune(root, keep=d)
        return mp
    except OSError as e:
        _warn("could not write the joined job table (%s: %s); using the shared table only" % (type(e).__name__, e))
        return shared_path


def _prune(root, keep):
    """Keep the newest KEEP_CACHES joined copies (each is two small files)."""
    try:
        dirs = [os.path.join(root, n) for n in os.listdir(root) if re.fullmatch(r"[0-9a-f]{16}", n)]
        dirs = [d for d in dirs if os.path.isdir(d) and d != keep]
        dirs.sort(key=lambda d: os.path.getmtime(d), reverse=True)
        import shutil
        for d in dirs[KEEP_CACHES - 1:]:
            shutil.rmtree(d, ignore_errors=True)
    except OSError:
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="join the shared job table with the personal one")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--manifest", metavar="SHARED_JOBS_MD", help="print the path a reader should open")
    g.add_argument("--personal", action="store_true", help="print the personal jobs.md path, or nothing")
    a = ap.parse_args(argv)
    if a.personal:
        p = resolve_personal_jobs()
        if p:
            print(p)
        return 0
    print(effective_manifest(a.manifest))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as e:  # a reader must never lose the shared table because the join broke
        _warn("join failed (%s: %s); using the shared table only" % (type(e).__name__, e))
        if "--manifest" in sys.argv:
            i = sys.argv.index("--manifest")
            if i + 1 < len(sys.argv):
                print(sys.argv[i + 1])
        sys.exit(0)
