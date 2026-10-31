#!/usr/bin/env python3
"""Worker for lib/watch_gate.sh (Round D B.5). See that file's header. argv: <hook script name> [--shadow-only]; the payload is on stdin."""
import datetime, json, os, re, subprocess, sys

HOOKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(os.path.expanduser("~"), ".claude", "run", "watch", "watch-log.jsonl")


def switches():
    out = {}
    try:
        for ln in open(os.path.join(HOOKDIR, "roundB.conf"), encoding="utf-8"):
            m = re.fullmatch(r"([a-z0-9_]+)=(on|off)\s*", ln)
            if m and m.group(1) != "mode":
                out[m.group(1)] = m.group(2)
    except OSError:
        pass
    for k in list(out):
        v = os.environ.get("ROUNDB_" + k.upper())
        if v is not None:
            out[k] = "on" if v.strip() == "on" else "off"
    return out


def run(script, payload, env_extra):
    env = dict(os.environ); env.update(env_extra); env["LHB_WATCH_CHILD"] = "1"
    try:
        p = subprocess.run(["bash", os.path.join(HOOKDIR, script)], input=payload, capture_output=True, env=env, timeout=60)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 0, b"", ("watch_run: %s failed to run (%s)\n" % (script, e)).encode()


def decision(rc, out):
    if rc == 2:
        return "block"
    try:
        d = json.loads(out.decode("utf-8", "replace") or "null")
        if isinstance(d, dict):
            h = d.get("hookSpecificOutput") or {}
            if h.get("permissionDecision") in ("ask", "deny"):
                return h["permissionDecision"]
            if d.get("decision") == "block":
                return "block"
    except ValueError:
        pass
    return "allow"


def summarize(payload):
    try:
        d = json.loads(payload)
        ti = d.get("tool_input") or {}
        return d.get("tool_name", ""), (ti.get("command") or ti.get("file_path") or "")[:200], d.get("session_id", "")
    except Exception:
        return "", "", ""


def log(rec):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


_OUT, _ERR = [], []


def emit(out, err):
    _OUT.append(out); _ERR.append(err)


def finish(rc):
    """Hand the result to lib/watch_gate.sh through files in LHB_WATCH_OUT; the `done` file is written LAST. If this process dies before that, watch_gate
    finds no `done` and runs the real hook itself (fail-open for the WATCHER, never for the guard)."""
    d = os.environ.get("LHB_WATCH_OUT")
    if not d:   # run by hand: old behaviour
        sys.stdout.buffer.write(b"".join(_OUT)); sys.stderr.buffer.write(b"".join(_ERR)); return rc
    for name, data in (("out", b"".join(_OUT)), ("err", b"".join(_ERR)), ("rc", str(rc).encode()), ("done", b"1")):
        with open(os.path.join(d, name), "wb") as f:
            f.write(data)
    return 0


def main():
    script = sys.argv[1]
    shadow_only = "--shadow-only" in sys.argv[2:]
    payload = sys.stdin.buffer.read()
    sw = switches()
    all_off = {"ROUNDB_" + k.upper(): "off" for k in sw}
    tool, action, sid = summarize(payload)
    base = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "guard": script, "tool": tool, "action": action, "session": sid}
    on = [k for k, v in sw.items() if v == "on"]
    if shadow_only:
        rc, out, err = run(script, payload, {"LIFEHACK_WATCH_SHADOW": "1"})
        dec = decision(rc, out)
        txt = (out + err).decode("utf-8", "replace")
        if dec != "allow" or (out.strip() and txt.strip()):
            log(dict(base, switch=on, would_decision=dec, message=txt.strip()[:400]))
        return 0
    if not on:
        rc, out, err = run(script, payload, {})
        emit(out, err)
        return rc
    s_rc, s_out, s_err = run(script, payload, {"LIFEHACK_WATCH_SHADOW": "1"})
    r_rc, r_out, r_err = run(script, payload, all_off)
    if (s_rc, s_out, s_err) != (r_rc, r_out, r_err):
        culprits = []
        for k in on:
            env = dict(all_off); env["ROUNDB_" + k.upper()] = "on"; env["LIFEHACK_WATCH_SHADOW"] = "1"
            c_rc, c_out, c_err = run(script, payload, env)
            if (c_rc, c_out, c_err) != (r_rc, r_out, r_err):
                culprits.append(k)
        log(dict(base, switch=culprits or on, would_decision=decision(s_rc, s_out), real_decision=decision(r_rc, r_out),
                 message=(s_out + s_err).decode("utf-8", "replace").strip()[:400]))
    emit(r_out, r_err)
    return r_rc


if __name__ == "__main__":
    try:
        sys.exit(finish(main()))
    except SystemExit:
        raise
    except BaseException as e:   # no `done` file is written: watch_gate.sh then runs the real hook normally
        sys.stderr.write("watch_run: error (%s); the real hook runs normally\n" % e)
        sys.exit(1)
