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
  Verify:  typed SHAPE|RUN|JUDGE; SHAPE names a `before`
  Done:    present
  Commit:  present unless Repo is none
  Query:   if present, a `Proof:` line follows (a zero result is UNKNOWN until proven well-formed)
  gates:   every "gated on" (any case) names a file path
  gear-2+: names a model
  plan:    has a `Review:` line

--self — the every-run guards: fixtures/broken.plan.md must FAIL (a known-bad plan coming back
clean means the checker is dead); SKILL.md must not exceed fixtures/.budget (the ratchet).

VERDICTS  0 clean · 2 defects (one line each, task id first) · 4 CANNOT-READ (the no-outcome member)
"""
import os, re, subprocess, sys, argparse

CANNOT_READ = 4
ID = r'[A-Za-z]{0,2}\d{1,3}\.\d{1,2}[a-z]?'
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

def derive_kind(where, rows):
    w = os.path.realpath(os.path.expanduser(where.split()[0])) if where else ""
    for path, kind in rows:
        if w == path or w.startswith(path + os.sep): return kind, path
    return "none", None

def live_branch(path):
    try:
        r = subprocess.run(["git", "-C", path, "branch", "--show-current"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def parse_cards(lines):
    cards, cur = [], None
    for i, l in enumerate(lines, 1):
        m = CARD_RE.match(l)
        if m:
            cur = {"id": m.group(1), "line": i, "text": [l], "slots": {}}
            cards.append(cur); continue
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
    return cards

def lint(path, rows):
    if not os.path.exists(path): cannot_read(f"plan does not exist: {path}")
    try: lines = open(path, encoding="utf-8").read().split("\n")
    except Exception as e: cannot_read(f"plan unreadable ({e}): {path}")
    defects = []
    if not any(l.strip().startswith(("> **Review:**", "Review:", "**Review:**")) for l in lines):
        defects.append(("plan", "no `Review:` line (reviewed or SKIPPED — either way it must say)"))
    cards = parse_cards(lines)
    if not cards: cannot_read(f"no `- [ ] **<id>` cards found in {path}")
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
        if "Query" in s and "Proof" not in s: defects.append((tid, "`Query:` with no `Proof:` — a zero result is UNKNOWN until the query is proven well-formed"))
        for l in c["text"]:
            if GATE_RE.search(l) and not PATHISH.search(l.split("gated on",1)[-1] if "gated on" in l.lower() else ""):
                defects.append((tid, "`gated on` names no file"))
        gm = GEAR_RE.search(c["text"][0])          # the tag is on the header line; prose about gears is not a delegation
        if gm and not MODEL_RE.search(body): defects.append((tid, f"gear-{gm.group(1)} with no model named"))
        w = s.get("Where", "").split()[0] if s.get("Where") else ""
        if w and not (w.startswith("/") or w.startswith("~")):
            defects.append((tid, f"`Where:` is not an absolute path or ~ ({w}) — a relative or placeholder path derives the wrong repo"))
    return cards, defects

def self_check(skill_dir):
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
    print(f"SELF-CHECK OK: fixture fails ({len(d)} defects); budget held"); sys.exit(0)

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
