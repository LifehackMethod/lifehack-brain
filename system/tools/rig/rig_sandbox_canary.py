#!/usr/bin/env python3
# not-wired-yet: run by rig_sandbox.preflight() INSIDE the actor sandbox (same wrap(), same env as the actor); never part of the product hooks
"""rig_sandbox_canary.py SPEC.json - the in-sandbox half of the rig actor sandbox preflight (2026-11-02, record rig-actor-sandbox).

Runs through the SAME rig_sandbox.wrap() and the SAME env as the actor (hook-sop §4 trap 1: exercise a guard through its real entry point,
never a sibling). Prints one JSON line per attempt: {"id", "name", "ok", "detail"}. The verdict comes from errno, never from "it failed":
a sandbox refusal is EPERM (errno 1); a timeout, ENOENT or no-route proves nothing and is NOT ok. Attempts that would register something
outside the sandbox if it were broken (crontab, at, launchctl, open) are harmless no-ops; whether anything got registered is judged
OUTSIDE by rig_sandbox.preflight(), which compares the before/after state. This file never decides the run on its own.
"""
import ctypes, errno, json, os, secrets, socket, subprocess, sys, tempfile, time

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


def cwd_name():
    """A free real-shaped name for claude's cwd file, so a probe never clobbers a live session's."""
    while True:
        p = "/private/tmp/claude-%s-cwd" % secrets.token_hex(2)  # allow-silence: probes the one allowed shape; whatever lands is removed in the same check
        if not os.path.lexists(p):
            return p


def remove_any(p):
    """A breach must not leave litter in the shared /private/tmp: remove what a wrongly allowed probe made."""
    try:
        os.rmdir(p) if os.path.isdir(p) and not os.path.islink(p) else os.unlink(p)
    except OSError:
        pass


def create_probe(p, make):
    """-> (ok, detail): ok only when `make` is refused with EPERM."""
    ok, det = must_eperm(make)
    if det == "ALLOWED":
        remove_any(p)
    return ok, det


def cwd_file_checks(cf, cwd_real):
    """C12 (rig-honest-exit): the one allowance works the way claude's Bash tool uses it, and nothing wider does. FAILS if the rule is widened."""
    p = cwd_name()
    try:   # the exact shell form claude ends each Bash call with, then its read back and unlink
        q = subprocess.run(["/bin/bash", "--noprofile", "--norc", "-c", 'pwd -P >| "%s"' % p], capture_output=True, text=True, timeout=20)
        got = open(p, encoding="utf-8").read().strip() if q.returncode == 0 else ""
        if q.returncode == 0:
            os.unlink(p)
        out("C12.write", "claude's cwd file: pwd -P >| name, read back, unlink", q.returncode == 0 and got == cwd_real and not os.path.lexists(p),
            "rc=%s got=%r err=%s" % (q.returncode, got, q.stderr.strip()[:120]))
    except (OSError, subprocess.TimeoutExpired) as x:
        out("C12.write", "claude's cwd file: pwd -P >| name, read back, unlink", False, repr(x))
    for i, w in enumerate(cf["wider"]):
        ok, det = create_probe(w, lambda w=w: open(w, "x", encoding="utf-8").close())
        out("C12.wider.%d" % i, "wider than the allowance, must be refused: " + w, ok, det)
    p = cwd_name()
    ok, det = create_probe(p, lambda: os.mkdir(p))
    out("C12.mkdir", "a directory at a cwd name refused", ok, det)
    p = cwd_name()
    ok, det = create_probe(p, lambda: os.symlink("/private/etc/hosts", p))
    out("C12.symlink", "a symlink at a cwd name refused", ok, det)
    p = cwd_name()
    ok, det = create_probe(p, lambda: os.mkfifo(p))
    out("C12.fifo", "a fifo at a cwd name refused", ok, det)
    p = cwd_name()
    ok, det = create_probe(p, lambda: os.link(cf["victim"], p))
    out("C12.link", "a hard link from a write-denied file onto a cwd name refused", ok, det)
    p = cwd_name()
    try:
        open(p, "x", encoding="utf-8").close()
        ok, det = must_eperm(lambda: os.chmod(p, 0o666))
        os.unlink(p)
    except OSError as x:
        ok, det = False, "control create failed: %s" % os.strerror(x.errno)
    out("C12.chmod", "chmod on a cwd file refused (three operations only)", ok, det)
    ok, det = must_eperm(lambda: open(cf["planted"], "w", encoding="utf-8").close())   # judged again outside: the target must not exist
    out("C12.through", "writing through a symlink planted at a cwd name refused", ok, det)


