#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: This system had no structured feedback signal. The user's quality judgments
#      ("8 - great", "2 - wrong") evaporated with the conversation. No way to
#      learn from rated outcomes over time.
# GUARDS: Nothing — UserPromptSubmit observer. Never blocks a prompt. Detects an
#         explicit 1-10 rating at the start of a message and logs it.
# REDIRECT: N/A (non-blocking). Signal log and low-rating failure captures live under
#      the notes root resolved through `shared/brain_root.py` — `<notes root>/system/
#      learnings-signals.jsonl` and `<notes root>/system/learnings/`. If no notes root
#      is set yet, this hook skips both writes rather than guessing a location — set
#      one with `python3 shared/brain_root.py --set <path>`.
# UPDATED: 2026-05-30 (ported; DRIVE resolution replaced with brain_root.py)
# ─────────────────────────────────────────────────────────────────────────────
# rating_capture.sh — UserPromptSubmit hook
# Captures explicit 1-10 ratings; low ratings (<=3) also produce a failure file.

REPO="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
ROOT=""
if [ -n "$REPO" ] && [ -f "$REPO/shared/brain_root.py" ]; then
  ROOT="$(python3 "$REPO/shared/brain_root.py" --quiet 2>/dev/null)"
fi
# NOT-SET is a real, expected state — skip silently rather than guess a path. This is a
# UserPromptSubmit observer; it must never block the prompt either way.
if [ -z "$ROOT" ]; then
  exit 0
fi
SIGNALS="$ROOT/system/learnings-signals.jsonl"
LEARN_DIR="$ROOT/system/learnings"

INPUT="$(cat 2>/dev/null)"

SIGNALS="$SIGNALS" LEARN_DIR="$LEARN_DIR" python3 - "$INPUT" <<'PY'
import sys, os, json, re, datetime

raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

prompt = (data.get("prompt") or "").strip()
session = data.get("session_id") or "unknown"
transcript = data.get("transcript_path") or ""

# A rating is a 1-10 number at the very start, then either:
#   - a separator (- – — : .) optionally spaced, followed by a comment, OR
#   - the "/10" form, OR
#   - the number alone (whole message).
# "3 items to fix" is rejected: digit followed by a word, no separator.
m_slash = re.match(r'^(10|[1-9])\s*/\s*10\b\s*(.*)$', prompt, re.S)         # N/10 [comment]
m_sep   = re.match(r'^(10|[1-9])\s*[-–—:.]\s*(.+)$', prompt, re.S)          # N - comment
m_bare  = re.match(r'^(10|[1-9])\s*$', prompt)                             # bare number

rating = None
comment = ""
if m_slash:
    rating = int(m_slash.group(1)); comment = m_slash.group(2).strip()
elif m_sep:
    rating = int(m_sep.group(1)); comment = m_sep.group(2).strip()
elif m_bare:
    rating = int(m_bare.group(1))

if rating is None:
    sys.exit(0)  # not a rating — pass through silently

ts = datetime.datetime.now().isoformat(timespec="seconds")
entry = {"ts": ts, "rating": rating, "comment": comment, "session": session}

signals = os.environ["SIGNALS"]
learn_dir = os.environ["LEARN_DIR"]
os.makedirs(os.path.dirname(signals), exist_ok=True)
with open(signals, "a") as f:
    f.write(json.dumps(entry) + "\n")

# Low rating → write a failure capture file for later review / distill.
if rating <= 3:
    os.makedirs(learn_dir, exist_ok=True)
    safe = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    path = os.path.join(learn_dir, f"{safe}-low-rating-{rating}.md")
    with open(path, "w") as f:
        f.write(f"""---
type: failure-capture
rating: {rating}
session: {session}
ts: {ts}
---

# Low rating ({rating}/10)

**User comment:** {comment or "(none)"}

**Transcript:** {transcript or "(not provided)"}

**Why this matters:** A rating <= 3 marks an output the user judged wrong or
poor. Review the transcript above, identify the FRICTION/CORRECTION, and if it
generalizes, promote a fix via /save into system/learnings.md.
""")
    sys.stderr.write(f"[rating_capture] {rating}/10 logged + failure file written: {os.path.basename(path)}\n")
else:
    sys.stderr.write(f"[rating_capture] {rating}/10 logged to learnings-signals.jsonl\n")
sys.exit(0)
PY
exit 0
