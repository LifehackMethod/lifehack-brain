#!/usr/bin/env bash
# seam.sh — the seam-leak snapshot for the skill-tester rig (card TR0.2).
#
# from ~/lifehack-v2/system/tools/tests/job-sim.sh @ 2026-10-28
#   (its embedded Python real_snapshot() / seam_leaks(): snapshot everything a rig run must never touch,
#    re-snapshot after, report the sorted union of paths whose value differs — present-before-only,
#    present-after-only, or changed). Adapted: the original keyed on mtime_ns of job locks/state; this
#    keys on sha256 content of the rig's own forbidden surfaces, and is bash 3.2 + BSD tools.
#
# What is snapshotted (each root overridable by env):
#   SEAM_STATE_ROOT   every file under the real notes root's state/
#                     default: <notes-root>/state, where <notes-root> is resolved at RUN TIME by the shared
#                     resolver $LIFEHACK_V2/shared/brain_root.py --quiet ($LIFEHACK_ROOT, the repo's .brain-root
#                     pointer, ~/.config/lifehack/brain-root, ...). Never hard-coded, never guessed: NOT-SET,
#                     PERMISSION-DENIED or a root with no state/ folder is CANNOT-READ (exit 4), never a pass —
#                     the seam must never silently watch nothing. `seam.sh state-root` prints the resolved root
#                     (run.sh uses it so the write guard denies the SAME folder the seam watches).
#   SEAM_SKILL_ROOTS  colon-separated; every SKILL.md beneath each
#                     default: ~/.claude/skills:~/lifehack-v2/.claude/skills:~/lifehack-v2/skills
#                     (~/lifehack-v2/skills does not exist today; it is recorded as ABSENT, so if it ever
#                      appears, verify reports it as a change instead of silently ignoring it)
#   SEAM_HOOKS_JSON   default: ~/lifehack-v2/hooks/hooks.json
#   SEAM_STANDIN      every file under the scratch STAND-IN for the notes folder (TR1.7): the sentinel writer's
#                     playground, inside scratch but SEAM SCOPE (the write guard denies it to the rig explicitly)
#                     default: ~/lifehack-scratch/skill-tester-rig/notes-standin (the CANONICAL scratch, whatever
#                     SKILL_TESTER_SCRATCH says, because the sentinel writes there)
#   SKILL_TESTER_SCRATCH  snapshots go to $SKILL_TESTER_SCRATCH/seam/<run-id>.sha
#                     default: ~/lifehack-scratch/skill-tester-rig
#
# EXCLUSIONS (printed on every snapshot/verify, never silent):
#   - files named .DS_Store (Finder metadata; Finder rewrites them on browse)
#   Nothing else is excluded. *.tmp files under state/ are real content there and ARE hashed.
# HOW NON-REGULAR ENTRIES ARE RECORDED (not excluded):
#   - symlinks: recorded as LINK:<readlink target> (not followed; a retarget is a change)
#   - a configured root/file that does not exist: recorded as ABSENT
# KNOWN LIMITS: find does not descend through symlinked directories (their contents are not walked; the
#   link itself is recorded under state/, and under skill roots only if the link is named SKILL.md).
#   Paths containing a tab or newline are not supported.
#
# Exits:  snapshot 0 ok / 3 a file could not be hashed (no partial snapshot is left)
#         verify   0 identical / 1 drift (every changed/added/removed path named) /
#                  4 CANNOT-READ (missing/empty snapshot; code and wording from shared/emit/verdicts.py)
#         selftest 0 = selftest ok (the inverse: every planted drift was caught), nonzero = selftest failed
#         selftest-load (TR1.7) last line 'SEAM under load denied 1/1 named ambient-only fp 0/5 actor-needs listed'
#                  (runs seam_load.sh: guard denial via F-19, sentinel mini-bite, actor-needs list)
#         state-root 0 prints the state root (SEAM_STATE_ROOT, else <notes-root>/state) / 4 CANNOT-READ
#         2 usage
set -u
set -o pipefail

V2="${LIFEHACK_V2:-$HOME/lifehack-v2}"
VERDICTS_DIR="$V2/shared/emit"
STATE_ROOT=""   # resolved lazily by resolve_state_root (snapshot/verify/state-root only)
SKILL_ROOTS="${SEAM_SKILL_ROOTS:-$HOME/.claude/skills:$V2/.claude/skills:$V2/skills}"
HOOKS_JSON="${SEAM_HOOKS_JSON:-$V2/hooks/hooks.json}"
STANDIN="${SEAM_STANDIN:-$HOME/lifehack-scratch/skill-tester-rig/notes-standin}"
SCRATCH="${SKILL_TESTER_SCRATCH:-$HOME/lifehack-scratch/skill-tester-rig}"
SEAM_DIR="$SCRATCH/seam"
TAB="$(printf '\t')"

