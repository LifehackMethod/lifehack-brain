#!/usr/bin/env python3
"""plan_retire — a task leaves the live plan only after CODE re-runs its Verify.

WHY: a plan that only accumulates checkmarks grows more confident and less accurate
(canon §5.11) — nothing ever re-checks an old tick. A typed "verified-by:" is
self-report, not evidence (canon §7.2). So retiring a task means RUNNING the
card's own `Verify:` command again, right now, and moving nothing on a miss.
When many cards fail at once, suspect this runner before the cards — 7 of 8
first-run failures were the runner's working directory.

WHAT: find the task's card, parse its `Verify:` line for runnable command(s), run
each for real, compare each result to the outcome the card states. All pass +
evidence of a shipped commit (or a stated `artifact:`) -> move the card out of
the live plan into `<plan>.done.md` with the receipt attached; collapse a
fully-retired phase.

VERDICTS
    RETIRED <id> hash=<h>       0  moved; live -1 open card, .done.md +1 block
    WOULD-RETIRE <id> hash=<h>  0  --dry-run only; nothing written
    ALREADY-RETIRED <id>        2  header is already `~~<id>~~`
    VERIFY-FAILED <id>          2  a Verify result missed its stated outcome;
                                    live plan untouched
    NO-EVIDENCE <id>            2  no shipped commit and no `artifact:` value
    COUNT-MISMATCH              2  post-move counts off by more than one;
                                    backup restored, nothing left half-moved
    CANNOT-READ <why>           4  NO-OUTCOME MEMBER -- unreadable/missing plan,
                                    missing card, or no runnable Verify. Never
                                    passes by default.

    2026-09-04: task 2.3 was wrongly RETIRED on this path — an unparsed
    expectation fell through to `ok = (rc == 0)`, and the card's own preferred
    `; echo $?` command shape makes the *shell's* exit code 0 unconditionally.
    Rule since: no parseable expectation => CANNOT-READ, never pass.
"""
import argparse, os, re, shutil, subprocess, sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CANNOT_READ = 4
ID = r'[A-Za-z]{0,2}\d{1,3}\.\d{1,2}[a-z]?'
KNOWN_CMDS = {"python3", "grep", "test", "wc", "ls", "awk", "git", "gh",
              "bash", "sh", "cat", "diff", "head", "tail"}
SCRIPT_RE = re.compile(r'^[\w.-]+\.py$')          # a bare `foo.py` naming a repo tool

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
CARD_ANY_RE = re.compile(r'^- \[ \] \*\*', re.M)
DONE_HEAD_RE = re.compile(r'^## ', re.M)


def _verify_cwd(block):
    """Verify commands are written relative to the card's own Where:, not the repo root.

    2026-09-04, first real use: 7 of 8 cards failed with rc=2 (grep: no such file) because
    their commands say `SKILL.md`, not the full path. The card already names Where:; derive
    the working directory from it rather than asking every command to repeat the path.
    Falls back to REPO_ROOT when the card has no usable Where:.
    """
    m = re.search(r'`?Where:\s*([^`\n]+)', block)
    if not m:
        return REPO_ROOT
    first = m.group(1).split("·")[0].strip().split()[0].strip("`")
    p = os.path.expanduser(first)
    if not os.path.isabs(p):
        return REPO_ROOT
    if os.path.isdir(p):
        return p
    d = os.path.dirname(p)
    return d if os.path.isdir(d) else REPO_ROOT


def cannot_read(why):
    print(f"CANNOT-READ {why}"); sys.exit(CANNOT_READ)

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def find_block(lines, task_id):
    """Locate the card's [header_idx, end_idx) span. Exits directly on
    ALREADY-RETIRED or missing-card (both terminal, no card to return)."""
    header_re = re.compile(r'^(\s*)- \[ \] \*\*' + re.escape(task_id) + r'\b')
    retired_re = re.compile(r'^~~' + re.escape(task_id) + r'~~')
    if any(retired_re.match(l) for l in lines):
        print(f"ALREADY-RETIRED {task_id}"); sys.exit(2)
    for i, l in enumerate(lines):
        if header_re.match(l):
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if CARD_ANY_RE.match(lines[j]) or lines[j].startswith('## ') or lines[j].rstrip() == '---':
                    end = j; break
            return i, end
    cannot_read(f"task {task_id} not found in plan")

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

