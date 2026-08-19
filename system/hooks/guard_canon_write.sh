#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: canon is the one thing that is loaded into every conversation before anything else. That is
#      its whole value and its whole danger. A line that lands there is carried forward forever
#      without ever being re-examined, and every session pays for it in context whether or not that
#      conversation had anything to do with the subject. So canon has two properties, and both need
#      defending mechanically rather than by good intentions: it stays TRUE over time, and it stays
#      SMALL.
# GUARDS: a Write or Edit to a canon file — anything under a `canon/` directory, plus the top-level
#      `canon.md` — that is either
#        (a) FAST-STALE: it carries a shelf-life, an expiry, or a snapshot marker. Something with an
#            expiry date in the always-loaded layer is a fact that will quietly go wrong and keep
#            being believed. Those belong in records/, dated, retrieved on demand.
#        (b) OVERSIZED: over 3,200 characters. Derived, not picked — see the rail below.
# REDIRECT: both denials say the same thing in different words — this belongs in records/, where
#      `/read` pulls it when it is relevant instead of every session paying for it forever.
# SIGNPOST: what canon is for lives in `system/knowledge-altitude.md` and `docs/data-layout.md`.
#      Change the rule there first; do not weaken this guard to get one write through.
# FAIL_POSTURE: closed — unparseable input denies.
# UPDATED: 2026-08-15 (T9.5d — added the ALLOW-path speed bump: an allowed canon write now emits
#      hookSpecificOutput.additionalContext, a loud non-blocking notice at the moment of write. See
#      the block comment at the ALLOW_CANON case below for why that field and not plain stdout.)
# UPDATED: 2026-08-11 (ported; the authority rail dropped, the size rail re-derived, the top-level
#      canon file brought into scope)
#
# ── (a) THE SIZE RAIL: 3,200 characters, and where that number comes from ────────────────────────
# NOT copied from the donor system, where it was measured against a different shape entirely — one
# insight per file, a whole directory of them. Here a canon file is an ACCUMULATING list of lines
# about one subject, so the donor's number would have had a completely different meaning.
# Re-derived against this repository's own already-shipped constant:
#   `system/hooks/session_context_loader.sh:28` loads every subject's canon at session start and
#   stops at 20,000 characters TOTAL, announcing what it had to leave out.
#   20,000 / 3,200 = 6.25 — so six subject folders can each sit at this rail and still all load.
#   A seventh starts pushing folders out of the session floor entirely.
# At roughly 200 characters a line that is about sixteen standing lines per subject, which is a
# generous ceiling for "the things that stay true" about one area of a life.
# ⛔ This is a deny WITH a redirect, not a ban: long material is welcome in records/, where it is
# pulled on demand. ⚠ Do NOT raise it to make one write fit. Raising it re-opens the drift it closes,
# and it does so silently — the cost lands on every future session, not on the one that raised it.
#
# ── (b) WHAT WAS DELIBERATELY LEFT OUT: the `authority: user` rail ───────────────────────────────
# The donor also refused any new canon file whose frontmatter did not carry `authority: user`, on
# the reasoning that only a human may promote something to canon. It is not ported, for two reasons,
# and the second is the one that decided it:
#
#   1. IT DOES NOT DO WHAT IT LOOKS LIKE IT DOES. `authority: user` is SELF-ATTESTATION — a machine
#      can type that line exactly as easily as a person can. It never protected against the hijacked
#      write it was written for; it only protected against a careless one that forgot the field.
#   2. IT BREAKS THIS PRODUCT ON DAY ONE. Measured 2026-08-11 against the canon this repository's own
#      `/save` writes after a person has approved it: exit 2, BLOCKED, "missing authority: user".
#      `/save` appends an approved line to `state/projects/<slug>/canon/current.md`, which carries no
#      frontmatter at all. So the first canon a person ever writes would be refused by a guard
#      shipped alongside the skill that wrote it. A guard that fires on correct work is one people
#      learn to route around, and then it is protecting nothing.
#
# What replaced it is stronger because it is interactive rather than textual: `/save` stops and shows
# the candidate line to the person before anything is written (`.claude/skills/save/phases/
# standard-steps.md`, the canon-gated pause). A pause a human answers cannot be typed past.
# ⚖ PENDING: this is a security-surface change and the owner's confirmation is outstanding. To
# restore the rail, re-add a check for `^authority:\s*user` on a Write and deny without it — one
# block in the python below. Do not restore it without also fixing what /save writes, or the
# product breaks again in exactly the way measured above.
# ─────────────────────────────────────────────────────────────────────────────
# guard_canon_write.sh — PreToolUse hook (matcher: Bash|Write|Edit)

