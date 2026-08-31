#!/usr/bin/env python3
"""brain_search.py -- find things in the AI Brain without walking a cloud mount.

WHY THIS EXISTS: the AI Brain is required to live in a cloud folder, and on macOS that folder
is a FileProvider mount where enumerating a directory is a network round-trip. Recursive
grep/find/glob over it does not merely run slow -- past a certain depth it BLOCKS inside the
readdir syscall, unrecoverably, every time (it does not warm up: the same walk was measured
stalling identically on three consecutive runs). See docs/findings/drive-scan-stall.md for the
measurements and system/tools/brain_scan_probe.py to reproduce them on any machine.

HOW THIS AVOIDS THE STALL: it never walks the tree. Spotlight has already indexed that folder,
so `mdfind` answers from the index in ~1s where a walk times out at 60s -- and it reads inside
PDF and .docx content that grep cannot read at all.

WHY THIS IS NOT THE "SEMANTIC INDEX" /read DELIBERATELY REMOVED. That tier was rejected on two
specific grounds, and this clears both:
  1. "It needed an external package fetched at run time." This fetches nothing. `mdfind` is
     part of macOS, already running, no install and no network call of our own.
  2. "It was only ever as fresh as its last reindex -- it could not answer 'did I just save
     that?'" The index here is used ONLY to narrow the candidate set. Every hit is then read
     back off the LIVE file before it is reported, so reported content is never a cached copy.
     Spotlight was measured picking up a newly written file in ~3 seconds; to close even that
     window, --text also checks files modified in the last FRESH_WINDOW_S regardless of what
     the index says. "Live files, every time" still holds -- what changes is how the candidate
     list is built, not what gets read.

DEGRADES HONESTLY. On a machine with no `mdfind` (Linux, or Spotlight disabled on that volume)
it falls back to a BOUNDED walk and says so in its output. It never silently returns a partial
result as though it were complete -- a search that could not look must not be spelled the same
way as a search that looked and found nothing.

USAGE
  brain_search.py --text "phrase"        # content search
  brain_search.py --name "filename"      # filename search
  brain_search.py --text "x" --under desks/ai-system   # scope to a sub-path
  brain_search.py --text "x" --json

EXIT CODES
  0  the search actually looked everywhere (zero hits is then a real answer)
  1  the search could NOT look everywhere -- truncated fallback. Never 0, even if it
     found something: "could not look" must not be spelled like "looked and found nothing"
  2  CANNOT EVALUATE -- brain root not set, or bad arguments

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

MDFIND_TIMEOUT_S = 20      # the index answers in ~1s; 20 is a wedged-Spotlight guard
FALLBACK_BUDGET_S = 20     # hard ceiling on the no-Spotlight walk
FRESH_WINDOW_S = 300       # also sweep files touched this recently, whatever the index says
MAX_CONFIRM = 400          # live-read at most this many candidates


def _resolve_root():
    try:
        import brain_root  # noqa: E402
        _src, path = brain_root.resolve_brain_root()
        return path
    except Exception:
        return None


def _have_mdfind():
    return os.path.exists("/usr/bin/mdfind")


def _mdfind(root, query, by_name):
    """Ask Spotlight. Returns (paths, ok). ok=False means Spotlight could not answer."""
    cmd = ["/usr/bin/mdfind", "-onlyin", root]
    if by_name:
        cmd += ["-name", query]
    else:
        cmd += [query]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=MDFIND_TIMEOUT_S)
    except (subprocess.TimeoutExpired, OSError):
        return [], False
    if out.returncode != 0:
        return [], False
    paths = [p for p in out.stdout.splitlines() if p.strip()]
    return paths, True


# The walk runs in a CHILD process, always. A wall-clock check in this process cannot stop a
# walk blocked inside `readdir`, and neither can SIGALRM -- the interpreter never gets a turn.
# Killing the process doing the walking is the only thing that works. (An earlier draft of this
# file bounded the walk in-process and hung on the very folder it was written for; so did the
# first draft of brain_scan_probe.py. Same mistake, same cause, worth only making once.)
_WALK_CHILD = r"""
import os, sys
root, max_depth, cutoff = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
frontier = [root]
for _d in range(max_depth):
    nxt = []
    for path in frontier:
        try:
            with os.scandir(path) as it:
                for e in it:
                    try:
                        if e.name.startswith('.'):
                            continue
                        if e.is_dir(follow_symlinks=False):
                            nxt.append(e.path)
                        elif cutoff <= 0 or e.stat(follow_symlinks=False).st_mtime >= cutoff:
                            sys.stdout.write(e.path + '\n')
                    except OSError:
                        pass
        except OSError:
            pass
    sys.stdout.flush()
    frontier = nxt
    if not frontier:
        break
