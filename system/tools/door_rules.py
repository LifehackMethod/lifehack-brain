"""door_rules.py -- the ONE copy of the job door's error-hiding rules (plan v2 3b CHECK 2, fix-group F2).

WHY A SHARED FILE: these patterns used to live only inside the python heredoc of install-schedulers.sh
(`--check-row`, rules 5.9(d) and 5.4(d)). The commit check system/githooks/checks/hides_failure.py needs the very
same rules for every staged script, and a second copy would drift. Both now import THIS file. Change a rule here
and the job door and the commit check change together. Behaviour of the door is unchanged (job-sim suite green).
"""
import re

MODEL_ID = re.compile(r"claude-(?:haiku|sonnet|opus|fable)-[0-9]")   # (d) no literal model id outside the table
MODEL_TABLE_FILES = ("model.lib.sh", "model_ids.py")
# a literal passed as a model flag/assignment (any future family name): --model X, "--model", "X", model="X", MODEL=X.
# A variable/expansion ($MODEL_ID_*, model_id(tier), run_model's tier) never matches: a value must START with a letter/digit.
MODEL_LIT = [re.compile(p) for p in (
    r"""--model(?:=|[ \t]+)["']?([A-Za-z0-9][\w.\-]*)""",
    r"""["']--model["']\s*,\s*["']([\w.\-]+)["']""",
    r"""\b[Mm][Oo][Dd][Ee][Ll]\s*=\s*["']([\w.\-]+)["']""",
    r"""^\s*(?:export\s+)?MODEL\s*=\s*([A-Za-z0-9][\w.\-]*)\s*(?:#.*)?$""")]
# (e) 5.9(d) no silenced error on a fetch, write, push or model call: `|| true`, `|| :` and `2>/dev/null` hide the one thing the
# wrapper needs to see. Narrow and pattern-based, one LINE at a time, bash files only: the line must (1) carry one of those
# silencers and (2) call something that fetches, writes, pushes or calls a model. Harmless uses pass: kill/pkill/pgrep/stat/rm/
# date/wait, `command -v`/`which` lookups, reading a stamp with cat. Failures are named, never swallowed: log to stderr and set the rc.
SILENCER = re.compile(r"\|\|\s*(?:true|:)(?=\s*(?:$|[;&|)}#]))|2>\s*/dev/null|&>\s*/dev/null|>\s*/dev/null\s+2>&1")
LOOKUP = re.compile(r"(?:command\s+-v|\bwhich|\btype\s+-p)\s+\S+")
CALLEES = [("fetch", re.compile(r"(?<![\w/.-])(?:gws|curl|wget)\b|\$\{?GWS\w*\}?\x22?\s+[a-z]|email_fetch\.py|safe_fetch|safe_search|[\w.-]*fetch[\w.-]*\.(?:py|sh)\b|\bgit\s+(?:-C\s+\S+\s+)?(?:fetch|pull|clone)\b")),
           ("push", re.compile(r"notify-send|\bgit\s+(?:-C\s+\S+\s+)?push\b|\bntfy\b")),
           ("model", re.compile(r"\brun_model\b|\bclaude\s+-p\b|\$\{?CLAUDE(?:_BIN)?\}?\s+-p\b|\"\$\{?CLAUDE(?:_BIN)?\}?\"\s+-p\b")),
           ("write", re.compile(r"emit_finding|emit_status|status-tile|(?<![\w:?-])write_status_tile(?=\s)|--write\b|--stamp\w*|--finish\b|[\w.-]*(?:write|sync|diary|journal|sensor|record)[\w.-]*\.(?:py|sh)\b"
                                r"|\b(?:printf|echo|cat|tee|cp|mv)\b[^|;&<>]*\s>>?\s*[^&\s>]"))]
# The fire-journal boilerplate (system/hooks/lib/journal.sh contract): `. lib/journal.sh 2>/dev/null || lhb_journal_fire() { :; }` and the
# `trap 'lhb_journal_fire ... 2>/dev/null || true' EXIT` line. Silent on purpose (the journal must never change a hook's own output).
JOURNAL_IDIOM = re.compile(r"lhb_journal_fire")
# "A real reason, or fix it" (Round C 3, switch allow_silence_reason): what an escape comment (`# allow-silence:`, `# empty-ok:`,
# `# not-wired-yet:`) must carry before it exempts anything. A reason is JUNK when it is short, only filler/placeholder words, or only
# repeats the code it sits on. Pure function; the callers read the switch.
JUNK_WORDS = frozenset("""todo tbd fixme ok okay fine needed need needs reason reasons because intentional intended on purpose ignore ignored
    ignoring skip skipped none na n/a noqa nope wip temp temporary later yes no safe harmless works work it its this that the a an is are be
    to for of and or so just here there see above below hack workaround quiet silence silent silenced stub test tests rig""".split())
