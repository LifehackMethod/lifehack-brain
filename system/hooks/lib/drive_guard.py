#!/usr/bin/env python3
"""drive_guard.py -- classify a Google Drive delete for guard_drive_destructive.sh (Round C, fine china).

Reads the hook payload (JSON) on stdin. One line on stdout, tab separated:
  PASS
  BULK <why>            more than one file, a query/wildcard delete, a loop/xargs of deletes, or empty-trash
  SINGLE <fileId|?>     one file deleted/trashed (the caller decides whether it is a Sheet)
The command reader is the repo's shared gws parser (lib/gws_guard.py: bash -c bodies, argv lists, assignment prefixes),
plus a quote-blind scan for the loop shapes that parser does not segment (xargs ... gws, do gws ...).
Nothing is executed; nothing is written.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gws_guard  # noqa: E402

DELETE_VERBS = {"delete", "trash"}
EMPTY_VERBS = {"emptytrash"}
LOOP = re.compile(r"\bxargs\b|\bparallel\b|\bfor\b|\bwhile\b|\buntil\b|-exec\b|-execdir\b")
QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
# a Drive delete written as text outside quotes (catches `do gws drive files delete`, `xargs -I{} gws drive ...`)
RAW = re.compile(r"\bgws\b[^|;&\n]*?\bdrive\b[^|;&\n]*?\b(delete|emptytrash|trash)\b", re.I)
ID_JSON = re.compile(r"fileId\\*[\"']?\s*[:=]\s*\\*[\"']?([A-Za-z0-9_\-$\{\}\(\)]+)")
IDS_LIST = re.compile(r"(?:fileIds|ids)\\*[\"']?\s*[:=]\s*\[([^\]]*)\]", re.I)
QUERY = re.compile(r"[\"']?\bq\b[\"']?\s*[:=]|--query\b|--all\b|\*", re.I)


def _bodies(cmd):
    out = [cmd]
    for m in gws_guard._EXECWRAP.finditer(cmd):
        inner = m.group("body") or m.group("body2")
        if inner:
            out.append(inner.strip("'\""))
    return out


def classify_bash(cmd):
    cmd = cmd.replace("\\\n", " ")
    cmd = gws_guard._strip_quoted_heredocs(cmd)
    stmts = []   # one entry per Drive delete/empty statement: (verb, text)
    for toks in gws_guard.gws_segments(cmd):
        low = [t.strip("'\"").lower() for t in toks]
        if "drive" not in low:
            continue
        chain = [c.lower() for c in gws_guard.op_chain(toks, "drive")]
        if set(chain) & EMPTY_VERBS or chain[:2] == ["trash", "empty"]:
            stmts.append(("empty", " ".join(toks)))
        elif set(chain) & DELETE_VERBS:
            stmts.append(("delete", " ".join(toks)))
        elif "update" in chain and re.search(r"trashed\W+true", " ".join(toks), re.I):
            stmts.append(("delete", " ".join(toks)))
    loop = False
    raw_hits = 0
    for body in _bodies(cmd):
        unq = QUOTED.sub(" ", body)
        for m in RAW.finditer(unq):
            raw_hits += 1
        if RAW.search(unq) and LOOP.search(unq):
            loop = True
    if not stmts and not raw_hits:
        return "PASS"
    if any(v == "empty" for v, _ in stmts) or re.search(r"\bemptytrash\b", QUOTED.sub(" ", cmd), re.I):
        return "BULK\temptying the Drive trash"
    if loop:
        return "BULK\ta loop or xargs of Drive deletes"
    n = max(len(stmts), raw_hits)
    if n > 1:
        return "BULK\t%d Drive deletes in one action" % n
    text = stmts[0][1] if stmts else cmd
    m = IDS_LIST.search(text) or IDS_LIST.search(cmd)
    if m and len([x for x in m.group(1).split(",") if x.strip()]) > 1:
        return "BULK\tseveral file ids in one call"
    if QUERY.search(text) and not ID_JSON.search(text):
        return "BULK\ta query or wildcard delete"
    ids = set(ID_JSON.findall(text)) | set(ID_JSON.findall(cmd))
    if len(ids) > 1:
        return "BULK\t%d file ids in one action" % len(ids)
    fid = next(iter(ids), "?")
    return "SINGLE\t" + fid


def kind_of(fid):
    """SHEET <name> | OTHER <name> | UNKNOWN. A sheet this system has opened leaves a marker; otherwise ask Drive
    (one metadata read, 8 s cap, via the same gws binary); if neither answers, UNKNOWN (the caller asks the person)."""
    import subprocess
    if not fid or fid == "?" or re.search(r"[$`{}()]", fid):
        return "UNKNOWN\t"
    mark = os.environ.get("SHEET_LLM_MARKDIR") or os.path.join(os.path.expanduser("~"), ".claude", "run", "sheet-llm")
    if os.path.exists(os.path.join(mark, fid)):
        return "SHEET\t(a sheet this window or an earlier one read)"
    gws = os.environ.get("GWS_BIN") or "gws"
    try:
        r = subprocess.run([gws, "drive", "files", "get", "--params",
                            json.dumps({"fileId": fid, "fields": "mimeType,name"})],
                           capture_output=True, text=True, timeout=8)
        info = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    except Exception:
        info = {}
    mt = info.get("mimeType") or ""
    if not mt:
        return "UNKNOWN\t"
    name = info.get("name") or ""
    return ("SHEET\t" if mt == "application/vnd.google-apps.spreadsheet" else "OTHER\t") + name


TRASH_WINDOW_S = 600


def count_trash(payload):
    """Round C gap 4 (fc_drive_bulk_delete): how many DIFFERENT files this session has sent to the Drive trash through
    the MCP tool in the last TRASH_WINDOW_S seconds, counting this one. State: one small file per session
    (${LHB_DRIVE_TRASH_DIR:-~/.claude/run/drive-trash}/<session_id>), one `epoch<TAB>key` line per call. The hook is
    registered twice (plugin and project), so both copies see each call: the key is the tool_use_id (else the file id)
    and a key counts once. Any error -> 1 (never blocks on its own failure)."""
    import time
    try:
        ti = payload.get("tool_input") or {}
        key = str(payload.get("tool_use_id") or ti.get("fileId") or "?")
        sid = re.sub(r"[^A-Za-z0-9_-]", "_", str(payload.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or "nosession"))[:80]
        d = os.environ.get("LHB_DRIVE_TRASH_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "run", "drive-trash")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, sid)
        now = int(time.time())
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("%d\t%s\n" % (now, key))
        keys = set()
        for ln in open(path, encoding="utf-8").read().splitlines():
            t, _, k = ln.partition("\t")
            if t.isdigit() and now - int(t) <= TRASH_WINDOW_S:
                keys.add(k)
        return max(1, len(keys))
    except Exception:
        return 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--count":
        try:
            print(count_trash(json.load(sys.stdin)))
        except Exception:
            print(1)
        return 0
    if len(sys.argv) > 2 and sys.argv[1] == "--kind":
        print(kind_of(sys.argv[2]))
        return 0
    try:
        d = json.load(sys.stdin)
    except Exception:
        print("PASS")
        return 0
    tool = d.get("tool_name") or ""
    ti = d.get("tool_input") or {}
    if tool.startswith("mcp__") and tool.endswith("__trash_file"):
        print("SINGLE\t" + str(ti.get("fileId") or "?"))
        return 0
    cmd = ti.get("command") or ""
    print(classify_bash(cmd) if cmd else "PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
