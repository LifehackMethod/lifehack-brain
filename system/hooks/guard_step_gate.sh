#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_step_gate.sh" "PreToolUse+UserPromptExpansion" "Skill|<register-driven>" 2>/dev/null || true' EXIT
# guard_step_gate.sh — PreToolUse(Skill) + UserPromptExpansion(*), register-driven
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: K6-DESIGN-SPEC.md §0/§2 — deliverable (a), the GENERIC no-skip-boundary shape, generalized
#      out of guard_checkin_needs_project.sh's proven two-leg pattern (PreToolUse(matcher=Skill) +
#      UserPromptExpansion, needed because typing /skillname bypasses PreToolUse — the same citation
#      that guard carries, code.claude.com/docs/en/hooks, fetched live 2026-08-14). That guard has
#      ONE hardcoded skill name and ONE hardcoded precondition (pm_flag armed). This script exists so
#      the NEXT no-skip boundary is a register row, never a new bash file: given the invoked skill's
#      own name, it looks up that skill's `needs` (schema_v1.py COMMON_FIELDS, open list_of_str — the
#      same field K6 §1 reuses for the checkin->save seam) and denies only if a declared need has no
#      matching, unexpired receipt under the shared `step-receipts` flag family (system/hooks/lib/flag.sh).
# GUARDS: nothing, TODAY, for any real skill — see the v1-scope note below. When a FUTURE register row
#      declares `"needs": ["some_precondition"]` on a skill AND that skill is wired to this script (a
#      register hook row with matcher=Skill + if=Skill(<name>), or UserPromptExpansion matcher=<name>,
#      mirroring guard_checkin_needs_project.sh's own two rows) AND no producer has written a
#      `step_receipt.sh write <precondition-name> ...` receipt this session, THIS is what denies it.
# ⛔ v1 SCOPE (K6-DESIGN-SPEC.md §0, R9/R34 journaled): this script is built and proven here (its own
#      test suite, synthetic register+receipt fixtures) but is DELIBERATELY NOT REGISTERED against any
#      real skill in this build — no row in system/register/register.jsonl wires it to checkin or save
#      or anything else, so it produces ZERO register rows (harvest.py's harvest_hooks() only ever
#      derives `hook`-type rows from the live settings.json/hooks.json wiring, never from a script's
#      mere existence on disk — confirmed this session against pm_flag.sh/skill_anchor.sh, both
#      register-row-free for the identical reason). WHY narrower than a literal register-wiring pass:
#      save's OWN row now legitimately carries "needs": [..., "project_reconciled"] (K6 §1) for the
#      checkin->save seam — and that seam is EXPLICITLY R9/R34 advisory-only, NEVER a hard block
#      (K6-DESIGN-SPEC.md §0/§3: "a declared data seam + seam test, never a live block"). A generic
#      register-driven gate that reads `needs` and denies on a missing receipt would, if wired to
#      save's Skill invocation, silently turn that advisory seam into exactly the hard block the
#      ruling forbids — the one failure this build cannot risk. The checkin->save seam is instead
#      handled entirely outside this script, by plain (non-hook) markdown-embedded shell in each
#      skill's own phase file calling `system/hooks/step_receipt.sh` directly (see that script + K6
#      seam test) — informational only, exit 0 always, never routed through a PreToolUse/
#      UserPromptExpansion deny path. Flagged for Enver alongside the design spec's own §Questions.
# REDIRECT: a future no-skip boundary needing a REAL hard gate: (1) give the consumer skill's register
#      row a `needs` entry naming the precondition, (2) have the producer's own phase file call
#      `step_receipt.sh write <precondition-name> field=value...` once satisfied, (3) add this script's
#      two hook rows (PreToolUse matcher=Skill if=Skill(<consumer>), UserPromptExpansion
#      matcher=<consumer>) to the register with state=active, expiry=null, then `generate.py` + restart
#      (hook-sop.md's documented "newly-registered hook is inert in the registering window" gotcha).
#      No new bash file needed — that is the entire point of generalizing the shape.
# SIGNPOST: K6-DESIGN-SPEC.md (this mechanism's design) · system/hooks/guard_checkin_needs_project.sh
#      (the two-leg precedent this generalizes) · system/hooks/lib/flag.sh (the step-receipts
#      mechanic) · system/hooks/step_receipt.sh (the checkin->save seam's OWN direct, non-hook use of
#      the same flag family — a different consumer of the same library, not a caller of this script)
#      · system/hook-contract.md (deny format) · system/sops/hook-sop.md (fail-closed rule).
# FAIL_POSTURE: closed — any unparsed/unknown event, or a register that fails to parse, denies rather
#      than allows (hook-sop.md §3 rule 2: "on ANY error a BLOCK hook denies, never exit 0 on error").
# UPDATED: 2026-09-17 (new — K6, enforcement-layer Phase 2. Deliverable (a) of the K6 card; built,
#      tested, deliberately unregistered — see the v1 SCOPE note above.)
# ─────────────────────────────────────────────────────────────────────────────
#
# ONE SCRIPT, branching on `hook_event_name`, mirroring guard_checkin_needs_project.sh's own
# reasoning verbatim: both legs share the identical "look up this skill's needs, check receipts"
# logic and the identical deny shape (exit 2 + stderr) -- only the input field that carries the
# invoked skill's name differs (`tool_input.*` for PreToolUse's Skill call vs `command_name` for
# UserPromptExpansion).
#
# DENY SHAPE: exit 2 + deny text on stderr, for BOTH events -- same citation and same reasoning as
# guard_checkin_needs_project.sh's own DENY SHAPE note (code.claude.com/docs/en/hooks, fetched
# 2026-08-14): exit-2-plus-stderr is documented as fully equivalent to a JSON "deny"/"block" on both
# PreToolUse and UserPromptExpansion.
set -uo pipefail
INPUT="$(cat 2>/dev/null)"

