"""journal_note.py -- hand a hook's decision JSON to the fire journal (lib/journal.sh), so an ASK is journaled as "ask".

WHY: the journal runs in the hook's EXIT trap and sees only the exit code. An ask hook exits 0, so every ask was
     journaled as "allow" (15,413 rows, not one ask, 2026-11-02). The trap cannot read the hook's stdout (it already
     went to the harness), so the emitter leaves a copy of the exact JSON it printed in $LHB_JOURNAL_NOTE, a per-process
     file journal.sh exports when it is sourced. The trap parses that copy and deletes it.
USE: print(s) FIRST, exactly as before, then note(s). Calling this can never change the hook: no output, no exception,
     no exit code. A missing variable or an unwritable folder just means the journal records "allow" as before.
SIGNPOST: system/hooks/lib/journal.sh (lhb_journal_fire, "decision"); tests: system/hooks/tests/test_fire_journal_decision.sh.
"""
import os


def note(text):
    try:
        p = os.environ.get("LHB_JOURNAL_NOTE", "")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(text if isinstance(text, str) else str(text))
    except Exception:  # allow-silence: fire-journal observer only, a failed note must never change the hook
        pass
