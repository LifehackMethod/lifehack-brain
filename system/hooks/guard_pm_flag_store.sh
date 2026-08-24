#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: WHICH PROJECT A WINDOW IS WORKING ON IS FIXED FOR THE LIFE OF THAT WINDOW. `pm_flag.sh`
#      enforces that — it refuses to re-point a window at a different project, and refuses to
#      un-point it. But the thing it is guarding is a handful of plain files under ~/.claude/run/pm/,
#      and a session has full shell access to them. An adversarial audit executed the bypass in one
#      command: write the flag file directly and the refusal is simply skipped — no error, no exit
#      code, no line in the log. So `pm_flag.sh` is the DECISION, and this hook is the only thing
#      that makes it a lock rather than a polite convention.
#      THE INCIDENT BEHIND IT: a session re-pointed its own window from one project to another on
#      its own judgment, twice in one day, and then wrote two handoff notes aimed at the wrong
#      project. Nobody noticed until much later, because nothing said anything.
# GUARDS: any Write/Edit whose target is under ~/.claude/run/pm/ OR ~/.claude/run/plan/, and any Bash
#      command that NAMES either folder AND carries a write or destroy token (a redirect · rm · mv ·
#      cp · tee · sed -i · truncate · chmod · ln · dd · an interpreter doing a write). It matches the
#      WRITE-TO-TARGET pattern, never the bare keyword — an `ls`, `cat` or `grep` of either store
#      stays allowed, and so does an ordinary `pm_flag.sh arm|status|locked` or `plan_flag.sh
#      record|set|status|locked`, which are the sanctioned writers.
#      ⭐ TWO STORES, ONE GUARD (2026-08-15). The plan lock is the same ruling applied to plans, and
#      it refuses through `plan_flag.sh` exactly as the project lock refuses through `pm_flag.sh`.
#      Until now this guard watched the pm store only, so a direct write to `plan-<key>.flag` or a
#      delete of `lock-<key>.plan` skipped the plan lock's refusal entirely — the identical hole an
#      audit had already executed against the pm store, left open on the other half. That is a
#      path-pattern extension, not a second mechanism: same tiers, same verb lists, same false-
#      positive shape. Only the REDIRECT text differs per store, because sending someone to
#      pm_flag.sh after they touched the plan store is the wrong instruction.
# REDIRECT: the only sanctioned writers are `bash <repo>/system/hooks/pm_flag.sh arm|clear|status|locked`
#      (projects) and `bash <repo>/system/hooks/plan_flag.sh record|set|clear|status|locked` (plans).
#      YOU cannot change which project or which plan this window is on. Two things can: a NEW window
#      (`/checkin <project>` there), or the PERSON saying so in their own next prompt — e.g.
#      "switch the project to <slug>" / "switch the plan to <name>" — which makes pm_persist.sh issue
#      ONE single-use grant that pm_flag.sh OR plan_flag.sh burns on one change. You cannot produce
#      that yourself, and writing the grant file by hand is a write to this store like any other:
#      denied here. READING another project's brief or plan needs no arming at all.
# SIGNPOST: the rule and its reasoning live in `system/hooks/pm_flag.sh`'s own header, and the plan
#      half in `system/hooks/plan_flag.sh`'s; this guard's matrix is
#      `system/hooks/tests/test_write_custody_guards.sh`, and its per-store path coverage is
#      section 11 (pm) + section 12 (plan) of `system/hooks/tests/test_pm_lock_override.sh`.
#      Change those first.
# FAIL_POSTURE: closed — unparseable input denies.
#
# ⚠ THIS IS A SPEED BUMP, NOT A WALL, AND IT IS SAID PLAINLY SO NOBODY OVER-TRUSTS IT.
#   An audit charged with defeating it walked past with four `cd` commands and a relative redirect,
#   and again with a path held in a variable, an aliased verb, rsync, base64 piped to a shell, and a
#   relative Write path. It matches TEXT. It does not parse a shell, resolve variables, follow a
#   `cd`, or resolve a symlink — so anything that can read this file can step around it.
#   That was accepted rather than overlooked. The goal is NOTICING, not preventing: the owner's
#   ruling is "I don't mind being able to write into a different brief. What I want is for it not to
#   change without me seeing it." The load-bearing controls are `pm_flag.sh`'s and `plan_flag.sh`'s
#   own refusals (which an obedient session cannot reach around, because tripping them requires no
#   evasion), the NOISE both make on every spend — a banner on the terminal the person is watching,
#   plus previous_slug/previous_plan + override_phrase written into the lock file — and
#   `guard_cross_project_write.sh`'s one-time alarm. This raises the cost of a careless direct write.
#   ⛔ COVERING THE PLAN STORE DOES NOT PROMOTE THIS TO A WALL. It is the same text match over one
#   more path; every evasion listed above works identically against `run/plan`.
#   ⛔ Do NOT add regex rules believing they close the gap — the only real fix is an operating-system
#   boundary, a store owned by a user the agent cannot write as, which is a deliberately deferred
#   decision. More regex buys false positives, and a guard that fires on correct work gets routed
#   around, which costs more than the hole it was patching.
# UPDATED: 2026-08-11 (ported; paths resolved from this script, personal references removed)
# ─────────────────────────────────────────────────────────────────────────────
# guard_pm_flag_store.sh — PreToolUse hook (matcher: Bash|Write|Edit)