# Resolve THIS repo's root from the hook's own location -- never a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"

# Register path -- overridable for tests (LHB_STEP_GATE_REGISTER), same override-for-testability
# convention guard_hook_sop_read.sh's tests already use (_REGISTER_ROOT there; a full path here,
# since this script only ever reads one file, never needs a whole fake repo tree).
REGISTER_PATH="${LHB_STEP_GATE_REGISTER:-$_REPO/system/register/register.jsonl}"

# Receipt TTL -- overridable for tests, matches skill_anchor.sh's ANCHOR_TTL_HOURS pattern.
TTL_HOURS="${LHB_STEP_GATE_TTL_HOURS:-24}"

_LIB="$_HOOKDIR/lib/flag.sh"

# ── fire-log: unconditional, first thing, before any logic (same reasoning as
# guard_checkin_needs_project.sh's own fire-log: proves the matchers are live, and empirically
# reveals the real tool_input shape the harness sends -- undocumented today). ─────────────────────
FIRELOG="${LHB_STEP_GATE_FIRELOG:-$HOME/.claude/run/step-gate-firelog.jsonl}"
mkdir -p "$(dirname "$FIRELOG")" 2>/dev/null
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
printf '%s\t%s\n' "$TS" "$INPUT" >> "$FIRELOG" 2>/dev/null || true

