#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: lib/bash_write_door.sh's __BWD_UNRESOLVED_VAR__ sentinel says "I could not resolve $NAME in
# this token" -- and on its own that is NOT evidence the write lands inside any particular guard's
# protected scope. `echo x > "$TMPDIR/foo"`, `cp a "$SOME_TOOL_VAR/tmp/b"`, `tee "$RUNNER_TEMP/out"`
# all produce it too, and every one of those is ordinary, unremarkable work that passed every one of
# the 5 guards that source lib/bash_write_door.sh before this file existed. Denying on ANY sentinel,
# unconditionally, was the first cut of FIXCARD-CROSS-PROJECT-WRITE-VAR-PATHS -- correct on the
# incident, wrong on everything else: a lead review (2026-09-17) caught it as a large false-block
# regression before it shipped.
# WHAT THIS DOES, AND WHAT IT DELIBERATELY DOES NOT DO: it computes the REMAINDER -- the raw token
# with its one $NAME / ${NAME} reference removed -- and nothing else. It makes NO decision. Each
# guard runs ITS OWN existing scope-classification logic (the same pattern it already applies to a
# real, resolved candidate) against that remainder, and decides deny-or-allow itself. That split is
# deliberate, the same one bash_write_door.sh's own header already draws for "is this a write" vs
# "is this path mine": this file only ever answers the former's variable-shaped cousin -- "what does
# the KNOWN part of this token look like" -- never the latter.
# GUARDS: nothing on its own -- a sourced library, not a hook.
# FAIL_POSTURE: n/a -- a pure text transform. It cannot itself allow or deny anything; a caller that
# cannot load this file must fail closed on its OWN terms, the same way it already does when
# lib/bash_write_door.sh or lib/winpath_fold.sh fails to load.
# SIGNPOST: the matrix lives in system/hooks/tests/test_bash_write_door.sh (the remainder function
# itself) and each of the 5 callers' own test suites (the scope decision).
# UPDATED: 2026-09-17 (created, in response to the lead review above)
# ─────────────────────────────────────────────────────────────────────────────

# bwd_sentinel_remainder <raw_token> <bare_name_without_dollar>
#   Prints <raw_token> with its one $NAME / ${NAME} reference removed -- word-boundary safe, so a
#   name that is a strict prefix of a longer identifier (e.g. NAME vs NAME2) is never partially
#   stripped. Prints an EMPTY string when the token WAS that reference and nothing else (a bare
#   `> "$X"`) -- the caller MUST treat an empty remainder as "could be anything, including something
#   in my scope" and fail closed, never as "nothing here."
bwd_sentinel_remainder() {
  python3 -c '
import sys, re
raw, name = sys.argv[1], sys.argv[2]
pat = re.compile("\\$\\{" + re.escape(name) + "\\}|\\$" + re.escape(name) + "(?![A-Za-z0-9_])")
sys.stdout.write(pat.sub("", raw))
' "${1:-}" "${2:-}"
}