# Where the sanctioned writer lives, resolved FROM THIS SCRIPT — never a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="${_HOOKDIR%/system/hooks}"
[ "$_REPO" = "$_HOOKDIR" ] && _REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"

INPUT=$(cat)
PARSED=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
ti = d.get('tool_input') or {}
print((d.get('tool_name') or '').strip())
print((ti.get('command') or '').replace('\n', ';'))   # a newline IS a separator, never a space
print((ti.get('file_path') or '').strip())
") || { printf '%s\n' '{"decision":"block","reason":"BLOCKED: guard_pm_flag_store could not read the hook input, so it is failing closed. The project-arming store (~/.claude/run/pm/) is protected; run the action through pm_flag.sh instead."}' >&2; exit 2; }

TOOL=$(printf '%s' "$PARSED"  | sed -n '1p')
COMMAND=$(printf '%s' "$PARSED" | sed -n '2p')
FILEPATH=$(printf '%s' "$PARSED" | sed -n '3p')

DENY="{\"decision\":\"block\",\"reason\":\"BLOCKED: direct write to the project-arming store (~/.claude/run/pm/). WHY: which project a window is working on is fixed for the life of that window — pm_flag.sh refuses to re-point a window or un-point it, and writing these files by hand is exactly how that refusal gets skipped. An audit proved a one-line direct write silently re-points a window with no refusal and no trace. The incident behind the rule: a session re-pointed itself mid-work and then wrote two handoff notes aimed at the wrong project. REDIRECT: the only sanctioned writer is \`bash ${_REPO}/system/hooks/pm_flag.sh arm|clear|status|locked\`. YOU cannot change which project THIS window is on. Two things can, and neither is available to you alone: (1) a NEW window — run \`/checkin <project>\` there; (2) the PERSON saying so in their own next prompt, e.g. \\\"switch the project to <slug>\\\", which issues a single-use grant that pm_flag.sh burns on exactly one change. ⛔ Do not hand them that sentence as a password to recite — ASK whether they actually want the project changed, and let them answer in their own words. Writing the grant file yourself is a direct write to this store and lands right back here. READING another project's brief or plan needs no arming: just open the file. Reads of this store (ls/cat/grep) are allowed. RULE: the header of system/hooks/pm_flag.sh.\"}"

# --- THE PLAN STORE'S OWN REFUSAL TEXT (2026-08-15).
# Same guard, same tiers — but a session that just tried to write `plan-<key>.flag` must be sent to
# plan_flag.sh, not pm_flag.sh. Handing it the project redirect would be a wrong instruction printed
# with total confidence, which is worse than no message: it teaches the reader the guard does not
# understand what it just blocked.
DENY_PLAN="{\"decision\":\"block\",\"reason\":\"BLOCKED: direct write to the plan-arming store (~/.claude/run/plan/). WHY: which plan a window is working on is fixed for the life of that window — plan_flag.sh refuses to re-point a window at a different plan, and refuses to un-point it. Writing plan-<key>.flag by hand, or deleting lock-<key>.plan, is exactly how that refusal gets skipped: no error, no exit code, no line in plan-denied.log. This is the same hole an audit already executed against the project store before this guard existed. REDIRECT: the only sanctioned writer is \`bash ${_REPO}/system/hooks/plan_flag.sh record|set|clear|status|locked\`. YOU cannot change which plan THIS window is on. Two things can, and neither is available to you alone: (1) a NEW window; (2) the PERSON saying so in their own next prompt, e.g. \\\"switch the plan to <name>\\\" or \\\"override the plan lock\\\", which issues a single-use grant that plan_flag.sh burns on exactly one change. ⭐ It is ONE grant for BOTH locks — the same file pm_flag.sh consumes — so it buys one change to the project OR one to the plan, never both. ⛔ Do not hand them that sentence as a password to recite — ASK whether they actually want the plan changed, and let them answer in their own words. Writing the grant file yourself is a direct write to the guarded store and lands right back here. READING another plan needs no arming: just open the file. Reads of this store (ls/cat/grep) are allowed. RULE: the header of system/hooks/plan_flag.sh.\"}"

