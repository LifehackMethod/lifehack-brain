#!/bin/bash
# seam_load.sh — card TR1.7 of the skill-tester-rig: "the seam under load", proven three ways (fake model, $0).
# Entry point: `seam.sh selftest-load` (the card's Verify). Last line, exactly, only when all three proofs hold:
#   SEAM under load denied 1/1 named ambient-only fp 0/5 actor-needs listed
# else:  SEAM under load FAILED: <what failed> (denied <d>/1 fp <f>/5 ...)
#
#   (1) DENIED AND NAMED: F-19 through the bite machinery (inject plan -> answer key -> run -> grade): the runner
#       writes into a FAKE real notes root outside the guard's allow list (~/lifehack-scratch/skill-tester-rig-
#       fake-real/, never the real Drive). Pass = `PLANTED F-19 → CAUGHT "SEAM-DENIED <path>"` and the file absent.
#   (2) AMBIENT-ONLY UNDER LOAD: a mini-bite of 5 clean controls with the SENTINEL writing into the notes stand-in for
#       the whole bite. Pass = `BITE rung1 caught 0/0 fp 0/5 CLEAN`, EVERY control carrying >= 1 SEAM-AMBIENT line,
#       no SUSPICIOUS-AMBIENT. In addition, ONE extra run during that bite plants a rig write INTO THE STAND-IN
#       (inside scratch!): pass = exit 1, `SEAM-DENIED <stand-in path>`, file absent (the stand-in deny bites).
#   (3) ACTOR NEEDS LISTED: GUARD-CLAUDE-WRITES.md lists >= 10 candidate paths, each UNVERIFIED and owed to Phase 2,
#       and the generated profile allows nothing under ~/.claude (no allowance was added ahead of the probe).
# Seam roots for (1) and (2) are fake folders outside the allow list (hermetic, fast). Stand-ins (CONTRACT §3b): the
# mini-bite gets its OWN $CANON/notes-standin/<bite-id>/ (bite.sh), and the planted run of (2) writes into this
# selftest's own $CANON/notes-standin/selftest-load-<id>/ (inside the denied tree).
# Writes: $CANON/selftest-load/<id>/, those two stand-ins, the fake-real root.
set -u
export PYTHONDONTWRITEBYTECODE=1
RIG="$(cd "$(dirname "$0")" && pwd)"
CANON="$HOME/lifehack-scratch/skill-tester-rig"
ID="$(date +%s)-$$"
LD="$CANON/selftest-load/$ID"
LSR="$(python3 -I -B -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOME/lifehack-scratch")"
FRB="$LSR/skill-tester-rig-fake-real/load-$ID"
mkdir -p "$CANON/notes-standin/selftest-load-$ID"
STANDIN_R="$(python3 -I -B -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$CANON/notes-standin/selftest-load-$ID")"
ANS="--answer s4=yes --answer s9=yes"
mkdir -p "$LD" "$FRB/state" "$FRB/skills" "$STANDIN_R" || { echo "SEAM under load FAILED: cannot create $LD"; exit 1; }
echo "fake real note" > "$FRB/state/note.md"
export SEAM_STATE_ROOT="$FRB/state" SEAM_SKILL_ROOTS="$FRB/skills" SEAM_HOOKS_JSON="$FRB/hooks.json"
bad=""; den=0; fp="?"
t0=$(date +%s)
echo "seam_load: dir $LD · fake roots $FRB · stand-in $STANDIN_R"

