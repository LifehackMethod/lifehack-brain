#!/usr/bin/env python3
"""conform — check a skill/runner folder (or one file) against the skills-SOP-v2 conformance rules.

LLM CONTEXT
  WHY:          The SOP v2 laws (never silence an external command, exit 0 is never proof of work,
                checks test content, the AI-to-code handoff is a fixed-shape contract, and for ordered
                skills: card / runner-only-writes-record / truncation guard / read-only ai / pinned
                model + ccv) were prose. This tool turns the code-checkable ones into a verdict a
                build window can run, so "conforms" stops being a claim and becomes a read-back.
  RULES:        Loaded from conform-rules.md (id | scope | check). A rule marked `judge` is only ever
                listed for a human (JUDGE line); a rule marked `code` must have a detector in DETECTORS
                below, else the tool exits 4 rather than quietly skipping it.
  USAGE:        conform.py <path> [--plan <planfile>]       path = folder or single file
  OUTPUT:       one line per finding `FAIL|PASS|N/A|EXCEPTION|JUDGE <rule> <file:line> <why>`, then
                `verdict=<PASS|FAIL|N/A> scope=<s> examined=<n> fail=<n> exceptions=<n> judge=<n>`.
  EXIT:         0 PASS · 1 FAIL · 3 N/A · 4 could-not-read (message on stderr AND stdout).
  GUARDS:       - Never exit 0 on an error: unreadable path, missing rules file, a code rule with no
                  detector, a bad --plan -> exit 4.
                - A declared scope LOWER than the evidence loses: evidence wins, `FAIL SCOPE` printed.
                - Inline waivers (`# conform: allow ...`) are never declarations; only `conform.decl`
                  or the --plan file can declare `exception: <ID> because <reason>` (reason required).
                - Comment lines are skipped when scanning code patterns (they quote the offender).
                - JUDGE rules (ORD-6/ORD-7) never pass or fail a verdict on their own.
  FAIL_POSTURE: closed. Anything the tool cannot read or cannot evaluate is exit 4, not a pass.
                Detectors are heuristics (one layer, not perfect enforcement): they err toward
                flagging the common shapes and say which line and why, so a human can rule.
  SIGNPOST:     rules data = system/tools/conform-rules.md · fixtures + check.log =
                system/tools/fixtures/conform/ (run_check.sh regenerates check.log) ·
                design contract = the build-skill plan's contract.md.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(HERE, "conform-rules.md")

CODE_EXT = {".sh", ".bash", ".zsh", ".py", ".js", ".ts"}
SHELL_EXT = {".sh", ".bash", ".zsh", ""}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}

# Commands whose failure must never be silenced (fetch / send / write to the outside world).
FETCH_CMDS = {"curl", "wget", "gh", "gws", "gog", "gcalcli", "osascript", "sendmail", "mail",
              "mailx", "ssh", "scp", "rsync", "sftp"}
FETCH_LIST_TEXT = ("curl, wget, gh, gws, gog, gcalcli, git push, osascript, sendmail/mail(x), "
                   "ssh/scp/rsync/sftp, python -c with requests/urllib/httpx")

SILENCE_RE = re.compile(r'2>\s*/dev/null|>\s*/dev/null\s+2>&1|&>\s*/dev/null|>&\s*/dev/null\s+2>&1|2>&1\s*>\s*/dev/null')
PY_SILENCE_RE = re.compile(r'DEVNULL|2>\s*/dev/null|\|\|\s*true')
PY_FETCH_RE = re.compile(r'\b(curl|wget|gh|gws|gog|gcalcli|osascript|sendmail|rsync|scp|ssh)\b|git["\', ]+push|requests\.|urllib|httpx')

# A line that tests CONTENT (not rc, not presence).
CONTENT_RE = re.compile(
    r'\b(grep|egrep|jq|cmp|diff|case|awk|verify\w*|validate\w*|check_\w+|assert\w*|sha\d*sum|md5\w*)\b|=~'
    r'|\[\[?\s*!?\s*"?\$\{?(?!\?)\w+\}?"?\s*(==?|!=|-eq|-ne|-gt|-ge|-lt|-le)\s')
PRESENCE_RE = re.compile(
    r'\[\[?\s+!?\s*-[sfe]\s|\btest\s+!?\s*-[sfe]\s|\bwc\s+-l\b|\bif\s+!?\s*ls\b|non-?empty|\[\[?\s+-n\s')
CARD_PRESENCE_RE = re.compile(r'test\s+!?\s*-[sfe]\b|\[\[?\s+!?\s*-[sfe]\s|\bls\b|wc\s+-l|non-?empty|exist|^\s*$', re.I)
SHAPE_RE = re.compile(r'\bgrep\b[^|]*(-\w*[xE]\w*|\^|\$)|\bjq\b|\bcase\b|=~|\bpython3?\b|\bawk\b'
                      r'|\[\[?\s*"?\$\{?\w+\}?"?\s*(==?|-eq|-gt|-ge|-lt|-le)\s|\btest\b[^|]*\s(=|-eq)\s|\bcmp\b|\bdiff\b')
MARK_NAME_RE = re.compile(r'(last|marker|state|tick|stamp|done|cursor|checkpoint|seen|watermark|synced|progress|success|\.ok\b|heartbeat|ran\b)', re.I)

CLAUDE_P_RE = re.compile(r'\bclaude\b[^|;]*?\s(?:-p|--print)\b')


# ---------------------------------------------------------------- loading

class CannotRead(Exception):
    pass


def read_text(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8", errors="replace")
    except OSError as exc:
        raise CannotRead("cannot read %s: %s" % (path, exc.strerror or exc))


def load_rules():
    """conform-rules.md -> [(id, scope, kind, text)] in file order."""
    text = read_text(RULES_FILE)
    rules = []
    for line in text.splitlines():
        m = re.match(r'^((?:ALW|ORD)-\d+)\s*\|\s*(\w+)\s*\|\s*(\w+)\b([^|]*)\|\s*([^|]*)', line)
        if m:
            rules.append((m.group(1), m.group(2).lower(), m.group(3).lower(), m.group(5).strip()))
    if not rules:
        raise CannotRead("no rules parsed from %s" % RULES_FILE)
    return rules


def strip_comment(s):
    """Cut a trailing shell/python comment, quote-aware. ` #` or line-start `#` only."""
    q = None
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i]
    return s


def logical_lines(text, first_lineno=1, strip=True):
    """Join backslash continuations; drop comment-only lines; return [(lineno, text)]."""
    out, buf, start = [], "", None
    for n, raw in enumerate(text.splitlines(), first_lineno):
        line = raw.rstrip()
        if buf == "" and line.lstrip().startswith("#"):
            continue
        if strip:
            line = strip_comment(line).rstrip()
        if start is None:
            start = n
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        buf += line
        if buf.strip():
            out.append((start, buf.strip()))
        buf, start = "", None
    if buf.strip():
        out.append((start, buf.strip()))
    return out


class Unit:
    """One scannable body of code: a file, or one fenced bash block of a .md."""
    def __init__(self, label, path, lines, lang):
        self.label, self.path, self.lines, self.lang = label, path, lines, lang


def is_code_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in CODE_EXT or ext == ".card":
        return True
    if ext == "" and os.path.basename(path) != "conform.decl":
        try:
            with open(path, "rb") as fh:
                return fh.read(2) == b"#!"
        except OSError:
            return False
    return False


def walk(root):
    if os.path.isfile(root):
        return [root]
    files = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith(".pre-"))
        for fn in sorted(fns):
            files.append(os.path.join(dp, fn))
    return files


def md_blocks(path, label):
    """Fenced bash/sh/shell/zsh blocks of a markdown file -> [Unit]."""
    text = read_text(path)
    units, cur, start = [], None, 0
    for n, raw in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*(```+|~~~+)\s*(\w*)', raw)
        if m and cur is None:
            cur = (m.group(2).lower(), m.group(1), [])
            start = n + 1
            continue
        if cur is not None and raw.strip().startswith(cur[1]):
            if cur[0] in ("bash", "sh", "shell", "zsh", "console"):
                body = "\n".join(cur[2])
                units.append(Unit("%s[block@%d]" % (label, start), path,
                                  logical_lines(body, start), "sh"))
            cur = None
            continue
        if cur is not None:
            cur[2].append(raw)
    return units


# ---------------------------------------------------------------- declarations

DECL_RE = re.compile(r'^[\s\-\*`>]*(scope|exception)\s*:\s*(.*?)[\s`]*$', re.I)


def parse_decls(text, label, decls):
    for n, raw in enumerate(text.splitlines(), 1):
        m = DECL_RE.match(raw)
        if not m:
            continue
        kind, rest = m.group(1).lower(), m.group(2)
        loc = "%s:%d" % (label, n)
        if kind == "scope":
            mm = re.match(r'^(always|ordered|not-applicable)\s+because\s+(\S.*)$', rest, re.I)
            if mm:
                decls["scope"].append((mm.group(1).lower(), mm.group(2), loc))
            else:
                decls["invalid"].append((loc, "scope declaration needs `scope: <always|ordered|not-applicable> because <reason>`"))
        else:
            mm = re.match(r'^((?:ALW|ORD)-\d+)\s+because\s+(\S.*)$', rest, re.I)
            if mm:
                decls["exception"][mm.group(1).upper()] = (mm.group(2), loc)
            else:
                decls["invalid"].append((loc, "exception needs `exception: <RULE-ID> because <non-empty reason>`"))


# ---------------------------------------------------------------- shell helpers

SEG_SPLIT_RE = re.compile(r'(;;|;|&&|\|\||\bthen\b|\bdo\b|\belse\b|\belif\b)')
PREFIX_RE = re.compile(r'^(?:(?:if|elif|while|until|!|\{|\(|time|sudo|command|exec|nohup|env|then|do|else)\s+|\(+\s*|\{\s+'
                       r'|[A-Za-z_]\w*=(?:"[^"]*"|\'[^\']*\'|[^\s"\']*)\s+|[A-Za-z_]\w*=\s*"?\s*'
                       r'|timeout\s+\S+\s+|"\s*)')


def prep(line):
    """Turn command substitutions into separators so inner commands are their own segments."""
    return line.replace("$(", ";").replace("`", ";").replace("<(", ";")


def segments(line):
    parts = SEG_SPLIT_RE.split(prep(line))
    segs, delim = [], None
    for p in parts:
        if SEG_SPLIT_RE.fullmatch(p):
            delim = p
        else:
            segs.append((delim, p))
    return segs


def first_cmd(member):
    s = member.strip()
    for _ in range(8):
        n = PREFIX_RE.sub("", s, count=1)
        if n == s:
            break
        s = n
    return s


def is_fetch_member(member):
    s = first_cmd(member)
    words = s.split()
    if not words:
        return None
    w = os.path.basename(words[0].strip("\"'"))
    if w in FETCH_CMDS:
        return w
    if w == "git" and re.search(r'\bpush\b', s):
        return "git push"
    if re.match(r'python3?$', w) and re.search(r'requests|urllib|httpx|urlopen', s):
        return "python http"
    return None


def fetch_in(seg_text):
    for member in re.split(r'(?<!\|)\|(?!\|)', seg_text):
        f = is_fetch_member(member)
        if f:
            return f
    return None


def alw1_shell(unit):
    out = []
    for n, line in unit.lines:
        segs = segments(line)
        for i, (delim, text) in enumerate(segs):
            if delim == "||" and re.match(r'^\s*(true|:)\s*\)?\s*$', text) and i > 0:
                f = fetch_in(segs[i - 1][1])
                if f:
                    out.append((unit.label, n, "`|| %s` swallows a failed %s" % (text.strip(), f)))
            if SILENCE_RE.search(text):
                f = fetch_in(text)
                if f:
                    out.append((unit.label, n, "stderr silenced on %s (%s)" % (f, SILENCE_RE.search(text).group(0))))
    return out


def alw1_other(unit):
    out = []
    for n, line in unit.lines:
        if PY_FETCH_RE.search(line) and PY_SILENCE_RE.search(line):
            out.append((unit.label, n, "error output silenced on a fetch/send command"))
    return out


def alw1(ctx):
    out = []
    for u in ctx["units"]:
        out += alw1_shell(u) if u.lang == "sh" else alw1_other(u)
    for cid, kind, action, check, label, n in ctx["card_lines"]:
        if kind == "code":
            u = Unit(label, None, [(n, action), (n, check)], "sh")
            out += [(l, n, w) for (l, _, w) in alw1_shell(u)]
    return dedupe(out)


def dedupe(items):
    seen, res = set(), []
    for it in items:
        k = (it[0], it[1], it[2])
        if k not in seen:
            seen.add(k)
            res.append(it)
    return res


# ALW-2 --------------------------------------------------------------

WRITE_TOUCH_RE = re.compile(r'\btouch\s+("[^"]+"|\'[^\']+\'|\S+)')
WRITE_REDIR_RE = re.compile(r'\b(?:echo|date|printf)\b[^;&|]*?>{1,2}\s*("[^"]+"|\'[^\']+\'|[^\s;&|"\']+)')


def find_marker_write(text):
    for m in WRITE_TOUCH_RE.finditer(text):
        return m.start(), m.group(1)           # touch is always a marker
    for m in WRITE_REDIR_RE.finditer(text):
        if MARK_NAME_RE.search(os.path.basename(m.group(1).strip("\"'"))):
            return m.start(), m.group(1)
    return None


def rc_only_condition(cond):
    c = cond.strip()
    if re.search(r'\$\{?(\?|rc|ret|status|exit\w*|retval|code|result)\}?"?\s*(-eq|==?)\s*"?0|\$\{?(rc|ret|status|retval)\}?"?\s*(-ne|!=)', c) \
            and not re.search(r'\b(grep|jq|cmp|diff|case|awk)\b', c):
        return True
    if CONTENT_RE.search(c):
        return False
    if "$?" in c:
        return True
    c = re.sub(r'^(if|elif|while)\s+', "", c).lstrip("! ").strip()
    return bool(c) and not re.match(r'^(\[|test\b)', c)


def alw2(ctx):
    out = []
    for u in ctx["units"]:
        if u.lang != "sh":
            continue
        L = u.lines
        for idx, (n, line) in enumerate(L):
            w = find_marker_write(line)
            if not w:
                continue
            pos, target = w
            before = line[:pos]
            why = None
            m = re.search(r'\bif\b(.*?);\s*then\b', line)
            if m and m.end() <= pos + 1 and rc_only_condition(m.group(1)):
                why = "marker %s advanced inside `if %s; then` with no content check" % (target, m.group(1).strip()[:40])
            elif "&&" in before:
                cond = before.rsplit("&&", 1)[0]
                if rc_only_condition(cond):
                    why = "marker %s advanced by `&&` on exit code alone" % target
            elif not m:
                # multi-line: look back for an `if <cmd>` ... then block (within 4 lines)
                for j in range(idx - 1, max(idx - 5, -1), -1):
                    pl = L[j][1]
                    if re.match(r'^(if|elif)\b', pl):
                        cond = " ".join(x[1] for x in L[j:idx])
                        cond = re.sub(r'\bthen\b.*$', "", cond)
                        if rc_only_condition(cond):
                            why = "marker %s advanced inside `%s` with no content check" % (target, pl[:40])
                        break
            if why:
                out.append((u.label, n, why))
    return dedupe(out)


# ALW-3 --------------------------------------------------------------

def alw3(ctx):
    out = []
    for u in ctx["units"]:
        if u.lang != "sh":
            continue
        has_content = any(CONTENT_RE.search(t) for _, t in u.lines)
        if has_content:
            continue
        for n, t in u.lines:
            m = PRESENCE_RE.search(t)
            if m:
                out.append((u.label, n, "check tests presence only (`%s`) and the file has no content test" % m.group(0).strip()))
    for cid, kind, action, check, label, n in ctx["card_lines"]:
        if kind == "code" and CARD_PRESENCE_RE.search(check) and not SHAPE_RE.search(check):
            out.append((label, n, "card %s check tests presence only" % cid))
    return dedupe(out)


# ALW-4 --------------------------------------------------------------

def alw4(ctx):
    out = []
    for u in ctx["units"]:
        if u.lang != "sh":
            continue
        L = u.lines
        for idx, (n, line) in enumerate(L):
            if not CLAUDE_P_RE.search(line):
                continue
            m = re.match(r'^(?:local\s+|export\s+)?(\w+)=\s*"?\$\(', line)
            ok = False
            if m:
                var = m.group(1)
                ref = re.compile(r'\$\{?%s\b' % re.escape(var))
                for _, t in L[idx + 1:]:
                    if ref.search(t) and (re.search(r'\bcase\b|\bgrep\b|\bjq\b|=~|\bawk\b|\bpython3?\b', t)
                                          or re.search(r'\[\[?\s*"?\$\{?%s\}?"?\s*(==?|-eq|-gt|-ge|-lt|-le)\s' % re.escape(var), t)):
                        ok = True
                        break
            else:
                if re.search(r'\|\s*(grep|jq|python3?|awk)\b', line):
                    ok = True
                else:
                    mt = re.search(r'>{1,2}\s*("[^"]+"|[^\s;&|]+)', line)
                    if mt:
                        tgt = mt.group(1).strip('"')
                        for _, t in L[idx + 1:]:
                            if tgt in t and SHAPE_RE.search(t):
                                ok = True
                                break
            if not ok:
                out.append((u.label, n, "ai output is not parsed by a fixed-shape check (case/grep -x/jq/number)"))
    for cid, kind, action, check, label, n in ctx["card_lines"]:
        if kind == "ai":
            if not check.strip():
                out.append((label, n, "ai step %s has no check" % cid))
            elif not SHAPE_RE.search(check):
                out.append((label, n, "ai step %s check has no fixed shape (presence/non-empty only)" % cid))
    return dedupe(out)


# ORD ----------------------------------------------------------------

def record_names(ctx):
    names = {"record.tsv"}
    for u in ctx["code_units"]:
        for _, t in u.lines:
            for m in re.finditer(r'--record[ =]+("?)([^\s"]+)\1', t):
                names.add(os.path.basename(m.group(2)))
    return names


def ord1(ctx):
    cards = ctx["card_files"]
    if not cards:
        return [(ctx["rootlabel"], 0, "no *.card file (id | kind | action | check) in an ordered artifact")]
    out = []
    for label in cards:
        valid = [x for x in ctx["card_lines"] if x[4] == label]
        if not valid:
            out.append((label, 0, "card has no valid `id | kind | action | check` line"))
    out += ctx["card_bad"]
    return out


def ord2(ctx):
    out = []
    names = record_names(ctx)
    name_re = re.compile("|".join(re.escape(x) for x in names) + r'|\$\{?RECORD\}?')
    for cid, kind, action, check, label, n in ctx["card_lines"]:
        if kind == "ai" and name_re.search(action):
            out.append((label, n, "ai step %s action names the record" % cid))
    for u in ctx["code_units"]:
        for n, t in u.lines:
            if CLAUDE_P_RE.search(t):
                body = re.sub(r'>{1,2}\s*("[^"]*"|\S+)', "", t[t.find("claude"):])
                if name_re.search(body):
                    out.append((u.label, n, "claude -p call names the record in its prompt"))
    return out


GUARD_RE = re.compile(r'tail\s+-c\s*1\b|truncat|last[-_ ]?line|tail\s+-n?\s*1\b|wc\s+-c|\bnewline\b', re.I)


def runner_units(ctx):
    rec = re.compile("|".join(re.escape(x) for x in record_names(ctx)) + r'|--record|\bRECORD\b')
    shell = [u for u in ctx["code_units"] if u.lang == "sh" or u.path.endswith(".py")]
    writers = [u for u in shell if any(rec.search(t) for _, t in u.lines)]
    return writers or shell


def ord3(ctx):
    rs = runner_units(ctx)
    if not rs:
        return [(ctx["rootlabel"], 0, "no runner found to carry a truncation guard")]
    out = []
    for u in rs:
        if not any(GUARD_RE.search(t) for _, t in u.lines):
            out.append((u.label, 0, "runner has no truncation / last-line-complete guard"))
    return out


def claude_calls(ctx):
    for u in ctx["code_units"]:
        for n, t in u.lines:
            for seg in re.split(r'\|\||&&|;', prep(t)):
                if CLAUDE_P_RE.search(seg):
                    yield u, n, seg


def ord4(ctx):
    out = []
    for u, n, seg in claude_calls(ctx):
        if not re.search(r'--allowed-?[tT]ools[ =]+["\']?Read["\']?(\s|$|\))', seg):
            out.append((u.label, n, "claude -p without `--allowedTools Read`"))
    return dedupe(out)


def ord5(ctx):
    out, calls = [], list(claude_calls(ctx))
    for u, n, seg in calls:
        if not re.search(r'--model[ =]+\S+', seg):
            out.append((u.label, n, "claude -p without `--model <x>`"))
    if calls and not any(re.search(r'\bccv=', t) for u in ctx["code_units"] for _, t in u.lines):
        out.append((ctx["rootlabel"], 0, "runner never records `ccv=` (claude version) per run"))
    return dedupe(out)


DETECTORS = {"ALW-1": alw1, "ALW-2": alw2, "ALW-3": alw3, "ALW-4": alw4,
             "ORD-1": ord1, "ORD-2": ord2, "ORD-3": ord3, "ORD-4": ord4, "ORD-5": ord5}


# ---------------------------------------------------------------- main

def build_context(root, files, decls):
    base = root if os.path.isdir(root) else os.path.dirname(root)

    def lab(p):
        return os.path.relpath(p, base) if os.path.isdir(root) else os.path.basename(p)

    ctx = {"rootlabel": os.path.basename(os.path.abspath(root)), "units": [], "code_units": [],
           "card_lines": [], "card_files": [], "card_bad": [], "md": [], "codefiles": []}
    for p in files:
        label = lab(p)
        ext = os.path.splitext(p)[1].lower()
        if os.path.basename(p) == "conform.decl":
            parse_decls(read_text(p), label, decls)
            continue
        if ext == ".md":
            ctx["md"].append((p, label))
            continue
        if not is_code_file(p):
            continue
        text = read_text(p)
        ctx["codefiles"].append(label)
        if ext == ".card":
            ctx["card_files"].append(label)
            for n, raw in enumerate(text.splitlines(), 1):
                if not raw.strip() or raw.strip().startswith("#"):
                    continue
                f = re.split(r'\s+\|\s+', raw.strip(), maxsplit=3)
                if len(f) == 4 and f[1].strip().lower() in ("code", "ai", "human"):
                    ctx["card_lines"].append((f[0].strip(), f[1].strip().lower(), f[2].strip(), f[3].strip(), label, n))
                elif " | " in raw:
                    ctx["card_bad"].append((label, n, "malformed card line (need `id | kind | action | check`, kind code|ai|human)"))
            continue
        lang = "sh" if ext in SHELL_EXT else "other"
        u = Unit(label, p, logical_lines(text), lang)
        ctx["units"].append(u)
        ctx["code_units"].append(u)
    return ctx


def classify(ctx, decls):
    has_code = bool(ctx["codefiles"])
    rec = any(re.search(r'record\.tsv|--record\b', t) for u in ctx["code_units"] for _, t in u.lines)
    if not has_code:
        ev = "not-applicable"
    elif ctx["card_files"] or rec:
        ev = "ordered"
    else:
        ev = "always"
    return ev


RANK = {"not-applicable": 0, "always": 1, "ordered": 2}


def emit(line):
    print(line)


def main(argv):
    args, plan = [], None
    i = 0
    while i < len(argv):
        if argv[i] == "--plan" and i + 1 < len(argv):
            plan = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if len(args) != 1:
        raise CannotRead("usage: conform.py <path> [--plan <planfile>]")
    root = args[0]
    if not os.path.exists(root):
        raise CannotRead("path does not exist: %s" % root)
    rules = load_rules()
    for rid, scope, kind, _ in rules:
        if kind == "code" and rid not in DETECTORS:
            raise CannotRead("rule %s is marked code in conform-rules.md but conform.py has no detector" % rid)

    decls = {"scope": [], "exception": {}, "invalid": []}
    files = walk(root)
    if os.path.isfile(root):
        d = os.path.join(os.path.dirname(os.path.abspath(root)), "conform.decl")
        if os.path.isfile(d):
            parse_decls(read_text(d), "conform.decl", decls)
    if plan:
        parse_decls(read_text(plan), os.path.basename(plan), decls)
    ctx = build_context(root, files, decls)

    evidence = classify(ctx, decls)
    scope = evidence
    findings = []   # (status, rule, loc, why)
    if decls["scope"]:
        dscope, dwhy, dloc = decls["scope"][-1]
        if RANK[dscope] < RANK[evidence]:
            findings.append(("FAIL", "SCOPE", dloc, "declared scope %s is lower than the evidence (%s); evidence wins" % (dscope, evidence)))
        else:
            scope = dscope
    for loc, why in decls["invalid"]:
        findings.append(("FAIL", "DECL", loc, why))

    if scope == "not-applicable":
        reason = "no executable code" if not decls["scope"] else decls["scope"][-1][1]
        if evidence == "not-applicable" and not any(f[0] == "FAIL" for f in findings):
            for f in findings:
                emit("%s %s %s %s" % f)
            emit("N/A - %s: %s" % (root, reason))
            emit("verdict=N/A scope=not-applicable examined=0 fail=0 exceptions=0 judge=0")
            return 3

    # markdown fenced bash blocks count when the folder has code
    if ctx["codefiles"]:
        for p, label in ctx["md"]:
            ctx["units"] += md_blocks(p, label)

    judge = 0
    for rid, rscope, kind, text in rules:
        if rscope == "ordered" and scope != "ordered":
            continue
        if kind == "judge":
            emit("JUDGE %s - %s" % (rid, text))
            judge += 1
            continue
        hits = DETECTORS[rid](ctx)
        if not hits:
            findings.append(("PASS", rid, "-", "no violations found"))
            continue
        for label, n, why in hits:
            loc = "%s:%d" % (label, n) if n else label
            if rid in decls["exception"]:
                findings.append(("EXCEPTION", rid, loc, "%s [declared at %s: %s]" % (why, decls["exception"][rid][1], decls["exception"][rid][0])))
            else:
                findings.append(("FAIL", rid, loc, why))
    used = {f[1] for f in findings if f[0] == "EXCEPTION"}
    for rid in decls["exception"]:
        if rid not in used:
            findings.append(("EXCEPTION", rid, "-", "unused"))

    nfail = sum(1 for f in findings if f[0] == "FAIL")
    nexc = sum(1 for f in findings if f[0] == "EXCEPTION" and f[2] != "-")
    for f in findings:
        emit("%s %s %s %s" % f)
    examined = len(ctx["codefiles"]) + len([u for u in ctx["units"] if "[block@" in u.label])
    verdict = "FAIL" if nfail else "PASS"
    emit("verdict=%s scope=%s examined=%d fail=%d exceptions=%d judge=%d" % (verdict, scope, examined, nfail, nexc, judge))
    return 1 if nfail else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except CannotRead as exc:
        msg = "CANNOT-READ: %s" % exc
        print(msg)
        print(msg, file=sys.stderr)
        sys.exit(4)
    except Exception as exc:  # never exit 0 on an error
        msg = "CANNOT-READ: internal error: %r" % (exc,)
        print(msg)
        print(msg, file=sys.stderr)
        sys.exit(4)
