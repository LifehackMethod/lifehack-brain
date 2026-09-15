#!/usr/bin/env python3
"""sony_zve10.py — drive the Sony ZV-E10 (original) over USB from the Mac via gphoto2.

Read-only by default. Changing a setting needs --set AND --yes. There is no delete, format,
or file-write verb in this tool and there never will be: footage on the card is irreplaceable.

Why it looks the way it does (verified 2026-09-15, macOS 26.5, gphoto2 2.5.32):
  * macOS's own camera daemons (ptpcamerad, mscamerad-xpc) grab the camera on plug-in and
    gphoto2 fails with "Could not claim the USB device". launchctl refuses under SIP, but a
    plain kill works and launchd only respawns them after a moment. So every call kills them
    first, and every operation is ONE gphoto2 invocation (one USB claim).
  * A read straight after a set returns the OLD value; the camera has to emit its event
    first. So a set is: set → wait-event → read back.
  * Card files are not visible in PC Remote mode. Use Mass Storage on the body for that.

Camera side: MENU → Network → PC Remote Function → PC Remote On, Cnct Method USB;
Smartphone Connect Off; USB Streaming off; mode dial on movie; USB-C to the Mac.

Examples:
  sony_zve10.py detect
  sony_zve10.py status                 # battery, firmware, exposure, WB, focus, recording state
  sony_zve10.py dump [-o dump.txt]     # every readable property
  sony_zve10.py get whitebalance iso
  sony_zve10.py choices whitebalance   # the values a setting accepts
  sony_zve10.py set whitebalance=Daylight --yes
  sony_zve10.py record --seconds 3 --yes
  sony_zve10.py preview -o frame.jpg    # one live-view frame to judge exposure and framing
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time

DAEMONS = ("ptpcamerad", "mscamerad-xpc")

# Short names → gphoto2 config paths. Anything else is passed through as a full /main/... path.
ALIASES = {
    "whitebalance": "/main/imgsettings/whitebalance",
    "wb": "/main/imgsettings/whitebalance",
    "iso": "/main/imgsettings/iso",
    "colortemperature": "/main/imgsettings/colortemperature",
    "aperture": "/main/capturesettings/f-number",
    "f-number": "/main/capturesettings/f-number",
    "shutterspeed": "/main/capturesettings/shutterspeed",
    "exposurecompensation": "/main/capturesettings/exposurecompensation",
    "ev": "/main/capturesettings/exposurecompensation",
    "focusmode": "/main/capturesettings/focusmode",
    "focusarea": "/main/capturesettings/focusarea",
    "expprogram": "/main/capturesettings/expprogram",
    "dro": "/main/capturesettings/dro",
    "metering": "/main/capturesettings/exposuremetermode",
    "zoom": "/main/capturesettings/zoom",
    "battery": "/main/status/batterylevel",
    "firmware": "/main/status/deviceversion",
    "serial": "/main/status/serialnumber",
    "recording": "/main/other/d21d",       # Movie Recording State: 0 idle, 1 recording
    "remaining": "/main/other/d24a",       # Media SLOT1 Shooting Time (seconds left)
    "pictureprofile": "/main/other/d23f",
    "movieformat": "/main/other/d241",
    "moviesetting": "/main/other/d242",
    "focus": "/main/status/focusindication",
}

# Paths this tool refuses to touch, ever. FormatMedia would wipe the card.
FORBIDDEN = ("d2ca", "formatmedia", "delete", "format")

STATUS_KEYS = ["firmware", "battery", "expprogram", "aperture", "shutterspeed", "iso", "ev",
               "whitebalance", "focusmode", "focusarea", "focus", "recording", "remaining"]


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve(name):
    if name.startswith("/main/"):
        path = name
    elif name in ALIASES:
        path = ALIASES[name]
    else:
        die(f"unknown setting '{name}'. Use a name from --help or a full /main/... path.")
    low = path.lower()
    if any(f in low for f in FORBIDDEN):
        die(f"refusing to touch '{path}': that property can destroy footage.")
    return path


def kill_daemons():
    """Free the USB device from macOS's camera services. Harmless if they are not running."""
    subprocess.run(["pkill", "-9", "-f", "|".join(DAEMONS)], capture_output=True)
    time.sleep(0.2)


def gphoto(args, timeout=60):
    if not shutil.which("gphoto2"):
        die("gphoto2 not installed. `brew install gphoto2` (tier 2 — ask first).")
    kill_daemons()
    p = subprocess.run(["gphoto2", *args], capture_output=True, text=True, timeout=timeout)
    out = p.stdout + p.stderr
    out = "\n".join(l for l in out.splitlines()
                    if "UNKNOWN PTP Property 00000000" not in l and "Waiting for" not in l)
    if "Could not claim the USB device" in out:
        die("macOS still holds the camera. Unplug, replug, and try again.", 3)
    if "Unknown model" in out or "no camera" in out.lower() and "auto-detect" not in args:
        die("no camera found. Is it on, in PC Remote (USB) mode, and plugged in?", 3)
    return p.returncode, out


def parse_blocks(text, paths=None):
    """Turn gphoto2 output into {path: {Label, Current, Readonly, Choices}}.

    --list-all-config prints a '/main/...' line before each block; --get-config does not, so
    blocks there are matched to `paths` in order.
    """
    blocks, cur, path, n = {}, None, None, 0
    for line in text.splitlines():
        if line.startswith("/main/"):
            path, cur = line.strip(), {"Choices": []}
            blocks[path] = cur
        elif line.startswith("Label:") and cur is None:
            path = paths[n] if paths and n < len(paths) else f"block{n}"
            n += 1
            cur = {"Choices": []}
            blocks[path] = cur
            cur["Label"] = line.split(":", 1)[1].strip()
        elif line.startswith("END"):
            cur = None
        elif cur is not None:
            if line.startswith("Choice:"):
                cur["Choices"].append(line.split(" ", 2)[-1])
            elif ":" in line:
                k, v = line.split(":", 1)
                cur[k.strip()] = v.strip()
    return blocks


