#!/usr/bin/env python3
"""cut_receipt.py -- archive-before-cut check (Round C 4, switch fc_archive_before_cut in system/hooks/roundB.conf).

RULE (Enver 2026-10-30: "I need to make sure that the pad archive is enforced."): text removed from a Harness SOP or a
canon file must FIRST be copied verbatim to <name>.history.md beside it, under a dated heading that carries a reason.
This module computes what an edit REMOVES and refuses unless each removed passage is already in that log.

HOW IT IS CALLED
  guard_canon_write.sh  -> `python3 lib/cut_receipt.py` with the hook payload on stdin (Write / Edit / MultiEdit)
  lib/build_mode.py     -> check_cut(...) for a Bash overwrite (>, tee, cp, mv, sed -i ...) of an existing SOP/canon file
No second archiver: the log is written by system/tools/save/pad_archive.py `cutlog` (copy -> read back -> RECEIPT), the same
tool and the same fail-closed receipt idea as the brief archive. Typing the block by hand in the same format also works.

WHAT COUNTS AS A CUT (stated, deliberate)
  * The REMOVED text = what the old text had that the new text does not: line diff first, then a word diff inside changed
    blocks. Pure additions, whitespace-only changes, re-wrapping and text that merely MOVED inside the same file remove nothing.
  * REWORDING removes the old wording, so it counts: the old wording must be logged. (Otherwise rewording is a free way to cut.)
  * THRESHOLD: the edit is ignored when everything it removes adds up to fewer than 40 characters (whitespace-collapsed):
    typo fixes, a changed number, a date. At 40 or more, EVERY removed run must be in the log.
  * A passage is "in the log" when its whitespace-collapsed text is inside ONE dated block of <name>.history.md whose heading
    (or the 3 lines after it) says `reason: <something>`. If the whole passage is not found in one piece, each of its lines of
    6+ characters must be found (so a passage logged line by line still counts).
  * A <name>.history.md file is never itself guarded. A NEW file, or an empty one, has nothing to lose.

# WHO-COULD-THIS-BREAK: a session (or the maintainer) that tidies, de-duplicates, condenses or moves text out of an SOP or canon
#   file, or rewords a rule, without logging what left. WAY-THROUGH: log the passage first, then retry the same edit unchanged:
#   python3 <code>/system/tools/save/pad_archive.py cutlog <the SOP> --reason "<why>" --start A --end B   (or --text-file F);
#   it prints RECEIPT. No GitHub, no network: it is a local append. The deny message prints this command ready to paste.
# FAIL_POSTURE: degrade-safe -- an internal error here prints a note on stderr and allows (the matcher is broad: Write|Edit|Bash).
"""
import difflib
import importlib.util
import json
import os
import re
import sys

MIN_TOTAL = 40          # characters removed (whitespace-collapsed) below which an edit is ignored
MIN_LINE = 6            # fallback line-by-line coverage ignores lines shorter than this
BIG = 4_000_000         # word-diff cost guard (tokens_old * tokens_new)
REASON_RX = re.compile(r"reason\W{0,6}\s*\S{3}", re.I)
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}")
HEAD_RX = re.compile(r"^#{1,6}\s")


def norm(s):
    return " ".join(s.split())


def removed_passages(old, new):
    """-> list of removed passages (strings; multi-line ones keep their newlines), or [] when the edit is tiny/additive."""
    if old == new:
        return []
    newn = norm(new)
    ol, nl = old.split("\n"), new.split("\n")
    runs = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ol, nl, autojunk=False).get_opcodes():
        if tag == "delete":
            runs.append("\n".join(ol[i1:i2]))
        elif tag == "replace":
            ot, nt = " ".join(ol[i1:i2]).split(), " ".join(nl[j1:j2]).split()
            if len(ot) * len(nt) > BIG:
                newset = {norm(x) for x in nl[j1:j2]}
                runs.extend(x for x in ol[i1:i2] if norm(x) not in newset)
                continue
            for t, a1, a2, _b1, _b2 in difflib.SequenceMatcher(None, ot, nt, autojunk=False).get_opcodes():
                if t in ("delete", "replace"):
                    runs.append(" ".join(ot[a1:a2]))
    keep = []
    for r in runs:
        n = norm(r)
        if n and n not in newn:      # still present elsewhere in the new text -> moved, not cut
            keep.append(r)
    if sum(len(norm(r)) for r in keep) < MIN_TOTAL:
        return []
    return keep


def history_path(doc):
    d, base = os.path.split(doc)
    stem = base[:-3] if base.endswith(".md") else base
    return os.path.join(d, stem + ".history.md")


