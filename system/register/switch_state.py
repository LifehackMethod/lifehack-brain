#!/usr/bin/env python3
"""switch_state.py — the register-backed guard switch's SEMANTICS, as one tiny
module (Feature S1/K1, enforcement-layer Phase 2 plan, 2026-09-16).

Enver's stamped binding constraint (system/journal.md, 2026-09-16): the hook-edit
protection's switch STATE and EXPIRY live IN THE REGISTER as data — otherwise the
on-commit drift gate reads the guard-rebuild lane's local flip as drift and
refuses their legitimate commits. This module exists so `generate.py` (which emits
the wiring) and `harvest.py` (which preserves declarations across re-harvests)
classify a hook row's switch state THE SAME WAY, with one test seam. The guard
itself (bash) carries a behavioral equivalent inline — it runs inside plugin
contexts that cannot import from here cheaply.

The whole feature in three lines:

    state="active" (the DEFAULT — every student)   -> emitted normally (ON)
    state="suspended", expiry >= today  -> HONORED: omitted from generated wiring
                                           (OFF, declared, temporary)
    state="suspended", expiry <  today  -> EXPIRED: emitted as ACTIVE again
                                           (self-heal ON) and alarmed loudly

Edge: expiry == today is still honored; the suspension lapses the day AFTER.
`expiry` shape/reality is enforced upstream by validate_register.py (generate.py's
schema gate runs before this is ever called); classify() still fails SAFE
("active") on any unparseable input, because protection ON is never the dangerous
default.

`today` is date.today() unless $LHB_REGISTER_TODAY=YYYY-MM-DD overrides it — the
deterministic seam the K1 test fleet uses; production runs never set it.
"""
import os
from datetime import date

EXPIRY_ENV = "LHB_REGISTER_TODAY"


def resolve_today(env=None):
    """Today's date, honoring the $LHB_REGISTER_TODAY test override (YYYY-MM-DD)."""
    env = os.environ if env is None else env
    raw = env.get(EXPIRY_ENV)
    if raw:
        return date.fromisoformat(raw.strip())
    return date.today()


def classify(row, today=None):
    """One of "active" | "honored" | "expired" for a register row.

    "active"   — emit the row into generated wiring (the default; also every
                 non-hook row, every row without the switch fields, and any
                 malformed suspension — fail SAFE).
    "honored"  — a declared, unexpired suspension: OMIT from generated wiring.
    "expired"  — a suspension whose expiry has passed: emit as ACTIVE (self-heal)
                 and ALARM loudly (the caller's job to print, not this function's).
    """
    today = resolve_today() if today is None else today
    if row.get("type") != "hook":
        return "active"
    if row.get("state") != "suspended":
        return "active"
    expiry = row.get("expiry")
    if not expiry:
        # validate_register.py refuses this combination before generate.py ever
        # sees it; a caller that bypassed the schema gate still fails SAFE.
        return "active"
    try:
        expiry_date = date.fromisoformat(expiry)
    except (ValueError, TypeError):
        return "active"  # unparseable -> protection ON, never a silent lift
    return "honored" if expiry_date >= today else "expired"
