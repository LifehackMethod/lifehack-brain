#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_cloud_destructive.sh" "PreToolUse" "Bash" 2>/dev/null || true' EXIT
. "$_lhb_dir/lib/watch_gate.sh" 2>/dev/null && watch_gate guard_cloud_destructive.sh  # Round D B.5: watch-only mode (no-op unless mode=watch / LIFEHACK_WATCH=1)
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: D-F11 (2026-11-01): a sandbox session trashed 899 real Drive files from a `python3 -I - <<'E'` loop, and no
#      hook knew gcloud, gsutil, rclone, aws, or a curl DELETE to googleapis.com at all. A cloud delete is fine china:
#      no local copy, often no undo. The protection is an ASK, never a block.
# GUARDS: PreToolUse Bash. One switch in system/hooks/roundB.conf: fc_cloud_destructive_ask (OFF = does nothing).
#      gcloud delete/rm verbs; gsutil rm/rb/rsync -d; rclone delete/deletefile/purge/rmdir(s)/cleanup/dedupe/move/sync;
#      aws s3 rm/rb/mv, sync --delete, delete-*/terminate-*; curl/wget DELETE (or a trashing PATCH/POST) to
#      *.googleapis.com; gws permissions/emptyTrash/delete/batchDelete across drive, gmail, calendar, sheets; the same
#      inside sh -c, python/node -c|-e bodies, interpreter-executed heredocs, argv lists and subprocess shell strings.
#      Engine and exact rules: lib/cloud_guard.py header. `gws drive files update` + trashed belongs to
#      guard_drive_destructive.sh (one owner per verb).
# REDIRECT: it is an ASK (harness permissionDecision "ask"); nobody is stuck. Show the person what will go and how many;
#      their Yes is the confirmation. Headless runs turn it into a refusal: stop and tell the person.
# WHO-COULD-THIS-BREAK: an unattended job that cleans its own bucket or remote; any session syncing with rclone sync.
#      WAY-THROUGH: the person answers Yes, or turns the switch off.
# SIGNPOST: logic in lib/cloud_guard.py; tests in tests/test_cloud_destructive_guard.sh.
# LIMITS: static text only. A script file written earlier and run later by name, code a script imports, obfuscated or
#      run-time-built text (base64/eval, "dr"+"ive", verbs from env/config), code fetched at run time, cron/launchd
#      jobs: not seen. A speed bump, not a boundary; the boundary is credential scope.
# FAIL_POSTURE: open on any internal error (stderr line), because it sits in front of every Bash command.
# UPDATED: 2026-11-02
# ─────────────────────────────────────────────────────────────────────────────
. "$_lhb_dir/lib/roundb.sh" 2>/dev/null || exit 0
roundb_on fc_cloud_destructive_ask || exit 0
IFS= read -r -d '' PAYLOAD || true
[ -n "$PAYLOAD" ] || exit 0
printf '%s' "$PAYLOAD" | grep -qiE 'gws|gcloud|gsutil|rclone|aws|curl|wget|googleapis|\.delete|emptyTrash|trashed|(files|drives|permissions|messages|threads|events)\(\)' || exit 0
printf '%s' "$PAYLOAD" | python3 "$_lhb_dir/lib/cloud_guard.py" || echo "guard_cloud_destructive: engine failed; allowing" >&2
exit 0
