#!/usr/bin/env python3
"""cmdreader.py - the shared command reader (v2 Round B, piece 4).

One place that reads a Bash command string the way a guard needs it read: split into
segments (across && || ; | & and newlines), with quoted text and heredoc bodies kept as DATA
(never a command word, never a write target), same-command variables and cd-chains resolved,
write targets listed, git invocations listed. Standard library only (shlex, re, json).

DESIGN RULE: only five things can be an ACTION - a command word at segment start, a redirect
target, an argument of a known writer program (cp, mv, tee, ln, ...), the body of a nested shell /
interpreter (bash -c, eval, python -c, a heredoc fed to a shell), and a $(...) / backtick body.
Everything else is DATA and is not searched for actions. A guard that wants to scan DATA anyway
(a secret / leak scan) calls all_text().

API (Python):
    from cmdreader import read, writes, programs, names_program, git_calls, is_git, resolve_git, all_text
    r = read(cmd, cwd=None, trust_resolvers=False)   # never raises; r.ok False = "could not parse"
    r.ok, r.parse_error, r.segments, r.flags
    writes(r)               -> [Write(path, abs, via, srcs, content, flags, segment)]  (nested + $(...) included)
    programs(r)             -> [basename, ...] of every program that can run
    names_program(r, "x.sh")-> True only if x.sh is a command word (or `bash x.sh`, `source x.sh`)
    git_calls(r)            -> [GitCall(sub, argv, c_dir, cwd_typed, tainted, segment)]
    is_git(r, "add")        -> any git call with that subcommand
    resolve_git(cmd, verb)  -> (status, target) with the same contract as git_target_resolver.resolve
    all_text(r)             -> raw command + heredoc bodies (for leak scans)
CLI:   printf '%s' "$CMD" | python3 cmdreader.py [--cwd DIR]   -> JSON on stdout, exit 0 always.

NOT DONE ON PURPOSE: $(...) is never executed (one narrow exception: with trust_resolvers=True the
one-line `python3 <dir>/brain_root.py --quiet` / `personal_code_root.py` resolvers run once, 2 s
timeout, cached). Deliberate evasion (obfuscation, a script file written now and run later) is
labelled in flags, not defeated: this is a speed bump for an obedient session, not a boundary.
"""
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field

READER_VERSION = "1"
MAX_LEN = 200_000
MAX_DEPTH = 4

_Q = "\x02"   # marks "this word contained quoting/escaping" (set by the pre-pass)
_PH = "\x01"  # placeholder fence for extracted substitutions / heredocs

_OPS = ["&>>", "<<<", "<<-", "&&", "||", ";;", "|&", ">>", "<<", ">&", "<&", "&>", ">|", "<>",
        ";", "|", "&", "(", ")", ">", "<"]
_JOINERS = {";", "&&", "||", "|", "&", "|&", ";;"}
_REDIR = {">", ">>", ">|", "&>", "&>>", "<>"}
_PREFIX_WORDS = {"do", "then", "else", "elif", "if", "while", "until", "{", "!", "time", "command",
                 "builtin", "exec", "nohup", "sudo", "env"}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
_PYS = {"python", "python3", "python2"}
_ENV_ALLOW = ("HOME", "USER", "PWD", "CLAUDE_PROJECT_DIR", "TMPDIR")
_COPY = {"cp", "mv", "install", "ginstall", "rsync", "ln"}
_TOUCH = {"touch", "mkdir", "truncate", "rm", "rmdir", "chmod", "chown", "unlink"}
_EXIT_SHAPES = {"exit", "return"}
_RESOLVER_RE = re.compile(r"^python3?\s+(\S*/)?(brain_root|personal_code_root)\.py(\s+--quiet)?$")
_resolver_cache = {}


@dataclass
class Word:
    text: str
    quoted: bool = False


@dataclass
class Write:
    path: str
    abs: str
    via: str
    srcs: list = field(default_factory=list)
    content: object = None
    flags: str = ""
    segment: int = 0


@dataclass
class GitCall:
    sub: str
    argv: list
    c_dir: str
    cwd_typed: str
    tainted: bool
    segment: object = None


