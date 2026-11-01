#!/bin/bash
# actor-guard.sh — skill-tester-rig card TR2.0b "The real actor, under the guard, with the harness loaded".
# ENTRY POINT, on-demand: the main window runs it by hand from its Bash, NEVER from a sub-agent (ruling 7); listed
# in README "Run by hand". It is an UNGUARDED orchestrator (like bite.sh): it starts the guarded pieces and reads
# their evidence; it never runs inside sandbox-exec itself.
#
#   actor-guard.sh              REAL: two stages, fail-fast, then the receipt
#     1. probe-actor-writes.sh  one real cheapest-tier actor under the census profile. Must end
#                               `WRITELIST: PROVEN ...`: every write the actor made lies in its per-run tree (throwaway
#                               HOME, run dir, TMPDIR), all inside the scratch allow root under run.sh. Anything else
#                               (NEEDS-RULING / CANNOT-RUN) stops here: stage 2 is NOT run. A path the actor needs that
#                               the guard lacks is named, and a PROPOSED patch is written beside the census; this script
#                               NEVER applies it and never widens the guard (applying it is a ruled step).
#     2. run.sh --real --model-tier small   one real canary run (12 steps) under the write guard with the Harness as
#                               --plugin-dir, then truth.py. Must hold ALL of: run exit 0 · SEAM_GUARD=on · zero
#                               SEAM-DENIED · zero SEAM-LEAK · zero SEAM-CANNOT-READ / GUARD-PROBE-FAILED · no other
#                               event line (SEAM-AMBIENT is allowed: ambient by construction, CONTRACT §3a) · truth.py
#                               exactly the clean `TOTAL ok=12 ...` line, no FLAG, exit 0 · plugin-dir ON: the run's ONE
#                               throwaway HOME (layout.py) holds a fire journal with lines from >= <number of ai steps>
#                               DISTINCT sessions whose plugin_src is THIS Harness tree (one fresh session per ai step).
#                               SEAM-DENIED-RULED lines (guard-ruled-denies.txt: cc-socks socket, fswatch probe; ruled
#                               2026-11-01) are allowed and counted: those writes STAY DENIED and the canary must still
#                               reach ok=12. Any other denial, or any ACTOR-READ/TOOL-DENIED line, fails it by name.
#     CAVEAT (ruled, stated on stdout, in the report and as the receipt's note <receipts>/actor-guard.note): the gate
#        trusts step files only because they sit in the actor's own $HOME/.claude; in real use the same holds under the
#        real ~/.claude.
#     3. receipt.sh write actor-guard <line>, written HERE after both stages have ended, whatever the outcome (a FAILED
#        line is a receipt too; it never matches the Verify). The line is exactly
#          ACTOR-GUARD ok=12 denied 0 leak 0 plugin-dir on writelist proven
#        only when everything above holds, else `ACTOR-GUARD FAILED: <what failed>`.
#        Refuses to start with SKILL_TESTER_RECEIPTS / SKILL_TESTER_RECEIPT_RIG / CLAUDE_BIN set, or inside a guarded run.
#   actor-guard.sh --selftest   FAKE actor only (probe-actor-writes-fixture/fake-actor.sh, which execs fake-claude.sh
#                               for canary steps): the judge on crafted runs, four end-to-end scenarios through the real
#                               run.sh --real path and the real guard, the refusals, and fail-first on broken copies.
#                               Last line `SELFTEST actor-guard <n>/<n> ALL OK`.
# Cost of the real run: probe cap $0.25 (1 call) + the canary on the small tier (8 ai steps, budget.sh default caps).
# Exit: 0 OK line · 1 FAILED line · 2 refused · 3 receipt not written. macOS bash 3.2, BSD tools, no set -e.
RIG="$(cd "$(dirname "$0")" && pwd)"
SELF="$RIG/$(basename "$0")"
CANON="$HOME/lifehack-scratch/skill-tester-rig"
OK_LINE="ACTOR-GUARD ok=12 denied 0 leak 0 plugin-dir on writelist proven"
CAVEAT="the gate trusts step files only because they sit in the actor's own \$HOME/.claude; in real use the same holds under the real ~/.claude"
CLEAN_TOTAL="TOTAL ok=12 silent_wrong=0 double_ran=0 stuck=0 lost=0 skipped=0 out_of_order=0 false_done=0"
ANS=( --answer s4=yes --answer s9=yes )

