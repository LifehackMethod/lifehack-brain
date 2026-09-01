#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: MONTHLY deep-mine leg of the Standing Archivist — STAGGERED, not all-at-once. Every
#      desk with a real records back-catalog gets deep-mined roughly once a month, spread out
#      so two never run the same tick. One dispatcher: each tick, pick the single MOST-OVERDUE
#      desk from a notes-durable last-mined ledger, mine just that one, stamp it. Read-only
#      insight-harvest per `.claude/skills/archivist-deepmine/SKILL.md` -> grouped proposal.
#      DETECTS + PROPOSES only; never fixes, never writes canon, never deletes.
# GUARDS: read-only forever; exits 0 even when it finds promotions (non-zero = tool broke ->
#      Pulse auto-disables after 3). Lock+watchdog (1800s).
# REDIRECT: registered as `archivist-deepmine` in system/pulse-config.md (interval 345600 = 4d
#      tick; the ~30-day-per-desk cadence is enforced inside via the ledger, mirroring the
#      donor's stagger). Engine: archivist-run.lib.sh.
#
# ⚖ PORT NOTE (donor: system/tools/archivist-deepmine-run.sh). Two things changed:
#   1. Drive-upload / folder-id machinery dropped — see archivist-run.lib.sh's own port note.
#      Output follows `.claude/skills/archivist-deepmine/SKILL.md`'s own documented contract:
#      `<notes>/system/logs/archivist_{date}_deepmine-{desk}.md`, exactly as that skill's own
#      "Write the synthesis proposal to" step already names.
#   2. `ARCH_DEEPMINE_SKIP_DESKS` SHIPS EMPTY here, not the donor's five hardcoded personal
#      desk names. That default rotation-skip list named that operator's own subjects (their
#      mid-build desks, one flagged "too thin," one flagged "too big for the watchdog") — none
#      of that is a fact about this install. An empty default means every desk with a records/
#      or projects/ body is eligible from a fresh clone; override per-install via the env var
#      if a desk genuinely needs holding back (mid-build, too-thin, too-big-for-the-watchdog —
#      same reasons the donor named, just not pre-filled with someone else's answer).
#   3. NOTE — the deepmine SKILL.md itself currently says "its scheduled runner does NOT ship
#      ... the skill IS the interactive path." That line predates this port (T9.8b); it is now
#      STALE, not a ruling to work around — the plan that authorized this file names the
#      scheduled leg as a real, currently-missing gap ("the weekly audit and monthly deep-mine
#      are manual forever without this"). Flagged here rather than silently overridden; the
#      skill file itself is outside this task's ownership to correct.
# ─────────────────────────────────────────────────────────────────────────────
set -u
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
# WINDOWS PATH FOLD: DATA is the unfolded output of brain_root.py --quiet, which on Windows is
# backslash-native. Bash's glob (`for d in "$DATA"/desks/*/`, below) treats `\` as an escape
# character, not a separator, so without this the glob would silently match zero desks on every
# Windows run. See system/hooks/lib/winpath_fold.sh. Degrade-safe fallback (identity) -- a run
# without a resolvable DATA already returns via arch_prerun's own `[ -n "$DATA" ] || return 1`.
. "$CODE_ROOT/system/hooks/lib/winpath_fold.sh" 2>/dev/null || _winfold() { printf '%s' "$1"; }
LEDGER="${DATA:+$DATA/state/archivist/deepmine-ledger.json}"   # notes-durable: {desk: last_mined_epoch}
PER_DESK_MIN_AGE_DAYS=25                                        # a desk is "due" only if last mined >= this

# SHIPS EMPTY — see port note (2) above. Space-separated; override per-install via env.
ARCH_DEEPMINE_SKIP_DESKS="${ARCH_DEEPMINE_SKIP_DESKS:-}"

ARCH_MODE="deepmine"
ARCH_LABEL="archivist-deepmine"
ARCH_WATCHDOG=1800

