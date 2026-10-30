#!/usr/bin/env python3
"""enforce_egress_allowlist — the logic behind the outbound-host hook.

Reads the PreToolUse JSON on stdin. Exits 2 (blocked, reason on stderr) or 0 (allowed).
The reasoning and the list itself live in system/egress-allowlist.md; the LLM-context block lives in
enforce_egress_allowlist.sh, which is the registered half.
"""
import sys, json, os, re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")))
from utf8_stdio import force_utf8_stdio
force_utf8_stdio()

# ── RESERVED NAMES: the ones that CANNOT reach a real destination ────────────────────────────────
# RFC 2606 / RFC 6761 set aside .example, .test and .invalid as names guaranteed never to resolve on
# the public internet. An outbound attempt at one therefore cannot be a real attempt to send data
# anywhere — which lets this hook tell a self-test from an actual event without knowing anything
# about the self-test.
#
# ⛔⛔ `.localhost` WAS ON THIS LIST AND WAS REMOVED, because the premise was factually wrong for it.
# RFC 6761 splits these two ways: §6.4 .invalid, §6.5 .test and RFC 2606 .example are guaranteed NOT
# to resolve; §6.3 localhost is REQUIRED TO ALWAYS RESOLVE, to loopback. Measured rather than
# recalled: socket.gethostbyname("localhost") and gethostbyname("anything.localhost") both return
# 127.0.0.1, while foo.test, bar.invalid and baz.example all raise. So localhost was the one name on
# that list that is actually REACHABLE — and anything already listening on loopback (an SSH remote
# forward, a planted proxy, a dev tunnel) turns a call at it into a working way out.
# ⚠ It was always BLOCKED and still is; only its LOG line was being skipped, and that is what got
# fixed. ★ The lesson worth keeping: the original justification was a claim about an RFC, asserted
# from memory and never run. One socket call falsified it.
_RESERVED_TEST_SUFFIXES = (".example", ".test", ".invalid")


def _is_synthetic_host(host):
    """True only for a name that cannot be a real destination."""
    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return False
    return h.endswith(_RESERVED_TEST_SUFFIXES) or h in ("example", "test", "invalid")


def _log_block(bad_hosts):
    """Record a blocked outbound attempt to the same event log the rest of the wall writes to, so a
    real attempt is visible afterwards rather than only in the moment. Never raises: a logging
    problem must never turn into an allowed call.

    ⛔ IT DOES NOT LOG A PROVABLY-FAKE DESTINATION, and that carve-out has a body count. In the
    system this came from, a health check fired a synthetic outbound call at a reserved-TLD host
    every five minutes. The wall blocked it correctly every single time — and wrote an identical
    unreviewed security event each time: 234 of them in 24 hours, none reviewed. A real attempt
    would have arrived as one line among 234 identical fakes. That is alarm fatigue manufactured by
    the system's own honesty check. The block is untouched; only the log line is skipped, and only
    when EVERY host in the command is synthetic — one fake host must never launder a real one.
    Keyed off the reserved-suffix list, never a hardcoded hostname, so any future self-test using a
    reserved name is covered without anyone remembering to add it."""
    if bad_hosts and all(_is_synthetic_host(h) for h in bad_hosts):
        return
    try:
        import time as _t
        _here = os.path.dirname(os.path.abspath(__file__))
        _repo = os.path.dirname(os.path.dirname(_here))
        # One definition of where the event log lives, imported rather than restated — a restated
        # path drifts, and then half the wall is writing somewhere nobody reads.
        sys.path.insert(0, os.path.join(_repo, "shared", "gate"))
        from sentinel_response import LOG
        lt = _t.localtime(); off = _t.strftime("%z", lt); off = (off[:3] + ":" + off[3:]) if off else "+00:00"
        rec = {"ts": _t.strftime("%Y-%m-%dT%H:%M:%S", lt) + off, "source": "hook/egress",
               "item": ("outbound to a host that is not on the list: " + ", ".join(bad_hosts))[:120],
               "verdict": "blocked", "detail": "raw outbound call, host not allowed",
               "disposition": "unreviewed"}
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


try:
    cmd = json.load(sys.stdin).get('tool_input', {}).get('command', '') or ''
except Exception:
    sys.exit(0)                      # unreadable input → allow; never brick the shell on a parse
if not cmd:
    sys.exit(0)

# Is this even a raw outbound call? Mirrors guard_egress.sh. If not, the hook does not apply — and
# this is why package managers, git and gws are untouched: none of them match.
MECH = re.compile(
    r'(^|[^A-Za-z0-9_/])(curl|wget|nc|ncat|netcat|telnet)([^A-Za-z0-9_]|$)'
    r'|urllib\.request|urllib\.urlopen|\brequests\.(get|post|put|patch|delete|request)'
    r'|\bhttpx\.|http\.client|socket\.(socket|create_connection)')
