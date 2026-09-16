#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_plans_truncation_floor.sh" "PreToolUse" "Write|Edit|MultiEdit|Bash" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: 2026-09-16. A 493 KB plan file (~/.claude/plans/lifehack-migration.plan.md) was
#      flattened to 28 bytes THREE TIMES in one morning. Root cause (system/journal.md,
#      2026-09-16, the correction entry): a hook script's own header comment quoted the
#      example `tee ~/.claude/plans/lifehack-migration.plan.md << EOF ... EOF` IN
#      BACKTICKS inside a double-quoted `python3 -c "..."` block -- bash performs command
#      substitution inside double quotes too, so the guard EXECUTED its own documentation
#      every time it fired, truncating the file to whatever the tee's heredoc happened to
#      hold. Nothing in this repo was watching ~/.claude/plans/ at all: it is a 140+ file,
#      multi-window, unowned shared surface with no per-file lock and, until this guard,
#      no floor. ⚠ HONEST SCOPE, stated once here rather than discovered later: that exact
#      incident is STRUCTURALLY INVISIBLE to this guard (or any PreToolUse hook) -- the
#      destructive write was a side effect of another hook's OWN shell execution, never a
#      distinguishable Bash/Write/Edit tool call the harness dispatches through PreToolUse.
#      A hook can only gate the tool-call boundary; it cannot see a write performed inside
#      another process's own script body, a cron job, or anything outside Claude Code
#      entirely. What this guard DOES cover: the much larger and more common class of
#      write -- an ordinary Write/Edit tool call, or a Bash tool call whose command
#      literally names a path under the plans directory -- ever leaving a plan file that
#      was substantial below a floor, whoever or whatever issues that call next.
# GUARDS: a Write/Edit/MultiEdit call that would leave a file under $HOME/.claude/plans/
#      (override: $LHB_PLANS_DIR) below $LHB_PLANS_FLOOR_BYTES (default 4096) bytes, when
#      that file was AT OR ABOVE the floor beforehand -- sized EXACTLY, since these tools
#      hand over the full resulting content (Write) or an old/new-string delta simulated
#      against the real on-disk bytes (Edit/MultiEdit). And a Bash call whose command is an
#      OVERWRITE-shaped write (never an append -- `>>`/`tee -a` are structurally incapable
#      of truncating and are scrubbed before analysis) to a plans-dir file already at/above
#      the floor: a shell overwrite's resulting size cannot be known before it runs, so --
#      same reasoning as system/hooks/guard_brief_truncation.sh's own Bash door -- ANY such
#      write is gated unconditionally, not sized. A brand-new plan file (nothing on disk
#      yet) can never trigger this: creation is always allowed.
# REDIRECT: two doors out, both stated in the deny text every time:
#      (1) INTENDED shrink (e.g. archiving/retiring a finished plan) -- set
#          LHB_PLANS_FLOOR_OVERRIDE=<the exact absolute path being shrunk> for that one
#          call and retry. Scoped to that literal path; never a blanket disable, and this
#          guard still writes its own dated backup first even when the override fires.
#      (2) UNINTENDED -- the write is refused and a dated snapshot of the pre-write file
#          already exists beside it (`<path>.<UTC timestamp>.preshrink.bak`), made BEFORE
#          the refusal is emitted, so recovery never depends on the session having backed
#          up first by hand.
# SIGNPOST: rule lives in system/sops/hook-sop.md + system/hook-contract.md; the shape is
#      system/hooks/guard_brief_truncation.sh (three-doors-in, snapshot-not-guess-on-Bash)
#      and its shared library system/hooks/lib/bash_write_door.sh; the incident is
#      system/journal.md, 2026-09-16 (both the original entry and same-day correction).
#      Change the floor, the plans-dir path, or this guard's shape there first.
# FAIL_POSTURE: mixed, deliberately, same convention as guard_brief_truncation.sh.
#      Not-our-business (wrong tool, path outside the plans dir, brand-new file, file
#      already below the floor) exits 0 -- this runs on every Bash/Write/Edit/MultiEdit
#      call system-wide, and a blanket deny on a transient glitch would be worse than the
#      gap. Once a plans-dir file AT the floor is identified as the target, any failure to
#      size the write, or to load lib/bash_write_door.sh, DENIES -- an unreadable payload
#      and an unsafe one must never look the same.
# UPDATED: 2026-09-16
# ─────────────────────────────────────────────────────────────────────────────
INPUT=$(cat)

_HOOKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FLOOR_BYTES="${LHB_PLANS_FLOOR_BYTES:-4096}"
PLANS_DIR="${LHB_PLANS_DIR:-$HOME/.claude/plans}"
OVERRIDE="${LHB_PLANS_FLOOR_OVERRIDE:-}"
# Normalized ONCE, the same way every candidate $path below is normalized (expanduser +
# normpath), so a trailing slash, a doubled slash, or a "~" in the override value still
# matches -- the comparison in handle_violation() is a plain string equality against an
# already-canonical form on both sides.
if [ -n "$OVERRIDE" ]; then
  OVERRIDE=$(python3 -c '
import os, sys
print(os.path.normpath(os.path.expanduser(sys.argv[1])))
' "$OVERRIDE" 2>/dev/null)
fi

deny() {
  python3 -c '
import json,sys
print(json.dumps({"decision":"block","reason":sys.argv[1]}))
' "$1" >&2
  exit 2
}

# make_backup <path> -> prints the backup path on success, nothing on failure. A DATED
# sibling file, never overwritten by a later call, so more than one refusal in a session
# leaves the whole trail rather than clobbering the previous snapshot.
make_backup() {
  local target="$1" ts backup
  ts=$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || date +%Y%m%dT%H%M%SZ)
  backup="${target}.${ts}.preshrink.bak"
  if cp -p "$target" "$backup" 2>/dev/null; then
    printf '%s' "$backup"
  fi
}

# handle_violation <path> <old_size> <new_size|UNKNOWN> -- always exits (0 via the named
# override, 2 via deny). Never returns.
handle_violation() {
  local path="$1" old="$2" new="$3" backup backup_line size_line
  backup=$(make_backup "$path")

  if [ -n "$OVERRIDE" ] && [ "$OVERRIDE" = "$path" ]; then
    printf 'NOTICE: guard_plans_truncation_floor override applied for %s (dated backup: %s)\n' \
      "$path" "${backup:-NONE -- cp failed, proceeding on the override alone}" >&2
    exit 0
  fi

  if [ -n "$backup" ]; then
    backup_line="BACKUP: a dated pre-shrink snapshot was written to $backup BEFORE this refusal."
  else
    backup_line="BACKUP FAILED: could not write a snapshot beside $path -- refusing anyway; copy it out by hand before retrying."
  fi
  if [ "$new" = "UNKNOWN" ]; then
    size_line="this $TOOL command targets $path (currently $old bytes, at/above the ${FLOOR_BYTES}-byte floor) with an overwrite-shaped write whose resulting size cannot be known before it runs"
  else
    size_line="this $TOOL would leave $path at $new bytes, below the ${FLOOR_BYTES}-byte floor (was $old bytes)"
  fi

  deny "BLOCKED: $size_line. WHY: on 2026-09-16 a 493 KB plan file (~/.claude/plans/lifehack-migration.plan.md) was flattened to 28 bytes three times in one morning because nothing watched that directory (system/journal.md, 2026-09-16). $backup_line REDIRECT: if this shrink is INTENDED (e.g. archiving a finished plan), set LHB_PLANS_FLOOR_OVERRIDE=$path for this one call and retry -- the override is scoped to this exact path, never a blanket disable. RULE: system/sops/hook-sop.md + system/hook-contract.md; shape: system/hooks/guard_brief_truncation.sh."
}

TOOL=$(printf '%s' "$INPUT" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('tool_name',''))
except Exception: print('')
" 2>/dev/null)

case "$TOOL" in
  Write|Edit|MultiEdit|Bash) ;;
  *) exit 0 ;;
esac