# ── DISPATCHER (prerun hook): pick the most-overdue desk; skip clean if none is due ──────
arch_prerun() {
  [ -n "$DATA" ] || return 1
  mkdir -p "$DATA/state/archivist" 2>/dev/null
  local d name desks=() DATA_GLOB
  # Folded ONLY as the glob root -- `name` two lines down comes back out of $d, the glob's own
  # match, whose wildcard portion keeps the real on-disk desk-folder case regardless of this fold
  # (Windows' filesystem is case-insensitive, so the lowercased root still opens the real
  # directory, and bash substitutes the wildcard from the actual directory-entry name it read).
  DATA_GLOB="$(_winfold "$DATA")"
  for d in "$DATA_GLOB"/desks/*/; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"
    if [ -d "$d/records" ] || [ -d "$d/projects" ]; then desks+=("$name"); fi
  done
  [ "${#desks[@]}" -gt 0 ] || { _alog "no desks with record bodies — nothing to mine."; return 1; }

  local keep=() name2
  for name2 in "${desks[@]}"; do
    case " $ARCH_DEEPMINE_SKIP_DESKS " in
      *" $name2 "*) _alog "skip '$name2' — held back (ARCH_DEEPMINE_SKIP_DESKS)"; continue ;;
    esac
    keep+=("$name2")
  done
  # Guard on `keep` BEFORE expanding it — macOS bash 3.2 throws 'unbound variable' on
  # "${keep[@]}" when empty, under set -u (fires if every desk was skipped).
  [ "${#keep[@]}" -gt 0 ] || { _alog "all candidate desks skipped — nothing to mine."; return 1; }
  desks=("${keep[@]}")

  local pick
  pick="$(DESKS="${desks[*]}" LEDGER="$LEDGER" MIN_AGE_DAYS="$PER_DESK_MIN_AGE_DAYS" python3 - <<'PY'
import json, os, time
desks = os.environ["DESKS"].split()
min_age = int(os.environ["MIN_AGE_DAYS"]) * 86400
try:
    led = json.load(open(os.environ["LEDGER"]))
    if not isinstance(led, dict): led = {}
except Exception:
    led = {}
now = time.time()
oldest = sorted(desks, key=lambda d: led.get(d, 0))[0]
print(oldest if (now - led.get(oldest, 0)) >= min_age else "")
PY
)"
  [ -n "$pick" ] || { _alog "no desk overdue (all mined < ${PER_DESK_MIN_AGE_DAYS}d ago) — skip cheap."; return 1; }

  DESK="$pick"
  local datestamp; datestamp="$(date +%F)"
  ARCH_QUEUE_FILE="$DATA/system/logs/archivist_${datestamp}_deepmine-${DESK}.md"
  ARCH_SUMMARY_FILE="$DATA/system/logs/archivist_${datestamp}_deepmine-${DESK}.summary.json"
  ARCH_PING_TITLE="Archivist — ${DESK} deep-mine"
  ARCH_PROMPT="Your notes root is: $DATA
You are the Standing Archivist's DEEP-MINE, running HEADLESS and UNATTENDED. You are READ-ONLY: you DETECT and PROPOSE — never fix, move, rename, or delete.
Read and follow $CODE_ROOT/.claude/skills/archivist-deepmine/SKILL.md exactly (resolve '<notes>' paths against the root above). TARGET DESK: ${DESK}. Mine ONLY this desk's record bodies under $DATA/desks/${DESK}/ (records/ and projects/**/records/, skipping backups/), fan out READ-ONLY sonnet Agent subagents in BATCHES OF 2-3 (never 6+) per the skill's own Architecture section, synthesize per its Procedure, and route every promotable insight's home via the librarian (.claude/skills/archivist-route/SKILL.md) — never a free-formed home.

WRITE EXACTLY TWO FILES, then exit — nothing else:
1) The grouped deep-mine proposal (markdown) → $ARCH_QUEUE_FILE
   Sections: A promote-to-desk-canon · B promote-to-project-canon · C other-refile · D stale-bulk-delete (dep-gated) · E reconciliations. One line per item: detail · proposed action · the ROUTED home. Lead with a count-by-section summary. If the desk yields nothing, say so plainly — a near-empty result on a young desk is a VALID result.
2) A machine-readable summary sidecar (JSON, one object) → $ARCH_SUMMARY_FILE
   EXACTLY: {\"status\":\"OK\"|\"NEEDS_REVIEW\",\"finding_count\":<integer>,\"headline\":\"<=8 word teaser, name the desk\"}
   Use status OK with finding_count 0 ONLY if the desk genuinely yielded nothing promotable and nothing stale; otherwise NEEDS_REVIEW with the true count.
Do NOT send any notification, do NOT touch any other file — the runner pings deterministically from the summary sidecar above."
  _alog "dispatch: mining the most-overdue desk -> '${DESK}'."
  return 0
}

# ── LEDGER STAMP (postrun hook): only on success, advance this desk's clock ──────────────
arch_postrun() {
  DESK="$DESK" LEDGER="$LEDGER" python3 - <<'PY' 2>/dev/null || true
import json, os, time
p = os.environ["LEDGER"]; desk = os.environ["DESK"]
try:
    led = json.load(open(p))
    if not isinstance(led, dict): led = {}
except Exception:
    led = {}
led[desk] = int(time.time())
os.makedirs(os.path.dirname(p), exist_ok=True)
tmp = p + ".tmp"
json.dump(led, open(tmp, "w"), indent=2)
os.replace(tmp, p)
PY
  _alog "ledger stamped: '${DESK}' mined $(date +%F) — rotation advanced."
}

# shellcheck source=/dev/null
source "$CODE_ROOT/system/tools/archivist-run.lib.sh"
run_archivist
exit $?
