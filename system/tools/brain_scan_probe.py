#!/usr/bin/env python3
"""brain_scan_probe.py -- is this notes folder safe to walk, or will it hang?

WHY THIS EXISTS: the AI Brain is REQUIRED to live in a cloud folder (INSTALL.md asks for a
Google Drive folder and nothing else). On macOS, Drive for Desktop mounts that folder through
the FileProvider framework, where a directory listing is not a local read -- it is a network
round-trip, resolved lazily, per directory. A tree walk over such a folder does not "run
slow": past a certain depth it BLOCKS, inside the readdir syscall, and it does not warm up --
the same walk was measured stalling identically on three consecutive runs. Measured on one
real install: a full `find` over one brain returned 21,237 entries in 1s, while the same
command over a second brain on the SAME machine timed out at 60s having reached 11,585.

WHY THE ENUMERATION RUNS IN A CHILD PROCESS. This was written twice. The first version bounded
each level with an in-process wall clock and hung anyway -- because the block is inside the
`readdir` syscall, so no Python-level check ever gets a turn to fire. A signal-based alarm has
the same problem for the same reason. The only thing that reliably stops it is killing the
process doing the walking, so the walk happens in a subprocess this one can kill. That failure
is the single most useful fact in this file: a timeout that lives in the same process as the
walk does not work, and will look like it works on every folder that was never going to hang.

WHAT "dataless" MEANS in the output: a file whose listing shows a real size but which occupies
zero blocks on disk -- present in the directory, not downloaded. Reading one forces a download.
It is reported because it is the cost people EXPECT to be the problem; on the installs measured
so far it was not (0 of 18,986 files on one brain) -- the cost was directory enumeration.
Reported so the next person can check rather than assume.

USAGE
  brain_scan_probe.py                      # probe the resolved brain root
  brain_scan_probe.py --path <folder>      # probe some other folder
  brain_scan_probe.py --budget 8           # seconds allowed per depth level (default 8)
  brain_scan_probe.py --json               # machine-readable

EXIT CODES
  0  WALKABLE        -- every level enumerated within budget
  1  STALLS          -- a level blew its budget; do not walk this folder
  2  CANNOT EVALUATE -- no such folder, or the brain root is not set

Compatible with /usr/bin/python3 (3.9) -- no `X | None` unions, stdlib only.
"""
import argparse
import json
import os
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.abspath(os.path.join(_HERE, "..", "..", "shared"))
if os.path.isdir(_SHARED):
    sys.path.insert(0, _SHARED)


def _resolve_root():
    """The brain root, through the one resolver -- never a hardcoded path."""
    try:
        import brain_root  # noqa: E402
        _src, path = brain_root.resolve_brain_root()
        return path
    except Exception:
        return None


# --------------------------------------------------------------------------------------
# WORKER: runs in the child. Walks breadth-first, printing one JSON line per COMPLETED
# level and flushing immediately, so that whatever arrives before the parent kills it is
# a true record of the levels that finished.
# --------------------------------------------------------------------------------------
def _worker(root, max_depth):
    frontier = [root]
    for depth in range(1, max_depth + 1):
        t0 = time.time()
        nxt = []
        dirs = files = dataless = 0
        for path in frontier:
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                dirs += 1
                                nxt.append(entry.path)
                            else:
                                files += 1
                                st = entry.stat(follow_symlinks=False)
                                if st.st_size > 0 and getattr(st, "st_blocks", 1) == 0:
                                    dataless += 1
                        except OSError:
                            pass
            except OSError:
                pass
        sys.stdout.write(json.dumps({
            "depth": depth, "dirs": dirs, "files": files,
            "dataless": dataless, "seconds": round(time.time() - t0, 2),
        }) + "\n")
        sys.stdout.flush()
        frontier = nxt
        if not frontier:
            break
    sys.stdout.write(json.dumps({"done": True}) + "\n")
    sys.stdout.flush()


def probe(root, budget=8.0, max_depth=8):
    """Run the walk in a killable child. Returns (walkable, levels).

    The parent enforces the clock because the child cannot: a process blocked in readdir
    cannot time itself out. `budget` is per level; the child is given the running total and
    killed the moment a level overruns it.
    """
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--worker",
         "--path", root, "--max-depth", str(max_depth)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    levels = []
    completed = False
    try:
        while True:
            deadline = time.time() + budget
            line = None
            # readline() itself can block past the deadline, so the deadline is enforced by
            # polling the pipe rather than trusting the read to return.
            import select
            while time.time() < deadline:
                r, _w, _x = select.select([proc.stdout], [], [], 0.2)
                if r:
                    line = proc.stdout.readline()
                    break
            if line is None:
                break                      # level overran its budget -> stall
            if not line.strip():
                if proc.poll() is not None:
                    break
                continue
            rec = json.loads(line)
            if rec.get("done"):
                completed = True
                break
            levels.append(rec)
            if len(levels) >= max_depth:
                completed = True
                break
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    return completed, levels


def main():
    ap = argparse.ArgumentParser(description="Detect whether a notes folder can be walked safely.")
    ap.add_argument("--path", default=None, help="folder to probe (default: the resolved brain root)")
    ap.add_argument("--budget", type=float, default=8.0, help="seconds allowed per depth level")
    ap.add_argument("--max-depth", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    root = args.path or _resolve_root()
    if not root:
        print("CANNOT EVALUATE: the brain root is not set, and no --path was given.")
        print('Set it with: python3 shared/brain_root.py --set "<your AI Brain folder>"')
        return 2
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(root):
        print("CANNOT EVALUATE: not a directory: %s" % root)
        return 2

    if args.worker:
        _worker(root, args.max_depth)
        return 0

    walkable, levels = probe(root, budget=args.budget, max_depth=args.max_depth)

    if args.json:
        print(json.dumps({"root": root, "walkable": walkable, "levels": levels}, indent=2))
        return 0 if walkable else 1

    print("probing: %s" % root)
    print("budget:  %.1fs per depth level\n" % args.budget)
    print("%5s %8s %8s %9s %8s  %s" % ("depth", "dirs", "files", "dataless", "secs", "verdict"))
    for lv in levels:
        verdict = "slow" if lv["seconds"] > 1.0 else "ok"
        print("%5d %8d %8d %9d %8.1f  %s" % (
            lv["depth"], lv["dirs"], lv["files"], lv["dataless"], lv["seconds"], verdict))
    if not walkable:
        print("%5s %8s %8s %9s %8s  %s" % (
            len(levels) + 1, "-", "-", "-", ">%.0f" % args.budget,
            "STALLED -- budget hit, walk killed"))

    total_dataless = sum(lv["dataless"] for lv in levels)
    print("")
    if walkable:
        print("WALKABLE -- every level enumerated inside its budget.")
        if total_dataless:
            print("Note: %d file(s) are present but not downloaded. A CONTENT search will" % total_dataless)
            print("still have to fetch those, which the listing above does not measure.")
        return 0
    print("STALLS -- this folder is a cloud-streamed mount and a recursive scan will hang.")
    print("Do not grep/find/glob it. Search it through the Spotlight index instead:")
    print("    python3 system/tools/brain_search.py --text \"<phrase>\"")
    print("    python3 system/tools/brain_search.py --name \"<filename>\"")
    return 1


if __name__ == "__main__":
    sys.exit(main())