# email_reader_block (Round C lock-prep A, system/hooks/roundB.conf, OFF = unchanged): python that speaks a mail protocol is a homemade email
# reader, whatever host it names (imap.gmail.com passes the host list because google.com is on it). HARD block, names the shared reader.
# WHO-COULD-THIS-BREAK: a one-off script that reads or sends mail by itself. WAY-THROUGH: python3 <repo>/shared/tools/email_fetch.py (reading).
MAILCODE = re.compile(r'\b(import|from)\s+(imaplib|poplib|smtplib)\b|\b(imaplib|poplib|smtplib)\.\w+|\bIMAP4(_SSL)?\s*\(|\bPOP3(_SSL)?\s*\(|\bfrom\s+googleapiclient|\bimport\s+googleapiclient|\bSMTP(_SSL)?\s*\(')
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
    from roundb import roundb_on as _rb_on
    _mail_block = _rb_on("email_reader_block")
except Exception:
    _mail_block = False
if _mail_block and re.search(r'\bpython[0-9.]*\b', cmd) and MAILCODE.search(cmd):
    sys.stderr.write(
        "BLOCKED (email_reader_block): python that speaks a mail protocol (imaplib / poplib / smtplib / Gmail API) is your own email reader. "
        "That is explicitly prohibited. WHY: raw mail skips the ingest sanitiser and the injection scan; an email is the commonest place an "
        "instruction is planted. USE THE SHARED READER: python3 <repo>/shared/tools/email_fetch.py --consumer <your-name> --query '<gmail query>' "
        "--cap <max threads> --since none --out <file.json> (sanitised, capped, scanned). WHO-COULD-THIS-BREAK: a one-off script that reads mail "
        "directly. WAY-THROUGH: call email_fetch.py instead.\n")
    sys.exit(2)
if not MECH.search(cmd):
    sys.exit(0)

# Pull out the hostnames: http(s):// URLs, plus the bare host argument to nc/telnet.
#
# ⛔ THE EXCLUDED SET ENDS THE HOST AT SHELL PUNCTUATION, and every character in it is there because
# leaving it out produced a real false block. A URL with no path runs to the end of the word, so
# whatever the shell put next got glued onto the hostname — and since none of it is legal in a host,
# the result matched nothing on the list and the call was refused. Measured, all five:
#     ${API_URL:-https://api.anthropic.com}      → api.anthropic.com}      BLOCKED
#     curl https://api.anthropic.com;echo done   → api.anthropic.com;echo  BLOCKED
#     curl https://api.anthropic.com&            → api.anthropic.com&      BLOCKED
#     curl https://api.anthropic.com|head        → api.anthropic.com|head  BLOCKED
#     curl https://api.anthropic.com,https://…   → api.anthropic.com,https BLOCKED
# Each one refused a command that was going somewhere explicitly allowed. That is the failure this
# file's own FAIL_POSTURE note warns about — a false positive is how a wall gets unregistered.
# ⚠ Ending the host EARLIER can only make it MORE likely to match the list, so the obvious worry is
# that this lets something through. It does not: the negative control is in the suite — a stranger
# wrapped in exactly the same punctuation is still blocked, because the shortened name is the REAL
# host and the real host is the thing being checked.
hosts = set()
for m in re.finditer(r'https?://([^/\s"\'`)};&|,\\<>]+)', cmd):
    hp = m.group(1)
    if '@' in hp:
        hp = hp.split('@', 1)[1]     # strip any user:pass@ prefix
    host = hp.split(':', 1)[0].strip().lower().rstrip('.')
    if host:
        hosts.add(host)
for m in re.finditer(r'\b(?:nc|ncat|netcat|telnet)\b\s+((?:-\S+\s+)*)([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b', cmd):
    host = m.group(2).strip().lower().rstrip('.')
    if host:
        hosts.add(host)

# ── BARE HOSTNAMES (v2 3.5b): `curl -d hi ntfy.sh/topic` has no scheme, so the URL pattern above never
# saw it and the call passed with only the "no hostname" warning. This pass reads tokens in a network
# tool's ARGUMENT position only (first word of a command segment is curl/wget/http/nc/...), and only
# accepts a token that is wholly `host.tld[:port][/path]`. Kept conservative on purpose:
#   - flags, and the value of a value-taking flag (-o out.json, --data @f.txt), are skipped
#   - `@file`, `./a.b/c`, `/abs`, `~/x`, `$VAR`, key=value, anything with :// are skipped
#   - with no path and no port, a file-extension "TLD" (notes.md, out.json) is skipped
# It only ever ADDS hosts to check, and only from network-tool args; every case above is unchanged.
_NET_TOOLS = {'curl', 'wget', 'http', 'https', 'httpie', 'xh', 'nc', 'ncat', 'netcat', 'telnet'}
_PREFIX = {'sudo', 'env', 'time', 'nohup', 'command', 'exec'}
_VAL_FLAGS = {  # flags whose NEXT token is a value, not a destination
    '-o', '-d', '-H', '-X', '-u', '-A', '-e', '-T', '-F', '-b', '-c', '-K', '-m', '-x', '-w', '-D', '-E',
    '-P', '-U', '-C', '-r', '-z',   # NOT -s -q -i -I -O -p: no value in curl/wget (-q is wget quiet)
    '--data', '--data-raw', '--data-binary', '--data-urlencode', '--data-ascii', '--json', '--output',
    '--header', '--request', '--user', '--user-agent', '--referer', '--form', '--form-string',
    '--upload-file', '--cookie', '--cookie-jar', '--max-time', '--connect-timeout', '--proxy', '--cacert',
    '--cert', '--key', '--config', '--write-out', '--dump-header', '--retry', '--output-document',
    '--post-data', '--post-file', '--directory-prefix', '--input-file', '--timeout',
    '--auth', '--session', '--proxy-user', '--limit-rate', '--range', '--resolve', '--url-query'}
