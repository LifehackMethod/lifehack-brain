#!/usr/bin/env python3
"""hook_register.py -- ONE template for every PreToolUse hook registration. Check it, or rewrite to it.

WHY: every PreToolUse hook is launched through system/hooks/hook_runner.sh (last-good restore, fail closed).
     A bare `bash .../hook_runner.sh <name>` makes that one file a single point of failure for ALL gates:
     missing -> every registered command exits 127 (non-blocking = every gate silently OPEN); a syntax
     error in it -> every command exits 2 (every tool blocked = the 2026-11-12 incident again).
     So each registered command is generated from the template below:
       runner present and parses  -> exec the runner (normal path)
       runner missing/unreadable/broken, hook present -> LOUD alert, then run the REAL hook directly
       hook missing too            -> LOUD alert, exit 2 (a missing gate fails CLOSED)

Usage:  python3 system/tools/hook_register.py --check [--root DIR]   exit 0 clean, 1 drift
        python3 system/tools/hook_register.py --write [--root DIR]   rewrite hooks/hooks.json + .claude/settings.json
Only PreToolUse commands that point at system/hooks/<name>.sh are managed. Anything else is left alone
(e.g. hooks/guard_harness_write.sh, which lives outside system/hooks). Rule: system/sops/hook-sop.md section 6.
"""
import argparse, json, os, re, sys

FILES = ("hooks/hooks.json", ".claude/settings.json")
MARK = ": hrt "   # every generated command starts with this no-op, which also carries the hook name + args
ROOTVAR = r'(\$\{CLAUDE_(?:PLUGIN_ROOT|PROJECT_DIR)\})'


def render(root_var, name, args=""):
    """The one template. root_var is the literal text ${CLAUDE_PLUGIN_ROOT} or ${CLAUDE_PROJECT_DIR}."""
    tail = (" " + args) if args else ""
    n = name + tail
    return (
        MARK + n + '; h="' + root_var + '/system/hooks"; '
        'a() { s="${LIFEHACK_STATE_DIR:-$HOME/.local/state/lifehack}"; mkdir -p "$s" || echo "could not create $s" >&2; '
        'printf \'{"alert":"hook-runner-unavailable","hook":"' + name + '","what":"%s"}\\n\' "$1" > "$s/hooks-alert.json" || echo "could not write $s/hooks-alert.json" >&2; '
        'echo "HOOK-RUNNER ALERT: $1" >&2; }; '
        'if [ -r "$h/hook_runner.sh" ] && bash -n "$h/hook_runner.sh" 2>/dev/null; then exec bash "$h/hook_runner.sh" ' + n + '; '
        'elif [ -f "$h/' + name + '" ]; then a "hook_runner.sh is missing or broken; running ' + name + ' directly, no last-good protection"; exec bash "$h/' + name + '"' + tail + '; '
        'else a "' + name + ' is missing and hook_runner.sh is unavailable -- failing CLOSED"; exit 2; fi'
    )


_NEW = re.compile('^' + re.escape(MARK) + r'([A-Za-z0-9_.-]+\.sh)((?: [^;]*)?); h="' + ROOTVAR + r'/system/hooks"; ')
_OLD_RUN = re.compile('^bash "' + ROOTVAR + r'/system/hooks/hook_runner\.sh" ([A-Za-z0-9_.-]+\.sh)(?: (.*))?$')
_OLD_BARE = re.compile('^bash "' + ROOTVAR + r'/system/hooks/([A-Za-z0-9_.-]+\.sh)"(?: (.*))?$')


def parse(cmd):
    """-> (root_var, name, args) for a managed command, else None."""
    m = _NEW.match(cmd)
    if m:
        return m.group(3), m.group(1), m.group(2).strip()
    for rx in (_OLD_RUN, _OLD_BARE):
        m = rx.match(cmd)
        if m and m.group(2) != "hook_runner.sh":
            return m.group(1), m.group(2), (m.group(3) or "").strip()
    return None


def pretool_commands(doc):
    for m in (doc.get("hooks") or {}).get("PreToolUse", []):
        for h in m.get("hooks", []):
            if h.get("type") == "command":
                yield h["command"]


def process(root, write):
    drift, managed = [], 0
    for rel in FILES:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        raw = open(p, encoding="utf-8").read()
        doc = json.loads(raw)
        new_raw = raw
        for cmd in dict.fromkeys(pretool_commands(doc)):
            parsed = parse(cmd)
            if not parsed:
                if "/system/hooks/" in cmd:
                    drift.append("%s: PreToolUse command not in a form this tool understands: %s" % (rel, cmd[:100]))
                continue
            managed += 1
            want = render(*parsed)
            if cmd != want:
                drift.append("%s: %s is not the template form" % (rel, parsed[1]))
                new_raw = new_raw.replace(json.dumps(cmd), json.dumps(want))
        if write and new_raw != raw:
            json.loads(new_raw)
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(new_raw)
            os.replace(tmp, p)
    return drift, managed


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(here)))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    a = ap.parse_args()
    drift, managed = process(a.root, a.write)
    if a.write:
        print("hook_register: rewrote %d drifting registration(s); %d managed in total" % (len(drift), managed))
        return 0
    for d in drift:
        print("DRIFT " + d, file=sys.stderr)
    print("hook_register: %d PreToolUse registrations managed, %d drifting" % (managed, len(drift)))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
