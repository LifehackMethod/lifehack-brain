#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible.
#
#  MEASURED HERE, 2026-08-14, not cited from elsewhere. Four of these guards were
#  fire-tested and then attacked by two independent auditors charged to break them:
#    · the first found 20 bypasses in ~20 minutes; 11 of 13 headline claims reproduced
#    · after a rewrite, the second found 13 more, all reproduced
#    · after three rounds of hardening, 1 of 27 tested attack forms still passes
#  Every one of those holes was in a guard reading a command STRING. This system's
#  own journal states the pattern: 17 of 52 registered hooks guard Bash, and every
#  guard that failed was one of them — every guard that fired correctly was on a
#  typed tool.
#
#  PRIOR ART, same conclusion: CVE-2025-66032 — eight independent bypasses of Claude
#  Code's own regex blocklist (`man --html`, `sort --compress-program`, sed's `e`
#  flag, `$IFS`, `${var@P}`), plus an independently reproduced `$(...)` bypass of an
#  allowlist.
#
#  ⇒ IF YOU ARE ADDING A CONTROL THAT MUST NOT BE BYPASSED, DO NOT ADD IT HERE.
#    Put it on a typed tool, or make the dangerous act structurally impossible.
#    Adding a ninth pattern to this file buys less than it appears to.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: On 2026-07-28 (organism-audit S2.3) a session edited enforce_skill_frontmatter.sh WITHOUT
#      reading system/sops/hook-sop.md first. The operator caught it; the system did not. The post-mortem
#      found TWO controls that both existed and NEITHER could have worked: (1)
#      inject_sop_before_build.sh is UserPromptSubmit and keys on BUILD-INTENT LANGUAGE IN THE
#      USER'S PROMPT — it watches what the human TYPES, not what the agent DOES, so it fired once
#      at session start and was silent when a hook was actually edited hours later; (2)
#      guard_write_paths.sh:121 fires at exactly the right moment on exactly the right file, but
#      knows nothing about the SOP and its redirect hands out the bypass verbatim ("chmod 644 the
#      hook, edit, chmod 555"). The control that knew the rule watched the wrong signal; the
#      control that watched the right signal did not know the rule. Nothing connected them.
#      inject_sop_before_build.sh's own header PRE-AUTHORISED this: "No teeth by design: a pointer,
#      not a gate (escalate to a block only if this proves skippable in practice)."
# FIXED 2026-08-24: this guard was registered on matcher `Bash` ONLY (its neighbours
#      guard_canon_write/guard_write_paths/enforce_skill_frontmatter all use `Bash|Write|Edit`), so a
#      session blocked on a Bash hook-write could switch to the Edit tool and walk straight through —
#      found live: an agent blocked here switched tools, went straight through, and reported it as a
#      clean workaround. Widening the matcher alone would have made this fire-and-pass, because the
#      script parsed ONLY tool_input.command — a Write/Edit payload carries tool_input.file_path and no
#      .command, so the old code found nothing to inspect and silently returned exit 0. Both halves are
#      fixed together below: TOOL_NAME + FILE_PATH are now parsed alongside RAW/command, and a
#      Write/Edit/MultiEdit call whose FILE_PATH lands in the hook plane is treated as write-shaped
#      directly (no verb detection needed — the tool call IS the write), gated by the same receipt.
# GUARDS: (1) a WRITE-SHAPED Bash command targeting system/hooks/ or ~/.claude/hooks/ (chmod with a
#      numeric mode · sed -i · tee · cp/mv/install into · rm · a > / >> redirect into · truncate ·
#      dd of=), and (2) a Write/Edit/MultiEdit tool call whose file_path resolves into system/hooks/ or
#      ~/.claude/hooks/ — in both cases, when NO receipt proves system/sops/hook-sop.md +
#      system/hook-contract.md were read THIS session. READ-SHAPED Bash commands are deliberately
#      untouched — grep/cat/ls/head/tail/wc, `bash <hook>` (running a hook is how the fire-test fleet
#      works and must never be blocked), and `git checkout/restore` of a hook (the emergency repair path
#      back to a known-good state). A Write/Edit under system/hooks/tests/* is likewise untouched — a
#      test is not the enforcement layer it tests (same carve-out as guard_write_paths.sh).
# REDIRECT: run `bash system/tools/read_sop.sh hook` (repo-relative; see PORTED note below) — it
#      PRINTS both docs to stdout and stamps the receipt as a side effect, then retry the exact
#      same command/edit. The receipt cannot be forged into existence without the SOP text passing
#      through context.
# SIGNPOST: the RULE lives in system/sops/hook-sop.md (WHEN + WHICH kind) and system/hook-contract.md
#      (mechanics + the two-machine Deploy & Verify checklist). To change what is gated, edit those
#      + get the operator's sign-off (a HUMAN ruling, `authority: user` — not a session's own
#      judgement), then update this guard and its settings.json registration.
# FAIL_POSTURE: closed — an unparseable payload DENIES (hook-sop.md §3.2).
# KNOWN LIMITS (stated, not hidden — an honest gap beats a false guarantee):
#   1. RECEIPT SCOPE. The receipt is session-keyed, with a cwd-keyed fallback retained ONLY to
#      prevent a BRICK (if read_sop.sh ran without CLAUDE_CODE_SESSION_ID set, the keys would
#      never match and hook repair would be impossible). Consequence: a cwd-keyed receipt
#      unlocks every window in that directory for its 12h TTL. For a single operator running
#      ~7 parallel windows that is a convenience, not a hole — the threat model here is an
#      INATTENTIVE agent, not a hostile one. A brick is the worse failure.
#   2. ATTENTION CANNOT BE FORCED. The receipt proves the SOP text was PRINTED INTO CONTEXT,
#      not that it was attended to. Nothing in a text interface can prove reading. What this
#      guarantees is presence rather than absence — the difference between a rule and a wish.
#   3. BASH-STRING DETECTION IS STILL A SPEED BUMP. The Write/Edit path (2) above is exact — it reads
#      the typed file_path field, not a guessed string — but the Bash path (1) is still the same
#      command-as-TEXT matcher the file's own banner warns about above: one phrasing behind, always.
# UPDATED: 2026-08-24 (widened matcher intent + added Write/Edit file_path parsing — see FIXED note
#      above). Previously 2026-08-03.
# PORTED (T9.7b, 2026-08-15) from claudeops-config: the REDIRECT message and read_sop.sh call
# below carried a hardcoded `~/claudeops-config/...` path; both now resolve from this hook's
# own location (repo-relative), matching the pattern already used by this repo's other ported
# hooks (announce_plan_write.sh etc.) — never a hardcoded home directory.
# ─────────────────────────────────────────────────────────────────────────────
# guard_hook_sop_read.sh — PreToolUse hook (matcher: Bash|Write|Edit)
# Blocks editing the enforcement layer until its rulebook is demonstrably in context.
set -uo pipefail

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"

