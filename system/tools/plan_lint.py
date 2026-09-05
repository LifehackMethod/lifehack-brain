#!/usr/bin/env python3
"""plan_lint — the draft gate. A plan is not shown until every task is a complete card.

WHY (2026-09-04): a plan that enumerated GitHub issues became a second tracker and lied for
three weeks (Bekim, 2026-09-01). Agents cite stale text and act on it. So: a plan never holds
what something else can tell you — and this checker refuses a plan that tries.

WHAT — for every `- [ ] **<id>` card:
  Owner:   present
  Where:   a path
  Repo:    RE-DERIVED from Where: + the map in ~/.claude/CLAUDE.md, must match the card's kind
           (public | private | none). Branch, if named, must match the live checkout at that path.
  Do:      present. The CARD contains NO `#NNN` issue/PR number outside Query:/Proof: (the two-tracker failure)
  Verify:  typed SHAPE|RUN|JUDGE; SHAPE names a `before`; the Verify: line itself must parse,
           via the shared verify_parse.parse_verify(), into (command, expectation) pairs —
           a dropped clause, an unsubstituted `<placeholder>`, or a prose-only Verify is a defect
  card id: every `- [ ] **` header's id must match the shared ID pattern, or it is a defect
           (2026-09-05: ids shaped like `3b.1` were silently invisible to the old pattern —
           a card can vanish from the plan's own read of itself with nothing said)
  Done:    present
  Commit:  present unless Repo is none
  Query:   if present, a `Proof:` line follows (a zero result is UNKNOWN until proven well-formed)
  gates:   every "gated on" (any case) names a file path
  gear-2+: names a model
  plan:    has a `Review:` line; a `six-lens` Review: names an `artifact:` path that EXISTS on disk
           (2026-09-05, card 6.3: a claim next to a thing is read as the thing -- SOP V.4d -- so
           the swarm's receipt is checked, not just asserted). `SKIPPED <date> <reason>` names no
           artifact and is not checked here.

--self — the every-run guards: fixtures/broken.plan.md must FAIL (a known-bad plan coming back
clean means the checker is dead); SKILL.md must not exceed fixtures/.budget (the ratchet).

VERDICTS  0 clean · 2 defects (one line each, task id first) · 4 CANNOT-READ (the no-outcome member)
"""
import os, re, subprocess, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_parse import ID, BARE_CARD_RE, parse_verify, VerifyParseError  # noqa: E402

CANNOT_READ = 4
CARD_RE = re.compile(r'^- \[ \] \*\*(' + ID + r')\b')
SLOT_RE = re.compile(r'^\s*`?(Owner|Where|Repo|Do|Verify|Done|Commit|Query|Proof):\s*(.*?)`?\s*$')
ISSUE_RE = re.compile(r'(?<![\w/`])#\d{1,5}\b(?!`)')
GATE_RE = re.compile(r'gated on\b', re.I)
GEAR_RE = re.compile(r'gear-([2-4])')
MODEL_RE = re.compile(r'\b(sonnet|opus|haiku)\b', re.I)
PATHISH = re.compile(r'[\w~./-]+\.(md|py|sh|json|key|txt|yaml)|/')

def cannot_read(why):
    print(f"CANNOT-READ\n  {why}"); sys.exit(CANNOT_READ)

def load_map():
    """Rows of the operator's repo map: [(abs_path, kind)]. No file or no rows → []."""
    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    p = os.path.join(cfg, "CLAUDE.md")
    if not os.path.exists(p): return []
    rows = []
    for line in open(p, encoding="utf-8"):
        m = re.search(r'`(~[^`]+|/[^`]+)`.*?\b(private|public)\b', line, re.I)
        if m and line.lstrip().startswith("|"):
            rows.append((os.path.realpath(os.path.expanduser(m.group(1))), m.group(2).lower()))
    return rows

def split_where(where):
    """A `Where:` value may legitimately hold SEVERAL paths, separated by ' · ' -- splitting on
    that separator is correct. Splitting on whitespace is not: a single path (a Google-Drive-style
    mount, say) can itself contain a space, and 6.7/6.12 are the same truncation bug hitting a
    third and fourth site. Never call .split() on a raw Where: value again -- call this."""
    return [p.strip() for p in where.split(" · ") if p.strip()] if where else []

