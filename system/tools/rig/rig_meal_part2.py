#!/usr/bin/env python3
# not-wired-yet: run by hand to write the part-2 tables of the rig meal record; reads saved live results, runs no model
"""rig_meal_part2.py - turn the saved LIVE results of the rig meal (rig_meal.py live) into the part-2 tables.

Re-derives from the saved streams (not from the model's account): whether the README named the new piece (a skill is named by its
folder: the first live scorer could never score a skill as registered), whether a denied write was retried unchanged and passed,
and the /build-catchable column:
  READ-LIST   the run skipped the toolbox or the right SOP and has a result defect (unregistered / copied a shared tool / did not use one)
  END-CHECKS  not READ-LIST, but a commit check exists for the defect (unregistered -> connected; copied -> is_copy; no shared use -> raw-call checks)
  NEITHER     neither applies.  Both flags are also printed: END-CHECKS is by defect CATEGORY, the checks were not run on these desk files.
Run: python3 rig_meal_part2.py LIVE.jsonl STREAMS_DIR
"""
import json, os, sys, glob, re, collections


def stream_calls(path):
    calls, byid = [], {}
    for ln in open(path, errors="replace", encoding="utf-8"):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        m = d.get("message")
        if not isinstance(m, dict) or not isinstance(m.get("content"), list):
            continue
        for c in m["content"]:
            if c.get("type") == "tool_use":
                r = {"name": c["name"], "input": c.get("input") or {}, "result": "", "err": False}
                calls.append(r); byid[c["id"]] = r
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in byid:
                r = byid[c["tool_use_id"]]; cont = c.get("content")
                r["result"] = cont if isinstance(cont, str) else " ".join(x.get("text", "") for x in (cont or []) if isinstance(x, dict))
                r["err"] = bool(c.get("is_error"))
    return calls


def analyse(r, sdir):
    L = r["live"]; calls = stream_calls(os.path.join(sdir, L["stream"]))
    files = L["files"]
    pieces = [os.path.basename(f) for f in files if f.endswith((".sh", ".py"))] + [os.path.basename(os.path.dirname(f)) for f in files if f.endswith("SKILL.md")]
    readme = " ".join(json.dumps(c["input"]) for c in calls if c["name"] in ("Write", "Edit") and c["input"].get("file_path", "").endswith("README.md"))
    registered = bool(pieces) and any(p in readme for p in pieces)
    # first denied Write/Edit by a guard hook, and did the same path get written again successfully?
    deny = next((c for c in calls if c["err"] and c["name"] in ("Write", "Edit") and "hook error" in c["result"]), None)
    kind = None; retried = None
    if deny:
        kind = "wrong-home" if "Wrong home" in deny["result"] else "sop-nudge"
        pth = deny["input"].get("file_path")
        i = calls.index(deny)
        retried = any(c["name"] in ("Write", "Edit") and c["input"].get("file_path") == pth and not c["err"] for c in calls[i + 1:])
    return registered, kind, retried, len(calls)


