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

⛔⭐ THIRD DEFECT, fire-tested and CONFIRMED LIVE 2026-08-23 in both repos: an argv built
by ANOTHER INTERPRETER -- a command built with subprocess.run() passed a Python LIST of
words instead of one shell string. That list is not shell text at all; it is exec'd
directly, with no shell in between. gws_segments() still tokenized on WHITESPACE ONLY, so
the whole call was one opaque token (its delimiters are commas and quotes, not spaces),
no segment was ever produced, and verdict() over zero segments defaulted to PASS.
Measured: the fire-test command in system/hooks/tests/firetest-gws-argv-bypass.sh
returned exit 0 -- NOT BLOCKED -- from three sibling guards, while the byte-identical
command written as plain shell returned exit 2.

⛔ WHY THE 2026-08-21 FIX DID NOT ALREADY COVER THIS: that fire test (see
system/hooks/tests/firetest-sheet-sep.sh) found the identical comma/quote shape and
patched it -- but only inside one guard's own BASH regexes (a SEP character class). This
shared Python parser, used by three OTHER guards, was never touched, so the hole
remained open everywhere else. THE FIX HERE, PER THE REPO'S OWN "no more nouns" RULE:
this is not a new keyword or a broadened verb list -- it is recognising that a
comma/quote-delimited run of string literals IS an argv, exactly the way a real
interpreter reads one, regardless of what language or brackets surround it (a list, a
tuple, a JS array, a bare comma-separated call). gws_segments() now runs a second,
structural pass alongside the whitespace one: find every maximal run of two or more
comma-separated quoted literals, decode each item the way an interpreter would, and feed
the resulting token list through the EXACT SAME classifier (assignment/wrapper stripping,
the binary-name match, nonliteral fallback) already used for real shell segments.
Nothing about WHAT is being matched changed; only HOW the argv is read.

⭐ ABSENT vs UNPARSEABLE. Before this fix, "no gws segment found" always meant PASS,
whether that was because the command genuinely never touched gws OR because a shape like
the one above defeated the tokenizer. Those are different findings and must not share an
outcome: an unparseable command is refused rather than guessed at, the same posture
already used for a $VAR or $(...) operation. Two backstops enforce this:
  - a comma-list run whose tail keeps going past what we could read as quoted items (a
    bare variable, an f-string, a spread) gets an explicit UNPARSEABLE sentinel appended
    to its tokens, so the existing "operation word we cannot resolve" rule fires instead
    of silently truncating the argv and reasoning over a partial one;
  - a lone quoted binary-name token immediately followed by a comma -- the shape of a
    list continuing -- that the comma-run pass above did not already resolve into a full
    segment (because the rest of the call is opaque, e.g. a variable built elsewhere) is
    flagged the same way. This is a SHAPE test, not a keyword search: ordinary prose that
    merely mentions the binary name (a commit message, a heredoc body written, never
    executed) is never followed directly by a comma this way, so it keeps passing exactly
    as before -- see the self-test cases marked ABSENT below.

⚠ STILL A SPEED BUMP, NOT A BOUNDARY. A shell (or another interpreter) has infinite
equivalent phrasings; this handles the ones we measured. Treat it accordingly.

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


_NONLIT = re.compile(r'[$`]')