def derive_kind(where, rows):
    for raw in split_where(where):
        w = os.path.realpath(os.path.expanduser(raw))
        for path, kind in rows:
            if w == path or w.startswith(path + os.sep): return kind, path
    return "none", None

REVIEW_LINE_START = ("> **Review:**", "Review:", "**Review:**")
REVIEW_CONTENT_RE = re.compile(r'\*\*Review:\*\*\s*(.*)$')
ARTIFACT_RE = re.compile(r'\bartifact:\s*(?:`([^`]+)`|(.+))', re.I)

def notes_root():
    """The person's own notes root, resolved the same way system/tools/journal.py does
    (shared/brain_root.py, THIS FILE's own position -- never cwd). None if unset; this
    file never hardcodes a personal path, since it ships in the public repo."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.normpath(os.path.join(here, "..", ".."))
    sys.path.insert(0, os.path.join(repo, "shared"))
    try:
        import brain_root
    except ImportError:
        return None
    return brain_root.resolve_brain_root()[1]

def resolve_artifact_path(raw):
    """An artifact: value in a `Review:` line. `<notes>/...` or `$DATA/...` (both names for the
    same thing -- Step 5.5 already uses `$DATA` on a lens spawn) resolve against notes_root();
    anything else (an absolute path, or `~/...`) is used as written -- this is also what lets a
    scratch fixture's literal `/nonexistent.json` be checked without a notes root at all."""
    for prefix in ("<notes>", "$DATA"):
        if raw.startswith(prefix):
            root = notes_root()
            if root is None: return None
            rest = raw[len(prefix):].lstrip("/")
            return os.path.join(root, rest)
    return os.path.expanduser(raw)

