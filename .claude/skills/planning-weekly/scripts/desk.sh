#!/bin/bash
# desk.sh — the ONE place a planning-desk path exists in this skill.
# Finds the planning desk's folder through shared/desk_list.py (never a literal path, never a
# guessed desk name); prints the folder's full path on stdout, one line. Fails loudly (exit 1,
# reason on stderr) when the desk list cannot be read or has no planning row.
#
# Usage: desk.sh            -> prints e.g. <notes-root>/desks/<folder>
#        desk.sh --relative -> prints the folder NAME only (what desk_list.py returns)
# allow-silence: build-ruled location — slice B of the planning-weekly build; the coordinator
# ruled this worktree skill folder as the home for these files, and the build task forbids
# own_list_add and any write outside the worktree. Not a personal tool; never moved to ClaudeOps.
set -u

CODE_ROOT="${LIFEHACK_CODE_ROOT:-}"
if [ -z "$CODE_ROOT" ] || [ ! -f "$CODE_ROOT/shared/desk_list.py" ]; then
    echo "ERROR: LIFEHACK_CODE_ROOT is not set or has no shared/desk_list.py — cannot find the desk list" >&2
    exit 1
fi

NAME="$(python3 "$CODE_ROOT/shared/desk_list.py" planning-folder)"
RC=$?
if [ $RC -ne 0 ]; then
    # desk_list.py already printed its named error on stderr (exit 2 = no planning row).
    echo "ERROR: the planning desk's folder is unknown (desk_list.py planning-folder exited $RC)" >&2
    exit 1
fi

if [ "${1:-}" = "--relative" ]; then
    printf '%s\n' "$NAME"
    exit 0
fi

# Full path: the notes root (resolved by shared/person_roots.py, the machine's one resolver)
# joined with desks/<NAME>. No fallback, no guess: if the notes root is unset, fail loudly.
FULL="$(python3 - "$CODE_ROOT" "$NAME" <<'PY'
import os, sys
code_root, name = sys.argv[1], sys.argv[2]
sys.path.insert(0, code_root + "/shared")
try:
    import person_roots
    notes = person_roots.notes_root()
except Exception as e:
    print("ERROR: cannot resolve the notes root: %s" % e, file=sys.stderr); sys.exit(1)
if not notes:
    print("ERROR: the notes root is not set — refusing to guess the planning desk's path", file=sys.stderr); sys.exit(1)
print(os.path.join(notes, "desks", name))
PY
)"
RC=$?
if [ $RC -ne 0 ] || [ -z "$FULL" ]; then
    echo "ERROR: could not resolve the planning desk's full path (exit $RC)" >&2
    exit 1
fi
printf '%s\n' "$FULL"
