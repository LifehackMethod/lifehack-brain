#!/usr/bin/env bash
# obsidian-reindex.sh — rebuild the machine-local Obsidian vault search index, then prune archived-copy nodes.
#
# ENVELOPE ONLY (self-monitoring 5.7): what the reindex DOES is unchanged from the donor (pinned `obsidian-brain@1.7.24 index`,
# then obsidian-prune-archive.mjs). What changed is how it runs and reports:
#   - paths resolve from this script's own location (or LIFEHACK_CODE_ROOT), never a dirname/../.. pinned to an old tree;
#   - the shared lock (runner-lock.lib.sh) records its owner pid; contention and an unreadable vault mount STAND DOWN (75), never 0;
#   - no step's errors are silenced: a failed index, prune or write exits non-zero and names the step on stderr;
#   - a RECEIPT is written only after kg.db is verified newer than the run start and non-empty:
#       ~/.config/lifehack/obsidian-reindex/last-index.txt   "obsidian-reindex ok index_rc=0 prune_rc=0 db_bytes=<n> at=<ISO>"
#   - the npx version pin and npx-cache path are fragile: a missing cached version fails loudly with a named message. Nothing is installed.
#
# WHY the lock + watchdog (2026-06-01): a wedged Drive mount let bare reindex runs pile up and helped stall the machine's I/O.
# At most ONE indexer runs; it is not launched if the vault root is unreadable; it is killed if it overruns (no `timeout` binary here).
#
# USAGE: obsidian-reindex.sh [--dry]
#   --dry  does everything EXCEPT the reindex and the prune: checks paths, the lock, the node/npx tools and the npx cache,
#          prints what it would do, writes no receipt.
# EXIT:  0 ok · 75 stood down (lock held by a live run, or vault mount unreadable) · 1 any failure (step named on stderr)
#        · 2 infra missing (tool or npx cache absent) · otherwise the failing step's own non-zero rc.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_ROOT="${LIFEHACK_CODE_ROOT:-$(cd "$HERE/../.." && pwd)}"

JOB="obsidian-reindex"
OB_VERSION="1.7.24"
OB_CACHE_ID="271d0627516ce9e8"   # the npx cache built for the node in use (the prune script imports the package from it)
TIMEOUT="${OBSIDIAN_REINDEX_TIMEOUT:-300}"   # hard cap on the indexer, seconds
DRY=0
case "${1:-}" in
  --dry) DRY=1 ;;
  '') ;;
  *) echo "[$JOB] usage: $0 [--dry]" >&2; exit 64 ;;
esac

die()  { echo "[$JOB] STEP $1 FAILED: $2" >&2; exit "${3:-1}"; }
note() { echo "[$JOB] $*"; }

# ── Drive spine root: resolved, never typed (the mount dir is named for the account) ─────────────────────────────────
_drive_root() {
  if [ -n "${CLAUDEOPS_DRIVE:-}" ]; then printf '%s' "$CLAUDEOPS_DRIVE"; return 0; fi
  local _m="$HOME/Library/CloudStorage" _c
  for _c in "$_m"/GoogleDrive-*/"My Drive"/_ClaudeOps; do
    if [ -d "$_c" ]; then printf '%s' "$_c"; return 0; fi
  done
  printf '%s' "$_m/GoogleDrive-UNRESOLVED/My Drive/_ClaudeOps"
}
DRIVE="$(_drive_root)"
DATA_DIR="$HOME/.local/share/obsidian-brain"
DB="$DATA_DIR/kg.db"
PRUNE_SCRIPT="$HERE/obsidian-prune-archive.mjs"
OB_DIST="${OBSIDIAN_BRAIN_DIST:-$HOME/.npm/_npx/$OB_CACHE_ID/node_modules/obsidian-brain/dist}"
RCPT_DIR="$HOME/.config/lifehack/$JOB"
RCPT="$RCPT_DIR/last-index.txt"

# ── single-instance lock (shared lib; records the owner pid). 75 = a live run holds it, 1 = corrupt lock ────────────
LOCKDIR="${LIFEHACK_RUNNER_LOCK_ROOT:-/tmp}/claudeops-${JOB}.lock"
. "$CODE_ROOT/system/tools/runner-lock.lib.sh" || { echo "[$JOB] FATAL: cannot source runner-lock.lib.sh under $CODE_ROOT" >&2; exit 1; }
runner_lock_acquire "$LOCKDIR" 1800 "$JOB" || exit $?
OUT=""
cleanup() { rm -rf "$LOCKDIR"; [ -n "$OUT" ] && rm -f "$OUT"; }
trap cleanup EXIT

# ── tools + npx cache: fail loudly and by name, install nothing ──────────────────────────────────────────────────────
for _t in node npx; do
  command -v "$_t" >/dev/null || die "preflight" "'$_t' not found on PATH" 2
