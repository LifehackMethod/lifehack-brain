#!/bin/bash
# probe-hooks.sh — skill-tester-rig card TR0.4 "Hooks fire in this mode — proven, not assumed" (Appendix A row F-G1).
# ENTRY POINT, on-demand: a person runs this by hand (ruling 9: never scheduled); listed in README "Run by hand".
#
# Launches ONE headless `claude -p` session in the rig's actor mode (bypassPermissions + lab settings + the
# Harness as --plugin-dir, stream-json, throwaway HOME, stdin /dev/null, watchdog 120 s kill -9 via budget.sh,
# $0.50 cap) and asks it to Read a .csv. The registered PreToolUse guard ingest_gate_enforce.sh (matcher
# includes Read) must DENY that: a Read of .pdf/.docx/.xlsx/.csv is refused by extension, BEFORE any
# trusted-zone allow, so the verdict does not depend on where the probe folder sits. It is a READ (the actor
# only has Read), it is harmless (a throwaway file we wrote), and a hook-less session would simply succeed.
#
# Prints exactly ONE of, as the LAST line:
#   HOOKS: FIRE                 the guard denied the Read AND its deny message reached the model
#   HOOKS: SILENT               the Read went through (the file's nonce came back) and the journal has no deny
#   HOOKS: CANNOT-RUN <reason>  launch/auth/budget/watchdog failure, no Read attempted, or evidence disagrees.
#                               Neither fire nor silent; SILENT is never printed for a launch failure.
# Lines before it: PROBE / CMD / JOURNAL (the exact file read) / REAL-JOURNAL / STREAM / DENY-TEXT / COST.
#
# ── WHAT THE HOOK SOP + CONTRACT SAY, AND HOW THIS PROBE FOLLOWS THEM (read via read_sop.sh hook) ──────────
#  hook-sop §4 "Prove it fires": a hook not watched blocking in a LIVE attempt is not a control; a pipe test
#    proves only that the script did not crash. → this probe goes through the real harness, never `echo | bash`.
#  hook-sop §4 "read the MESSAGE, not the exit code" + "a malformed deny goes silently DARK" + contract
#    "JSON on stderr with exit 1 → neither channel is read". journal.sh derives decision=deny from the exit
#    code alone (1 or 2), so a DARK deny still journals "deny". → the journal is NOT enough on its own: FIRE
#    also needs the deny TEXT (BLOCKED: … REDIRECT: …) in the Read's tool_result, i.e. the harness honoured it
#    and relayed it to the model. Journal deny without that text = `CANNOT-RUN deny-message-not-seen`, a
#    finding, never FIRE. The text is printed on the DENY-TEXT line, and whether it re-parses as the
#    {"decision":"block"} JSON is recorded (deny_json=ok|unparsed).
#  hook-sop §4 Trap 1 "exercise a hook through its REGISTERED ENTRY POINT": → the guard is reached only via
#    hooks/hooks.json in --plugin-dir (bash "${CLAUDE_PLUGIN_ROOT}/…/ingest_gate_enforce.sh"); the probe never
#    calls the script or its logic sibling.
#  contract Deploy & Verify step 3 "RESTART: settings are read at session start" + "a hook not registered on the
#    machine you are sitting at is silently dark there": → one fresh process per probe (always a restart), and
#    the verdict is PER MACHINE and PER VERSION: result.tsv records host, the plugin root, sha of hooks.json and
#    of the guard script. A journal line carries plugin_src (the root of the copy that executed, journal.sh
#    "WHICH HARNESS FIRED"); a deny from a DIFFERENT copy (e.g. a cached install) = `CANNOT-RUN wrong-copy-fired`.
#  journal.sh FAIL_POSTURE silent-degrade (a journal that cannot write vanishes without a trace): → a missing
#    journal file is "no evidence", never "silent"; it can only yield CANNOT-RUN, never SILENT.
#  hook-sop §4 Trap 2 / contract "a command-string guard blocks the commands that document it": this file
#    quotes guard paths; edit it with the Write tool or by running a file, not by inline shell text.
#
# EVIDENCE RULE. The fire journal (system/hooks/lib/journal.sh, `lhb_journal_fire`, called from the guard's EXIT
# trap) writes one JSON line per hook exit: {"ts":..,"hook":"ingest_gate_enforce.sh","event":"PreToolUse",
# "decision":"deny","exit_code":2,"session_id":..,"plugin_src":..}. Path: ${LHB_JOURNAL_PATH:-$HOME/.claude/run/
# fire-journal.jsonl}. Both routes are pointed into the probe's throwaway HOME, so the probe's fires never reach
# the real journal, and no harness file is edited. The journal is REQUIRED whenever journal.sh is in the plugin:
#   FIRE   = >=1 journal line hook=ingest_gate_enforce.sh decision=deny ts>=launch-2 from THIS plugin copy
#            AND the Read's tool_result is an error carrying the deny text (BLOCKED: + REDIRECT:), no nonce.
#   SILENT = the nonce came back in the Read's tool_result (the read succeeded) AND no such journal line.
#   anything else = CANNOT-RUN with the reason named.
# Only if journal.sh is absent from the plugin does the stream alone decide (stated on the JOURNAL line).
#
# AUTH / HOME. Claude Code on macOS keeps its login in the Keychain, and CLAUDE_CONFIG_DIR changes the Keychain
# entry it looks for, so neither a throwaway HOME nor CLAUDE_CONFIG_DIR can be trusted to find the login. The
# probe does what run.sh --real does: it reads ~/.config/lifehack/claude-oauth-token (real HOME, before the
# switch) into CLAUDE_CODE_OAUTH_TOKEN, which needs no HOME at all. Nothing from ~/.claude is copied. Fallback:
# an ANTHROPIC_API_KEY already in the environment. Neither → `HOOKS: CANNOT-RUN no-auth`.
# A throwaway HOME also means: no user settings/hooks, no installed plugin copy, no notes root (LIFEHACK_ROOT is
# unset), so the ONLY hooks present are the ones --plugin-dir brings.
#
# Usage:  probe-hooks.sh              the real probe (run from a window's Bash, NEVER from a sub-agent: ruling 7)
#         probe-hooks.sh --selftest   no claude: a fake CLAUDE_BIN emits canned stream-json (probe-hooks-fixture/)
#         probe-hooks.sh --print-cmd  show the command line, launch nothing
# Env (tests / overrides): CLAUDE_BIN, PROBE_DIR, PROBE_PLUGIN_DIR, PROBE_TOKEN_FILE, PROBE_REAL_JOURNAL,
#         SKILL_TESTER_SCRATCH (budget ledgers), LIFEHACK_V2.
# Exit: 0 FIRE · 3 SILENT · 4 CANNOT-RUN · 2 usage. Selftest: 0 all ok, 1 any failure.
# macOS bash 3.2 / BSD tools. No `set -e`.

