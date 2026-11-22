#!/usr/bin/env python3
"""component_page.py — round five step 5: the component page's generator and stamper.

The as-built half reads ORIGIN ONLY (never the working tree, except to count
drift); the status half copies receipt tiles that checks wrote — this tool is
NOT a status runner and runs no checks itself. It never writes outside the two
machine fences on the page (AS-BUILT and STATUS).

Contract/test: system/tools/tests/test_component_page.sh (must print ALL PASS).
# not-wired-yet: built this session to its test's contract only — the task forbade
# touching register.jsonl/hooks.json, so no caller is registered; wiring is a
# separate step the owner approved (round five step 5 follow-up).
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

GENERATOR = "system/tools/organism/component_page.py"


# ── small helpers ────────────────────────────────────────────────────────────

def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def git(repo, *args):
    return sh(["git", "-C", repo, *args])


def utcnow():
    return datetime.now(timezone.utc)


def iso_utc(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_dt(s):
    if not s:
        return None
    s = str(s).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def strip_comment(line):
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
            continue
        if ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def split_top(s):
    parts, buf, depth, q = [], [], 0, None
    for ch in s:
        if q:
            buf.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
            buf.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_value(v):
    v = v.strip()
    if v.startswith("{") and v.endswith("}"):
        d = {}
        for part in split_top(v[1:-1]):
            if ":" not in part:
                continue
            k, _, vv = part.partition(":")
            d[unquote(k)] = parse_value(vv)
        return d
    if v.startswith("[") and v.endswith("]"):
        return [parse_value(x) for x in split_top(v[1:-1])]
    v = unquote(v)
    if v == "true":
        return True
    if v == "false":
        return False
    try:
        return int(v)
    except ValueError:
        return v


def parse_frontmatter(text):
    """Minimal YAML-ish frontmatter parser. Returns (fm, body_start_line_index)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, 0
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, 0
    fm, key = {}, None
    for line in lines[1:end]:
        s = strip_comment(line)
        if not s.strip():
            continue
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", s)
        if m and not line[:1] in (" ", "\t") and not line.lstrip().startswith("- "):
            key = m.group(1)
            val = m.group(2).strip()
            fm[key] = [] if val == "" else parse_value(val)
            continue
        if s.strip().startswith("- ") and key is not None:
            if not isinstance(fm.get(key), list):
                fm[key] = [fm[key]]
            fm[key].append(parse_value(s.strip()[2:]))
    return fm, end + 1


def glob_re(g):
    """Scope glob: ** matches any depth, * stays within one path segment."""
    out, i = "", 0
    while i < len(g):
        c = g[i]
        if c == "*":
            if i + 1 < len(g) and g[i + 1] == "*":
                out += ".*"
                i += 2
                continue
            out += "[^/]*"
            i += 1
            continue
        if c == "?":
            out += "[^/]"
            i += 1
            continue
        out += re.escape(c)
        i += 1
    return re.compile("^" + out + "$")


# ── fence machinery ──────────────────────────────────────────────────────────

def find_fence(lines, name):
    b = None
    for i, l in enumerate(lines):
        if l.strip().startswith("<!-- %s:BEGIN" % name):
            b = i
            break
    if b is None:
        return None
    for j in range(b + 1, len(lines)):
        if lines[j].strip() == "<!-- %s:END -->" % name:
            return (b, j)
    return None


def fence_body(lines, b, j):
    inner = lines[b + 1:j]
    return "\n".join(inner) + ("\n" if inner else "")


def begin_sha(lines, b):
    m = re.search(r"sha256=([0-9a-f]{64})", lines[b])
    return m.group(1) if m else None


