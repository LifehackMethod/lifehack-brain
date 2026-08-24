#!/usr/bin/env bash
# ── hook-doc-lint — enforce the Hook Self-Documentation Rule ──────────────────
# WHY: Every hook must self-explain (WHY/GUARDS/REDIRECT/UPDATED) so a fresh
#      session that trips it understands why and where to go instead. This lint
#      makes that rule mechanically enforceable — it can't silently drift.
# GUARDS: read-only over system/hooks/*.sh — writes only the maintenance-due
#      flag under the resolved brain root; never touches a hook file itself.
# REDIRECT: <brain root>/system/logs/maintenance-due.md (skipped, never guessed
#      at, when no brain root is configured — see the DRIVE check below).
# RUN:  bash system/tools/hook-doc-lint.sh            (report; exit 1 if any fail)
#       Not yet wired to a scheduled job in this repo — run it by hand, or wire it into your own
#       cron/Pulse config if you want it weekly.
# UPDATED: 2026-08-22
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # residency: code from clone
HOOKS="$CODE_ROOT/system/hooks"

# The notes root, through the ONE resolver — never a hardcoded personal Drive path.
DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
FLAG="${DRIVE:+$DRIVE/system/logs/maintenance-due.md}"

pass=0; fail=0; failed_list=""

for f in "$HOOKS"/*.sh; do
  [ -e "$f" ] || continue
  n=$(basename "$f"); miss=""
  grep -q "LLM CONTEXT" "$f" || miss="$miss CONTEXT"
  grep -q "^# WHY:"      "$f" || miss="$miss WHY"
  grep -q "^# GUARDS:"   "$f" || miss="$miss GUARDS"
  grep -q "^# REDIRECT:" "$f" || miss="$miss REDIRECT"
  grep -q "^# UPDATED:"  "$f" || miss="$miss UPDATED"
  if [ -z "$miss" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); failed_list="$failed_list\n  FAIL $n — missing:$miss"
    printf "  FAIL %-30s missing:%s\n" "$n" "$miss"
  fi
done

echo "hook-doc-lint: $pass pass / $fail fail (of $((pass+fail)) hooks in system/hooks/)"

if [ "$fail" -gt 0 ]; then
  if [ -n "$FLAG" ]; then
    # Surface via the maintenance-due flag (see system/organism/elements/pulse-cron.md)
    {
      echo "# Maintenance Due"
      echo ""
      echo "## hook-doc-lint — $(date '+%Y-%m-%d %H:%M')"
      echo "$fail hook(s) missing the mandatory LLM CONTEXT block:"
      printf "%b\n" "$failed_list"
      echo ""
      echo "Fix: add WHY/GUARDS/REDIRECT/UPDATED to each hook listed above."
    } > "$FLAG" 2>/dev/null
  else
    echo "[hook-doc-lint] no notes root configured — skipping the maintenance-due flag write" \
      "(set one: python3 shared/brain_root.py --set <folder>)"
  fi
  exit 1
fi
exit 0
