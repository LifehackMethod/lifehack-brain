#!/usr/bin/env python3
"""Engine for guard_cloud_destructive.sh (D-F11, 2026-11-02). Payload on stdin. ASKS only (permissionDecision "ask",
exit 0, the output shape of fine_china_ask.py); never blocks. Switch: fc_cloud_destructive_ask in roundB.conf
(env ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK wins). OFF = prints nothing.

WHY: a sandbox session trashed 899 real Drive files from a `python3 -I - <<'E'` loop, and no hook knew gcloud, gsutil,
rclone, aws, or a curl DELETE to googleapis.com at all. A cloud delete has no local copy and often no undo.

WHAT ASKS (Bash only; read in the command itself, in sh -c / eval bodies, in python/node/ruby/perl -c|-e bodies, in a
heredoc an interpreter executes (python3 - <<'E'), in an argv list built in that code (subprocess.run([...])), and in
a shell string handed to subprocess/os.system):
  gcloud   any `delete` or `rm` verb (storage rm, storage buckets delete, projects/instances/sql/secrets delete ...)
  gsutil   rm, rb, rsync -d
  rclone   delete, deletefile, purge, rmdir, rmdirs, cleanup, dedupe, move, moveto, sync (sync deletes on the target)
  aws      s3 rm|rb|mv, s3 sync --delete, any delete-*/terminate-* verb (s3api delete-object, ...)
  curl / wget   to *.googleapis.com: method DELETE; or PATCH/PUT/POST whose body sets trashed true, or whose path is
           /trash, emptyTrash, batchDelete or /permissions. A DELETE to a URL it cannot read ($VAR) asks too.
  gws      drive | gmail | calendar | sheets: permissions create/update/patch/delete, emptyTrash, delete, batchDelete,
           calendar acl insert/update/patch/delete and calendars clear; an operation word it cannot read ($VAR).
           (`files update` with trashed true belongs to guard_drive_destructive.sh: one owner per verb.)
  python   googleapiclient .files()/.drives() delete|emptyTrash, .files().update(... trashed ...), .permissions()
           create|update|patch|delete, .messages()/.threads() trash|delete|batchDelete, .events() delete;
           requests/httpx .delete( to googleapis.com.
The reason says "in a loop / an unknown number" when the call sits in a for/while/xargs/forEach/map, and "a whole
tree or wildcard" for -r, *, purge.
PASSES: listing and reading (gws ... list/get, gcloud storage ls, gsutil ls, rclone ls/copy, curl GET), a heredoc
that only WRITES text (cat > f <<EOF ... EOF), prose that mentions the words (echo, git commit -m, grep).
LIMITS (static text only; a speed bump, not a boundary -- the real boundary is credential scope):
  a script file written earlier and run later by name (python3 x.py) is not opened; code imported by a script;
  obfuscated or built text ("dr"+"ive", getattr, base64/exec/eval, chr joins, verbs from a config or env var);
  code fetched at run time (curl ... | python3); a Makefile/npm script one level away; cron/launchd jobs that fire
  later; an argv built entirely at run time with no literal binary name.
Fail posture: any internal error prints nothing (allow) plus one stderr line, because it sits in front of every Bash call.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gws_guard  # noqa: E402

OUT = []
CLIS = {"gcloud", "gsutil", "rclone", "aws", "curl", "wget"}
GWS_SERVICES = {"drive", "gmail", "calendar", "sheets"}
RCLONE_VERBS = {"delete", "deletefile", "purge", "rmdir", "rmdirs", "cleanup", "dedupe", "move", "moveto", "sync"}
LOOP = re.compile(r"\bxargs\b|\bparallel\b|\bfor\b|\bwhile\b|\buntil\b|-exec\b|\.forEach\b|\bmap\s*\(|Promise\.all|"
                  r"ThreadPoolExecutor|\.each\s+do\b")
QUOTED = re.compile(gws_guard._QUOTED)
TRASHED = re.compile(r"trashed\W{0,6}(?:true|1)\b", re.I)
GOOGLE_HOST = re.compile(r"(?:^|[/@.\s'\"])(?:[\w-]+\.)*googleapis\.com\b", re.I)
GOOGLE_DESTRUCTIVE_PATH = re.compile(r"/trash\b|emptyTrash|batchDelete|/permissions\b", re.I)
# heredoc-quiet-fix (2026-11-02): an executed heredoc body is read only when it names something this guard is about;
# a python heredoc that edits a plan file stays inert.
CLOUD_MENTION = re.compile(r"(?:^|[^A-Za-z0-9_.-])(?:gws|gcloud|gsutil|rclone|aws|curl|wget)(?:[^A-Za-z0-9_-]|$)|googleapis|"
                           r"googleapiclient|\.(?:files|drives|permissions|messages|threads|events)\(\)|\b(?:requests|httpx)\b")
LIB_RULES = [
    (re.compile(r"\.(?:files|drives)\(\)\s*\.\s*(?:delete|emptyTrash)\s*\("), "a Drive delete through the Google API client"),
    (re.compile(r"\.files\(\)\s*\.\s*update\s*\([^)]*trashed", re.S), "a Drive trash (files().update trashed) through the Google API client"),
    (re.compile(r"\.permissions\(\)\s*\.\s*(?:create|delete|update|patch)\s*\("), "a Drive sharing change through the Google API client"),
    (re.compile(r"\.(?:messages|threads)\(\)\s*\.\s*(?:trash|delete|batchDelete)\s*\("), "a Gmail delete through the Google API client"),
    (re.compile(r"\.events\(\)\s*\.\s*delete\s*\("), "a Calendar event delete through the Google API client"),
    (re.compile(r"\b(?:requests|httpx|session|client)\.delete\s*\(\s*[fbr]?['\"][^'\"]*googleapis\.com"), "an HTTP DELETE to a Google API"),
]


def on(name):
    try:
        from roundb import roundb_on
        return roundb_on(name)
    except Exception:
        return False


def _strip_q(t):
    return t.strip("'\"")


def _base(t):
    return gws_guard._debinary(t).rsplit("/", 1)[-1].lower()


def _shell_texts(cmd):
    """The shell text this command runs: itself (inert heredoc bodies blanked, EXECUTED ones kept), sh -c / eval
    bodies, and shell strings handed to subprocess/os.system from executed code."""
    vis = gws_guard._strip_quoted_heredocs(cmd, True, CLOUD_MENTION)
    texts = [vis]
    for m in gws_guard._EXECWRAP.finditer(vis):
        inner = m.group("body") or m.group("body2")
        if inner:
            texts.append(inner.strip("'\""))
    for text in (vis, vis.replace('\\"', '"').replace("\\'", "'")):
        for m in gws_guard._SHELL_CALL.finditer(text):
            lit = m.group(1)[1:-1].replace('\\"', '"').replace("\\'", "'")
            if _base(lit.split()[0] if lit.split() else "") in CLIS:
                texts.append(lit)
    return vis, texts


def _split_statements(text):
    """Split shell text into statements on newline ; | || & && -- but never inside quotes or after a backslash, so a
    quoted `grep "a\\|rclone purge"` stays ONE statement (the shared _STMT split is quote-blind on purpose; it is the
    gws parser's fail-closed reader, while this guard asks and must not ask on prose)."""
    out = []
    for line in text.split("\n"):
        cur = []
        q = None
        i = 0
        n = len(line)
        while i < n:
            c = line[i]
            if q:
                if c == "\\" and q == '"' and i + 1 < n:
                    cur.append(line[i:i + 2])
                    i += 2
                    continue
                if c == q:
                    q = None
                cur.append(c)
            elif c == "\\" and i + 1 < n:
                cur.append(line[i:i + 2])
                i += 2
                continue
            elif c in "'\"":
                q = c
                cur.append(c)
            elif c in ";|&":
                out.append("".join(cur))
                cur = []
                while i + 1 < n and line[i + 1] in "|&":
                    i += 1
            else:
                cur.append(c)
            i += 1
        out.append("".join(cur))
    return out


def _cli_segments(texts):
    """(cli, args, statement_text) for every shell statement whose command word is one of CLIS."""
    out = []
    for text in texts:
        for stmt in _split_statements(text):
            s = re.sub(r"^[\s({!]+", "", stmt).rstrip(") };")
            word, args = gws_guard._cmd_word(s.split())
            if word.startswith("$(") or word.startswith("`"):
                word = word.lstrip("$(`")
            if word in CLIS:
                out.append((word, args, s))
            for m in re.finditer(r"(?:\$\(|`)\s*((?:[\w./~-]*/)?(?:%s)\b[^)`]*)" % "|".join(CLIS), s):
                toks = m.group(1).split()
                out.append((_base(toks[0]), toks[1:], m.group(1)))
    return out


def _argv_segments(vis):
    """(cli, args, span) for every argv LIST built in code that names one of CLIS as a quoted literal followed by a
    comma -- the whole call, every quoted literal in it (UNPARSEABLE appended when part of it is not a literal)."""
    out = []
    text = vis.replace('\\"', '"').replace("\\'", "'")
    for m in gws_guard._SOLO_GWS_QUOTE.finditer(text):
        w = _base(m.group(2))
        if w not in CLIS:
            continue
        b = m.start() - 1
        while b >= 0 and text[b] in " \t":
            b -= 1
        if b >= 0 and text[b] in "[(":
            span = text[b:gws_guard._match_close(text, b)]
        else:
            nl = text.find("\n", m.end())
            span = text[m.start():(len(text) if nl == -1 else nl)]
        items = gws_guard._list_items(span)
        if re.search(r"[A-Za-z_$]", QUOTED.sub(" ", span)):
            items.append(gws_guard.UNPARSEABLE)
        if items and _base(items[0]) == w:
            out.append((w, items[1:], span))
    return out


def _nonflags(args):
    return [_strip_q(a) for a in args if not a.startswith("-") and not a.startswith("'-") and not a.startswith('"-')]


def _curl_reason(cli, args, text):
    method = None
    has_data = False
    i = 0
    a = [_strip_q(x) for x in args]
    while i < len(a):
        t = a[i]
        if t in ("-X", "--request", "--method") and i + 1 < len(a):
            method = a[i + 1].upper()
            i += 2
            continue
        m = re.match(r"^(?:-X|--request=|--method=)(\w+)$", t)
        if m:
            method = m.group(1).upper()
        if t in ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode", "--json", "-F", "--form",
                 "--post-data", "--body-data", "--post-file", "--body-file") or re.match(r"^(?:--data|--json|--post-data|--body-data)", t):
            has_data = True
        i += 1
    if method is None:
        method = "POST" if has_data else "GET"
    urls = [x for x in a if re.match(r"^(?:https?://)?[\w.-]+\.\w+(?::\d+)?/", x) or "googleapis.com" in x]
    google = [u for u in urls if GOOGLE_HOST.search(" " + u)]
    if method == "DELETE":
        if google:
            return "an HTTP DELETE to a Google API (%s)" % google[0][:80]
        if not urls and any(gws_guard._NONLITERAL.search(x) for x in a):
            return "an HTTP DELETE to an address this guard cannot read"
        return None
    if google and method in ("PATCH", "PUT", "POST"):
        if TRASHED.search(text):
            return "an HTTP %s that sends a Google file to the trash" % method
        if any(GOOGLE_DESTRUCTIVE_PATH.search(u) for u in google):
            return "an HTTP %s to a destructive Google API path (%s)" % (method, google[0][:80])
    return None


