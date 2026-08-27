#!/usr/bin/env python3
"""stale_sweep.py — mechanical half of the weekly stale-record sweep.

WHY: open claims in state/debt-ledger.md and state/open-loops.md rot in one direction — work
finishes and the record keeps saying "open" (2026-08-26: 14 dead entries closed by hand; three of
them had just been presented to the owner as live deadlines). This tool is the CODE side of the
sweep's LAW-1 split: it EXTRACTS claims (structure-anchored, never keyword grep — see the three
logged mention-vs-target false positives in skill-building-sop §II.4a) and VALIDATES the model's
dispositions against a closed vocabulary, fail-closed. The judgment ("does live evidence close this
claim?") belongs to the headless model in stale-sweep-run.sh; membership enforcement belongs here.

Subcommands:
  extract  --ledger <path> --loops <path> [--out <path>]   → claims JSON (stdout or file)
  validate --claims <path> --dispositions <path>            → normalized dispositions JSON to stdout
                                                              (off-list/missing → NO-OUTCOME), plus
                                                              counts; exit 0 always unless unreadable.

The vocabulary (spec: stale-sweep-spec_2026.08.27.md). Any model failure — off-list value, missing
claim, unparseable file — maps to NO-OUTCOME, NEVER to a clean verdict: "I could not look" must
never be spelled like "I looked and it was fine".
"""
import argparse
import json
import re
import sys

VOCAB = ["STALE-CLOSE-PROPOSED", "STILL-OPEN", "NEEDS-HUMAN", "UNVERIFIABLE", "NO-OUTCOME"]

TAG_RE = re.compile(r"\[([A-Z][A-Z-]*)\]")
STATE_RE = re.compile(r"state:\s*`?\s*([a-z][a-z-]*)")


def _is_struck(text):
    """An item is already closed iff its content (after the bullet/number marker) opens with ~~."""
    return text.lstrip().startswith("~~")


def extract_ledger(path):
    """Claims from the ## Open section: col-0 bullets `- ...` until the next `- ` or `## `.
    Struck bullets (content opening with ~~) are closed — skipped."""
    lines = open(path, encoding="utf-8").read().splitlines()
    claims, in_open, item, item_line = [], False, None, 0

    def flush():
        if item is None:
            return
        body = "\n".join(item).strip()
        content = re.sub(r"^-\s*", "", body, count=1)
        if not body or _is_struck(content):
            return
        tag = TAG_RE.search(content[:60])
        state = STATE_RE.search(content)
        claims.append({
            "id": "ledger:%d" % item_line,
            "source": "%s:%d" % (path, item_line),
            "tag": tag.group(1) if tag else None,
            "state_marker": state.group(1) if state else None,
            "text": body,
        })

    for n, ln in enumerate(lines, 1):
        if ln.startswith("## "):
            flush(); item = None
            in_open = ln.strip() == "## Open"
            continue
        if not in_open:
            continue
        if ln.startswith("- "):
            flush()
            item, item_line = [ln], n
        elif item is not None:
            item.append(ln)
    flush()
    return claims


def extract_loops(path):
    """Claims from open-loops.md: numbered items (^N. ) and col-0 bullets, in every section whose
    heading does not start with '## Resolved'. Struck items are closed — skipped."""
    lines = open(path, encoding="utf-8").read().splitlines()
    claims, in_scope, item, item_line, marker = [], True, None, 0, ""

    def flush():
        if item is None:
            return
        body = "\n".join(item).strip()
        content = re.sub(r"^(\d+\.|-)\s*", "", body, count=1)
        if not body or _is_struck(content):
            return
        state = STATE_RE.search(content)
        claims.append({
            "id": "loops:%s" % (marker or str(item_line)),
            "source": "%s:%d" % (path, item_line),
            "tag": None,
            "state_marker": state.group(1) if state else None,
            "text": body,
        })

    num_re = re.compile(r"^(\d+)\.\s")
    for n, ln in enumerate(lines, 1):
        if ln.startswith("## "):
            flush(); item = None
            in_scope = not ln.startswith("## Resolved")
            continue
        if not in_scope:
            continue
        m = num_re.match(ln)
        if m:
            flush()
            item, item_line, marker = [ln], n, "#" + m.group(1)
        elif ln.startswith("- "):
            flush()
            item, item_line, marker = [ln], n, ""
        elif item is not None:
            item.append(ln)
    flush()
    return claims


def cmd_extract(args):
    claims = extract_ledger(args.ledger) + extract_loops(args.loops)
    out = json.dumps({"claim_count": len(claims), "vocabulary": VOCAB, "claims": claims},
                     indent=1, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("wrote %d claims -> %s" % (len(claims), args.out))
    else:
        print(out)
    return 0


def cmd_validate(args):
    try:
        claims = {c["id"]: c for c in json.load(open(args.claims, encoding="utf-8"))["claims"]}
    except Exception as e:
        print("FATAL: cannot read claims file: %s" % e, file=sys.stderr)
        return 1
    try:
        raw = json.load(open(args.dispositions, encoding="utf-8"))
        entries = {d.get("id"): d for d in raw.get("dispositions", []) if isinstance(d, dict)}
    except Exception as e:
        # The model's output was unreadable — every claim is NO-OUTCOME, not clean.
        entries, raw = {}, {"_error": str(e)}
    normalized, counts = [], {v: 0 for v in VOCAB}
    for cid, claim in claims.items():
        d = entries.get(cid, {})
        verdict = d.get("disposition")
        if verdict not in VOCAB:
            verdict = "NO-OUTCOME"
        counts[verdict] += 1
        normalized.append({
            "id": cid, "source": claim["source"], "disposition": verdict,
            "proof": d.get("proof", "") if verdict != "NO-OUTCOME" else
                     d.get("proof", "no valid disposition returned"),
        })
    alien = [k for k in entries if k not in claims]
    print(json.dumps({"counts": counts, "alien_ids_dropped": alien,
                      "dispositions": normalized}, indent=1, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("extract")
    p1.add_argument("--ledger", required=True)
    p1.add_argument("--loops", required=True)
    p1.add_argument("--out")
    p2 = sub.add_parser("validate")
    p2.add_argument("--claims", required=True)
    p2.add_argument("--dispositions", required=True)
    args = ap.parse_args()
    sys.exit(cmd_extract(args) if args.cmd == "extract" else cmd_validate(args))


if __name__ == "__main__":
    main()
