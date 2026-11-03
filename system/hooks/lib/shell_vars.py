#!/usr/bin/env python3
"""shell_vars.py -- write a variable's value into a Bash command, when the same command set it, so a guard judges the real target.

WHY: fine china read literal targets only. Live sample, 2026-11-03: `f=~/.config/lifehack/placement.conf; printf ... >> "$f"` switched a check off with
     no sign and no ask. A blind model writes that idiom in ordinary work (exam D-B07 was the same lesson for the placement rules).
WHAT: substitute(cmd) -> cmd with each `$NAME` / `${NAME}` replaced, left to right, when an earlier statement of this command assigned NAME a value we can read:
     NAME=value, export NAME=value, or `for NAME in <one word>`. A value built from another known variable or $HOME is read through it.
     Single-quoted text and escaped dollars are left alone, as the shell leaves them. Heredoc bodies are left alone.
ALSO: a shell keyword at the start of a statement (then, do, else, if ...) is dropped, so the command after it is read as a command (street-sign record, the same defect in the stand-in hook).
AN UNREADABLE VARIABLE STAYS AS IT WAS: not set here, $(...), a backtick, ${NAME:-x}, or a loop over several words. The caller then behaves as it did before.
LIMIT: text only, nothing runs. A prefix assignment (`f=x cmd "$f"`) is not read, because the shell does not expand it there either.
     A value set in only one branch of an if is treated as set. The result only ever feeds a sign or an ask, never a new hard block.
SWITCH: fc_var_targets in system/hooks/roundB.conf (the callers check it). TESTS: tests/test_fc_signs.py VarTargets.
"""
import os
import re
import shlex

_ASSIGN = re.compile(r"(?:(?:export|local|declare|readonly)\s+)?([A-Za-z_]\w*)=")
_FOR = re.compile(r"for\s+([A-Za-z_]\w*)\s+in\s+([^;\n]*?)\s*(?:;|\n)")
_REF = re.compile(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)")
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
_KEYWORD = re.compile(r"(?:then|do|else|elif|if|while|until|!)(?=\s)")


def _home():
    return os.path.expanduser("~")


def _read_value(cmd, i, known):
    """Parse an assignment's value from cmd[i:]. -> (value or None when unreadable, next index)."""
    out, quote, ok = [], None, True
    n = len(cmd)
    while i < n:
        c = cmd[i]
        if quote == "'":
            if c == "'":
                quote = None
            else:
                out.append(c)
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(cmd[i + 1])
            i += 2
            continue
        if c == "`":
            ok = False
        if c == "$":
            m = _REF.match(cmd, i)
            if m:
                name = m.group(1) or m.group(2)
                if name in known:
                    out.append(known[name])
                elif name == "HOME":
                    out.append(_home())
                else:
                    ok = False
                i = m.end()
                continue
            ok = False
        if quote == '"':
            if c == '"':
                quote = None
            else:
                out.append(c)
            i += 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            continue
        if c in " \t\n;&|()":
            break
        out.append(c)
        i += 1
    val = "".join(out)
    return (val if ok and "\n" not in val else None), i


def substitute(cmd):
    """-> cmd with same-command variables written in. Never raises; any surprise returns cmd unchanged."""
    try:
        return _substitute(cmd)
    except Exception:
        return cmd


def _substitute(cmd):
    if len(cmd) > 200000 or ("$" not in cmd and not re.search(r"(?:^|[;&|\n(])\s*(?:then|do|else|elif|if|while|until|!)\s", cmd)):
        return cmd
    known, out, quote, start, pending = {}, [], None, True, []
    i, n = 0, len(cmd)
    while i < n:
        c = cmd[i]
        if quote == "'":
            out.append(c)
            if c == "'":
                quote = None
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(cmd[i:i + 2])
            i += 2
            start = False
            continue
        if quote is None:
            if c == "\n" and pending:      # a heredoc body is data: copied as it stands
                out.append(c)
                i += 1
                for delim in pending:
                    while i <= n:
                        j = cmd.find("\n", i)
                        line = cmd[i:] if j < 0 else cmd[i:j]
                        out.append(line + ("\n" if j >= 0 else ""))
                        i = n + 1 if j < 0 else j + 1
                        if line.strip() == delim:
                            break
                pending = []
                start = True
                continue
            if c in " \t":
                out.append(c)
                i += 1
                continue
            if start:
                k = _KEYWORD.match(cmd, i)
                if k:
                    i = k.end()
                    continue
                f = _FOR.match(cmd, i)
                if f:
                    words = f.group(2).split()
                    if len(words) == 1 and not re.search(r"[*?\[$`]", words[0]):
                        known[f.group(1)] = words[0].strip("\"'")
                    else:
                        known.pop(f.group(1), None)
                    out.append(f.group(0))
                    i = f.end()
                    continue
                a = _ASSIGN.match(cmd, i)
                if a:
                    val, e = _read_value(cmd, a.end(), known)
                    rest = cmd[e:]
                    alone = not rest.strip(" \t") or rest.lstrip(" \t")[0] in ";&|\n)"
                    if alone:
                        if val is None:
                            known.pop(a.group(1), None)
                        else:
                            known[a.group(1)] = val
                        out.append(cmd[i:e])
                        i = e
                        continue
            h = _HEREDOC.match(cmd, i)
            if h:
                pending.append(h.group(2))
                out.append(h.group(0))
                i = h.end()
                start = False
                continue
            if c in "'\"":
                quote = c
                out.append(c)
                i += 1
                start = False
                continue
            if c in ";&|\n(){":
                out.append(c)
                i += 1
                start = True
                continue
        elif c == '"':
            quote = None
            out.append(c)
            i += 1
            continue
        if c == "$":
            m = _REF.match(cmd, i)
            if m and (m.group(1) or m.group(2)) in known:
                v = known[m.group(1) or m.group(2)]
                out.append(v if quote == '"' else (v if re.fullmatch(r"[\w@%+=:,./~-]+", v) else shlex.quote(v)))
                i = m.end()
                start = False
                continue
        out.append(c)
        i += 1
        start = False
    return "".join(out)
