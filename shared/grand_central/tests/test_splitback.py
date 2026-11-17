#!/usr/bin/env python3
"""test_splitback.py — regression test for the 'gate split-back failed' bug (plan task 1.5b).

The old lane joined fields with a fixed '\\n---\\n' separator. FIELD-mode sanitize flattens
'\\n---\\n' AND any '---' inside a field value to the same ' --- ', so a task whose notes
contained '---' (and newlines) split into unattributable chunks, parse_gate_content returned None,
and 3 real tasks were wrongly quarantined. The fix: a random per-call separator token.

Run: python3 tests/test_splitback.py   → exit 0 on pass.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RIG = os.path.dirname(_HERE)
sys.path.insert(0, _RIG)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "system", "tools"))
os.environ.setdefault("RIG_HANDOFF_DIR", __import__("tempfile").mkdtemp(prefix="rig-handoff-test-"))  # never the live handoff dir

import pull  # noqa: E402  (join_fields / split_fields; module import has no side effects)
import sanitize  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


# The note text that broke the old lane: contains '---' on its own line and mid-line, plus newlines.
NOTES = ("Call the venue first\n---\nthen email the caterer. Budget is flexible --- ask about "
         "the off-season rate.\nIf Friday fails, try\nthe following week.")

# What the gate hands back on a NONE/BENIGN verdict: the body through FIELD-mode sanitize.
def gate_content_sim(body):
    return sanitize.sanitize(body, max_len=sanitize.NO_CAP)


print("test_splitback.py")
print("=" * 60)

# 1. Round-trip: multi-field item incl. the killer notes value.
fields = {"title": "Prep materials", "notes": NOTES, "status": ""}
body, token = pull.join_fields(fields)
content = gate_content_sim(body)
cleared = pull.split_fields(content, token, fields)
check("round-trip with '---' and newlines in a value", cleared is not None)
if cleared:
    check("title survives verbatim", cleared["title"] == fields["title"],
          repr(cleared.get("title")))
    check("notes survive (whitespace-flattened, content intact)",
          cleared["notes"] == sanitize.sanitize(NOTES, max_len=sanitize.NO_CAP),
          repr(cleared.get("notes")))
    check("empty-going-in fields come back empty", cleared["status"] == "")

# 2. The OLD separator would have failed here — prove the failure mode existed: splitting the
#    old-style body on the old '\s*---\s*' regex yields a chunk that is not a FIELD header.
import re as _re
old_body = "\n---\n".join(f"FIELD {n}: {v}" for n, v in fields.items() if v)
old_content = gate_content_sim(old_body)
old_chunks = [c for c in _re.split(r"\s*---\s*", old_content) if c.strip()]
bad_chunks = [c for c in old_chunks if not pull.FIELD_PREFIX.match(c.strip())]
check("old fixed separator provably breaks on '---' values (negative control)",
      bool(bad_chunks), f"old parser saw {len(old_chunks)} chunks, {len(bad_chunks)} malformed")

# 3. A chunk that doesn't start with FIELD → None (fallback to per-field, never silent corruption).
content, token = pull.join_fields({"notes": NOTES})
content = gate_content_sim(content) + " @@nonexistent-token@@ stray chunk"
# split on a token that IS present but a chunk is malformed:
bad, tok2 = pull.join_fields(fields)
malformed = gate_content_sim(bad) + f"@@{tok2}@@this chunk has no FIELD prefix"
check("malformed chunk → split returns None (conservative)",
      pull.split_fields(malformed, tok2, fields) is None)

# 4. Duplicate field chunk → None.
dup = gate_content_sim(bad) + f"@@{tok2}@@FIELD notes: injected"
check("duplicated field name → split returns None",
      pull.split_fields(dup, tok2, fields) is None)

# 5. Tokens are per-call random: two calls never share a separator.
_b2, tok3 = pull.join_fields(fields)
check("separator token is per-call random", tok2 != tok3 and tok2 != token)

print("=" * 60)
if FAILURES:
    print(f"FAILED: {len(FAILURES)} check(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("ALL PASS")
sys.exit(0)
