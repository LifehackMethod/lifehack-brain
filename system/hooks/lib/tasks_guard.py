#!/usr/bin/env python3
"""tasks_guard — decide whether a shell command would write to the goals task list.

WHY THIS EXISTS, AND WHY IT IS NOT A REGEX.
The control this replaces was a bash guard that matched the command as TEXT. Three independent
auditors, each charged to REFUTE it, found SEVENTEEN working bypasses across three passes. Not one
needed anything exotic — a semicolon, a newline, two adjacent quotes, `xargs`, a duplicate JSON key,
a magic word. Each round was patched and the next round broke it somewhere new, and the patch for
round two BROKE THE LEGITIMATE PATH: a day's plan titled `Q3 R&D review` was refused, because a text
matcher cannot tell an `&` inside a quoted string from a shell operator.

That is the signature of the wrong instrument. A shell command is a LANGUAGE — infinite spellings of
the same act — and a matcher is always one spelling behind. So this module stops matching and starts
PARSING. Three failures the text version could not have avoided, all closed here by construction:

  1. `&` / `#` / `;` INSIDE A QUOTED STRING. `shlex` knows quoting, so a task titled "Call bank
     #urgent" is one token and not two statements. The false-deny disappears; it is not patched.
  2. A DUPLICATE JSON KEY. `{"parent":"<real>", ..., "parent":"<a goal>"}` fooled the old guard,
     which found the first and approved, while a real JSON parser takes the LAST. `json.loads` here
     resolves it exactly as the API will, so the guard reasons about the value that will actually be
     sent — not a different one that happens to appear earlier in the text.
  3. `@default`, AND AN OMITTED TARGET. Google Tasks resolves both to the caller's default list, and
     this repo's own code uses that alias (shared/tools/tasks_store_sync.py). A guard keyed on the
     configured ID never sees them. Here they are UNRESOLVED, and unresolved is refused, because
     whether the default list IS the goals list cannot be known without asking Google.

⛔ WHAT THIS STILL CANNOT DO. It is a better instrument, not a wall. It does not execute the shell,
so a command whose text is assembled at runtime (`$VAR`, a substitution, a file read) is opaque to
it — those are REFUSED rather than guessed at, which is the safe direction but is still a refusal
rather than an understanding. It also cannot know your list ids without config. If you need an act
to be impossible rather than merely difficult, it does not belong in front of a shell at all.

VERDICTS (a closed set, returned as an exit code by __main__):
  0  ALLOW    nothing here touches the goals list, or it is the one sanctioned write
  2  DENY     with a reason on stderr
"""
from __future__ import annotations   # /usr/bin/python3 on macOS is 3.9

import json
import os
import re
import shlex
import sys

# Verbs that only ever READ. Everything else — including a verb nobody has invented yet — is
# treated as a write. This is the inversion that the text guard eventually reached too: recognise
# what is safe and refuse the rest, never list what is dangerous.
READ_VERBS = {"list", "get"}

# The four that may legitimately add or amend a subtask under the day's parent. delete and clear are
# deliberately absent: Google Tasks keeps no version history, so they are the two acts with no undo,
# and they are refused on the goals list even when everything else about the command is correct.
CARVE_OUT_VERBS = {"insert", "update", "patch", "move"}

NOUNS = {"tasks", "tasklists"}

# Words a command can be wrapped in without changing what it does. Stripped so that
# `env gws ...` and `command gws ...` are seen as the invocation they are.
WRAPPERS = {"env", "command", "exec", "nohup", "time", "builtin", "sudo", "xargs"}

_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_NONLITERAL = re.compile(r"[$`]")
# A substitution that names the config key it is about to resolve. This is the one indirection that
# is legible WITHOUT being executed: it says, in plain text, which key it will read. The shipped
# day's-plan command is written this way, so refusing all substitutions would refuse the only write
# this system is supposed to make.
_GET_KEY = re.compile(r"--get\s+([A-Za-z_][A-Za-z0-9_]*)")