INPUT=$(cat 2>/dev/null) || INPUT=""

# Single parse pass: tool_name, command (Bash), and file_path (Write/Edit/MultiEdit), plus
# session_id. __ERR__ on the first line means the WHOLE payload failed to parse.
_PARSED=$(printf '%s' "$INPUT" | python3 -c "
import sys, json, os
try:
    d = json.load(sys.stdin)
except Exception:
    print('__ERR__')
    raise SystemExit
ti = (d.get('tool_input') or {})
tool = (d.get('tool_name') or '').strip()
cmd = (ti.get('command', '') or '').replace(chr(10), ' ')
path = ti.get('file_path') or ti.get('path') or ''
resolved = ''
if path:
    base = os.environ.get('_REPO') or os.getcwd()
    p = path if os.path.isabs(path) else os.path.join(base, path)
    try:
        resolved = os.path.realpath(p)
    except Exception:
        resolved = '__PATH_ERR__'
sid = d.get('session_id', '') or ''
print('OK')
print(tool)
print(cmd)
print(resolved)
print(sid)
" 2>/dev/null)

if [ -z "$_PARSED" ] || [ "$(printf '%s' "$_PARSED" | sed -n '1p')" = "__ERR__" ]; then
  printf '%s\n' "BLOCKED: guard_hook_sop_read could not parse its input — failing CLOSED. WHY: this guard protects the enforcement layer (system/hooks/), so an uninspectable payload must not pass. REDIRECT: retry the command/edit; if it persists, inspect the tool call. RULE: system/sops/hook-sop.md + system/hook-contract.md." >&2
  exit 2
fi

TOOL_NAME=$(printf '%s' "$_PARSED" | sed -n '2p')
RAW=$(printf '%s' "$_PARSED" | sed -n '3p')
FILE_PATH=$(printf '%s' "$_PARSED" | sed -n '4p')
SID=$(printf '%s' "$_PARSED" | sed -n '5p')

deny() {
  printf '%s\n' "$1" >&2
  exit 2
}

IS_WRITE=0

case "$TOOL_NAME" in
  Write|Edit|MultiEdit)
    # A path that failed to resolve is treated the same as an unparseable payload — never guessed at.
    if [ "$FILE_PATH" = "__PATH_ERR__" ]; then
      deny 'BLOCKED: guard_hook_sop_read could not resolve this Write/Edit file_path — failing CLOSED. WHY: this guard protects the enforcement layer (system/hooks/), so an uninspectable target must not pass. REDIRECT: retry the edit; if it persists, inspect the tool call. RULE: system/sops/hook-sop.md + system/hook-contract.md.'
    fi
    # Does this edit land in the hook plane at all?
    case "$FILE_PATH" in
      */system/hooks/tests/*)
        # Tests are not the enforcement layer they test — same carve-out as guard_write_paths.sh.
        exit 0 ;;
      */system/hooks/*|*/.claude/hooks/*)
        IS_WRITE=1 ;;
      *)
        exit 0 ;;
    esac
    ;;
  *)
    # ── Bash path (original logic, unchanged) ──────────────────────────────────────────────
    # ── does this command touch the hook plane at all? ───────────────────────────────────────
    printf '%s' "$RAW" | grep -qE '(system/hooks/|\.claude/hooks/)' || exit 0

    # ── READ-SHAPED / SAFE — never block these ───────────────────────────────────────────────
    # `bash <hook>` is how label_checker.py and fire_test_probe.py fire every guard; blocking it would
    # brick the entire fire-test system. `git checkout|restore` is the emergency path back to a
    # committed-good hook and must stay open, or a broken guard becomes unfixable.
    if printf '%s' "$RAW" | grep -qE '(^|[|;&[:space:]])(git[[:space:]]+(checkout|restore|stash|diff|log|show|status|blame))([[:space:]]|$)'; then
      exit 0
    fi

    # ── WRITE-SHAPED detection (TOKENIZED — 2026-08-03) ──────────────────────────────────────
    # The 2026-07-13 build-sop lesson ("a guard that greps a command STRING for a keyword
    # false-positives on mere MENTIONS") was applied here on 2026-07-28 as REGEXES. That fixed the
    # verb half and left the REDIRECT half broken, because a regex cannot tell a QUOTED '>' from a
    # real one. The old REDIR_RE was:
    #     >>?[[:space:]]*[^|;&]*(system/hooks/|\.claude/hooks/)
    # which asks "is there a '>' somewhere AND a hooks path somewhere later" — it never bound the
    # hooks path to the redirect's TARGET. Measured 2026-08-03 (13-case two-sided suite): 5/5 real
    # hook writes blocked correctly, 3 benign commands blocked wrongly, all three from that one gap:
    #   - a heredoc writing notes.md whose BODY merely names a hook
    #   - grep -rn ">> system/hooks/" docs/        (a search PATTERN, not a redirect)
    #   - grep -rn "cat > system/hooks/" docs/     (likewise)
    # FIX: tokenize with shlex instead of pattern-matching. A real redirect survives tokenization as
    # its OWN bare token ('>>'); a quoted one stays glued inside a token that contains SPACES, and a
    # shell redirect operator can never contain a space. That single property is the discriminator.
    # A write VERB now only counts in COMMAND POSITION within its own segment (split on ; && || |),
    # and only when a hooks path appears among THAT segment's arguments — so `mv plan.md new.md &&
    # bash system/hooks/plan_flag.sh set x` no longer blocks. `bash -c "..."` recurses so the
    # tokenizer cannot be used as a bypass. On a tokenizer error we FALL BACK to the old regexes,
    # which are strictly more blocking — fail-closed, per FAIL_POSTURE.
    IS_WRITE=$(printf '%s' "$RAW" | python3 -c "
import sys, re, shlex
HOOK = re.compile(r'(system/hooks/|\.claude/hooks/)')
WRITE_VERBS = {'chmod','chown','cp','mv','rm','install','truncate','dd','tee','ln','touch','patch','ed','shred'}
WRAPPERS = {'sudo','doas','env','command','nohup','time','stdbuf'}
SEPS = {';','&&','||','|','&'}
ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')

def check(cmd, depth=0):
    if depth > 3:
        return True                      # pathological nesting -> fail closed
    toks = shlex.split(cmd, posix=True)  # ValueError propagates -> caller falls back
    segs = [[]]
    for t in toks:
        if t in SEPS: segs.append([])
        else: segs[-1].append(t)
    for s in segs:
        if not s: continue
        # -- redirect: a bare operator token. Quoted text keeps its spaces; an operator cannot.
        for i, t in enumerate(s):
            if ' ' in t: continue
            m = re.match(r'^[0-9]*>>?\|?(.*)$', t)
            if not m or '>' not in t: continue
            tgt = m.group(1) or (s[i+1] if i+1 < len(s) else '')
            if HOOK.search(tgt): return True
        # -- write verb, but only in COMMAND POSITION for this segment
        j = 0
        while j < len(s) and (s[j] in WRAPPERS or ASSIGN.match(s[j])): j += 1
        if j >= len(s): continue
        head = s[j].rsplit('/', 1)[-1]
        args = s[j+1:]
        if head in ('bash','sh','zsh','dash','ksh'):
            for k, a in enumerate(args):
                if a == '-c' and k+1 < len(args):
                    if check(args[k+1], depth+1): return True
            continue                     # 'bash <hook>' = RUNNING a hook; the fire-test fleet needs this
        if head == 'sed':
            if any(a.startswith('-i') or a == '--in-place' for a in args) and any(HOOK.search(a) for a in args):
                return True
            continue
        if head in WRITE_VERBS and any(HOOK.search(a) for a in args):
            return True
    return False

raw = sys.stdin.read()
try:
    print('1' if check(raw) else '0')
except Exception:
    print('__FALLBACK__')
" 2>/dev/null)

    if [ "$IS_WRITE" = "__FALLBACK__" ] || [ -z "$IS_WRITE" ]; then
      # Tokenizer could not parse (unbalanced quotes, etc.) -> the old, more-blocking regexes.
      WRITE_RE='(^|[|;&[:space:]])(chmod[[:space:]]+[0-7]{3,4}[[:space:]]|sed[[:space:]]+-i([[:space:]]|$)|tee([[:space:]]|$)|cp([[:space:]]|$)|mv([[:space:]]|$)|rm([[:space:]]|$)|install([[:space:]]|$)|truncate([[:space:]]|$)|dd[[:space:]]+.*of=)'
      REDIR_RE='>>?[[:space:]]*[^|;&]*(system/hooks/|\.claude/hooks/)'
      IS_WRITE=0
      printf '%s' "$RAW" | grep -qE "$WRITE_RE" && IS_WRITE=1
      printf '%s' "$RAW" | grep -qE "$REDIR_RE" && IS_WRITE=1
    fi
    ;;
esac

[ "$IS_WRITE" -eq 1 ] || exit 0

# ── receipt check ────────────────────────────────────────────────────────────────────────
# shasum is NOT guaranteed on PATH (Git Bash on Windows ships without it). Called bare, it emits
# "command not found" and `cut` returns an EMPTY string, collapsing the key to a constant -- the
# guard then never matches the receipt read_sop.sh wrote, and the result is a PERMANENT DENY.
# ⚠ THIS HELPER IS IDENTICAL IN system/tools/read_sop.sh AND system/hooks/guard_hook_sop_read.sh
# (BOTH repos: private ClaudeOps AND public lifehack-brain -- all four copies) AND MUST STAY THAT
# WAY -- one writes the receipt, the other reads it. If they ever compute the key differently,
# they disagree on every machine lacking shasum. Same rule as hash_key() in
# guard_cross_project_write.sh (sha1 not sha256, deliberately, so a machine with shasum and one
# without still key the same).
# FIXED 2026-08-23: the two repos had DRIFTED -- private fell back to `python3 hashlib.sha1`
# (agrees with `shasum`'s SHA-1), public fell back to `cksum` (a DIFFERENT algorithm entirely).
# With shasum present (this Mac) the fallback never ran, so both agreed by accident; on a PATH
# without shasum (Git Bash on Windows, minimal containers) they computed DIFFERENT keys from the
# IDENTICAL receipt, so one repo's guard allowed and the other denied for the same real state.
# The fix is a shared degrade order that only ever uses ONE algorithm family (SHA-1): shasum ->
# python3 hashlib.sha1 -> openssl sha1. If NONE of those three exist, _hashcwd prints nothing --
# callers below MUST treat that as CANNOT-DETERMINE, never silently build a key from an empty
# string (which would collapse every cwd to the same constant key).
_hashcwd() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$PWD" | shasum | cut -c1-12
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$PWD" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12
  elif command -v openssl >/dev/null 2>&1; then
    printf '%s' "$PWD" | openssl dgst -sha1 -r 2>/dev/null | awk '{print $1}' | cut -c1-12
  fi
}

HASHCWD="$(_hashcwd)"
# CANNOT-DETERMINE, not a silent ALLOW or DENY: with no session id available AND no hashing tool
# on PATH, the cwd-fallback key would collapse to the constant "cwd-" -- indistinguishable from a
# real (but wrong) match. Report the distinct outcome instead of guessing. Exit 3 matches this
# repo's ABSENT-SUBJECT convention (system/hooks/tests/verify-pm-guard.sh, guard_harness_writeback.sh).
if [ -z "$SID" ] && [ -z "${CLAUDE_CODE_SESSION_ID:-}" ] && [ -z "$HASHCWD" ]; then
  printf '%s\n' "CANNOT-DETERMINE: guard_hook_sop_read has no session_id in the payload, no CLAUDE_CODE_SESSION_ID, and no hashing tool (shasum/python3/openssl) on PATH to derive a cwd-based fallback key. WHY: building a key from an empty hash would collapse every working directory to the same constant key -- an unverified guess, not a real match. REDIRECT: install shasum, python3, or openssl on PATH, or retry once CLAUDE_CODE_SESSION_ID is set. RULE: system/hooks/guard_hook_sop_read.sh header." >&2
  exit 3
fi

KEY="${SID:-${CLAUDE_CODE_SESSION_ID:-cwd-$HASHCWD}}"
RUN_DIR="$HOME/.claude/run/sop"
RECEIPT="$RUN_DIR/hook.$KEY.receipt"

# Accept ANY receipt for this session key, or a cwd-keyed one (the tool may have been run before
# the session id was known). TTL 12h so a stale receipt cannot certify a read from yesterday.
# stat -f is BSD/macOS-only; -c is GNU. Try both so the TTL check works on either platform instead
# of silently falling to `echo 0` (which makes AGE ~= now, permanently failing the TTL and dead-ing
# the whole receipt path on any non-BSD stat). Matches guard_brief_truncation.sh's pattern.
FOUND=0
for cand in "$RECEIPT" "$RUN_DIR/hook.cwd-$HASHCWD.receipt"; do
  [ -f "$cand" ] || continue
  MTIME=$(stat -f %m "$cand" 2>/dev/null || stat -c %Y "$cand" 2>/dev/null)
  if [ -z "$MTIME" ]; then
    # Neither BSD nor GNU stat could read the mtime of a receipt that DOES exist -- CANNOT-DETERMINE,
    # never `echo 0` (which would make AGE ~= now, permanently and silently failing the TTL as if
    # the receipt were stale). See FIXED 2026-08-23 note above.
    printf '%s\n' "CANNOT-DETERMINE: guard_hook_sop_read found a receipt at $cand but could not read its modification time with either BSD (stat -f %m) or GNU (stat -c %Y) stat. WHY: treating an unreadable mtime as 0 would silently and permanently fail the TTL check; treating it as ALLOW would be an unverified guess. REDIRECT: this platform's stat is neither BSD- nor GNU-shaped -- report this so the guard can be extended. RULE: system/hooks/guard_hook_sop_read.sh header." >&2
    exit 3
  fi
  AGE=$(( $(date +%s) - MTIME ))
  [ "$AGE" -lt 43200 ] && FOUND=1 && break
done

[ "$FOUND" -eq 1 ] && exit 0

deny "BLOCKED: this Bash command or Write/Edit call WRITES to the hook plane (system/hooks/) but the hook SOP has not been read this session. WHY: on 2026-07-28 a hook was edited with its rulebook unread — the existing reminder (inject_sop_before_build.sh) keys on the USER prompt, so it fires at session start and is silent at the moment the agent actually edits a hook. Hooks are the enforcement layer: a wrong edit here silently disables a control, and a silently-dark guard is worse than no guard because the map still reports it green. REDIRECT: run \`bash $_REPO/system/tools/read_sop.sh hook\` (it PRINTS hook-sop.md + hook-contract.md and stamps a 12h session receipt as a side effect), then retry this exact command/edit. Reading is the only way to earn the receipt. RULE: system/sops/hook-sop.md (WHEN + which kind) + system/hook-contract.md (mechanics + the two-machine Deploy & Verify checklist) — edit those + get the operator's sign-off (a HUMAN ruling, \`authority: user\`) to change what is gated, then update this guard."
