#!/usr/bin/env python3
"""verify_parse — the one parser for a card's `Verify:` line, shared by plan_lint.py
(refuses an unparseable card at write time) and plan_retire.py (re-runs the parsed
command at retire time). Card 6.1, 2026-09-05.

WHAT a Verify: line is. Exactly two runnable shapes, plus one that LOWERS to the first:
  SHAPE — `cmd` → before `X`, after `Y`   (checks Y is now true; X is the destruction
                                            probe, SOP §V.4c — a check never seen to fail)
  RUN   — `cmd; echo $?` → `N`             (the LAST non-empty line of stdout is compared
                                            to N; empty stdout falls back to the exit code)
  JUDGE — `Verify: JUDGE` — artifact: <path>   lowers to SHAPE: `test -s "<path>"; echo $?`
          → `0`. The judgment itself is not code-checkable; the artifact's existence is
          what the parser can check, so this still only ever emits a runnable pair.
Multi-clause verifies (separated by ` · `) pair each clause with its OWN expectation —
this already worked when every clause's leading token was recognised.

THE ONE RULE, THREE SURFACES: nothing unrecognised is ever silently dropped — it is
reported, as a VerifyParseError (CANNOT-READ at retire time, a defect at lint time).
  (a) DROPPED CLAUSE — 2026-09-05, card 6.2: three ` · ` clauses, the middle one led
      with the literal token `...`. The old parser filtered unknown-command backtick
      spans out of its scan and returned pairs for the two clauses either side —
      wrong: it should have refused the WHOLE Verify, because the surviving clauses
      no longer say what the card's author meant to check.
  (b) DROPPED CARD — a `- [ ] **` line whose id does not match the ID pattern was
      previously just never matched by CARD_RE and vanished from parse_cards with no
      trace. `ID` here does NOT cover this on its own; plan_lint.py additionally scans
      for any `- [ ] **` line and reports one whose id it could not recognise.
  (c) DROPPED SUBSTITUTION — a Verify command still carrying an unsubstituted
      `<placeholder>` (e.g. `<copy>`, `<id>`) is refused here too: the shell reads `<`
      as a redirection operator, so the command would silently test nothing rather
      than fail loudly. A JUDGE `artifact:` value is a real path, not a command-string
      placeholder, and is checked the same way but is not mistaken for one just for
      using this same regex.

VERDICT for callers: `parse_verify(line)` returns `[(cmd, expectation-or-None), ...]`
on success, or raises `VerifyParseError` — never a partial list standing in for a
refusal. `expectation` may still be `None` for one pair (no stated outcome on that
clause) — that is a *different*, pre-existing failure mode callers already handle.
"""
import re

ID = r'[A-Za-z]{0,2}\d{1,3}[a-z]?(?:\.\d{1,2}[a-z]?)?'
BARE_CARD_RE = re.compile(r'^- \[ \] \*\*')
CARD_ID_RE = re.compile(r'^- \[ \] \*\*(' + ID + r')\b')

KNOWN_CMDS = {"python3", "grep", "test", "wc", "ls", "awk", "git", "gh",
              "bash", "sh", "cat", "diff", "head", "tail",
              # 2026-09-05, card 6.1 fix 1: common read-only shell tools a card's
              # own Verify legitimately pipes through (repaired.plan.md 2.4: `sed`).
              # Deliberately NOT here: bare `echo` -- a Verify whose command is just
              # `echo` tests nothing, and that should stay refused.
              "sed", "find", "sort", "uniq", "cut", "tr", "jq", "printf",
              "basename", "dirname", "python"}
SCRIPT_RE = re.compile(r'^[\w.-]+\.py$')          # a bare `foo.py` naming a repo tool

CLAUSE_SPLIT_RE = re.compile(r'\s+·\s+')
PLACEHOLDER_RE = re.compile(r'<[^<>\s][^<>]*>')
JUDGE_RE = re.compile(r'\bJUDGE\b.*?\bartifact:\s*`?([^`\n]+?)`?\s*$', re.I)
TYPE_LABEL_RE = re.compile(r'^(?:Verify:)?\s*(SHAPE|RUN|JUDGE)\s*$', re.I)


class VerifyParseError(Exception):
    """A Verify: line could not be turned, in full, into (command, expectation)
    pairs. Never partially satisfied — see the module docstring's three surfaces."""


