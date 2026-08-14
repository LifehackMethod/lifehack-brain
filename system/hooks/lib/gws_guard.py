#!/usr/bin/env python3
"""
gws_guard.py — the ONE shell-segment parser the gws guards share.

WHY THIS EXISTS AS A SHARED FILE. Four guards need to answer the same question —
"is this command really invoking the gws binary, and against what?" — and three of
them got it wrong in three different ways. Measured by fire test, 2026-08-14: 7 of
43 adversarial cases disagreed with intent. build-sop.md: "a gate/guard used by more
than one runner lives in ONE sourced helper; a private copy is debt, not independence."

THE TWO DEFECTS THIS FIXES, both measured, not theorised:

  1. INLINE ASSIGNMENT PREFIX.  guard_gmail_destructive.sh took seg.split()[0] and
     tested it against ^gws$. For `ID=18abc gws gmail users threads trash ...` the
     first word is `ID=18abc`, so the segment was SKIPPED ENTIRELY and the command
     ALLOWED (rc 0). An assignment prefix is ordinary, runnable POSIX shell.
     ⭐ This is the parser the plan told us to COPY into three more guards. Copying
     it unfixed would have propagated the hole.

  2. NON-LITERAL VERB / TARGET.  The sheets + tasks guards matched destructive verbs
     and protected ids as LITERAL text, then fell through to `exit 0` when the text
     was not literal. `gws sheets spreadsheets values $VERB --params ...` matched
     nothing and was allowed unconditionally.

⛔ THE RULE THIS ENCODES: an indirection we cannot resolve is UNKNOWN, and UNKNOWN
FAILS CLOSED. An unknown must never be read as permission. That is the same trade
already made deliberately for guard_gws_logout on an irreversible action.

⚠ STILL A SPEED BUMP, NOT A BOUNDARY. A shell has infinite equivalent phrasings;
this handles the ones we measured. Treat it accordingly.

Usage from a guard:
    python3 "$LIB/gws_guard.py" --service sheets --destructive clear,delete,batchclear \
                                --safe get,list,create,append,batchget,metadata
    (command on stdin; exit 7 = BLOCK, exit 0 = pass)
"""
import argparse
import re
import sys

# TRUE STATEMENT separators only. ⚠ The first draft also split on `$(` and `(` —
# which DESTROYED the evidence it needed: for
#   gws sheets spreadsheets values $(echo clear) --params ...
# the split consumed the `$(`, leaving a segment with no `$` in it, so the
# indirection test saw a clean literal command and PASSED it. Caught by the
# self-test below before this was wired to anything.
_STMT = re.compile(r'(?:\n|;|\|\||\||&&|&)')
_ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
_BINARY = re.compile(r'^(?:[\w./~-]*/)?gws$')
# WRAPPER WORDS -- found by an adversarial audit 2026-08-14 and reproduced before
# fixing. The parser required the token after any assignments to be LITERALLY the
# binary name. Every one of these ordinary prefixes made it return ZERO segments,
# and a verdict over zero segments defaults to PASS.
_WRAPPER = {'command', 'exec', 'env', 'builtin', 'nohup', 'time', 'nice', 'sudo', 'xargs'}
# A token whose value we cannot know by reading.
_NONLITERAL = re.compile(r'[$`]')
# The binary nested inside a command substitution IS executed, so it is its own call.
# A shell asked to run a string: the string is a command.
_EXECWRAP = re.compile(r'\b(?:ba|z|da)?sh\s+-c\s+(?P<body>"[^"]*"|\'[^\']*\')'
                      r'|\beval\s+(?P<body2>"[^"]*"|\'[^\']*\'|[^;&|\n]+)')
_NESTED = re.compile(r'[$`]\(?\s*((?:[\w./~-]*/)?gws\b[^)`]*)')


def _debinary(tok):
    """Strip the disguises a shell ignores: quotes and a leading backslash.
    A backslashed, single-quoted and double-quoted binary name all execute the same
    thing; the old regex saw three different strings and matched none of them."""
    return tok.replace("'", '').replace('"', '').replace('\\', '')