def parse_verify(line):
    """Return [(cmd_text, expectation-or-None), ...] found on one Verify line."""
    spans = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r'`([^`]+)`', line)]
    cmd_spans = [s for s in spans if _is_known_cmd(s[2])]
    out = []
    for k, (start, end, cmd) in enumerate(cmd_spans):
        gap_end = cmd_spans[k + 1][0] if k + 1 < len(cmd_spans) else len(line)
        gap = line[end:gap_end]
        if '→' not in gap:               # no arrow -> no stated outcome
            out.append((cmd, None)); continue
        after_arrow = gap.split('→', 1)[1]
        m = re.search(r'\bafter\b\s*`?([^`,.\s]+)`?', after_arrow, re.I)
        exp = classify(m.group(1)) if m else None
        if exp is None:
            # A backtick-quoted expectation sitting right after the arrow is read
            # verbatim and parsing STOPS at its closing backtick -- a parenthetical
            # aside or a trailing sentence after that point is never consulted.
            # Scanning the whole rest of the line (the old fallback) is what
            # silently erased 2.3's stated `0` behind "(a trailing aside)"
            # (2026-09-04); this does not guess, it just stops reading sooner.
            m2 = re.match(r'\s*`([^`]+)`', after_arrow)
            exp = classify(m2.group(1)) if m2 else classify(after_arrow)
        out.append((cmd, exp))
    return out

def _resolve_script(cmd):
    """A card names its own tool bare (`plan_lint.py args`), meaning 'run the tool
    that lives in this card's own directory' — but shell=True/cwd does not put cwd
    on PATH, so bash reports 'command not found' (rc=127) for a real, executable
    file sitting right there. Rewrite a bare `<script>.py` leading token to
    `./<script>.py` so it resolves relative to the cwd we already derived. A
    command that already carries a path (`./x.py`, `system/tools/x.py`) is left
    alone; if the script genuinely is not in that directory, `./x.py` fails
    honestly (No such file), which is the true answer, not a fabricated one.
    """
    m = re.match(r'^([\w.-]+\.py)(\s|$)', cmd)
    if m and "/" not in m.group(1):
        return "./" + cmd
    return cmd

def run_cmd(cmd, cwd=None):
    return subprocess.run(_resolve_script(cmd), shell=True, cwd=cwd or REPO_ROOT,
                           capture_output=True, text=True, timeout=120,
                           stdin=subprocess.DEVNULL)

def check_verify(block_lines, task_id):
    """Run every command on the card's Verify line; return receipts on full
    pass, or print VERIFY-FAILED and exit 2 on any miss.

    2026-09-04: an unparseable expectation (exp is None) is CANNOT-READ, never a
    pass. This is checked for EVERY command before any of them are run, so a
    card with one unreadable expectation moves nothing. Fixed after task 2.3
    was wrongly retired: its unparsed `→ `0`` fell through to `ok = (rc == 0)`,
    and the card's own preferred `; echo $?` shape makes the shell's own exit
    code 0 unconditionally — an unreachable check is not a clean result.
    """
    verify_line = next((l for l in block_lines if re.match(r'^\s*`?Verify:', l)), None)
    if verify_line is None:
        cannot_read(f"no Verify: line on {task_id}")
    cmds = parse_verify(verify_line)
    if not cmds:
        cannot_read(f"no runnable verify on {task_id}")
    for cmd, exp in cmds:
        if exp is None:
            cannot_read(f"no parseable expectation for {task_id}: {cmd}")
    cwd = _verify_cwd("\n".join(block_lines))
    receipts, failures = [], []
    for cmd, exp in cmds:
        proc = run_cmd(cmd, cwd)
        rc, out = proc.returncode, proc.stdout
        receipts.append((cmd, rc, out))
        if exp[0] == 'exit':
            ok = (rc == exp[1])
        elif exp[0] == 'bare':
            if out.strip() == str(exp[1]):
                ok = True
            elif out.strip() == '' and 0 <= exp[1] <= 255:
                # no stdout at all (e.g. `test -f x` with no `; echo $?`) -> the
                # stated number is the command's exit code, not printed text.
                ok = (rc == exp[1])
            else:
                ok = False
        elif exp[0] == 'ge':
            ok = out.strip().lstrip('-').isdigit() and int(out.strip()) >= exp[1]
        elif exp[0] == 'le':
            ok = out.strip().lstrip('-').isdigit() and int(out.strip()) <= exp[1]
        elif exp[0] == 'substr':
            ok = exp[1] in out
        if not ok:
            failures.append((cmd, exp, rc, out))
    if failures:
        print(f"VERIFY-FAILED {task_id}")
        for cmd, exp, rc, out in failures:
            print(f"  cmd: {cmd}")
            print(f"  expected: {exp}")
            print(f"  got: rc={rc} stdout={out!r}")
        sys.exit(2)
    return receipts