REASON_HELP = ("a reason names WHICH failure is tolerated and WHY that is safe, e.g. "
               "`# allow-silence: best-effort stamp; if the write fails the next run repeats the line, nothing is lost`")
def weak_reason(reason, code=""):
    """-> '' if the escape reason is real, else a short why-it-is-junk string."""
    r = (reason or "").strip()
    words = re.findall(r"[a-z0-9][a-z0-9_./-]*", r.lower())
    if len(r) < 15 or len(words) < 3: return "too short to say what failure is tolerated and why"
    content = [w for w in words if w not in JUNK_WORDS]
    if len(content) < 2: return "only filler/placeholder words"
    toks = set(re.findall(r"[a-z0-9]+", (code or "").lower()))
    if all(w in toks for w in re.findall(r"[a-z0-9]+", " ".join(content))): return "only repeats the code"
    return ""
def silenced_call(line):
    """-> kind ('fetch'|'push'|'model'|'write') if this bash line silences the error of a fetch/write/push/model call, else ''."""
    if not SILENCER.search(line): return ""
    if JOURNAL_IDIOM.search(line): return ""   # the fire-journal boilerplate every hook carries (hooks/lib/journal.sh): silent BY DESIGN
    probe = LOOKUP.sub("", line)
    probe = re.sub(r"[\w./$\"{}-]*(?:\btest[_-]|[_-]tests?\.)[\w.-]*\.(?:sh|py)", "", probe)   # a test script's exit code IS its verdict, read by the caller
    for kind, rx in CALLEES:
        if rx.search(probe): return kind
    return ""

# slip 41 (raw Gmail/curl): a script that curls a Google/Gmail API host itself bypasses the one sanctioned Gmail read. Shared by the job
# door and commit check 2. Exempt: the shared tool itself (email_fetch.py) and the safe readers (safe_*.py, safe_fetch).
GOOGLE_CURL = re.compile(r"(?<![\w/.-])(?:curl|wget)\b.*\b(?:gmail\.googleapis\.com|mail\.google\.com|(?:www\.)?googleapis\.com/gmail|oauth2\.googleapis\.com)")
GOOGLE_CURL_TOOL = "shared/tools/email_fetch.py"
GOOGLE_CURL_WHY = f"raw curl to a Google/Gmail API host: go through the shared email tool ({GOOGLE_CURL_TOOL}; system/register/toolbox.md)"
def google_curl_exempt(path):
    b = path.replace("\\", "/").rsplit("/", 1)[-1]
    return b == "email_fetch.py" or b.startswith("safe_")
def google_curl(line):
    """-> True if this (comment-stripped) bash/python line curls a Google/Gmail API host directly."""
    return bool(GOOGLE_CURL.search(line))

# F3 (a checker that checked nothing reports pass): a script that is a checker/linter/verifier/validator (by name or header) and
# iterates over FOUND files (glob/find/ls/listdir/walk) must say what happens at zero targets. MECHANICAL and lenient: it fires only when
# the whole file shows no zero-count guard at all. Not caught (not reliably mechanical): `exit 0` after an empty scan with a guard elsewhere.
CHECKER_NAME = re.compile(r"(?:^|[-_.])(?:check|checks|checker|lint|linter|verify|verifier|validate|validator)(?:[-_.]|$)")
CHECKER_HEAD = re.compile(r"\b(?:check(?:s|er)?|lint(?:er)?|verif(?:y|ier|ies)|validat(?:e|or|es))\b", re.I)
FOUND_LOOP = re.compile(r"""^\s*for\s+\w+(?:\s*,\s*\w+)*\s+in\s+.*(?:glob|rglob|iterdir|os\.walk|listdir|scandir|find_files|\bfiles\b|\bpaths\b)"""
                        r"""|^\s*for\s+\w+\s+in\s+.*(?:\*|\$\((?:find|ls)\b|`(?:find|ls)\b|\$\{?\w*FILES\w*\}?)"""
                        r"""|^\s*(?:find|ls)\b.*\|\s*while\s+(?:IFS=\S*\s+)?read\b|^\s*while\s+(?:IFS=\S*\s+)?read\b.*<\s*<?\(?\s*(?:find|ls)\b""")
