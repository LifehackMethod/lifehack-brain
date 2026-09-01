#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Capability-boundary violations (e.g. a read-only desk firing a write it
#      shouldn't, or one desk's session touching another desk's calendar) were
#      undetectable — there was no audit trail of which tool calls ran in which
#      desk. This hook records one compact line per tool call so boundary
#      breaches can be caught after the fact, and so gws commands carry a full
#      audit string.
# GUARDS: n/a — this is an observability hook, not a guard. It NEVER blocks
#      (PostToolUse cannot block) and NEVER writes to the notes root on the hot path.
# REDIRECT: Buffer is /tmp/lifehack-observability-buffer.jsonl. `session_flight_recorder.sh`
#      (a Stop hook) flushes it to `<notes root>/system/observability/YYYY-MM-DD.jsonl` at
#      session end, resolved through `shared/brain_root.py` — see that hook for the exact
#      path. ⚠ CORRECTED 2026-08-15 (T9.7d): this used to deny the repo had any scheduler at all —
#      that's false (`system/tools/pulse.sh` is the live daemon), but no pruning job is registered for these logs in
#      `system/pulse-config.md`, so nothing prunes them automatically today; trim
#      `<notes root>/system/observability/` by hand if it grows large.
#      If lines are missing, check this hook is registered under PostToolUse with
#      command: bash "${CLAUDE_PROJECT_DIR}/system/hooks/observability_logger.sh".
# UPDATED: 2026-05-30 (ported; buffer/flush paths adapted — see REDIRECT above)
# ─────────────────────────────────────────────────────────────────────────────
# observability_logger.sh — PostToolUse hook (matcher: * / all tools)
# Appends ONE compact JSON line per tool call to a /tmp buffer. Buffer only —
# never writes to the notes root on the hot path (avoids per-call sync latency).
# Always exits 0.

BUFFER="/tmp/lifehack-observability-buffer.jsonl"
ARGS="$(cat)"

# Defensive: empty input → exit 0, write nothing.
if [ -z "$ARGS" ]; then
  exit 0
fi

# WINDOWS FOLD: resolved once here, by $0's own directory (same GUARD_LIB convention
# guard_gmail_send.sh uses for lib/gws_guard.py), and handed to the python -c string below via
# the environment (it is single-quoted, so bash does no substitution inside it).
_OBS_LIB="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/lib/winpath_fold.py"

# All parsing in Python with a blanket try/except so malformed/garbage input
# never crashes the hook. On any failure: print nothing, exit 0.
printf '%s' "$ARGS" | OBS_WINFOLD_LIB="$_OBS_LIB" python3 -c '
import sys, json, os, datetime

def out_nothing():
    sys.exit(0)

try:
    raw = sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        out_nothing()
except Exception:
    out_nothing()

tool = data.get("tool_name", "") or ""
session = data.get("session_id", "") or "unknown"
cwd = data.get("cwd", "") or ""

# WINDOWS FOLD: cwd arrives backslash-native on Windows, so a bare "/desks/" substring test
# never matches there and every Windows call gets misfiled as desk "root", silently. Fold a
# COMPARISON copy to find the marker; the DESK NAME itself is sliced out of the ORIGINAL cwd (by
# matching LENGTH, not by re-splitting the folded copy) so the real desk name casing is never
# lowercased into the log. Degrade-safe, not fail-closed: this is a PostToolUse hook and this
# this repo header above says it NEVER blocks -- on a missing helper it falls back to the
# pre-fix (unfolded) comparison rather than trying to block a write that already happened, and
# flags the line itself so the degradation is visible in the log instead of silent.
_fold_degraded = False
try:
    import importlib.util
    _obs_lib = os.environ.get("OBS_WINFOLD_LIB", "")
    _obs_spec = importlib.util.spec_from_file_location("winpath_fold", _obs_lib)
    _obs_wf = importlib.util.module_from_spec(_obs_spec)
    _obs_spec.loader.exec_module(_obs_wf)
    cwd_cmp = _obs_wf.winfold(cwd)
except Exception:
    cwd_cmp = cwd
    _fold_degraded = True

desk = "root"
marker = "/desks/"
idx = cwd_cmp.find(marker)
if idx != -1:
    rest_cmp = cwd_cmp[idx + len(marker):]
    seg_len = len(rest_cmp.split("/", 1)[0])
    seg = cwd[idx + len(marker):idx + len(marker) + seg_len]
    if seg:
        desk = seg

ts = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

line = {
    "ts": ts,
    "tool": tool,
    "desk": desk,
    "session": session,
    "status": "ok",
}
if _fold_degraded:
    # Visible, non-blocking: the desk above was computed WITHOUT the Windows fold, so on a real
    # Windows backslash-native cwd it may read "root" when it should not have.
    line["fold_degraded"] = True

# SPECIAL CASE: Bash + command contains "gws" → capture full gws command string
# (capability-boundary audit trail), plus exit code best-effort.
tool_input = data.get("tool_input", {})
if not isinstance(tool_input, dict):
    tool_input = {}
command = tool_input.get("command", "")
if not isinstance(command, str):
    command = ""

if tool == "Bash" and "gws" in command:
    line["gws_command"] = command
    # Best-effort exit code from the tool response, if the payload exposes one.
    resp = data.get("tool_response", {})
    if not isinstance(resp, dict):
        resp = {}
    exit_code = None
    for key in ("exit_code", "exitCode", "returnCode", "code"):
        if key in resp and isinstance(resp[key], (int,)):
            exit_code = resp[key]
            break
    if exit_code is not None:
        line["gws_exit"] = exit_code

sys.stdout.write(json.dumps(line, separators=(",", ":")) + "\n")
' >> "$BUFFER" 2>/dev/null

exit 0
