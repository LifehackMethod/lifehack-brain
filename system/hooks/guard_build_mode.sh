#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_build_mode.sh" "PreToolUse" "Bash|Write|Edit|MultiEdit" 2>/dev/null || true' EXIT
. "$_lhb_dir/lib/watch_gate.sh" 2>/dev/null && watch_gate guard_build_mode.sh  # Round D B.5: watch-only mode (no-op unless mode=watch / LIFEHACK_WATCH=1)
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: v2 plan 3.2 + 3.4. Sessions build skills/jobs/hooks/desks without opening the rulebook, and copy
#      shared tools into desks (68 drifted copies). A prompt reminder is not enough at write time.
# GUARDS: PreToolUse Bash|Write|Edit|MultiEdit.
#   A  speed bump: the FIRST attempt per kind (skill|job|hook|desk) per session is denied (exit 2) with
#      "Looks like you're building a <kind> -- read <SOP>, or use /build". The identical retry passes.
#      "No block" means no LASTING block. Marker: ~/.claude/run/build-mode/<kind>.<session>.seen
#   B  copy block: HARD (exit 2, every time) when a cp/mv/rsync source is under <code>/shared/, or a desk
#      file is created with a DISTINCTIVE shared-tool basename. GENERIC basenames (paths.py, registry.py,
#      verdicts.py + __init__/utils/config...) get the speed bump instead. Wrappers (12 lines or fewer
#      naming /shared/, or a '# wraps-shared:' marker in the first 10 lines) pass. Names are read from
#      system/register/register.jsonl at run time (cached on its mtime+size).
#      Generic = in a small fixed list OR a single-word stem (no _ or -): today that computes to
#      paths, registry, verdicts. Compound names (notify-governor, ingest_gate...) are tool identities.
#   C  placement (3.2c): a NEW file whose kind does not match where it is going (code into your notes folder;
#      personal notes into the harness repo) gets the speed bump once per rule per session. Never hard.
#      The list: system/hooks/placement.conf (+ optional ~/.config/lifehack/placement.conf). Data files
#      (.json/.jsonl/.csv, logs) are never listed, so always allowed.
#      A folder the person listed by hand as `kept TAB <folder>` in ~/.config/lifehack/placement.conf (read by shared/tools/own_list_add.kept_folders)
#      is never asked about again for code-outside-homes. (The reason gate and remember_reason switches were removed 2026-11-01: they never fired.)
#      2026-11-02 placement_route_sign (exam D-B06): every stop here names the one route (e.g. <personal code>/tools/<name> + the own_list_add command) instead of "retry"; same triggers, still once per session, never hard.
#      2026-11-02 fc_python_canon_block (with fc_shell_overwrite): a PYTHON overwrite of an SOP/canon file in an executed -c/heredoc body gets the same hard block and message.
#      2026-11-03 desk_tool_sign (exam D-B07 r2): the same once-per-session stop on a new tool going loose in the personal code folder when the person just named one real desk (placement.conf desk-tool-loose, lib/desk_said.py).
#      Round C fc_shell_overwrite: a Bash overwrite (`>`, `>|`, `tee` without -a, cp/mv/install/rsync onto, `sed -i`, `truncate`) of an
#      EXISTING SOP (a .md in the rulebook folders of build_mode_sops.conf) or canon file is a HARD block (exit 2). `>>` and `tee -a` pass.
#      Round C gap closure: the same check reads through `bash -c`/`sh -c`/`eval`, `env`/`exec`/`nohup`/`time` prefixes, and `dd of=` (oflag=append passes).
# Round D: the same switch also ASKS (never blocks) before a Bash overwrite of an existing non-empty DATA file (csv tsv json jsonl yaml yml toml xml xlsx xls ods parquet ini sql, .env); tmp, throwaway, git-ignored, new/empty and last-10-minutes files never ask.
# WHO-COULD-THIS-BREAK (fc_shell_overwrite): a session or the person's own script that regenerates an SOP/canon file with a redirect, sed -i or cp. WAY-THROUGH: change it with the Edit tool (the Write-side guards govern it), or ask the person.
# REDIRECT: every deny names the SOP or the shared path to use instead.
# SIGNPOST: SOP paths: system/hooks/build_mode_sops.conf (edit there when the rulebook sort renames files).
#      Logic: system/hooks/lib/build_mode.py. Tests: system/hooks/tests/test_guard_build_mode.sh.
#      Design: notes root state/projects/v2/records/2026-10-29-build-mode-hook-design.md.
# FAIL_POSTURE: degrade-safe (deliberate, see the design record). ANY internal error (parse failure,
#      missing register, missing code-root pointer, python crash) allows (exit 0) and writes a line to
#      stderr. The only exit-2 paths are the deliberate denies. (The 09-08 outage: one broken Bash hook
#      blocked every Bash call.)
# LIMITS: a speed bump, not a boundary -- Bash is matched as text (python -c, variables, $(...) get past).
# ─────────────────────────────────────────────────────────────────────────────
IFS= read -r -d '' PAYLOAD || true
[ -n "$PAYLOAD" ] || exit 0
# Cheap pre-filter, no fork: look only inside tool_input and only for the strings a build act contains.
BODY="${PAYLOAD#*\"tool_input\"}"
go=0
case "$BODY" in
  *"worktree add"*|*skills/*|*desks*|*hooks/*|*hooks.json*|*settings*.json*|*jobs.md*|*-run.sh*|*.plist*|*/shared/*) go=1 ;;
esac
if [ "$go" -eq 0 ]; then
  # placement pre-filter (builtins only): known roots from the code-root pointer and the notes-root cache
  _code=""; _notes=""
  [ -r "$HOME/.config/lifehack/code-root" ] && read -r _code < "$HOME/.config/lifehack/code-root" 2>/dev/null
  [ -r "$HOME/.claude/run/build-mode/notes-root" ] && { IFS=$'\t' read -r _c _notes < "$HOME/.claude/run/build-mode/notes-root"; } 2>/dev/null
  if [ -z "$_notes" ]; then
    case "$BODY" in *.sh*|*.py*|*.md*) go=1 ;; esac   # cache not warmed yet: let the engine resolve and cache it
  else
    case "$BODY" in *"$_notes"/*) case "$BODY" in *.sh*|*.py*) go=1 ;; esac ;; esac
  fi
  if [ "$go" -eq 0 ] && [ -n "$_code" ]; then
    case "$BODY" in
      *"$_code"/state/*|*"$_code"/data/*|*"$_code"/memory/*|*"$_code"/records/*|*"$_code"/desks/*) go=1 ;;
    esac
  fi
  if [ "$go" -eq 0 ]; then   # Round C 4 (fc_shell_overwrite): a command that names an SOP or canon file
    # *sops* not *sops/*: after `cd .../sops && echo x > a.md` the text has no "sops/" (D-F04 follow-up, cd chains)
    case "$BODY" in *sops*|*canon*) { . "${_lhb_dir}/lib/roundb.sh" && { roundb_on fc_shell_overwrite || roundb_on fc_archive_before_cut; } && go=1; } 2>/dev/null ;; esac
  fi
  if [ "$go" -eq 0 ]; then   # Round D miss fix (fc_shell_overwrite): a command that names a data file (csv json yaml ...)
    case "$BODY" in *.csv*|*.tsv*|*.json*|*.ndjson*|*.yaml*|*.yml*|*.toml*|*.xml*|*.xls*|*.ods*|*.parquet*|*.ini*|*.sql*|*.env*) { . "${_lhb_dir}/lib/roundb.sh" && roundb_on fc_shell_overwrite && go=1; } 2>/dev/null ;; esac
  fi
  if [ "$go" -eq 0 ]; then   # placement rule 4 (switch placement_outside_homes): new code can be anywhere, so let the engine look
    case "$BODY" in *.sh*|*.py*|*SKILL.md*) { . "${_lhb_dir}/lib/roundb.sh" && { roundb_on placement_outside_homes || roundb_on desk_tool_sign; } && go=1; } 2>/dev/null ;; esac
  fi
fi
[ "$go" -eq 1 ] || exit 0
PY="${_lhb_dir}/lib/build_mode.py"
[ -f "$PY" ] || { echo "guard_build_mode: $PY missing; allowing" >&2; exit 0; }
printf '%s' "$PAYLOAD" | python3 "$PY"
rc=$?
if [ "$rc" -eq 2 ]; then exit 2; fi
[ "$rc" -eq 0 ] || echo "guard_build_mode: engine exited $rc; allowing" >&2
exit 0