@dataclass
class Segment:
    id: int
    joiner_before: object = None
    program_raw: object = None
    program: object = None
    program_unresolved: bool = False
    args: list = field(default_factory=list)       # unquoted arg strings
    words: list = field(default_factory=list)      # [Word] command word + args
    assignments: list = field(default_factory=list)
    redirects: list = field(default_factory=list)  # {"op","fd","target"}
    heredocs: list = field(default_factory=list)   # {"delim","quoted","body","role":"DATA"}
    here_strings: list = field(default_factory=list)
    substitutions: list = field(default_factory=list)  # [Result-like sub readers]
    nested: list = field(default_factory=list)     # [{"via","language","inner","segments"}]
    group_open: int = 0
    group_close: int = 0
    cwd_typed: str = ""     # last cd target as typed ("" = none)
    cwd: object = None      # absolute effective dir, None = unknown
    tainted: bool = False   # a cd we cannot model came before this segment
    in_pipe: bool = False
    stripped: list = field(default_factory=list)   # prefix words dropped (do, then, sudo ...)
    _assign_raw: list = field(default_factory=list, repr=False)
    _sub_ids: list = field(default_factory=list, repr=False)
    _skip_git: bool = False
    _vars: dict = field(default_factory=dict, repr=False)


@dataclass
class Result:
    ok: bool
    parse_error: object
    segments: list
    raw: str = ""
    stripped_text: str = ""
    unresolved: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)

    def to_dict(self):
        def seg(s):
            return {"id": s.id, "joiner_before": s.joiner_before, "program": s.program,
                    "program_raw": s.program_raw, "program_unresolved": s.program_unresolved,
                    "args": s.args, "assignments": s.assignments, "redirects": s.redirects,
                    "heredocs": s.heredocs, "here_strings": s.here_strings,
                    "cwd": s.cwd, "cwd_typed": s.cwd_typed, "tainted": s.tainted,
                    "substitutions": [{"segments": [seg(x) for x in sub.segments]} for sub in s.substitutions],
                    "nested": [{"via": n["via"], "language": n["language"], "inner": n["inner"],
                                "segments": [seg(x) for x in n.get("segments", [])]} for n in s.nested]}
        return {"ok": self.ok, "parse_error": self.parse_error,
                "segments": [seg(s) for s in self.segments],
                "writes": [w.__dict__ for w in writes(self)],
                "unresolved": self.unresolved, "flags": self.flags}


# ----------------------------------------------------------------------------- pre-pass
class _ParseError(Exception):
    pass


def _match_paren(s, i):
    """s[i] is just after an opening '('. Return index of the matching ')' (quote aware)."""
    depth, n, q = 1, len(s), None
    while i < n:
        c = s[i]
        if q:
            if c == "\\" and q == '"':
                i += 1
            elif c == q:
                q = None
        elif c == "\\":
            i += 1
        elif c in "'\"":
            q = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise _ParseError("unbalanced parenthesis in substitution")


def _prepare(cmd):
    """Walk the command once. Returns (text for shlex, heredocs, subs).
    - heredoc bodies are cut out (stored as DATA) and `<<DELIM` becomes `<< <PH>H<n><PH>`;
    - $(..), `..`, <(..), >(..), $((..)) become <PH>S<n><PH> placeholders with the inner text stored;
    - unquoted newlines become ';'; comments are dropped; quoted/escaped words get the _Q marker."""
    out, heredocs, subs, pending = [], [], [], []
    i, n = 0, len(cmd)
    q = None
    word_start = True
    while i < n:
        c = cmd[i]
        if q == "'":
            out.append(c)
            if c == "'":
                q = None
            i += 1
            continue
        if c == "\\":
            if i + 1 < n and cmd[i + 1] == "\n":
                i += 2
                continue
            if q is None:
                out.append(_Q)
            out.append(cmd[i:i + 2])
            i += 2
            word_start = False
            continue
        if c == "$" and i + 1 < n and cmd[i + 1] == "(":
            if cmd.startswith("$((", i):
                j = _match_paren(cmd, i + 2)
                subs.append(("arith", cmd[i:j + 1]))
                out.append("%sS%d%s" % (_PH, len(subs) - 1, _PH))
                i = j + 1
            else:
                j = _match_paren(cmd, i + 2)
                subs.append(("$(", cmd[i + 2:j]))
                out.append("%sS%d%s" % (_PH, len(subs) - 1, _PH))
                i = j + 1
            word_start = False
            continue
        if c == "`":
            j = i + 1
            while j < n and cmd[j] != "`":
                j += 2 if cmd[j] == "\\" else 1
            if j >= n:
                raise _ParseError("unbalanced backtick")
            subs.append(("`", cmd[i + 1:j]))
            out.append("%sS%d%s" % (_PH, len(subs) - 1, _PH))
            i = j + 1
            word_start = False
            continue
        if q == '"':
            out.append(c)
            if c == '"':
                q = None
            i += 1
            continue
        # ---- unquoted
        if c in "'\"":
            out.append(_Q)
            out.append(c)
            q = c
            i += 1
            word_start = False
            continue
        if c in "<>" and i + 1 < n and cmd[i + 1] == "(":
            j = _match_paren(cmd, i + 2)
            subs.append((c + "(", cmd[i + 2:j]))
            out.append("%sS%d%s" % (_PH, len(subs) - 1, _PH))
            i = j + 1
            word_start = False
            continue
        if c == "#" and word_start:
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        if c == "\n":
            out.append(" ; ")
            i += 1
            for hd in pending:
                tag, strip = hd["delim"], hd["strip_tabs"]
                body = []
                while True:
                    if i >= n:
                        raise _ParseError("heredoc not closed (%s)" % tag)
                    j = cmd.find("\n", i)
                    line = cmd[i:] if j < 0 else cmd[i:j]
                    i = n if j < 0 else j + 1
                    if (line.lstrip("\t") if strip else line) == tag:
                        break
                    body.append(line.lstrip("\t") if strip else line)
                hd["body"] = "\n".join(body)
            pending = []
            word_start = True
            continue
        if c == "<" and cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            m = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|\\?([^\s;&|<>()]+))").match(cmd, i)
            if m:
                tag = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))
                quoted = m.group(4) is None or "\\" in cmd[i + 2:m.end()]
                hd = {"delim": tag, "quoted": bool(quoted), "strip_tabs": m.group(1) == "-", "body": "", "role": "DATA"}
                heredocs.append(hd)
                pending.append(hd)
                out.append(" << %sH%d%s " % (_PH, len(heredocs) - 1, _PH))
                i = m.end()
                word_start = False
                continue
        if c in " \t;&|()":
            word_start = True
        else:
            word_start = False
        out.append(c)
        i += 1
    if q:
        raise _ParseError("unbalanced quote")
    if pending:
        raise _ParseError("heredoc not closed (%s)" % pending[0]["delim"])
    return "".join(out), heredocs, subs