def _cli_reason(cli, args, text):
    nf = _nonflags(args)
    low = [x.lower() for x in nf]
    flags = [_strip_q(x) for x in args if _strip_q(x).startswith("-")]
    if any(x == gws_guard.UNPARSEABLE for x in args) and not nf[:1]:
        return "a %s command this guard cannot read" % cli
    if cli == "gcloud":
        head = low[:5]
        if "delete" in head or "rm" in head:
            return "gcloud %s" % " ".join(nf[:4])
        if head and gws_guard._NONLITERAL.search(" ".join(nf[:4])):
            return "a gcloud command whose operation this guard cannot read"
    elif cli == "gsutil":
        op = low[0] if low else ""
        if op in ("rm", "rb"):
            return "gsutil %s" % op
        if op == "rsync" and "-d" in flags:
            return "gsutil rsync -d (deletes on the target)"
        if op and gws_guard._NONLITERAL.search(op):
            return "a gsutil command whose operation this guard cannot read"
    elif cli == "rclone":
        op = low[0] if low else ""
        if op in RCLONE_VERBS:
            return "rclone %s%s" % (op, " (deletes on the target side)" if op == "sync" else "")
        if op and gws_guard._NONLITERAL.search(op):
            return "an rclone command whose operation this guard cannot read"
    elif cli == "aws":
        if len(low) >= 2:
            svc, op = low[0], low[1]
            if svc == "s3" and op in ("rm", "rb", "mv"):
                return "aws s3 %s" % op
            if svc == "s3" and op == "sync" and "--delete" in flags:
                return "aws s3 sync --delete"
            if op.startswith("delete-") or op.startswith("terminate-"):
                return "aws %s %s" % (svc, op)
    elif cli in ("curl", "wget"):
        return _curl_reason(cli, args, text)
    return None