# judge <run-dir> <truth-out> <truth-rc> <run-rc> <actor-home> <plugin-dir> <writelist-line> <card>
# prints exactly one line: OK_LINE or `ACTOR-GUARD FAILED: <reasons>`. Pure: reads files, writes nothing.
judge() {
  python3 -I -B - "$@" "$OK_LINE" "$CLEAN_TOTAL" <<'PY'
import json, os, re, sys
rd, tout, trc, rrc, ahome, plugin, wl, card, okline, clean = sys.argv[1:11]
bad = []
if not wl.startswith("WRITELIST: PROVEN "):
    bad.append("writelist not proven (%s)" % (wl or "no probe line"))
def lines(p):
    try: return [l.rstrip("\n") for l in open(p, encoding="utf-8", errors="replace")]
    except OSError: return None
if rrc == "-":   # stage 2 was never run (the write list was not proven): name that alone, no stage-2 noise
    print("ACTOR-GUARD FAILED: " + " · ".join(bad + ["canary not run"])); sys.exit(0)
if rrc != "0": bad.append("run exit %s" % rrc)
meta = lines(os.path.join(rd, "meta.env"))
if meta is None: bad.append("no meta.env")
elif "SEAM_GUARD=on" not in meta: bad.append("guard not on (%s)" % ",".join(l for l in meta if l.startswith("SEAM_GUARD=")) or "no SEAM_GUARD line")
ev = lines(os.path.join(rd, "events.log"))
if ev is None: bad.append("no events.log"); ev = []
ev = [l for l in ev if l.strip()]
nden = sum(1 for l in ev if l.startswith("SEAM-DENIED "))
nleak = sum(1 for l in ev if l.startswith("SEAM-LEAK "))
if nden: bad.append("denied %d (%s)" % (nden, next(l for l in ev if l.startswith("SEAM-DENIED "))[12:]))
if nleak: bad.append("leak %d (%s)" % (nleak, next(l for l in ev if l.startswith("SEAM-LEAK "))[10:]))
nadn = sum(1 for l in ev if l.startswith(("ACTOR-READ-DENIED ", "ACTOR-TOOL-DENIED ")))
if nadn: bad.append("actor-denied %d (%s)" % (nadn, next(l for l in ev if l.startswith("ACTOR-"))))
other = [l for l in ev if not l.startswith(("SEAM-DENIED ", "SEAM-LEAK ", "SEAM-AMBIENT ", "SEAM-DENIED-RULED ",
                                            "ACTOR-READ-DENIED ", "ACTOR-TOOL-DENIED "))]
if other: bad.append("events %d (%s)" % (len(other), other[0]))
tl = lines(tout) or []
if trc != "0": bad.append("truth exit %s" % trc)
if clean not in tl: bad.append("truth %s" % (next((l for l in tl if l.startswith("TOTAL ")), "no TOTAL line")))
flags = [l for l in tl if l.startswith("FLAG")]
if flags: bad.append("truth %s" % flags[0])
# plugin-dir ON: the run's ONE throwaway HOME journalled hook exits from THIS Harness copy in >= one distinct session
# per ai step (every ai step is a fresh claude session; a cached copy's lines, plugin_src "root"/"path", never count)
ai = []
for l in lines(card) or []:
    m = re.match(r"^s(\d+) \| ai \|", l)
    if m: ai.append(m.group(1))
prp = os.path.realpath(plugin); sess = set()
for l in lines(os.path.join(ahome, ".claude", "run", "fire-journal.jsonl")) or []:
    try: j = json.loads(l)
    except ValueError: continue
    src = str(j.get("plugin_src", "") or "")
    if src.startswith("/") and os.path.realpath(src) == prp: sess.add(str(j.get("session_id", "")))
if not ai: bad.append("plugin-dir unknown (no ai steps in the card)")
elif len(sess) < len(ai): bad.append("plugin-dir off: %d/%d ai sessions journalled from this Harness copy" % (len(sess), len(ai)))
print(okline if not bad else "ACTOR-GUARD FAILED: " + " · ".join(bad))
PY
}

