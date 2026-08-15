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
#      path. This repo has no scheduler, so nothing prunes old observability logs
#      automatically; trim `<notes root>/system/observability/` by hand if it grows large.
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

# All parsing in Python with a blanket try/except so malformed/garbage input
# never crashes the hook. On any failure: print nothing, exit 0.
printf '%s' "$ARGS" | python3 -c '
import sys, json, datetime

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

# Derive desk from cwd: .../desks/<desk>/...  else "root".
desk = "root"
marker = "/desks/"
idx = cwd.find(marker)
if idx != -1:
    rest = cwd[idx + len(marker):]
    seg = rest.split("/", 1)[0]
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
