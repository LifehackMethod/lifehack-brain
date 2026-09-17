#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_hook_sop_read.sh" "PreToolUse" "Bash|Write|Edit" 2>/dev/null || true' EXIT
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
#   4. BASH-SHAPED REGISTER RESOLUTION NOW MATCHES WRITE/EDIT (R2-C, 2026-09-16 — Decision 5 of
#      R2-SPEC-A-plugin-guard.md is no longer a limit, it is fixed below). Every hook-plane target
#      the Bash tokenizer already finds (a redirect target, a write-verb argument, a `sed -i`
#      target) is resolved against the payload's own `cwd` field when relative, taken as-is when
#      absolute, realpath'd, and its git toplevel found — the same Decision-2 strict Harness-repo
#      test and Decision-3 no-cross-repo-lift rule as the Write/Edit path, gated on ALL targets in
#      the command agreeing on one suspended repo. `cd` inside the command itself is NOT tracked:
#      a relative target always resolves against the payload's `cwd`, never a `cd` the command
#      performs, so `cd <repo> && echo x >> system/hooks/f` is judged by the session's real cwd.
#      Any target that fails to resolve, targets spanning more than one repo, or the regex-fallback
#      path (no tokenizer result, so no resolved target at all) leave the lookup at the old
#      `_REPO`-based default — never a lift.
# UPDATED: 2026-09-16 (R2-C — Bash-shaped writes into the hook plane now resolve the register from
#      the write target(s)' own repo too, closing the gap Decision 5 left open; see
#      system/hooks/tests/test_hook_sop_read_guard_bash_target.sh). Previously 2026-09-16 (R2 Part A
#      — Write/Edit register lookup now resolves from the write target's own repo, gated by a
#      strict Harness-repo test, so a plugin-cache copy of this guard honors a target repo's
#      declared suspension instead of always defaulting to "active"). Previously 2026-09-16 (a
#      heredoc BODY that merely MENTIONS a hooks path was tokenizing as literal argv to the
#      enclosing write verb -- e.g. `tee <plan path> << 'EOF' ... system/hooks/ ... EOF` blocked a
#      PLAN-file write. Fixed with _trim_heredoc(): args are truncated at the first `<<`/`<<-`
#      token before the HOOK-mention scan runs, so heredoc CONTENT is never read as a command-line
#      argument again. See system/hooks/tests/test_hook_sop_read_guard.sh.). Previously 2026-08-24
#      (widened matcher intent + added Write/Edit file_path parsing — see FIXED note above).
#      Previously 2026-08-03.
# PORTED (T9.7b, 2026-08-15) from claudeops-config: the REDIRECT message and read_sop.sh call
# below carried a hardcoded `~/claudeops-config/...` path; both now resolve from this hook's
# own location (repo-relative), matching the pattern already used by this repo's other ported
# hooks (announce_plan_write.sh etc.) — never a hardcoded home directory.
# ─────────────────────────────────────────────────────────────────────────────
# SWITCH (S1/K1, 2026-09-16): this guard is REGISTER-BACKED. Its row in
# system/register/register.jsonl carries `state` + `expiry`: state="active"
# (DEFAULT — students) means protection ON and this guard is wired normally.
# state="suspended" with an unexpired `expiry` means the guard-rebuild lane
# has a declared, temporary lift; generate.py omits it from fresh wiring.
# The runtime backstop below catches STALE wiring (e.g. an un-refreshed
# plugin cache) and honors/alarms instead of enforcing. A past-expiry
# suspension is treated as ACTIVE again and alarms loudly — the self-heal.
#
# R2 PART A (2026-09-16): a globally-enabled PLUGIN copy of this guard runs
# from a hookdir with no register at all (the plugin cache ships no
# system/register/register.jsonl) — measured live, C1.2. The switch above
# only works when the guard's OWN tree happens to carry the register; a
# plugin copy never does, so its lookup always defaulted to "active" and
# a repo's declared suspension was invisible to it. FIX: for a Write/Edit/
# MultiEdit call the register is resolved from the WRITE TARGET's own repo
# (git toplevel of dirname(FILE_PATH), which is already realpath'd below —
# symlink-safe by construction), never from this hook's own location, never
# from CLAUDE_PROJECT_DIR/cwd (neither is documented as available inside a
# hook process; see R2-SPEC-A-plugin-guard.md Decision 1). That target root
# must pass a strict "is a Harness repo" test (Decision 2: register.jsonl +
# switch_state.py + this guard itself, all present as regular files) before
# its register is trusted at all — a repo with the data file but not the
# mechanism (or vice versa) is not a real install and is treated as having
# no register (state stays "active"). This is what makes the security
# property hold (Decision 3): repo X's declared suspension can only ever
# lift an edit whose REALPATH lands inside X — never inside another repo,
# never inside a plugin cache with no register of its own. No target-repo
# Python is imported or exec'd for this (Decision 4) — the register is read
# as plain JSON lines here, same as the same-repo path below.
# Bash-shaped commands were NOT changed by this fix and kept resolving the
# register from `_REPO` (this hook's own tree) — a single Bash string has no
# one resolved target to derive a toplevel from, so this was documented as a
# known-limit, not an oversight (R2-SPEC-A Decision 5; C1.2 exercises the
# Write/Edit path this fix covers).
# ⚠ SUPERSEDED 2026-09-16 by R2-C, directly below: Decision 5 is no longer a
# limit — a Bash-shaped write now resolves the register from its own
# target(s)' repo too, on the same Decision 1-4 rules, reusing the SAME
# tokenizer that already finds a hook-plane target in a Bash command (below)
# rather than a second parser.
#
# R2-C (2026-09-16): extends the Write/Edit fix above to Bash. The tokenizer
# in the Bash path below (the one that decides IS_WRITE) already walks every
# segment of the command looking for a hook-plane target (a redirect target,
# a write-verb argument, a `sed -i` target) — R2-C has it also COLLECT those
# target strings instead of discarding them once IS_WRITE is known. Each
# collected target is then resolved exactly like FILE_PATH above: relative to
# the payload's own `cwd` field (never a `cd` the command itself performs —
# that is not tracked), realpath'd, and its git toplevel found. A lift is
# granted only when EVERY target in the command agrees on the SAME toplevel
# AND that toplevel passes Decision 2's strict Harness-repo test; one
# unresolved target, disagreeing toplevels, or the regex-fallback path (no
# tokenizer result, so no target at all) all leave the lookup at the old
# `_REPO`/"repo" default — never a lift. See
# system/hooks/tests/test_hook_sop_read_guard_bash_target.sh.
#
# guard_hook_sop_read.sh — PreToolUse hook (matcher: Bash|Write|Edit)
# Blocks editing the enforcement layer until its rulebook is demonstrably in context.
set -uo pipefail

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"
export _REPO
# Default register-lookup root: this is the fallback for BOTH paths. The
# Write/Edit branch always overrides it once a hook-plane target is confirmed
# (Decision 1). The Bash branch (below) ALSO overrides it now (R2-C,
# 2026-09-16) when every hook-plane target the tokenizer found resolves,
# unambiguously, into the SAME repo -- otherwise (an unresolved target,
# disagreeing repos, or the regex-fallback path with no target at all) it
# stays right here: _REPO, checked with the OLD, looser "does register.jsonl
# exist" check, no strict Harness-repo gate. Either override is the only way
# to reach Decision 2's strict three-file test ("target" mode, below).
_REGISTER_ROOT="$_REPO"
_REGISTER_MODE="repo"
export _REGISTER_ROOT _REGISTER_MODE

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
# R2-C: the payload's own cwd, used ONLY to resolve a RELATIVE Bash-target string below --
# an absolute target ignores it entirely, same as FILE_PATH resolution above ignores it once
# a path is already absolute.
cwd = (d.get('cwd') or '').replace(chr(10), ' ')
print('OK')
print(tool)
print(cmd)
print(resolved)
print(sid)
print(cwd)
" 2>/dev/null)

