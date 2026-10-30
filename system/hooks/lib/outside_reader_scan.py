#!/usr/bin/env python3
"""outside_reader_scan.py -- switch email_reader_block (system/hooks/roundB.conf). Called by ingest_gate_enforce.sh.

RULE (Enver 2026-10-30, a vetted rule): a session may NOT write its own reader of outside content. Two kinds:
  MAIL  code that reads mail itself (imaplib, poplib, googleapiclient talking to Gmail, raw Gmail REST, openssl s_client to an
        IMAP/POP port). Raw mail skips the ingest sanitiser, so it is a prompt-injection hole. HARD deny.
  WEB   code that fetches web pages / APIs itself (requests, urllib.request, urllib3, httpx, aiohttp, http.client, curl/wget in a script,
        fetch() in JS). Same hole, same fix.
The sanctioned tools: mail -> shared/tools/email_fetch.py; web -> system/tools/safe_fetch.py, search -> system/tools/safe_search_api.sh.
Files in system/tools/shared-fetch-allowlist.txt ARE the shared fetches and are never blocked. Test files (test_*.py, *_test.py, a tests/
folder) are not blocked. Loopback-only web code (localhost, 127.0.0.1) is not outside content. A word in a comment, docstring or
string is not a use: Python is read with the ast (imports + calls), other languages with comment lines dropped and code-shaped patterns.

WHO-COULD-THIS-BREAK: a session or student who writes a script that calls a JSON API, scrapes a page, or reads mail directly (an invoice
  checker, a weather widget). WAY-THROUGH: mail -> call python3 <code>/shared/tools/email_fetch.py (below); a web page or API ->
  python3 <code>/system/tools/safe_fetch.py '<url>' (sanitises, scans, egress allowlist) and parse its output; a search -> bash
  <code>/system/tools/safe_search_api.sh '<query>'. A genuinely new shared fetcher is added to shared-fetch-allowlist.txt by the maintainer.
FAIL_POSTURE: degrade-safe: an internal error prints a note on stderr and allows (the matcher is broad).
CLI: reads a PreToolUse payload on stdin; exit 2 + JSON block reason on stderr, else 0.
"""
import ast
import json
import os
import re
import sys