def cmd_detect(_):
    rc, out = gphoto(["--auto-detect"])
    print(out.strip())
    return 0 if "ZV-E10" in out else 1


def cmd_get(a):
    paths = [resolve(n) for n in a.names]
    args = []
    for p in paths:
        args += ["--get-config", p]
    _, out = gphoto(args)
    for p, b in parse_blocks(out, paths).items():
        print(f"{b.get('Label', p)}: {b.get('Current', '?')}"
              + ("  [read-only]" if b.get("Readonly") == "1" else ""))
    return 0


def cmd_choices(a):
    p = resolve(a.name)
    _, out = gphoto(["--get-config", p])
    b = parse_blocks(out, [p]).get(p, {})
    print(f"{b.get('Label', p)} — current: {b.get('Current')}")
    for c in b.get("Choices", []):
        print("  ", c)
    return 0


def cmd_status(a):
    a.names = STATUS_KEYS
    return cmd_get(a)


def cmd_dump(a):
    _, out = gphoto(["--summary", "--list-all-config"], timeout=180)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(out)
        n = sum(1 for l in out.splitlines() if l.startswith("/main/"))
        print(f"wrote {a.output}: {n} properties")
    else:
        print(out)
    return 0


def cmd_set(a):
    if not a.yes:
        die("changing a camera setting needs --yes (explicit on purpose).")
    if "=" not in a.assignment:
        die("use NAME=VALUE, e.g. whitebalance=Daylight")
    name, value = a.assignment.split("=", 1)
    p = resolve(name)
    _, before = gphoto(["--get-config", p])
    b = parse_blocks(before, [p]).get(p, {})
    if b.get("Readonly") == "1":
        die(f"{b.get('Label', p)} is read-only in the camera's current mode.")
    if b.get("Choices") and value not in b["Choices"]:
        die(f"'{value}' is not a valid value. Run: choices {name}")
    _, out = gphoto(["--set-config-value", f"{p}={value}", "--wait-event=2s", "--get-config", p])
    after = parse_blocks(out, [p]).get(p, {}).get("Current")
    print(f"{b.get('Label', p)}: {b.get('Current')} → {after}")
    if after != value:
        print("WARNING: read-back does not match. Re-read with `get` in a second.", file=sys.stderr)
        return 1
    return 0


def cmd_record(a):
    if not a.yes:
        die("recording writes a clip to the card; needs --yes.")
    secs = max(1, int(a.seconds))
    rec, rem = ALIASES["recording"], ALIASES["remaining"]
    _, out = gphoto(["--get-config", rem,
                     "--set-config", "/main/actions/movie=1", "--wait-event=1s",
                     "--get-config", rec, f"--wait-event={max(0, secs - 1)}s",
                     "--set-config", "/main/actions/movie=0", "--wait-event=3s",
                     "--get-config", rec, "--get-config", rem], timeout=secs + 40)
    states = re.findall(r"Movie Recording State\nReadonly: \d\nType: \w+\nCurrent: (\d)", out)
    times = re.findall(r"Shooting Time\nReadonly: \d\nType: \w+\nCurrent: (\d+)", out)
    print(f"recording state during/after: {states}; card seconds before/after: {times}")
    ok = states[:1] == ["1"] and states[-1:] == ["0"]
    print("RECORDED" if ok else "NOT CONFIRMED — check the camera screen")
    return 0 if ok else 1


def cmd_preview(a):
    """One live-view frame (1024x576 JPEG on the ZV-E10) so the operator can judge the shot."""
    out_path = os.path.abspath(a.output)
    _, out = gphoto(["--capture-preview", "--filename", out_path])
    # gphoto2 prefixes the name with thumb_ on some builds; report whichever landed.
    d, b = os.path.split(out_path)
    for cand in (out_path, os.path.join(d, "thumb_" + b)):
        if os.path.exists(cand):
            print(f"wrote {cand} ({os.path.getsize(cand)} bytes)")
            return 0
    print(out)
    die("no preview frame was written", 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect", help="is the camera visible in PC Remote mode?").set_defaults(fn=cmd_detect)
    sub.add_parser("status", help="the settings that matter, in one screen").set_defaults(fn=cmd_status)
    d = sub.add_parser("dump", help="every readable property (read-only)")
    d.add_argument("-o", "--output", help="write to this file instead of stdout")
    d.set_defaults(fn=cmd_dump)
    g = sub.add_parser("get", help="read one or more settings")
    g.add_argument("names", nargs="+", help=", ".join(sorted(ALIASES)))
    g.set_defaults(fn=cmd_get)
    c = sub.add_parser("choices", help="list the values a setting accepts")
    c.add_argument("name")
    c.set_defaults(fn=cmd_choices)
    s = sub.add_parser("set", help="change ONE setting (needs --yes)")
    s.add_argument("assignment", help="NAME=VALUE")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_set)
    v = sub.add_parser("preview", help="grab one live-view frame as JPEG (read-only)")
    v.add_argument("-o", "--output", default="preview.jpg")
    v.set_defaults(fn=cmd_preview)
    r = sub.add_parser("record", help="start and stop a movie recording (needs --yes)")
    r.add_argument("--seconds", default=3)
    r.add_argument("--yes", action="store_true")
    r.set_defaults(fn=cmd_record)
    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