# orchestrate <real|test> <scratch-for-test-out> : runs both stages, prints evidence lines, the result line LAST
orchestrate() {
  local mode="$1" STAMP RUN_ID PLINE PRC RRC TRC RD AH RES OUTD PLUGIN
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  if [ "$mode" = real ]; then
    for v in SKILL_TESTER_RECEIPTS SKILL_TESTER_RECEIPT_RIG CLAUDE_BIN SKILL_TESTER_SCRATCH SKILL_TESTER_RIG PAW_OUT_ROOT PAW_PLUGIN_DIR PAW_TOKEN_FILE; do
      eval "vv=\${$v:-}"; [ -z "$vv" ] || { echo "actor-guard: REFUSED: $v is set; the real run writes the real 'actor-guard' receipt and refuses overrides" >&2; exit 2; }
    done
    RUN_ID="ag-$STAMP"; OUTD="$CANON/actor-guard/$STAMP"
  else
    RUN_ID="agst-$STAMP"; OUTD="$2/ag-$STAMP"
  fi
  [ -z "${RIG_GUARD_TAG:-}" ] || { echo "actor-guard: REFUSED: inside a guarded run (this is the unguarded orchestrator)" >&2; exit 2; }
  mkdir -p "$OUTD" || { echo "actor-guard: cannot create $OUTD" >&2; exit 2; }
  PLUGIN="$(cd "$RIG/../../.." && pwd -P)"
  echo "ACTOR-GUARD: run-id=$RUN_ID out=$OUTD plugin=$PLUGIN"
  # ── stage 1: the write-list census ──
  echo "== stage 1: probe-actor-writes.sh (census)"
  if [ "$mode" = test ]; then
    env FAKE_ACTOR_WRITES="${_AG_PROBE_WRITES:-}" bash "$RIG/probe-actor-writes.sh" > "$OUTD/probe.out" 2>&1; PRC=$?
  else
    bash "$RIG/probe-actor-writes.sh" > "$OUTD/probe.out" 2>&1; PRC=$?
  fi
  PLINE="$(tail -1 "$OUTD/probe.out")"
  grep -E '^(PROBE|ACTOR|WRITE|PATCH|⛔)' "$OUTD/probe.out" | sed 's/^/  | /'
  echo "  probe rc=$PRC: $PLINE"
  RRC="-"; TRC="-"; : > "$OUTD/truth.out"
  RD="$(python3 -I "$RIG/run_helper.py" rundir "$CANON" "$RUN_ID")"; AH="$(python3 -I "$RIG/run_helper.py" actorhome "$CANON" "$RUN_ID")"
  if [ "$PRC" = 0 ] && printf '%s' "$PLINE" | grep -q '^WRITELIST: PROVEN '; then
    # ── stage 2: one real canary run under the guard with the Harness loaded ──
    echo "== stage 2: run.sh --real --model-tier small --run-id $RUN_ID"
    if [ "$mode" = test ]; then
      env FAKE_ACTOR_WRITES="${_AG_CANARY_WRITES:-}" FAKE_ACTOR_JOURNAL="${_AG_CANARY_JOURNAL:-1}" \
        bash "$RIG/run.sh" --real --model-tier small --run-id "$RUN_ID" "${ANS[@]}" > "$OUTD/run.out" 2>&1; RRC=$?
    else
      bash "$RIG/run.sh" --real --model-tier small --run-id "$RUN_ID" "${ANS[@]}" > "$OUTD/run.out" 2>&1; RRC=$?
    fi
    python3 -B "$RIG/truth.py" --run "$RUN_ID" > "$OUTD/truth.out" 2>&1; TRC=$?
    echo "  run rc=$RRC; truth rc=$TRC: $(grep '^TOTAL' "$OUTD/truth.out" | tail -1)"
    [ -s "$RD/events.log" ] && sed 's/^/  | event: /' "$RD/events.log"
    echo "  cost: $(cat "$RD"/s*.raw.json 2>/dev/null | python3 -I -B -c '
import json, sys
c = t = 0; u = 0
for l in sys.stdin:
    l = l.strip()
    if not l.startswith("{"): continue
    try: j = json.loads(l)
    except ValueError: continue
    v = j.get("total_cost_usd")
    if isinstance(v, (int, float)): c += v
    else: u += 1
    t += j.get("num_turns", 0) if isinstance(j.get("num_turns"), int) else 0
print("total_cost_usd=%.4f num_turns=%d unknown_cost_steps=%d" % (c, t, u))')"
  else
    echo "== stage 2: NOT RUN (the write list is not proven; a ruling comes first, the guard is never widened here)"
  fi
  RES="$(judge "$RD" "$OUTD/truth.out" "$TRC" "$RRC" "$AH" "$PLUGIN" "$PLINE" "$RIG/canary/card.txt")"
  [ -n "$RES" ] || RES="ACTOR-GUARD FAILED: judge produced no line"
  printf '%s\n' "$RES" > "$OUTD/result.line"; printf 'CAVEAT: %s\n' "$CAVEAT" > "$OUTD/caveat.txt"
  echo "CAVEAT: $CAVEAT"
  [ -s "$RD/events.log" ] && grep -c '^SEAM-DENIED-RULED ' "$RD/events.log" | sed 's/^/  ruled denials (stayed denied, not blocking): /' 
  # ── receipt: HERE, unguarded, after both stages have ended, whatever the outcome ──
  if ! bash "$RIG/receipt.sh" write actor-guard "$RES" --note "CAVEAT: $CAVEAT" 1>&2; then echo "actor-guard: RECEIPT NOT WRITTEN for '$RES'" >&2; echo "$RES"; exit 3; fi
  echo "$RES"
  [ "$RES" = "$OK_LINE" ] && exit 0
  exit 1
}

