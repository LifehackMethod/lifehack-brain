#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: THERE ARE THREE DOORS INTO A FILE — Write, Edit, and Bash. Three of this repo's guards
#      (`guard_canon_write`, `guard_cross_project_write`, `guard_throughline_write_scope`) stood at
#      two of them. That is not a soft wall; it is a solid wall with a door beside it. And the door
#      is not exotic: an ORDINARY, OBEDIENT session writes through the shell constantly — a heredoc,
#      a `cat >`, a `python3 - <<PY` block. Closing it is not about stopping an evader.
# GUARDS: nothing on its own. This is a SOURCED LIBRARY, not a hook. It answers ONE mechanical
#      question for its callers: *given a Bash command string, which paths is it WRITING TO?*
#      Each calling guard then applies its own scope test to those paths. That split is deliberate —
#      the library owns "is this a write" (mechanical, shared); the guard owns "is this path mine"
#      (domain judgment, different for each one).
# REDIRECT: n/a — nothing is blocked here. Callers emit their own deny text.
# SIGNPOST: the shape this follows is `system/hooks/guard_pm_flag_store.sh`, whose header records the
#      false positives that taught it. The matrix is `system/hooks/tests/test_bash_write_door.sh`.
#      Change the rule there first.
# FAIL_POSTURE: closed — on any parse failure it prints the sentinel `__BWD_PARSE_ERROR__`, and every
#      caller must treat that as "deny", never as "no targets found". An empty result and a broken
#      result must never look the same.
# UPDATED: 2026-09-04 -- Windows path blindness closed. Until this date `looks_like_path`
#      tested only for "/" or a known extension, so a native backslash path was invisible to
#      EVERY caller, and the redirect scanner stopped at the first space, so a quoted target
#      containing one was truncated to an unmatchable fragment. Both are DETECTION-side only;
#      nothing about what is emitted, or about the fail-closed sentinel, changed.
#
# ⚠ WHY ONE SOURCED COPY AND NOT THREE PRIVATE ONES. `build-sop.md`: *"a gate/guard used by more than
#   one runner lives in ONE sourced helper; a private copy is debt, not independence."* That rule was
#   earned when ten runners moved onto a shared machine-gate and one kept its own inline copy — it
#   was silently skipped for weeks and its skip branch exited 0, so nothing alerted. Three guards
#   needing this logic is exactly the Rule of Three; extracting it here is the sanctioned move.
#
# ⚠ STATED LOSS, so nobody over-trusts this — the same honesty `guard_pm_flag_store.sh` prints about
#   itself. This matches TEXT. It does not resolve variables, follow a `cd`, expand a glob, resolve a
#   symlink, or parse a nested shell. `cat > "$TARGET"` is not caught. That is a KNOWN, ACCEPTED miss:
#   the goal is to close the door an obedient session walks through by accident, not to defeat a
#   session that is actively evading — which is a different problem with a different answer (an OS
#   boundary), deliberately deferred.
#   ⛔ Do NOT try to close that miss by matching more nouns. The repo has paid for that twice: a guard
#   that matched a keyword anywhere blocked a fixture teardown and then blocked the very edit that
#   repaired it. Narrow by evidence of a WRITE, never by adding words.
# ─────────────────────────────────────────────────────────────────────────────