# CONFIRMED LIVE, 2026-08-23: the SAME argv-built-by-another-interpreter shape that bypassed
# system/hooks/lib/gws_guard.py bypasses this parser too, for an analogous reason. shlex is
# quote-aware, so a command built as `python3 -c "import subprocess; subprocess.run([...])"`
# becomes ONE statement -- ['python3', '-c', "import subprocess; subprocess.run([...])"] --
# because shlex correctly refuses to split inside the outer quoted -c argument. is_gws_tasks()
# then checks toks[1] == 'tasks', finds '-c' instead, and the whole call is invisible to this
# guard. The fix mirrors gws_guard.py's: read a comma/quote-delimited run of string literals as
# its own argv, the way the interpreter that built it would, and hand the result through the
# EXACT SAME judge()/is_gws_tasks()/find_verb() pipeline as a real shlex statement -- nothing
# about what counts as a write changes, only how the argv is found.
_QUOTED = r"(?:'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`(?:[^`\\]|\\.)*`)"
_ARGV_JUNK = r"[\s\[\]\(\)\{\}]*"
_COMMA_LIST = re.compile(r"%s(?:%s,%s%s)+" % (_QUOTED, _ARGV_JUNK, _ARGV_JUNK, _QUOTED))
_LIST_ITEM = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|`((?:[^`\\]|\\.)*)`")
# Sentinel for a list that trailed off into a bare variable/expression partway through: kept as
# its own token so a caller reasoning about the argv sees UNKNOWN, never a silently truncated
# (and therefore falsely short and harmless-looking) argument list.
_ARGV_UNPARSEABLE = '\x00UNPARSEABLE\x00'


def _argv_list_statements(command):
    """Find every maximal run of two or more comma-separated quoted literals ANYWHERE in the raw
    command text and return each as its own token list, decoded the way the interpreter that
    built it would read it. This is a SHAPE test (quote, comma, quote, ...), not a keyword
    search, so it does not fire on ordinary prose that merely mentions gws or tasks.

    Also undoes the one shell disguise that defeats a naive quote scan: this command is very
    often itself the BODY of an outer shell double-quoted argument (`python3 -c "...."`), and
    inside a shell double quote a backslash immediately before a quote is stripped by the shell
    before the inner program ever runs -- a backslash-quote and a bare quote execute identically.
    Used ONLY here, never for the shlex-based statements above, which already see the real thing.
    """
    argv_cmd = command.replace('\\"', '"').replace("\\'", "'")
    out = []
    for m in _COMMA_LIST.finditer(argv_cmd):
        items = []
        for im in _LIST_ITEM.finditer(m.group(0)):
            items.append(next(g for g in im.groups() if g is not None))
        if not items:
            continue
        tail = argv_cmd[m.end():m.end() + 2].lstrip()
        if tail.startswith(','):
            items = items + [_ARGV_UNPARSEABLE]
        out.append(items)
    return out


class Verdict:
    """A decision plus the sentence a human will read. The reason is not decoration: a guard that
    blocks without explaining sends the next session to fix the wrong thing."""

    def __init__(self, allow: bool, reason: str = "", redirect: str = ""):
        self.allow = allow
        self.reason = reason
        self.redirect = redirect


def split_statements(command: str):
    """Split a command line into statements, QUOTE-AWARE.

    This is the whole reason the false-deny existed. `punctuation_chars=True` makes shlex emit
    `;`, `&&`, `||`, `|`, `&` and newlines as their own tokens while leaving those same characters
    ALONE inside quotes — so `--json '{"title":"Q3 R&D review"}'` stays one argument, and
    `a ; b` is two statements. Returns None if the line cannot be tokenized at all, which is a
    refusal, never a pass.
    """
    try:
        # ⚠ A NEWLINE IS A SEPARATOR, AND shlex TREATS IT AS WHITESPACE BY DEFAULT — so two lines
        # silently merged into one token list, and a delete on the second line hid behind the read
        # verb on the first. Removing it from `whitespace` and adding it to `punctuation_chars`
        # makes it a token, which is what it is. Doing this INSIDE shlex rather than splitting the
        # string on newlines first is the whole point: a newline inside a quoted note stays part of
        # that note, so a multi-line task body is not mistaken for a second statement.
        lex = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace_split = True
        lex.whitespace = " \t\r"
        tokens = list(lex)
    except ValueError:
        return None                      # unbalanced quotes: we do not get to guess

    statements, current = [], []
    for tok in tokens:
        if tok in (";", "&&", "||", "|", "&", "\n"):
            if current:
                statements.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        statements.append(current)

    # CONFIRMED LIVE, 2026-08-23: an argv assembled by ANOTHER INTERPRETER (see
    # _argv_list_statements()'s own docstring) is invisible to the shlex-based split above --
    # its delimiters are commas and quotes, not the whitespace/punctuation shlex tokenises on.
    # Add each one it finds as its own extra statement, judged by the exact same pipeline.
    statements.extend(_argv_list_statements(command))
    return statements


def _strip_wrappers(tokens):
    """Drop assignment prefixes and wrapper words so the real binary is at the front."""
    i = 0
    stripped_any = False
    while i < len(tokens):
        t = tokens[i]
        if _ASSIGN.match(t) or os.path.basename(t) in WRAPPERS:
            i += 1
            stripped_any = True
            continue
        # A wrapper's OWN flags sit between it and the real command: `xargs -I{} gws ...`. Without
        # this, stripping stopped at `-I{}` and the invocation behind it was never recognised as a
        # gws call at all — which is exactly how the xargs bypass reached the goals list.
        if stripped_any and t.startswith("-"):
            i += 1
            continue
        break
    return tokens[i:]


def is_gws_tasks(tokens):
    """Is this statement a `gws tasks ...` invocation? Matches the binary by BASENAME, so an
    absolute path counts, and after wrapper-stripping, so `env gws` counts."""
    toks = _strip_wrappers(tokens)
    if len(toks) < 2:
        return False
    if toks[1] != "tasks":
        return False
    # A binary held in a variable is STILL an invocation — `V=gws; $V tasks tasks delete` runs
    # exactly the same command. Refusing to recognise it because the name is not literal is how it
    # walked past the previous guard entirely. Recognise it, and let the unresolved-target and
    # unreadable-verb branches refuse it on their own terms.
    if _NONLITERAL.search(toks[0]):
        return True
    return os.path.basename(toks[0]) == "gws"


def find_verb(tokens):
    """The verb, read positionally: `gws tasks <noun> <verb>`. Returns None when the slot holds
    something that is not a bare word — an `xargs` placeholder, a variable — which is UNKNOWN and
    must not be read as a read."""
    toks = _strip_wrappers(tokens)
    # ⚠ START AFTER THE SERVICE WORD. The shape is `gws tasks <noun> <verb>`, and the service word
    # is itself literally "tasks" — so scanning from the front matched the SERVICE as the noun and
    # returned "tasks" as the verb. Every read was then treated as an unknown verb, and the shipped
    # day's-plan write was refused. Caught by this module's own selftest before it was wired up.
    toks = toks[2:] if len(toks) > 2 else []
    for i, t in enumerate(toks):
        if t in NOUNS and i + 1 < len(toks):
            nxt = toks[i + 1]
            if _NONLITERAL.search(nxt) or not re.match(r"^\+?[A-Za-z][A-Za-z0-9_-]*$", nxt):
                return None              # a verb we cannot read is not a verb we can trust
            return nxt.lstrip("+")       # gws's own shorthand, e.g. +insert
    return None


def _json_bodies(tokens):
    """Every JSON object passed as a flag value, parsed by a REAL parser.

    Parsing rather than matching is what closes the duplicate-key bypass: `json.loads` keeps the
    LAST value for a repeated key, which is what the API will receive. The old guard searched the
    text, found an earlier occurrence, and approved a write that would actually land somewhere else.
    """
    out = []
    for t in tokens:
        s = t.strip()
        if s.startswith("{") and s.endswith("}"):
            # ⚠ THE SHIPPED COMMAND IS NOT VALID JSON BEFORE THE SHELL RUNS IT. It reads
            #   {"tasklist":"$(python3 "$ROOT/shared/cal_config.py" --get goals_tasklist)"}
            # and those inner double quotes end the JSON string early. It becomes valid only AFTER
            # the shell expands the substitution — which we deliberately never do. Parsing it raw
            # therefore fails, and treating that failure as "unknown" refused the one write this
            # system exists to make. So substitutions are collapsed to a sentinel FIRST: the body
            # becomes parseable, and the sentinel still carries which config key it names.
            s = re.sub(r"\$\([^)]*--get\s+([A-Za-z_][A-Za-z0-9_]*)[^)]*\)",
                       lambda m: "__SUBST:%s__" % m.group(1), s)
            s = re.sub(r"\$\([^)]*\)", "__SUBST:UNKNOWN__", s)
            s = re.sub(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?", "__SUBST:UNKNOWN__", s)
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    out.append(obj)
            except ValueError:
                out.append(None)         # looked like JSON and is not: unknown, not empty
    return out


def _flag_value(tokens, name):
    """`--name value` or `--name=value`."""
    for i, t in enumerate(tokens):
        if t == name and i + 1 < len(tokens):
            return tokens[i + 1]
        if t.startswith(name + "="):
            return t.split("=", 1)[1]
    return None


def resolve_target(tokens, goals_id):
    """What list does this statement act on?

    Returns one of: 'goals' · 'other' · 'unresolved'.
    ⛔ `@default` and an ABSENT target are UNRESOLVED, not 'other'. Google resolves both to the
    caller's default list, and whether that IS the goals list cannot be known from here. Calling
    them 'other' is what let `delete --params '{"tasklist":"@default"}'` through.
    """
    bodies = _json_bodies(tokens)
    if any(b is None for b in bodies):
        return "unresolved"              # a malformed body may name anything

    value = None
    for b in bodies:
        if "tasklist" in b:
            value = str(b["tasklist"])
    if value is None:
        value = _flag_value(tokens, "--tasklist")

    if value is None:
        return "unresolved"              # no target named: Google supplies the default
    if value.strip() in ("@default", "@Default", "default"):
        return "unresolved"
    m = re.match(r"^__SUBST:([A-Za-z_][A-Za-z0-9_]*)__$", value)
    if m:
        # A substitution collapsed above. It is legible only if it NAMED its config key.
        if m.group(1) == "goals_tasklist":
            return "goals"
        if m.group(1) == "UNKNOWN":
            return "unresolved"
        return "other"
    if _NONLITERAL.search(value):
        key = _GET_KEY.search(value)
        if key:
            return "goals" if key.group(1) == "goals_tasklist" else "other"
        return "unresolved"              # opaque indirection
    if goals_id and value == goals_id:
        return "goals"
    return "other"


def names_daily_parent(tokens, parent_id):
    """Does this statement hang the write from the day's parent task, in a real PARENT slot?

    The value is taken from PARSED json (last-key-wins) or the `--parent` flag — never from a text
    search, which is what a decorative `"notes":"parent:<id>"` exploited.
    """
    value = None
    for b in _json_bodies(tokens):
        if isinstance(b, dict) and "parent" in b:
            value = str(b["parent"])
    if value is None:
        value = _flag_value(tokens, "--parent")
    if value is None:
        return False
    m = re.match(r"^__SUBST:([A-Za-z_][A-Za-z0-9_]*)__$", value)
    if m:
        return m.group(1) == "daily_parent_task"
    if _NONLITERAL.search(value):
        key = _GET_KEY.search(value)
        return bool(key and key.group(1) == "daily_parent_task")
    return bool(parent_id) and value == parent_id


def judge(command: str, goals_id: str, parent_id: str) -> Verdict:
    """The whole decision. Every statement is judged on its own; ONE refusal refuses the line."""
    statements = split_statements(command)
    if statements is None:
        return Verdict(False,
                       "this command could not be parsed, so there is no way to tell what it does.",
                       "REDIRECT: check the quoting and run it again. An unreadable command aimed at "
                       "a list with no undo is refused rather than guessed at.")

    for tokens in statements:
        if not is_gws_tasks(tokens):
            continue

        # No noun at all (`gws tasks --help`, a bare `gws tasks`) names no list and performs no
        # operation on one. That is not an unknown verb — it is not an operation. Distinguishing
        # the two matters: an xargs placeholder DOES sit in a verb slot after a noun, and must
        # still be refused.
        _stripped = _strip_wrappers(tokens)
        if not any(t in NOUNS for t in _stripped[2:]):
            continue

        verb = find_verb(tokens)
        if verb is None:
            target = resolve_target(tokens, goals_id)
            if target in ("goals", "unresolved"):
                return Verdict(False,
                               "the operation in this command is not written out — it is supplied at "
                               "run time, so this guard cannot tell a read from a delete.",
                               "REDIRECT: write the verb literally (a tasks insert, list, and so on) "
                               "so it can be seen before it runs.")
            continue

        if verb in READ_VERBS:
            continue                     # reads always pass, on any list, including the goals list

        # Nothing on file to protect. Matching the calendar guard beside it, a WRITE refuses rather
        # than passing: this guard cannot tell whether the list being written IS the goals list, and
        # guessing wrong is silent and permanent. A read has already passed, above.
        if not goals_id:
            return Verdict(False,
                           "a Google Tasks write, and no goals list is on file — so this guard "
                           "cannot tell whether this command is about to rewrite the list holding "
                           "your goals.",
                           "REDIRECT: put your goals list's id in <notes>/config/cal.md so this "
                           "guard knows what to protect:\n"
                           "    goals_tasklist:    <the id of the task list holding your goals>\n"
                           "    daily_parent_task: <the id of the one task a day's plan hangs from>\n"
                           "Run: python3 shared/cal_config.py   to see what is on file. If you do "
                           "not keep goals in Google Tasks, point goals_tasklist at the list you "
                           "most want protected — there is no safe way to guess.")

        target = resolve_target(tokens, goals_id)

        if target == "unresolved":
            return Verdict(False,
                           "a write whose target list cannot be identified — it is hidden behind a "
                           "variable, or it names @default, or it names no list at all.",
                           "REDIRECT: name the task list explicitly. @default and an omitted list "
                           "both resolve to whatever Google considers your default, which may be the "
                           "very list this guard protects — so it is refused rather than assumed "
                           "safe. Your ids: python3 shared/cal_config.py")

        if target == "other":
            continue                     # any other list is yours to write

        # Aimed at the goals list. Only the day's plan survives.
        if verb not in CARVE_OUT_VERBS:
            return Verdict(False,
                           "a %s aimed at your goals list." % verb,
                           "REDIRECT: nothing may delete or clear anything in the goals list — not "
                           "even the day's plan, which may only ADD subtasks. Google Tasks keeps no "
                           "version history, so these are the two acts with no way back. Remove goals "
                           "yourself, in Google Tasks.")

        if not parent_id:
            return Verdict(False,
                           "a write to your goals list, and no daily parent task is on file.",
                           "REDIRECT: the only permitted write here is a subtask under one specific "
                           "parent. Add it to <notes>/config/cal.md:\n"
                           "    daily_parent_task: <the id of the one task a day's plan hangs from>")

        if not names_daily_parent(tokens, parent_id):
            return Verdict(False,
                           "a write to your goals list that does not hang from the day's parent task.",
                           "REDIRECT: the only permitted write here is a subtask of the task on file "
                           "as daily_parent_task:\n    %s\n"
                           "Name it in a real parent slot — a \"parent\" field in the params body, or "
                           "--parent %s. Note that a REPEATED \"parent\" key resolves to the LAST "
                           "one, which is both the value this guard reads and the value the API "
                           "receives." % (parent_id, parent_id))

    return Verdict(True)


def _selftest():
    """The cases three adversarial passes produced, plus the shipped command that must never break.
    A guard whose failure path has never been seen is not a guard."""
    G, P = "GOALSLIST", "DAILYPARENT"
    shipped = ('gws tasks tasks insert --params \'{"tasklist":"$(python3 cal_config.py --get '
               'goals_tasklist)","parent":"$(python3 cal_config.py --get daily_parent_task)"}\'')
    cases = [
        # (should_allow, label, command)
        (True,  "shipped day's-plan write", shipped),
        (True,  "shipped write, title with an ampersand",
         shipped[:-1] + '\' --json \'{"title":"Q3 R&D review"}\''),
        (True,  "title with a hash", shipped[:-1] + '\' --json \'{"title":"Call bank #urgent"}\''),
        (True,  "title with semicolons", shipped[:-1] + '\' --json \'{"title":"milk; eggs; bread"}\''),
        (True,  "read of the goals list", 'gws tasks tasks list --tasklist %s' % G),
        (True,  "write to another list", 'gws tasks tasks insert --tasklist OTHER --params \'{}\''),
        (True,  "not a tasks command", 'git status'),
        (False, "literal delete on goals", 'gws tasks tasks delete --tasklist %s --id g1' % G),
        (False, "whole-list delete", 'gws tasks tasklists delete --tasklist %s' % G),
        (False, "clear on goals", 'gws tasks tasks clear --tasklist %s' % G),
        (False, "@default delete", 'gws tasks tasks delete --id X --params \'{"tasklist":"@default"}\''),
        (False, "@default clear", 'gws tasks tasks clear --params \'{"tasklist":"@default"}\''),
        (False, "no target at all", 'gws tasks tasks delete --id X'),
        (False, "duplicate parent key, last wins",
         'gws tasks tasks insert --params \'{"tasklist":"%s"}\' --json \'{"parent":"%s","parent":"AGOAL"}\'' % (G, P)),
        (False, "decoy then chained delete",
         'echo decoy tasks tasks insert "parent":"%s" ; gws tasks tasks delete --tasklist %s --id g1' % (P, G)),
        (False, "newline-separated delete",
         'gws tasks tasks list --tasklist %s\ngws tasks tasklists delete --tasklist %s' % (G, G)),
        (False, "parent smuggled into notes",
         'gws tasks tasks update --tasklist %s --id g1 --json \'{"notes":"parent:%s"}\'' % (G, P)),
        (False, "verb via xargs placeholder",
         'xargs -I{} gws tasks tasks {} --params \'{"tasklist":"%s"}\'' % G),
        (False, "binary behind a variable is unreadable",
         'gws tasks tasks delete --tasklist $LIST --id g1'),
        (False, "opaque substitution target",
         'gws tasks tasks delete --params \'{"tasklist":"$(cat /tmp/x)"}\''),

        # -- REGRESSION, 2026-08-23: the CONFIRMED LIVE bypass shared with gws_guard.py -- an
        # argv built by ANOTHER INTERPRETER (comma/quote-delimited, invisible to shlex because
        # the whole thing sits inside one outer quoted -c argument). Returned ALLOW before the
        # fix; see _argv_list_statements()'s own docstring.
        (False, "python argv-list delete on goals",
         ('python3 -c "import subprocess; subprocess.run([\'gws\',\'tasks\',\'tasks\','
          '\'delete\',\'--params\',\'{\\"tasklist\\":\\"%s\\",\\"id\\":\\"g1\\"}\'])"') % G),
        # The same shape but a SAFE verb -- proof this is not "block every argv list".
        (True, "python argv-list list (read) on goals",
         ('python3 -c "import subprocess; subprocess.run([\'gws\',\'tasks\',\'tasks\','
          '\'list\',\'--params\',\'{\\"tasklist\\":\\"%s\\"}\'])"') % G),
        # The same shape targeting a DIFFERENT list must still pass -- any other list is the
        # caller's to write.
        (True, "python argv-list delete on another list",
         ('python3 -c "import subprocess; subprocess.run([\'gws\',\'tasks\',\'tasks\','
          '\'delete\',\'--params\',\'{\\"tasklist\\":\\"OTHERLIST\\",\\"id\\":\\"g1\\"}\'])"')),
    ]
    failed = 0
    for expect_allow, label, cmd in cases:
        v = judge(cmd, G, P)
        if v.allow != expect_allow:
            failed += 1
            print("  [FAIL] %-42s expected %s" % (label, "ALLOW" if expect_allow else "DENY"))
        else:
            print("  [ok]   %-42s %s" % (label, "ALLOW" if v.allow else "DENY"))
    print("\n%d checks, %d failed" % (len(cases), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    cmd = sys.stdin.read()
    goals = os.environ.get("TASKS_GUARD_GOALS", "")
    parent = os.environ.get("TASKS_GUARD_PARENT", "")
    v = judge(cmd, goals, parent)
    if v.allow:
        sys.exit(0)
    sys.stderr.write("BLOCKED (tasks guard): %s\n" % v.reason)
    sys.stderr.write(
        "WHY: the list on file as goals_tasklist holds what you decided your life is for, and it is "
        "yours to edit, not your agent's. Google Tasks keeps no version history, so a deleted or "
        "overwritten task is gone for good.\n")
    sys.stderr.write("%s\n" % v.redirect)
    sys.stderr.write(
        "RULE: which list is protected is your setting, at <notes>/config/cal.md (INSTALL.md -> the "
        "Google sit-down). Change it there. Do not loosen this guard to fit a command.\n")
    sys.exit(2)
