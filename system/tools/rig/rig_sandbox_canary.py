#!/usr/bin/env python3
# not-wired-yet: run by rig_sandbox.preflight() INSIDE the actor sandbox (same wrap(), same env as the actor); never part of the product hooks
"""rig_sandbox_canary.py SPEC.json - the in-sandbox half of the rig actor sandbox preflight (2026-11-02, record rig-actor-sandbox).

Runs through the SAME rig_sandbox.wrap() and the SAME env as the actor (hook-sop §4 trap 1: exercise a guard through its real entry point,
never a sibling). Prints one JSON line per attempt: {"id", "name", "ok", "detail"}. The verdict comes from errno, never from "it failed":
a sandbox refusal is EPERM (errno 1); a timeout, ENOENT or no-route proves nothing and is NOT ok. Attempts that would register something
outside the sandbox if it were broken (crontab, at, launchctl, open) are harmless no-ops; whether anything got registered is judged
OUTSIDE by rig_sandbox.preflight(), which compares the before/after state. This file never decides the run on its own.
"""
import ctypes, errno, json, os, socket, subprocess, sys, time

EPERM = errno.EPERM


def out(i, name, ok, detail=""):
    print(json.dumps({"id": i, "name": name, "ok": bool(ok), "detail": str(detail)[:300]}), flush=True)