def gws_segments(cmd):
    """Every shell statement that actually INVOKES the gws binary, as a token list.

    Substitutions are RETAINED in the tokens so has_nonliteral() can still see them.
    """
    # A backslash-newline is REMOVED BY THE SHELL before the command runs, so the
    # wrapped form and the joined form execute identically -- but every guard saw a
    # different string and all four missed it (second audit, 2026-08-14). Join first.
    cmd = cmd.replace('\\\n', ' ')
    out = []
    # `bash -c "..."`, `sh -c "..."` and `eval "..."` EXECUTE their argument. Parse it.
    # A heredoc that merely WRITES the same words does not execute them and is left
    # alone -- that distinction is the whole point, and re-breaking it was the
    # previous attempt's mistake (hook-sop Trap 2, the 2026-07-28 incident).
    for m in _EXECWRAP.finditer(cmd):
        inner = m.group('body') or m.group('body2')
        if inner:
            out.extend(gws_segments(inner.strip('\'"')))
    for stmt in _STMT.split(cmd):
        s = stmt.strip()
        if not s:
            continue
        # A subshell or brace group is still a command being run.
        s = s.lstrip('({ ').rstrip(') };')
        toks = s.split()
        # ⭐ FIX 1: strip leading NAME=value assignment prefixes before taking the
        # first word. `ID=x gws ...` runs gws; the old parser could not see it.
        # Strip BOTH assignment prefixes and wrapper words, repeatedly and in any
        # order -- `env FOO=bar command <bin> ...` is all of them at once.
        while toks and (_ASSIGN.match(toks[0]) or _debinary(toks[0]) in _WRAPPER):
            toks.pop(0)
        if toks and _BINARY.match(_debinary(toks[0])):
            out.append(toks)
        # ⭐ FIX 2: a gws inside $( ) or backticks is still a real invocation.
        for m in _NESTED.finditer(s):
            out.append(m.group(1).split())
    return out


def has_nonliteral(toks):
    """Does any token hide its value behind a variable or a substitution?"""
    return any(_NONLITERAL.search(t) for t in toks)


def op_chain(toks, service):
    """The operation words: everything after the service word up to the first flag.

    A spreadsheets values-clear call yields [spreadsheets, values, clear]. Nothing
    outside this window is consulted to PERMIT anything, which is what kills the
    decoy-word bypass.
    """
    idx = None
    for i, t in enumerate(toks):
        if t.strip('\'"').lower() == service.lower():
            idx = i
            break
    if idx is None:
        return []
    # ⚠ This used to STOP at the first flag, which let a flag placed between the
    # resource path and the operation push the operation out of the window entirely.
    # Skip flags and their values instead; keep scanning for the operation words.
    chain = []
    skip_next = False
    for t in toks[idx + 1:]:
        if skip_next:
            skip_next = False
            continue
        if t.startswith('-'):
            skip_next = '=' not in t      # `--flag value` consumes the next token
            continue
        chain.append(t)
    return chain


def verdict(cmd, service, destructive, safe, require_any=None, write_verbs=None):
    """BLOCK | PASS for one command.

    REWRITTEN 2026-08-14 after an adversarial audit. The previous rule was "block if
    indirected AND no safe word appears ANYWHERE in the segment", so any decoy token
    satisfied it. The rule now reads the OPERATION POSITION and nothing else:
      1. an operation word we cannot resolve          -> UNKNOWN -> BLOCK
      2. a destructive operation, in scope             -> BLOCK
      3. a write operation whose TARGET is indirected -> UNKNOWN target -> BLOCK
    `safe` is retained for signature compatibility and is deliberately unused: a word
    being present is no longer evidence of anything.
    """
    write_verbs = write_verbs or []
    for toks in gws_segments(cmd):
        seg = ' '.join(toks)
        if not re.search(r'\b%s\b' % re.escape(service), seg, re.I):
            continue
        chain = op_chain(toks, service)
        if not chain:
            if has_nonliteral(toks):
                return 'BLOCK'
            continue
        if has_nonliteral(chain):
            return 'BLOCK'                      # 1. unknown operation
        low = [c.lower() for c in chain]
        in_scope = (not require_any) or any(w.lower() in low for w in require_any)
        if in_scope and any(v.lower() in low for v in destructive):
            return 'BLOCK'                      # 2. destructive, in scope
        if any(v.lower() in low for v in write_verbs):
            if has_nonliteral(toks[len(chain) + 1:]):
                return 'BLOCK'                  # 3. write, unresolvable target
    return 'PASS'


