#!/usr/bin/env python3
"""grade.py: pure-code grader for the morning-read finish test (plan B2 step 4).

Takes a morning draft and a case's expected.json, prints pass/fail per check,
exits 0 only if every check passes.

    python3 grade.py --draft draft.md --expected cases/01_paid_testreel/expected.json
    python3 grade.py --draft draft.md --form form.json --expected ...   # form in a catalogue file

Ruling 2026-11-15 (plan B2 step 4 / step 7): the morning write-up is STAGED
each morning in records (a records/context/ file); the small fixed form for
code to check lives in the CATALOGUE beside it (a catalogue line / JSON file),
not inside the record prose; ONE low-confidence diary entry per desk is
written by the morning run from what was staged that day. --form reads the fixed
form from that separate catalogue file; without it, the older fenced-block
inside the draft is still accepted (compatibility).

Diary mode (--midnight, the flag keeps the retired job's name) grades a whole desk diary directory:

    python3 grade.py --midnight --diary <diary dir> --expected cases/08_midnight_entry/expected.json

Diary-entry check kinds (the midnight_ prefix is the retired job's name; expected.json "checks" list; each carries "date"):
  midnight_one_entry        -- exactly ONE diary file for the date, containing exactly one entry heading ("# ...")
  midnight_low_confidence   -- today's entry is marked low confidence ("confidence: low")
  midnight_points_to_staged -- today's entry references each staged write-up named in "files"
  midnight_no_earlier_edit  -- every file present the day before is byte-identical, and nothing
                               exists in the diary beyond the before-set plus today's ONE entry

Draft format (the contract the morning read must write; see README.md):
  - Markdown with "## What changed", "## Picture", "## Questions" sections.
  - One fenced ```json block at the end, the fixed form:
      {"deadlines": [...], "money": [...], "needs_him": [...], "project_updates": [...],
       "questions": [...], "coverage": {"<msg id>": "used"|"sorted_out_by_triage"|"skipped_with_reason"}}
    Fixed-form items are objects; every string value is concatenated for matching.
    An item may carry "confidence": "stated" | "guess" | "cant_tell" (+ "why").

Check kinds (expected.json "checks" list):
  required_fixed       {field, contains, couldnt_tell_allowed?, topic?}
  required_question    {contains}   -- a line under "## Questions" must contain it
  required_in_markdown {contains}   -- anywhere in the markdown
  forbidden_as_fact    {contains}   -- must not appear as a confirmed fact: every
                                      occurrence must sit in a Questions line or a
                                      line marked "(unconfirmed"
  not_in_markdown      {contains}   -- must not appear in the markdown at all (junk kept out)
  coverage             {status: {msg-id: expected status}}   -- and NO extra ids allowed
  max_change           {max_changed_lines, empty_fields: [...]}  -- the quiet week
"""
import argparse
import json
import os
import re
import sys

FIXED_FIELDS = ("deadlines", "money", "needs_him", "project_updates")

def load_draft_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def fixed_from_markdown(text):
    """The old contract: one fenced ```json block inside the draft markdown."""
    m = None
    for m in re.finditer(r"```json\s*(\{.*?\})\s*```", text, re.S):
        pass
    if not m:
        raise SystemExit("FAIL: no fenced ```json fixed-form block found in the draft")
    try:
        return json.loads(m.group(1))
    except ValueError as e:
        raise SystemExit("FAIL: fixed-form JSON block does not parse: %s" % e)

def fixed_from_catalogue(path):
    """The new contract (2026-11-15): the fixed form lives in the catalogue,
    a JSON file beside the staged record, never inside its prose."""
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except ValueError as e:
            raise SystemExit("FAIL: catalogue form file %s does not parse: %s" % (path, e))

def load_draft(path, form_path=None):
    text = load_draft_text(path)
    if form_path:
        return text, fixed_from_catalogue(form_path)
    return text, fixed_from_markdown(text)

def sections(markdown):
    out, cur = {}, "_top"
    for line in markdown.splitlines():
        mm = re.match(r"^##\s+(.+?)\s*$", line)
        if mm:
            cur = mm.group(1).lower()
            out.setdefault(cur, [])
            continue
        out.setdefault(cur, []).append(line)
    return out

