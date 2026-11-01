#!/bin/bash
# fake-actor.sh — FAKE stand-in for `claude -p`, used ONLY by probe-actor-writes.sh --selftest and actor-guard.sh
# --selftest (card TR2.0b). No network, no tokens, never the real binary. bash 3.2.
#
# 1. LAUNCH-SHAPE assertion (actor.lib.sh): refuses (exit 5, stderr `FAKE-ACTOR: shape ...`) unless HOME is NOT the
#    real home, LHB_JOURNAL_PATH lies inside HOME, CLAUDE_CONFIG_DIR / LIFEHACK_ROOT / CLAUDE_PLUGIN_ROOT /
#    CANARY_SEED / SKILL_TESTER_SEED are unset, DISABLE_AUTOUPDATER=1, and --plugin-dir, --settings,
#    --permission-mode bypassPermissions and --allowedTools Read are on the command line. Refuses
#    --dangerously-skip-permissions (exit 2).
# 2. WRITES it attempts (a refusal is logged to stderr and NOT acted on: a denied write must be caught by the kernel
#    log, never by the actor's own exit code):
#      $HOME/.claude.json                         always (the per-run home write every real session makes)
#      one fire-journal line to LHB_JOURNAL_PATH  unless FAKE_ACTOR_JOURNAL=0; plugin_src = the --plugin-dir value
#      FAKE_ACTOR_WRITES                          ':'-separated absolute paths; the token @systmp means
#                                                 <DARWIN_USER_TEMP_DIR>/claude-fake-<pid>.tmp (a TMPDIR bypass)
# 3. REPLY: a prompt carrying `read the file <path>,` (the census) -> the file's first line in claude's
#    --output-format json envelope (FAKE_ACTOR_MODE=noreply: a reply without it; launchfail: exit 1, no output).
#    Any other prompt (a canary step) -> exec fake-claude.sh with the same argv (FAKE_MODE good).
REAL_HOME="${FAKE_ACTOR_REAL_HOME:-}"
shape=""
plugin=""; prompt=""; perm=""; tools=""; settings=""
for a in "$@"; do [ "$a" = "--dangerously-skip-permissions" ] && { echo "FAKE-ACTOR: refused --dangerously-skip-permissions" >&2; exit 2; }; done
args=( "$@" )
i=0
while [ $i -lt ${#args[@]} ]; do
  case "${args[$i]}" in
    -p) prompt="${args[$((i+1))]}" ;;
    --plugin-dir) plugin="${args[$((i+1))]}" ;;
    --permission-mode) perm="${args[$((i+1))]}" ;;
    --allowedTools) tools="${args[$((i+1))]}" ;;
    --settings) settings="${args[$((i+1))]}" ;;
  esac
  i=$((i+1))
done
[ -n "$REAL_HOME" ] && [ "$HOME" = "$REAL_HOME" ] && shape="$shape HOME-is-real"
case "${LHB_JOURNAL_PATH:-}" in "$HOME"/*) ;; *) shape="$shape journal-outside-home" ;; esac
for v in CLAUDE_CONFIG_DIR LIFEHACK_ROOT CLAUDE_PLUGIN_ROOT CANARY_SEED SKILL_TESTER_SEED; do
  eval "[ -n \"\${$v+x}\" ]" && shape="$shape $v-set"
done
[ "${DISABLE_AUTOUPDATER:-}" = 1 ] || shape="$shape autoupdater-on"
[ -n "$plugin" ] || shape="$shape no-plugin-dir"
[ -n "$settings" ] || shape="$shape no-settings"
[ "$perm" = bypassPermissions ] || shape="$shape perm=$perm"
[ "$tools" = Read ] || shape="$shape tools=$tools"
if [ -n "$shape" ]; then echo "FAKE-ACTOR: shape$shape" >&2; exit 5; fi
[ "${FAKE_ACTOR_MODE:-}" = launchfail ] && exit 1

# the writes (refusals are expected under the guard: logged to stderr, deliberately not acted on)
{ printf '{"fake":true}\n' > "$HOME/.claude.json"; } || echo "FAKE-ACTOR: write refused (the kernel log must name it): $HOME/.claude.json" >&2
if [ "${FAKE_ACTOR_JOURNAL:-1}" != 0 ]; then
  mkdir -p "$(dirname "$LHB_JOURNAL_PATH")" || echo "FAKE-ACTOR: mkdir refused: $(dirname "$LHB_JOURNAL_PATH")" >&2
  { printf '{"ts":%s,"hook":"ingest_gate_enforce.sh","event":"PreToolUse","decision":"allow","exit_code":0,"session_id":"fake-%s","plugin_src":"%s"}\n' \
      "$(date +%s)" "$$" "$plugin" >> "$LHB_JOURNAL_PATH"; } || echo "FAKE-ACTOR: journal write refused: $LHB_JOURNAL_PATH" >&2
fi
oifs="$IFS"; IFS=':'
for w in ${FAKE_ACTOR_WRITES:-}; do
  IFS="$oifs"
  [ "$w" = @systmp ] && w="$(getconf DARWIN_USER_TEMP_DIR)claude-fake-$$.tmp"
  [ -n "$w" ] && { { printf 'fake actor write\n' > "$w"; } || echo "FAKE-ACTOR: write refused (the kernel log must name it): $w" >&2; }
  IFS=':'
done
IFS="$oifs"

f="$(printf '%s' "$prompt" | sed -n 's/.*read the file \([^ ,]*\),.*/\1/p' | head -1)"
if [ -z "$f" ]; then
  exec bash "$(cd "$(dirname "$0")/.." && pwd)/fake-claude.sh" "$@"
fi
line="$(head -1 "$f" 2>/dev/null)"
[ "${FAKE_ACTOR_MODE:-}" = noreply ] && line="I could not read it"
python3 -I -c 'import json,sys; print(json.dumps({"type":"result","subtype":"success","is_error":False,"result":sys.argv[1],"total_cost_usd":0.0007,"num_turns":2,"model":"fake-small"}))' "$line"
exit 0