def body_hash(body):
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def write_block(page, name, attrs, new_body):
    """Replace the named fence. Returns True if a hand edit was refused."""
    with open(page, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fr = find_fence(lines, name)
    refused = False
    n = 0
    if fr:
        b, j = fr
        old_body = fence_body(lines, b, j)
        old_sha = begin_sha(lines, b)
        if old_body.strip() and (old_sha is None or old_sha != body_hash(old_body)):
            refused = True
            if old_sha is not None:
                # count actually changed lines (added plus removed), not the difference in length
                n = sum(1 for dl in difflib.unified_diff(old_body.splitlines(), new_body.splitlines(), lineterm="")
                        if dl[:1] in ("+", "-") and dl[:3] not in ("+++", "---"))
            else:
                # a BEGIN line that lost its sha256: nothing to diff against
                n = len(old_body.splitlines())
    refusal = "hand edit refused, overwritten (%d lines changed since the last generation)" % n
    final = new_body
    if refused:
        fl = refusal
        if name == "AS-BUILT" or not new_body.startswith("Status: "):
            final = fl + "\n" + new_body
        else:
            bl = new_body.split("\n")
            idx = 0
            for i, l in enumerate(bl):
                if l.startswith("Status: "):
                    idx = i
                    break
            bl.insert(idx + 1, fl)
            final = "\n".join(bl)
    h = body_hash(final)
    begin_line = "<!-- %s:BEGIN %s sha256=%s -->" % (name, attrs, h)
    new_lines = [begin_line] + final.rstrip("\n").split("\n") + ["<!-- %s:END -->" % name]
    if fr:
        b, j = fr
        lines[b:j + 1] = new_lines
    else:
        lines.extend([""] + new_lines)
    with open(page, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if refused:
        print(refusal)
    return refused


# ── frontmatter-derived scope ────────────────────────────────────────────────

def scope_sets(fm):
    pats = [glob_re(g) for g in fm.get("scope", [])]
    excluded = set()
    for e in fm.get("shared", []):
        if isinstance(e, dict) and e.get("home") is False:
            for p in e.get("paths", []):
                excluded.add(str(p))
    return pats, excluded


def in_scope(path, pats, excluded):
    return path not in excluded and any(p.match(path) for p in pats)


def kind_of(path):
    base = path.rsplit("/", 1)[-1]
    if "tests" in path.split("/") or base.startswith("test_"):
        return "test"
    return "file"


# ── asbuilt ──────────────────────────────────────────────────────────────────

def resolve_source(repo, source, no_fetch):
    """Resolve the source ref. Returns (sha, fetch_failed)."""
    fetch_failed = False
    if "/" in source and not no_fetch:
        remote, branch = source.split("/", 1)
        r = git(repo, "fetch", remote, branch)
        fetch_failed = r.returncode != 0
    r = git(repo, "rev-parse", source)
    return (r.stdout.strip() if r.returncode == 0 else None), fetch_failed


def cmd_asbuilt(args):
    page = args.page
    repo = args.repo
    if not repo:
        r = sh(["git", "-C", str(__import__("os").path.dirname(page) or "."), "rev-parse", "--show-toplevel"])
        if r.returncode != 0:
            print("error: page is not inside a git repository and no --repo given", file=sys.stderr)
            return 2
        repo = r.stdout.strip()
    with open(page, "r", encoding="utf-8") as f:
        text = f.read()
    fm, fm_end = parse_frontmatter(text)
    source = fm.get("source")
    component = fm.get("component")
    if not source or not component:
        print("error: frontmatter needs `component` and `source`", file=sys.stderr)
        return 2
    pats, excluded = scope_sets(fm)

    sha, fetch_failed = resolve_source(repo, source, args.no_fetch)
    if not sha:
        print("error: cannot resolve %s" % source, file=sys.stderr)
        return 2

    lr = git(repo, "ls-tree", "-r", "--name-only", sha)
    all_paths = [l for l in lr.stdout.split("\n") if l]
    files = [f for f in all_paths if in_scope(f, pats, excluded)]

    out = []
    out.append("As built from origin `%s` (@%s):" % (source, sha[:7]))
    out.append("")
    if fetch_failed:
        out.append("origin as of last fetch (fetch failed)")
        out.append("")
    out.append("| kind | path | commit |")
    out.append("| --- | --- | --- |")
    for f in files:
        g = git(repo, "log", "-1", "--format=%h %cs", sha, "--", f)
        parts = g.stdout.strip().split()
        commit = parts[0] if parts else "?"
        date = parts[1] if len(parts) > 1 else "?"
        out.append("| %s | %s | %s %s |" % (kind_of(f), f, commit, date))

    # hooks
    out.append("")
    out.append("Hook wiring (from origin `hooks/hooks.json`):")
    out.append("")
    hj = git(repo, "show", "%s:hooks/hooks.json" % sha)
    hook_rows = []
    if hj.returncode == 0:
        try:
            data = json.loads(hj.stdout)
            for event, entries in (data.get("hooks") or {}).items():
                for entry in entries:
                    matcher = entry.get("matcher", "*")
                    for h in entry.get("hooks", []):
                        cmd = h.get("command", "")
                        m = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"'\s]+)", cmd)
                        if m and m.group(1) in files:
                            hook_rows.append((m.group(1), event, matcher))
        except ValueError:
            pass
    if hook_rows:
        out.append("| path | event · matcher |")
        out.append("| --- | --- |")
        for p, ev, mt in hook_rows:
            out.append("| %s | %s · %s |" % (p, ev, mt))
    else:
        out.append("(none)")

    # register
    out.append("")
    out.append("Register rows in scope (from origin `system/register/register.jsonl`):")
    out.append("")
    rj = git(repo, "show", "%s:system/register/register.jsonl" % sha)
    reg_rows, registered = [], set()
    if rj.returncode == 0:
        for line in rj.stdout.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            p = str(row.get("path", "")).lstrip("/")
            registered.add(p)
            if in_scope(p, pats, excluded):
                reg_rows.append("| %s | %s | %s | %s |" % (row.get("id", "?"), row.get("path", p), row.get("type", "?"), row.get("sha", "?")))
    if reg_rows:
        out.append("| id | path | type | sha |")
        out.append("| --- | --- | --- | --- |")
        out.extend(reg_rows)
    else:
        out.append("(none)")
    unreg = [f for f in files if f.endswith((".sh", ".py")) and kind_of(f) == "file" and f not in registered]
    for f in unreg:
        out.append("in scope, unregistered: `%s`" % f)

    # jobs
    if "system/jobs.md" in files:
        out.append("")
        out.append("Jobs (from origin `system/jobs.md`):")
        out.append("")
        jm = git(repo, "show", "%s:system/jobs.md" % sha)
        job_rows = []
        if jm.returncode == 0:
            in_block = False
            for line in jm.stdout.split("\n"):
                s = line.strip()
                if s.startswith("```"):
                    if in_block:
                        break
                    if s == "```jobs":
                        in_block = True
                    continue
                if in_block and s:
                    if s.startswith("#"):
                        continue
                    cols = [c.strip() for c in s.split("|")]
                    if len(cols) == 9 and re.match(r"^[a-z0-9][a-z0-9-]*$", cols[0]):
                        filled = all(c != "TBD" for c in cols[3:8])
                        job_rows.append("| %s | %s | %s | %s |" % (cols[0], cols[1], cols[2], "filled" if filled else "TBD"))
        if job_rows:
            out.append("| name | enabled | interval | contract |")
            out.append("| --- | --- | --- | --- |")
            out.extend(job_rows)
        else:
            out.append("(no job rows)")

    # pointers: backticked repo-path tokens in the body OUTSIDE the two fences
    lines = text.split("\n")
    skip = set(range(0, fm_end))
    for name in ("AS-BUILT", "STATUS"):
        fr = find_fence(lines, name)
        if fr:
            skip.update(range(fr[0], fr[1] + 1))
    scan = [l for i, l in enumerate(lines) if i not in skip]
    flags = []
    seen = set()
    blobset = set(all_paths)
    def resolve_pointer(tok, path, ln):
        """Flag string for one pointer token, or None if it resolves at origin."""
        if ln is None:
            if path in blobset:
                return None
            t = git(repo, "cat-file", "-t", "%s:%s" % (sha, path))
            if t.returncode == 0 and t.stdout.strip() in ("blob", "tree"):
                return None  # a directory (tree) resolves
            return "named but missing: `%s` ⛔ not on origin" % tok
        if path not in blobset:
            return "named but missing: `%s` ⛔ not on origin" % tok
        c = git(repo, "show", "%s:%s" % (sha, path))
        nlines = len(c.stdout.splitlines())
        if ln > nlines:
            return "named but missing: `%s` (file has %d lines) ⛔ line past the end at origin" % (tok, nlines)
        return None

    for tok in re.findall(r"`([^`\n]+)`", "\n".join(scan)):
        if tok in seen:
            continue
        seen.add(tok)
        if "/" not in tok or " " in tok:
            continue
        if tok.startswith(("~", "<", "$", "http")):
            continue
        m = re.match(r"^(.+?):(\d+)$", tok)
        path, ln = (m.group(1), int(m.group(2))) if m else (tok, None)
        f = resolve_pointer(tok, path, ln)
        if f:
            flags.append(f)

    # bare (unbackticked) repo-path tokens, optional :N / :N-M / :N,M suffix; a range/list checks its LAST number
    bare_re = re.compile(
        r"(?:canon|system|shared|hooks|\.claude|\.github|desks|skills)/[\w./-]+(?::\d+(?:-\d+|,\d+)?)?")
    for line in scan:
        cleaned = re.sub(r"`[^`\n]+`", " ", line)  # backticked spans were scanned above
        for m in bare_re.finditer(cleaned):
            tok = m.group(0).rstrip(".")
            if tok in seen:
                continue
            seen.add(tok)
            m2 = re.match(r"^(.+?):(\d+)(?:-(\d+)|(,(\d+)))?$", tok)
            if m2:
                path = m2.group(1)
                ln = int(m2.group(5) or m2.group(3) or m2.group(2))
            else:
                path, ln = tok, None
            f = resolve_pointer(tok, path, ln)
            if f:
                flags.append(f)
    if flags:
        out.append("")
        out.append("Pointers:")
        out.append("")
        out.extend(flags)

    # not on origin
    diff = []
    if files:
        d = git(repo, "diff", "--name-only", sha, "--", *files)
        diff = [l for l in d.stdout.split("\n") if l]
    u = git(repo, "ls-files", "--others", "--exclude-standard")
    untracked = [l for l in u.stdout.split("\n") if l and in_scope(l, pats, excluded)]
    out.append("")
    out.append("not on origin: %d" % (len(diff) + len(untracked)))

    # pointed at by
    needle = "canon/components/%s.md" % component
    pointed = []
    for p in all_paths:
        if p.startswith("canon/"):
            c = git(repo, "show", "%s:%s" % (sha, p))
            if needle in c.stdout:
                pointed.append(p)
    out.append("")
    if pointed:
        for p in pointed:
            out.append("pointed at by: `%s`" % p)
    else:
        out.append("pointed at by: none")

    if args.no_fetch:
        lr = git(repo, "log", "-1", "--format=%cI", source)
        when = lr.stdout.strip() if lr.returncode == 0 and lr.stdout.strip() else "unknown"
        fetched_attr = "none (--no-fetch; ref as of %s)" % when
    else:
        fetched_attr = iso_utc(utcnow())
    attrs = "generator=%s source=%s@%s fetched=%s" % (GENERATOR, source, sha[:7], fetched_attr)
    write_block(page, "AS-BUILT", attrs, "\n".join(out) + "\n")
    return 0


# ── stamp ────────────────────────────────────────────────────────────────────

RANK = {"untested": 0, "unproven": 1, "PARTIAL": 2, "LIVE": 3}


def reading_label(reading):
    if reading == "untested" or reading.startswith("untested ("):
        return "untested", RANK["untested"]
    if reading.startswith("unproven"):
        return "unproven", RANK["unproven"]
    if reading.startswith("PARTIAL"):
        return "PARTIAL", RANK["PARTIAL"]
    return "LIVE", RANK["LIVE"]


def cmd_stamp(args):
    page = args.page
    repo = args.repo
    if not repo:
        r = sh(["git", "-C", os.path.dirname(page) or ".", "rev-parse", "--show-toplevel"])
        if r.returncode != 0:
            print("error: page is not inside a git repository and no --repo given", file=sys.stderr)
            return 2
        repo = r.stdout.strip()
    brain = args.brain
    if not brain:
        r = sh(["python3", repo.rstrip("/") + "/shared/brain_root.py", "--quiet"])
        brain = r.stdout.strip()
    with open(page, "r", encoding="utf-8") as f:
        text = f.read()
    fm, _ = parse_frontmatter(text)
    source = fm.get("source")
    expected = [c for c in fm.get("checks", []) if isinstance(c, dict)]
    page_component = fm.get("component")
    if not expected:
        # no `checks:` declared: nothing can ever earn a label here — say so, do not crash
        status = "Status: untested — no check exists · not built yet: (no check declared) · Serves: see the page's Quality characteristics"
        write_block(page, "STATUS", "stamper=%s stamped=%s" % (GENERATOR, iso_utc(utcnow())), status + "\n")
        return 0
    now = parse_dt(args.now) if args.now else utcnow()

    # current origin sha (fetch unless --no-fetch); a failed fetch is remembered, never hidden
    current_sha = None
    fetch_note = None
    if source and "/" in source:
        if args.no_fetch:
            fetch_note = "--no-fetch"
        else:
            remote, branch = source.split("/", 1)
            if git(repo, "fetch", remote, branch).returncode != 0:
                fetch_note = "fetch failed"
    if source:
        r = git(repo, "rev-parse", source)
        if r.returncode == 0:
            current_sha = r.stdout.strip()

    # the page's whole in-scope file list at the current origin sha (home:false paths excluded);
    # covered paths come from the PAGE, never from a receipt's covers field
    page_files = []
    if current_sha:
        pats, excluded = scope_sets(fm)
        lsr = git(repo, "ls-tree", "-r", "--name-only", current_sha)
        page_files = [l for l in lsr.stdout.split("\n") if l and in_scope(l, pats, excluded)]

    # read receipts
    receipts = []
    corrupt_receipts = []
    malformed_receipts = []
    for rp in fm.get("receipts", []):
        full = str(rp).replace("<brain>", brain)
        data = None
        if os.path.exists(full):  # a missing file is "receipt missing"; an unreadable one is corrupt
            try:
                with open(full, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    data = None
            except Exception:
                data = None
            if data is None:
                corrupt_receipts.append(str(rp))
        receipts.append((str(rp), data))   # display the <brain> form: the page is public, the expanded path is personal

    def eval_check(c, rdata, rpath):
        """Returns the reading dict for one check inside one readable receipt."""
        base = {"receipt": rpath, "result": c.get("result", "?"), "date": None,
                "sha": None, "clean": None, "window": None, "untested": c.get("untested", ""),
                "not_tested": [str(x) for x in (rdata.get("not_tested") or []) if str(x)],
                "suspect": False}
        if str(rdata.get("component")) != str(page_component):
            base["reading"] = "unproven (receipt is for another component)"
            base["rank"] = RANK["unproven"]
            return base
        rsha = rdata.get("origin_sha")
        if not isinstance(rsha, str) or not re.fullmatch(r"[0-9a-f]{40}", rsha):
            base["reading"] = "unproven (no origin sha)"
            base["rank"] = RANK["unproven"]
            return base
        base["sha"] = rsha
        base["clean"] = rdata.get("clean_tree") is True  # clean ONLY when the JSON boolean true
        last = parse_dt(rdata.get("last_run"))
        window = rdata.get("stale_after_s")
        if isinstance(window, bool) or not isinstance(window, int) or window > 2592000:
            base["reading"] = "unproven (bad window)"
            base["rank"] = RANK["unproven"]
            return base
        base["window"] = window
        base["date"] = last
        if not base["clean"]:
            base["reading"] = "unproven (dirty tree)"
            base["rank"] = RANK["unproven"]
            return base
        if last is not None and last > now + timedelta(minutes=5):
            base["reading"] = "unproven (dated in the future)"
            base["rank"] = RANK["unproven"]
            return base
        if last is None or now > last + timedelta(seconds=window):
            base["reading"] = "unproven (past window)"
            base["rank"] = RANK["unproven"]
            return base
        if not current_sha:
            base["reading"] = "unproven (origin unreadable)"
            base["rank"] = RANK["unproven"]
            return base
        # the receipt's sha must sit ON the current source branch, never merely be matched against origin
        mb = git(repo, "merge-base", "--is-ancestor", rsha, current_sha)
        if mb.returncode != 0:
            base["reading"] = "unproven (sha not on origin)"
            base["rank"] = RANK["unproven"]
            return base
        # every covered path is the page's whole in-scope list at the current origin sha
        if page_files:
            g = git(repo, "log", "--format=%H", "%s..%s" % (rsha, current_sha), "--", *page_files)
            if g.returncode != 0:
                base["reading"] = "unproven (could not compare)"
                base["rank"] = RANK["unproven"]
                return base
            if g.stdout.strip():
                base["reading"] = "unproven (code changed since)"
                base["rank"] = RANK["unproven"]
                return base
        if c.get("result") == "FAIL":
            base["reading"] = "PARTIAL"
            base["rank"] = RANK["PARTIAL"]
            return base
        if c.get("result") != "PASS":  # only an exact PASS earns above PARTIAL
            val = c.get("result")
            base["result"] = val if val is not None else "?"
            base["reading"] = "unproven (check did not pass or fail: %s)" % (val if val is not None else "?")
            base["rank"] = RANK["unproven"]
            return base
        if c.get("refused_once") is not True:
            base["reading"] = "PARTIAL (suspect)"
            base["suspect"] = True
            base["rank"] = RANK["PARTIAL"]
            return base
        base["reading"] = "LIVE"
        base["rank"] = RANK["LIVE"]
        return base

    # fix 7: expected checks = the page's checks list UNION every check id in a readable receipt
    page_ids = [c.get("id", "?") for c in expected]
    watches_by_id = {c.get("id", "?"): c.get("watches", "") for c in expected}
    extra_ids = []
    for rp, data in receipts:
        if not data:
            continue
        for rc in (data.get("checks") or []):
            if not isinstance(rc, dict):  # fix 3: skip it, but name it in the block
                if rp not in malformed_receipts:
                    malformed_receipts.append(rp)
                continue
            cid = rc.get("id")
            if cid is not None and cid not in page_ids and cid not in extra_ids:
                extra_ids.append(cid)

    def pick_best(cid):
        best = None
        for rpath, data in receipts:
            if not data:
                continue
            for rc in data.get("checks", []):
                if isinstance(rc, dict) and rc.get("id") == cid:
                    info = eval_check(rc, data, rpath)
                    if best is None or info["rank"] < best["rank"]:
                        best = info
        if best is None:
            if not any(d for _, d in receipts):
                missing = [p for p, d in receipts if not d]
                return {"reading": "unproven (receipt missing)", "rank": RANK["unproven"],
                        "receipt": missing[0] if missing else "?", "result": None, "date": None,
                        "sha": None, "clean": None, "window": None, "untested": "",
                        "not_tested": [], "suspect": False}
            return {"reading": "untested", "rank": RANK["untested"], "receipt": None,
                    "result": None, "date": None, "sha": None, "clean": None,
                    "window": None, "untested": "", "not_tested": [], "suspect": False}
        return best

    # step 6(b): a page check may declare its part DORMANT (built, deliberately not in
    # use) or not_run (honestly "not run here", with the reason). The declaration wins
    # over any receipt: DORMANT stands outside the weakest-wins roll-up and is counted
    # beside it; "not run here" reads as untested with that reason, never green.
    dormant_ids = set(c.get("id") for c in expected if c.get("dormant") is True and c.get("id") is not None)
    notrun_by_id = dict((c.get("id"), c) for c in expected if c.get("not_run") and c.get("id") is not None)

    def declared_reading(cid):
        base = {"receipt": None, "result": None, "date": None, "sha": None, "clean": None,
                "window": None, "untested": "", "not_tested": [], "suspect": False}
        if cid in dormant_ids:
            base["reading"] = "DORMANT (built, not in use)"
            base["rank"] = None  # outside the weakest-wins order
            return base
        base["reading"] = "untested (not run here: %s)" % notrun_by_id[cid].get("not_run")
        base["rank"] = RANK["untested"]
        return base

    rows = []
    readings = []
    for cid in page_ids + extra_ids:
        if cid in dormant_ids or cid in notrun_by_id:
            best = declared_reading(cid)
        else:
            best = pick_best(cid)
        readings.append(best)
        unt = best.get("untested") or "; ".join(best.get("not_tested") or [])  # fix 8
        rows.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            cid, watches_by_id.get(cid, "—"),
            best.get("result") if best.get("result") is not None else "—",
            best["date"].date().isoformat() if best.get("date") else "—",
            (best["sha"][:7] if best.get("sha") else "—"),
            ("yes" if best.get("clean") else "no") if best.get("clean") is not None else "—",
            best["window"] if best.get("window") is not None else "—",
            best.get("receipt") or "—",
            unt or "—",
            best["reading"]))

    n_dormant = sum(1 for r in readings if r.get("rank") is None)
    active = [r for r in readings if r.get("rank") is not None]
    labels = [reading_label(r["reading"]) for r in active]
    weakest = min(labels, key=lambda t: t[1])[0] if labels else None
    if fetch_note and weakest == "LIVE":  # fix 4: an unread origin cannot earn LIVE
        weakest = "PARTIAL"
    # only the receipts that actually stand behind the label set the dates
    contributed = set(r["receipt"] for r in readings if r.get("receipt"))
    readable = [(p, d) for p, d in receipts if d and p in contributed]
    if readable:
        lasts = [parse_dt(d.get("last_run")) for _, d in readable if parse_dt(d.get("last_run"))]
        valids = []
        for _, d in readable:
            l = parse_dt(d.get("last_run"))
            w = d.get("stale_after_s")
            if isinstance(w, bool) or not isinstance(w, int) or w > 2592000:
                w = None  # a bad window never extends validity
            if l and w is not None:
                valids.append(l + timedelta(seconds=w))
        checked = min(lasts).date().isoformat() if lasts else "unknown"
        valid_until = min(valids).date().isoformat() if valids else "unknown"
    else:
        checked = valid_until = "unknown"
    receipts_str = " ".join(p for p, _ in receipts) if receipts else "(none declared)"

    n_untested = sum(1 for l, _ in labels if l == "untested")
    n_total = len(labels)
    dorm_suffix = " · %d dormant" % n_dormant if n_dormant else ""
    if readings and n_total == 0:
        # every check on the page is DORMANT: the page itself reads DORMANT
        status = "Status: DORMANT (all %d checks dormant) · checked unknown · valid until unknown · %s" % (
            n_dormant, receipts_str)
    elif n_untested and n_total:
        rest = [lab for lab, rk in labels if lab != "untested"]
        best_earned = min(rest, key=lambda l: RANK.get(l, 0)) if rest else "none"
        if fetch_note and best_earned == "LIVE":  # fix 4
            best_earned = "PARTIAL"
        status = "Status: untested (%d of %d checks missing) · best earned %s · checked %s · valid until %s · %s" % (
            n_untested, n_total, best_earned, checked, valid_until, receipts_str)
    elif weakest == "unproven":
        reasons = sorted({r["reading"][len("unproven ("):-1] for r in readings if r["reading"].startswith("unproven (")})
        reason = reasons[0] if len(reasons) == 1 else "; ".join(reasons)
        status = "Status: unproven (%s) · checked %s · valid until %s · %s" % (reason, checked, valid_until, receipts_str)
    else:
        status = "Status: %s · checked %s · valid until %s · %s" % (weakest, checked, valid_until, receipts_str)
    if n_total:
        status += dorm_suffix

    # health line
    health_paths = fm.get("health", []) or []
    if not health_paths:
        health = "Health: no tile declared"
    else:
        parts = []
        for hp in health_paths:
            full = str(hp).replace("<brain>", brain)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    hd = json.load(f)
                parts.append("`%s`: %s (last %s, window %ss)" % (hp, hd.get("status", "?"), hd.get("last_run", "?"), hd.get("stale_after_s", "?")))
            except Exception:
                parts.append("`%s`: missing" % hp)
        health = "Health: " + "; ".join(parts)

    body = [status,
            'Past "valid until", read this as unproven, whatever the word says.',
            health,
            "",
            "| check | watches | result | date | at sha | clean | window | receipt | untested | reading |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    if fetch_note:
        body.insert(2, "origin not fetched (%s); cannot read LIVE" % fetch_note)  # fix 4
    body.extend(rows)
    nt_all = []
    for _, d in readable:
        for item in (d.get("not_tested") or []):
            item = str(item)
            if item and item not in nt_all:
                nt_all.append(item)
    if nt_all:
        body.append("not tested by these checks: " + "; ".join(nt_all))
    for rp in corrupt_receipts:
        body.append("receipt refused (corrupt): %s" % rp)
    for cid in extra_ids:  # fix 7
        body.append("check in receipt but not on the page: %s" % cid)
    for rp in malformed_receipts:  # fix 3
        body.append("malformed check entry in receipt (skipped): %s" % rp)
    attrs = "stamper=%s stamped=%s" % (GENERATOR, iso_utc(utcnow()))
    write_block(page, "STATUS", attrs, "\n".join(body) + "\n")
    return 0


# ── verify ───────────────────────────────────────────────────────────────────

def cmd_verify(args):
    with open(args.page, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    for name in ("AS-BUILT", "STATUS"):
        fr = find_fence(lines, name)
        if not fr:
            continue
        b, j = fr
        body = fence_body(lines, b, j)
        old_sha = begin_sha(lines, b)
        if old_sha and body_hash(body) != old_sha:
            print("%s block does not match its sha256 — hand edited" % name)
            return 1
    return 0


# ── entry ────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="component page generator and stamper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("asbuilt")
    p.add_argument("page")
    p.add_argument("--repo")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_asbuilt)

    p = sub.add_parser("stamp")
    p.add_argument("page")
    p.add_argument("--repo")
    p.add_argument("--brain")
    p.add_argument("--now")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_stamp)

    p = sub.add_parser("verify")
    p.add_argument("page")
    p.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
