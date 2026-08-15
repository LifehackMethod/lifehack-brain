# PASS 0 — PREFLIGHT (which layer runs today)

TRIPWIRE: this pass makes exactly one decision — **Layer 1 alone, or Layer 1 + Layer 2** — and says
which, out loud, before anything else runs. Never skip it and never assume from a prior session; a
person can disconnect Google, run this on a second machine, or open this for the very first time.

Cal ships in two layers. **Layer 1** — diary, daily planning as a conversation, open loops — needs
nothing but this folder and works the first time it is ever opened, no account anywhere. **Layer 2** —
calendar reads, task writes — needs the person's own Google connected. This pass finds out which is
true today, honestly: it never guesses, and it never silently assumes either one.

## Do this

1. **Resolve the notes folder.** `python3 "$ROOT/shared/brain_root.py" --quiet`. If this is NOT-SET,
   stop and say so plainly in one line — nothing below has anywhere to write yet. (A normal setup run
   already does this; a bare clone opened for the first time may not have.)

2. **Check for Google — read-only. Never attempt a login, never touch stored credentials.**
   ```bash
   HAVE_GWS=0; command -v gws >/dev/null 2>&1 && HAVE_GWS=1
   AUTHED=0
   if [ "$HAVE_GWS" = 1 ]; then gws auth status >/dev/null 2>&1 && AUTHED=1; fi
   echo "gws on PATH: $HAVE_GWS   authenticated: $AUTHED"
   python3 "$ROOT/shared/cal_config.py"
   ```
   The last line prints all four identifiers `cal_config.py` knows about, each `set` or `— not set`.
   Every one of these is a read; nothing here changes anything on disk or in any account.

3. **Decide, and say which layer runs — in one line, before the first question.**
   - `gws` missing, OR not authenticated, OR **any** of the four `cal.md` identifiers not set →
     **LAYER 1 ONLY today.** Name what's missing specifically (which identifiers, or "Google isn't
     connected") rather than a vague "not configured." Then move straight into Layer 1 — do not stall
     on the gap, do not make them go fix it before they can plan their day.
   - `gws` present + authenticated + all four identifiers on file → **LAYER 1 + LAYER 2.** Say so in
     one line and proceed to the full trust-fall.
   - ⛔ **A half-configured reading is still Layer 1 only.** `cal_config.py` refuses per missing key,
     not per file — three of four identifiers set is not "close enough." Never round up to Layer 2.

## NEXT
- Layer 1 only → load and follow `prompts/l1-lookback.md`.
- Layer 1 + Layer 2 → load and follow `prompts/00-lookback.md` (the full trust-fall — unchanged below
  this point, except its Pass 0 no longer assumes a cron ran; see the note at its top).