def _is_known_cmd(text):
    """True for a shell builtin/tool in KNOWN_CMDS, or a bare `<script>.py NAME arg...`
    invocation — cards name their own tools by filename only (e.g. `plan_lint.py args`),
    and that was being silently dropped as unrecognised (2026-09-04, task 2.3:
    CANNOT-READ 'no runnable verify' when the tool itself was right there, executable,
    on disk). A bare script name with NO args (task 2.1: `plan_lint.py` alone, mid
    prose) is a REFERENCE to the tool, not a complete invocation — recognising it
    anyway pulled in an unrelated `exit 2` from three clauses later in the sentence
    (2026-09-04, discovered fixing 2.3). Requiring an argument is what tells the two
    apart; a card that genuinely means to run a script with no arguments does not
    exist here."""
    toks = text.split()
    if not toks:
        return False
    if toks[0] in KNOWN_CMDS:
        return True
    return bool(SCRIPT_RE.match(toks[0])) and len(toks) > 1


def classify(text):
    """Given a chunk of expectation text, return (kind, value) or None."""
    t = text.strip()
    m = re.search(r'\bexit\s+(-?\d+)', t, re.I)
    if m: return ('exit', int(m.group(1)))
    m = re.search(r'≥\s*(-?\d+)', t)          # >=
    if m: return ('ge', int(m.group(1)))
    m = re.search(r'≤\s*(-?\d+)', t)          # <=
    if m: return ('le', int(m.group(1)))
    m = re.search(r'"([^"]+)"', t)
    if m: return ('substr', m.group(1))
    m = re.search(r"'([^']+)'", t)
    if m: return ('substr', m.group(1))
    bare = t.strip('`.,; \t')
    if re.fullmatch(r'-?\d+', bare):
        return ('bare', int(bare))
    return None


def _command_attempt_span(clause):
    """Return the content of the first backtick-quoted span in `clause` that is
    NOT just the `Verify: SHAPE`/`RUN`/`JUDGE` type label -- i.e. the span that
    LOOKS like a command attempt, whether or not its leading token turns out to
    be recognised. None if the clause carries no such span at all (2026-09-05,
    fix 2: naming the label span's token -- 'Verify:' -- as "the unrecognised
    command" sent the reader to fix the wrong thing; every card's first clause
    legitimately starts with that label)."""
    for m in re.finditer(r'`([^`]+)`', clause):
        content = m.group(1).strip()
        if TYPE_LABEL_RE.match(content):
            continue
        return content
    return None


def _parse_clause(clause):
    """Return [(cmd, exp), ...] found in ONE ` · `-delimited clause, or None if the
    clause carries no recognised command at all (the dropped-clause case, surface a)."""
    spans = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r'`([^`]+)`', clause)]
    cmd_spans = [s for s in spans if _is_known_cmd(s[2])]
    if not cmd_spans:
        return None
    out = []
    for k, (start, end, cmd) in enumerate(cmd_spans):
        gap_end = cmd_spans[k + 1][0] if k + 1 < len(cmd_spans) else len(clause)
        gap = clause[end:gap_end]
        if '→' not in gap:               # no arrow -> no stated outcome
            out.append((cmd, None)); continue
        after_arrow = gap.split('→', 1)[1]
        m = re.search(r'\bafter\b\s*`?([^`,.\s]+)`?', after_arrow, re.I)
        exp = classify(m.group(1)) if m else None
        if exp is None:
            # A backtick-quoted expectation sitting right after the arrow is read
            # verbatim and parsing STOPS at its closing backtick -- a parenthetical
            # aside or a trailing sentence after that point is never consulted.
            m2 = re.match(r'\s*`([^`]+)`', after_arrow)
            exp = classify(m2.group(1)) if m2 else classify(after_arrow)
        out.append((cmd, exp))
    return out