def sandboxed():
    try:
        lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        f = lib.sandbox_check
        f.restype, f.argtypes = ctypes.c_int, [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        return f(os.getpid(), None, 0) == 1
    except (OSError, AttributeError):
        return False


def must_eperm(fn):
    """-> (ok, detail). ok only when fn raises EPERM."""
    try:
        fn()
        return False, "ALLOWED"
    except OSError as e:
        return e.errno == EPERM, os.strerror(e.errno) if e.errno else repr(e)


def mkdir_probe(d, nonce):
    p = os.path.join(d, ".rig-canary-" + nonce)
    ok, det = must_eperm(lambda: os.mkdir(p))
    return ok, det, p


def connect_direct(host, port):
    ip = socket.gethostbyname(host) if not host.replace(".", "").isdigit() else host
    s = socket.socket()
    s.settimeout(8)
    try:
        s.connect((ip, port))
    finally:
        s.close()


def via_proxy(pport, target):
    s = socket.create_connection(("127.0.0.1", pport), 8)
    try:
        s.sendall(("CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n" % (target, target)).encode())
        return s.recv(200).decode("latin-1").split("\r\n", 1)[0]
    finally:
        s.close()


def run(cmd, inp=None, timeout=20):
    try:
        p = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stderr or p.stdout).strip()[:200]
    except OSError as e:          # exec refused (setuid binary under a sandbox: EPERM) or binary missing
        return -e.errno, os.strerror(e.errno)
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def main(spec_path):
    s = json.load(open(spec_path, encoding="utf-8"))
    n = s["nonce"]
    out("C0", "this process is sandboxed (sandbox_check)", sandboxed())
    for i, d in enumerate(s.get("write_denied", [])):
        ok, det, p = mkdir_probe(d, n)
        out("C1.%d" % i, "write denied: " + d, ok, det)
    for i, d in enumerate(s.get("write_allowed", [])):
        p = os.path.join(d, ".rig-canary-" + n)
        try:
            os.mkdir(p)
            os.rmdir(p)
            out("C4.%d" % i, "write allowed (control): " + d, True)
        except OSError as e:
            out("C4.%d" % i, "write allowed (control): " + d, False, os.strerror(e.errno))
    for i, (h, port) in enumerate(s.get("direct_hosts", [])):
        try:
            ok, det = must_eperm(lambda: connect_direct(h, port))
        except socket.gaierror as e:   # DNS failure is not proof of a kernel deny
            ok, det = False, "dns: %s" % e
        except socket.timeout:
            ok, det = False, "timeout (not a kernel deny)"
        out("C5.%d" % i, "direct connect denied: %s:%d" % (h, port), ok, det)
    px = s.get("proxy") or {}
    for i, t in enumerate(px.get("denied", [])):
        try:
            st = via_proxy(px["port"], t)
            out("C6.%d" % i, "proxy refuses " + t, " 403 " in st + " ", st)
        except OSError as e:
            out("C6.%d" % i, "proxy refuses " + t, False, "proxy unreachable: %s" % e)
    for i, t in enumerate(px.get("allowed", [])):
        try:
            st = via_proxy(px["port"], t)
            out("C7.%d" % i, "proxy allows " + t + " (control)", " 200 " in st + " ", st)
        except OSError as e:
            out("C7.%d" % i, "proxy allows " + t + " (control)", False, "proxy unreachable: %s" % e)
    for i, p in enumerate(s.get("read_denied", [])):
        fn = (lambda p=p: os.listdir(p)) if os.path.isdir(p) else (lambda p=p: open(p, "rb").read(1))
        ok, det = must_eperm(fn)
        out("C8.%d" % i, "read denied: " + p, ok, det)
    e = s.get("escapes") or {}
    if e.get("security"):
        rc, det = run([e["security"], "show-keychain-info"])
        out("C9.keychain", "keychain unreachable (security show-keychain-info)", rc != 0, "rc=%s %s" % (rc, det))
    if e.get("osascript"):
        # `get name` of an application object is answered locally (no event sent: rc 0 even when Apple Events are denied), so ask for
        # something only the target process knows: the list of running processes
        rc, det = run([e["osascript"], "-e", 'tell application "System Events" to get name of every process'])
        out("C9.appleevent", "Apple Events refused", rc != 0, "rc=%s %s" % (rc, det))
    # NO `open x.command` probe: under the sandbox it raises a visible macOS dialog every run (removed 2026-11-02 at the owner's request).
    # LaunchServices - the door `open`/Terminal go through - is probed QUIETLY: lsappinfo asks launchservicesd for the front app; refused
    # (mach-lookup denied) it prints "[ NULL ]" instead of an ASN. Shown both ways when written: outside -> "ASN:0x...", inside -> "[ NULL ]".
    if e.get("lsappinfo"):
        try:
            p = subprocess.run([e["lsappinfo"], "front"], capture_output=True, text=True, timeout=20)
            o = (p.stdout + p.stderr).strip()
        except (OSError, subprocess.TimeoutExpired) as x:
            o = repr(x)
        out("C9.launchservices", "LaunchServices unreachable (lsappinfo front gives no app)", "ASN:" not in o, o[:120])
    # crontab/at are setuid: inside the sandbox the kernel refuses to EXEC them at all (EPERM). Probe with their READ-ONLY list form, so a
    # broken sandbox can never replace the person's crontab or queue a job: ok only when the exec itself was refused.
    if e.get("crontab"):
        rc, det = run([e["crontab"], "-l"])
        out("C9.crontab", "crontab cannot even start (exec refused)", rc == -EPERM, "rc=%s %s" % (rc, det))
    if e.get("at"):
        rc, det = run([e["at"], "-l"])
        out("C9.at", "at cannot even start (exec refused)", rc == -EPERM, "rc=%s %s" % (rc, det))
    if e.get("launchctl"):
        lc = e["launchctl"]
        rc, det = run([lc, "submit", "-l", e["label"] + ".submit", "--", "/usr/bin/true"])
        out("C9.lc-submit", "launchctl submit refused (judged outside)", rc != 0, "rc=%s %s" % (rc, det))
        rc, det = run([lc, "load", e["plist"]])
        out("C9.lc-load", "launchctl load attempted (judged outside)", True, "rc=%s %s" % (rc, det))
        rc, det = run([lc, "bootstrap", "gui/%d" % os.getuid(), e["plist"]])
        out("C9.lc-bootstrap", "launchctl bootstrap refused (judged outside)", rc != 0, "rc=%s %s" % (rc, det))
    time.sleep(0)


if __name__ == "__main__":
    main(sys.argv[1])