# ───────────────────────────────────────── selftest (FAKE actor only) ─────────────────────────────────────────
FX="$RIG/probe-actor-writes-fixture/fake-actor.sh"
# crafted run for the judge: st_craft <dir> -> <dir>/run, <dir>/truth.out, <dir>/ahome (ONE journal, 8 sessions), clean
st_craft() {
  local D="$1" n
  rm -rf "$D"; mkdir -p "$D/run" "$D/ahome/.claude/run"
  printf 'RUN_ID=x\nSEAM_GUARD=on\n' > "$D/run/meta.env"; : > "$D/run/events.log"
  { for n in 1 2 3 4 5 6 7 8 9 10 11 12; do echo "s$n ok"; done; echo "$CLEAN_TOTAL"; } > "$D/truth.out"
  for n in 2 3 5 6 8 10 11 12; do
    printf '{"ts":1,"hook":"h","decision":"allow","session_id":"sess-s%s","plugin_src":"%s"}\n' "$n" "$(cd "$RIG/../../.." && pwd -P)" >> "$D/ahome/.claude/run/fire-journal.jsonl"
  done
}
st_judge() {  # the judge on crafted runs; prints ok/FAIL lines; returns the number of failures
  local B="$1" f=0 got P WL="WRITELIST: PROVEN a=5 b=0 c=0"
  P="$(cd "$RIG/../../.." && pwd -P)"
  j() {  # j <label> <want-regex> [rrc] [trc] [wl]
    got="$(judge "$B/j/run" "$B/j/truth.out" "${4:-0}" "${3:-0}" "$B/j/ahome" "$P" "${5:-$WL}" "$RIG/canary/card.txt")"
    if printf '%s' "$got" | grep -qE "$2"; then echo "  ok   judge $1 → $got"; else echo "  FAIL judge $1 → '$got' want /$2/"; f=$((f+1)); fi
  }
  st_craft "$B/j"; j clean "^$OK_LINE\$"
  st_craft "$B/j"; echo "SEAM-DENIED /Users/x/.claude.json" >> "$B/j/run/events.log"; j denied '^ACTOR-GUARD FAILED: denied 1 \(/Users/x/.claude.json\)$'
  st_craft "$B/j"; printf 'SEAM-LEAK ADDED\t/s/x\n' >> "$B/j/run/events.log"; j leak '^ACTOR-GUARD FAILED: leak 1 '
  st_craft "$B/j"; printf 'SEAM-AMBIENT CHANGED\t/s/x\n' >> "$B/j/run/events.log"; j ambient-allowed "^$OK_LINE\$"
  st_craft "$B/j"; echo "SEAM-CANNOT-READ denials" >> "$B/j/run/events.log"; j cannot-read '^ACTOR-GUARD FAILED: events 1 \(SEAM-CANNOT-READ denials\)$'
  st_craft "$B/j"; sed -i '' "s/^TOTAL ok=12/TOTAL ok=11/" "$B/j/truth.out"; j truth-11 '^ACTOR-GUARD FAILED: truth TOTAL ok=11'
  st_craft "$B/j"; echo "FLAG second-copy x" >> "$B/j/truth.out"; j truth-flag '^ACTOR-GUARD FAILED: truth FLAG second-copy x$'
  st_craft "$B/j"; sed -i '' '/sess-s8/d' "$B/j/ahome/.claude/run/fire-journal.jsonl"; j plugin-off-s8 '^ACTOR-GUARD FAILED: plugin-dir off: 7/8 ai sessions journalled from this Harness copy$'
  st_craft "$B/j"; sed -i '' '/sess-s2/s#"plugin_src":"[^"]*"#"plugin_src":"root"#' "$B/j/ahome/.claude/run/fire-journal.jsonl"; j plugin-cached-copy '^ACTOR-GUARD FAILED: plugin-dir off: 7/8 ai sessions journalled from this Harness copy$'
  st_craft "$B/j"; echo "SEAM-DENIED-RULED /x/cc-socks/42.sock" >> "$B/j/run/events.log"; j ruled-denied-allowed "^$OK_LINE\$"
  st_craft "$B/j"; echo "ACTOR-READ-DENIED s5 /h/.claude/projects/p/x.jsonl" >> "$B/j/run/events.log"; j actor-read-denied '^ACTOR-GUARD FAILED: actor-denied 1 \(ACTOR-READ-DENIED s5 /h/.claude/projects/p/x.jsonl\)$'
  st_craft "$B/j"; printf 'RUN_ID=x\nSEAM_GUARD=off:sandbox-unavailable\n' > "$B/j/run/meta.env"; j guard-off '^ACTOR-GUARD FAILED: guard not on \(SEAM_GUARD=off:sandbox-unavailable\)$'
  st_craft "$B/j"; j run-rc '^ACTOR-GUARD FAILED: run exit 1$' 1
  st_craft "$B/j"; j writelist '^ACTOR-GUARD FAILED: writelist not proven \(WRITELIST: NEEDS-RULING a=2 b=1 c=0 patch=x\)$' 0 0 "WRITELIST: NEEDS-RULING a=2 b=1 c=0 patch=x"
  return $f
}
selftest() {
  local B fails=0 n=0 out rc last rl real_rc
  [ -x "$FX" ] || { echo "SELFTEST actor-guard FAILED: no fixture $FX"; exit 1; }
  B="$CANON/selftest/actor-guard-$(date -u +%Y%m%dT%H%M%SZ)-$$"; mkdir -p "$B/receipts" "$B/probe" || exit 1
  printf 'fake-token\n' > "$B/token"
  echo "SELFTEST actor-guard (FAKE actor; base $B)"
  echo "-- judge on crafted runs"
  st_judge "$B"; rc=$?; n=$((n+14)); fails=$((fails+rc))
  echo "-- end to end: FAKE actor through the real run.sh --real path and the real write guard"
  e2e() {  # e2e <label> <want-last-regex> <want-rc> [env assignments...]
    local label="$1" want="$2" wrc="$3"; shift 3
    n=$((n+1))
    out="$(env "$@" CLAUDE_BIN="$FX" SKILL_TESTER_RECEIPTS="$B/receipts" PAW_OUT_ROOT="$B/probe" PAW_TOKEN_FILE="$B/token" \
          PAW_PLUGIN_DIR="$(cd "$RIG/../../.." && pwd -P)" FAKE_ACTOR_REAL_HOME="$HOME" \
          bash "$SELF" --selftest-run "$B" 2>&1)"; rc=$?
    last="$(printf '%s\n' "$out" | tail -1)"; rl="$(head -1 "$B/receipts/actor-guard.receipt" 2>/dev/null)"
    E2E_OUT="$out"
    if [ "$rc" = "$wrc" ] && printf '%s' "$last" | grep -qE "$want" && [ "$rl" = "$last" ]; then echo "  ok   e2e $label (rc $rc; receipt line 1 = result) → $last"
    else echo "  FAIL e2e $label (rc $rc want $wrc; receipt '$rl') → $last"; printf '%s\n' "$out" | tail -12 | sed 's/^/       | /'; fails=$((fails+1)); fi
  }
  e2e clean "^$OK_LINE\$" 0
  e2e writelist-needs-ruling '^ACTOR-GUARD FAILED: writelist not proven \(WRITELIST: NEEDS-RULING a=[0-9]+ b=1 c=0 patch=[^)]*\) · canary not run$' 1 _AG_PROBE_WRITES=@systmp
  n=$((n+1)); if printf '%s\n' "$E2E_OUT" | grep -q '^== stage 2: NOT RUN'; then echo "  ok   stage 2 not run when the write list is not proven"; else echo "  FAIL stage 2 ran on an unproven write list"; fails=$((fails+1)); fi
  local OUTSIDE="$HOME/lifehack-scratch/.actor-guard-selftest-denied-$$"
  e2e canary-denied "^ACTOR-GUARD FAILED: .*denied 1 \\($(cd "$HOME/lifehack-scratch" && pwd -P)/\\.actor-guard-selftest-denied-$$\\)" 1 _AG_CANARY_WRITES="$OUTSIDE"
  n=$((n+1)); if [ ! -e "$OUTSIDE" ]; then echo "  ok   the canary's write outside scratch did not land"; else rm -f "$OUTSIDE"; echo "  FAIL the canary's write outside scratch LANDED"; fails=$((fails+1)); fi
  e2e plugin-off '^ACTOR-GUARD FAILED: plugin-dir off: 0/8 ai sessions ' 1 _AG_CANARY_JOURNAL=0
  # the RULED denials (cc-socks socket, fswatch probe) stay denied and the canary still reaches ok=12 (ruling 2026-11-01)
  local RULED_W="/private/tmp/claude-$(id -u)/fswatch-probe-agst$$"   # allow-silence: deliberate denied-write target named by the TR2.0b ruling; asserted never to land
  e2e ruled-denied-still-ok "^$OK_LINE\$" 0 _AG_CANARY_WRITES="$RULED_W"
  n=$((n+1)); if printf '%s\n' "$E2E_OUT" | grep -qE "^  \| event: SEAM-DENIED-RULED $RULED_W\$" && [ ! -e "$RULED_W" ]; then echo "  ok   the ruled write was denied (did not land) and named SEAM-DENIED-RULED"
  else rm -f "$RULED_W"; echo "  FAIL the ruled write was not named SEAM-DENIED-RULED, or it landed"; fails=$((fails+1)); fi
  n=$((n+1)); if [ "$(cat "$B/receipts/actor-guard.note" 2>/dev/null)" = "CAVEAT: $CAVEAT" ]; then echo "  ok   the receipt's note carries the gate caveat"
  else echo "  FAIL the receipt note lacks the caveat"; fails=$((fails+1)); fi
  echo "-- refusals (real mode)"
  local v
  # SAFETY: should a refusal ever break, the fall-through can launch nothing: PATH holds no claude and the variable
  # points at a non-executable path inside this selftest's base (the probe would stop at CANNOT-RUN no-claude-binary)
  for v in SKILL_TESTER_RECEIPTS SKILL_TESTER_RECEIPT_RIG CLAUDE_BIN; do
    n=$((n+1))
    out="$(env PATH=/usr/bin:/bin:/usr/sbin:/sbin "$v=$B/refusal-not-a-binary" bash "$SELF" 2>&1)"; real_rc=$?
    if [ "$real_rc" = 2 ] && printf '%s' "$out" | grep -q "REFUSED: $v is set"; then echo "  ok   real mode refuses $v"; else echo "  FAIL real mode with $v set: rc $real_rc"; fails=$((fails+1)); fi
  done
  echo "-- fail-first: broken copies of the judge must fail the crafted cases"
  ffj() {  # ffj <label> <sed-expr>
    local C="$B/ff-$1"; n=$((n+1))
    rm -rf "$C"; mkdir -p "$C/system/tools/skill-tester-rig"; cp -Rp "$RIG/." "$C/system/tools/skill-tester-rig/"
    find "$C" -name __pycache__ -prune -exec rm -rf {} +
    sed -i '' "$2" "$C/system/tools/skill-tester-rig/actor-guard.sh"
    if cmp -s "$SELF" "$C/system/tools/skill-tester-rig/actor-guard.sh"; then echo "  FAIL ff-$1: the break did not apply"; fails=$((fails+1)); return; fi
    if bash "$C/system/tools/skill-tester-rig/actor-guard.sh" --selftest-judge "$B/ff-$1-run" > "$B/ff-$1.log" 2>&1; then
      echo "  FAIL ff-$1: the broken judge PASSED every crafted case"; fails=$((fails+1))
    else echo "  ok   ff-$1: broken judge FAILED as it must ($(grep -m1 '  FAIL' "$B/ff-$1.log" | cut -c1-100))"; fi
    rm -rf "$C"
  }
  ffj no-denied-count 's/^if nden: bad.append/if False: bad.append/'
  ffj no-plugin-check 's/^elif len(sess) < len(ai): bad.append/elif False: bad.append/'
  ffj ruled-swallows-denied 's/^nden = sum(1 for l in ev if l.startswith("SEAM-DENIED "))/nden = 0/'
  if [ "$fails" = 0 ]; then echo "SELFTEST actor-guard $n/$n ALL OK"; exit 0; fi
  echo "SELFTEST actor-guard FAILED ($fails/$n)"; exit 1
}

case "${1:-}" in
  "") orchestrate real ;;
  --selftest) selftest ;;
  --selftest-run)   # internal (selftest e2e only): test mode needs the FAKE actor and a selftest receipts dir
    [ "${CLAUDE_BIN:-}" = "$FX" ] || { echo "actor-guard: --selftest-run needs CLAUDE_BIN=$FX (the fake)" >&2; exit 2; }
    case "${SKILL_TESTER_RECEIPTS:-}" in "$CANON"/selftest/*) ;; *) echo "actor-guard: --selftest-run needs SKILL_TESTER_RECEIPTS under $CANON/selftest" >&2; exit 2 ;; esac
    orchestrate test "${2:?}" ;;
  --selftest-judge) [ -n "${2:-}" ] || exit 2; mkdir -p "$2"; st_judge "$2"; [ $? = 0 ] ;;
  *) echo "usage: actor-guard.sh [--selftest]" >&2; exit 2 ;;
esac