_FILE_EXT = set("""md txt json yaml yml xml csv tsv log html htm py js mjs ts rb pl php c h cpp go rs java
jpg jpeg png gif svg pdf zip gz tgz tar bz2 xz bin dat out tmp conf cfg ini toml lock sql db pem key crt
cer css map env sample bak orig diff patch jsonl ndjson cookies""".split())
_BARE = re.compile(r'^((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}|\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?(/\S*)?$', re.I)


def _segments(c):
    import shlex
    try:
        lx = shlex.shlex(c, posix=True, punctuation_chars=';&|()')
        lx.whitespace_split = True
        toks = list(lx)
    except Exception:
        return []
    segs, cur = [], []
    for t in toks:
        if t and set(t) <= set(';&|()'):
            segs.append(cur); cur = []
        else:
            cur.append(t)
    segs.append(cur)
    return segs


def _bare_hosts(c):
    out = set()
    for seg in _segments(c):
        i = 0
        while i < len(seg) and (seg[i] in _PREFIX or re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', seg[i])):
            i += 1
        if i >= len(seg) or os.path.basename(seg[i]) not in _NET_TOOLS:
            continue
        skip = False
        for t in seg[i + 1:]:
            if skip:
                skip = False; continue
            if t.startswith('-'):
                if t in _VAL_FLAGS:
                    skip = True
                continue
            if not t or t[0] in '@./~$' or '://' in t or '=' in t or '\\' in t:
                continue
            m = _BARE.match(t)
            if not m:
                continue
            host, port, path = m.group(1).lower(), m.group(2), m.group(3)
            if re.match(r'^\d', host) and not (port or path):
                continue                      # a bare dotted number (1.5) is a number, not a host
            if not (port or path) and host.rsplit('.', 1)[1] in _FILE_EXT:
                continue                      # notes.md, out.json
            out.add(host)
    return out


hosts |= _bare_hosts(cmd)

if not hosts:                        # a mechanism but no host we can read → allow, and say so
    sys.stderr.write("[egress] an outbound call with no hostname this hook could read — allowed. "
                     "Your OS firewall is the layer that actually holds this line.\n")
    sys.exit(0)

# The list. Default is this repo's own copy, resolved from this file — never a home directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_LIST = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "system", "egress-allowlist.md")
allow, inblock = [], False
try:
    with open(os.environ.get('ALLOWLIST_FILE') or _DEFAULT_LIST) as f:
        for line in f:
            s = line.strip()
            if s == '<!-- ALLOWLIST-START -->': inblock = True; continue
            if s == '<!-- ALLOWLIST-END -->':   inblock = False; continue
            if inblock and s and not s.startswith('#'):
                allow.append(s.lower().lstrip('.'))
except Exception:
    allow = []
if not allow:                        # unreadable or empty list → allow, and say why
    sys.stderr.write("[egress] the allowlist is empty or unreadable — allowed. "
                     "Fix system/egress-allowlist.md; until then this layer is doing nothing.\n")
    sys.exit(0)


def ok(h):
    return any(h == d or h.endswith('.' + d) for d in allow)


bad = [h for h in sorted(hosts) if not ok(h)]
if bad:
    sys.stderr.write(
        "BLOCKED: a raw outbound call to a host that is not on the list: " + ", ".join(bad) + ". "
        "WHY: reading a poisoned page is survivable; reading one and then sending something out is "
        "not, and a hand-rolled curl is how that would happen. This is the second half of the wall. "
        "REDIRECT: to READ a web page, use python3 <repo>/system/tools/safe_fetch.py '<url>' — it "
        "sanitizes on the way in and has a domain seal of its own (system/safe-fetch-allowlist.md, "
        "which ships OFF), and it does not go through this check. "
        "If this host genuinely belongs here, add its base domain to "
        "system/egress-allowlist.md between the ALLOWLIST markers.\n")
    _log_block(bad)
    sys.exit(2)
sys.exit(0)