ZERO_GUARD = re.compile(r"""if\s+not\s+\(?\w[\w.\[\]()]*\)?\s*:|if\s+not\s+any\(|len\([^)]*\)\s*(?:==|<|<=)\s*[01]\b|\bif\s+\w+\s*==\s*0\b|\bif\s+\w+\s*<\s*1\b"""
                         r"""|\[\[?\s+-z\s|\[\[?\s+!\s+-[sef]\s|-eq\s+0\b|-lt\s+1\b|\(\(\s*\w+\s*(?:==|<|<=)\s*[01]\s*\)\)|\bcount\w*\s*==\s*0"""
                         r"""|(?:no|zero|0|nothing|empty)\s+(?:\w+\s+){0,3}(?:found|checked|matched|to check|targets|files|skills)""", re.I)
def f3_checker(path, text):
    """-> True when this script is a checker by name or header (first 12 lines)."""
    b = path.replace("\\", "/").rsplit("/", 1)[-1]
    head = "\n".join(text.splitlines()[:12])
    return bool(CHECKER_NAME.search(b) or CHECKER_HEAD.search(head))
def f3_unguarded(path, text, lines_added, lines):
    """-> [(lineno, why)] for added found-files loops in a checker script whose file has no zero-target guard anywhere."""
    if not f3_checker(path, text) or ZERO_GUARD.search(text):
        return []
    return [(i, "checker iterates over found files but nothing fails at zero targets (a checker that checked nothing reports pass): "
                "add `if not files: fail` / `[ -z \"$files\" ] && exit 1`, or `# empty-ok: <why>`")
            for i in sorted(lines_added) if 0 < i <= len(lines) and FOUND_LOOP.search(lines[i - 1])]

# F7 (slip 56: pulse jobs wrote status tiles under other names, 9 of 16): the status tile a job writes must be named for the job's
# own id, because system-health resolves a tile by that name with zero aliases. Door rule, so it also holds at run time (job-run.sh
# runs the door on every launch). Mechanical: every `write_status_tile <name> ...` call in a runner (or what it sources) must pass a
# name that is the row's id, either as a literal or as a variable the same file sets to that literal. Anything else is refused.
TILE_CALL = re.compile(r"""(?<![\w./-])write_status_tile\s+(?:"([^"]*)"|'([^']*)'|(\S+))""")
def tile_name_refusals(job, lines):
    """-> [(lineno, why)] for each write_status_tile call whose first argument is not the job id (comments skipped)."""
    out = []
    def assigned(var):
        val = None
        for ln in lines:
            m = re.match(r"""\s*(?:readonly\s+|export\s+|declare\s+-r\s+)?%s=(?:"([^"]*)"|'([^']*)'|([^\s;#]+))""" % re.escape(var), ln)
            if m: val = next(g for g in m.groups() if g is not None)
        return val
    for i, ln in enumerate(lines, 1):
        if ln.lstrip().startswith("#"): continue
        m = TILE_CALL.search(ln)
        if not m: continue
        arg = next(g for g in m.groups() if g is not None)
        v = arg
        mv = re.fullmatch(r"\$\{?(\w+)\}?", arg)
        if mv:
            v = assigned(mv.group(1))
            if v is None:
                out.append((i, f"status tile name '{arg}' is not set to a literal in this file: the tile must be named for the job id '{job}'")); continue
        if v != job:
            out.append((i, f"status tile named '{v}' but the job id is '{job}': system-health finds a tile by the job id, a differently named tile is never read"))
    return out

# 3.4b (slips 16/18): the row's OWN command must not swallow the job's exit code. `<runner> || true` (or `|| :`) turns every failure
# into success before job-run.sh sees it, whatever the runner is. Checked on the command text itself, at the door and so at run time.
CMD_SWALLOW = re.compile(r"\|\|\s*(?:true|:)(?=\s*(?:$|[;&|)}#]))")
def cmd_swallows(cmd):
    """-> True when the row's command ends a step in `|| true` / `|| :`."""
    return bool(CMD_SWALLOW.search(cmd))