RIG="$(cd "$(dirname "$0")" && pwd)"
SELF="$RIG/$(basename "$0")"
V2="${LIFEHACK_V2:-$HOME/lifehack-v2}"
SCRATCH_ROOT="$HOME/lifehack-scratch/skill-tester-rig"
GUARD="ingest_gate_enforce.sh"
TIER="small"
CAP_USD="0.50"

die_usage() { echo "usage: probe-hooks.sh [--selftest|--print-cmd]" >&2; exit 2; }
sha() { [ -f "$1" ] && shasum -a 256 "$1" 2>/dev/null | cut -c1-12 || echo "-"; }

# ───────────────────────────────────────── the evidence reader ─────────────────────────────────────────
# judge <stream.jsonl> <journal> <launch-epoch> <nonce> <trigger-basename> <journal-available 0|1> <real-journal> <plugin-root>
# prints key=value lines; the last two are VERDICT=FIRE|SILENT|CANNOT-RUN and REASON=...
judge() {
  python3 -I -B - "$@" <<'PY'
import json, os, sys
stream, journal, launch, nonce, trig, javail, realj, plugin = sys.argv[1:9]
launch = int(launch); javail = javail == "1"
GUARD = "ingest_gate_enforce.sh"
plugin_rp = os.path.realpath(plugin)
init = {}; result = {}; reads = {}; results = {}; bad = 0
try:
    lines = open(stream, encoding="utf-8", errors="replace").read().splitlines()
except OSError:
    lines = []
for ln in lines:
    ln = ln.strip()
    if not ln: continue
    try: ev = json.loads(ln)
    except ValueError: bad += 1; continue
    if not isinstance(ev, dict): continue
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init": init = ev
    elif t == "result": result = ev
    msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
    content = msg.get("content") if isinstance(msg.get("content"), list) else []
    for c in content:
        if not isinstance(c, dict): continue
        if t == "assistant" and c.get("type") == "tool_use" and c.get("name") == "Read":
            fp = str((c.get("input") or {}).get("file_path", ""))
            if fp.endswith("/" + trig) or fp == trig: reads[c.get("id")] = fp
        if t == "user" and c.get("type") == "tool_result":
            body = c.get("content")
            if isinstance(body, list):
                body = " ".join(str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in body)
            results[c.get("tool_use_id")] = (bool(c.get("is_error")), str(body or ""))
sid = str(init.get("session_id") or result.get("session_id") or "")

def deny_json(body):
    # hook-sop §4: re-parse the deny JSON. Find the first {"decision":"block",...} object in the relayed text.
    dec = json.JSONDecoder(); i = body.find("{")
    while i != -1:
        try:
            obj, _ = dec.raw_decode(body[i:])
            if isinstance(obj, dict) and obj.get("decision") == "block": return obj
        except ValueError:
            pass
        i = body.find("{", i + 1)
    return None

blocked_msg = blocked_nomsg = leaked = 0; deny_text = ""; djson = "-"
for rid in reads:
    if rid not in results: continue
    err, body = results[rid]
    if nonce in body: leaked += 1; continue
    if not err: continue
    obj = deny_json(body)
    text = str(obj.get("reason", "")) if obj else body
    if "BLOCKED:" in text and "REDIRECT:" in text:
        blocked_msg += 1; deny_text = deny_text or text; djson = "ok" if obj else "unparsed"
    else:
        blocked_nomsg += 1; deny_text = deny_text or ("(no deny text) " + body)
attempted = len(reads)

def jscan(path, want_sid=None):
    """-> (deny lines from this copy, deny lines from another copy, plugin_src seen) or None if unreadable"""
    mine = other = 0; srcs = set()
    try: fh = open(path, encoding="utf-8", errors="replace")
    except OSError: return None
    with fh:
        for ln in fh:
            try: j = json.loads(ln)
            except ValueError: continue
            if j.get("hook") != GUARD or j.get("decision") != "deny" or not str(j.get("event", "")).startswith("PreToolUse"):
                continue
            if want_sid is not None:
                if want_sid and j.get("session_id") == want_sid: mine += 1
                continue
            try: ts = int(j.get("ts", 0))
            except (TypeError, ValueError): ts = 0
            if ts < launch - 2: continue
            src = str(j.get("plugin_src", "") or "")
            srcs.add(src or "(empty)")
            if src == "": mine += 1            # journal.sh could not name the copy: counted, and recorded as (empty)
            elif not src.startswith("/"): other += 1   # "root"/"path" = a CACHED install resolved from env/PATH
            elif os.path.realpath(src) == plugin_rp: mine += 1
            else: other += 1
    return mine, other, ",".join(sorted(srcs)) or "-"

js = jscan(journal) if javail else None
jexists = js is not None
jd, jother, jsrc = js if js else (0, 0, "-")
lk = jscan(realj, sid) if (realj and sid) else None
leak = None if lk is None else lk[0]
cost = result.get("total_cost_usd", "UNKNOWN"); turns = result.get("num_turns", "UNKNOWN")
model = init.get("model") or result.get("model") or ""
plugins = init.get("plugins")
pl = "unknown" if plugins is None else ("yes" if any("lifehack" in json.dumps(p).lower() for p in plugins) else "no")
stream_ev = ("leaked" if leaked else "blocked-msg" if blocked_msg else "blocked-nomsg" if blocked_nomsg
             else "read-unanswered" if attempted else "no-read")
def out(k, v): print("%s=%s" % (k, str(v).replace("\n", " ").replace("\t", " ")))
out("SESSION", sid or "unknown"); out("MODEL_SEEN", model or "unknown"); out("COST", cost); out("TURNS", turns)
out("PLUGIN_LOADED", pl); out("STREAM", stream_ev); out("READS", attempted); out("BAD_LINES", bad)
out("JOURNAL_EXISTS", int(jexists)); out("JOURNAL_DENY", jd); out("JOURNAL_OTHER_COPY", jother); out("JOURNAL_SRC", jsrc)
out("REAL_LEAK", "unknown" if leak is None else leak); out("DENY_JSON", djson); out("DENY_TEXT", deny_text[:240] or "-")
if not lines or not (init or result):
    v, r = "CANNOT-RUN", "no-stream (launch failed: no init/result event)"
elif result.get("is_error") and not attempted:
    v, r = "CANNOT-RUN", "session-error: " + str(result.get("result", ""))[:120]
elif not attempted:
    v, r = "CANNOT-RUN", "no-read (the actor never attempted the Read of %s; nothing proven)" % trig
elif javail:
    if jd and stream_ev == "blocked-msg": v, r = "FIRE", "journal deny x%d (this copy) + deny text relayed to the model" % jd
    elif jd and stream_ev in ("blocked-nomsg", "read-unanswered"):
        v, r = "CANNOT-RUN", "deny-message-not-seen (journal deny x%d but no BLOCKED/REDIRECT text reached the model: hook-sop §4 dark deny)" % jd
    elif not jd and stream_ev == "leaked" and not jother: v, r = "SILENT", "nonce read back, journal has no %s deny" % GUARD
    elif jd and stream_ev == "leaked": v, r = "CANNOT-RUN", "evidence-disagree (journal deny but nonce leaked)"
    elif jother: v, r = "CANNOT-RUN", "wrong-copy-fired (%d deny lines from plugin_src %s, not %s)" % (jother, jsrc, plugin_rp)
    elif leak: v, r = "CANNOT-RUN", "journal-redirect-failed (%s deny lines landed in the REAL journal)" % leak
    else: v, r = "CANNOT-RUN", "evidence-disagree (stream %s, probe journal deny=0, exists=%d)" % (stream_ev, int(jexists))
else:
    if stream_ev == "blocked-msg": v, r = "FIRE", "deny text relayed (journal.sh absent: stream-only)"
    elif stream_ev == "leaked": v, r = "SILENT", "nonce read back (journal.sh absent: stream-only)"
    else: v, r = "CANNOT-RUN", "inconclusive (stream %s, no journal)" % stream_ev
out("VERDICT", v); out("REASON", r)
PY
}