deny() {
  # $1 = leg label, $2 = skill name, $3 = missing need
  cat <<MSG >&2
BLOCKED: /$2 -- a declared precondition is missing.

WHY: the register declares "$2" needs "$3" before it runs, and no matching step-receipt (system/hooks/
step_receipt.sh, flagdir step-receipts) is present and unexpired for this session. (Leg: $1)

REDIRECT: run whichever step is supposed to produce "$3" first, then retry -- or if this looks wrong,
the precondition is declared on "$2"'s own row in system/register/register.jsonl ("needs").

RULE: K6-DESIGN-SPEC.md (this mechanism's design) + system/hook-contract.md (deny format) +
system/hooks/lib/flag.sh (the step-receipts mechanic this reads).
MSG
  exit 2
}

fail_closed() {
  # $1 = reason
  cat <<MSG >&2
BLOCKED: guard_step_gate.sh could not evaluate this call and is failing CLOSED, not open.

WHY: $1

RULE: system/sops/hook-sop.md ("on ANY error a BLOCK hook denies, never exit 0 on error").
MSG
  exit 2
}

# needs_for_skill <skill-name> -- prints one need per line (may be empty), or nothing if the
# skill has no row / the register can't be read. A missing register or a missing row is NOT an
# error here -- it means "nothing declared", which allows (there is nothing to gate).
needs_for_skill() {
  [ -f "$REGISTER_PATH" ] || return 0
  python3 -c "
import json, sys
name = sys.argv[1]
path = sys.argv[2]
try:
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get('type') == 'skill' and row.get('name') == name:
                for n in row.get('needs') or []:
                    print(n)
                break
except OSError:
    pass
" "$1" "$REGISTER_PATH" 2>/dev/null
}

# receipt_satisfied <need-name> -- 0 (true) if an unexpired step-receipt exists for this need
# under the shared step-receipts flag family, keyed by the need's OWN name as its prefix (the
# reusable convention this script establishes for any FUTURE producer/consumer pair -- see
# REDIRECT above). Independent of step_receipt.sh (that script is the checkin->save seam's own
# direct caller of flag.sh; this reads the same on-disk shape without depending on that CLI so a
# corrupt/missing step_receipt.sh cannot silently widen what this gate allows).
receipt_satisfied() {
  [ -f "$_LIB" ] || return 1
  # shellcheck source=lib/flag.sh
  . "$_LIB" || return 1
  flag_init step-receipts "$1"
  [ -f "$FLAG" ] || return 1
  flag_ttl_expired $(( TTL_HOURS * 3600 )) && return 1
  return 0
}

check_and_maybe_deny() {
  # $1 = leg label, $2 = skill name
  local leg="$1" skill="$2"
  [ -n "$skill" ] || return 0   # nothing to gate -- not this script's concern
  local needs
  needs="$(needs_for_skill "$skill")"
  [ -n "$needs" ] || return 0   # no declared preconditions -- allow
  while IFS= read -r need; do
    [ -n "$need" ] || continue
    receipt_satisfied "$need" || deny "$leg" "$skill" "$need"
  done <<< "$needs"
  return 0
}

EVENT="$(printf '%s' "$INPUT" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(str(d.get('hook_event_name') or '').strip())
" 2>/dev/null)"

case "$EVENT" in
  UserPromptExpansion)
    CMD_NAME="$(printf '%s' "$INPUT" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(str(d.get('command_name') or '').strip().lower())
" 2>/dev/null)"
    check_and_maybe_deny "UserPromptExpansion (typed)" "$CMD_NAME"
    exit 0
    ;;
  PreToolUse)
    # No documented tool_input schema for the Skill tool (same gap guard_checkin_needs_project.sh
    # notes) -- try the plausible field names; the fire-log above closes this gap empirically the
    # first time either leg fires for real.
    SKILL_NAME="$(printf '%s' "$INPUT" | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
ti = d.get('tool_input') or {}
name = ti.get('skill') or ti.get('name') or ''
print(str(name).strip().lower())
" 2>/dev/null)"
    check_and_maybe_deny "PreToolUse (Skill, via natural language)" "$SKILL_NAME"
    exit 0
    ;;
  "")
    # Empty/unparsed input on a hook_event_name we never even resolved. Fail CLOSED
    # (hook-sop.md §3 rule 2), same posture as guard_checkin_needs_project.sh's own default arm.
    fail_closed "unrecognized/unparsed hook_event_name ('$EVENT')"
    ;;
  *)
    # A real, known event this script simply doesn't branch on (only PreToolUse and
    # UserPromptExpansion carry a skill/command name this gate can evaluate) -- allow, there is
    # nothing to check.
    exit 0
    ;;
esac