def _gws_reason(toks):
    low = [_strip_q(t).lower() for t in toks]
    svc = next((s for s in low if s in GWS_SERVICES), None)
    if svc is None:
        return None
    # The operation is the words between the service and the first flag (gws <service> <resource> [<sub>] <method>).
    # Past the first flag sit values -- a JSON body split on its spaces, a $t inside a query -- which are not the
    # operation. Fewer than two leading words (a flag placed before the method) falls back to op_chain, which skips
    # flags and their values, so `gws drive --format json files delete` is still read as files delete.
    i = low.index(svc)
    lead = []
    for t in toks[i + 1:]:
        if t.startswith("-") or t == gws_guard.UNPARSEABLE:
            break
        lead.append(t)
    chain = lead if len(lead) >= 2 else gws_guard.op_chain(toks, svc)[:4]
    if gws_guard.has_nonliteral(chain):
        return "a gws %s command whose operation this guard cannot read" % svc
    c = [x.lower() for x in chain]
    words = " ".join(chain[:4])
    if "permissions" in c and set(c) & {"create", "update", "patch", "delete", "insert"}:
        return "gws %s %s (a sharing change)" % (svc, words)
    if "emptytrash" in c or c[:2] == ["trash", "empty"]:
        return "gws %s emptyTrash (permanent)" % svc
    if set(c) & {"delete", "batchdelete"}:
        return "gws %s %s" % (svc, words)
    if svc == "calendar" and ("clear" in c or ("acl" in c and set(c) & {"insert", "update", "patch", "delete"})):
        return "gws calendar %s" % words
    return None


