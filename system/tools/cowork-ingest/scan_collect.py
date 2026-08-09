#!/usr/bin/env python3
"""
scan_collect.py — the SCAN rung's COLLECTOR (controller-side; runs OFF the main session's eyes).

The SCAN phase spawns tool-less reader subagents over gate-sanitized SLICES; each returns, per chat,
a JSON row {file, guess, gist}. This tool reads those raw agent outputs and lands them safely in the
corpus map. It does THREE things, all of which are the security wall — not convenience:

  1. VALIDATE the guess against the closed verb set {toss, research, park}. Anything else → dropped
     (guess=None). A hijacked reader cannot inject a novel verdict.
  2. SECOND-GATE the free-text gist. The gist is untrusted content (an LLM wrote it while reading an
     untrusted body) — it is NOT trusted just because it is short. It is re-run through the SAME
     `ingest_gate.gate()`; a gist the gate FLAGS is WITHHELD (replaced with a neutral placeholder) and
     its guess forced to None, so the human must open the chat rather than trust a poisoned summary.
  3. WRITE scan_summary/scan_guess via pipeline.set_scan (which refuses an already-closed chat).

The MAIN session never reads the raw reader output — it reads only THIS tool's sanitized summary line.
That keeps the reader-actor wall intact even though SCAN now flows a slice of EVERY chat through readers.

Usage:
  python3 scan_collect.py --map <corpus-map.json> --raw <dir-of-raw-reader-outputs> [--desk cowork-ingest]
"""
import argparse, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import pipeline
from tag import extract_json_array   # robust JSON-array pull (handles prose preamble / fences)

# the frozen on-path gate (shared/tools/ingest_gate.py) — CODE_ROOT is 4 dirs up from here
CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
_SHARED = os.path.join(CODE_ROOT, "shared", "tools")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
from ingest_gate import gate  # noqa: E402

VERBS = {"toss", "research", "park"}
WITHHELD = "[gist withheld — flagged by the injection gate; open the chat to rule]"
# THE DETAIL FLOOR — TIERED by the machine's guess (found 2026-07-11 on a live mixed basket): a KEEPER
# (`research`) feeds the deep read, so it must be meaty (3 sentences); a `toss`/`park` is junk/one-off and
# is NATURALLY brief — forcing 3 sentences on it just bounces it and re-reads junk (a wasteful loop). So
# junk only needs 2 sentences to be rulable. A too-short gist is still a reader miss: we DON'T store it,
# the chat stays un-scanned, and the next pass re-summarizes it.
MIN_SENTENCES_RESEARCH = 3
MIN_SENTENCES_OTHER = 2      # toss / park / no-guess — enough to rule on, not a wasteful 3-sentence demand
MIN_CHARS_RESEARCH = 100
MIN_CHARS_OTHER = 60
STORE_CAP = 900              # so a genuine 3–4 sentence keeper is stored whole (prompt targets ~60 words)


def _too_short(g, guess=None):
    enders = g.count(".") + g.count("!") + g.count("?")
    if guess == "research":
        return len(g) < MIN_CHARS_RESEARCH or enders < MIN_SENTENCES_RESEARCH
    return len(g) < MIN_CHARS_OTHER or enders < MIN_SENTENCES_OTHER


def _store_trim(g, cap=STORE_CAP):
    """Trim to <=cap WITHOUT clipping mid-sentence: cut back to the last sentence-end at/under the cap.
    Only ever runs on a gist that ALREADY passed the floor, so we never turn a good gist into a reject."""
    if len(g) <= cap:
        return g
    window = g[:cap]
    cut = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
    return window[:cut + 1].rstrip() if cut > 0 else window.rstrip()


def _measure_chars(flat_dir, f):
    """Character length of the FLATTENED body, MEASURED from disk — never guessed, never asked of a reader.

    A reader only ever sees a gate-sanitized SLICE, so it structurally cannot know the true size; asking it
    would produce a confident wrong number. The file on disk is the only honest source. Returns None if the
    flat dir wasn't supplied or the file isn't there, and the ruling screen then simply omits the size
    rather than inventing one. (2026-08-05, SPEC.md §8 step 2.6.)"""
    if not flat_dir:
        return None
    p = os.path.join(flat_dir, f)
    try:
        return len(open(p, errors="replace").read())
    except OSError:
        return None


def collect(m, raw_dir, desk="cowork-ingest", flat_dir=None):
    """Returns a stats dict; mutates m in place (caller saves)."""
    files = sorted(glob.glob(os.path.join(raw_dir, "*")))
    wrote = withheld = dropped_guess = skipped = too_short = 0
    rows = pipeline.rows_of(m)
    for fp in files:
        if not os.path.isfile(fp):
            continue
        for r in extract_json_array(open(fp, errors="replace").read()):
            if not isinstance(r, dict):
                continue
            f = r.get("file")
            if f and not str(f).endswith(".txt"):
                f = str(f) + ".txt"
            if not f or f not in rows:
                skipped += 1
                continue
            raw_guess = r.get("guess")
            guess = raw_guess if raw_guess in VERBS else None
            if raw_guess and guess is None:
                dropped_guess += 1
            gist = (r.get("gist") or r.get("summary") or "").strip()
            withheld_this = False
            if gist:
                res = gate(desk, "file", gist, item=f)   # SECOND gate pass — the gist is untrusted too
                if not res.get("passed"):
                    gist, guess, withheld_this = WITHHELD, None, True
                    withheld += 1
                else:
                    gist = (res.get("content") or "").strip()   # FULL sanitized gist — do NOT truncate yet
            # DETAIL FLOOR (TIERED by guess) checked on the FULL gist, BEFORE any trim — so a genuine
            # keeper summary is never falsely rejected by clipping, and a brief junk summary isn't bounced
            # for lacking a needless 3rd sentence.
            if not withheld_this and _too_short(gist, guess):
                too_short += 1
                continue
            if not withheld_this:
                gist = _store_trim(gist)   # store whole if <=cap; else cut back to a sentence boundary
            ok, _msg = pipeline.set_scan(m, f, guess=guess, summary=gist,
                                         chars=_measure_chars(flat_dir, f))
            if ok:
                wrote += 1
            else:
                skipped += 1
    return {"wrote": wrote, "withheld": withheld, "dropped_guess": dropped_guess,
            "skipped": skipped, "too_short": too_short, "raw_files": len(files)}


def main():
    ap = argparse.ArgumentParser(description="SCAN collector — validate guess + gate gist + write map")
    ap.add_argument("--map", required=True)
    ap.add_argument("--raw", required=True, help="dir of raw scan-reader outputs (one JSON array each)")
    ap.add_argument("--desk", default="cowork-ingest")
    ap.add_argument("--flat", default=os.path.expanduser("~/.cache/cowork-ingest/flatten"),
                    help="flattened-corpus dir; the chat's char length is MEASURED from here for the "
                         "ruling screen. Omit/point elsewhere and the size is simply not shown.")
    a = ap.parse_args()
    m = pipeline.load(a.map)
    st = collect(m, a.raw, a.desk, flat_dir=a.flat)
    pipeline._save(m, a.map)
    print(f"OK scan-collect: wrote {st['wrote']} gists from {st['raw_files']} reader file(s) — "
          f"{st['withheld']} withheld by the gate, {st['too_short']} rejected as too short (stay un-scanned "
          f"→ re-run to retry), {st['dropped_guess']} out-of-vocab guesses dropped, "
          f"{st['skipped']} unknown-file/closed skipped → {a.map}")


if __name__ == "__main__":
    main()