usage() { echo "usage: seam.sh snapshot <run-id> | verify <run-id> | state-root | selftest | selftest-load" >&2; exit 2; }

valid_id() {
  case "$1" in ""|*/*|.*) echo "seam: bad run-id '$1' (no slashes, not empty, no leading dot)" >&2; exit 2;; esac
}

# CANNOT-READ, in place from the shared module (never copied): prints its verdict, exits its code.
cannot_read() {
  python3 - "$VERDICTS_DIR" "$1" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from verdicts import print_cannot_read, CANNOT_READ
print_cannot_read(sys.argv[2])
sys.exit(CANNOT_READ)
PY
  exit $?
}

# resolve_state_root: SEAM_STATE_ROOT if set (tests, explicit override), else <notes-root>/state with the notes root
# from the SHARED resolver (shared/brain_root.py, used in place, never copied). Unresolvable -> CANNOT-READ (exit 4):
# a seam that watched an empty or wrong root would report CLEAN on a run that wrote real notes.
resolve_state_root() {
  if [ -n "${SEAM_STATE_ROOT:-}" ]; then STATE_ROOT="$SEAM_STATE_ROOT"; return 0; fi
  local br="$V2/shared/brain_root.py" root
  [ -f "$br" ] || cannot_read "seam: cannot resolve the notes root: shared resolver missing ($br)"
  root="$(python3 -I -B "$br" --quiet 2>/dev/null)" \
    || cannot_read "seam: cannot resolve the notes root (shared/brain_root.py: NOT-SET or PERMISSION-DENIED); set LIFEHACK_ROOT or SEAM_STATE_ROOT"
  [ -n "$root" ] && [ -d "$root/state" ] \
    || cannot_read "seam: notes root '$root' has no state/ folder; refusing to watch nothing (set SEAM_STATE_ROOT)"
  STATE_ROOT="$root/state"
}

print_exclusions() {
  echo "seam: exclusions: files named .DS_Store (Finder metadata) — nothing else excluded"
}

# The full current picture, unsorted, to stdout: "<sha256|LINK:<target>|ABSENT>\t<path>". Nonzero (3) if anything
# failed to hash. One python walker for every root (TR1.7, "under load"): a file that VANISHES between being listed
# and being hashed (ENOENT: another writer deleted or renamed it mid-snapshot) is simply not present in this
# snapshot, exactly as if the walk had run a moment later. Before TR1.7 `find | xargs shasum` failed the whole
# snapshot on that race (exit 3 -> SEAM-CANNOT-READ), so a busy notes folder could fail a clean run. Any OTHER
# error (EACCES, EIO, ...) still fails the snapshot (exit 3). Semantics otherwise equal the old find predicates:
# state/stand-in roots = every regular file and every symlink (not followed) except .DS_Store; skill roots =
# only entries named SKILL.md; a symlinked directory is recorded as a LINK and not descended.
take() {
  python3 -I -B - "$STATE_ROOT" "$STANDIN" "$SKILL_ROOTS" "$HOOKS_JSON" <<'PYW'
import errno, hashlib, os, sys
state, standin, skills, hooks = sys.argv[1:5]
rc = 0
def gone(e): return isinstance(e, OSError) and e.errno == errno.ENOENT
def emit(v, p): sys.stdout.write("%s\t%s\n" % (v, p))
def one(p, skill_only):
    global rc
    name = os.path.basename(p)
    if name == ".DS_Store" or (skill_only and name != "SKILL.md"):
        return
    try:
        if os.path.islink(p):
            emit("LINK:" + os.readlink(p), p); return
        if not os.path.isfile(p):
            return
        v = os.environ.get("SEAM_TEST_VANISH", "")
        if v and p == v and "/seam-selftest." in p:   # selftest knob only: the race, made to happen
            os.unlink(p)
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        emit(h.hexdigest(), p)
    except OSError as e:
        if gone(e):
            return
        sys.stderr.write("seam: cannot hash %s: %s\n" % (p, e)); rc = 3
def tree(root, skill_only):
    global rc
    if not os.path.lexists(root):
        emit("ABSENT", root); return
    if os.path.islink(root) or not os.path.isdir(root):
        one(root, skill_only); return
    def err(e):
        global rc
        if not gone(e):
            sys.stderr.write("seam: cannot walk %s: %s\n" % (getattr(e, "filename", root), e)); rc = 3
    for d, dirs, files in os.walk(root, onerror=err, followlinks=False):
        for n in list(dirs):
            if os.path.islink(os.path.join(d, n)):
                one(os.path.join(d, n), skill_only)
        for n in files:
            one(os.path.join(d, n), skill_only)
tree(state, False)
tree(standin, False)
for r in skills.split(":"):
    if r:
        tree(r, True)
if os.path.islink(hooks):
    emit("LINK:" + os.readlink(hooks), hooks)
elif os.path.isfile(hooks):
    one(hooks, False)
else:
    emit("ABSENT", hooks)
sys.stdout.flush()
sys.exit(rc)
PYW
}

body_sorted() { take | LC_ALL=C sort -t "$TAB" -k2; }

cmd_snapshot() {
  valid_id "$1"
  resolve_state_root
  mkdir -p "$SEAM_DIR" || { echo "seam: cannot create $SEAM_DIR" >&2; exit 3; }
  local out="$SEAM_DIR/$1.sha" tmp="$SEAM_DIR/.$1.sha.partial" n
  print_exclusions
  {
    echo "# seam snapshot run-id=$1 created=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# state-root=$STATE_ROOT"
    echo "# skill-roots=$SKILL_ROOTS (SKILL.md only)"
    echo "# hooks-json=$HOOKS_JSON"
    echo "# standin=$STANDIN"
    echo "# excluded: files named .DS_Store"
  } > "$tmp"
  if ! body_sorted >> "$tmp"; then
    rm -f "$tmp"
    echo "seam: SNAPSHOT-FAILED — a file could not be hashed; no snapshot written" >&2
    exit 3
  fi
  mv "$tmp" "$out"
  n=$(grep -vc '^#' "$out")
  echo "seam: snapshot $1: $n entries -> $out"
}

cmd_verify() {
  valid_id "$1"
  local snap="$SEAM_DIR/$1.sha" now
  if [ ! -s "$snap" ]; then cannot_read "seam snapshot missing or empty: $snap"; fi
  resolve_state_root
  print_exclusions
  now="$(mktemp "${TMPDIR:-/tmp}/seam-now.XXXXXX")" || exit 3
  if ! body_sorted > "$now"; then rm -f "$now"; echo "seam: VERIFY-FAILED — a file could not be hashed" >&2; exit 3; fi
  # seam_leaks(): union of keys, report every key whose value differs.
  local report
  report="$(awk -F "$TAB" '
    FNR==NR { if ($0 ~ /^#/) next; before[$2]=$1; next }
    { after[$2]=$1 }
    END {
      for (p in before) { if (!(p in after)) print "REMOVED\t" p; else if (before[p]!=after[p]) print "CHANGED\t" p }
      for (p in after)  { if (!(p in before)) print "ADDED\t" p }
    }' "$snap" "$now" | LC_ALL=C sort -t "$TAB" -k2)"
  rm -f "$now"
  if [ -z "$report" ]; then
    echo "seam: verify $1: CLEAN (no real-state file changed, added or removed)"
    exit 0
  fi
  echo "seam: verify $1: LEAK — $(printf '%s\n' "$report" | wc -l | tr -d ' ') path(s) moved:"
  printf '%s\n' "$report" | sed 's/^/  /'
  exit 1
}

cmd_selftest() {
  local self fails=0 out rc
  self="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  T="$(mktemp -d "${TMPDIR:-/tmp}/seam-selftest.XXXXXX")" || exit 3
  trap 'rm -rf "$T"' EXIT
  # A throwaway tree shaped like the real roots, with spaces in paths, a symlink, a .DS_Store, a .tmp.
  mkdir -p "$T/My Drive/state/projects/a b" "$T/My Drive/state/records" \
           "$T/skills one/s1" "$T/skills two/s 2/nested" "$T/v2/hooks" "$T/scratch"
  echo alpha > "$T/My Drive/state/projects/a b/brief.md"
  echo beta  > "$T/My Drive/state/records/r1.md"
  echo draft > "$T/My Drive/state/records/map-J.tmp"
  echo junk  > "$T/My Drive/state/.DS_Store"
  ln -s "projects/a b/brief.md" "$T/My Drive/state/link-to-brief"
  echo "# s1"  > "$T/skills one/s1/SKILL.md"
  echo "# s2"  > "$T/skills two/s 2/nested/SKILL.md"
  echo "notes" > "$T/skills one/s1/README.md"
  echo '{}'    > "$T/v2/hooks/hooks.json"

  export SEAM_STATE_ROOT="$T/My Drive/state"
  export SEAM_SKILL_ROOTS="$T/skills one:$T/skills two:$T/no such root"
  export SEAM_HOOKS_JSON="$T/v2/hooks/hooks.json"
  export SKILL_TESTER_SCRATCH="$T/scratch"
  mkdir -p "$T/standin"; echo s0 > "$T/standin/n0.md"
  export SEAM_STANDIN="$T/standin"

  # check <name> <expected-exit> <path-that-must-be-named-or-empty>
  check() {
    local name="$1" want="$2" must="$3"
    out="$(bash "$self" verify st 2>&1)"; rc=$?
    local ok=1
    [ "$rc" = "$want" ] || ok=0
    if [ -n "$must" ]; then printf '%s\n' "$out" | grep -qF -- "$must" || ok=0; fi
    if [ $ok = 1 ]; then echo "  ok   $name: verify exit $rc (want $want)${must:+, named '$must'}"
    else echo "  FAIL $name: verify exit $rc (want $want)${must:+, must name '$must'}"; printf '%s\n' "$out" | sed 's/^/       | /'; fails=$((fails+1)); fi
  }
  resnap() { bash "$self" snapshot st >/dev/null 2>&1 || { echo "  FAIL snapshot itself failed"; fails=$((fails+1)); }; }

  echo "seam selftest: throwaway tree $T"
  out="$(bash "$self" verify st 2>&1)"; rc=$?
  if [ "$rc" = 4 ] && printf '%s\n' "$out" | head -1 | grep -qx 'CANNOT-READ'; then echo "  ok   missing snapshot: exit 4, CANNOT-READ"
  else echo "  FAIL missing snapshot: exit $rc, output: $out"; fails=$((fails+1)); fi

  resnap; check "unchanged tree" 0 ""
  echo junk2 > "$T/My Drive/state/.DS_Store"; check ".DS_Store edit (declared exclusion)" 0 ""
  echo more >> "$T/skills one/s1/README.md";  check "non-SKILL.md file under skill root (out of scope)" 0 ""

  resnap; echo "probe" >> "$T/My Drive/state/projects/a b/brief.md"; check "probe change in state/ (path with spaces)" 1 "CHANGED${TAB}$T/My Drive/state/projects/a b/brief.md"
  resnap; echo new > "$T/My Drive/state/records/added file.md";       check "added file" 1 "ADDED${TAB}$T/My Drive/state/records/added file.md"
  resnap; rm "$T/My Drive/state/records/r1.md";                       check "removed file" 1 "REMOVED${TAB}$T/My Drive/state/records/r1.md"
  resnap; echo "# s2 edited" > "$T/skills two/s 2/nested/SKILL.md";   check "SKILL.md edit" 1 "CHANGED${TAB}$T/skills two/s 2/nested/SKILL.md"
  resnap; echo '{"x":1}' > "$T/v2/hooks/hooks.json";                  check "hooks.json edit" 1 "CHANGED${TAB}$T/v2/hooks/hooks.json"
  resnap; rm "$T/My Drive/state/link-to-brief"; ln -s "records/map-J.tmp" "$T/My Drive/state/link-to-brief"
                                                                      check "symlink retarget" 1 "CHANGED${TAB}$T/My Drive/state/link-to-brief"
  resnap; echo "x" >> "$T/My Drive/state/records/map-J.tmp";          check ".tmp file edit (not excluded)" 1 "map-J.tmp"
  resnap; echo s1 > "$T/standin/n1.md";                               check "stand-in file added (TR1.7 scope)" 1 "ADDED${TAB}$T/standin/n1.md"
  resnap; echo s0b > "$T/standin/n0.md";                              check "stand-in file edited (TR1.7 scope)" 1 "CHANGED${TAB}$T/standin/n0.md"
  # a file that vanishes between listing and hashing is "not present", never a failed snapshot (TR1.7 under load)
  out="$(SEAM_TEST_VANISH="$T/standin/n1.md" bash "$self" snapshot st 2>&1)"; rc=$?
  if [ "$rc" = 0 ] && ! grep -q "n1.md" "$T/scratch/seam/st.sha"; then echo "  ok   file vanishing mid-snapshot: snapshot exit 0, path absent"
  else echo "  FAIL file vanishing mid-snapshot: exit $rc"; printf '%s\n' "$out" | sed 's/^/       | /'; fails=$((fails+1)); fi
  resnap; mkdir -p "$T/no such root/x"; echo "# new" > "$T/no such root/x/SKILL.md"
                                                                      check "absent root appears" 1 "$T/no such root"

  if [ $fails = 0 ]; then echo "seam selftest: OK — every planted drift caught, clean tree verified 0"; return 0; fi
  echo "seam selftest: FAILED — $fails check(s) wrong"; return 1
}

case "${1:-}" in
  snapshot) [ $# = 2 ] || usage; cmd_snapshot "$2" ;;
  verify)   [ $# = 2 ] || usage; cmd_verify "$2" ;;
  state-root) [ $# = 1 ] || usage; resolve_state_root; printf '%s\n' "$STATE_ROOT" ;;
  selftest) [ $# = 1 ] || usage; cmd_selftest; exit $? ;;
  # TR1.7: the seam under load (write guard + sentinel), proven three ways; see seam_load.sh
  selftest-load) [ $# = 1 ] || usage; exec bash "$(cd "$(dirname "$0")" && pwd)/seam_load.sh" ;;
  *) usage ;;
esac
