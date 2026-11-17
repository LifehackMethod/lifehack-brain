#!/usr/bin/env python3
# retiring: kept only for gc-daily's proposals until Phase 5
"""run.py: the engine. Steps talk only through the memory (kg_*), in order gather -> score -> stitch -> rank -> gaps.
Each step replaces its own earlier output, so two runs in a row leave the same picture. One transaction for the lot.
Retiring: kept only for gc-daily's proposals until Phase 5.

  python3 run.py [--db PATH] [--json]
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import gather  # noqa: E402  (static imports so the engine's steps are visibly wired; order is the STEPS order)
import gaps  # noqa: E402
import rank  # noqa: E402
import score  # noqa: E402
import stitch  # noqa: E402

STEPS = (("gather", gather), ("score", score), ("stitch", stitch), ("rank", rank), ("gaps", gaps))


def run_con(con):
    """Run every step on a connection the store handed in. Returns the merged counts dict."""
    out = {}
    for name, mod in STEPS:
        out[name] = mod.run(con)
    return out


def summary_line(res):
    g, c, s, k, p = res["gather"], res["score"], res["stitch"], res["rank"], res["gaps"]
    return ("engine: %d item(s) in window (%s); %d episode(s); %d ranked (%d pinned, %d quiet, %d demoted); %d gap(s) (%d dismissed)" % (
        g["window_items"], ", ".join("%s %d" % kv for kv in sorted(g["by_kind"].items())) or "none", s["episodes"], k["ranked"],
        k["pinned"], k["quiet"], k["demoted"], p["gaps_kept"], p["gaps_dismissed"]))


def run(con=None):
    """Run the engine; con=None goes through the store wrapper (one transaction). Returns the counts dict."""
    if con is None:
        import store
        return store.engine_run()
    return run_con(con)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="use another database file (default: the live rig.db)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    import store
    if a.db:
        store.set_path(a.db)
    res = run()
    print(json.dumps(res, sort_keys=True) if a.json else summary_line(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
