#!/usr/bin/env bash
# model.lib.sh — THE one place a scheduled job calls a model (self-monitoring plan 5.3, B.4).
#
# WHY: a job that calls a model needs the same guardrails every time — which model, the token, a
# timeout, a check that the reply is not empty, a count of calls (cost), and a tripwire when a job
# calls far more than its row says it should. Each desk copying those is how they drift (the layer
# law: shared = fetch, auth, timeout, output check, cost). A row says `small | medium | large`;
# this file is the ONLY place that turns a tier into a model id.
#
# USAGE (from a job command run by job-run.sh):
#   . "$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh"
#   run_model <tier> <prompt-file> <out-file> [marker] || exit 1
# RETURNS 0 ok. 1 failed (reason printed; also written for job-run.sh to name in last-run).
#   Failure reasons: "empty model output" · "model output missing marker" · "model call timed out"
#   · "over budget: <n> calls > <budget>" · "unknown model tier" · "model call failed (rc=<n>)".
# job-run.sh provides (all optional outside it): JOB_RUN_CALLS_FILE (one "<tier> <secs>" line per call,
#   appended here), JOB_RUN_BUDGET (max calls this run; the tripwire), and reads $JOB_RUN_CALLS_FILE.fail
#   (this library writes the failure reason there so a job that swallows the return code still fails).
# ENV: MODEL_TIMEOUT (seconds per call, default 600). LIFEHACK_MODEL_STUB=<script> (TEST-ONLY, inert
#   when unset): called as `<script> <model-id> <prompt-file> <out-file>` instead of `claude`.
# ⛔ NO `set` LINE: sourced into callers with different option sets. The token is never printed.

# ── THE tier table. The ONLY place model ids live. ──
MODEL_ID_SMALL="claude-haiku-5-5"
MODEL_ID_MEDIUM="claude-sonnet-5-5"
MODEL_ID_LARGE="claude-opus-5-5"

_MODEL_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$_MODEL_LIB_DIR/claude-auth.lib.sh" || { echo "FATAL: cannot source claude-auth.lib.sh"; return 1 2>/dev/null; }

model_id_for_tier() {
  case "${1:-}" in
    small) printf '%s' "$MODEL_ID_SMALL" ;;
    medium) printf '%s' "$MODEL_ID_MEDIUM" ;;
    large) printf '%s' "$MODEL_ID_LARGE" ;;
    *) return 1 ;;
  esac
}

_model_fail() {   # _model_fail <reason> — print it, leave it for job-run.sh, return 1
  echo "[run_model] FAILED: $1"
  [ -n "${JOB_RUN_CALLS_FILE:-}" ] && printf '%s\n' "$1" > "${JOB_RUN_CALLS_FILE}.fail"
  return 1
}

run_model() {
  local tier="${1:-}" prompt="${2:-}" out="${3:-}" marker="${4:-}" id n budget secs t0 rc cpid wpid
  id="$(model_id_for_tier "$tier")" || { _model_fail "unknown model tier '$tier' (want small|medium|large)"; return 1; }
  [ -r "$prompt" ] || { _model_fail "prompt file unreadable: $prompt"; return 1; }
  [ -n "$out" ] || { _model_fail "no out-file given"; return 1; }

  # BUDGET tripwire: a call that would exceed the row's budget refuses to run.
  if [ -n "${JOB_RUN_BUDGET+x}" ]; then
    budget="$JOB_RUN_BUDGET"
    n=0; [ -n "${JOB_RUN_CALLS_FILE:-}" ] && [ -f "$JOB_RUN_CALLS_FILE" ] && n="$(wc -l < "$JOB_RUN_CALLS_FILE" | tr -d ' ')"
    n=$((n + 1))
    case "$budget" in ''|*[!0-9]*) _model_fail "over budget: $n calls > '$budget' (budget is not a number)"; return 1 ;; esac
    if [ "$n" -gt "$budget" ]; then _model_fail "over budget: $n calls > $budget"; return 1; fi
  fi

  rm -f "$out.timeout"
  : > "$out" 2>/dev/null || { _model_fail "cannot write out-file: $out"; return 1; }
  t0="$(date +%s)"
  if [ -n "${LIFEHACK_MODEL_STUB:-}" ]; then
    bash "$LIFEHACK_MODEL_STUB" "$id" "$prompt" "$out" > /dev/null &
    cpid=$!
  else
    require_claude_token "run_model" || { _model_fail "claude token not configured"; return 1; }
    local bin="${CLAUDE_BIN:-$(command -v claude 2>/dev/null)}"
    [ -n "$bin" ] || { _model_fail "claude binary not reachable"; return 1; }
    "$bin" -p --model "$id" --dangerously-skip-permissions < "$prompt" > "$out" 2>/dev/null &
    cpid=$!
  fi
  ( sleep "${MODEL_TIMEOUT:-600}"; touch "$out.timeout"; pkill -TERM -P "$cpid" 2>/dev/null; kill -TERM "$cpid" 2>/dev/null
    sleep 5; pkill -KILL -P "$cpid" 2>/dev/null; kill -KILL "$cpid" 2>/dev/null ) >/dev/null 2>&1 & wpid=$!
  disown "$wpid" 2>/dev/null
  wait "$cpid" 2>/dev/null; rc=$?
  local wsleep; wsleep="$(pgrep -P "$wpid" 2>/dev/null)"   # kill the watchdog FIRST so it can never reach its kill lines
  kill "$wpid" 2>/dev/null; [ -n "$wsleep" ] && kill $wsleep 2>/dev/null
  secs=$(( $(date +%s) - t0 ))
  # every call counts, success or not
  [ -n "${JOB_RUN_CALLS_FILE:-}" ] && printf '%s %s\n' "$tier" "$secs" >> "$JOB_RUN_CALLS_FILE"

  if [ -f "$out.timeout" ]; then rm -f "$out.timeout"; _model_fail "model call timed out after ${MODEL_TIMEOUT:-600}s"; return 1; fi
  [ "$rc" -eq 0 ] || { _model_fail "model call failed (rc=$rc)"; return 1; }
  [ -s "$out" ] || { _model_fail "empty model output"; return 1; }
  if [ -n "$marker" ] && ! grep -qF -e "$marker" "$out"; then _model_fail "model output missing marker"; return 1; fi
  return 0
}