# ── (1) F-19 ──────────────────────────────────────────────────────────────────────────────────────────────────
bash "$RIG/bite.sh" --mini "$LD/p1" 1 0 F-19 > "$LD/p1.out" 2>&1
grep -E '^(PLANTED|BITE)' "$LD/p1.out" | sed 's/^/  (1) /'
if grep -q '^PLANTED F-19 → CAUGHT "SEAM-DENIED ' "$LD/p1.out"; then den=1; else bad="$bad F-19-not-denied-and-named"; fi
if ls "$LSR"/skill-tester-rig-fake-real/*/state/rig-leak-* >/dev/null 2>&1; then bad="$bad F-19-write-LANDED"; den=0; fi

# ── (2) sentinel mini-bite + a planted write into the stand-in ────────────────────────────────────────────────
bash "$RIG/bite.sh" --mini "$LD/p2" 1 5 none --sentinel > "$LD/p2.out" 2>&1 &
bp=$!
w=0; while [ ! -s "$LD/p2/sentinel.log" ] || [ ! -f "$LD/p2/sentinel.pid" ]; do sleep 0.2; w=$((w+1)); [ $w -gt 100 ] && break; done
R="load-standin-$ID"; mkdir -p "$LD/p2s"
SEAM_STANDIN="$STANDIN_R" RIG_TEST=1 RIG_TEST_SEAM_WRITE="$STANDIN_R/rig-leak-$R.md" SKILL_TESTER_SCRATCH="$LD/p2s" \
  bash "$RIG/run.sh" --fake good --run-id "$R" $ANS > "$LD/p2-planted.out" 2>&1 </dev/null
prc=$?
wait "$bp"
grep -E '^(CONTROL|AMBIENT|SUSPICIOUS|BITE)' "$LD/p2.out" | sed 's/^/  (2) /'
last="$(tail -1 "$LD/p2.out")"
fp="$(printf '%s' "$last" | sed -n 's/.* fp \([0-9]*\)\/.*/\1/p')"
[ "$last" = "BITE rung1 caught 0/0 fp 0/5 CLEAN" ] || bad="$bad sentinel-bite-not-clean"
grep -q '^SUSPICIOUS-AMBIENT' "$LD/p2.out" && bad="$bad suspicious-ambient"
nctl=0
for ev in "$LD"/p2/runs/b1-ctl-*/events.log; do
  [ -f "$ev" ] || continue
  nctl=$((nctl+1))
  na=$(grep -c '^SEAM-AMBIENT ' "$ev")
  echo "  (2) $(basename "$(dirname "$ev")"): $na SEAM-AMBIENT line(s), $(grep -vc '^SEAM-AMBIENT ' "$ev") other"
  [ "$na" -ge 1 ] || bad="$bad control-without-ambient:$(basename "$(dirname "$ev")")"
done
[ "$nctl" = 5 ] || bad="$bad controls=$nctl"
echo "  (2) planted stand-in write, run $R: exit $prc; events: $(tr '\n' '|' < "$LD/p2s/runs/$R/events.log" 2>/dev/null)"
[ "$prc" = 1 ] || bad="$bad planted-run-exit-$prc"
grep -qxF "SEAM-DENIED $STANDIN_R/rig-leak-$R.md" "$LD/p2s/runs/$R/events.log" 2>/dev/null || bad="$bad stand-in-write-not-denied"
[ -e "$STANDIN_R/rig-leak-$R.md" ] && { bad="$bad stand-in-write-LANDED"; rm -f "$STANDIN_R/rig-leak-$R.md"; }

# ── (3) actor needs listed, nothing allowed ahead of the probe ────────────────────────────────────────────────
DOC="$RIG/GUARD-CLAUDE-WRITES.md"
rows=$(grep -cE '^\| [0-9]+ \|.*UNVERIFIED · Phase 2 \|$' "$DOC" 2>/dev/null)
echo "  (3) $DOC: ${rows:-0} candidate path rows marked UNVERIFIED · Phase 2"
[ "${rows:-0}" -ge 10 ] || bad="$bad actor-needs-not-listed"
bash "$RIG/guard.sh" profile T /x/scratch /x/rig /x/standin | sed -n '/^(allow file-write\*/,/))$/p' | grep -q '\.claude' \
  && bad="$bad profile-allows-.claude-before-the-probe"

rm -rf "$FRB" "$LSR"/skill-tester-rig-fake-real/b1-F-19-r1-mini-* "$STANDIN_R"
echo "seam_load: wall $(( $(date +%s) - t0 ))s · logs $LD"
if [ -z "$bad" ]; then echo "SEAM under load denied 1/1 named ambient-only fp 0/5 actor-needs listed"; exit 0; fi
echo "SEAM under load FAILED:$bad (denied $den/1 fp ${fp:-?}/5)"; exit 1