def _selftest():
    ID = 'TESTFAKESHEETID0000000000000000000000000000'
    D = ['clear', 'batchclear', 'delete']
    S = ['get', 'batchget', 'metadata', 'create', 'append', 'list']
    cases = [
        # (command, service, expected)
        ("gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"%s\"}'" % ID, 'sheets', 'BLOCK'),
        ("VERB=clear; gws sheets spreadsheets values $VERB --params '{\"a\":1}'", 'sheets', 'BLOCK'),
        ("gws sheets spreadsheets values $(echo clear) --params '{\"a\":1}'", 'sheets', 'BLOCK'),
        ("SHEET=s1 gws sheets spreadsheets values clear --params '{\"a\":1}'", 'sheets', 'BLOCK'),
        ("echo go; gws sheets spreadsheets values clear --params '{\"a\":1}'", 'sheets', 'BLOCK'),
        ("gws sheets spreadsheets values get --params \"{\\\"id\\\":\\\"$ID\\\"}\"", 'sheets', 'PASS'),
        ("gws sheets spreadsheets values append --params '{\"a\":1}'", 'sheets', 'PASS'),
        ("gws sheets spreadsheets create --params '{\"a\":1}'", 'sheets', 'PASS'),
        ("git commit -m 'gws sheets values clear is destructive'", 'sheets', 'PASS'),
        ("ID=18abc gws gmail users threads trash --id \"$ID\"", 'gmail', 'BLOCK'),
        ("gws gmail users threads trash --id 18abc", 'gmail', 'BLOCK'),
        ("/opt/homebrew/bin/gws gmail users threads trash --id 18abc", 'gmail', 'BLOCK'),
        ("gws gmail users threads untrash --id 18abc", 'gmail', 'PASS'),
        ("gws gmail users threads modify --id 18abc --add-label-ids L1", 'gmail', 'PASS'),
        ("python3 - <<'EOF'\nopen('/tmp/p','w').write('gws gmail users threads trash')\nEOF", 'gmail', 'PASS'),
        # scope: deleting a LABEL is not deleting mail -- must stay allowed
        ("gws gmail users labels delete --id L1", 'gmail', 'PASS'),
        # but a hidden scope word is UNKNOWN and must fail closed
        ("gws gmail users $THING delete --id L1", 'gmail', 'BLOCK'),
    ]
    gmail_d = ['delete', 'batchDelete', 'trash']
    gmail_s = ['modify', 'untrash', 'list', 'get']
    bad = 0
    for cmd, svc, want in cases:
        d, s = (gmail_d, gmail_s) if svc == 'gmail' else (D, S)
        req = ['messages', 'threads'] if svc == 'gmail' else None
        got = verdict(cmd, svc, d, s, req)
        ok = got == want
        bad += (not ok)
        print("  [%s] %-5s %s" % ('PASS' if ok else 'FAIL', got, cmd.splitlines()[0][:66]))
    print("\n%d checks, %d failed" % (len(cases), bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--service', help='gws service word, e.g. sheets / gmail / tasks')
    ap.add_argument('--destructive', default='', help='comma-separated destructive verbs')
    ap.add_argument('--safe', default='', help='comma-separated legible-safe verbs')
    ap.add_argument('--require-any', default='', help='comma-separated scope words; at least one must be present')
    ap.add_argument('--write-verbs', default='', help='comma-separated write verbs whose TARGET must be literal')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not a.service:
        ap.error('--service is required')
    d = [x for x in a.destructive.split(',') if x]
    s = [x for x in a.safe.split(',') if x]
    r = [x for x in getattr(a, 'require_any').split(',') if x]
    w = [x for x in getattr(a, 'write_verbs').split(',') if x]
    sys.exit(7 if verdict(sys.stdin.read(), a.service, d, s, r, w) == 'BLOCK' else 0)


if __name__ == '__main__':
    main()