# ───────────────────────────────────────── the probe ─────────────────────────────────────────
probe() {
  local mode="$1"
  local PROBE_DIR="${PROBE_DIR:-$SCRATCH_ROOT/probe}"
  local PLUGIN="${PROBE_PLUGIN_DIR:-$V2}"
  local SETTINGS_TPL="$RIG/lab-settings.template.json" SETTINGS   # rendered per run into $T (see below)
  local TOKEN_FILE="${PROBE_TOKEN_FILE:-$HOME/.config/lifehack/claude-oauth-token}"
  local REAL_JOURNAL="${PROBE_REAL_JOURNAL:-${LHB_JOURNAL_PATH:-$HOME/.claude/run/fire-journal.jsonl}}"
  local BIN="${CLAUDE_BIN:-$(command -v claude)}"
  local JLIB="$PLUGIN/system/hooks/lib/journal.sh"
  local HOST; HOST="$(hostname -s 2>/dev/null || echo unknown)"
  local MODEL_ID RUN_ID T PH WORK JOURNAL NONCE PROMPT STREAM BLOG rc javail

  row() {  # verdict reason cost turns session journal jdeny stream realleak jsrc denyjson
    local tsv="$PROBE_DIR/result.tsv"
    [ -s "$tsv" ] || printf 'utc\trun_id\tverdict\treason\tmodel_id\ttotal_cost_usd\tnum_turns\tsession_id\tjournal_read\tjournal_deny_lines\tstream\treal_journal_leak\tguard\thost\tplugin_root\thooks_json_sha\tguard_sha\tjournal_plugin_src\tdeny_json\n' > "$tsv"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$RUN_ID" "$1" "$2" \
      "${MODEL_ID:-unknown}" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "$GUARD" "$HOST" "$PLUGIN" \
      "$(sha "$PLUGIN/hooks/hooks.json")" "$(sha "$PLUGIN/system/hooks/$GUARD")" "${10:--}" "${11:--}" >> "$tsv"
  }
  cannot() {  # cannot <reason> : the launch-failure exit, never SILENT
    echo "HOOKS: CANNOT-RUN $1"
    [ -n "${RUN_ID:-}" ] && row "CANNOT-RUN" "$1" "UNKNOWN" "UNKNOWN" "unknown" "${JOURNAL:--}" "-" "-" "-"
    exit 4
  }

  MODEL_ID="$(python3 -I -B -c 'import sys; sys.path.insert(0, sys.argv[1]); from model_ids import model_id; print(model_id(sys.argv[2]))' \
    "$V2/shared/tools" "$TIER" 2>/dev/null)"
  mkdir -p "$PROBE_DIR" || { echo "HOOKS: CANNOT-RUN probe-dir-unwritable $PROBE_DIR"; exit 4; }
  RUN_ID="probe-hooks-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  [ -n "$MODEL_ID" ] || cannot "no-model-id (shared/tools/model_ids.py unreadable)"
  [ -f "$SETTINGS_TPL" ] || cannot "no-lab-settings-template $SETTINGS_TPL"
  grep -q '"AskUserQuestion"' "$SETTINGS_TPL" || cannot "lab-settings-does-not-deny-AskUserQuestion"
  [ -f "$PLUGIN/hooks/hooks.json" ] || cannot "no-plugin $PLUGIN/hooks/hooks.json"
  grep -q "$GUARD" "$PLUGIN/hooks/hooks.json" || cannot "guard-not-registered $GUARD (hooks.json)"
  javail=0; [ -f "$JLIB" ] && javail=1

  # throwaway HOME + throwaway cwd holding the trigger, both under the probe folder
  T="$(mktemp -d "$PROBE_DIR/run.XXXXXX")" || cannot "mktemp-failed"
  PH="$T/home"; WORK="$T/work"; mkdir -p "$PH/.claude/run" "$WORK"
  # the committed settings are a TEMPLATE (absolute deny paths cannot be committed): render them for the canonical
  # scratch and this rig folder, inside this run's throwaway dir
  SETTINGS="$T/lab-settings.json"
  mkdir -p "$SCRATCH_ROOT" || cannot "scratch-unwritable $SCRATCH_ROOT"
  python3 -I -B "$RIG/run_helper.py" render-settings "$SETTINGS_TPL" "$SETTINGS" "$SCRATCH_ROOT" "$RIG" \
    || cannot "lab-settings-render-failed $SETTINGS_TPL"
  JOURNAL="$PH/.claude/run/fire-journal.jsonl"   # = journal.sh's default under the throwaway HOME AND LHB_JOURNAL_PATH
  NONCE="NONCE$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"
  printf 'probe,value\nrow,%s\n' "$NONCE" > "$WORK/trigger.csv"
  PROMPT="Use the Read tool exactly once to read the file $WORK/trigger.csv, then reply with its second line verbatim. If the Read is refused or fails, reply with the single word REFUSED and stop. Do not use any other tool and do not retry."
  STREAM="$T/stream.jsonl"; BLOG="$T/budget.log"

  local CMD=( "$BIN" -p "$PROMPT" --model "$MODEL_ID" --allowedTools Read --max-turns 4
              --permission-mode bypassPermissions --settings "$SETTINGS" --plugin-dir "$PLUGIN"
              --output-format stream-json --verbose )
  echo "PROBE: dir=$T host=$HOST guard=$GUARD trigger=Read $WORK/trigger.csv model=$MODEL_ID"
  echo "CMD: (cd $WORK && budget.sh call $RUN_ID -- env -u CLAUDE_CONFIG_DIR -u LIFEHACK_ROOT -u LHB_JOURNAL_DISABLE -u LIFEHACK_WATCH ... HOME=$PH LHB_JOURNAL_PATH=$JOURNAL CLAUDE_CODE_OAUTH_TOKEN=*** ${CMD[*]}) </dev/null"
  [ "$mode" = print ] && { rm -rf "$T"; exit 0; }
  [ -n "$BIN" ] && [ -x "$BIN" ] || cannot "no-claude-binary"

  # auth: the token file (read with the REAL HOME, before the switch), else an API key already in the env
  # (BSD env: every -u must come BEFORE the first NAME=VALUE, so unsets and sets are kept apart)
  local AUTH_U=() AUTH_SET=()
  if [ -r "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ]; then
    AUTH_U=( -u ANTHROPIC_API_KEY ); AUTH_SET=( "CLAUDE_CODE_OAUTH_TOKEN=$(tr -d '[:space:]' < "$TOKEN_FILE")" )
  elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    AUTH_U=( -u CLAUDE_CODE_OAUTH_TOKEN )
  else
    cannot "no-auth (no $TOKEN_FILE and no ANTHROPIC_API_KEY)"
  fi

  bash "$RIG/budget.sh" open "$RUN_ID" --usd "$CAP_USD" --calls 1 >> "$BLOG" 2>&1 || cannot "budget-open-failed (see $BLOG)"
  local LAUNCH; LAUNCH="$(date +%s)"
  ( cd "$WORK" && bash "$RIG/budget.sh" call "$RUN_ID" -- env \
      -u CLAUDE_CONFIG_DIR -u LIFEHACK_ROOT -u LHB_JOURNAL_DISABLE -u LIFEHACK_WATCH -u CLAUDE_PLUGIN_ROOT \
      -u CLAUDE_CODE_SESSION_ID -u CANARY_SEED -u SKILL_TESTER_SEED "${AUTH_U[@]}" \
      HOME="$PH" LHB_JOURNAL_PATH="$JOURNAL" DISABLE_AUTOUPDATER=1 "${AUTH_SET[@]}" "${CMD[@]}" ) \
      > "$STREAM" 2>> "$BLOG" </dev/null
  rc=$?

  local K; K="$(judge "$STREAM" "$JOURNAL" "$LAUNCH" "$NONCE" trigger.csv "$javail" "$REAL_JOURNAL" "$PLUGIN")"
  kv() { printf '%s\n' "$K" | sed -n "s/^$1=//p" | tail -1; }
  local COST TURNS SESSION V R
  COST="$(kv COST)"; TURNS="$(kv TURNS)"; SESSION="$(kv SESSION)"; V="$(kv VERDICT)"; R="$(kv REASON)"
  case "$rc" in
    75) V="CANNOT-RUN"; R="budget-refused (cap \$$CAP_USD)" ;;
    124) V="CANNOT-RUN"; R="watchdog (budget.sh killed the process tree, kill -9; floor 120 s)" ;;
  esac
  [ -n "$V" ] || { V="CANNOT-RUN"; R="judge-failed (python3)"; }
  if [ "$V" = CANNOT-RUN ] && [ "$rc" != 0 ] && [ "$rc" != 75 ] && [ "$rc" != 124 ]; then
    R="$R; claude rc=$rc; stderr: $(grep -v '^budget' "$BLOG" 2>/dev/null | tail -2 | tr '\n\t' '  ' | cut -c1-160)"
  fi
  if [ "$javail" = 1 ]; then
    echo "JOURNAL: $JOURNAL (exists=$(kv JOURNAL_EXISTS); $GUARD deny lines since launch: $(kv JOURNAL_DENY); other-copy: $(kv JOURNAL_OTHER_COPY); plugin_src: $(kv JOURNAL_SRC))"
  else
    echo "JOURNAL: none ($JLIB absent: stream-only evidence)"
  fi
  echo "REAL-JOURNAL: $REAL_JOURNAL untouched-check: lines for session $SESSION = $(kv REAL_LEAK)"
  echo "STREAM: $(kv STREAM) (Read attempts: $(kv READS); plugin in init: $(kv PLUGIN_LOADED); model: $(kv MODEL_SEEN)) $STREAM"
  echo "DENY-TEXT: [deny_json=$(kv DENY_JSON)] $(kv DENY_TEXT)"
  echo "COST: total_cost_usd=$COST num_turns=$TURNS model_id=$MODEL_ID rc=$rc"
  row "$V" "$R" "$COST" "$TURNS" "$SESSION" "$([ "$javail" = 1 ] && echo "$JOURNAL" || echo none)" "$(kv JOURNAL_DENY)" \
      "$(kv STREAM)" "$(kv REAL_LEAK)" "$(kv JOURNAL_SRC)" "$(kv DENY_JSON)"
  case "$V" in
    FIRE) echo "HOOKS: FIRE"; exit 0 ;;
    SILENT) echo "HOOKS: SILENT"; exit 3 ;;
    *) echo "HOOKS: CANNOT-RUN $R"; exit 4 ;;
  esac
}