# THIRD DEFECT'S CONSTANTS -- an argv assembled by ANOTHER INTERPRETER (Python, Node, ...)
# is comma/quote-delimited, not whitespace-delimited. These read that shape directly, the way
# the interpreter that built it would, rather than trying to re-derive shell tokenisation rules
# that were never in play. A quoted literal in any of the three quote styles a language
# actually uses for a string/array literal.
_QUOTED = r"(?:'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`(?:[^`\\]|\\.)*`)"
# Bracket/paren/brace/whitespace characters are not delimiters themselves here -- they merely
# decorate a list, tuple, set or bare call-argument list, and are skipped so the SAME regex
# recognises ['a','b'], ('a','b'), {'a','b'} and a bare f('a','b') alike.
_ARGV_JUNK = r"[\s\[\]\(\)\{\}]*"
# A maximal run of two or more comma-separated quoted literals -- the shape of an argv built
# as a list/tuple/array literal, regardless of the language or the brackets around it.
_COMMA_LIST = re.compile(r"%s(?:%s,%s%s)+" % (_QUOTED, _ARGV_JUNK, _ARGV_JUNK, _QUOTED))
_LIST_ITEM = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|`((?:[^`\\]|\\.)*)`")
# BACKSTOP shape: a lone quoted 'gws' immediately followed by a comma -- a list continuing --
# that the comma-run above did not already resolve into a full segment (its neighbour was not
# a quoted literal at all: a bare variable, a function call, a spread). Deliberately NOT a
# keyword search: ordinary prose that merely mentions "gws" is a single quoted string with no
# comma directly after its own closing quote, so it is never matched by this and keeps
# passing.
_SOLO_GWS_QUOTE = re.compile(r"(['\"`])((?:[^'\"`\\]|\\.)*?)\1\s*,")
# Sentinel appended to a token list when part of an argv could not be read as a quoted
# literal. It contains characters no real shell word or quoted string can produce, so it can
# never collide with a legitimate token, and has_nonliteral() below treats it exactly like a
# "$VAR" it cannot resolve -- the same fail-closed rule, not a new one.
UNPARSEABLE = '\x00UNPARSEABLE\x00'


def _list_items(span_text):
    """Decode every quoted literal in a comma-run match, in order, the way an interpreter
    would: strip the surrounding quote characters and keep the content. No further
    unescaping is attempted -- this only needs to recognise the LITERAL VALUE well enough to
    compare it against a service word or a destructive verb, not to reproduce the string
    byte-for-byte."""
    items = []
    for m in _LIST_ITEM.finditer(span_text):
        items.append(next(g for g in m.groups() if g is not None))
    return items


def _classify(toks, out):
    """Shared classifier: strip assignment/wrapper prefixes, then decide whether this token
    list is a recognised gws invocation, an unresolved (nonliteral) one, or neither. Used
    identically for real shell-split segments and for tokens read out of an interpreter-built
    argv -- the SAME rule regardless of how the tokens were assembled, which is the whole
    point: the difference between this repo's two prior fixes and this one is that earlier
    fixes taught the parser a new SHAPE to read; this keeps the decision itself in exactly
    one place."""
    while toks and (_ASSIGN.match(toks[0]) or _debinary(toks[0]) in _WRAPPER):
        toks.pop(0)
    if not toks:
        return
    if _BINARY.match(_debinary(toks[0])):
        out.append(toks)
    elif _NONLIT.search(toks[0]) or toks[0] == UNPARSEABLE:
        out.append(toks)


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
        # FIX 1 + FIX 3, both 2026-08-14, NOW SHARED via _classify(): strip leading NAME=value
        # assignment prefixes and wrapper words before taking the first word (`ID=x gws ...` runs
        # gws; the old parser could not see it), then accept either a literal `gws` binary or a
        # binary name we cannot resolve (`$V`) -- an unresolved binary is kept so has_nonliteral()
        # can still see it and the verdict becomes UNKNOWN, which every calling guard already
        # fails closed on. See _classify()'s own docstring for why this is now one function
        # instead of duplicated inline logic split across this branch and the argv-list branch
        # added below.
        _classify(toks, out)
        # FIX 2: a gws inside $( ) or backticks is still a real invocation.
        for m in _NESTED.finditer(s):
            out.append(m.group(1).split())

    # FIX 4 (2026-08-23, the CONFIRMED LIVE bypass): an argv assembled by ANOTHER INTERPRETER --
    # comma/quote-delimited, never whitespace-delimited, so nothing above ever saw it. Find every
    # maximal run of two or more comma-separated quoted literals ANYWHERE in the command (not
    # just inside one already-split statement, since the statement itself may be a single opaque
    # token to the whitespace splitter above -- see gws_segments()'s module-docstring addendum),
    # decode it the way the interpreter that wrote it would, and classify it through the exact
    # same rule as a real shell segment.
    #
    # NORMALISE ONE MORE SHELL DISGUISE FIRST: this whole command is itself very often the BODY
    # of an outer shell double-quoted argument (`python3 -c "...."`), and inside a shell double
    # quote a backslash immediately before a quote character is stripped by the shell before the
    # inner program ever runs -- `\"gws\"` and `"gws"` execute identically. Scanning the raw text
    # for quote characters without accounting for that disguise missed every list literal written
    # with double-quoted items this way (`subprocess.run(["gws","gmail",...])`), because the
    # first REAL unescaped quote the naive scan could find was the very last one in the whole
    # command, so the entire payload looked like one opaque quoted blob. This mirrors _debinary()
    # above, which strips the same disguise for the binary name; used ONLY for finding argv-list
    # shape, never for anything the whitespace-tokenised path above already relies on.
    argv_cmd = cmd.replace('\\"', '"').replace("\\'", "'")
    covered = []
    for m in _COMMA_LIST.finditer(argv_cmd):
        covered.append((m.start(), m.end()))
        items = _list_items(m.group(0))
        if not items:
            continue
        toks = items
        # The list may continue past what we could read as a quoted literal -- a bare variable,
        # an f-string, a spread operator. That is NOT the same finding as "the list ends here",
        # and must not be reasoned over as if it were a complete, literal argv: append the
        # UNPARSEABLE sentinel so has_nonliteral() (and therefore every existing UNKNOWN-fails-
        # closed rule downstream) treats the unread remainder as exactly that -- unknown.
        tail = argv_cmd[m.end():m.end() + 2].lstrip()
        if tail.startswith(','):
            toks = toks + [UNPARSEABLE]
        _classify(toks, out)

    # BACKSTOP: a lone quoted 'gws' immediately followed by a comma that the comma-run pass above
    # did not already turn into a resolved segment (its neighbour in the list was not itself a
    # quoted literal -- e.g. a bare variable or a function call standing in for the rest of the
    # argv). ABSENT (no such shape at all -- an ordinary command, a commit message, a heredoc
    # body) and UNPARSEABLE (the shape exists but the rest of it could not be read) are kept
    # distinct here on purpose: this returns a segment, not a silent skip, so verdict() below
    # can no longer default to PASS over it.
    for m in _SOLO_GWS_QUOTE.finditer(argv_cmd):
        if any(start <= m.start() < end for start, end in covered):
            continue
        # Reuse the SAME binary-recognition rule as every other path (_BINARY / _debinary):
        # a path-qualified binary ('/usr/local/bin/gws',) is the identical invocation as a
        # bare literal ('gws',) and must be caught the same way -- restored 2026-08-26 after
        # the private rewrite narrowed this to the bare literal only, which a path-qualified
        # call defeated.
        if not _BINARY.match(_debinary(m.group(2))):
            continue
        out.append(['gws', UNPARSEABLE])
    return out


def has_nonliteral(toks):
    """Does any token hide its value behind a variable, a substitution, or an argv this parser
    could read only PART of (the UNPARSEABLE sentinel -- see gws_segments())? All three are the
    same finding from a caller's point of view: this token's real value cannot be read, so it
    must not be reasoned about as if it were literal text."""
    return any(t == UNPARSEABLE or _NONLITERAL.search(t) for t in toks)


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
        # A fully-opaque argv (the SOLO_GWS_QUOTE backstop, `['gws', UNPARSEABLE]`) never
        # literally names a service -- there was nothing left to read once the rest of the call
        # turned out to be a variable or a function result, not a quoted literal. We cannot know
        # which service it targets, so it is not this guard's business to decide it is SOME OTHER
        # guard's problem: every guard checking any service must treat it as BLOCK. Skipping the
        # service-name filter below only for this exact shape is what makes that possible; every
        # other segment still has to literally name the service being checked, same as before.
        if len(toks) == 2 and toks[0] == 'gws' and toks[1] == UNPARSEABLE:
            return 'BLOCK'
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


def verdict_reason(cmd, service, destructive, safe, require_any=None, write_verbs=None):
    """ADDITIVE, MESSAGE-ONLY HELPER -- does not decide anything by itself, and nothing in this
    file real gating path (verdict(), main() sys.exit) calls it. It exists because several
    callers were reusing ONE rule deny message for every reason verdict() can return BLOCK,
    including the fail-closed we-could-not-resolve-this case -- so an unparseable drafts-create
    command came back denied with a Gmail-deletion-specific message that named a rule the command
    never touched. Measured 2026-08-23.

    Mirrors verdict() conditions and their ORDER exactly, so the reason it reports can never
    disagree with the decision verdict() already made. A caller uses this ONLY after verdict()
    (via the unchanged --service/--destructive/... invocation) has already returned BLOCK, purely
    to pick which honest message to print.

    Returns (verdict, reason) where reason is one of:
      None                   -- PASS, or no gws segment for this service was found
      unresolved_operation   -- the operation itself could not be read (a $VAR, a substitution, or
                                 an xargs-style placeholder sits where the verb should be)
      unparseable_argv       -- an argv assembled by another interpreter (Python, Node, ...) that
                                 this parser could recognise as naming the gws binary but could
                                 not read far enough to know which service it targets at all
      destructive             -- a literal, in-scope destructive verb was matched
      unresolved_target      -- a literal write verb, but its TARGET could not be read
    """
    write_verbs = write_verbs or []
    for toks in gws_segments(cmd):
        # Mirrors verdict()'s own special case above, in the same order, for the same reason:
        # a fully-opaque argv never names a service literally, so every service check must
        # treat it as BLOCK rather than silently skipping past it.
        if len(toks) == 2 and toks[0] == 'gws' and toks[1] == UNPARSEABLE:
            return "BLOCK", "unparseable_argv"
        seg = " ".join(toks)
        if not re.search(r"\b%s\b" % re.escape(service), seg, re.I):
            continue
        chain = op_chain(toks, service)
        if not chain:
            if has_nonliteral(toks):
                return "BLOCK", "unresolved_operation"
            continue
        if has_nonliteral(chain):
            return "BLOCK", "unresolved_operation"
        low = [c.lower() for c in chain]
        in_scope = (not require_any) or any(w.lower() in low for w in require_any)
        if in_scope and any(v.lower() in low for v in destructive):
            return "BLOCK", "destructive"
        if any(v.lower() in low for v in write_verbs):
            if has_nonliteral(toks[len(chain) + 1:]):
                return "BLOCK", "unresolved_target"
    return "PASS", None


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

        # -- REGRESSION, 2026-08-23: the CONFIRMED LIVE bypass, argv built by ANOTHER
        # INTERPRETER (comma/quote-delimited, never whitespace-delimited). Every one of these
        # returned exit 0 / PASS before the fix; see this file's module docstring.
        ("python3 -c \"import subprocess; subprocess.run(['gws','gmail','users','threads','trash','--id','18abc'])\"", 'gmail', 'BLOCK'),
        # Node-style: the binary as its own quoted argument, the rest as a separate array literal.
        ("execFileSync('gws', ['gmail','users','threads','trash','--id','18abc'])", 'gmail', 'BLOCK'),
        # A tuple, not a list -- the comma/quote shape is what matters, not the bracket character.
        ("subprocess.run(('gws','gmail','users','threads','trash','--id','18abc'))", 'gmail', 'BLOCK'),
        # Mixed quote styles within one argv must not defeat the extraction.
        ("subprocess.run(['gws',\"gmail\",'users','threads',\"trash\",'--id','18abc'])", 'gmail', 'BLOCK'),
        # The same shape with a SAFE verb must still PASS -- proof this is not "block every list".
        ("subprocess.run(['gws','gmail','users','threads','untrash','--id','18abc'])", 'gmail', 'PASS'),
        # A list that trails off into a bare (unquoted) variable partway through must not be
        # silently truncated and read as a clean, short, harmless argv -- it is UNKNOWN and
        # fails closed, same as a $VAR would in the whitespace path.
        ("subprocess.run(['gws','gmail','users','threads', op, '--id', tid])", 'gmail', 'BLOCK'),
        # Fully opaque construction: gws named, the rest of the argv is a function call, not a
        # literal. We cannot know which service this targets, so it fails closed for EVERY
        # service a guard might be checking, not just the one that happens to guess right.
        ("os.execvp('gws', build_argv())", 'gmail', 'BLOCK'),
        ("os.execvp('gws', build_argv())", 'sheets', 'BLOCK'),
        # REGRESSION, 2026-08-26: a PATH-QUALIFIED binary defeated the narrowed
        # _SOLO_GWS_QUOTE backstop (it only matched the bare literal). Restored by
        # routing the backstop's matched content through the same _BINARY/_debinary
        # check every other path already uses.
        ("os.execvp('/usr/local/bin/gws', build_argv())", 'sheets', 'BLOCK'),
        # ABSENT, not unparseable: an ordinary comma-bearing sentence that merely MENTIONS gws is
        # never a list-literal shape and must keep passing exactly as before the fix.
        ("echo 'gws, gmail, and sheets are all guarded now, for what it is worth'", 'gmail', 'PASS'),
        # ABSENT: a real, unrelated two-item list near an unrelated mention of gws elsewhere in
        # the same line must not be swept in by proximity alone.
        ("echo 'gws was mentioned here'; run(['a','b'])", 'gmail', 'PASS'),
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
    # ADDITIVE, MESSAGE-ONLY. Does not touch the decision path above or below it: the ORIGINAL
    # invocation a caller already made (no --reason-only) still runs verdict() and exits 7/0
    # exactly as before, byte-for-byte. This flag is for a SECOND, separate invocation a caller
    # makes only after that original call already returned BLOCK, purely to learn which of
    # verdict()'s three conditions fired so it can print an honest reason instead of reusing one
    # rule's message for all of them. Always exits 0 -- it is a query, never a gate.
    ap.add_argument('--reason-only', action='store_true',
                     help='print WHY verdict() would say BLOCK (unresolved_operation / destructive '
                          '/ unresolved_target / none), then exit 0. Never gates anything itself.')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not a.service:
        ap.error('--service is required')
    d = [x for x in a.destructive.split(',') if x]
    s = [x for x in a.safe.split(',') if x]
    r = [x for x in getattr(a, 'require_any').split(',') if x]
    w = [x for x in getattr(a, 'write_verbs').split(',') if x]
    if a.reason_only:
        _, reason = verdict_reason(sys.stdin.read(), a.service, d, s, r, w)
        print(reason or 'none')
        sys.exit(0)
    sys.exit(7 if verdict(sys.stdin.read(), a.service, d, s, r, w) == 'BLOCK' else 0)


if __name__ == '__main__':
    main()