if [ "$TOOL" = "Bash" ]; then
  COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys,json
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception: print('')
" 2>/dev/null)
  [ -z "$COMMAND" ] && exit 0

  # Cheap pre-filter: no plans-dir-shaped path mentioned at all -> not our business.
  printf '%s' "$COMMAND" | grep -qF '.claude/plans' || exit 0

  # shellcheck source=lib/bash_write_door.sh
  . "$_HOOKDIR/lib/bash_write_door.sh" 2>/dev/null || \
    deny "BLOCKED: guard_plans_truncation_floor could not load lib/bash_write_door.sh, so it is failing closed. This command names a path under .claude/plans and the Bash door into that directory is unguarded without the library. REDIRECT: restore system/hooks/lib/bash_write_door.sh from git, then retry. RULE: system/sops/hook-sop.md."

  # Append-only shapes cannot truncate. Neutralise them, then ask the library again.
  SCRUBBED=$(printf '%s' "$COMMAND" | sed -e 's/>>/ /g' -e 's/tee[[:space:]]\{1,\}-a/tee_append_noop/g')

  TARGETS=$(bwd_write_targets "$SCRUBBED")
  case "$TARGETS" in
    *__BWD_PARSE_ERROR__*)
      deny "BLOCKED: guard_plans_truncation_floor could not analyse this command, and it names a path under .claude/plans. WHY: an unparseable command targeting the plans directory is refused rather than guessed at, and no backup can be made because the target path itself could not be determined with confidence. REDIRECT: write the plan file through the Write tool instead, or simplify the command so its target is a literal path. RULE: system/sops/hook-sop.md."
      ;;
  esac

  # Find a TARGET that resolves under PLANS_DIR. bwd_write_targets emits either a bare
  # path (a real shell redirect/writer verb -- EXACT) or, for an interpreter, the WHOLE
  # write expression -- open('.../plans/x.md','w').write(y) -- with the plans-dir path
  # embedded inside it (EMBED), same shape as guard_brief_truncation.sh's own HIT search.
  # Resolving the path HERE (once, in the same python call) instead of re-deriving it
  # from the matched text later avoids a second, more error-prone round of quote/escape
  # stripping on a string that may itself contain quotes.
  HIT=$(printf '%s\n' "$TARGETS" | PLANS_DIR="$PLANS_DIR" python3 -c '
import sys, os, re

plans_dir = os.path.normpath(os.path.expanduser(os.environ.get("PLANS_DIR", "")))
home = os.path.expanduser("~")

def resolved(cand):
    c = cand.replace("$HOME", home).replace("${HOME}", home)
    return os.path.normpath(os.path.expanduser(c))

def under_plans(p):
    return p == plans_dir or p.startswith(plans_dir + os.sep)

for line in sys.stdin:
    tok = line.rstrip("\n")
    if not tok:
        continue
    p = resolved(tok)
    if under_plans(p):
        print("EXACT|" + p); break
    hit_path = None
    for m in re.finditer(r"[^\s\x27\"()]+", tok):
        p2 = resolved(m.group(0))
        if under_plans(p2):
            hit_path = p2; break
    if hit_path:
        print("EMBED|" + hit_path); break
' 2>/dev/null)

  [ -z "$HIT" ] && exit 0    # append-only, a read, or the plans dir was only mentioned

  MODE="${HIT%%|*}"
  RESOLVED="${HIT#*|}"

  # NARROWING, same false-positive class guard_brief_truncation.sh already closed: an
  # ordinary READ -- python3 -c "print(len(open(path).read()))" -- must never be denied.
  # EXACT (a bare shell redirect/writer-verb target) is trusted outright; EMBED (dug out
  # of a larger interpreter expression) only counts with real mutation evidence in the
  # command, since a bare `open(` alone is not proof of a write.
  if [ "$MODE" = "EMBED" ]; then
    printf '%s' "$COMMAND" | grep -qE "\\.write[a-zA-Z]*\\(|\\.truncate\\(|open\\([^)]*,[[:space:]]*['\"][^'\"]*[wax+]|os\\.(replace|rename|remove|unlink)|shutil\\.(move|copy)|write_text|writeFileSync" \
      || exit 0
  fi

  [ -z "$RESOLVED" ] && exit 0
  [ -f "$RESOLVED" ] || exit 0   # a brand-new file cannot be truncated

  OLD_SIZE=$(stat -c %s "$RESOLVED" 2>/dev/null || stat -f %z "$RESOLVED" 2>/dev/null || echo "")
  [ -z "$OLD_SIZE" ] && deny "BLOCKED: guard_plans_truncation_floor could not stat $RESOLVED after identifying it as an overwrite target under the plans directory. REDIRECT: retry; if this persists, check file permissions. RULE: system/sops/hook-sop.md."
  [ "$OLD_SIZE" -lt "$FLOOR_BYTES" ] && exit 0   # was never substantial -- nothing to protect

  # A Bash overwrite's resulting size cannot be known before it runs -- same reasoning
  # system/hooks/guard_brief_truncation.sh already applies to this exact door. Any
  # confirmed overwrite-shaped write to a plans file already at/above the floor is
  # therefore gated unconditionally, not sized.
  handle_violation "$RESOLVED" "$OLD_SIZE" "UNKNOWN"
  exit 0
fi

# ── typed tools: Write / Edit / MultiEdit -- these we CAN size exactly ──────
printf '%s' "$INPUT" | grep -qF '.claude/plans' || exit 0

RESULT=$(printf '%s' "$INPUT" | TOOL="$TOOL" PLANS_DIR="$PLANS_DIR" FLOOR_BYTES="$FLOOR_BYTES" python3 -c '
import sys, json, os

def blen(s):
    return len((s or "").encode("utf-8"))

def under_plans(path, plans_dir):
    if not path:
        return False
    p = os.path.normpath(os.path.expanduser(path))
    d = os.path.normpath(os.path.expanduser(plans_dir))
    return p == d or p.startswith(d + os.sep)

try:
    data = json.loads(sys.stdin.read())
except Exception:
    print("ERROR|unparseable tool payload|")
    sys.exit(0)

tool = os.environ.get("TOOL", "")
plans_dir = os.environ.get("PLANS_DIR", "")
try:
    floor = int(os.environ.get("FLOOR_BYTES", "4096"))
except ValueError:
    floor = 4096

ti = data.get("tool_input", {}) or {}
path = ti.get("file_path", "") or ""

if not under_plans(path, plans_dir):
    print("SKIP||"); sys.exit(0)

path = os.path.normpath(os.path.expanduser(path))

if not os.path.isfile(path):
    print("SKIP||"); sys.exit(0)   # creating a new plan file cannot shrink one

try:
    old_size = os.path.getsize(path)
except OSError:
    print("ERROR|cannot stat the plan file|" + path); sys.exit(0)

if old_size < floor:
    print("SKIP||"); sys.exit(0)   # was never substantial -- nothing to protect

try:
    if tool == "Write":
        new_size = blen(ti.get("content"))
    elif tool in ("Edit", "MultiEdit"):
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
            content = f.read()
        if tool == "Edit":
            edits = [{
                "old_string": ti.get("old_string", ""),
                "new_string": ti.get("new_string", ""),
                "replace_all": bool(ti.get("replace_all", False)),
            }]
        else:
            edits = ti.get("edits") or []
        for e in edits:
            old_s = e.get("old_string", "")
            new_s = e.get("new_string", "")
            if not old_s or old_s not in content:
                # Cannot simulate this edit faithfully -- the real tool would
                # error on it (or it is a no-op old_string); not this guard
                # own business either way.
                print("SKIP||"); sys.exit(0)
            if e.get("replace_all"):
                content = content.replace(old_s, new_s)
            else:
                content = content.replace(old_s, new_s, 1)
        new_size = blen(content)
    else:
        print("SKIP||"); sys.exit(0)
except Exception:
    print("ERROR|cannot size the write|" + path); sys.exit(0)

if new_size >= floor:
    print("SKIP||"); sys.exit(0)

print("VIOLATION|%s|%d|%d" % (path, old_size, new_size))
' 2>/dev/null)

case "$RESULT" in
  SKIP*|"") exit 0 ;;
  ERROR*)
    msg=$(printf '%s' "$RESULT" | cut -d'|' -f2)
    deny "BLOCKED: guard_plans_truncation_floor identified a plans-directory file as the write target but could not size the write ($msg). WHY: an unreadable payload and an unsafe one must never look the same once the target is identified. REDIRECT: retry; if this persists, check the file is readable and the JSON payload is well-formed. RULE: system/sops/hook-sop.md."
    ;;
  VIOLATION*)
    path=$(printf '%s' "$RESULT" | cut -d'|' -f2)
    old=$(printf '%s'  "$RESULT" | cut -d'|' -f3)
    new=$(printf '%s'  "$RESULT" | cut -d'|' -f4)
    handle_violation "$path" "$old" "$new"
    ;;
esac

exit 0