def main():
    rs = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    sdir = sys.argv[2]
    rows = []
    for r in rs:
        L = r["live"]; b = L["bases"]
        reg, kind, retried, ncalls = analyse(r, sdir)
        used = b["used_shared"]
        result_ok = used and reg and b["right_home"]
        fric = bool(L["deny_rows"])
        bucket = "SLIPPED" if not result_ok else ("SAVED" if fric else ("RIGHT_FIRST_TIME" if b["read_toolbox"] and b["read_sop"] else "RIGHT_FIRST_TIME_UNREAD"))
        defects = [x for x, bad in (("unregistered", not reg), ("copied-shared", bool(L["copied"])), ("no-shared-use", not used)) if bad]
        unread = not (b["read_toolbox"] and b["read_sop"])
        rl = bool(defects) and unread
        ec = bool(defects)
        if bucket in ("RIGHT_FIRST_TIME",):
            bc = "-"
        elif not defects:
            bc = "n/a (end state right)"
        else:
            bc = "READ-LIST" if rl else ("END-CHECKS" if ec else "NEITHER")
        rows.append(dict(id=r["case"]["id"], kind=r["case"]["live"]["kind"], bucket=bucket, scorer_bucket=L["bucket"], tb=b["read_toolbox"], sop=b["read_sop"], used=used, reg=reg,
                         home=b["right_home"], deny_kind=kind, retried=retried, defects=defects, rl=rl, ec=ec, bc=bc, turns=L["turns"], cost=L["cost_usd"] or 0, secs=r["secs"], layers=r.get("deniers") or [], fric=fric))
    print("| case | kind | bucket | toolbox | SOP | shared ok | registered | home | deny (retried unchanged?) | defects | /build-catchable | READ-LIST? | END-CHECKS? |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for x in rows:
        print("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (x["id"], x["kind"], x["bucket"], x["tb"], x["sop"], x["used"], x["reg"], x["home"],
              "none" if not x["deny_kind"] else "%s (%s)" % (x["deny_kind"], "yes" if x["retried"] else "no"), ",".join(x["defects"]) or "-", x["bc"], x["rl"], x["ec"]))
    def tally(sub, name):
        c = collections.Counter(x["bucket"] for x in sub)
        print("- %s (n=%d): %s" % (name, len(sub), ", ".join("%s %d" % kv for kv in sorted(c.items()))))
    print()
    tally(rows, "all"); tally([x for x in rows if x["kind"] == "ordinary"], "ordinary"); tally([x for x in rows if x["kind"] == "wrong-move"], "wrong-move")
    n = len(rows); rft = sum(x["bucket"] == "RIGHT_FIRST_TIME" for x in rows)
    o = [x for x in rows if x["kind"] == "ordinary"]
    print("- right-first-time rate: %d/%d = %.0f%% overall; ordinary %d/%d = %.0f%%" % (rft, n, 100 * rft / n, sum(x["bucket"] == "RIGHT_FIRST_TIME" for x in o), len(o), 100 * sum(x["bucket"] == "RIGHT_FIRST_TIME" for x in o) / len(o)))
    print("- scorer-vs-rederived bucket changes: %s" % (", ".join("%s %s->%s" % (x["id"], x["scorer_bucket"], x["bucket"]) for x in rows if x["scorer_bucket"] != x["bucket"] and x["scorer_bucket"] != "SAVED") or "none"))
    print("- saving layers (journal): %s" % dict(collections.Counter(l for x in rows if x["bucket"] == "SAVED" for l in x["layers"])))
    print("- denies on ordinary runs: %s" % dict(collections.Counter(x["deny_kind"] or "none" for x in o)))
    print("- denies retried unchanged and then passed: %d of %d denied writes" % (sum(bool(x["retried"]) for x in rows if x["deny_kind"]), sum(bool(x["deny_kind"]) for x in rows)))
    sl = [x for x in rows if x["bucket"] == "SLIPPED"]
    print("- /build-catchable over non-right runs (%d): %s; slipped only (%d): %s" % (n - rft, dict(collections.Counter(x["bc"] for x in rows)), len(sl), dict(collections.Counter(x["bc"] for x in sl))))
    print("- slipped: READ-LIST would prevent %d, END-CHECKS would catch %d, both %d, neither %d" % (sum(x["rl"] for x in sl), sum(x["ec"] for x in sl), sum(x["rl"] and x["ec"] for x in sl), sum(not x["rl"] and not x["ec"] for x in sl)))
    both = [x for x in rows if x["tb"] and x["sop"]]; part = [x for x in rows if not (x["tb"] and x["sop"])]
    print("- read both toolbox and SOP before building: %d runs, defects in %d; skipped at least one: %d runs, defects in %d" % (len(both), sum(bool(x["defects"]) for x in both), len(part), sum(bool(x["defects"]) for x in part)))
    for f, name in (("tb", "toolbox"), ("sop", "right SOP"), ("used", "shared tool used/not copied"), ("reg", "registered"), ("home", "code in an accepted home")):
        print("- %s: %d of %d" % (name, sum(x[f] for x in rows), n))
    print("- sessions: %d, turns (model-call rounds) %d, cost $%.4f, session time %.0f s" % (n, sum(x["turns"] or 0 for x in rows), sum(x["cost"] for x in rows), sum(x["secs"] for x in rows)))


if __name__ == "__main__":
    main()
