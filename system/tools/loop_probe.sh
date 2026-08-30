#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the operator's question, 2026-07-28 — "prove that a plan can be built, and as it is built the inputs
#      from that plan recursively find their way BACK into the plan, so instead of a delta between the
#      plan and real life, the plan gets sharpened as it works."
#      Detection ("can it SPOT a conflict") was already shown. This probes the FULL loop:
#         read reality -> discover what the plan does not know -> WRITE IT BACK -> plan is now accurate.
#      The measurement is mechanical, not a judgement: a fact that reality has and the plan lacks is
#      either present in the plan afterwards or it is not.
#
# HOW IT MEASURES:
#   STALE half   — plan.md is missing the three blocking gates the brief's SCRATCHPAD names.
#                  PASS = after one loop pass, all three gate terms appear in the plan.
#   IN-SYNC half — plan.md has already absorbed them (it IS the known-correct output of sharpening
#                  stale). PASS = the loop reports NO TENSIONS and proposes no change.
#                  This is the CONTROL. A flip here VOIDS the run (skill-building-sop §V.4a) — a
#                  detector that flags everything aces the stale half and is worthless.
#
# GUARDS: read-only against the real corpus. Works on a COPY in a temp dir; the fixtures are never
#         mutated. The model is asked to EMIT the corrected plan on stdout — it is NEVER granted write
#         access, so no --dangerously-skip-permissions is required anywhere in this probe.
# FAIL_POSTURE: any error -> non-zero exit + loud message. Never silently reports a pass.
# UPDATED: 2026-07-28 (new)
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
FIX="${FIX:-$REPO_ROOT/system/factory/loop-fixtures}"
MODEL="${MODEL:-sonnet}"
# The three facts reality (the SCRATCHPAD) knows that the stale plan does not.
# ⚠ MATCH ON MEANING, NOT WORD ORDER. First version of this probe searched the literal string
#   "scope confirm"; the model wrote "Confirm scope for canon curation" and the probe reported a
#   FAIL on a plan that was actually correct — 1 of 3 "failures" was the tester, not the subject.
#   That is skill-building-sop §V.2 reproduced live (39 apparent failures collapsed to 2 once the
#   instrument was fixed). Each gate is an ORDER-INSENSITIVE regex; keep it that way.
GATES=(
  "scope.*confirm|confirm.*scope"
  "canon.is.observation"
  "refresh.*brief|brief.*refresh|refresh this brief"
)

die() { printf '\n\033[31mPROBE ERROR: %s\033[0m\n' "$1" >&2; exit 2; }
[ -d "$FIX/stale" ]   || die "no fixture at $FIX/stale"
[ -d "$FIX/in-sync" ] || die "no fixture at $FIX/in-sync"
command -v claude >/dev/null || die "claude CLI not on PATH"

count_gates() {  # how many of the known facts does this plan file contain? (order-insensitive)
  local f=$1 n=0 g
  for g in "${GATES[@]}"; do grep -qiE -- "$g" "$f" && n=$((n+1)); done
  echo "$n"
}

# ── the loop pass: reconcile, and EMIT the corrected plan (never write it) ──
sharpen() {
  local dir=$1
  claude -p --model "$MODEL" <<EOF 2>/dev/null
You are the reconcile step of ClaudeOps /checkin, followed by its plan-repair step.

Compare the brief against the plan. A tension counts ONLY where acting on one source would mean doing
DIFFERENT WORK than acting on the other — not merely different wording.

Then OUTPUT, in this exact shape and nothing else:

TENSIONS: <one line per tension, or the single word NONE>
---PLAN---
<the full corrected plan.md. If there were no tensions, reproduce it byte-for-byte unchanged.
 If there were, add the missing work as real tasks so the plan no longer omits what the brief knows.>

=== brief.md ===
$(cat "$dir/brief.md")

=== plan.md ===
$(cat "$dir/plan.md")
EOF
}

run_half() {
  local name=$1 dir=$2 expect=$3   # expect = SHARPEN | NOCHANGE
  local tmp; tmp=$(mktemp -d) || die "mktemp failed"
  cp "$dir/brief.md" "$dir/plan.md" "$tmp/" || die "copy failed"

  local before after out tensions newplan
  before=$(count_gates "$tmp/plan.md")

  out=$(sharpen "$tmp") || die "claude -p failed for $name"
  [ -n "$out" ] || die "empty model output for $name"

  tensions=$(printf '%s' "$out" | sed -n '1,/^---PLAN---$/p' | sed '$d')
  newplan=$(printf '%s' "$out" | sed -n '/^---PLAN---$/,$p' | tail -n +2)
  [ -n "$newplan" ] || die "model emitted no ---PLAN--- section for $name"

  printf '%s\n' "$newplan" > "$tmp/plan.after.md"
  after=$(count_gates "$tmp/plan.after.md")

  echo "──────────────────────────────────────────────────────────────"
  echo "HALF: $name   (expect: $expect)"
  echo "  known facts present in plan  BEFORE: $before/3   AFTER: $after/3"
  echo "  model said → $(printf '%s' "$tensions" | head -3)"

  local verdict
  if [ "$expect" = "SHARPEN" ]; then
    if [ "$after" -gt "$before" ] && [ "$after" -eq 3 ]; then verdict=PASS; else verdict=FAIL; fi
    echo "  RULE: plan must GAIN all 3 facts it was missing"
  else
    if [ "$after" -eq "$before" ] && printf '%s' "$tensions" | grep -qi "none"; then
      verdict=PASS; else verdict="FAIL (control flipped — the run is VOID)"; fi
    echo "  RULE: control — must report NONE and change nothing"
  fi
  echo "  VERDICT: $verdict"
  rm -rf "$tmp"
  [ "${verdict:0:4}" = "PASS" ]
}

echo "LOOP PROBE — does a plan SHARPEN itself from what the build discovers?"
echo "model=$MODEL   fixtures=$FIX"
ok=0
run_half "STALE   (plan is missing what the notes know)" "$FIX/stale"   SHARPEN  || ok=1
run_half "IN-SYNC (control — already sharpened)"          "$FIX/in-sync" NOCHANGE || ok=1
echo "──────────────────────────────────────────────────────────────"
if [ "$ok" -eq 0 ]; then
  echo "✓ LOOP PROVEN — the plan absorbed what it did not know, and the control stayed silent."
else
  echo "✗ NOT PROVEN — read the halves above. A control flip VOIDS the run entirely."
fi
exit "$ok"