if [ -z "$_PARSED" ] || [ "$(printf '%s' "$_PARSED" | sed -n '1p')" = "__ERR__" ]; then
  printf '%s\n' "BLOCKED: guard_hook_sop_read could not parse its input — failing CLOSED. WHY: this guard protects the enforcement layer (system/hooks/), so an uninspectable payload must not pass. REDIRECT: retry the command/edit; if it persists, inspect the tool call. RULE: system/sops/hook-sop.md + system/hook-contract.md." >&2
  exit 2
fi

TOOL_NAME=$(printf '%s' "$_PARSED" | sed -n '2p')
RAW=$(printf '%s' "$_PARSED" | sed -n '3p')
FILE_PATH=$(printf '%s' "$_PARSED" | sed -n '4p')
SID=$(printf '%s' "$_PARSED" | sed -n '5p')
CWD=$(printf '%s' "$_PARSED" | sed -n '6p')

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
        IS_WRITE=1
        # R2 Part A: resolve the register from the WRITE TARGET's own repo, not
        # this hook's (_REPO stays self-location/sha plumbing only, per Decision 1).
        # FILE_PATH is already realpath'd (see the single parse pass above), so a
        # symlink escaping repo X into repo Y lands _TARGET_ROOT on Y, never X.
        _TARGET_DIR="$(dirname "$FILE_PATH")"
        _TARGET_ROOT="$(cd "$_TARGET_DIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
        _REGISTER_ROOT="$_TARGET_ROOT"
        _REGISTER_MODE="target"
        export _REGISTER_ROOT _REGISTER_MODE
        ;;
      *)
        exit 0 ;;
    esac
    ;;
  *)
    # ── Bash path (write-shape detection unchanged; register resolution extended by R2-C) ──
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
    # R2-C (2026-09-16): the SAME tokenizer/check() below now also collects the literal
    # hook-plane TARGET string(s) it matched on (a redirect target, a write-verb argument, a
    # `sed -i` target) into TARGETS, printed after the '1'/'0' verdict line -- one extra channel
    # of output from the same parse pass, never a second parser. The regex-fallback path
    # (tokenizer ValueError) still has no resolved target at all, by construction.
    _BASH_DETECT=$(printf '%s' "$RAW" | python3 -c "
import sys, re, shlex
HOOK = re.compile(r'(system/hooks/|\.claude/hooks/)')
WRITE_VERBS = {'chmod','chown','cp','mv','rm','install','truncate','dd','tee','ln','touch','patch','ed','shred'}
WRAPPERS = {'sudo','doas','env','command','nohup','time','stdbuf'}
SEPS = {';','&&','||','|','&'}
ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
TARGETS = []

    # ⛔ NO BACKTICKS IN THIS BLOCK: it is a bash DOUBLE-quoted string, so a backtick is live command
    # substitution. A backticked tee example here truncated the migration plan to 28 bytes, 2026-09-16.
def _trim_heredoc(args):
    # shlex has no concept of a bash heredoc (<<DELIM ... DELIM) -- it is a multi-line shell
    # construct, not a quoting rule, so shlex.split happily explodes the heredoc BODY into a run
    # of ordinary-looking tokens glued onto the END of the preceding command's argv. Measured
    # 2026-09-15: tee ~/.claude/plans/lifehack-migration.plan.md << 'EOF' ... this plan touches
    # system/hooks/ ... EOF tokenizes to ['tee', '<plan path>', '<<', 'EOF', ..., 'system/hooks/',
    # ..., 'EOF'] -- the mere MENTION of a hooks path inside the file's own CONTENT (the heredoc
    # body) then reads as an "argument" to tee and trips the HOOK.search(args) check below, even
    # though the actual write target (the plan file, captured correctly by the REDIRECT check
    # elsewhere in this function) is nowhere near system/hooks/. A real write-verb TARGET argument
    # (e.g. cp foo.sh system/hooks/bar.sh) always appears BEFORE any << operator in the same
    # segment, never after -- so truncating args at the first heredoc operator removes exactly the
    # DATA (file content) that was never a command-line argument in the first place, while a
    # genuine target argument earlier in the same args list is untouched.
    for idx, a in enumerate(args):
        if a == '<<' or a == '<<-' or a.startswith('<<'):
            return args[:idx]
    return args

def check(cmd, depth=0):
    if depth > 3:
        TARGETS.append('__UNRESOLVED__')  # R2-C: pathological nesting has no single target -> fail-safe
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
            if HOOK.search(tgt):
                TARGETS.append(tgt)  # R2-C
                return True
        # -- write verb, but only in COMMAND POSITION for this segment
        j = 0
        while j < len(s) and (s[j] in WRAPPERS or ASSIGN.match(s[j])): j += 1
        if j >= len(s): continue
        head = s[j].rsplit('/', 1)[-1]
        args = _trim_heredoc(s[j+1:])
        if head in ('bash','sh','zsh','dash','ksh'):
            for k, a in enumerate(args):
                if a == '-c' and k+1 < len(args):
                    if check(args[k+1], depth+1): return True
            continue                     # 'bash <hook>' = RUNNING a hook; the fire-test fleet needs this
        if head == 'sed':
            if any(a.startswith('-i') or a == '--in-place' for a in args):
                matched = [a for a in args if HOOK.search(a)]
                if matched:
                    TARGETS.extend(matched)  # R2-C
                    return True
            continue
        if head in WRITE_VERBS:
            matched = [a for a in args if HOOK.search(a)]
            if matched:
                TARGETS.extend(matched)  # R2-C
                return True
    return False

raw = sys.stdin.read()
try:
    verdict = '1' if check(raw) else '0'
except Exception:
    verdict = '__FALLBACK__'
    TARGETS[:] = []  # R2-C: no tokenizer result means no resolved target either
print(verdict)
for t in TARGETS:
    print(t)
" 2>/dev/null)

    IS_WRITE=$(printf '%s' "$_BASH_DETECT" | sed -n '1p')
    _BASH_TARGETS=$(printf '%s' "$_BASH_DETECT" | tail -n +2)

    if [ "$IS_WRITE" = "__FALLBACK__" ] || [ -z "$IS_WRITE" ]; then
      # Tokenizer could not parse (unbalanced quotes, etc.) -> the old, more-blocking regexes.
      # No resolved target exists on this path, so the R2-C block below never runs for it --
      # fail-safe: the register lookup stays at the _REPO/"repo" default set at the top of this file.
      WRITE_RE='(^|[|;&[:space:]])(chmod[[:space:]]+[0-7]{3,4}[[:space:]]|sed[[:space:]]+-i([[:space:]]|$)|tee([[:space:]]|$)|cp([[:space:]]|$)|mv([[:space:]]|$)|rm([[:space:]]|$)|install([[:space:]]|$)|truncate([[:space:]]|$)|dd[[:space:]]+.*of=)'
      REDIR_RE='>>?[[:space:]]*[^|;&]*(system/hooks/|\.claude/hooks/)'
      IS_WRITE=0
      printf '%s' "$RAW" | grep -qE "$WRITE_RE" && IS_WRITE=1
      printf '%s' "$RAW" | grep -qE "$REDIR_RE" && IS_WRITE=1
      _BASH_TARGETS=""
    fi

    # ── R2-C (2026-09-16): resolve the register from the Bash write target(s)' own repo ──────
    # Same rules as the Write/Edit path (Decision 1-4 of R2-SPEC-A, extended to Bash). Every
    # candidate target line in _BASH_TARGETS is resolved against CWD (the payload's own `cwd`
    # field) when relative, taken as-is when absolute, realpath'd, and its git toplevel found.
    # A lift is only even considered when EVERY target resolves and every one agrees on the SAME
    # toplevel -- one unresolved target, a resolution error, or targets spanning more than one
    # repo all leave _REGISTER_ROOT/_REGISTER_MODE at the _REPO/"repo" default (never a lift).
    # `cd` inside the command is NOT tracked: a relative target resolves against the session's
    # real cwd, never a `cd` the command itself performs.
    if [ "$IS_WRITE" = "1" ] && [ -n "$_BASH_TARGETS" ]; then
      _BASH_TOPLEVEL=""
      _BASH_RESOLVE_OK=1
      while IFS= read -r _tgt; do
        [ -n "$_tgt" ] || continue
        if [ "$_tgt" = "__UNRESOLVED__" ]; then
          _BASH_RESOLVE_OK=0
          break
        fi
        _RESOLVED=$(_TGT="$_tgt" _CWD="$CWD" python3 -c "
import os
tgt = os.environ.get('_TGT', '')
cwd = os.environ.get('_CWD', '')
base = cwd if cwd else os.getcwd()
p = tgt if os.path.isabs(tgt) else os.path.join(base, tgt)
try:
    print(os.path.realpath(p))
except Exception:
    print('__PATH_ERR__')
" 2>/dev/null)
        if [ -z "$_RESOLVED" ] || [ "$_RESOLVED" = "__PATH_ERR__" ]; then
          _BASH_RESOLVE_OK=0
          break
        fi
        _TOP=$(cd "$(dirname "$_RESOLVED")" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)
        if [ -z "$_TOP" ]; then
          _BASH_RESOLVE_OK=0
          break
        fi
        if [ -z "$_BASH_TOPLEVEL" ]; then
          _BASH_TOPLEVEL="$_TOP"
        elif [ "$_TOP" != "$_BASH_TOPLEVEL" ]; then
          _BASH_RESOLVE_OK=0
          break
        fi
      done <<< "$_BASH_TARGETS"
      if [ "$_BASH_RESOLVE_OK" = "1" ] && [ -n "$_BASH_TOPLEVEL" ]; then
        _REGISTER_ROOT="$_BASH_TOPLEVEL"
        _REGISTER_MODE="target"
        export _REGISTER_ROOT _REGISTER_MODE
      fi
    fi
    ;;
esac

[ "$IS_WRITE" -eq 1 ] || exit 0

# ── S1/K1 register-backed switch (2026-09-16) ────────────────────────────────────────────
# This guard is SWITCHABLE by register data, not by editing this file: its row in
# system/register/register.jsonl carries state+expiry. state=suspended with an
# UNEXPIRED expiry means the guard-rebuild lane has a declared, temporary lift and
# this guard was also OMITTED from freshly generated wiring. If we fire here, the
# wiring is STALE (e.g. an un-refreshed plugin cache), so honor the declaration:
# NOTICE, then allow. An EXPIRED suspension means the lift lapsed: ALARM LOUDLY,
# then enforce normally (the self-heal: protection is ON again). Missing or
# unparseable register defaults to enforce (protection ON is the fail-safe).
_SWITCH=$(python3 - <<'PY' 2>/dev/null
import os, json
from datetime import date
guard_path = "/system/hooks/guard_hook_sop_read.sh"
# _REGISTER_ROOT is the write target's own repo for a Write/Edit/MultiEdit
# call (Decision 1), OR for a Bash-shaped command whose every hook-plane
# target agrees on one repo (R2-C, 2026-09-16, extending Decision 1 to Bash);
# otherwise it is _REPO (this hook's own tree) unchanged -- set by the bash
# side above.
# _REGISTER_MODE says which: "target" gates the lookup on Decision 2's strict
# Harness-repo test (all three files present) -- reached by EITHER an
# unambiguous Write/Edit target or an unambiguous, fully-agreeing Bash target
# set; "repo" is the ORIGINAL behavior -- just "does register.jsonl exist" --
# for whichever path (Bash falls back here on any unresolved/disagreeing
# target or the regex-fallback path) has no independently resolved target
# repo to hold to a stricter standard.
target_root = os.environ.get("_REGISTER_ROOT", "") or ""
register_mode = os.environ.get("_REGISTER_MODE", "repo")

def is_harness_repo(root):
    # Decision 2: strict, ALL three, as regular files. A data file (register.jsonl)
    # with no mechanism (switch_state.py / this guard) alongside it, or the reverse,
    # is not a real install — the register is ignored (state stays "active").
    if not root:
        return False
    for rel in (
        "system/register/register.jsonl",
        "system/register/switch_state.py",
        "system/hooks/guard_hook_sop_read.sh",
    ):
        if not os.path.isfile(os.path.join(root, rel)):
            return False
    return True

state = "active"
expiry = None
register_ok = is_harness_repo(target_root) if register_mode == "target" else (
    bool(target_root) and os.path.isfile(os.path.join(target_root, "system/register/register.jsonl"))
)
if register_ok:
    register_path = os.path.join(target_root, "system/register/register.jsonl")
    try:
        with open(register_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("type") == "hook" and row.get("path") == guard_path:
                    state = row.get("state", "active")
                    expiry = row.get("expiry")
                    break
    except Exception:
        pass
if state != "suspended" or not expiry:
    print("ACTIVE")
else:
    try:
        today = date.fromisoformat(os.environ.get("LHB_REGISTER_TODAY", date.today().isoformat()))
        expiry_date = date.fromisoformat(expiry)
        print("HONORED" if expiry_date >= today else "EXPIRED")
    except Exception:
        print("ACTIVE")
PY
)
case "$_SWITCH" in
  HONORED)
    printf '%s\n' "NOTICE: guard_hook_sop_read is REGISTER-SUSPENDED until its expiry in system/register/register.jsonl — this guard should not be wired at all; it fires only because the plugin cache or wiring is stale. The lane's declared lift is honored (protection OFF)." >&2
    exit 0
    ;;
  EXPIRED)
    printf '%s\n' "⛔ ALARM: guard_hook_sop_read has a register-declared suspension whose EXPIRY HAS PASSED — protection is RE-ARMED. Update system/register/register.jsonl (state=active or a fresh expiry) to clear this alarm." >&2
    ;;
esac

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
  MTIME=$(stat -c %Y "$cand" 2>/dev/null || stat -f %m "$cand" 2>/dev/null)
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

deny "BLOCKED: this Bash command or Write/Edit call WRITES to the hook plane (system/hooks/) but the hook SOP has not been read this session. WHY: on 2026-07-28 a hook was edited with its rulebook unread — the existing reminder (inject_sop_before_build.sh) keys on the USER prompt, so it fires at session start and is silent at the moment the agent actually edits a hook. Hooks are the enforcement layer: a wrong edit here silently disables a control, and a silently-dark guard is worse than no guard because the map still reports it green. REDIRECT: run `bash $_REPO/system/tools/read_sop.sh hook` (it PRINTS hook-sop.md + hook-contract.md and stamps a 12h session receipt as a side effect), then retry this exact command/edit. Reading is the only way to earn the receipt. RULE: system/sops/hook-sop.md (WHEN + which kind) + system/hook-contract.md (mechanics + the two-machine Deploy & Verify checklist) — edit those + get the operator's sign-off (a HUMAN ruling, `authority: user`) to change what is gated, then update this guard."