def parse_verify(line):
    """Turn one card's Verify: line into [(cmd, expectation-or-None), ...].

    Raises VerifyParseError, never returning a partial result, when:
      - any ` · ` clause's leading command token is unrecognised (surface a),
      - a command (or a JUDGE artifact: value) still carries an unsubstituted
        `<placeholder>` (surface c),
      - a JUDGE line names no artifact: value at all,
      - the line yields no runnable command whatsoever (a prose-only Verify).
    """
    text = line.strip()

    jm = JUDGE_RE.search(text)
    if jm:
        path = jm.group(1).strip()
        if not path:
            raise VerifyParseError("JUDGE Verify names no artifact: value to check")
        ph = PLACEHOLDER_RE.search(path)
        if ph:
            raise VerifyParseError(
                f"JUDGE artifact: value is an unsubstituted placeholder {ph.group(0)!r} "
                f"({path!r}) -- a card's Verify must run as written by a stranger")
        return [(f'test -s "{path}"; echo $?', ('bare', 0))]

    clauses = CLAUSE_SPLIT_RE.split(text)
    out, problems = [], []
    for idx, clause in enumerate(clauses, 1):
        pairs = _parse_clause(clause)
        if pairs is None:
            span = _command_attempt_span(clause)
            if span is None:
                problems.append(
                    f"clause {idx}/{len(clauses)}: no command-shaped (backtick-quoted) span "
                    f"at all, only the `Verify: TYPE` label and/or prose -- name a real `cmd` "
                    f"in backticks: {clause.strip()[:120]!r}")
            else:
                tok = span.split()[0] if span.split() else "(empty)"
                problems.append(
                    f"clause {idx}/{len(clauses)}: leading token {tok!r} (from `{span}`) is "
                    f"not in the recognised command set ({', '.join(sorted(KNOWN_CMDS))}, or a "
                    f"bare `<script>.py ARG...`), so this clause cannot become a (command, "
                    f"expectation) pair -- {clause.strip()[:120]!r}")
            continue
        for cmd, exp in pairs:
            ph = PLACEHOLDER_RE.search(cmd)
            if ph:
                problems.append(
                    f"clause {idx}/{len(clauses)}: command still carries the unsubstituted "
                    f"placeholder {ph.group(0)!r} -- the shell reads `<` as redirection, so "
                    f"`{cmd}` would silently test nothing rather than fail loudly")
                continue
            out.append((cmd, exp))
    if problems:
        raise VerifyParseError(
            "Verify is unparseable -- a Verify: is exactly one of two runnable shapes "
            "(`cmd; echo $?` -> `N`, or `cmd` -> before `X`, after `Y`; JUDGE lowers to "
            "the first). Every clause must turn into a (command, expectation) pair or the "
            "WHOLE card is refused -- never just the clauses that happened to parse "
            "(2026-09-05, card 6.2: a silent `...` clause dropped its own check while its "
            "neighbours quietly passed): " + "; ".join(problems))
    if not out:
        raise VerifyParseError(
            "no runnable command found on the Verify: line -- a prose-only Verify "
            "(\"re-read the file and confirm it looks right\") cannot be turned into "
            "(command, expectation) pairs; name a real `cmd` in backticks")
    return out


def _self_smoke():
    """No fixtures needed: a handful of hand-built lines proving each surface fires,
    plus that the two legitimate shapes still parse clean."""
    ok_lines = [
        '`Verify: SHAPE` — `grep -c "debounce" system/tools/pulse_alert.py` → before `0`, after `1`.',
        '`Verify: JUDGE` — artifact: system/tools/plan_lint.py',
        '`Verify: RUN` `python3 -m pytest tests/test_x.py -q; echo $?` → `0`',
    ]
    bad_lines = [
        '`Verify:` `grep -c x y; echo $?` → `0` · `...` · `grep -c z y; echo $?` → `1`',
        '`Verify: SHAPE` — `cat <copy>` → before `0`, after `1`.',
        '`Verify: SHAPE` — re-read the file and confirm it looks right → before `no`, after `yes`.',
        '`Verify: JUDGE` — artifact: <this plan>',
    ]
    failed = False
    for t in ok_lines:
        try:
            r = parse_verify(t)
            print(f"OK      parsed: {t[:70]!r} -> {r}")
        except VerifyParseError as e:
            print(f"FAIL (should have parsed): {t}\n  {e}"); failed = True
    for t in bad_lines:
        try:
            r = parse_verify(t)
            print(f"FAIL (should have been refused): {t} -> {r}"); failed = True
        except VerifyParseError as e:
            print(f"OK      refused: {t[:70]!r}")

    # fix 2, 2026-09-05: an unrecognised command token must be named in the
    # message -- never the `Verify: TYPE` label every card legitimately starts
    # with. Regression case: this is exactly repaired.plan.md card 2.4's shape.
    mislabel_case = ('`Verify: SHAPE` — `sed -n \'1,20p\' system/tools/pulse_alert.py | '
                      'grep -c "DEBOUNCE_SECONDS"` → before `0`, after `1`.')
    try:
        r = parse_verify(mislabel_case)
        print(f"OK      parsed (sed now known): {mislabel_case[:70]!r} -> {r}")
    except VerifyParseError as e:
        print(f"FAIL (sed is now a known command, this should parse): {e}"); failed = True

    unknown_cmd_case = ('`Verify: SHAPE` — `frobnicate -x file.txt` → before `0`, after `1`.')
    try:
        r = parse_verify(unknown_cmd_case)
        print(f"FAIL (should have been refused): {unknown_cmd_case} -> {r}"); failed = True
    except VerifyParseError as e:
        msg = str(e)
        names_right_token = "'frobnicate'" in msg
        names_wrong_token = "'Verify:'" in msg
        if names_right_token and not names_wrong_token:
            print(f"OK      refused, names 'frobnicate' not 'Verify:': {unknown_cmd_case[:70]!r}")
        else:
            print(f"FAIL (message names the wrong token): {msg}"); failed = True
    return not failed


if __name__ == "__main__":
    import sys
    ok = _self_smoke()
    print("SELF-CHECK OK" if ok else "SELF-CHECK FAILED")
    sys.exit(0 if ok else 1)