def live_branch(path):
    try:
        r = subprocess.run(["git", "-C", path, "branch", "--show-current"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def parse_cards(lines):
    """Return (cards, unrecognised) where `unrecognised` is [(lineno, text), ...] for
    every `- [ ] **` header whose id the ID pattern could not match — surface (b),
    2026-09-05: those lines used to just fail CARD_RE and vanish from `cards` with
    nothing said, so a plan could read PLAN-CLEAN while carrying dropped cards."""
    cards, cur, unrecognised = [], None, []
    for i, l in enumerate(lines, 1):
        m = CARD_RE.match(l)
        if m:
            cur = {"id": m.group(1), "line": i, "text": [l], "slots": {}}
            cards.append(cur); continue
        if BARE_CARD_RE.match(l):
            unrecognised.append((i, l.strip()))
            cur = None; continue
        if cur is None: continue
        if l.startswith("- [ ]") or l.startswith("## ") or l.startswith("---"):
            cur = None; continue
        cur["text"].append(l)
    for c in cards:
        for l in c["text"]:
            sm = SLOT_RE.match(l)
            if sm: c["slots"].setdefault(sm.group(1), sm.group(2))
            om = re.search(r'`Owner:\s*([^`]+)`', l)      # Owner often sits on the header line
            if om: c["slots"].setdefault("Owner", om.group(1))
    return cards, unrecognised

def lint(path, rows):
    if not os.path.exists(path): cannot_read(f"plan does not exist: {path}")
    try: lines = open(path, encoding="utf-8").read().split("\n")
    except Exception as e: cannot_read(f"plan unreadable ({e}): {path}")
    defects = []
    review_line = next((l for l in lines if l.strip().startswith(REVIEW_LINE_START)), None)
    if review_line is None:
        defects.append(("plan", "no `Review:` line (reviewed or SKIPPED — either way it must say)"))
    else:
        rm = REVIEW_CONTENT_RE.search(review_line)
        content = rm.group(1) if rm else re.sub(r'^\s*>?\s*Review:\s*', '', review_line.strip())
        if re.match(r'\s*six-lens\b', content, re.I):
            am = ARTIFACT_RE.search(content)
            if not am:
                defects.append(("plan", "`Review:` line is `six-lens` but names no `artifact:` "
                                 "path — a claim next to a thing is read as the thing (SOP V.4d); "
                                 "point at the swarm's receipt or write `Review: SKIPPED <date> "
                                 "<reason>` instead"))
            else:
                raw_path = (am.group(1) or am.group(2)).rstrip('.,;:)')
                resolved = resolve_artifact_path(raw_path)
                if resolved is None:
                    defects.append(("plan", f"`Review:` artifact `{raw_path}` uses <notes>/$DATA "
                                     f"but no notes root is set (shared/brain_root.py) — cannot "
                                     f"confirm it exists"))
                elif not os.path.exists(resolved):
                    defects.append(("plan", f"`Review:` artifact does not exist: {raw_path}"))
    cards, unrecognised = parse_cards(lines)
    if not cards: cannot_read(f"no `- [ ] **<id>` cards found in {path}")
    for lineno, text in unrecognised:
        defects.append((f"line {lineno}", f"`- [ ] **` card header id not recognised by the "
                         f"ID pattern (`{ID}`) — silently dropping this line would let the plan "
                         f"read PLAN-CLEAN with a card missing: {text[:100]!r}"))
    for c in cards:
        s, tid, body = c["slots"], c["id"], "\n".join(c["text"])
        for req in ("Owner", "Where", "Do", "Verify", "Done"):
            if req not in s: defects.append((tid, f"missing `{req}:`"))
        kind, mpath = derive_kind(s.get("Where", ""), rows)
        repo = s.get("Repo", "")
        if not repo: defects.append((tid, "missing `Repo:` (derive it: Where: → map)"))
        else:
            rl = repo.lower()
            if rl.startswith("none"): said = "none"
            elif "public" in rl: said = "public"
            elif "private" in rl: said = "private"
            else:
                # a path-form Repo: (e.g. `~/lifehack-brain`) — derive its kind the same way Where: is
                said, _ = derive_kind(repo, rows)
                said = said if said != "none" else "?"
            if said != kind: defects.append((tid, f"`Repo:` says {said} but Where: derives {kind} from the map"))
            bm = re.search(r'\b(V2|v2|main)\b', repo)
            if bm and mpath:
                lb = live_branch(mpath)
                if lb and lb.lower() != bm.group(1).lower(): defects.append((tid, f"`Repo:` names branch {bm.group(1)} but {mpath} is on {lb}"))
        if kind != "none":
            cm = s.get("Commit", "")
            if not cm: defects.append((tid, "missing `Commit:` on a repo task"))
            elif cm.strip().lower() in ("n/a", "na", "none", "-"): defects.append((tid, "`Commit: n/a` on a repo task — a file in a repo gets committed, or Where: is wrong"))
            elif not cm.strip().startswith(tid + ":"): defects.append((tid, f"`Commit:` subject does not start with `{tid}:` — plan_git_check finds the hash by that prefix"))
        card_prose = "\n".join(l for l in c["text"] if not re.match(r'\s*`?(Query|Proof):', l))
        if ISSUE_RE.search(card_prose): defects.append((tid, "card enumerates an issue/PR number — point at the query instead"))
        v = s.get("Verify", "")
        if v and not re.match(r'\s*(SHAPE|RUN|JUDGE)\b', v): defects.append((tid, "`Verify:` is untyped (SHAPE|RUN|JUDGE)"))
        if v.startswith("SHAPE") and "before" not in body.lower(): defects.append((tid, "SHAPE verify names no `before` value"))
        if v:
            # Use the RAW line, not the SLOT_RE-captured group -- that regex eats the
            # leading backtick, which throws off verify_parse's own backtick-span scan.
            raw_verify = next((l for l in c["text"] if re.match(r'^\s*`?Verify:', l)), None)
            if raw_verify is not None:
                try:
                    parse_verify(raw_verify)
                except VerifyParseError as e:
                    defects.append((tid, f"Verify: unparseable — {e}"))
        if "Query" in s and "Proof" not in s: defects.append((tid, "`Query:` with no `Proof:` — a zero result is UNKNOWN until the query is proven well-formed"))
        for l in c["text"]:
            if GATE_RE.search(l) and not PATHISH.search(l.split("gated on",1)[-1] if "gated on" in l.lower() else ""):
                defects.append((tid, "`gated on` names no file"))
        gm = GEAR_RE.search(c["text"][0])          # the tag is on the header line; prose about gears is not a delegation
        if gm and not MODEL_RE.search(body): defects.append((tid, f"gear-{gm.group(1)} with no model named"))
        for w in split_where(s.get("Where", "")):
            if not (w.startswith("/") or w.startswith("~")):
                defects.append((tid, f"`Where:` is not an absolute path or ~ ({w}) — a relative or placeholder path derives the wrong repo"))
    return cards, defects

def _check_where_space_derivation():
    """6.12: a `Where:` path containing a space must derive its repo kind correctly, not get
    truncated at the first word. Synthetic map row + synthetic Where: -- no real filesystem
    paths needed, derive_kind only compares normalised strings."""
    root = os.path.realpath(os.path.expanduser("~/My Drive/lifehack-brain"))
    rows = [(root, "private")]
    where = "~/My Drive/lifehack-brain/system/tools/plan_lint.py"
    kind, mpath = derive_kind(where, rows)
    return kind == "private" and mpath == root

def _local_install_drift(skill_dir):
    """A local install at <config>/skills/autoplan must match the repo copy.

    CONDITIONAL BY DESIGN: a student installs by plugin and has NO local copy --
    absent is fine and silent. An unconditional check would fail for every student.
    Also refuses to compare a file with itself: if --self runs FROM the local
    install, skill_dir IS that copy and the comparison would be a tautology.
    Returns None when there is nothing to say, else the failure message.
    """
    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    local = os.path.realpath(os.path.join(cfg, "skills", "autoplan", "SKILL.md"))
    repo = os.path.realpath(os.path.join(skill_dir, "SKILL.md"))
    if not os.path.exists(local) or local == repo or not os.path.exists(repo):
        return None
    if open(local, encoding="utf-8").read() == open(repo, encoding="utf-8").read():
        return None
    return ("LOCAL COPY DRIFTED: " + local + " differs from the repo source " + repo +
            ". The local install is a DERIVED copy, never a source -- edit the repo and refresh it. "
            "If the repo is also ahead of origin, that is unpushed work.")

def self_check(skill_dir):
    if not _check_where_space_derivation():
        print("SELF-CHECK FAILED: a Where: path containing a space did not derive its repo kind "
              "correctly — derive_kind is truncating at the first whitespace again"); sys.exit(2)
    fx = os.path.join(skill_dir, "fixtures", "broken.plan.md")
    if not os.path.exists(fx): cannot_read(f"no known-bad fixture at {fx} — cannot prove the checker fires")
    _, d = lint(fx, load_map())
    if not d: print("SELF-CHECK FAILED: the known-bad fixture came back clean — the checker is dead"); sys.exit(2)
    budget = os.path.join(skill_dir, "fixtures", ".budget")
    skill = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(budget) and os.path.exists(skill):
        bl, bw = [int(x) for x in open(budget, encoding="utf-8").read().split()[:2]]
        txt = open(skill, encoding="utf-8").read(); nl, nw = txt.count("\n"), len(txt.split())
        if nl > bl or nw > bw:
            print(f"RATCHET: SKILL.md {nl} lines / {nw} words exceeds recorded floor {bl} / {bw}"); sys.exit(2)
    drift = _local_install_drift(skill_dir)
    if drift:
        print("SELF-CHECK FAILED: " + drift); sys.exit(2)
    print(f"SELF-CHECK OK: spacey Where: derives correctly; fixture fails ({len(d)} defects); budget held; local copy in step"); sys.exit(0)

def main():
    ap = argparse.ArgumentParser(description="plan_lint — a plan is not shown until every task is a complete card")
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--self", action="store_true", help="every-run guards: fixture must fail; SKILL.md within budget")
    ap.add_argument("--skill-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".claude", "skills", "autoplan"))
    a = ap.parse_args()
    if a.self: self_check(os.path.normpath(a.skill_dir))
    if not a.plan: cannot_read("no plan path given")
    cards, defects = lint(os.path.expanduser(a.plan), load_map())
    print(f"  cards: {len(cards)}  map rows: {len(load_map())}")
    if not defects: print("PLAN-CLEAN"); sys.exit(0)
    print(f"DEFECTS {len(defects)}")
    for tid, msg in defects: print(f"  {tid}: {msg}")
    sys.exit(2)

if __name__ == "__main__":
    main()