def scan(cmd):
    """-> list of reasons (empty = pass)."""
    cmd = cmd.replace("\\\n", " ")
    vis, texts = _shell_texts(cmd)
    reasons = []
    for cli, args, text in _cli_segments(texts) + _argv_segments(vis):
        r = _cli_reason(cli, args, text)
        if r:
            reasons.append(r)
    for toks in gws_guard.gws_segments(cmd, True):
        r = _gws_reason(toks)
        if r:
            reasons.append(r)
    for toks, span in gws_guard.gws_calls(cmd, True):
        r = _gws_reason(toks)
        if r:
            reasons.append(r)
    code = "\n".join(gws_guard.exec_bodies(vis, True))
    for rx, what in LIB_RULES:
        if code and rx.search(code):
            reasons.append(what)
    return list(dict.fromkeys(reasons))


def scope(cmd):
    vis = gws_guard._strip_quoted_heredocs(cmd.replace("\\\n", " "), True, CLOUD_MENTION)
    unq = "\n".join(QUOTED.sub(" ", t) for t in [vis] + gws_guard.exec_bodies(vis, True))
    if LOOP.search(unq):
        return "in a loop: an unknown number of items"
    if re.search(r"(?:^|\s)(?:-r|-R|--recursive)\b|\*|\bpurge\b|--all\b", unq):
        return "a whole tree or wildcard: an unknown number of items"
    return "one target"


def main_inner():
    if not on("fc_cloud_destructive_ask"):
        return
    d = json.loads(sys.stdin.read())
    if d.get("tool_name") != "Bash":
        return
    cmd = (d.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return
    reasons = scan(cmd)
    if reasons:
        OUT.append("ASK FIRST (cloud guard): this runs %s (%s). WHY: a cloud delete, purge, sync or sharing change "
                   "acts on the person's real files with no local copy, and often no undo; the moment it runs is never "
                   "the moment anyone is checking the list. WAY THROUGH: the person answers yes to the prompt that "
                   "appears; never retry by another route. RULE: system/hooks/guard_cloud_destructive.sh "
                   "(fc_cloud_destructive_ask)." % ("; ".join(reasons[:4]), scope(cmd)))


def main():
    try:
        main_inner()
    except BaseException as e:
        sys.stderr.write("guard_cloud_destructive: internal error (%s: %s); allowing\n" % (type(e).__name__, e))
        return 0
    if OUT:
        s = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                               "permissionDecisionReason": " | ".join(dict.fromkeys(OUT))[:1800]}})
        print(s)
        try:  # fire journal: record the real decision (ask), after the print; can never change it (lib/journal_note.py)
            import journal_note
            journal_note.note(s)
        except Exception:  # allow-silence: fire-journal observer only, a failed note must never change the hook
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
