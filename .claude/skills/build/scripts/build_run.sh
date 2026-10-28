#!/bin/bash
# build_run.sh <plan.md> [--run-id R] [--answer yes|no] [--record PATH] [--artifact PATH]
# (no set -e: a failing command must be RECORDED, never abort silently)
#
# LLM CONTEXT
# WHY: the "build nurse" - walks a plan's open cards in order and makes "done" a read-back, not a claim.
#   Per card: AI builder writes the files, then the RUNNER (not the AI) runs the card's Verify and
#   compares the last stdout line to the expected value exactly, then Door 2 (conform.py on Where:).
#   Door 1 (before the first card) asks whether this is a card job at all; Door 3 (after the last)
#   conforms the finished artifact. Checkpoint cards and Door 1 pause for Enver (exit 70, --answer).
# GUARDS: only this runner writes the record (record.tsv: run_id ts step status detail; first line of a
#   run carries ccv=). A record whose last byte is not a newline is refused (exit 4). Door 1 output must
#   match SCOPE=<card|normal-skill|not-applicable> REASON=<text> or the run fails. Builder prompt never
#   names the record, and the builder gets no Bash. Verify exit code alone is never trusted: content is.
#   ORD-4 is declared in conform.decl: the builder must write the card's Where: files.
# FAIL_POSTURE: closed. Any external command that fails is recorded with its rc; unparseable or empty
#   means failed. Exit: 0 done | 1 failed/refused | 2 usage | 4 unreadable/truncated record or plan_queue
#   error | 70 waiting for a human answer.
# SIGNPOST: plan_queue.py (same folder) gives the cards; system/tools/conform.py is Door 2/3; test with
#   BUILD_AI_CMD=<stub>; BUILD_RUN_HOME, BUILD_MODEL, BUILD_CONFORM override defaults. Where: path = its
#   first token, backticks stripped, ~ expanded.

HERE="$(cd "$(dirname "$0")" && pwd)"
AI="${BUILD_AI_CMD:-claude}"
MODEL="${BUILD_MODEL:-sonnet}"
CONFORM="${BUILD_CONFORM:-$HERE/../../../../system/tools/conform.py}"
PLAN=""; RUN_ID=""; ANSWER=""; HAVE_ANSWER=0; RECORD=""; ARTIFACT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2 ;;
    --answer) ANSWER="$2"; HAVE_ANSWER=1; shift 2 ;;
    --record) RECORD="$2"; shift 2 ;;
    --artifact) ARTIFACT="$2"; shift 2 ;;
    *) PLAN="$1"; shift ;;
  esac
done
case "$ANSWER" in yes|no) ;; "") [ "$HAVE_ANSWER" = 0 ] || { echo "build_run: --answer needs yes or no" >&2; exit 2; } ;;
  *) echo "build_run: --answer must be yes or no, got '$ANSWER'" >&2; exit 2 ;; esac
[ -f "$PLAN" ] || { echo "build_run: plan not found: $PLAN" >&2; exit 2; }
PLAN="$(cd "$(dirname "$PLAN")" && pwd)/$(basename "$PLAN")"
[ -n "$RUN_ID" ] || { RUN_ID="$(basename "$PLAN")"; RUN_ID="${RUN_ID%.md}"; }
[ -n "$RECORD" ] || RECORD="${BUILD_RUN_HOME:-$HOME/.claude/run/build}/$RUN_ID/record.tsv"
mkdir -p "$(dirname "$RECORD")" || { echo "build_run: cannot create record dir" >&2; exit 4; }

# Guard: refuse a truncated record (last byte must be a newline) before anything resumes.
if [ -s "$RECORD" ] && [ "$(tail -c 1 "$RECORD" | od -An -c | tr -d ' ')" != '\n' ]; then
  echo "build_run: RECORD TRUNCATED (last byte not a newline): $RECORD - refusing to resume" >&2; exit 4
fi

rec() {  # step status detail
  local d="${3//[$'\t\n\r']/ }"
  printf '%s\t%s\t%s\t%s\t%s\n' "$RUN_ID" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "$d" >> "$RECORD"
}
has() {  # step status : does the record hold it for this run?
  [ -f "$RECORD" ] && awk -F'\t' -v r="$RUN_ID" -v s="$1" -v t="$2" '$1==r && $3==s && $4==t {f=1} END{exit !f}' "$RECORD"
}
detail() {  # step status : detail of the last such line
  awk -F'\t' -v r="$RUN_ID" -v s="$1" -v t="$2" '$1==r && $3==s && $4==t {d=$5} END{print d}' "$RECORD"
}
loud() { printf '\n==== %s ====\n' "$*" >&2; }
trim() { printf '%s' "$1" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }

# Run start: record the claude version (ccv=) - a failure to get it is recorded, not hidden.
ccvout="$(claude --version)"; ccvrc=$?
ccv="$(printf '%s' "$ccvout" | head -n 1 | awk '{print $1}')"
[ "$ccvrc" -eq 0 ] && [ -n "$ccv" ] || ccv="missing-rc$ccvrc"
rec run start "ccv=$ccv"

# Step 0: the queue. plan_queue failing means no run.
Q="$(mktemp -d)" || { echo "build_run: mktemp failed" >&2; exit 4; }
trap '[ -n "$Q" ] && [ -d "$Q" ] && rm -rf -- "$Q"' EXIT
python3 "$HERE/plan_queue.py" "$PLAN" --json > "$Q/out.txt" 2> "$Q/err.txt"; qrc=$?
if [ "$qrc" -ne 0 ]; then
  rec queue failed "plan_queue rc=$qrc $(head -c 200 "$Q/err.txt") $(head -c 200 "$Q/out.txt")"
  loud "plan_queue failed rc=$qrc"; cat "$Q/err.txt" "$Q/out.txt" >&2; exit 4
fi
grep '^WEAK ' "$Q/out.txt" | while IFS= read -r w; do echo "$w" >&2; done
python3 - "$Q" <<'PY'
import json, sys, os
q = sys.argv[1]
raw = open(os.path.join(q, "out.txt")).read()
data = json.loads(raw[raw.index("{"):])
w = lambda n, s: open(os.path.join(q, n), "w").write(str(s))
w("n", len(data["cards"])); w("weak", "\n".join("%s %s" % (x["id"], x["reason"]) for x in data["weak"]))
for i, c in enumerate(data["cards"]):
    for k in ("id", "title", "where", "do"):
        w("%d.%s" % (i, k), c[k].strip().lstrip("`").strip())
    w("%d.cp" % i, "1" if c["checkpoint"] else "0"); w("%d.nv" % i, len(c["verify"]))
    for j, v in enumerate(c["verify"]):
        e = v["expect"] if isinstance(v["expect"], list) else ["none", ""]
        w("%d.v%d.cmd" % (i, j), v["cmd"]); w("%d.v%d.kind" % (i, j), e[0]); w("%d.v%d.exp" % (i, j), e[1])
PY
[ $? -eq 0 ] && [ -s "$Q/n" ] || { rec queue failed "queue json unreadable"; echo "build_run: queue JSON unreadable" >&2; exit 4; }
if [ -s "$Q/weak" ]; then rec weak warn "$(tr '\n' ';' < "$Q/weak")"; fi
N="$(cat "$Q/n")"

# Human-pause protocol, used by Door 1 and checkpoint cards. Returns 0 = passed now, exits otherwise.
pause() {  # step what
  local step="$1" what="$2"
  if has "$step" passed; then return 0; fi
  if has "$step" refused; then loud "$step was refused earlier"; exit 1; fi
  if [ "$HAVE_ANSWER" = 1 ] && has "$step" waiting; then
    HAVE_ANSWER=0   # consumed by the first waiting step only
    if [ "$ANSWER" = yes ]; then rec "$step" passed "answer=yes"; return 0; fi
    rec "$step" refused "answer=no"; loud "$step refused by answer=no"; exit 1
  fi
  has "$step" waiting || rec "$step" waiting "$what"
  loud "WAITING FOR ENVER at $step: $what"
  echo "Answer with: build_run.sh $PLAN --run-id $RUN_ID --answer yes|no" >&2; exit 70
}

# Door 1 (design): once per run, before the first card.
if ! has door1 passed; then
  if ! has door1 waiting && ! has door1 refused; then
    d1prompt="Read the plan at $PLAN. Decide how it should be built, using this rule. A CARD (runner + record) only if step order must hold AND (losing progress costs real time or money, OR a human pauses mid-run, OR it spans sessions, OR it has more than one ai step). A short job you can rerun from scratch is a NORMAL SKILL with per-step checks. Documents, research and design are NOT-APPLICABLE. Answer with EXACTLY one line and nothing else: SCOPE=<card|normal-skill|not-applicable> REASON=<one sentence>"
    d1out="$($AI -p "$d1prompt" --model "$MODEL" --allowedTools Read)"; d1rc=$?
    d1line="$(printf '%s\n' "$d1out" | grep -E '^SCOPE=(card|normal-skill|not-applicable) REASON=.+$' | head -n 1)"
    if [ "$d1rc" -ne 0 ] || [ -z "$d1line" ]; then
      rec door1 failed "rc=$d1rc unparseable: $(printf '%s' "$d1out" | head -c 200)"
      loud "door1 failed: ai answer was not SCOPE=... REASON=... (rc=$d1rc)"; exit 1
    fi
    scope="${d1line#SCOPE=}"; scope="${scope%% REASON=*}"; reason="${d1line#* REASON=}"
    rec door1 waiting "$scope $reason"
  fi
  pause door1 "$(detail door1 waiting)"
fi