done
[ -f "$PRUNE_SCRIPT" ] || die "preflight" "prune script missing: $PRUNE_SCRIPT" 2
_have=0
for _pj in "$HOME"/.npm/_npx/*/node_modules/obsidian-brain/package.json; do
  [ -f "$_pj" ] && grep -q "^  \"version\": \"$OB_VERSION\"" "$_pj" && { _have=1; break; }
done
[ "$_have" -eq 1 ] || die "npx-cache" "obsidian-brain@$OB_VERSION is not in any ~/.npm/_npx cache, and the run is --offline; refusing to install. Seed the cache by hand once, then re-run." 2
[ -f "$OB_DIST/store/db.js" ] && [ -f "$OB_DIST/store/nodes.js" ] \
  || die "npx-cache" "the prune script's build is missing: $OB_DIST/store/{db,nodes}.js (cache $OB_CACHE_ID, obsidian-brain@$OB_VERSION). Refusing to install." 2
grep -q "^  \"version\": \"$OB_VERSION\"" "$OB_DIST/../package.json" \
  || die "npx-cache" "$OB_DIST/../package.json is not obsidian-brain@$OB_VERSION" 2

# ── vault mount preflight: unreadable -> stand down 75 (bounded by its own 15 s watchdog in case the ls itself hangs) ──
( ls "$DRIVE" >/dev/null ) 2>&1 & pf=$!
( sleep 15; kill -9 "$pf" ) >/dev/null 2>&1 & pfwd=$!
disown "$pfwd"
wait "$pf"; pf_rc=$?
kill "$pfwd" >/dev/null 2>&1
if [ "$pf_rc" -ne 0 ]; then
  echo "[$JOB] vault root unreadable (mount wedged?) rc=$pf_rc: $DRIVE — standing down" >&2
  exit 75
fi

[ -f "$DB" ] || note "WARN: $DB does not exist yet — the index will be built from scratch"

# ── dry: everything above has been checked; say what a real run would do, write nothing ─────────────────────────────
if [ "$DRY" -eq 1 ]; then
  note "DRY — checks passed, nothing run, no receipt written"
  note "  code root     : $CODE_ROOT"
  note "  vault         : $DRIVE (readable)"
  note "  lock          : $LOCKDIR (acquired, released on exit)"
  note "  npx cache     : obsidian-brain@$OB_VERSION present; prune build $OB_DIST"
  note "  index db      : $DB ($( [ -f "$DB" ] && stat -f %z "$DB" 2>/dev/null || echo absent ) bytes)"
  note "would run 1: VAULT_PATH=<vault> DATA_DIR=$DATA_DIR OBSIDIAN_BRAIN_NO_WATCH=1 npx --offline obsidian-brain@$OB_VERSION index   (hard cap ${TIMEOUT}s)"
  note "would run 2: OBSIDIAN_BRAIN_DIST=$OB_DIST node $PRUNE_SCRIPT $DB"
  note "would run 3: verify $DB is newer than the run start and non-empty, then write $RCPT"
  exit 0
fi

# ── 1) the reindex, under a hard watchdog ───────────────────────────────────────────────────────────────────────────
START="$(date +%s)"
OUT="$(mktemp "${TMPDIR:-/tmp}/obsidian-reindex.XXXXXX")" || die "preflight" "cannot create a scratch output file" 1
VAULT_PATH="$DRIVE" DATA_DIR="$DATA_DIR" OBSIDIAN_BRAIN_NO_WATCH=1 \
  npx --offline "obsidian-brain@$OB_VERSION" index >"$OUT" 2>&1 & job=$!
(
  sleep "$TIMEOUT"
  if kill -0 "$job"; then
    echo "[$JOB] TIMEOUT ${TIMEOUT}s — killing indexer (pid $job)" >&2
    kill -9 "$job"
    pkill -9 -f "obsidian-brain.* index"   # the ` index` subcommand only — never the MCP `server`
  fi
) >/dev/null 2>&1 & wd=$!
disown "$wd"
wait "$job"; index_rc=$?
kill "$wd" >/dev/null 2>&1
tail -3 "$OUT"
if [ "$index_rc" -ne 0 ]; then
  tail -20 "$OUT" >&2
  die "index" "the indexer exited rc=$index_rc$( [ "$index_rc" -eq 137 ] && echo ' (watchdog kill: overran '"$TIMEOUT"'s)' )" "$index_rc"
fi
note "index done rc=0"

# ── 2) prune archived-copy nodes — only after a clean index (a partial index would give a stale node list) ─────────
OBSIDIAN_BRAIN_DIST="$OB_DIST" node "$PRUNE_SCRIPT" "$DB" >>"$OUT" 2>&1; prune_rc=$?
tail -3 "$OUT"
if [ "$prune_rc" -ne 0 ]; then
  tail -20 "$OUT" >&2
  die "prune" "the archive prune exited rc=$prune_rc" "$prune_rc"
fi
note "archive prune done rc=0"

# ── 3) verify the artifact, then write the receipt (ONLY on success). exit 0 alone is never proof of work. ──────────
[ -f "$DB" ] || die "verify" "$DB does not exist after a clean index" 1
DB_MTIME="$(stat -f %m "$DB")" || die "verify" "cannot stat $DB" 1
DB_BYTES="$(stat -f %z "$DB")" || die "verify" "cannot stat $DB" 1
[ "$DB_BYTES" -gt 0 ] || die "verify" "$DB is empty" 1
[ "$DB_MTIME" -ge "$START" ] || die "verify" "$DB was not modified by this run (mtime $DB_MTIME < start $START): the index did not write" 1
mkdir -p "$RCPT_DIR" || die "receipt" "cannot create $RCPT_DIR" 1
printf '%s ok index_rc=%s prune_rc=%s db_bytes=%s at=%s\n' "$JOB" "$index_rc" "$prune_rc" "$DB_BYTES" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "$RCPT.tmp" || die "receipt" "cannot write $RCPT.tmp" 1
mv "$RCPT.tmp" "$RCPT" || die "receipt" "cannot move the receipt into place: $RCPT" 1
note "ok — db_bytes=$DB_BYTES; receipt $RCPT"
exit 0