def _tokens(text):
    lex = shlex.shlex(text, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        raw = list(lex)
    except ValueError as e:
        raise _ParseError(str(e))
    toks = []
    for t in raw:
        if t and all(ch in "();<>|&" for ch in t):
            while t:
                for op in _OPS:
                    if t.startswith(op):
                        toks.append((op, True))
                        t = t[len(op):]
                        break
                else:
                    toks.append((t[0], True))
                    t = t[1:]
        else:
            toks.append((t, False))
    return toks


# ----------------------------------------------------------------------------- reader
class _Reader:
    def __init__(self, cwd, trust, depth, vars_):
        self.cwd0 = cwd
        self.trust = trust
        self.depth = depth
        self.vars = dict(vars_)
        self.unresolved = []
        self.flags = {"has_nested_shell": False, "has_python_c": False, "has_substitution": False,
                      "has_heredoc": False, "has_loop_or_if": False}
        self.seg_counter = [0]

    # -- variable expansion
    def expand(self, text, quoted_raw_single, subs, seg_id):
        if quoted_raw_single:
            return text

        def rep(m):
            name = m.group(1) or m.group(2)
            if name in self.vars:
                v = self.vars[name]
                if v is not None:
                    return v
            elif name in _ENV_ALLOW and os.environ.get(name):
                return os.environ[name]
            elif not name.isdigit():
                pass
            else:
                return m.group(0)
            self.unresolved.append({"var": name, "segment": seg_id, "where": "word"})
            return m.group(0)
        return re.sub(r"\$\{(\w+)\}|\$([A-Za-z_]\w*)", rep, text)

    def segments_from(self, text, heredocs, subs, state, depth_label=""):
        toks = _tokens(text)
        segs = []
        cur = []        # raw tokens (text, is_op)
        joiner = None

        groups = []

        def flush(next_joiner):
            nonlocal cur, joiner
            if cur:
                groups.append((joiner, cur))
            cur = []
            joiner = next_joiner
        for t, is_op in toks:
            if is_op and t in _JOINERS:
                if t == "&" and cur and cur[-1] == (">", True):
                    cur.append((t, True))
                    continue
                flush(t)
            else:
                cur.append((t, is_op))
        flush(None)
        # phase A: build in order, so a later segment sees earlier same-command assignments
        for k, (jn, gt) in enumerate(groups):
            seg = self._build(gt, jn, heredocs, subs, state)
            nxt = groups[k + 1][0] if k + 1 < len(groups) else None
            seg.in_pipe = jn in ("|", "|&") or nxt in ("|", "|&")
            self._assign(seg, state)
            seg._vars = dict(self.vars)
            segs.append(seg)
        # phase B: cd chain; phase C: substitutions and nested code (need the cwd)
        self._cd_pass(segs, state)
        for s in segs:
            self._code(s, state)
        return segs

    def _build(self, rawtoks, joiner, heredocs, subs, state):
        sid = self.seg_counter[0]
        self.seg_counter[0] += 1
        seg = Segment(id=sid, joiner_before=joiner)
        # strip leading "(" / trailing ")" group marks
        while rawtoks and rawtoks[0] == ("(", True):
            seg.group_open += 1
            rawtoks = rawtoks[1:]
        while rawtoks and rawtoks[-1] == (")", True):
            seg.group_close += 1
            rawtoks = rawtoks[:-1]
        words = []
        i, n = 0, len(rawtoks)
        while i < n:
            t, is_op = rawtoks[i]
            if is_op and t in (")", "("):
                i += 1
                continue
            if is_op and (t in _REDIR or t in ("<", "<<", "<<<", ">&", "<&", "<<-")):
                # fd number glued before the operator
                fd = None
                if words and re.fullmatch(r"[0-9]", words[-1].text) and not words[-1].quoted:
                    fd = int(words.pop().text)
                tgt = rawtoks[i + 1][0] if i + 1 < n else ""
                tq = False
                if t in ("<<", "<<-"):
                    m = re.fullmatch(_PH + r"H(\d+)" + _PH, tgt)
                    if m:
                        hd = heredocs[int(m.group(1))]
                        seg.heredocs.append({"delim": hd["delim"], "quoted": hd["quoted"], "body": hd["body"], "role": "DATA"})
                        self.flags["has_heredoc"] = True
                    i += 2
                    continue
                tgt_text, tq = self._unq(tgt, subs, sid, state)
                if t == "<<<":
                    seg.here_strings.append({"text": tgt_text, "role": "DATA"})
                elif t in (">&", "<&"):
                    if re.fullmatch(r"\d+|-", tgt_text):
                        pass  # fd duplication: not a file
                    elif t == ">&":
                        seg.redirects.append({"op": ">", "fd": fd if fd is not None else 1, "target": tgt_text})
                elif t == "<":
                    seg.redirects.append({"op": "<", "fd": fd if fd is not None else 0, "target": tgt_text})
                else:
                    seg.redirects.append({"op": t, "fd": fd if fd is not None else 1, "target": tgt_text})
                i += 2
                continue
            txt, q = self._unq(t, subs, sid, state)
            words.append(Word(txt, q))
            i += 1
        # prefix words and assignments
        k = 0
        assigns = []
        while k < len(words):
            w = words[k]
            if not w.quoted and w.text in _PREFIX_WORDS:
                seg.stripped.append(w.text)
                if w.text in ("while", "until", "if", "elif"):
                    self.flags["has_loop_or_if"] = True
                k += 1
                continue
            m = re.match(r"^([A-Za-z_]\w*)=(.*)$", w.text, re.S)
            if m and not w.quoted or (m and w.quoted and re.match(r"^[A-Za-z_]\w*=", w.text)):
                assigns.append((m.group(1), m.group(2), w.quoted))
                k += 1
                continue
            break
        words = words[k:]
        for w in words:
            w.text = _restore(w.text, subs)
        for rd in seg.redirects:
            rd["target"] = _restore(rd["target"], subs)
        seg.words = words
        seg.assignments = [{"name": a, "value": v, "kind": "substitution" if _PH in v else "literal"} for a, v, _ in assigns]
        for a in seg.assignments:
            a["value"] = re.sub(_PH + r"S(\d+)" + _PH, lambda m: _sub_text(subs, int(m.group(1))), a["value"])
        seg._assign_raw = assigns
        if words:
            pr = words[0].text
            seg.program_raw = pr
            seg.program = os.path.basename(pr) if pr else pr
            seg.program_unresolved = pr.startswith("$") or pr.startswith("`")
            seg.args = [w.text for w in words[1:]]
        # substitutions mentioned in this segment
        used = set()
        for t, _ in rawtoks:
            for m in re.finditer(_PH + r"S(\d+)" + _PH, t):
                used.add(int(m.group(1)))
        seg._sub_ids = sorted(used)
        return seg

    def _unq(self, tok, subs, sid, state):
        """token -> (text with variables expanded, quoted?)"""
        quoted = _Q in tok
        # single-quoted-only words are never expanded
        single_only = quoted and "'" in tok.replace(_Q, "") and '"' not in tok and "\\" not in tok
        text = tok.replace(_Q, "")
        # posix shlex already removed the quote characters; _Q only survives as a marker
        if text.startswith("~") and not quoted:
            text = os.path.expanduser("~") + text[1:]
        text = self.expand(text, single_only, subs, sid)
        return text, quoted

    # -- cd chain
    def _cd_pass(self, segs, state):
        cwd_typed, tainted = state["cwd_typed"], state["tainted"]
        cwd = state["cwd"]
        k = 0
        n = len(segs)
        while k < n:
            s = segs[k]
            s.cwd_typed, s.tainted, s.cwd = cwd_typed, tainted, cwd
            prog = s.program
            if prog in ("pushd", "popd"):
                cwd_typed, tainted, cwd = "", True, None
            elif prog == "cd":
                if s.group_open or s.in_pipe:
                    cwd_typed, tainted, cwd = "", True, None
                else:
                    tgt = ""
                    for a in s.args:
                        if not a.startswith("-"):
                            tgt = a
                            break
                    if not tgt or tgt == "-":
                        cwd_typed, tainted, cwd = "", True, None
                    else:
                        nxt = segs[k + 1] if k + 1 < n else None
                        newcwd = _join(cwd if cwd is not None else self.cwd0, tgt)
                        if nxt is not None and nxt.joiner_before == "||":
                            if nxt.program in _EXIT_SHAPES:
                                cwd_typed, tainted, cwd = tgt, False, newcwd
                            else:
                                cwd_typed, tainted, cwd = "", True, None
                            nxt.cwd_typed, nxt.tainted, nxt.cwd = cwd_typed, tainted, cwd
                            nxt._skip_git = True
                            k += 2
                            continue
                        cwd_typed, tainted, cwd = tgt, False, newcwd
            elif s.group_open and any(w.text == "cd" for w in s.words):
                cwd_typed, tainted, cwd = "", True, None
            k += 1
        state["end"] = (cwd_typed, tainted, cwd)

    # -- per segment: variables, substitutions, nested code
    def _assign(self, s, state):
        subs = state["subs"]
        if s.program in ("for", "select") and len(s.args) >= 1:
            self.vars[s.args[0]] = None
            self.flags["has_loop_or_if"] = True
        if s.program in ("case", "function") or "if" in s.stripped:
            self.flags["has_loop_or_if"] = True
        in_compound = self.flags["has_loop_or_if"]
        # assignments
        persist = not s.program and not s.in_pipe
        for name, val, _q in s._assign_raw:
            m = re.fullmatch(_PH + r"S(\d+)" + _PH, val)
            newv = None
            if _PH in val:
                if m and self.trust and subs[int(m.group(1))][0] in ("$(", "`"):
                    newv = self._trusted(subs[int(m.group(1))][1])
            else:
                newv = val
            if in_compound:
                newv = None
            if persist or s.program is None:
                self.vars[name] = newv
        # export NAME=value
        if s.program == "export":
            for a in s.args:
                m = re.match(r"^([A-Za-z_]\w*)=(.*)$", a)
                if m:
                    self.vars[m.group(1)] = None if (_PH in m.group(2) or in_compound) else m.group(2)

    def _code(self, s, state):
        subs = state["subs"]
        saved = self.vars
        self.vars = s._vars
        # substitutions -> recursive segments (they run before the command)
        for sid in s._sub_ids:
            kind, inner = subs[sid]
            if kind == "arith":
                continue
            self.flags["has_substitution"] = True
            s.substitutions.append(self._sub_reader(inner, s, kind))
        self._nested(s, state)
        self.vars = saved

    def _trusted(self, inner):
        inner = inner.strip()
        if not _RESOLVER_RE.match(inner):
            return None
        parts = inner.split()
        script = parts[1]
        if script in _resolver_cache:
            return _resolver_cache[script]
        val = None
        try:
            if os.path.isfile(script):
                p = subprocess.run([sys.executable, script, "--quiet"], capture_output=True, text=True, timeout=2)
                out = p.stdout.strip()
                val = out if p.returncode == 0 and out else None
        except Exception:
            val = None
        _resolver_cache[script] = val
        return val

    def _sub_reader(self, inner, parent, kind):
        res = _read_inner(inner, self.depth + 1, self.trust, self.vars, parent.cwd if parent.cwd is not None else self.cwd0,
                          parent.cwd_typed, parent.tainted)
        self.unresolved.extend(res.unresolved)
        for k, v in res.flags.items():
            self.flags[k] = self.flags[k] or v
        return res

    def _nested(self, s, state):
        prog = s.program
        if not prog:
            return
        if prog in _SHELLS:
            code = None
            for k, a in enumerate(s.args):
                if a.startswith("-") and not a.startswith("--") and "c" in a[1:] and k + 1 < len(s.args):
                    code = s.args[k + 1]
                    break
            if code is not None:
                self._add_nested(s, "bash -c", code, "shell")
            elif s.heredocs and not [a for a in s.args if not a.startswith("-")]:
                for hd in s.heredocs:
                    self._add_nested(s, prog + " <<heredoc", hd["body"], "shell")
            elif s.here_strings and not [a for a in s.args if not a.startswith("-")]:
                self._add_nested(s, prog + " <<<", s.here_strings[0]["text"], "shell")
            elif s.joiner_before in ("|", "|&") and not [a for a in s.args if not a.startswith("-")]:
                s.nested.append({"via": "| " + prog, "language": "shell", "inner": None, "segments": []})
                self.flags["has_nested_shell"] = True
        elif prog == "eval" and s.args:
            self._add_nested(s, "eval", " ".join(s.args), "shell")
        elif re.fullmatch(r"python[0-9.]*", prog or ""):
            code = None
            for k, a in enumerate(s.args):
                if a == "-c" and k + 1 < len(s.args):
                    code = s.args[k + 1]
                    break
            if code is not None:
                self.flags["has_python_c"] = True
                s.nested.append({"via": "python -c", "language": "python", "inner": code, "segments": []})
            elif s.heredocs and ("-" in s.args or not [a for a in s.args if not a.startswith("-")]):
                self.flags["has_python_c"] = True
                for hd in s.heredocs:
                    s.nested.append({"via": "python <<heredoc", "language": "python", "inner": hd["body"], "segments": []})
        elif prog in ("source", ".") and False:
            pass

    def _add_nested(self, s, via, code, lang):
        self.flags["has_nested_shell"] = True
        res = _read_inner(code, self.depth + 1, self.trust, self.vars, s.cwd if s.cwd is not None else self.cwd0,
                          s.cwd_typed, s.tainted)
        self.unresolved.extend(res.unresolved)
        for k, v in res.flags.items():
            self.flags[k] = self.flags[k] or v
        s.nested.append({"via": via, "language": lang, "inner": code, "segments": res.segments,
                         "ok": res.ok, "parse_error": res.parse_error})
        if not res.ok:
            s.nested[-1]["unparsed"] = True


def _restore(text, subs):
    return re.sub(_PH + r"S(\d+)" + _PH, lambda m: _sub_text(subs, int(m.group(1))), text)


def _sub_text(subs, idx):
    kind, inner = subs[idx]
    if kind == "arith":
        return inner
    if kind == "`":
        return "`" + inner + "`"
    return kind + inner + ")"


def _join(base, tgt):
    tgt = os.path.expanduser(tgt)
    if os.path.isabs(tgt):
        return os.path.normpath(tgt)
    if base is None:
        return None
    return os.path.normpath(os.path.join(base, tgt))


def _read_inner(cmd, depth, trust, vars_, cwd, cwd_typed, tainted):
    if depth > MAX_DEPTH:
        return Result(False, "nesting too deep", [], cmd)
    try:
        text, heredocs, subs = _prepare(cmd)
        rd = _Reader(cwd, trust, depth, vars_)
        state = {"cwd_typed": cwd_typed, "tainted": tainted, "cwd": cwd, "subs": subs}
        segs = rd.segments_from(text, heredocs, subs, state)
        return Result(True, None, segs, cmd, text, rd.unresolved, rd.flags)
    except _ParseError as e:
        return Result(False, str(e), [], cmd)
    except Exception as e:  # never raise out of the reader
        return Result(False, "internal: %s" % e, [], cmd)


def read(cmd, cwd=None, trust_resolvers=False):
    """Parse one Bash command string. Never raises; r.ok is False when it could not be read safely."""
    if not isinstance(cmd, str):
        return Result(False, "not a string", [], "")
    if len(cmd) > MAX_LEN:
        return Result(False, "too long", [], cmd)
    base = os.path.abspath(cwd) if cwd else None
    return _read_inner(cmd, 0, trust_resolvers, {}, base, "", False)


# ----------------------------------------------------------------------------- walkers
def _all_segments(segs):
    """Execution-ish order: a segment's $(..) bodies, the segment, then its nested code."""
    for s in segs:
        for sub in s.substitutions:
            yield from _all_segments(sub.segments)
        yield s
        for nst in s.nested:
            yield from _all_segments(nst.get("segments", []))


def iter_segments(r):
    return list(_all_segments(r.segments))


def programs(r):
    return [s.program for s in iter_segments(r) if s.program]


def names_program(r, name, as_command=True):
    """True only when `name` is a command word, or the script run by bash/sh/source/. ./name.
    A file name used as an ARGUMENT (sed -n 1,60p name) or inside data never counts."""
    base = os.path.basename(name)
    for s in iter_segments(r):
        if not s.program_raw:
            continue
        if os.path.basename(s.program_raw) == base:
            return True
        if s.program in _SHELLS or s.program in ("source", "."):
            rest = [a for a in s.args if not a.startswith("-")]
            if rest and os.path.basename(rest[0]) == base:
                return True
    return False


def all_text(r):
    """Raw command plus heredoc bodies - for leak / secret scans that must see DATA too."""
    parts = [r.raw]
    for s in iter_segments(r):
        parts.extend(h["body"] for h in s.heredocs)
        parts.extend(h["text"] for h in s.here_strings)
    return "\n".join(parts)


def _git_split(s):
    """-> (c_dir, sub, argv_after_sub) for a git segment or None."""
    if not s.program or s.program != "git" or s._skip_git:
        return None
    a = s.args
    j, cdir = 0, ""
    while j < len(a) and a[j].startswith("-"):
        if a[j] in ("-C", "-c"):
            if a[j] == "-C" and j + 1 < len(a):
                cdir = a[j + 1]
            j += 2
        else:
            j += 1
    if j >= len(a):
        return cdir, "", []
    return cdir, a[j], a[j + 1:]


def git_calls(r):
    out = []
    for s in iter_segments(r):
        g = _git_split(s)
        if g:
            out.append(GitCall(g[1], g[2], g[0], s.cwd_typed, s.tainted, s))
    return out


def is_git(r, sub=None):
    return any(c.sub and (sub is None or c.sub == sub) for c in git_calls(r))


def resolve_git(cmd, verb):
    """Same contract as git_target_resolver.resolve: NOT_OURS | AMBIGUOUS | DENY,target | REFUSE_AMBIGUOUS."""
    r = cmd if isinstance(cmd, Result) else read(cmd)
    if not r.raw.strip():
        return ("NOT_OURS", "")
    if not r.ok:
        shape = re.compile(r"(^|[;&|(\s])git\s+(-{1,2}\S+\s+)*" + re.escape(verb) + r"\b")
        if shape.search(r.stripped_text or r.raw):
            return ("AMBIGUOUS", "")
        return ("NOT_OURS", "")
    for c in git_calls(r):
        if c.sub == verb:
            if c.c_dir:
                return ("DENY", c.c_dir)
            if c.tainted:
                return ("REFUSE_AMBIGUOUS", "")
            return ("DENY", c.cwd_typed)
    return ("NOT_OURS", "")


def git_argv(r, verb):
    """argv after the first `git <verb>` (redirections already removed); [] if none."""
    for c in git_calls(r):
        if c.sub == verb:
            return list(c.argv)
    return []


# ----------------------------------------------------------------------------- writes
_PY_OPEN = re.compile(r"""open\(\s*(?:r|b|u)?(["'])(.+?)\1\s*,\s*(?:r|b|u)?["'][wax+][^"']*["']""")
_PY_PATH_W = re.compile(r"""Path\(\s*(["'])(.+?)\1\s*\)\s*\.\s*(?:write_text|write_bytes)\(""")
_PY_SYMLINK = re.compile(r"""symlink\(\s*(?:r|b|u)?(["'])(.+?)\1\s*,\s*(?:r|b|u)?(["'])(.+?)\3""")
_PY_SYMLINK_TO = re.compile(r"""Path\(\s*(["'])(.+?)\1\s*\)\.symlink_to\(\s*(["'])(.+?)\3""")
_PY_COPY = re.compile(r"shutil\.(?:copy2?|copyfile|copytree|move)\(")
_PY_LIT = re.compile(r"""^(?:r|b|u)?(["'])(.*)\1$""")
_PY_JOIN = re.compile(r"""^os\.path\.join\((.*)\)$""", re.S)


def _py_call_args(code, i):
    """Top-level comma-separated args of a call whose '(' is just before index i."""
    args, depth, cur, q = [], 1, [], None
    while i < len(code):
        ch = code[i]
        if q:
            cur.append(ch)
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                break
            cur.append(ch)
        elif ch == "," and depth == 1:
            args.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    args.append("".join(cur))
    return args


def _py_arg(expr):
    expr = expr.strip()
    m = _PY_LIT.match(expr)
    if m:
        return m.group(2)
    m = _PY_JOIN.match(expr)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        lits = [_PY_LIT.match(p) for p in parts]
        if all(lits):
            return "/".join(x.group(2).strip("/") if k else x.group(2) for k, x in enumerate(lits))
    return None


def _positional(args, valued=()):
    out, k = [], 0
    while k < len(args):
        a = args[k]
        if a == "--":
            out.extend(args[k + 1:])
            break
        if a.startswith("-") and len(a) > 1:
            if a in valued:
                k += 2
                continue
            k += 1
            continue
        out.append(a)
        k += 1
    return out


def _abs(p, cwd, home=True):
    if not p:
        return None
    p = os.path.expanduser(p)
    if os.path.isabs(p):
        return os.path.normpath(p)
    if cwd is None:
        return None
    return os.path.normpath(os.path.join(cwd, p))


def _seg_writes(s, base_cwd):
    cwd = s.cwd if s.cwd is not None else base_cwd
    out = []
    content = None
    if s.heredocs:
        content = "\n".join(h["body"] for h in s.heredocs)

    def add(path, via, srcs=None, flags="", cont=None):
        out.append(Write(path, _abs(path, cwd), via, [_abs(x, cwd) or x for x in (srcs or [])], cont, flags, s.id))
    for rd in s.redirects:
        if rd["op"] in _REDIR or rd["op"].startswith(">"):
            t = rd["target"]
            if t and t != "/dev/null" and not t.startswith("&"):
                add(t, ">", cont=content)
    prog, a = s.program, s.args
    if not prog:
        return out
    flags = "".join(x.lstrip("-") for x in a if x.startswith("-") and not x.startswith("--"))
    if prog == "tee":
        for p in _positional(a):
            if p != "-":
                add(p, "tee", cont=content)
    elif prog in _COPY:
        tdir = None
        for k, x in enumerate(a):
            if x in ("-t", "--target-directory") and k + 1 < len(a):
                tdir = a[k + 1]
            elif x.startswith("--target-directory="):
                tdir = x.split("=", 1)[1]
        pos = _positional(a, valued=("-t", "--target-directory", "-m", "-o", "-g", "-e", "--exclude", "--include", "-S"))
        if tdir is not None:
            for src in pos:
                add(os.path.join(tdir, os.path.basename(src.rstrip("/"))), prog, [src], flags)
        elif len(pos) >= 2:
            dest = pos[-1]
            dabs = _abs(dest, cwd)
            for src in pos[:-1]:
                t = dest
                if dest.endswith("/") or (dabs and os.path.isdir(dabs)):
                    t = os.path.join(dest, os.path.basename(src.rstrip("/")))
                add(t, prog, [src], flags)
    elif prog in _TOUCH:
        for p in _positional(a, valued=("-r", "-d", "-t", "-s")):
            if prog in ("chmod", "chown") and p is _positional(a)[0]:
                continue
            add(p, prog, flags=flags)
    elif prog == "dd":
        for x in a:
            if x.startswith("of="):
                add(x[3:], "dd")
    elif prog in ("sed", "perl") and any(x.startswith("-i") or (x.startswith("-") and not x.startswith("--") and "i" in x[1:] and prog == "sed" and x[1:2] != "e" and x[1:2] != "n") for x in a):
        pos = _positional(a, valued=("-e", "-f"))
        has_script = any(x in ("-e", "-f") for x in a)
        files = pos if has_script else pos[1:]
        for p in files:
            add(p, prog + " -i")
    elif prog == "git":
        pass
    return out


def _py_writes(code):
    out = []
    for m in _PY_OPEN.finditer(code):
        out.append((m.group(2), "python open", []))
    for m in _PY_PATH_W.finditer(code):
        out.append((m.group(2), "python write_text", []))
    for m in _PY_SYMLINK.finditer(code):
        out.append((m.group(4), "symlink", [m.group(2)]))
    for m in _PY_SYMLINK_TO.finditer(code):
        out.append((m.group(2), "symlink", [m.group(4)]))
    for m in _PY_COPY.finditer(code):
        args = _py_call_args(code, m.end())
        if len(args) >= 2:
            src, dst = _py_arg(args[0]), _py_arg(args[1])
            if dst:
                out.append((dst, "python copy", [src] if src else []))
    return out


def writes(r, cwd=None):
    """Every path the command writes: redirects, tee, cp/mv/ln/..., sed -i, and (from python -c / a
    heredoc fed to python) open(..,'w'), write_text, shutil.copy, symlink. Nested + $(..) included."""
    base = os.path.abspath(cwd) if cwd else None
    out = []

    def walk(segs):
        for s in segs:
            for sub in s.substitutions:
                walk(sub.segments)
            out.extend(_seg_writes(s, base))
            for nst in s.nested:
                if nst["language"] == "python" and nst.get("inner"):
                    for path, via, srcs in _py_writes(nst["inner"]):
                        cwdp = s.cwd if s.cwd is not None else base
                        out.append(Write(path, _abs(path, cwdp), via, [_abs(x, cwdp) or x for x in srcs], None, "", s.id))
                else:
                    walk(nst.get("segments", []))
    walk(r.segments)
    return out


# ----------------------------------------------------------------------------- CLI
def _main(argv):
    cwd = None
    if "--cwd" in argv:
        cwd = argv[argv.index("--cwd") + 1]
    try:
        cmd = sys.stdin.read()
        r = read(cmd, cwd=cwd)
        print(json.dumps(r.to_dict()))
    except Exception as e:  # the verdict is in the JSON, never in the exit code
        print(json.dumps({"ok": False, "parse_error": "internal: %s" % e, "segments": []}))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
