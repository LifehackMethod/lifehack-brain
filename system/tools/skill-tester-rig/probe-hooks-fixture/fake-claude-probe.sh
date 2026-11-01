#!/bin/bash
# fake-claude-probe.sh — stand-in for `claude` in probe-hooks.sh --selftest. No network, no tokens.
# Emits canned stream-json and, where a real guard would, a fire-journal line to $LHB_JOURNAL_PATH in the
# shape journal.sh writes (ts, hook, event, decision, exit_code, session_id, plugin_src = the plugin root).
# FIRST it asserts the launch contract (exit 9 + "ASSERT ..." on stderr if broken), so a probe that
# drifts from the card's command line / isolation cannot pass the FIRE case.
# FAKE_PROBE_MODE: blocked|allowed|launchfail|dark|streamonly|stale|wronghook|wrongcopy|cachemark|noread|realleak|hang
a() { echo "ASSERT: $*" >&2; exit 9; }
args=" $* "
for x in "$@"; do [ "$x" = "--dangerously-skip-permissions" ] && a "--dangerously-skip-permissions passed (ruling 8)"; done
case "$args" in *" --permission-mode bypassPermissions "*) ;; *) a "no --permission-mode bypassPermissions" ;; esac
case "$args" in *" --output-format stream-json "*) ;; *) a "no --output-format stream-json" ;; esac
case "$args" in *" --verbose "*) ;; *) a "no --verbose" ;; esac
case "$args" in *" --model "*) ;; *) a "no --model" ;; esac
prompt=""; settings=""; model=""; plugin=""
while [ $# -gt 0 ]; do
  case "$1" in -p) prompt="$2"; shift ;; --settings) settings="$2"; shift ;; --model) model="$2"; shift ;;
               --plugin-dir) plugin="$2"; shift ;; esac; shift
done
[ -f "$plugin/hooks/hooks.json" ] || a "--plugin-dir has no hooks/hooks.json: '$plugin'"
grep -q '"AskUserQuestion"' "$settings" 2>/dev/null || a "settings $settings does not deny AskUserQuestion"
[ -n "$FAKE_REAL_HOME" ] && [ "$HOME" = "$FAKE_REAL_HOME" ] && a "HOME is the real HOME"
case "$HOME" in */probe/run.*/home) ;; *) a "HOME not a throwaway under the probe dir: $HOME" ;; esac
[ "$LHB_JOURNAL_PATH" = "$HOME/.claude/run/fire-journal.jsonl" ] || a "LHB_JOURNAL_PATH not in the throwaway HOME: $LHB_JOURNAL_PATH"
[ -z "${CLAUDE_CONFIG_DIR+x}" ] || a "CLAUDE_CONFIG_DIR leaked in"
[ -z "${LIFEHACK_ROOT+x}" ] || a "LIFEHACK_ROOT leaked in (hooks could reach the real notes)"
[ -n "$CLAUDE_CODE_OAUTH_TOKEN" ] || a "no CLAUDE_CODE_OAUTH_TOKEN"
if IFS= read -r -t 1 _x; then a "stdin is not /dev/null"; fi
case "$PWD" in */probe/run.*/work) ;; *) a "cwd not the throwaway work folder: $PWD" ;; esac

mode="${FAKE_PROBE_MODE:-blocked}"
trig="$(printf '%s' "$prompt" | sed -n 's/.*read the file \([^ ,]*\),.*/\1/p')"
[ -f "$trig" ] || a "trigger file not found from prompt: '$trig'"
now="$(date +%s)"; sid="fake-sess-1"; root="$(cd "$plugin" && pwd -P)"
J() {  # J <file> <ts> <hook> <decision> <rc> [plugin_src]
  printf '{"ts":%s,"hook":"%s","event":"PreToolUse","matcher":"Read","decision":"%s","exit_code":%s,"session_id":"%s","plugin_version":"x","plugin_src":"%s","harness":"V2"}\n' \
    "$2" "$3" "$4" "$5" "$sid" "${6:-$root}" >> "$1"
}
init() { printf '{"type":"system","subtype":"init","session_id":"%s","model":"%s","tools":["Read"],"plugins":[{"name":"lifehack-brain","path":"%s"}]}\n' "$sid" "$model" "$root"; }
use() { printf '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"tu1","name":"Read","input":{"file_path":"%s"}}]}}\n' "$trig"; }
# the relayed deny: the harness's "hook error" prefix + the guard's stderr JSON (same shape as ingest_gate_enforce's .csv deny)
res_block() { printf '%s\n' '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"tu1","is_error":true,"content":"PreToolUse:Read hook error: [bash ingest_gate_enforce.sh]: {\"decision\":\"block\",\"reason\":\"BLOCKED: Read on a .csv hands over cells beginning =, +, - or @. REDIRECT: python3 <repo>/system/tools/safe_csv.py <path>.\"}"}]}}'; }
res_dark()  { printf '%s\n' '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"tu1","is_error":true,"content":"PreToolUse:Read hook error: [bash ingest_gate_enforce.sh]: No stderr output"}]}}'; }
res_ok() { python3 -I -c 'import json,sys; print(json.dumps({"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"tu1","content":[{"type":"text","text":open(sys.argv[1]).read()}]}]}}))' "$trig"; }
final() { printf '{"type":"result","subtype":"success","is_error":false,"result":"%s","total_cost_usd":0.0042,"num_turns":2,"session_id":"%s"}\n' "$1" "$sid"; }
G=ingest_gate_enforce.sh
case "$mode" in
  blocked)    init; use; J "$LHB_JOURNAL_PATH" "$now" $G deny 2; res_block; final REFUSED ;;
  allowed)    init; use; J "$LHB_JOURNAL_PATH" "$now" $G allow 0; res_ok; final row ;;
  launchfail) echo "Invalid API key · Please run /login" >&2; exit 1 ;;
  dark)       init; use; J "$LHB_JOURNAL_PATH" "$now" $G deny 1; res_dark; final REFUSED ;;
  streamonly) init; use; res_block; final REFUSED ;;
  stale)      init; use; J "$LHB_JOURNAL_PATH" "$((now-1000))" $G deny 2; res_block; final REFUSED ;;
  wronghook)  init; use; J "$LHB_JOURNAL_PATH" "$now" guard_canon_write.sh deny 2; res_block; final REFUSED ;;
  wrongcopy)  init; use; J "$LHB_JOURNAL_PATH" "$now" $G deny 2 "/x/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.0"; res_block; final REFUSED ;;
  cachemark)  init; use; J "$LHB_JOURNAL_PATH" "$now" $G deny 2 "root"; res_block; final REFUSED ;;
  noread)     init; final "I will not read files." ;;
  realleak)   init; use; J "$FAKE_REAL_JOURNAL" "$now" $G deny 2; res_block; final REFUSED ;;
  hang)       init; sleep 600 ;;   # pacing: the hang stand-in; probe-hooks' watchdog must kill it
  *) a "unknown FAKE_PROBE_MODE $mode" ;;
esac
exit 0