def logged_text(hist):
    """Whitespace-collapsed text of every VALID dated block (heading with a date + a reason), joined by NULs."""
    try:
        with open(hist, encoding="utf-8", errors="replace") as f:
            lines = f.read().split("\n")
    except OSError:
        return ""
    blocks, cur, fence = [], None, None
    for ln in lines:
        s = ln.strip()
        if fence is None and (s.startswith("~~~") or s.startswith("```")):
            fence = s[:3]
        elif fence is not None and s.startswith(fence):
            fence = None
        elif fence is None and HEAD_RX.match(ln) and DATE_RX.search(ln):
            cur = [ln]; blocks.append(cur); continue
        if cur is not None:
            cur.append(ln)
    out = []
    for b in blocks:
        head = " ".join([b[0]] + [x for x in b[1:] if x.strip()][:3])
        if REASON_RX.search(head):
            out.append(norm("\n".join(b)))
    return "\x00".join(out)


def missing_passages(passages, hist):
    log = logged_text(hist)
    miss = []
    for p in passages:
        pn = norm(p)
        if pn in log:
            continue
        lines = [norm(x) for x in p.split("\n")]
        lines = [x for x in lines if len(x) >= MIN_LINE]
        if len(lines) > 1 and all(x in log for x in lines):
            continue
        miss.append(p)
    return miss


def _load_build_mode():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("_bm_for_cut", os.path.join(here, "build_mode.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _locate(text, passage):
    i = text.find(passage)
    if i < 0:
        return None
    a = text.count("\n", 0, i) + 1
    return a, a + passage.count("\n") + 1


def deny_message(path, miss, old_text, code):
    tool = os.path.join(code or "<code-root>", "system", "tools", "save", "pad_archive.py")
    hist = history_path(path)
    name, hname = os.path.basename(path), os.path.basename(hist)
    shown = []
    for p in miss[:3]:
        q = norm(p)
        shown.append('"%s%s"' % (q[:110], "..." if len(q) > 110 else ""))
    loc = _locate(old_text, miss[0]) if old_text else None
    if loc:
        cmd = 'python3 "%s" cutlog "%s" --reason "<why this text is leaving>" --start %d --end %d' % (tool, path, loc[0], loc[1])
    else:
        cmd = 'python3 "%s" cutlog "%s" --reason "<why this text is leaving>" --text-file <a file holding the exact text>' % (tool, path)
    return ("BLOCKED (archive before cut): this change removes %d passage(s) from %s that are not in %s: %s. "
            "WHY: text cut from an SOP or canon file is gone for good unless it was copied somewhere first; Enver's rule is that the "
            "copy comes BEFORE the cut, verbatim, with a date and a reason. "
            "WAY THROUGH: log the passage first, then retry the SAME edit: %s  (it copies the text into %s, reads it back, prints RECEIPT; "
            "no GitHub or network needed). Or append by hand to %s: a heading `## YYYY-MM-DD - reason: <why>` followed by the exact "
            "text. Several cuts: log each, or log them together in one block. Pure additions, whitespace changes and edits that remove "
            "under %d characters need nothing. RULE: system/hooks/lib/cut_receipt.py (switch fc_archive_before_cut in system/hooks/roundB.conf)."
            % (len(miss), name, hname, "; ".join(shown), cmd, hname, hname, MIN_TOTAL))


def check_cut(path, old_text, new_text, code):
    """-> deny message or None. `path` absolute; old_text is the file as it is now; new_text what it would become."""
    if os.path.basename(path).endswith(".history.md"):
        return None
    if not old_text.strip():
        return None
    bm = _load_build_mode()
    if not bm.protected_doc(path, code or ""):
        return None
    passages = removed_passages(old_text, new_text)
    if not passages:
        return None
    miss = missing_passages(passages, history_path(path))
    if not miss:
        return None
    return deny_message(path, miss, old_text, code)


def check_payload(d):
    """Write / Edit / MultiEdit hook payload -> deny message or None."""
    tool = d.get("tool_name") or ""
    ti = d.get("tool_input") or {}
    if tool not in ("Write", "Edit", "MultiEdit"):
        return None
    fp = ti.get("file_path") or ""
    if not fp:
        return None
    bm = _load_build_mode()
    path = bm.resolve(fp, d.get("cwd") or os.getcwd())
    code = bm.code_root()
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            cur = f.read()
    except OSError:
        return None          # new file
    if tool == "Write":
        return check_cut(path, cur, ti.get("content", ""), code)
    edits = [ti] if tool == "Edit" else (ti.get("edits") or [])
    text = cur
    for e in edits:
        o, n = e.get("old_string", ""), e.get("new_string", "")
        if o and o in text:
            text = text.replace(o, n) if (e.get("replace_all") or tool == "MultiEdit" and e.get("replace_all")) else text.replace(o, n, 1)
    return check_cut(path, cur, text, code)


def main():
    try:
        d = json.loads(sys.stdin.read())
        msg = check_payload(d)
    except Exception as e:           # degrade-safe: say so, allow
        sys.stderr.write("cut_receipt: internal error (%s); allowing\n" % e)
        return 0
    if msg:
        sys.stderr.write(json.dumps({"decision": "block", "reason": msg}) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