# --- Write/Edit: the tool IS a write. Any target inside either store is denied outright.
case "$TOOL" in
  Write|Edit|NotebookEdit)
    case "$FILEPATH" in
      *"/.claude/run/pm/"*)   printf '%s\n' "$DENY"      >&2; exit 2 ;;
      *"/.claude/run/plan/"*) printf '%s\n' "$DENY_PLAN" >&2; exit 2 ;;
    esac
    exit 0 ;;
esac

# --- RUNNING THE GRANT ISSUER IS A WRITE TO THE STORE BY ANOTHER NAME (2026-08-15).
# pm_persist.sh is the only thing that mints the human-word override grant, and it mints it from
# the prompt handed to it on stdin. Only the harness has any business handing it that — a session
# with a shell can pipe it a sentence the person never said and manufacture its own authorisation,
# which is precisely the thing the lock exists to make impossible. There is no legitimate reason
# for a session to execute a UserPromptSubmit hook by hand.
# ⚠ THIS IS ONE FILENAME, NOT A NEW VERB LIST — the header's warning above ("do NOT add regex rules
# believing they close the gap") is about chasing evasive writes with more patterns, and it still
# stands. This adds no pattern to that chase: no verb pairing, no path resolution, nothing that can
# fire on ordinary work. The whole false-positive surface is someone debugging the hook by hand,
# and the redirect below names the supported way to do exactly that.
if printf '%s' "$COMMAND" | grep -qE '(^|[[:space:]/;&|(])pm_persist\.sh([[:space:]]|$|["'"'"'])'; then
  printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: running pm_persist.sh by hand. WHY: that hook is the sole issuer of the project-lock override grant, and it issues it from whatever prompt text it is handed on stdin. Only the harness should hand it that. A session that pipes it a sentence the person never typed manufactures its own permission to change which project this window writes to — which is the exact failure the lock exists to prevent, and it would carry the person's name on it. REDIRECT: you cannot authorise this yourself. If the project really should change, ASK — and let them answer in their own words, in their own next message; the hook will see it. To exercise or debug the hook, run its suite: \`bash ${_REPO}/system/hooks/tests/test_pm_lock_override.sh\`, which drives it inside a sandbox HOME. RULE: the header of system/hooks/pm_flag.sh.\"}" >&2
  exit 2
fi

# --- Bash: only deny when the command NAMES a store AND carries a write/destroy token.
# Path-BOUNDARY anchored: `.claude/run/pm` or `.claude/run/plan` must be followed by a `/`, a quote,
# whitespace, or the end of the string. Without this, sibling folders like run/pm-ack were treated as
# the protected store — found when the guard blocked the very build of its own successor. The same
# anchor is what keeps `run/plans-archive` out of the plan store's coverage; `plan` and `pm` are
# alternatives inside ONE boundary, never a bare prefix match.
printf '%s' "$COMMAND" | grep -qE '\.claude/run/(pm|plan)($|[/"'"'"'[:space:]])' || exit 0

# WHICH store did they name? The message must match the store, and when a single command names both
# the project text is the one that prints — it is the broader rule and it names the incident.
STORE_DENY="$DENY_PLAN"
printf '%s' "$COMMAND" | grep -qE '\.claude/run/pm($|[/"'"'"'[:space:]])' && STORE_DENY="$DENY"

