#!/usr/bin/env python3
"""enforce_egress_allowlist — the logic behind the outbound-host hook.

Reads the PreToolUse JSON on stdin. Exits 2 (blocked, reason on stderr) or 0 (allowed).
The reasoning and the list itself live in system/egress-allowlist.md; the LLM-context block lives in
enforce_egress_allowlist.sh, which is the registered half.
"""
import sys, json, os, re

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
if not MECH.search(cmd):
    sys.exit(0)

# Pull out the hostnames: http(s):// URLs, plus the bare host argument to nc/telnet.
hosts = set()
for m in re.finditer(r'https?://([^/\s"\'`)\\<>]+)', cmd):
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
        "sanitizes on the way in and does its own allowlisting, and it does not go through this "
        "check. If this host genuinely belongs here, add its base domain to "
        "system/egress-allowlist.md between the ALLOWLIST markers.\n")
    _log_block(bad)
    sys.exit(2)
sys.exit(0)