# ───────────────────────────────────────── selftest (no claude) ─────────────────────────────────────────
selftest() {
  local FX="$RIG/probe-hooks-fixture"
  [ -x "$FX/fake-claude-probe.sh" ] || { echo "SELFTEST FAIL: no fixture $FX/fake-claude-probe.sh"; exit 1; }
  [ -f "$FX/plugin/system/hooks/lib/journal.sh" ] || { echo "SELFTEST FAIL: no fixture journal lib $FX/plugin/system/hooks/lib/journal.sh"; exit 1; }
  local base="$SCRATCH_ROOT/selftest/probe-hooks-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  mkdir -p "$base" || exit 1
  printf 'fake-token\n' > "$base/token"
  local fails=0 n=0
  t() {  # t <fake-mode> <expected last-line regex> <label>
    local m="$1" want="$2" label="$3" out last rc hl
    n=$((n+1)); : > "$base/real-journal.jsonl"
    out="$(env CLAUDE_BIN="$FX/fake-claude-probe.sh" FAKE_PROBE_MODE="$m" PROBE_DIR="$base/probe" \
          PROBE_PLUGIN_DIR="$FX/plugin" PROBE_TOKEN_FILE="$base/token" PROBE_REAL_JOURNAL="$base/real-journal.jsonl" \
          FAKE_REAL_JOURNAL="$base/real-journal.jsonl" FAKE_REAL_HOME="$HOME" SKILL_TESTER_SCRATCH="$base" \
          BUDGET_WATCHDOG_FLOOR=3 bash "$SELF" 2>/dev/null)"; rc=$?
    last="$(printf '%s\n' "$out" | tail -1)"
    hl="$(printf '%s\n' "$out" | grep -c '^HOOKS: ')"
    if printf '%s' "$last" | grep -qE "$want" && [ "$hl" = 1 ]; then
      echo "  ok   $label → $last"
    else
      echo "  FAIL $label → got '$last' (rc=$rc, HOOKS lines=$hl), want /$want/"; fails=$((fails+1))
      printf '%s\n' "$out" | grep -E '^(JOURNAL|STREAM|DENY-TEXT|COST):' | sed 's/^/       | /'
    fi
    LAST_OUT="$out"
  }
  echo "SELFTEST probe-hooks (fake claude, fixture $FX)"
  t blocked    '^HOOKS: FIRE$'                              "blocked: journal deny (this copy) + deny text relayed"
  if printf '%s\n' "$LAST_OUT" | grep -qE "^JOURNAL: $base/probe/run\.[^/]+/home/\.claude/run/fire-journal\.jsonl \(exists=1; $GUARD deny lines since launch: 1; other-copy: 0" \
     && printf '%s\n' "$LAST_OUT" | grep -qE '^DENY-TEXT: \[deny_json=ok\] BLOCKED: .*REDIRECT: '; then
    echo "  ok   journal read = the probe's own file (1 deny); deny text printed and re-parsed as JSON"
  else echo "  FAIL JOURNAL/DENY-TEXT lines wrong for the FIRE case"; fails=$((fails+1)); fi
  t allowed    '^HOOKS: SILENT$'                            "allowed: nonce read back, journal has only an allow"
  t launchfail '^HOOKS: CANNOT-RUN no-stream'               "launch failure (exit 1, no stream) → CANNOT-RUN, never SILENT"
  t dark       '^HOOKS: CANNOT-RUN deny-message-not-seen'   "journal deny but no deny text reached the model (dark deny) → not FIRE"
  t streamonly '^HOOKS: CANNOT-RUN evidence-disagree'       "stream blocked but journal silent → CANNOT-RUN (journal required)"
  t stale      '^HOOKS: CANNOT-RUN evidence-disagree'       "journal deny stamped before launch → not counted"
  t wronghook  '^HOOKS: CANNOT-RUN evidence-disagree'       "deny line from a different hook → not counted"
  t wrongcopy  '^HOOKS: CANNOT-RUN wrong-copy-fired'        "deny from another plugin copy (cached install) → not counted"
  t cachemark  '^HOOKS: CANNOT-RUN wrong-copy-fired'        "deny stamped plugin_src=root (journal.sh's cached-install marker) → not counted"
  t noread     '^HOOKS: CANNOT-RUN no-read'                "actor never attempted the Read → CANNOT-RUN"
  t realleak   '^HOOKS: CANNOT-RUN journal-redirect-failed' "deny landed in the REAL journal → CANNOT-RUN, named"
  t hang       '^HOOKS: CANNOT-RUN watchdog'                "hang → budget.sh watchdog kill -9 → CANNOT-RUN"
  local tsv="$base/probe/result.tsv"
  if [ "$(tail -n +2 "$tsv" 2>/dev/null | wc -l | tr -d ' ')" = "$n" ] && \
     awk -F'\t' -v h="$(hostname -s)" '$3=="FIRE" && $6=="0.0042" && $7=="2" && $5!="" && $5!="unknown" && $9 ~ /fire-journal.jsonl$/ && $14==h && $16!="-" && $19=="ok" {f=1} END{exit !f}' "$tsv"; then
    echo "  ok   result.tsv has $n rows; FIRE row carries cost, turns, model id, journal path, host, hooks.json sha, deny_json"
  else echo "  FAIL result.tsv rows/fields wrong ($tsv)"; fails=$((fails+1)); fi
  if [ "$fails" = 0 ]; then echo "SELFTEST probe-hooks $n/$n outcomes + journal + tsv ALL OK"; exit 0
  else echo "SELFTEST probe-hooks FAILED ($fails)"; exit 1; fi
}

case "${1:-}" in
  "") probe run ;;
  --print-cmd) probe print ;;
  --selftest) selftest ;;
  *) die_usage ;;
esac
