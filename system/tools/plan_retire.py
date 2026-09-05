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
    NOT-YET <id> gated on <o>   4  a `gated on <o>` on this card's own lines
                                    names a card <o> that is still open
    CANNOT-READ <why>           4  NO-OUTCOME MEMBER -- unreadable/missing plan,
                                    missing card, or no runnable Verify. Never
                                    passes by default.

    2026-09-04: task 2.3 was wrongly RETIRED on this path — an unparsed
    expectation fell through to `ok = (rc == 0)`, and the card's own preferred
    `; echo $?` command shape makes the *shell's* exit code 0 unconditionally.
    Rule since: no parseable expectation => CANNOT-READ, never pass.

    2026-09-05, card 6.2: build order and verify order can differ — a `gated on`
    card retired out of order used to have nothing stopping it. Backups now carry
    the task id and microseconds (second-resolution collided when several retires
    ran within the same second). A Verify amended between attempts is now kept,
    not silently overwritten, in the .done.md receipt. `--dry-run --all` reports
    every open card's state in one pass (canon §5.13).
"""
import argparse, glob, os, re, shutil, subprocess, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_parse import ID, parse_verify, VerifyParseError, BARE_CARD_RE  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CANNOT_READ = 4
CARD_ANY_RE = re.compile(BARE_CARD_RE.pattern, re.M)
DONE_HEAD_RE = re.compile(r'^## ', re.M)
OPEN_HEADER_RE = re.compile(r'^\s*- \[ \] \*\*(' + ID + r')\b')
GATE_LINE_RE = re.compile(r'gated on\b(.*)$', re.I)


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
    # 2026-09-05, card 6.10: `.split()[0]` here truncated the value at its FIRST
    # SPACE -- the identical whitespace-truncation bug 6.7 fixed in get_evidence()
    # four lines away. Every notes path on this machine sits under Google Drive's
    # `My Drive`, so any card whose Where: names such a path silently ran its
    # Verify from REPO_ROOT instead -- no error, just the wrong directory. The
    # regex above already captures the WHOLE value up to the next backtick or
    # newline; only strip the ` · ...` suffix and surrounding whitespace, never
    # split on internal spaces.
    first = m.group(1).split("·")[0].strip().strip("`")
    p = os.path.expanduser(first)
    if not os.path.isabs(p):
        return REPO_ROOT
    if os.path.isdir(p):
        return p
    d = os.path.dirname(p)
    return d if os.path.isdir(d) else REPO_ROOT


def _block_in_text(text, task_id):
    """Like find_block, but non-exiting and against an arbitrary text blob (a
    backup file, or the live plan when scanning --all) -- returns the card's own
    lines, or None if that id has no open card header in this text at all."""
    lines = text.split("\n")
    header_re = re.compile(r'^(\s*)- \[ \] \*\*' + re.escape(task_id) + r'\b')
    for i, l in enumerate(lines):
        if header_re.match(l):
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if CARD_ANY_RE.match(lines[j]) or lines[j].startswith('## ') or lines[j].rstrip() == '---':
                    end = j; break
            return lines[i:end]
    return None


def _card_is_open(full_text, task_id):
    """True only if <task_id> still has an open `- [ ] **id**` header in this
    plan text. A retired (`~~id~~`) or wholly-absent id is never treated as
    gating -- gate on what is verifiably still open, never on a guess."""
    return bool(re.search(r'^\s*- \[ \] \*\*' + re.escape(task_id) + r'\b', full_text, re.M))


def _gate_refs(block_text, self_id):
    """Task ids named after a `gated on` phrase written on THIS card's own lines
    (its body, or a PARALLEL-LANES note living inside the card block itself),
    self excluded, de-duplicated in order.

    WHAT THIS DOES NOT CATCH, stated plainly rather than overclaimed: a
    phase-level `**PARALLEL LANES:**` line living under the `## Phase` heading,
    outside any single card's own block, is never scanned here -- a gate stated
    only at the phase level and not echoed on the gated card's own lines is
    invisible to this check. Likewise a gate named in prose with no id-shaped
    token (`gated on the migration finishing`) yields nothing to check against
    -- there is no card to look up. Only an id matching the shared `ID` shape,
    written on the card's own lines, is ever honoured.
    """
    ids = []
    for l in block_text.split("\n"):
        m = GATE_LINE_RE.search(l)
        if not m:
            continue
        for idm in re.finditer(ID, m.group(1)):
            tid = idm.group(0)
            if tid != self_id and tid not in ids:
                ids.append(tid)
    return ids


def check_gates(block_lines, full_text, task_id):
    """Before this card's Verify ever runs: if a `gated on <other>` written on
    its own lines names a card that is STILL OPEN, this card is not retireable
    yet, no matter what its own Verify would say -- build order and verify
    order are not the same order (2026-09-05, card 6.2)."""
    block_text = "\n".join(block_lines)
    for other in _gate_refs(block_text, task_id):
        if _card_is_open(full_text, other):
            print(f"NOT-YET {task_id} gated on {other}"); sys.exit(CANNOT_READ)


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

def _resolve_script(cmd):
    """A card names its own tool bare (`plan_lint.py args`), meaning 'run the tool
    that lives in this card's own directory' — but shell=True/cwd does not put cwd
    on PATH, so bash reports 'command not found' (rc=127) for a real, executable
    file sitting right there.

    2026-09-05, coordinator catch on card 6.2 itself: the earlier fix rewrote a
    bare leading token to `./<script>.py` — but none of these tools carry the
    exec bit (mode `-rw-r--r--` throughout this tree, by default, always), so
    `./x.py` fails with rc=126 (permission denied), not the honest "no such
    file". That 126 then got compared against whatever number the card's own
    Verify expected and scored a confident, WRONG VERIFY-FAILED — the exact
    disease 6.1 fixed one layer up: an unrecognised form producing a wrong
    answer instead of a loud refusal. Every one of these cards' own tools is
    invoked as `python3 <script>.py` everywhere else in the plan and needs no
    file-mode change, so that is the rewrite: `python3 <script>.py`, never
    `./<script>.py`. A command that already carries a path (`./x.py`,
    `system/tools/x.py`) is left alone -- rewriting only the bare form.
    """
    m = re.match(r'^([\w.-]+\.py)(\s|$)', cmd)
    if m and "/" not in m.group(1):
        return "python3 " + cmd
    return cmd

def run_cmd(cmd, cwd=None):
    return subprocess.run(_resolve_script(cmd), shell=True, cwd=cwd or REPO_ROOT,
                           capture_output=True, text=True, timeout=120,
                           stdin=subprocess.DEVNULL)


def _eval_expectation(exp, rc, out):
    """The one comparison used for every clause of a parsed Verify: shared by
    the full-detail single-task path and the terse --all scan, so the two never
    silently drift apart on what counts as a pass."""
    if exp[0] == 'exit':
        return rc == exp[1]
    if exp[0] == 'bare':
        # Compare the LAST non-empty line of stdout, not the whole of it: a
        # `cmd; echo $?` on a command that prints its own output (pytest -q,
        # grep with matches, etc) is multi-line, and `; echo $?` only ever
        # adds ONE more line at the end (2026-09-05, card 6.1). Comparing the
        # full strip() failed every chatty command even when its own printed
        # exit code was exactly right.
        nonempty = [ln for ln in out.splitlines() if ln.strip() != '']
        last = nonempty[-1].strip() if nonempty else ''
        if last == str(exp[1]):
            return True
        if last == '' and 0 <= exp[1] <= 255:
            # no stdout at all (e.g. `test -f x` with no `; echo $?`) -> the
            # stated number is the command's exit code, not printed text.
            return rc == exp[1]
        return False
    if exp[0] == 'ge':
        return out.strip().lstrip('-').isdigit() and int(out.strip()) >= exp[1]
    if exp[0] == 'le':
        return out.strip().lstrip('-').isdigit() and int(out.strip()) <= exp[1]
    if exp[0] == 'substr':
        return exp[1] in out
    return False


def _verify_line_text(block_lines):
    l = next((x for x in block_lines if re.match(r'^\s*`?Verify:', x)), None)
    return l.strip() if l else None


def check_verify(block_lines, task_id):
    """Run every command on the card's Verify line; return receipts on full
    pass, or print VERIFY-FAILED and exit 2 on any miss.

    2026-09-04: an unparseable expectation (exp is None) is CANNOT-READ, never a
    pass. This is checked for EVERY command before any of them are run, so a
    card with one unreadable expectation moves nothing. Fixed after task 2.3
    was wrongly retired: its unparsed `→ `0`` fell through to `ok = (rc == 0)`,
    and the card's own preferred `; echo $?` shape makes the shell's own exit
    code 0 unconditionally — an unreachable check is not a clean result.

    2026-09-05: parsing itself now comes from the shared verify_parse module and
    can raise VerifyParseError — a dropped ` · ` clause, an unsubstituted
    `<placeholder>`, or no runnable command at all. Any of those is CANNOT-READ,
    same as an unparseable expectation; never a partial run on the clauses that
    happened to parse (card 6.1).
    """
    verify_line = _verify_line_text(block_lines)
    if verify_line is None:
        cannot_read(f"no Verify: line on {task_id}")
    try:
        cmds = parse_verify(verify_line)
    except VerifyParseError as e:
        cannot_read(f"Verify unparseable for {task_id}: {e}")
    for cmd, exp in cmds:
        if exp is None:
            cannot_read(f"no parseable expectation for {task_id}: {cmd}")
    cwd = _verify_cwd("\n".join(block_lines))
    receipts, failures = [], []
    for cmd, exp in cmds:
        proc = run_cmd(cmd, cwd)
        rc, out = proc.returncode, proc.stdout
        receipts.append((cmd, rc, out))
        if not _eval_expectation(exp, rc, out):
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
    """The `artifact:` value on a card's own lines, whole -- not the first word of it.

    2026-09-05, card 6.7: `\\S+` split the real value (a notes path) at its first space,
    since every notes path on this machine sits under Google Drive's `My Drive`. The
    truncated pointer parsed as valid and pointed at nothing (SOP V.4d). A card writes
    its artifact value inside one backtick pair -- `` `artifact: /path with spaces/x` ``
    (see e.g. card 6.6's own `Repo:`/`artifact:` line) -- so the value runs from just
    after the `artifact:` label to the NEXT backtick, not to the next space. Recorded
    back out backtick-quoted (`artifact:`<value>``) so it round-trips through the same
    convention rather than being ambiguous prose again.
    """
    art = re.search(r'artifact:\s*([^`\n]+)', '\n'.join(block_lines), re.I)
    tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_git_check.py")
    proc = subprocess.run([sys.executable, tool, "--task", task_id, "--hash"],
                           cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
    if proc.returncode == 0:
        return proc.stdout.strip()
    if art:
        return f"artifact:`{art.group(1).strip()}`"
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


def _scan_one(orig_text, task_id):
    """--all: the terse, non-exiting per-card check used to report every open
    card's state in one pass -- never runs a card's Verify commands out of
    order relative to another card's, never writes anything, never raises."""
    if re.search(r'^~~' + re.escape(task_id) + r'~~', orig_text, re.M):
        return f"{task_id}: ALREADY-RETIRED"
    block = _block_in_text(orig_text, task_id)
    if block is None:
        return f"{task_id}: CANNOT-READ (card not found)"
    for other in _gate_refs("\n".join(block), task_id):
        if _card_is_open(orig_text, other):
            return f"{task_id}: NOT-YET gated on {other}"
    verify_line = _verify_line_text(block)
    if verify_line is None:
        return f"{task_id}: CANNOT-READ (no Verify: line)"
    try:
        cmds = parse_verify(verify_line)
    except VerifyParseError as e:
        return f"{task_id}: CANNOT-READ (Verify unparseable: {e})"
    for cmd, exp in cmds:
        if exp is None:
            return f"{task_id}: CANNOT-READ (no parseable expectation: {cmd})"
    cwd = _verify_cwd("\n".join(block))
    for cmd, exp in cmds:
        proc = run_cmd(cmd, cwd)
        if not _eval_expectation(exp, proc.returncode, proc.stdout):
            return f"{task_id}: VERIFY-FAILED ({cmd})"
    return f"{task_id}: WOULD-RETIRE"


DONE_ENTRY_RE = re.compile(r'^## (' + ID + r') — retired ', re.M)


def _done_entries(done_text):
    """Yield (task_id, card_lines) for every retired entry in `.done.md` -- the
    embedded card block exactly as it stood the moment it was retired (its own
    `Where:`/`Verify:` lines included), so re-running it re-checks the SAME claim
    that was made at retirement, never a hypothetical new one. Stops each block
    at the `verified-by:` line the retirer itself writes -- everything after that
    is the receipt, not the card.

    2026-09-05, card 6.10: this defect has fired three times in one day (6.4 vs
    4.4, 6.3 vs 6.4, 6.8 vs 6.4) because a card's own Verify passing at ITS OWN
    retirement was never treated as a claim that could go stale. `.done.md` is
    the ledger of every such claim; this is what re-checks them.
    """
    lines = done_text.split("\n")
    heads = [(i, m.group(1)) for i, m in
             ((i, DONE_ENTRY_RE.match(l)) for i, l in enumerate(lines)) if m]
    for idx, (i, tid) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        section = lines[i + 1:end]
        header_re = re.compile(r'^(\s*)- \[ \] \*\*' + re.escape(tid) + r'\b')
        start = next((j for j, l in enumerate(section) if header_re.match(l)), None)
        if start is None:
            continue
        stop = next((j for j in range(start + 1, len(section))
                     if section[j].strip().startswith('verified-by:')), len(section))
        yield tid, section[start:stop]


def _regression_scan(plan_path):
    """Re-run every retired card's own Verify, exactly as check_verify() would for
    a live card, and report the ones that passed at retirement (they are IN
    `.done.md` at all only because they did) and fail now. Never writes anything,
    never touches the live plan or `.done.md`. A card whose receipt can no longer
    even be parsed or run (a stale scratch fixture, a since-deleted artifact) is
    reported as UNCHECKED, not silently folded into REGRESSION -- an unrunnable
    claim and a claim that ran and failed are different findings (SOP honesty
    rule: report what each verdict actually means).
    """
    done_path = re.sub(r'\.md$', '.done.md', plan_path)
    if not os.path.exists(done_path):
        return []
    with open(done_path, encoding="utf-8") as fh:
        done_text = fh.read()
    findings = []
    for tid, card in _done_entries(done_text):
        verify_line = _verify_line_text(card)
        if verify_line is None:
            findings.append((tid, "UNCHECKED", "no Verify: line in receipt")); continue
        try:
            cmds = parse_verify(verify_line)
        except VerifyParseError as e:
            findings.append((tid, "UNCHECKED", f"Verify unparseable: {e}")); continue
        unreadable = next((cmd for cmd, exp in cmds if exp is None), None)
        if unreadable is not None:
            findings.append((tid, "UNCHECKED", f"no parseable expectation: {unreadable}")); continue
        cwd = _verify_cwd("\n".join(card))
        broke = None
        for cmd, exp in cmds:
            proc = run_cmd(cmd, cwd)
            if not _eval_expectation(exp, proc.returncode, proc.stdout):
                broke = (cmd, exp, proc.returncode, proc.stdout); break
        if broke is not None:
            cmd, exp, rc, out = broke
            findings.append((tid, "REGRESSION",
                              f"cmd: {cmd} | expected: {exp} | got rc={rc} stdout={out[:200]!r}"))
    return findings


def _open_ids(lines):
    ids = []
    for l in lines:
        m = OPEN_HEADER_RE.match(l)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def _prior_backup_verify(plan_path, task_id, current_backup_basename):
    """The most recent existing backup for THIS task id (strictly older than
    the run in progress), and that backup's own copy of this card's Verify:
    line -- None, None if no prior backup exists, or the card is not present
    in it. Used to detect a Verify: amended between retire attempts (card 6.2,
    part d) — the correction is the valuable part, and it is lost the moment a
    new backup silently overwrites an old one without anyone comparing them.
    """
    pattern = f"{plan_path}.pre-retire.{task_id}.*.bak"
    matches = sorted(m for m in glob.glob(pattern)
                      if os.path.basename(m) < current_backup_basename)
    if not matches:
        return None, None
    latest = matches[-1]
    try:
        with open(latest, encoding="utf-8") as fh:
            old_text = fh.read()
    except OSError:
        return latest, None
    old_block = _block_in_text(old_text, task_id)
    if old_block is None:
        return latest, None
    return latest, _verify_line_text(old_block)


def main():
    ap = argparse.ArgumentParser(description="Retire one plan task after re-running its Verify.")
    ap.add_argument("plan")
    ap.add_argument("task_id", nargs="?", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true",
                     help="report every open card's state in one pass; report-only, requires --dry-run")
    ap.add_argument("--regressions", action="store_true",
                     help="re-run every .done.md card's own Verify; report any that "
                          "passed at retirement and fails now. report-only, requires --dry-run")
    a = ap.parse_args()

    if not os.path.exists(a.plan):
        cannot_read(f"plan does not exist: {a.plan}")
    try:
        with open(a.plan, encoding="utf-8") as fh:
            orig_text = fh.read()
    except Exception as e:
        cannot_read(f"plan unreadable ({e.__class__.__name__}: {e}): {a.plan}")
    lines = orig_text.split("\n")

    if a.regressions:
        if not a.dry_run:
            cannot_read("--regressions is report-only; pass --dry-run")
        findings = _regression_scan(a.plan)
        for tid, kind, detail in findings:
            print(f"{kind} {tid}: {detail}")
        sys.exit(1 if any(kind == "REGRESSION" for _, kind, _ in findings) else 0)

    if a.all:
        if not a.dry_run:
            cannot_read("--all is report-only; pass --dry-run")
        for tid in _open_ids(lines):
            print(_scan_one(orig_text, tid))
        # 2026-09-05, card 6.10: fold the regression gate into the every-run guard
        # so a future plan gets it free -- --all already reports every open card's
        # state in one pass; a retired card's claim going stale is the same kind of
        # thing, checked the same run.
        for tid, kind, detail in _regression_scan(a.plan):
            print(f"{kind} {tid}: {detail}")
        sys.exit(0)

    if a.task_id is None:
        cannot_read("no task_id given (or pass --all for a report of every open card)")

    header_i, end_i = find_block(lines, a.task_id)
    block = lines[header_i:end_i]
    check_gates(block, orig_text, a.task_id)
    receipts = check_verify(block, a.task_id)
    evidence = get_evidence(block, a.task_id)

    if a.dry_run:
        print(f"WOULD-RETIRE {a.task_id} hash={evidence}"); sys.exit(0)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # 2026-09-05, card 6.2 (c): second-resolution + no task id let eight retires
    # in two seconds overwrite each other's backups. Microseconds + the task id
    # make each backup filename unique to this task and this instant.
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = f"{a.plan}.pre-retire.{a.task_id}.{ts}.bak"

    prior_backup, prior_verify = _prior_backup_verify(a.plan, a.task_id, os.path.basename(backup))
    current_verify = _verify_line_text(block)

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
    amended = ""
    if prior_verify is not None and current_verify is not None and prior_verify != current_verify:
        # 2026-09-05, card 6.2 (d): the Verify: changed since the last time this
        # card was attempted -- that correction is the valuable part, so both
        # versions go in the receipt rather than the old one being silently lost.
        amended = (f"\namended-before-passing:\n"
                   f"  prior ({os.path.basename(prior_backup)}): {prior_verify}\n"
                   f"  final: {current_verify}\n")
    entry = (f"\n## {a.task_id} — retired {now_iso()}\n"
             + "\n".join(block) + "\n\n"
             f"verified-by: plan_retire.py {now_iso()}\n"
             f"{amended}```\n{receipt_block}\n```\n")
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