INPUT=$(cat)

# ── THE THIRD DOOR, and this one is handled DIFFERENTLY from the other two guards — read why.
# The rails below are about CONTENT: how big the write is, and whether it carries an expiry marker.
# Through Write/Edit the content arrives as a field and can be measured. Through a shell command it
# is embedded in a heredoc, an echo, a pipe or a generator, and any attempt to measure it there is a
# guess. ⛔ A guess is exactly what must not happen in a size rail — a wrong measurement either blocks
# correct work or waves through the thing the rail exists to stop.
# ⇒ SO THIS DOOR IS CLOSED RATHER THAN INSPECTED: a Bash write aimed at canon is denied, and the deny
# names the door that works. The cost is real and small — writing canon through the shell stops being
# possible. The gain is that the content rails become unbypassable instead of decorative, which was
# the entire argument for having them.
_CANON_TOOL=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except Exception: print('__PARSE_ERROR__'); raise SystemExit
print((d.get('tool_name') or '').strip())
print(((d.get('tool_input') or {}).get('command') or '').replace('\n',';'))
")
if [ "$(printf '%s' "$_CANON_TOOL" | sed -n '1p')" = "Bash" ]; then
  _CANON_CMD=$(printf '%s' "$_CANON_TOOL" | sed -n '2p')
  if [ -n "$_CANON_CMD" ]; then
    _CW_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
    # shellcheck source=lib/bash_write_door.sh
    if . "$_CW_DIR/lib/bash_write_door.sh" 2>/dev/null; then
      while IFS= read -r _cc; do
        [ -n "$_cc" ] || continue
        if [ "$_cc" = "__BWD_PARSE_ERROR__" ]; then
          printf '%s\n' '{"decision":"block","reason":"BLOCKED: guard_canon_write could not analyse this Bash command, so it is failing closed. An unreadable command and a harmless one must never look the same. REDIRECT: use the Write or Edit tool for canon — the content rails only work there."}' >&2; exit 2
        fi
        case "$_cc" in
          */canon/*|*/canon.md|canon.md)
            printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: this Bash command writes to a canon file (${_cc}). WHY: canon carries two content rails — a size limit and an expiry-marker check — and both need to READ the content being written. Through the Write tool the content is a field this guard can measure; inside a shell command it is a heredoc or a pipe, and measuring it there would be a guess. A size rail that guesses is worse than none: it either blocks correct work or waves through the thing it exists to stop. So this door is closed rather than guessed at. REDIRECT: make this edit with the Write or Edit tool and the rails will run properly. If the content is generated, write it to a scratch file first, read it, then Write it. RULE: system/knowledge-altitude.md, and this hook's header.\"}" >&2
            exit 2 ;;
        esac
      done <<EOF
$(bwd_write_targets "$_CANON_CMD")
EOF
    fi
  fi
  exit 0
fi

PYCHECK=$(cat <<'PY'
import sys, json, os
try:
    d = json.load(sys.stdin)
except Exception:
    print("PARSE_ERROR"); sys.exit()
ti = d.get("tool_input", {}) or {}
path = ti.get("file_path") or ti.get("path") or ""
content = ti.get("content", ti.get("new_string", "")) or ""

# IN SCOPE: anything inside a canon/ directory, and the top-level canon.md.
# THE SECOND HALF IS NOT IN THE DONOR. It was added here because this repository has a canon file
# that the donor's path test could not see: `<notes>/canon.md`, the root canon — the one file whose
# own text says it is carried into every conversation forever, and the canon of every project that
# has no folder of its own (shared/registry.py, Project.canon). Leaving the single most
# always-loaded file out of a guard whose entire argument is "always-loaded costs are paid forever"
# would have shipped the guard with its main target missing.
in_canon_dir = "/canon/" in path
is_root_canon = os.path.basename(path) == "canon.md"
if not (in_canon_dir or is_root_canon):
    print("ALLOW_NONE"); sys.exit()

MAX_CHARS = 3200
if len(content) > MAX_CHARS:
    print(f"BLOCK_SIZE|{len(content)}|{MAX_CHARS}"); sys.exit()

low = content.lower()
stale = ["shelf-life:", "shelf_life:", "expires:", "tier: snapshot",
         "record_type: snapshot", "type: snapshot"]
hit = next((s for s in stale if s in low), None)
if hit:
    print("BLOCK_STALE|" + hit); sys.exit()
print("ALLOW_CANON|" + path + "|" + str(len(content)))
PY
)

RESULT=$(printf '%s' "$INPUT" | python3 -c "$PYCHECK")

