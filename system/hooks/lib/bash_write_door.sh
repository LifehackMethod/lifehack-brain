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
# UPDATED: 2026-08-13
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
import sys, shlex, os

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
WRITE_CALLS   = ("open(", ".write(", ".writelines(", "write_text", "writeFileSync", ".writeText",
                 "os.replace", "os.rename", "os.remove", "os.unlink", "shutil.copy", "shutil.move",
                 ">", ">>")

def looks_like_path(tok):
    if not tok or tok.startswith("-"):
        return False
    return "/" in tok or tok.endswith((".md", ".json", ".txt", ".py", ".sh"))

out, seen = [], set()

def emit(p):
    p = p.strip().strip("\"\x27")
    if not p or p in ("/dev/null", "/dev/stdout", "/dev/stderr"):
        return
    if p not in seen:
        seen.add(p); out.append(p)

try:
    for seg in segments(RAW):
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
                k = j
                while k < len(seg) and seg[k] not in " \t;|&":
                    k += 1
                emit(seg[j:k])
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
                    emit(t)

        if head in INPLACE and any(t.startswith("-") and "i" in t for t in toks):
            for t in words[1:]:
                if looks_like_path(t):
                    emit(t)

        # --- an INTERPRETER only counts as a write when the segment ALSO shows a write call. The bare
        # token used to be enough, and it denied pure READS — including a documented procedure the
        # system itself tells sessions to run. Narrow by evidence of a write.
        if head in INTERPRETERS and any(w in seg for w in WRITE_CALLS):
            for t in words[1:]:
                if looks_like_path(t):
                    emit(t)

    for p in out:
        print(p)
except Exception:
    print("__BWD_PARSE_ERROR__")
    sys.exit(0)
'
}