# bwd_write_targets "<command string>"
#   Prints, one per line, each path the command appears to WRITE TO. Prints nothing when the command
#   writes nothing we can see. Prints `__BWD_PARSE_ERROR__` if it could not analyse the command.
bwd_write_targets() {
  printf '%s' "${1:-}" | python3 -c '
import sys, shlex, os, re

RAW = sys.stdin.read()

# A newline IS a command separator, never whitespace. Flattening it to a space is how two unrelated
# commands silently become one segment — the bug guard_pm_flag_store.sh records in its own header.
SEPS = ("\n", ";", "&&", "||", "|", "&")

def segments(cmd):
    parts, buf, i = [], [], 0
    while i < len(cmd):
        hit = None
        for s in SEPS:
            if cmd.startswith(s, i):
                hit = s; break
        if hit:
            parts.append("".join(buf)); buf = []; i += len(hit)
        else:
            buf.append(cmd[i]); i += 1
    parts.append("".join(buf))
    return [p for p in parts if p.strip()]

# Verbs whose ARGUMENTS are written/destroyed. mv and cp count BOTH sides: a guard asking "was this
# file modified" must treat `mv brief.md /tmp/` as a modification of brief.md, not only of /tmp.
ARG_WRITERS   = {"rm","rmdir","shred","unlink","truncate","tee","touch","chmod","chown","dd","install"}
BOTH_SIDES    = {"mv","cp","rsync","ln"}
INPLACE       = {"sed","perl"}
INTERPRETERS  = {"python","python3","perl","ruby","node","php","bash","sh","zsh"}
# ⛔ ">" and ">>" do NOT belong in this tuple, and must never come back. This checks for SUBSTRING
# evidence anywhere in the segment — including inside a stderr redirect (`2>&1`, `2>/dev/null`,
# `>&2`), which contains ">" but writes nothing. That false "write" evidence both denied ordinary
# reads AND let a real write slip past unnoticed once the redirect was removed (the guard fired on
# the wrong token, not on the write). A genuine `> file` / `>> file` redirect is ALREADY caught by
# the positional redirect scanner above, which correctly ignores `2>&1` and correctly finds the
# real target in `cmd > file`. Do not re-add these tokens here.
WRITE_CALLS   = ("open(", ".write(", ".writelines(", "write_text", "writeFileSync", ".writeText",
                 "os.replace", "os.rename", "os.remove", "os.unlink", "shutil.copy", "shutil.move")

def looks_like_path(tok):
    if not tok or tok.startswith("-"):
        return False
    # WINDOWS, 2026-09-04. A backslash is a path separator too. Without this clause a native
    # Windows path satisfied NEITHER test and was silently dropped: an interpreter write arrives
    # as ONE token -- open(r"D:\...\notes.md","w").write(x) -- which contains no "/" and ends in
    # ")", not in a known extension. Measured that day by sourcing this library directly: the
    # POSIX spelling of the same write returned the full expression, the Windows spelling
    # returned NOTHING, and every guard downstream then read "no write targets" as "nothing to
    # check" and exited 0. Three guards were affected -- guard_canon_write,
    # guard_cross_project_write and guard_throughline_write_scope.
    # This widens DETECTION only. What is EMITTED stays the raw text the command used, because
    # each caller folds separators itself via lib/winpath_fold.sh; rewriting a path here would
    # hand a caller a string its own scope test never saw.
    return "/" in tok or "\\" in tok or tok.endswith((".md", ".json", ".txt", ".py", ".sh"))

# ── VARIABLE RESOLUTION (FIXCARD-CROSS-PROJECT-WRITE-VAR-PATHS, 2026-09-17) ──────────────────────
# WHY: a guard downstream captures whatever TEXT this library emits and uses it both to CLASSIFY the
# target and as the ack-file HASH KEY. `B="<real path>"; cat >> "$B/plans/x.plan.md"` is an ordinary,
# obedient two-line idiom -- assign once, reuse -- and the OLD behaviour emitted the literal,
# unexpanded `$B/plans/x.plan.md`, so acking the REAL absolute path (the only thing a person actually
# has to paste) could never match the hash of the literal string that was captured. This resolves a
# same-command `NAME=value` assignment (optionally `export`-prefixed) into `known_vars`, then
# substitutes it into any LATER write-target token in the same command -- so what gets emitted, and
# therefore hashed, is the real path.
# ⛔ NARROW ON PURPOSE. Only `known_vars` (assignments seen EARLIER in this same command -- a
# variable used before it is assigned is NOT resolved, same as a real shell) and a three-name
# allowlist of vars a hook always legitimately sees -- HOME, USER, PWD, CLAUDE_PROJECT_DIR, TMPDIR
# (2026-09-17: the last two added after a lead review found the first cut of this fix denying
# ordinary commands like `echo x > "$TMPDIR/foo"` outright -- see the 5 caller scope-narrowing
# checks, lib/bwd_sentinel_scope.sh, for the other half of that fix) -- are ever substituted.
# Never the full os.environ: an unrelated build tool or session env var must never quietly stand in
# for a real value. A command-substitution RHS (`` ` `` or `$(`) is NEVER evaluated -- this
# file does no shell execution of any kind anywhere, only text analysis -- so a variable assigned that
# way is POISONED: treated as unresolvable, exactly like one that was never set at all, even if it
# held a good value from an earlier assignment.
# FAIL_POSTURE: an unresolvable `$NAME`/`${NAME}` reference in a write-target token is NEVER emitted
# as if it were an ordinary path (that IS the bug this closes) and never silently dropped either (a
# caller reading "no targets" as "nothing to check" is the exact regression the 2026-09-04 Windows
# fix above already warns about). It emits a distinct sentinel instead, one line per token:
#   __BWD_UNRESOLVED_VAR__\t$NAME\t<raw token>
# -- parallel to `__BWD_PARSE_ERROR__` below. Every caller MUST treat a line with this prefix as
# DENY, the same posture as a parse error, and may pull $NAME out of the second field for a clearer,
# specific message instead of the generic parse-error text.
VAR_RE = re.compile("\\$\\{([A-Za-z_][A-Za-z0-9_]*)\\}|\\$([A-Za-z_][A-Za-z0-9_]*)")
ASSIGN_RE = re.compile("^(?:export\\s+)?([A-Za-z_][A-Za-z0-9_]*)=(\\x22[^\\x22]*\\x22|\\x27[^\\x27]*\\x27|[^\\s]*)$")
INHERITED_ALLOWLIST = ("HOME", "USER", "PWD", "CLAUDE_PROJECT_DIR", "TMPDIR")

known_vars = {}
poisoned = set()

def resolve_var_refs(text):
    # Substitutes every $NAME / ${NAME} in text from known_vars, then the narrow allowlist.
    # Returns (resolved_text, None) on full success, or (None, first_unresolved_name) otherwise.
    bad = []
    def repl(m):
        name = m.group(1) or m.group(2)
        if not bad:
            if name in poisoned:
                bad.append(name)
            elif name in known_vars:
                return known_vars[name]
            elif name in INHERITED_ALLOWLIST:
                val = os.environ.get(name)
                if val is not None:
                    return val
                bad.append(name)
            else:
                bad.append(name)
        return m.group(0)
    new_text = VAR_RE.sub(repl, text)
    if bad:
        return None, bad[0]
    return new_text, None

out, seen = [], set()

def emit(p):
    p = p.strip().strip("\"\x27")
    if not p or p in ("/dev/null", "/dev/stdout", "/dev/stderr"):
        return
    if p not in seen:
        seen.add(p); out.append(p)

def emit_unresolved(name, raw):
    # The sentinel row for a write-target token this library could not resolve a $VAR inside. Kept
    # in the SAME `out`/`seen` stream as ordinary paths -- one line each, printed in order -- so a
    # caller that reads line-by-line sees it exactly where the unresolved target would have been.
    raw_clean = raw.strip().strip("\"\x27")
    line = "__BWD_UNRESOLVED_VAR__\t$%s\t%s" % (name, raw_clean)
    if line not in seen:
        seen.add(line); out.append(line)

def emit_path_token(t):
    # Every call site that used to call emit(t) directly on a candidate write-target token now comes
    # through here instead: resolve any $VAR the token carries first, and if that fails, emit the
    # sentinel rather than ever letting the raw, unresolved literal pass through emit() as if it were
    # a real path -- which is exactly how the ack-hash mismatch bug happened.
    resolved, bad_name = resolve_var_refs(t)
    if bad_name is not None:
        emit_unresolved(bad_name, t)
    else:
        emit(resolved)

try:
    for seg in segments(RAW):
        seg_stripped = seg.strip()

        # A bare `NAME=value` assignment (optionally `export NAME=value`): record it into
        # known_vars and move on to the NEXT segment. Never run the write-detection scan on an
        # assignment segment, and never emit anything for it -- it writes nothing.
        _m = ASSIGN_RE.match(seg_stripped)
        if _m:
            _vname, _vrhs = _m.group(1), _m.group(2)
            if "$(" in _vrhs or "`" in _vrhs:
                # Command substitution in the RHS is NEVER evaluated -- no shell execution happens
                # anywhere in this file, only text analysis. Poison the name instead of leaving a
                # stale prior value in place, so a later use of it fails closed.
                known_vars.pop(_vname, None)
                poisoned.add(_vname)
                continue
            _vval = _vrhs.strip().strip("\"\x27")
            _resolved_val, _bad_name = resolve_var_refs(_vval)
            if _bad_name is not None:
                known_vars.pop(_vname, None)
                poisoned.add(_vname)
            else:
                known_vars[_vname] = _resolved_val
                poisoned.discard(_vname)
            continue

        # --- redirects: the target is the token immediately AFTER the > or >>, nothing else in the
        # segment. This is the whole reason `cat brief.md > /tmp/x` does not flag brief.md.
        i = 0
        while i < len(seg):
            if seg[i] == ">":
                j = i + 1
                if j < len(seg) and seg[j] == ">":
                    j += 1
                while j < len(seg) and seg[j] in " \t":
                    j += 1
                # QUOTE-AWARE, 2026-09-04. A redirect target may be QUOTED and may contain
                # spaces: cat > "D:\My Notes\projects\x\notes.md". The old scanner stopped at
                # the first space and emitted a truncated fragment, which no scope test
                # downstream could ever match -- so a quoted target with a space in it was
                # effectively invisible. Scan to the matching quote instead; emit() already
                # strips the quote characters off both ends.
                k = j
                if j < len(seg) and seg[j] in "\"\x27":
                    _q = seg[j]
                    k = j + 1
                    while k < len(seg) and seg[k] != _q:
                        k += 1
                    if k < len(seg):
                        k += 1
                else:
                    while k < len(seg) and seg[k] not in " \t;|&":
                        k += 1
                emit_path_token(seg[j:k])
                i = k
            else:
                i += 1

        try:
            toks = shlex.split(seg, comments=False, posix=True)
        except ValueError:
            toks = seg.split()
        if not toks:
            continue

        words = [t for t in toks if not t.startswith("-")]
        head  = os.path.basename(toks[0]) if toks else ""

        if head in ARG_WRITERS or head in BOTH_SIDES:
            for t in words[1:]:
                if looks_like_path(t):
                    emit_path_token(t)

        if head in INPLACE and any(t.startswith("-") and "i" in t for t in toks):
            for t in words[1:]:
                if looks_like_path(t):
                    emit_path_token(t)

        # --- an INTERPRETER only counts as a write when the segment ALSO shows a write call. The bare
        # token used to be enough, and it denied pure READS — including a documented procedure the
        # system itself tells sessions to run. Narrow by evidence of a write.
        if head in INTERPRETERS and any(w in seg for w in WRITE_CALLS):
            for t in words[1:]:
                if looks_like_path(t):
                    emit_path_token(t)

    for p in out:
        print(p)
except Exception:
    print("__BWD_PARSE_ERROR__")
    sys.exit(0)
'
}