R="WHAT CANON IS: the few things that stay true, small enough that every session can afford to carry them. Two tests, and a line has to pass both. (1) Will this still be true in six months, with no expiry date attached? If it has a date on it, it is a record, not canon. (2) Can a completely fresh session read this line ALONE, with no other context, and act on it correctly? If it needs the conversation around it, it is not finished. Everything else goes in records/, dated — nothing is lost, it is just pulled when it is relevant instead of carried always. SOURCE: system/knowledge-altitude.md + docs/data-layout.md."

case "$RESULT" in
  ALLOW_NONE) exit 0 ;;
  ALLOW_CANON*)
    # ── T9.5d — THE ALLOW-PATH SPEED BUMP (2026-08-15). ────────────────────────────────────
    # A write that PASSED both content rails still deserves a loud, non-blocking notice, at
    # the moment it happens — canon is the layer nothing re-checks later, so the write itself
    # is the only moment anyone is looking. Plain stdout/stderr on exit 0 is a DEAD channel for
    # PreToolUse (confirmed against the current Claude Code hooks reference, 2026-08-15: it
    # reaches the debug log only, never the model) — the exact failure this repo's own
    # hook-sop.md already has on record for `guard_web_search.sh` ("a WARNING-ONLY PreToolUse
    # hook that printed a caution then exit 0'd... the warning was security theater the model
    # never saw"). The ONE channel confirmed to reach the model on an ALLOW decision is
    # `hookSpecificOutput.permissionDecision:"allow"` + `additionalContext`. This is a narrower
    # claim than the house style's blanket "do NOT use hookSpecificOutput" (hook-contract.md,
    # written for the competing BLOCK formats) — that line never covered ALLOW+additionalContext,
    # which did not exist when it was written. Verified live this port: fired through the real
    # harness, not a bash pipe (hook-sop.md §4 — "a hook you haven't watched fire in a live
    # attempt is not a control").
    _T="${RESULT#ALLOW_CANON|}"; CPATH="${_T%%|*}"; CLEN="${_T##*|}"
    CANON_PATH="$CPATH" CANON_LEN="$CLEN" python3 -c "
import json, os
path = os.environ.get('CANON_PATH', '')
clen = os.environ.get('CANON_LEN', '')
msg = (f'CANON WRITE ALLOWED -- {path} ({clen} chars) is about to be loaded into EVERY future '
       f'session start, forever, whether or not that session has anything to do with this '
       f'subject. This is a speed bump, not a block (T9.5d, 2026-08-15) -- the authority:user '
       f'rail was dropped 2026-08-11 because it was self-attestation a machine types as easily '
       f'as a person, and it blocked /save writing its own approved canon. Before this settles '
       f'in: (1) will this still be true in six months with no expiry attached? (2) can a fresh '
       f'session with zero other context read this line ALONE and act on it correctly? If '
       f'either answer is no, this belongs in records/, dated, not here. '
       f'RULE: system/knowledge-altitude.md.')
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                          'permissionDecision': 'allow',
                                          'additionalContext': msg}}))
"
    exit 0 ;;
  PARSE_ERROR)
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: guard_canon_write could not read the tool input, so it is failing closed. ${R}\"}" >&2
    exit 2 ;;
  BLOCK_SIZE*)
    _T="${RESULT#BLOCK_SIZE|}"; GOT="${_T%%|*}"; LIM="${_T##*|}"
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: this canon file is ${GOT} characters against a ${LIM}-character rail. WHY: canon is loaded at the start of EVERY session, so its size is a cost paid forever by every conversation, including the ones that have nothing to do with this subject. The session loader stops at 20,000 characters across all your subjects and tells you what it left out — at this rail six subjects fit, and a file this size is starting to crowd the others off the page. A canon file this long is almost always reference material that drifted into the always-on layer. REDIRECT: put it in records/ (dated) and let /read pull it when it is relevant. If it genuinely IS canon, it is too long — cut it to the lines that a fresh session could read alone and act on. RULE: system/knowledge-altitude.md. Raise the rail there, with reason, never to make one write fit. ${R}\"}" >&2
    exit 2 ;;
  BLOCK_STALE*)
    MARK="${RESULT#BLOCK_STALE|}"
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: this canon write carries an expiry marker ('${MARK}'). WHY: canon is the layer nothing re-checks. A fact with a shelf-life put there does not expire — it just quietly becomes wrong and keeps being believed, in every conversation, because it is loaded before anything that could correct it. REDIRECT: write it to records/ with its date, where /read can see how old it is and say so. ${R}\"}" >&2
    exit 2 ;;
  *)
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: guard_canon_write ended in a state it does not recognise, so it is failing closed. ${R}\"}" >&2
    exit 2 ;;
esac