# --- Tier 1: unambiguous write/destroy tokens, EACH ANCHORED TO THE STORE PATH.
# ⛔ THE FALSE POSITIVE THIS SHAPE FIXES fired three times in one session, and the third time it
# blocked the very edit that repairs it, because the patch text pairs the verb list with the store
# path. The verb list used to match a destroy token ANYWHERE in a command that merely MENTIONED the
# store — so a fixture teardown (`rm -rf /tmp/checkin-fixture`) sitting in the same script as a pure
# READ of the store was denied, twice, while someone was verifying a documented procedure.
# ⭐ THE RULE, which this guard's own header already claimed: match the WRITE-TO-TARGET pattern,
# never the keyword alone.
# ⇒ Each verb must be followed, WITHIN THE SAME COMMAND SEGMENT (no `;`, `&` or `|` between), by the
# store path. A delete aimed at the store still denies; a delete aimed at /tmp in a script that also
# reads the store does not. Flattening newlines to `;` above is what makes "same segment" mean
# anything in a multi-line script — as a space it silently joined two unrelated commands into one.
# STATED LOSS: a destroy whose target is only in a variable is not caught. It never was — the
# boundary check above exits when the literal path is absent — and this guard does not resolve
# variables, as the header says. That is a narrow, contrived miss traded against a repeated false
# positive on read-only work.
if printf '%s' "$COMMAND" | grep -qE '(>>?[[:space:]]*[^|&;]*\.claude/run/(pm|plan)|(^|[[:space:]!;&|(])(rmdir|rm|mv|cp|tee|truncate|ln|install|dd|chmod|chown|touch|shred|unlink)[[:space:]][^;&|]*\.claude/run/(pm|plan)|(sed|perl)[[:space:]]+-[a-zA-Z]*i[^;&|]*\.claude/run/(pm|plan))'; then
  printf '%s\n' "$STORE_DENY" >&2
  exit 2
fi

# --- Tier 2: an INTERPRETER only counts as a write when the command ALSO shows a write verb.
# ⛔⛔ THE FALSE POSITIVE THIS FIXES, and it is the same disease as Tier 1's. The bare tokens
# python3|perl|ruby|node|php used to sit in Tier 1, so ANY script that merely MENTIONED the store was
# denied — including a pure read. That broke a real, shipped instruction: `/checkin`'s gate tells a
# session to read a value out of this store, and the guard denied it. The step was unrunnable as
# written. A guard that blocks the system's own documented procedure protects nothing; it teaches
# sessions to route around it.
# ⛔ Do NOT "fix" a future false positive by adding more nouns above — that direction buys a silent
# false negative. Narrow by evidence of a WRITE instead, the way this does.
if printf '%s' "$COMMAND" | grep -qE '(^|[[:space:]!;&|(])(python3?|perl|ruby|node|php)([[:space:]]|$)'; then
  # STREAM WRITES ARE NOT FILE WRITES (regression repaired 2026-08-23; first recorded 2026-08-13).
  # The verb list below contains a bare `.write(` token, which also matches the Python idioms for
  # printing to stdout and stderr. So a READ-ONLY harness that merely PRINTED json while naming the
  # guarded store was DENIED -- while the deny text it printed said reads of the store are allowed.
  # The guard contradicted itself out loud.
  # THE PREVIOUS "FIX" WAS TO DELETE THE TWO FAILING TEST CASES from system/hooks/tests/, which is
  # why that suite reported green while the defect stayed live. The cases are restored in
  # system/tools/verify-pm-guard.sh; this is the actual repair.
  # THIS NARROWS THE GUARD, so state precisely why it opens no hole: a stream write can only reach
  # the guarded store through a shell REDIRECT, and Tier 1 above already denies every `>` and `>>`
  # aimed at it, independently of this test. Neutralising the stream tokens here therefore removes a
  # false positive and no true positive. Verified by the full 18-case suite before landing.
  _CMD_NOSTREAM=$(printf '%s' "$COMMAND" | sed -E 's/sys\.(stdout|stderr)\.(buffer\.)?(write|writelines)/__stream_out__/g')
  if printf '%s' "$_CMD_NOSTREAM" | grep -qE "(open\([^)]*['\"](w|a|x|r\+|w\+|a\+)|\.write\(|\.writelines\(|\.writeText|writeFileSync|write_text|os\.replace|os\.rename|os\.remove|os\.unlink|shutil\.(copy|move)|Path\([^)]*\)\.(write|unlink|rename)|mkstemp|NamedTemporaryFile)"; then
    printf '%s\n' "$STORE_DENY" >&2
    exit 2
  fi
fi
exit 0
