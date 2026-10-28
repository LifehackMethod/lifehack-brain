#!/usr/bin/env python3
"""plan_queue — turn a plan's OPEN cards into a work queue, and flag WEAK Verify lines first.

LLM CONTEXT
WHY: the /build runner needs the plan as data (id, Where, Do, Verify, Done, checkpoint flag,
  declared exceptions) in file order. A Verify that tests presence, hides errors, is prose, or
  counts a substring of its own negation (`grep -c "MATCH"` also counts MISMATCH) passes while
  proving nothing -- so those are named BEFORE anything runs.
GUARDS: card grammar and Verify parsing come from system/tools/verify_parse.py (imported, never
  copied). Card count must equal plan_lint.py's on the same plan (--selftest checks it on the
  real build-skill plan). Reads the plan only; writes nothing.
FAIL_POSTURE: never exit 0 on error. 0 ok (WEAK lines are warnings, not errors) | 1 a card is
  malformed (unrecognised id, no Where/Verify, unparseable Verify) | 2 usage | 4 could-not-read.
SIGNPOST: checkpoint marker -- the plan grammar/plan_lint/verify_parse define none, so a card is a
  checkpoint if `Owner:` is ENVER or HUMAN (or contains CHECKPOINT), or its header line / a
  `Kind:`/`Type:` slot / a standalone `checkpoint` backtick token says so. Prose in Do: that merely
  MENTIONS checkpoints does not count. Exceptions: `exception: <RULE-ID> because <reason>` lines.

Usage: plan_queue.py <plan.md> [--json]     plan_queue.py --selftest
"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "system", "tools"))
sys.path.insert(0, TOOLS)
import verify_parse as vp  # noqa: E402

SLOT_RE = re.compile(r'^\s*`?(Owner|Where|Repo|Do|Verify|Done|Commit|Query|Proof|Kind|Type):\s*(.*?)`?\s*$')
TITLE_RE = re.compile(r'^- \[ \] \*\*(' + vp.ID + r')\s+(.*?)\*\*')
EXC_RE = re.compile(r'\bexception:\s*([A-Z]+-?\d+|[\w.-]+)\s+because\s+(.+?)\s*`?\s*$')
CP_OWNERS = ("ENVER", "HUMAN", "CHECKPOINT")


def die(code, msg):
    print(msg, file=sys.stderr)
    sys.exit(code)


def parse_plan(path):
    """Return (cards, malformed). Open cards only, file order."""
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except Exception as e:
        die(4, f"CANNOT-READ {path}: {e}")
    cards, bad, cur = [], [], None
    for i, l in enumerate(lines, 1):
        m = vp.CARD_ID_RE.match(l)
        if m:
            t = TITLE_RE.match(l)
            cur = {"id": m.group(1), "line": i, "title": t.group(2).strip() if t else "",
                   "header": l, "text": [], "slots": {}}
            cards.append(cur)
            continue
        if vp.BARE_CARD_RE.match(l):
            bad.append((i, f"card header id not recognised: {l.strip()[:80]}"))
            cur = None
            continue
        if l.startswith("- [") or l.startswith("## ") or l.startswith("---"):
            cur = None
            continue
        if cur is not None:
            cur["text"].append(l)
    for c in cards:
        om = re.search(r'`Owner:\s*([^`]+)`', c["header"])
        if om:
            c["slots"]["Owner"] = om.group(1).strip()
        for l in c["text"]:
            sm = SLOT_RE.match(l)
            if sm:
                c["slots"].setdefault(sm.group(1), sm.group(2))
                if sm.group(1) == "Verify":
                    c["slots"]["_verify_line"] = l.strip()
    return cards, bad


def is_checkpoint(c):
    owner = c["slots"].get("Owner", "").upper()
    if any(k in owner for k in CP_OWNERS):
        return True
    if re.search(r'\bcheckpoint\b', c["header"], re.I):
        return True
    if re.search(r'^(checkpoint)', c["slots"].get("Kind", "") + c["slots"].get("Type", ""), re.I):
        return True
    return any(re.match(r'^\s*`checkpoint`\s*$', l, re.I) for l in c["text"])


def exceptions(c):
    out = []
    for l in c["text"]:
        m = EXC_RE.search(l)
        if m:
            out.append({"rule": m.group(1), "because": m.group(2).strip()})
    return out


# ---- weak-Verify heuristics -------------------------------------------------
SUBSTR_PAT_RE = re.compile(r'grep\s+(?:-[a-zA-Z]*c[a-zA-Z]*)\s+(?:-[a-zA-Z]+\s+)*"([A-Za-z]+)(\$?)"')
# a bare word that is a suffix of a plausible negation (MATCH <- MISMATCH/UNMATCHED...)
NEGATABLE = {"MATCH", "MATCHED", "PASS", "PASSED", "OK"}


def _segments(cmd):
    return [s.strip() for s in cmd.split("|")]


def weak_reasons(vline, pairs):
    r = []
    low = vline.lower()
    if re.search(r'<[^<>\s][^<>]*>|\bTODO\b|\bTBD\b', vline):
        r.append("placeholder (<...>/TODO/TBD) in Verify")
    if pairs is None:
        r.append("prose-only Verify (no RUN command)")
        return r
    if re.search(r'\bJUDGE\b', vline):
        r.append("presence-only (JUDGE lowers to test -s on the artifact)")
    if re.search(r'non-?empty|not empty', low):
        r.append("presence-only (non-empty check)")
    for cmd, _exp in pairs:
        segs = _segments(cmd)
        first = segs[0]
        if re.match(r'^(test|\[)\s+-[sfe]\b', first) and len(segs) == 1 and "JUDGE" not in vline:
            r.append("presence-only (test/[ -s|-f|-e)")
        if re.match(r'^test\s+-n\b|^\[\s+-n\b', first):
            r.append("presence-only (non-empty test)")
        if re.match(r'^ls\b', first) and len(segs) == 1:
            r.append("presence-only (ls alone)")
        if any(re.match(r'^wc\s+-l\b', s) for s in segs[1:]) and re.match(r'^(ls|find)\b', first) \
                and not re.search(r'[*?\[]', first) \
                and not any(re.match(r'^(grep|awk|sed)\b', s) for s in segs[1:]):
            r.append("presence-only (wc -l of a listing, no content filter)")
        if "|| true" in cmd:
            r.append("silenced error (|| true)")
        if "2>/dev/null" in cmd:
            r.append("silenced error (2>/dev/null)")
        m = SUBSTR_PAT_RE.search(cmd)
        if m and m.group(1).isupper() and m.group(1) in NEGATABLE | {"MATCH"}:
            r.append(f'count-of-substring trap (grep -c "{m.group(1)}{m.group(2)}" also counts '
                     f'MISMATCH/UNMATCHED-style lines)')
    seen, out = set(), []
    for x in r:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def build_queue(path):
    cards, bad = parse_plan(path)
    if bad:
        for ln, msg in bad:
            print(f"MALFORMED line {ln}: {msg}", file=sys.stderr)
    if not cards and not bad:
        die(4, f"CANNOT-READ no open `- [ ] **<id>` cards in {path}")
    queue, weak, malformed = [], [], list(bad)
    for c in cards:
        s = c["slots"]
        for need in ("Where", "Do", "Verify", "Done"):
            if need not in s:
                malformed.append((c["line"], f"{c['id']}: missing {need}:"))
        vline = s.get("_verify_line", "")
        pairs, prose = None, False
        if vline:
            try:
                pairs = vp.parse_verify(vline)
            except vp.VerifyParseError as e:
                msg = str(e)
                if "placeholder" in msg and "no runnable" not in msg:
                    pairs = None  # reported as WEAK placeholder below
                elif "no runnable command" in msg or "no command-shaped" in msg:
                    pairs = None
                else:
                    malformed.append((c["line"], f"{c['id']}: unparseable Verify: {msg[:140]}"))
                    continue
        if vline:
            for why in weak_reasons(vline, pairs):
                weak.append((c["id"], why))
        queue.append({
            "id": c["id"], "title": c["title"], "where": s.get("Where", ""), "do": s.get("Do", ""),
            "verify": [{"cmd": a, "expect": b} for a, b in (pairs or [])],
            "done": s.get("Done", ""), "checkpoint": is_checkpoint(c), "exceptions": exceptions(c),
        })
    return queue, weak, malformed


def tsv_clean(x):
    return re.sub(r'[\t\n\r]+', ' ', str(x)).strip()


def run(path, as_json):
    queue, weak, malformed = build_queue(path)
    for cid, why in weak:
        print(f"WEAK {cid} {why}")
    if as_json:
        print(json.dumps({"cards": queue, "weak": [{"id": a, "reason": b} for a, b in weak]}, indent=1))
    else:
        for q in queue:
            v = " && ".join(x["cmd"] for x in q["verify"])
            e = " && ".join(str(x["expect"]) for x in q["verify"])
            ex = ";".join(f"{x['rule']} because {x['because']}" for x in q["exceptions"])
            print("\t".join(tsv_clean(f) for f in (q["id"], q["title"], "CHECKPOINT" if q["checkpoint"] else "-",
                                                  q["where"], q["do"], v, e, q["done"], ex)))
    if malformed:
        for ln, msg in malformed:
            print(f"MALFORMED line {ln}: {msg}", file=sys.stderr)
        return 1
    return 0


# ---- selftest ---------------------------------------------------------------
def card(cid, title, verify, owner="BUILD", extra=()):
    body = [f"- [ ] **{cid} {title}.** `Owner: {owner}` · gear-1",
            "  `Where: ~/x/file.txt`", "  `Do:` make the thing.", "  `Repo: none`", f"  {verify}"]
    body += list(extra)
    body += ["  `Commit: x`", "  `Done: Verify passes → retire`", ""]
    return "\n".join(body)


GOOD = '`Verify: RUN` `grep -c "^ok" "$HOME/x.log"` → `3`'


def selftest():
    results = []

    def check(name, cond):
        results.append(cond)
        print(("PASS " if cond else "FAIL ") + name)

    d = tempfile.mkdtemp(prefix="plan_queue_")
    def mk(name, *cards):
        p = os.path.join(d, name)
        open(p, "w").write("# plan\n\n## Phase 1\n\n" + "\n".join(cards) + "\n")
        return p

    p = mk("a.plan.md",
           card("T1.1", "Clean", GOOD),
           "- [x] **T1.2 Already done.** `Owner: BUILD`\n  `Where: ~/y`\n",
           card("T1.3", "Needs Enver", GOOD, owner="ENVER"),
           card("T1.4", "Has exception", GOOD,
                extra=["  exception: ALW-03 because the fetch is best-effort by design"]),
           card("T1.5", "Prose only", GOOD, extra=["  Do-note: a checkpoint card waits."]))
    q, weak, mal = build_queue(p)
    check("open cards in file order, [x] skipped: " + ",".join(x["id"] for x in q),
          [x["id"] for x in q] == ["T1.1", "T1.3", "T1.4", "T1.5"])
    check("clean card has no WEAK and no malformed", weak == [] and mal == [])
    check("Owner ENVER marks checkpoint", [x["checkpoint"] for x in q] == [False, True, False, False])
    check("exception parsed",
          q[2]["exceptions"] == [{"rule": "ALW-03", "because": "the fetch is best-effort by design"}])
    check("verify parsed via verify_parse", q[0]["verify"] == [{"cmd": 'grep -c "^ok" "$HOME/x.log"',
                                                               "expect": ("bare", 3)}])

    kinds = {
        "test -s": ('`Verify: RUN` `test -s "$HOME/x"; echo $?` → `0`', "presence-only (test/[ -s|-f|-e)"),
        "ls alone": ('`Verify: RUN` `ls "$HOME/x"; echo $?` → `0`', "presence-only (ls alone)"),
        "wc -l listing": ('`Verify: RUN` `ls "$HOME/dir" | wc -l` → `3`',
                          "presence-only (wc -l of a listing, no content filter)"),
        "|| true": ('`Verify: RUN` `grep -c "^ok" "$HOME/x" || true` → `3`', "silenced error (|| true)"),
        "2>/dev/null": ('`Verify: RUN` `grep -c "^ok" "$HOME/x" 2>/dev/null` → `3`',
                        "silenced error (2>/dev/null)"),
        "prose": ('`Verify: RUN` re-read the file and confirm it looks right', "prose-only Verify (no RUN command)"),
        "placeholder": ('`Verify: RUN` `cat <copy>` → `0`', "placeholder (<...>/TODO/TBD) in Verify"),
        "MATCH trap": ('`Verify: RUN` `grep -c "MATCH" "$HOME/x.log"` → `13`',
                       'count-of-substring trap (grep -c "MATCH" also counts MISMATCH/UNMATCHED-style lines)'),
    }
    for i, (k, (v, why)) in enumerate(kinds.items(), 1):
        p = mk(f"w{i}.plan.md", card(f"W{i}.1", k, v))
        q, weak, mal = build_queue(p)
        check(f"WEAK {k}: exact reason", weak == [(f"W{i}.1", why)] or (k == "placeholder" and (f"W{i}.1", why) in weak))
    p = mk("ok.plan.md", card("S1.1", "anchored", '`Verify: RUN` `grep -c "^MATCH" "$HOME/x.log"` → `13`'))
    check("anchored ^MATCH not flagged", build_queue(p)[1] == [])
    p = mk("ls.plan.md", card("S2.1", "glob listing", '`Verify: RUN` `ls -d "$HOME/x/bad-"* | wc -l | tr -d \' \'` → `10`'))
    check("ls with glob filter not flagged", build_queue(p)[1] == [])

    bad = os.path.join(d, "bad.plan.md")
    open(bad, "w").write("- [ ] **!!** broken\n  `Where: ~/x`\n")
    rc = subprocess.run([sys.executable, os.path.abspath(__file__), bad], capture_output=True).returncode
    check("malformed header exits 1", rc == 1)
    rc = subprocess.run([sys.executable, os.path.abspath(__file__), os.path.join(d, "nope")],
                        capture_output=True).returncode
    check("missing file exits 4", rc == 4)
    rc = subprocess.run([sys.executable, os.path.abspath(__file__)], capture_output=True).returncode
    check("no args exits 2", rc == 2)

    # count equals plan_lint's on the real plan
    try:
        root = subprocess.check_output([sys.executable, os.path.join(HERE, "..", "..", "..", "..", "shared",
                                        "brain_root.py"), "--quiet"], text=True).strip()
        real = os.path.join(root, "plans", "build-skill.plan.md")
        import plan_lint
        lint_cards, _ = plan_lint.parse_cards(open(real, encoding="utf-8").read().split("\n"))
        q, weak, mal = build_queue(real)
        check(f"real build-skill plan: card count {len(q)} == plan_lint {len(lint_cards)}",
              len(q) == len(lint_cards) and len(q) > 0)
        wid = sorted({a for a, _ in weak})
        check(f"real plan WEAK ids include BS1.3 and BS3.3 ({wid})", "BS1.3" in wid and "BS3.3" in wid)
    except Exception as e:
        check(f"real-plan comparison ran ({e})", False)
    ok = all(results)
    print(f"SELFTEST {'OK' if ok else 'FAILED'} {sum(results)}/{len(results)}")
    return 0 if ok else 1


def main(argv):
    args = argv[1:]
    if args == ["--selftest"]:
        return selftest()
    as_json = "--json" in args
    rest = [a for a in args if a != "--json"]
    if len(rest) != 1 or rest[0].startswith("-"):
        print("usage: plan_queue.py <plan.md> [--json] | --selftest", file=sys.stderr)
        return 2
    return run(os.path.expanduser(rest[0]), as_json)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
