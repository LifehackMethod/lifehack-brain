#!/usr/bin/env python3
# not-wired-yet: started by rig_sandbox.py (outside the actor sandbox) for every live rig actor; never part of the product hooks
"""rig_proxy.py - the ONE network door of a sandboxed rig actor (2026-11-02, record rig-actor-sandbox).

WHY: the actor runs under sandbox-exec (rig_sandbox.py), whose profile denies every outbound connection except 127.0.0.1:<this port>.
     SBPL cannot filter by host name, so the host allowlist lives here, in a process OUTSIDE the sandbox.
WHAT: an HTTP CONNECT proxy that tunnels only to the host:port pairs given on the command line (live runs: api.anthropic.com:443) and
     answers 403 to anything else (plain-HTTP requests included). Every request is logged one JSON line per decision, so a host the
     actor or claude asked for and did not get is a run finding, not a silent failure.
     If this process dies, the actor has no network at all: the sandbox fails closed.
Usage: rig_proxy.py --allow api.anthropic.com:443 [--allow HOST:PORT ...] --log FILE [--port 0]
       Prints "PORT <n>" on stdout once listening, then serves until killed.
"""
import argparse, json, select, socket, sys, threading, time


def log(path, **kw):
    kw["t"] = time.strftime("%H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw) + "\n")


def pipe(a, b):
    socks = [a, b]
    try:
        while True:
            r, _, _ = select.select(socks, [], [], 300)
            if not r:
                return
            for s in r:
                d = s.recv(65536)
                if not d:
                    return
                (b if s is a else a).sendall(d)
    except OSError:
        return


def handle(c, allow, logpath):
    try:
        c.settimeout(30)
        head = b""
        while b"\r\n\r\n" not in head and len(head) < 65536:
            d = c.recv(4096)
            if not d:
                return
            head += d
        parts = head.split(b"\r\n", 1)[0].decode("latin-1").split()
        target = parts[1] if len(parts) >= 2 else ""
        if len(parts) < 2 or parts[0] != "CONNECT" or target.lower() not in allow:
            log(logpath, verdict="REFUSE", method=parts[0] if parts else "", target=target[:200])
            c.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            return
        host, _, port = target.rpartition(":")
        u = socket.create_connection((host, int(port)), 15)
        log(logpath, verdict="ALLOW", target=target)
        c.settimeout(None)
        c.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
        pipe(c, u)
        u.close()
    except Exception as e:   # one bad client never takes the proxy down; the failure is logged
        log(logpath, verdict="ERROR", error=repr(e)[:200])
    finally:
        c.close()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow", action="append", required=True, help="HOST:PORT the actor may reach (repeatable)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--port", type=int, default=0)
    a = ap.parse_args(argv)
    allow = {x.lower() for x in a.allow}
    for x in allow:
        if x.count(":") != 1 or not x.rpartition(":")[2].isdigit() or "*" in x:
            sys.exit("rig_proxy: --allow must be an exact HOST:PORT, no wildcard: %r" % x)
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", a.port))
    s.listen(64)
    port = s.getsockname()[1]
    log(a.log, verdict="LISTEN", port=port, allow=sorted(allow))
    print("PORT %d" % port, flush=True)
    while True:
        conn, _ = s.accept()
        threading.Thread(target=handle, args=(conn, allow, a.log), daemon=True).start()


if __name__ == "__main__":
    main()
