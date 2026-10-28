"""model_ids.py — Python's read of the ONE model table (system/tools/model.lib.sh, plan §B.4 / 5.3).

WHY: models are named in one place. A hard-coded id rots silently: the intake reader still asked for a
retired haiku-4-5 id, so every headless judge call exited 1 and the email danger path could never
fire (found by the 5.4 danger drill, 2026-10-28). Python callers ask for a TIER, never an id.
"""
import os
import re

_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "system", "tools", "model.lib.sh")
_FALLBACK = {"small": "claude-haiku-5-5", "medium": "claude-sonnet-5-5", "large": "claude-opus-5-5"}


def model_id(tier):
    """small | medium | large → the id in model.lib.sh (fallback only if the table can't be read)."""
    tier = tier.lower()
    try:
        with open(_LIB) as f:
            m = re.search(r'^MODEL_ID_%s="([^"]+)"' % tier.upper(), f.read(), re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    return _FALLBACK[tier]