def question_lines(secs):
    lines = []
    for name, body in secs.items():
        if "question" in name:
            lines.extend(body)
    return lines

def item_text(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return " ".join(str(v) for v in item.values() if isinstance(v, str))
    return str(item)

def contains_all(hay, subs):
    h = hay.lower()
    return all(s.lower() in h for s in subs)

def check_required_fixed(fixed, c):
    items = fixed.get(c["field"]) or []
    for item in items:
        t = item_text(item)
        if contains_all(t, c["contains"]):
            return True, "matched item: %s" % t[:100]
    if c.get("couldnt_tell_allowed"):
        topic = c.get("topic") or c["contains"][0]
        for item in items:
            if isinstance(item, dict) and item.get("confidence") == "cant_tell" \
               and topic.lower() in item_text(item).lower():
                return True, "matched as cant_tell (allowed): %s" % item_text(item)[:100]
    return False, "no fixed-form item in '%s' contains %s" % (c["field"], c["contains"])

def check_forbidden_as_fact(markdown, secs, c):
    subs = c["contains"]
    qlines = question_lines(secs)
    for line in markdown.splitlines():
        low = line.lower()
        if not any(s.lower() in low for s in subs):
            continue
        is_q = line in qlines or low.lstrip().startswith(("q", "- q"))
        is_unc = "(unconfirmed" in low
        if not (is_q or is_unc):
            return False, "appears as fact: %s" % line.strip()[:120]
    return True, "only in question/unconfirmed lines (or absent)"

def check_coverage(fixed, c):
    cov = fixed.get("coverage")
    if not isinstance(cov, dict):
        return False, "fixed form has no coverage dict"
    for mid, want in c["status"].items():
        got = cov.get(mid)
        if got != want:
            return False, "%s: expected %s, got %s" % (mid, want, got)
    extra = sorted(set(cov) - set(c["status"]))
    if extra:
        return False, "unknown message ids in coverage (padding?): %s" % ", ".join(extra)
    return True, "all %d ids accounted for, no extras" % len(c["status"])

def check_max_change(markdown, fixed, c):
    secs = sections(markdown)
    body = []
    for name, lines in secs.items():
        if "what changed" in name:
            body = lines
    n = sum(1 for ln in body if ln.strip().startswith("-"))
    if n > c["max_changed_lines"]:
        return False, "What changed has %d bullets, max %d" % (n, c["max_changed_lines"])
    for field in c.get("empty_fields", []):
        if fixed.get(field):
            return False, "quiet week but '%s' is not empty: %s" % (field, fixed[field][:1])
    return True, "What changed: %d bullets; quiet fields empty" % n

def strip_fixed_block(markdown):
    """The prose draft without the fenced JSON block: fixed-form questions legitimately
    restate forbidden phrases, so fact-checks read prose only."""
    return re.sub(r"```json\s*\{.*?\}\s*```", "", markdown, flags=re.S)

def run(draft_path, expected_path, form_path=None):
    markdown, fixed = load_draft(draft_path, form_path)
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    secs = sections(markdown)
    results, all_ok = [], True
    for c in expected["checks"]:
        kind = c["kind"]
        if kind == "required_fixed":
            ok, detail = check_required_fixed(fixed, c)
        elif kind == "required_question":
            ok = any(contains_all(ln, c["contains"]) for ln in question_lines(secs))
            detail = "found in Questions" if ok else "no Questions line contains %s" % c["contains"]
        elif kind == "required_in_markdown":
            ok = contains_all(markdown, c["contains"])
            detail = "present" if ok else "missing from markdown"
        elif kind == "forbidden_as_fact":
            ok, detail = check_forbidden_as_fact(strip_fixed_block(markdown), secs, c)
        elif kind == "not_in_markdown":
            ok = not any(s.lower() in markdown.lower() for s in c["contains"])
            detail = "absent" if ok else "found in markdown: %s" % c["contains"]
        elif kind == "coverage":
            ok, detail = check_coverage(fixed, c)
        elif kind == "max_change":
            ok, detail = check_max_change(markdown, fixed, c)
        else:
            ok, detail = False, "unknown check kind %r" % kind
        results.append((c.get("id", kind), ok, detail))
        all_ok &= ok
    for name, ok, detail in results:
        print("%s  %s -- %s" % ("PASS" if ok else "FAIL", name, detail))
    print("RESULT: %s (%d/%d checks passed)" % ("PASS" if all_ok else "FAIL",
          sum(1 for _, ok, _ in results if ok), len(results)))
    return 0 if all_ok else 1

ENTRY_HEADING = re.compile(r"^#\s", re.M)

def midnight_today_files(diary_dir, date):
    return sorted(f for f in os.listdir(diary_dir)
                  if date in f and os.path.isfile(os.path.join(diary_dir, f)))

def check_midnight(diary_dir, exp_dir, c):
    date = c["date"]
    kind = c["kind"]
    today = midnight_today_files(diary_dir, date)
    if kind != "midnight_no_earlier_edit" or not today:
        pass
    if kind == "midnight_one_entry":
        if len(today) != 1:
            return False, "expected exactly ONE diary file for %s, found %d: %s" % (
                date, len(today), ", ".join(today))
        n = len(ENTRY_HEADING.findall(load_draft_text(os.path.join(diary_dir, today[0]))))
        return (n == 1), ("one file, one entry heading" if n == 1 else
                          "file %s holds %d entry headings; the day gets ONE" % (today[0], n))
    if len(today) != 1:
        return False, "no single entry file for %s (found %d)" % (date, len(today))
    text = load_draft_text(os.path.join(diary_dir, today[0]))
    if kind == "midnight_low_confidence":
        ok = re.search(r"confidence\s*:\s*low", text, re.I) is not None
        return ok, ("entry is marked low confidence" if ok else
                    "entry is not marked low confidence (confidence: low)")
    if kind == "midnight_points_to_staged":
        missing = [f for f in c["files"] if f not in text]
        return (not missing), ("points to all %d staged write-ups" % len(c["files"]) if not missing
                               else "entry does not point to staged write-up(s): %s" % ", ".join(missing))
    if kind == "midnight_no_earlier_edit":
        before_dir = os.path.join(exp_dir, c.get("before_dir", "diary_before"))
        before = sorted(os.listdir(before_dir))
        problems = []
        for f in before:
            p = os.path.join(diary_dir, f)
            if not os.path.isfile(p):
                problems.append("%s: missing (deleted?)" % f)
            elif load_draft_text(p) != load_draft_text(os.path.join(before_dir, f)):
                problems.append("%s: CHANGED since yesterday" % f)
        allowed = set(before) | set(today)
        extra = sorted(set(os.listdir(diary_dir)) - allowed)
        for f in extra:
            problems.append("%s: unexpected new file (only one entry per desk per day)" % f)
        return (not problems), ("all %d earlier files byte-identical; nothing extra beyond today's entry" % len(before)
                                if not problems else "; ".join(problems))
    return False, "unknown midnight check kind %r" % kind

def run_midnight(diary_dir, expected_path):
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    exp_dir = os.path.dirname(os.path.abspath(expected_path))
    results, all_ok = [], True
    for c in expected["checks"]:
        ok, detail = check_midnight(diary_dir, exp_dir, c)
        results.append((c.get("id", c["kind"]), ok, detail))
        all_ok &= ok
    for name, ok, detail in results:
        print("%s  %s -- %s" % ("PASS" if ok else "FAIL", name, detail))
    print("RESULT: %s (%d/%d checks passed)" % ("PASS" if all_ok else "FAIL",
          sum(1 for _, ok, _ in results if ok), len(results)))
    return 0 if all_ok else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft")
    ap.add_argument("--form", help="catalogue JSON file holding the fixed form (beside the staged record)")
    ap.add_argument("--midnight", action="store_true", help="grade a whole desk diary directory")
    ap.add_argument("--diary", help="diary directory (with --midnight)")
    ap.add_argument("--expected", required=True)
    args = ap.parse_args()
    if args.midnight:
        if not args.diary:
            ap.error("--midnight needs --diary <dir>")
        sys.exit(run_midnight(args.diary, args.expected))
    if not args.draft:
        ap.error("--draft <draft.md> is required (or use --midnight --diary)")
    sys.exit(run(args.draft, args.expected, args.form))

if __name__ == "__main__":
    main()