# Each card in order.
i=0
while [ "$i" -lt "$N" ]; do
  id="$(cat "$Q/$i.id")"; title="$(cat "$Q/$i.title")"; where="$(cat "$Q/$i.where")"
  if has "$id" passed; then echo "skip $id (already passed)" >&2; i=$((i+1)); continue; fi
  if [ "$(cat "$Q/$i.cp")" = 1 ]; then pause "$id" "checkpoint: $title"; i=$((i+1)); continue; fi
  bprompt="You are the builder for plan card $id: $title. Plan (for context only): $PLAN. Where: $where. Do: $(cat "$Q/$i.do"). Write or edit only the files named in Where. You cannot run commands; the runner verifies afterwards. When finished, end your reply with exactly one line: BUILT $id"
  bout="$($AI -p "$bprompt" --model "$MODEL" --allowedTools Read,Write,Edit,Glob,Grep)"; brc=$?
  if [ "$brc" -ne 0 ] || ! printf '%s\n' "$bout" | grep -qx "BUILT $id"; then
    rec "$id" failed "builder rc=$brc no 'BUILT $id' line: $(printf '%s' "$bout" | tail -c 200)"
    loud "$id failed: builder rc=$brc or missing BUILT line"; exit 1
  fi
  nv="$(cat "$Q/$i.nv")"
  if [ "$nv" -eq 0 ]; then rec "$id" failed "no runnable Verify"; loud "$id failed: no runnable Verify"; exit 1; fi
  j=0
  while [ "$j" -lt "$nv" ]; do
    vcmd="$(cat "$Q/$i.v$j.cmd")"; want="$(trim "$(cat "$Q/$i.v$j.exp")")"
    vout="$(bash -c "$vcmd" </dev/null)"; vrc=$?
    got="$(trim "$(printf '%s\n' "$vout" | tail -n 1)")"
    kind="$(cat "$Q/$i.v$j.kind")"; ok=0
    case "$kind" in
      bare)   [ "$got" = "$want" ] && ok=1 ;;
      exit)   [ "$vrc" = "$want" ] && ok=1 ;;
      substr) case "$got" in *"$want"*) ok=1 ;; esac ;;
      ge)     [[ "$got" =~ ^-?[0-9]+$ ]] && [ "$got" -ge "$want" ] && ok=1 ;;
      le)     [[ "$got" =~ ^-?[0-9]+$ ]] && [ "$got" -le "$want" ] && ok=1 ;;
    esac
    if [ "$ok" -ne 1 ]; then
      rec "$id" failed "got=$got want=$want kind=$kind vrc=$vrc"; loud "$id VERIFY MISMATCH got='$got' want='$want' kind=$kind (rc=$vrc)"; exit 1
    fi
    j=$((j+1))
  done
  wpath="${where%%[[:space:]]*}"; wpath="${wpath//\`/}"; wpath="${wpath%,}"; wpath="${wpath/#\~/$HOME}"
  cout="$(python3 "$CONFORM" "$wpath" --plan "$PLAN")"; crc=$?
  case "$crc" in
    0) rec "$id" passed "door2=PASS" ;;
    3) rec "$id" passed "door2=N/A" ;;
    *) first="$(printf '%s\n' "$cout" | grep -m1 '^FAIL')"
       rec "$id" failed "door2=FAIL rc=$crc ${first:-$(printf '%s' "$cout" | tail -n 1)}"
       loud "$id DOOR 2 failed rc=$crc: ${first:-no FAIL line}"; exit 1 ;;
  esac
  i=$((i+1))
done

# Door 3 (finished): conform the whole artifact.
if [ -z "$ARTIFACT" ]; then ARTIFACT="$(grep -m1 -E '^[[:space:]-]*Artifact:' "$PLAN" | sed -E 's/^[[:space:]-]*Artifact:[[:space:]]*//; s/`//g')"; fi
if [ -z "$ARTIFACT" ]; then rec door3 failed "door3 needs an artifact path"; loud "door3 needs an artifact path (--artifact or plan line 'Artifact: <path>')"; exit 1; fi
ARTIFACT="${ARTIFACT/#\~/$HOME}"
cout="$(python3 "$CONFORM" "$ARTIFACT" --plan "$PLAN")"; crc=$?
verdict="$(printf '%s\n' "$cout" | grep -o 'verdict=[A-Z/]*' | tail -n 1)"
case "$crc:$verdict" in
  0:verdict=PASS) v=PASS ;;
  3:verdict=N/A)  v="N/A" ;;
  *) v=FAIL ;;
esac
if [ "$v" = "N/A" ] && [ "$(detail door1 waiting | awk '{print $1}')" != "not-applicable" ]; then v=FAIL; fi
rec door3 "$v" "door3 verdict=$v rc=$crc artifact=$ARTIFACT"
loud "door3 verdict=$v"
if [ "$v" = PASS ] || [ "$v" = "N/A" ]; then rec build done "all $N cards"; exit 0; fi
exit 1
