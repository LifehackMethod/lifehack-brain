#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Five session-scoped switches (`skill_anchor.sh` · `scratch_flag.sh` · `altitude_flag.sh` ·
#      `numbers_flag.sh` · `throughline_flag.sh`) each hand-copied the same ~40 lines: the
#      `hash_key` fallback, the sess-/cwd- key derivation, the flag-path/NOW preamble, the
#      TTL-expiry check, and the "remove mine, then sweep this session's others" clear loop. Seven
#      identical copies (these five plus `pm_flag.sh`/`plan_flag.sh`, not yet wired here — B5.4)
#      is exactly the duplication `build-sop.md`'s Rule of Three exists to end.
# GUARDS: nothing on its own. This is a SOURCED LIBRARY, not a hook — it never blocks and never
#      decides what SHOULD be armed. Each shim owns its own verbs, its own payload fields, and any
#      arg validation (e.g. skill_anchor's "the anchor file must exist"); this file owns only the
#      mechanical parts that were byte-identical across all five already.
# REDIRECT: n/a — nothing is blocked here. A shim that cannot load this file must fail loudly on
#      its own stderr and exit non-zero (see FAIL_POSTURE) rather than silently no-op.
# SIGNPOST: the profile each shim passes (flag-dir name, file-prefix, TTL var/value) is inline in
#      that shim, matching the shape `pm_flag.sh`/`plan_flag.sh` will later adopt in B5.4. Change a
#      SHARED mechanic (key derivation, TTL math, sweep loop) here; change what one flag STORES or
#      how it validates its own args in that flag's own shim.
# FAIL_POSTURE: n/a for this file itself (a library has no posture of its own) — but every caller
#      MUST treat "this file is missing, unreadable, or fails to source" as fatal: exit non-zero
#      with a clear stderr line naming the failure. A silent exit 0 here would look identical to
#      "nothing is armed" to every downstream reader, including the two locks this pattern will
#      later cover (D6 condition ③ — a silent no-op could un-arm every lock at once).
# UPDATED: 2026-09-15 (new — B5.1. Extracted verbatim from skill_anchor.sh, scratch_flag.sh,
#      altitude_flag.sh, numbers_flag.sh, throughline_flag.sh as they stood at e15408c; no behavior
#      change intended — see scratchpad/B5.1-report.md for the byte-identity verification.
#      pm_flag.sh / plan_flag.sh are NOT sourcing this yet; that is B5.4, gated on a pilot PASS.)
# ─────────────────────────────────────────────────────────────────────────────
# Public functions (all assume the caller has already set nothing except what's documented):
#   flag_hash_key <string>             -> prints a 12-char hex digest on stdout
#   flag_init <flagdir-name> <prefix>  -> sets FLAGDIR, KEY, FLAG, NOW; mkdir -p's FLAGDIR
#   flag_write field=value [...]       -> (re)writes $FLAG, one line per arg, in order given
#   flag_get <field>                   -> prints that field's value from $FLAG (empty if absent)
#   flag_ttl_expired <ttl_seconds>     -> 0 (true) + REMOVES $FLAG if armed_at is stale; 1 (false)
#   flag_clear_sweep <prefix>          -> removes $FLAG, then (session mode only) every OTHER
#                                          "<prefix>-*.flag" under FLAGDIR whose session= line
#                                          matches this session; prints the count removed
# ─────────────────────────────────────────────────────────────────────────────

# ── hash_key: the fallback session key, and it MUST match every caller of this library, plus
# pm_flag.sh/plan_flag.sh (not yet on this lib) and every reader hook that still carries its own
# copy (skill_anchor_inject.sh, inject_work_altitude.sh, inject_compute_mechanically.sh,
# guard_throughline_write_scope.sh, pm_persist.sh, statusline.sh — untouched by B5.1, out of scope).
# When the harness gives us no session id we key on the working directory instead. `shasum` does
# that on macOS and Linux and is ABSENT from Git Bash on Windows, where it produces an EMPTY key —
# so every window on that machine would collide on one flag, silently.
# ⚠ SHA-1 DELIBERATELY, NOT SHA-256: this must equal what `shasum` prints, or a machine that has
# shasum and a machine that does not would key the SAME folder differently. One writer and one
# reader disagreeing about the key is worse than having no key at all.
# TEMPORARY: Git Bash is the documented Windows floor; a real Windows story is still owed.
flag_hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-12)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12)"
  fi
  printf '%s' "$_hk"
}

# flag_init <flagdir-name> <file-prefix>
# Sets globals FLAGDIR / KEY / FLAG / NOW exactly as each of the five scripts' preamble did.
flag_init() {
  FLAGDIR="$HOME/.claude/run/$1"
  mkdir -p "$FLAGDIR" 2>/dev/null
  if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
    KEY="sess-$CLAUDE_CODE_SESSION_ID"
  else
    KEY="cwd-$(flag_hash_key "$PWD")"
  fi
  FLAG="$FLAGDIR/$2-$KEY.flag"
  NOW="$(date +%s 2>/dev/null)"
}

# flag_write field=value [field=value ...] — (re)creates $FLAG with one line per argument, in the
# order given. Callers pass the WHOLE "key=value" string per arg (including an empty value, e.g.
# "session=") so this stays a dumb line-writer with no opinion about field names.
flag_write() {
  : > "$FLAG"
  for kv in "$@"; do
    printf '%s\n' "$kv" >> "$FLAG"
  done
}

# flag_get <field> — the `getf`/inline-grep pattern every script repeated.
flag_get() {
  grep "^$1=" "$FLAG" 2>/dev/null | cut -d= -f2-
}

# flag_ttl_expired <ttl_seconds> — true (0) AND removes $FLAG when armed_at is older than
# ttl_seconds; false (1) otherwise, including "no armed_at field at all" (never armed / already
# gone) — matches every TTL check across the five scripts, condition-for-condition.
flag_ttl_expired() {
  AT="$(flag_get armed_at)"
  if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge "$1" ]; then
    rm -f "$FLAG" 2>/dev/null
    return 0
  fi
  return 1
}

# flag_clear_sweep <file-prefix> — the "remove mine, then sweep this session's others" loop shared
# by skill_anchor/scratch/numbers/throughline's `clear` verb (altitude's `clear` is deliberately
# NOT built on this — it only ever removed its own file, never swept; that divergence is preserved
# in altitude_flag.sh itself, not folded in here). Echoes the removed-count on stdout.
flag_clear_sweep() {
  n=0
  [ -f "$FLAG" ] && { rm -f "$FLAG" 2>/dev/null; n=$((n+1)); }
  if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
    for f in "$FLAGDIR"/"$1"-*.flag; do
      [ -f "$f" ] || continue
      s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
      [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && { rm -f "$f" 2>/dev/null; n=$((n+1)); }
    done
  fi
  printf '%s' "$n"
}