CODE_EXT = {".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".php", ".go"}
MAIL_MODS = {"imaplib", "poplib"}
WEB_MODS = {"requests", "urllib3", "httpx", "aiohttp"}
WEB_DOTTED = {"urllib.request", "http.client"}
LOOP = re.compile(r"https?://(localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|\[::1\])([:/\s\"']|$)", re.I)
URL = re.compile(r"https?://[^\s\"'`)>]+", re.I)

MAIL_LINE = re.compile(
    r"\b(imaplib|poplib|IMAP4(_SSL)?|POP3(_SSL)?)\b|gmail\.googleapis\.com|googleapis\.com/(upload/)?gmail|/gmail/v1/users"
    r"|openssl\s+s_client[^\n]*:(993|995|143|110)\b|\bcurl\b[^\n]*\b(imaps?|pop3s?)://|node-imap|imapflow|\bgws\s+gmail\s+users\s+(messages|threads)\s+(get|list)\b", re.I)
WEB_LINE = re.compile(
    r"\b(curl|wget)\b[^\n]*https?://|\bfetch\(\s*[`'\"]https?://|require\(\s*['\"](axios|node-fetch|got|request|superagent)['\"]\)"
    r"|from\s+['\"](axios|node-fetch|got|superagent)['\"]|\bimport\s+(requests|urllib3|httpx|aiohttp)\b|\bfrom\s+(requests|urllib3|httpx|aiohttp)\s+import\b"
    r"|\bimport\s+urllib\.request\b|\bfrom\s+urllib\.request\b|\bfrom\s+urllib\s+import\s+[^\n]*\brequest\b|\bimport\s+http\.client\b|\bfrom\s+http\.client\b"
    r"|\burllib\.request\.urlopen\b", re.I)


def _py_findings(text):
    """-> set of 'mail'/'web' from the ast; None when the text does not parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    out = set()
    gmail_word = "gmail" in text.lower()

    def mod(name):
        root = name.split(".")[0]
        if root in MAIL_MODS:
            out.add("mail")
        elif root == "googleapiclient" and gmail_word:
            out.add("mail")
        elif root in WEB_MODS or name in WEB_DOTTED or any(name.startswith(d + ".") for d in WEB_DOTTED):
            out.add("web")
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                mod(a.name)
        elif isinstance(n, ast.ImportFrom):
            m = n.module or ""
            mod(m)
            if m == "urllib" and any(a.name == "request" for a in n.names):
                out.add("web")
            if m == "http" and any(a.name == "client" for a in n.names):
                out.add("web")
        elif isinstance(n, ast.Call):
            f = n.func
            fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if fname in ("__import__", "import_module") and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                mod(n.args[0].value)
    return out


def _is_comment(line):
    s = line.strip()
    return s.startswith("#") or s.startswith("//") or s.startswith("*") or s.startswith("/*") or s.startswith("--")


def findings(text, ext):
    """-> set of 'mail' / 'web' found in code text."""
    out = set()
    if ext == ".py":
        r = _py_findings(text)
        if r is not None:
            out = r
        else:
            text = "\n".join(l for l in text.split("\n") if not _is_comment(l))
            if re.search(r"^\s*(import|from)\s+(imaplib|poplib)\b|\b(imaplib|poplib)\.(IMAP4|POP3)", text, re.M):
                out.add("mail")
            if re.search(r"^\s*(import|from)\s+googleapiclient\b", text, re.M) and "gmail" in text.lower():
                out.add("mail")
            if WEB_LINE.search(text):
                out.add("web")
    else:
        code = "\n".join(l for l in text.split("\n") if not _is_comment(l))
        if MAIL_LINE.search(code):
            out.add("mail")
        if WEB_LINE.search(code):
            out.add("web")
    if "web" in out:        # loopback-only web code is not outside content
        urls = URL.findall(text)
        if urls and all(LOOP.match(u) for u in urls):
            out.discard("web")
    return out


def code_root():
    r = os.environ.get("OUTSIDE_READER_CODE_ROOT")
    if r:
        return os.path.realpath(r)
    return os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def allowlisted(path, root):
    try:
        with open(os.path.join(root, "system", "tools", "shared-fetch-allowlist.txt"), encoding="utf-8", errors="replace") as f:
            rels = [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
    except OSError:
        return False             # a missing allowlist means no exemption (closed), like the clause (h) rule
    rp = os.path.realpath(path)
    return any(rp == os.path.realpath(os.path.join(root, r)) for r in rels)


def is_test_file(path):
    b = os.path.basename(path)
    return b.startswith("test_") or re.search(r"_test\.\w+$", b) is not None or "/tests/" in path.replace("\\", "/")


def message(kind, path, root):
    name = os.path.basename(path) or path
    if kind == "mail":
        return ("BLOCKED (email_reader_block): %s would read mail with its own code (imaplib / poplib / the Gmail API). That is explicitly "
                "prohibited. WHY: raw mail skips the ingest sanitiser and the injection scan, and anyone in the world can put an instruction "
                "in front of the model through an email; a homemade reader is a security hole, not a convenience. "
                "USE THE SHARED READER: python3 %s/shared/tools/email_fetch.py --consumer <your-name> --query '<gmail query, e.g. is:unread>' "
                "--cap <max threads> --since none [--label <label>] --out <file.json>  (every choice explicit; sanitised, capped, injection-scanned; "
                "exit 75 = the label is paused, exit 3 = reader down). Read the JSON it writes. Mail already ingested: "
                "python3 %s/shared/tools/email_service_read.py. WHO-COULD-THIS-BREAK: a script that reads mail by itself. "
                "WAY-THROUGH: call email_fetch.py from your script (subprocess) instead of imaplib/poplib/Gmail API. "
                "RULE: system/hooks/lib/outside_reader_scan.py (switch email_reader_block); allowed files: system/tools/shared-fetch-allowlist.txt."
                % (name, root, root))
    return ("BLOCKED (email_reader_block): %s would fetch outside content with its own code (requests / urllib / httpx / curl in a script). "
            "WHY: a page or API response is third-party text that can carry an instruction addressed to the model; the sanitiser, injection scan "
            "and egress allowlist exist only inside the shared fetch. "
            "USE THE SHARED FETCH: python3 %s/system/tools/safe_fetch.py '<url>' (page or API, sanitised and scanned) or bash "
            "%s/system/tools/safe_search_api.sh '<query>' (search). From a script, run safe_fetch.py with subprocess and parse its output. "
            "WHO-COULD-THIS-BREAK: a script that calls a JSON API or scrapes a page (a weather widget, an invoice checker). "
            "WAY-THROUGH: route the call through safe_fetch.py; a new shared fetcher is added to system/tools/shared-fetch-allowlist.txt by the maintainer. "
            "Loopback (localhost) code and test files are not blocked. RULE: system/hooks/lib/outside_reader_scan.py (switch email_reader_block)."
            % (name, root, root))


def _verdict(path, text, root, loose=False):
    ext = os.path.splitext(path)[1].lower()
    if ext not in CODE_EXT or is_test_file(path) or allowlisted(path, root):
        return None
    f = findings(text, ".sh" if loose else ext)   # loose: a one-line echo/printf payload is not parseable python
    if "mail" in f:
        return message("mail", path, root)
    if "web" in f:
        return message("web", path, root)
    return None


HEREDOC = re.compile(r"(?:>>?|\btee(?:\s+-a)?)\s*(\"[^\"]+\"|'[^']+'|[^\s<>|;&]+)[^\n]*?<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)(?:\n\s*\2\s*(?:\n|$)|$)", re.S)
HEREDOC_TEE = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)(?:\n\s*\1\s*(?:\n|$)|$)", re.S)
REDIR1 = re.compile(r"(?:\becho\b|\bprintf\b)[^\n]*?>>?\s*(\"[^\"]+\"|'[^']+'|[^\s<>|;&]+)")


def bash_verdict(cmd, cwd, root):
    """Heredoc / redirect writes of code to a file. -> message or None."""
    def res(p):
        p = p.strip("\"'")
        return p if os.path.isabs(p) else os.path.join(cwd or os.getcwd(), p)
    for m in HEREDOC.finditer(cmd):
        v = _verdict(res(m.group(1)), m.group(3), root)
        if v:
            return v
    for m in re.finditer(r"\btee\s+(?:-a\s+)?(\"[^\"]+\"|'[^']+'|[^\s<>|;&]+)[^\n]*?<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*)", cmd, re.S):
        v = _verdict(res(m.group(1)), m.group(3), root)
        if v:
            return v
    for m in re.finditer(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*)", cmd, re.S):      # cat <<EOF | tee file / cat <<EOF > file
        head = cmd[:m.start()] + cmd[m.start():].split("\n", 1)[0]
        tm = re.search(r"(?:>>?|\btee(?:\s+-a)?)\s*(\"[^\"]+\"|'[^']+'|[^\s<>|;&]+)\s*$", head.strip()) or re.search(r"\|\s*tee\s+(?:-a\s+)?(\S+)", head)
        if tm:
            v = _verdict(res(tm.group(1)), m.group(2), root)
            if v:
                return v
    for m in REDIR1.finditer(cmd):
        v = _verdict(res(m.group(1)), cmd, root, loose=True)
        if v:
            return v
    return None


def check_payload(d):
    tool = d.get("tool_name") or ""
    ti = d.get("tool_input") or {}
    cwd = d.get("cwd") or os.getcwd()
    root = code_root()
    if tool in ("Write", "Edit", "MultiEdit"):
        fp = ti.get("file_path") or ""
        if not fp:
            return None
        p = fp if os.path.isabs(fp) else os.path.join(cwd, fp)
        if tool == "Write":
            text = ti.get("content", "")
        elif tool == "Edit":
            text = ti.get("new_string", "")
        else:
            text = "\n".join(e.get("new_string", "") for e in (ti.get("edits") or []))
        return _verdict(p, text, root)
    if tool == "Bash":
        return bash_verdict(ti.get("command", ""), cwd, root)
    return None


def main():
    try:
        d = json.loads(sys.stdin.read())
        msg = check_payload(d)
    except Exception as e:
        sys.stderr.write("outside_reader_scan: internal error (%s); allowing\n" % e)
        return 0
    if msg:
        sys.stderr.write(json.dumps({"decision": "block", "reason": msg}) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