def tmpdir_check(allowed):
    """C13 (rig-honest-exit): the per-run temp dir is $TMPDIR, inside an allowed dir, and python's tempfile really lands there."""
    t = os.path.realpath(os.environ.get("TMPDIR") or "/nonexistent-tmpdir")
    try:
        fd, p = tempfile.mkstemp(dir=t)
        os.write(fd, b"x")
        os.close(fd)
        fd2, p2 = tempfile.mkstemp()
        os.close(fd2)
        os.unlink(p2)
        os.unlink(p)
        inside = any(t.startswith(os.path.realpath(a) + os.sep) for a in allowed)
        out("C13.tmpdir", "per-run TMPDIR is inside an allowed dir and writable", inside and os.path.realpath(p2).startswith(t + os.sep), "TMPDIR=%s default=%s" % (t, p2))
    except OSError as x:
        out("C13.tmpdir", "per-run TMPDIR is inside an allowed dir and writable", False, "TMPDIR=%s %s" % (t, x))


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
    # C10 (STUDENT, rig-validity-fix bug 2): the real home is read-denied. Judged by errno: lexists() on a denied path is False, so only EPERM
    # counts as denied and ENOENT (decoy missing) is NOT ok. Controls: every re-allowed path must still read.
    hr = s.get("home_read")
    if hr:
        ok, det = must_eperm(lambda: open(hr["decoy"], "rb").read(1))
        out("C10.decoy", "decoy under the real home unreadable: " + hr["decoy"], ok, det)
        ok, det = must_eperm(lambda: os.listdir(hr["home"]))
        out("C10.home-list", "real home cannot be listed: " + hr["home"], ok, det)
        for i, p in enumerate(hr.get("controls", [])):
            try:
                try:
                    os.listdir(p)
                except NotADirectoryError:
                    open(p, "rb").read(1)
                out("C10.control.%d" % i, "re-allowed path readable (control): " + p, True)
            except OSError as x:
                out("C10.control.%d" % i, "re-allowed path readable (control): " + p, False, os.strerror(x.errno) if x.errno else repr(x))
        for i, p in enumerate(hr.get("probe_denied", [])):
            ok, det = must_eperm(lambda p=p: os.listdir(p))
            out("C10.probe.%d" % i, "cannot be listed: " + p, ok, det)
    # C11 (rig-validity-fix bug 1): a stand-in hook run the way claude runs hooks (bash <script>, this same actor env) can mktemp, and the
    # files land inside an allowed dir (macOS mktemp ignores TMPDIR without the rig's shim, and the shared T dir is not writable here).
    if s.get("hook_standin"):
        try:
            p = subprocess.run(["/bin/bash", s["hook_standin"]], capture_output=True, text=True, timeout=30)
            made = p.stdout.split()
            inside = len(made) == 2 and all(any(m.startswith(os.path.realpath(a) + os.sep) for a in s.get("write_allowed", [])) for m in made)
            out("C11.mktemp", "stand-in hook: mktemp + mktemp -d work inside an allowed dir", p.returncode == 0 and inside,
                "rc=%s made=%s err=%s" % (p.returncode, made, p.stderr.strip()[:150]))
        except (OSError, subprocess.TimeoutExpired) as x:
            out("C11.mktemp", "stand-in hook: mktemp + mktemp -d work inside an allowed dir", False, repr(x))
    # C14 (rig-blind-runs): a read of a sibling run's folder (and task dir) is EPERM, the rig root and task dir cannot be listed; this run's own folder reads
    rb = s.get("rig_blind")
    if rb:
        for i, p in enumerate(rb["denied"]):
            ok, det = must_eperm(lambda p=p: os.listdir(p))
            out("C14.denied.%d" % i, "read of a sibling run / listing that names one DENIED: " + p, ok, det)
        for i, p in enumerate(rb["allowed"]):
            ok, det = must_eperm(lambda p=p: os.listdir(p))
            out("C14.own.%d" % i, "read of this run's own folder ALLOWED: " + p, det == "ALLOWED", det)
    if s.get("cwd_file"):
        cwd_file_checks(s["cwd_file"], os.getcwd())
    tmpdir_check(s.get("write_allowed", []))
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
