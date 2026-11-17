"""score.py: step 2. Discovers signals/*.py (NAME, VERSION, compute(con, item_ids)), clears each signal's
old rows and writes kg_scores (subject_ref 'item:<id>', signal NAME) for the email items in the window."""
import importlib
import os
import pkgutil

import common as C
import store_graph as sg
from signals import first_seen_sender  # noqa: E402
from signals import long_quiet_returns  # noqa: E402
from signals import on_calendar_14d  # noqa: E402
from signals import sender_history  # noqa: E402
from signals import to_vs_cc  # noqa: E402

# The five signals named outright, so the wiring is visible; discover() still finds signals/*.py by itself
# (a sixth dropped in signals/ is picked up with no edit here; tests/test_score_signals.py keeps the two lists equal).
EXPLICIT = (first_seen_sender, long_quiet_returns, on_calendar_14d, sender_history, to_vs_cc)

SIGNALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals")


def discover():
    mods = []
    for m in sorted(pkgutil.iter_modules([SIGNALS_DIR]), key=lambda x: x.name):
        mod = importlib.import_module("signals." + m.name)
        if hasattr(mod, "NAME") and hasattr(mod, "compute"):
            mods.append(mod)
    return mods


def run(con):
    ids = C.window_ids(con)
    items = C.load_items(con, ids)
    email_ids = [i for i in ids if items.get(i, {}).get("kind") == "email"]
    counts = {}
    for mod in discover():
        sg.clear_scores(con, mod.NAME)
        res = mod.compute(con, email_ids)
        for iid in sorted(res):
            v, reason = res[iid]
            sg.set_score(con, "item:%d" % iid, mod.NAME, mod.VERSION, float(v), reason)
        counts[mod.NAME] = len(res)
    return {"signals": counts}
