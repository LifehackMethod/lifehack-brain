#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: The debt list GREW +29 items over 4 days (2026-06-14..18) because "closing" an item
#      annotated it "✅ RESOLVED" IN PLACE in the live ## Open list instead of removing it — so
#      the list only ever accumulated. The 2026-06-18 debt-knockout drain made the ledger's
#      ## Open section DELETION-ONLY; this guard enforces that structurally so the growth pattern
#      cannot recur (Priya pre-mortem FATAL #1: the drain must be DETERMINISTIC, not LLM-remembered).
# GUARDS: a Write/Edit to state/debt-ledger.md that ADDS a status-annotation line (✅ / RESOLVED /
#      CLEARED / FIXED) to the ## Open section. The only legal change to ## Open is DELETION of a line.
# REDIRECT: to close an item, DELETE its line from ## Open. If it warrants a history note, add a
#      ONE-LINE dated entry under ## Cleared instead. See the state/debt-ledger.md header.
# UPDATED: 2026-06-18 (ported 2026-08-13 from claudeops-config — verbatim; the ledger path is
#      already matched as a relative suffix, so no path resolution work was needed)
# SCOPING NOTE: this fires on ALL Write|Edit but guards ONLY debt-ledger.md. On any parse failure
#      or non-ledger target it exits 0 (allow) — a bug here must NEVER block the whole edit surface;
#      it can only ever miss a ledger check (the Health Authority + human still backstop that).
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
INPUT=$(cat)
export CLAUDEOPS_LEDGER_HOOK_INPUT="$INPUT"
python3 <<'PY'
import os, json, re, sys
try:
    data = json.loads(os.environ.get("CLAUDEOPS_LEDGER_HOOK_INPUT", ""))
except Exception:
    sys.exit(0)
ti = (data.get("tool_input") or {})
path = (ti.get("file_path") or ti.get("path") or "").replace("\\", "/")
if not path.endswith("state/debt-ledger.md"):
    sys.exit(0)                          # only the canonical ledger is guarded
try:
    cur = open(path, encoding="utf-8").read()
except Exception:
    cur = ""
if ti.get("content") is not None:        # Write (full overwrite)
    new = ti["content"]
elif "new_string" in ti:                 # Edit
    o, n = ti.get("old_string", ""), ti.get("new_string", "")
    new = cur.replace(o, n) if ti.get("replace_all") else cur.replace(o, n, 1)
else:
    sys.exit(0)
FORBIDDEN = re.compile(r"✅|\b(RESOLVED|CLEARED|FIXED)\b")
def open_section(text):
    lines, start = text.splitlines(), None
    for i, ln in enumerate(lines):
        if ln.strip() == "## Open" or ln.strip().startswith("## Open "):
            start = i + 1; break
    if start is None:
        return []
    out = []
    for ln in lines[start:]:
        if ln.startswith("## "):
            break
        out.append(ln)
    return out
def count(text):
    return sum(1 for ln in open_section(text) if FORBIDDEN.search(ln))
if count(new) > count(cur):
    deny = ('{"decision":"block","reason":"BLOCKED: this edit ADDS a status-annotation '
            '(✅/RESOLVED/CLEARED/FIXED) line to the ## Open section of state/debt-ledger.md. '
            'WHY: annotate-in-place is exactly what made the debt list GROW +29 in 4 days — '
            'the ## Open section is DELETION-ONLY (2026-06-18 drain). REDIRECT: to close an item, '
            'DELETE its line from ## Open; if it needs a history note, add a one-line dated entry '
            'under ## Cleared instead."}')
    print(deny, file=sys.stderr)
    sys.exit(2)
sys.exit(0)
PY