def get_evidence(block_lines, task_id):
    art = re.search(r'artifact:\s*(\S+)', '\n'.join(block_lines), re.I)
    tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_git_check.py")
    proc = subprocess.run([sys.executable, tool, "--task", task_id, "--hash"],
                           cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    if proc.returncode == 0:
        return proc.stdout.strip()
    if art:
        return f"artifact:{art.group(1)}"
    print(f"NO-EVIDENCE {task_id}"); sys.exit(2)

def collapse_phases(text):
    """Any '## Phase ...' heading whose section has zero open cards and only
    struck (~~) card lines gets replaced by one collapsed line."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        if l.startswith('## ') and 'Phase' in l:
            j = i + 1
            while j < len(lines) and not lines[j].startswith('## '):
                j += 1
            section = lines[i + 1:j]
            strikes = [s for s in section if s.lstrip().startswith('~~')]
            has_open = any(CARD_ANY_RE.match(s) for s in section)
            if not has_open and strikes:
                title = l[3:].strip()
                out.append(f"## ~~{title}~~ ✅ complete "
                           f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} · "
                           f"{len(strikes)} cards · .done.md")
                i = j; continue
        out.append(l); i += 1
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser(description="Retire one plan task after re-running its Verify.")
    ap.add_argument("plan"); ap.add_argument("task_id"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.plan):
        cannot_read(f"plan does not exist: {a.plan}")
    try:
        with open(a.plan, encoding="utf-8") as fh:
            orig_text = fh.read()
    except Exception as e:
        cannot_read(f"plan unreadable ({e.__class__.__name__}: {e}): {a.plan}")
    lines = orig_text.split("\n")

    header_i, end_i = find_block(lines, a.task_id)
    block = lines[header_i:end_i]
    receipts = check_verify(block, a.task_id)
    evidence = get_evidence(block, a.task_id)

    if a.dry_run:
        print(f"WOULD-RETIRE {a.task_id} hash={evidence}"); sys.exit(0)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = f"{a.plan}.pre-retire.{ts}.bak"
    shutil.copy2(a.plan, backup)

    indent = re.match(r'^(\s*)', lines[header_i]).group(1)
    strike = f"{indent}~~{a.task_id}~~ ✅ {date} · {evidence} · .done.md"
    new_lines = lines[:header_i] + [strike] + lines[end_i:]
    new_text = collapse_phases("\n".join(new_lines))

    done_path = re.sub(r'\.md$', '.done.md', a.plan)
    done_before = ""
    if os.path.exists(done_path):
        with open(done_path, encoding="utf-8") as fh:
            done_before = fh.read()
    receipt_block = "\n".join(f"$ {c}\nrc={rc}\n{out[:2000]}" for c, rc, out in receipts)
    entry = (f"\n## {a.task_id} — retired {now_iso()}\n"
             + "\n".join(block) + "\n\n"
             f"verified-by: plan_retire.py {now_iso()}\n```\n{receipt_block}\n```\n")
    done_after = done_before + entry

    before_open, before_done = len(CARD_ANY_RE.findall(orig_text)), len(DONE_HEAD_RE.findall(done_before))
    after_open, after_done = len(CARD_ANY_RE.findall(new_text)), len(DONE_HEAD_RE.findall(done_after))
    if after_open != before_open - 1 or after_done != before_done + 1:
        shutil.copy2(backup, a.plan)
        print("COUNT-MISMATCH"); sys.exit(2)

    with open(a.plan, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    with open(done_path, "w", encoding="utf-8") as fh:
        fh.write(done_after)

    print(f"RETIRED {a.task_id} hash={evidence}"); sys.exit(0)

if __name__ == "__main__":
    main()