sys.stdout.write('COMPLETE-SENTINEL-8f3a\n')
"""

_SENTINEL = "COMPLETE-SENTINEL-8f3a"


def _child_walk(root, max_depth, budget_s, cutoff=0.0):
    """Walk in a killable subprocess. Returns (paths, complete)."""
    try:
        out = subprocess.run(
            [sys.executable, "-c", _WALK_CHILD, root, str(max_depth), str(cutoff)],
            capture_output=True, text=True, timeout=budget_s,
        )
        text = out.stdout or ""
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout or ""
        text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
    except OSError:
        return [], False
    complete = _SENTINEL in text
    paths = [ln for ln in text.splitlines() if ln and ln != _SENTINEL]
    return paths, complete


def _recent_files(root, window_s, budget_s=5.0):
    """Shallow sweep for files written in the last `window_s`, to cover the index lag.

    A safety net, not a search: bounded by depth AND by a clock that can actually fire.
    """
    paths, _complete = _child_walk(root, 4, budget_s, cutoff=time.time() - window_s)
    return paths


def _bounded_walk(root, budget_s):
    """Last resort when Spotlight is unavailable. Returns (paths, complete)."""
    return _child_walk(root, 32, budget_s)


# Extensions whose text lives in a container format: Spotlight can read inside them, a plain
# text read cannot. A candidate of this kind that we cannot confirm is NOT a miss to discard --
# it is a hit we could not personally verify, and it gets reported that way. (grep never found
# these at all; dropping them silently would make this tool quietly worse than the index it is
# built on.)
OPAQUE_EXTS = (".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".xls", ".key", ".pages", ".numbers",
               ".rtf", ".odt", ".epub")


def _confirm_live(paths, needle):
    """Read each candidate off the LIVE file. This is what keeps freshness honest.

    Returns (confirmed, unverifiable) -- the second list is candidates the index matched but
    this process cannot read as text, reported rather than dropped.
    """
    confirmed = []
    unverifiable = []
    for p in paths[:MAX_CONFIRM]:
        if p.lower().endswith(OPAQUE_EXTS):
            unverifiable.append(p)
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                body = fh.read()
        except (OSError, ValueError):
            unverifiable.append(p)
            continue
        if needle.lower() in body.lower():
            confirmed.append(p)
    return confirmed, unverifiable


def main():
    ap = argparse.ArgumentParser(description="Search the AI Brain without walking the cloud mount.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="search inside file contents")
    g.add_argument("--name", help="search filenames")
    ap.add_argument("--under", default=None, help="restrict to a sub-path of the brain root")
    ap.add_argument("--root", default=None, help="override the brain root (testing)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--no-index", action="store_true",
                    help="ignore Spotlight and use the fallback walk (what a non-Mac install gets)")
    args = ap.parse_args()

    root = args.root or _resolve_root()
    if not root:
        print("CANNOT EVALUATE: the brain root is not set.")
        print('Set it with: python3 shared/brain_root.py --set "<your AI Brain folder>"')
        return 2
    root = os.path.abspath(os.path.expanduser(root))
    if args.under:
        root = os.path.join(root, args.under)
    if not os.path.isdir(root):
        print("CANNOT EVALUATE: not a directory: %s" % root)
        return 2

    query = args.text or args.name
    by_name = args.name is not None
    method = None
    trustworthy = True
    used_index = False

    if _have_mdfind() and not args.no_index:
        candidates, ok = _mdfind(root, query, by_name)
        if ok:
            method = "spotlight index (mdfind)"
            used_index = True
        else:
            method = "bounded walk (Spotlight did not answer)"
            candidates, complete = _bounded_walk(root, FALLBACK_BUDGET_S)
            trustworthy = complete
    else:
        method = "bounded walk (no mdfind on this platform)"
        candidates, complete = _bounded_walk(root, FALLBACK_BUDGET_S)
        trustworthy = complete

    unverifiable = []
    if by_name:
        hits = candidates
    else:
        # index narrows; the live file decides. Plus a sweep for anything too new to be indexed.
        fresh = _recent_files(root, FRESH_WINDOW_S)
        merged = list(dict.fromkeys(list(candidates) + fresh))
        hits, unverifiable = _confirm_live(merged, query)

    hits = sorted(hits)
    unverifiable = sorted(unverifiable)
    shown = hits[:args.limit]

    if args.json:
        print(json.dumps({
            "root": root, "query": query, "mode": "name" if by_name else "text",
            "method": method, "trustworthy": trustworthy,
            "total": len(hits), "hits": shown,
            "unverifiable": unverifiable,
        }, indent=2))
        return 0 if trustworthy else 1

    print("searched: %s" % root)
    print("query:    %r  (%s)" % (query, "filename" if by_name else "content"))
    print("method:   %s" % method)
    if not trustworthy:
        print("")
        print("⚠ INCOMPLETE -- the fallback walk hit its %ds ceiling before finishing." % FALLBACK_BUDGET_S)
        print("  Treat 'no hits' below as 'could not look', NOT as 'nothing there'.")
    print("")
    if not hits:
        print("no hits.")
    else:
        print("%d hit(s)%s:" % (len(hits), "" if len(hits) <= args.limit else
                                 " -- showing first %d" % args.limit))
        for p in shown:
            print("  %s" % os.path.relpath(p, root))
    if unverifiable:
        print("")
        seen_by = "the index matched" if used_index else "were found"
        print("%d further file(s) %s but this tool cannot read as text" % (len(unverifiable), seen_by))
        print("(PDF/Office/etc). Listed, not dropped -- open them to confirm:")
        for p in unverifiable[:10]:
            print("  ? %s" % os.path.relpath(p, root))
    return 0 if trustworthy else 1


if __name__ == "__main__":
    sys.exit(main())
