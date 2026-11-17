#!/usr/bin/env python3
"""Read-only look at LuLu's saved rules and settings (world-readable files in /Library/Objective-See/LuLu/).
Prints the mailroom's rules and a PASS/NOT YET against Vision 3.1:
  gws    allow only gmail.googleapis.com, www.googleapis.com, oauth2.googleapis.com, accounts.google.com
  claude allow only api.anthropic.com
  no allow-everything rule for either, and no rule at all for Lima.
A rule counts only if it is IN FORCE: not disabled, no expiry, not tied to one running process (a
"temporarily" rule). And the firewall itself must be on: LuLu not disabled, not in passive mode.
No sudo, no network, no mail. LuLu writes these files a moment after a click, so wait ~10 s first.
Run:  python3 -I tools/lulu_rules_check.py      (exit 0 = PASS, 1 = NOT YET)"""
import datetime
import os
import plistlib
import subprocess
import sys

RULES = "/Library/Objective-See/LuLu/rules.plist"
PREFS = "/Library/Objective-See/LuLu/preferences.plist"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gc_settings  # noqa: E402

BIN = gc_settings.mailroom_install_dir().rstrip("/") + "/bin/"   # the mailroom's own gws and claude
WANT = {BIN + "gws": {"gmail.googleapis.com", "www.googleapis.com", "oauth2.googleapis.com", "accounts.google.com"},
        BIN + "claude": {"api.anthropic.com"}}
SIGNED = {BIN + "claude"}               # only these may be found under a signer key; gws stays path-keyed
EMPTY = (None, "$null", False, 0)       # how LuLu saves "not set" (today every real rule has these)


def decode(d):
    """LuLu saves rules as an NSKeyedArchiver plist -> {program path: {"rules": [rule dict, ...]}}."""
    objs = d["$objects"]

    def dec(x, depth=0):
        if isinstance(x, plistlib.UID):
            x = objs[x.data]
        if isinstance(x, dict):
            if "NS.keys" in x:
                return {dec(k, depth + 1): dec(v, depth + 1) for k, v in zip(x["NS.keys"], x["NS.objects"])}
            if "NS.objects" in x:
                return [dec(v, depth + 1) for v in x["NS.objects"]]
            if "NS.time" in x:
                return str(datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=x["NS.time"]))[:19]
            return {k: dec(v, depth + 1) for k, v in x.items() if k != "$class"} if depth < 6 else "..."
        return x
    return dec(d["$top"]["root"])


def not_in_force(r):
    """-> plain reason a saved rule is not a lasting rule, or None."""
    if r.get("isDisabled") not in EMPTY:
        return "disabled"
    if r.get("expiration") not in EMPTY:
        return "expires"
    if r.get("pid") not in EMPTY:
        return "only for one running process (temporary)"
    return None


def signer_key(path):
    """LuLu's key for a code-signed program: "<identifier>:<first Authority>". codesign -dvv is read-only.
    None if unsigned / ad-hoc / unreadable."""
    try:
        out = subprocess.run(["/usr/bin/codesign", "-dvv", path], capture_output=True, text=True, timeout=20).stderr
    except Exception:
        return None
    ident = auth = None
    for ln in out.splitlines():
        if ln.startswith("Identifier=") and ident is None:
            ident = ln[11:]
        elif ln.startswith("Authority=") and auth is None:
            auth = ln[10:]
    return "%s:%s" % (ident, auth) if ident and auth else None


def judge(top, prefs, signers=None):
    """-> (lines to print, list of problems). Problems empty = PASS.
    signers: {mailroom program path: its LuLu signer key}. Rules under that key count for that program."""
    signers = signers or {}
    prog_of = {k: k for k in WANT}
    for p, k in signers.items():
        if p in SIGNED and k:
            prog_of[k] = p
    wild = set()                        # programs with a lasting allow-everything rule under their SIGNER key
    lines, bad = [], []
    if prefs.get("disabled") not in (False, 0, None):
        bad.append("LuLu itself is switched off")
    if prefs.get("passiveMode") not in (False, 0, None):
        bad.append("LuLu is in passive mode (it allows everything without asking)")
    if prefs.get("blockMode") not in (False, 0, None):
        lines.append("note: LuLu is in block mode (it blocks everything without a rule)")
    seen = {p: set() for p in WANT}
    for key, val in sorted(top.items()):
        rules = val.get("rules") if isinstance(val, dict) else None
        low = key.lower()
        if rules is None or not (key in prog_of or "lima" in low or gc_settings.mailroom_account_stem() in low):
            continue
        prog = prog_of.get(key)
        for r in rules:
            addr = r.get("endpointAddr") or "*"
            host = r.get("endpointHost")
            host = host if isinstance(host, str) and host != "$null" else ""
            port = r.get("endpointPort") or "*"
            act = {1: "ALLOW", 0: "BLOCK"}.get(r.get("action"), str(r.get("action")))
            off = not_in_force(r)
            lines.append("%-5s %-34s -> %s %s port %s  (made %s)%s" % (
                act, key.replace(BIN, "mailroom "), addr, ("[" + host + "]") if host else "", port,
                r.get("creation"), ("   NOT IN FORCE: " + off) if off else ""))
            if "lima" in low:
                bad.append("a Lima rule still exists: " + key)
                continue
            if act != "ALLOW":
                continue
            names = {n for n in (addr, host) if n and n != "*"}
            if off:
                if prog and names & WANT[prog]:
                    bad.append("%s: the rule for %s is %s, not a lasting rule" % (prog, sorted(names & WANT[prog])[0], off))
                continue
            if not names:
                if prog and key != prog:
                    wild.add(prog)      # ruled, accepted gap (Vision 3.1): judged below
                else:
                    bad.append("allow-everything rule for " + key)
            elif prog and not names & WANT[prog]:
                bad.append("%s may reach %s (not on the list)" % (prog, sorted(names)[0]))
            elif prog:
                seen[prog] |= names & WANT[prog]
    for p, hosts in WANT.items():
        for h in sorted(hosts - seen[p]):
            bad.append("%s has no lasting allow rule for %s yet" % (p, h))
        if p in wild and not hosts - seen[p]:
            lines.append("ACCEPTED: covered by signer rule - %s (a broader allow-any rule sits under the same signer key)"
                         % p.replace(BIN, "mailroom "))
    return lines, bad


def main():
    top = decode(plistlib.load(open(RULES, "rb")))
    prefs = plistlib.load(open(PREFS, "rb"))
    lines, bad = judge(top, prefs, {p: signer_key(p) for p in SIGNED})
    for l in lines:
        print(l)
    print()
    print("RESULT: PASS" if not bad else "RESULT: NOT YET - " + "; ".join(bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
