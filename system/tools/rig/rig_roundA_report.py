#!/usr/bin/env python3
# not-wired-yet: run by hand to write the Round A re-run section of the rig meal record; reads saved results, runs no model
"""rig_roundA_report.py - BEFORE -> AFTER table for plan 3b.2 Round A. Every number computed here from saved results.
Run: rig_roundA_report.py BEFORE_REPLAY.jsonl BEFORE_LIVE.jsonl BEFORE_STREAMS AFTER_REPLAY.jsonl AFTER_LIVE.jsonl"""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rig_student as rs, rig_meal_part2 as p2

J = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def replay(rows):
    o = rs.summarize(rows); st, en = o["student"], o["today"]
    fa = sum(r["grade"] == "false-alarm" for r in rows)
    byroad = collections.Counter(r["case"].get("road") for r in rows if r["grade"] == "slipped")
    sbyroad = collections.Counter(r["case"].get("road") for r in rows if r["grade"] in rs.SAVED + ("slipped",) and rs.student_grade(r)[1] == "slipped")
    return dict(st=st, en=en, fa=fa, byroad=byroad, sbyroad=sbyroad, n=o["wrong_move_n"], clean=sum(r["grade"] == "clean" for r in rows))


def live_before(rows, sdir):
    out = []
    for r in rows:
        L = r["live"]; b = L["bases"]; reg, kind, retried, _ = p2.analyse(r, sdir)
        ok = b["used_shared"] and reg and b["right_home"]
        bucket = "SLIPPED" if not ok else ("SAVED" if L["deny_rows"] else ("RFT" if b["read_toolbox"] and b["read_sop"] else "RFT_UNREAD"))
        out.append(dict(bucket=bucket, tb=b["read_toolbox"], sop=b["read_sop"], false=(kind == "wrong-home"), build=False, bump=False,
                        defects=[x for x, bad in (("unregistered", not reg), ("copied-shared", bool(L["copied"])), ("no-shared-use", not b["used_shared"]), ("wrong-home", not b["right_home"])) if bad]))
    return out


def live_after(rows):
    out = []
    for r in rows:
        b = r["bases"]
        bucket = {"RIGHT_FIRST_TIME": "RFT", "RIGHT_FIRST_TIME_UNREAD": "RFT_UNREAD"}.get(r["bucket"], r["bucket"])
        out.append(dict(bucket=bucket, tb=b["read_toolbox"], sop=b["read_sop"], false=bool(r["real_false"]), build=r["build_after_bump"], bump=r["bump_names_build"],
                        defects=[x for x, bad in (("unregistered", not b["registered"]), ("copied-shared", bool(r["copied"])), ("no-shared-use", not b["used_shared"]), ("wrong-home", not b["right_home"])) if bad]))
    return out


def lv(x):
    n = len(x); c = collections.Counter(r["bucket"] for r in x)
    return dict(n=n, rft=c["RFT"], unread=c["RFT_UNREAD"], saved=c["SAVED"], slipped=c["SLIPPED"], tb=sum(r["tb"] for r in x), sop=sum(r["sop"] for r in x), both=sum(r["tb"] and r["sop"] for r in x),
                false=sum(r["false"] for r in x), build=sum(r["build"] for r in x), bump=sum(r["bump"] for r in x), defects=collections.Counter(d for r in x for d in r["defects"] if r["bucket"] == "SLIPPED"))


def strict_reads(streams, cases):
    """Cross-check of the scorer's read rates: first build act = first Write/Edit, or a Bash write that is not just `2>/dev/null` / `2>&1`
    (the scorer counts any `>x` as building, so a `cat sop 2>/dev/null` is read as a build act)."""
    import re, rig_live_score as ls
    clean = lambda c: re.sub(r"\d?>\s*/dev/null|\d>&\d|&>\s*/dev/null", "", c)
    tb = sop = both = 0
    for cid, sops in cases.items():
        f = os.path.join(streams, cid + ".stream.jsonl")
        calls = ls.parse_stream(f)[1]
        fb = next((c["i"] for c in calls if c["name"] in ("Write", "Edit", "MultiEdit") or (c["name"] == "Bash" and ls.WRITE_BASH.search(clean(c["input"].get("command", ""))))), len(calls))
        pre = [c for c in calls if c["i"] < fb]
        t = any("toolbox.md" in json.dumps(c["input"]) and c["name"] in ("Read", "Bash", "Grep") for c in pre)
        o = any((c["name"] in ("Read", "Bash", "Grep") and any(x in json.dumps(c["input"]) for x in sops)) or (c["name"] == "Bash" and "read_sop.sh" in c["input"].get("command", "")) for c in pre)
        tb += t; sop += o; both += t and o
    return tb, sop, both


def main():
    br, bl, bs, ar, al = sys.argv[1:6]
    B, A = replay(J(br)), replay(J(ar))
    LB, LA = lv(live_before(J(bl), bs)), lv(live_after(J(al)))
    row = lambda name, b, a: print("| %s | %s | %s |" % (name, b, a))
    print("| measure | BEFORE | AFTER |\n|---|---|---|")
    f = lambda s: "%d/%d, %.1f%% unweighted, %.1f%% weighted" % (s["saved"], B["n"], s["unweighted_pct"], s["weighted_pct"])
    row("STUDENT score, replay wrong moves (headline)", f(B["st"]), f(A["st"]))
    row("Enver bonus score (adds githook layers)", f(B["en"]), f(A["en"]))
    row("replay false alarms (correct moves wrongly stopped)", B["fa"], A["fa"])
    row("replay correct moves left alone", B["clean"], A["clean"])
    row("LIVE right-first-time", "%d/%d (+%d correct but unread)" % (LB["rft"], LB["n"], LB["unread"]), "%d/%d (+%d correct but unread)" % (LA["rft"], LA["n"], LA["unread"]))
    row("LIVE SAVED / SLIPPED", "%d / %d" % (LB["saved"], LB["slipped"]), "%d / %d" % (LA["saved"], LA["slipped"]))
    row("LIVE slips by defect (a session can have several)", dict(LB["defects"]), dict(LA["defects"]))
    row("LIVE false alarms (sessions with a non-nudge deny on a legitimate move)", "%d/%d" % (LB["false"], LB["n"]), "%d/%d" % (LA["false"], LA["n"]))
    row("toolbox read before building", "%d/%d" % (LB["tb"], LB["n"]), "%d/%d" % (LA["tb"], LA["n"]))
    row("right SOP read before building", "%d/%d" % (LB["sop"], LB["n"]), "%d/%d" % (LA["sop"], LA["n"]))
    row("both read", "%d/%d" % (LB["both"], LB["n"]), "%d/%d" % (LA["both"], LA["n"]))
    row("sessions whose speed bump named /build + toolbox", "n/a (old bump)", "%d/%d" % (LA["bump"], LA["n"]))
    row("sessions that invoked /build (Skill) after a bump", "n/a", "%d/%d" % (LA["build"], LA["n"]))
    for tag, sd, cf in (("BEFORE", sys.argv[3], "meal-part2-live.jsonl"), ("AFTER", sys.argv[6], "meal-roundA-live.jsonl")):
        cs = {c["id"]: c["live"]["sop"] for c in J(os.path.join(HERE, "cases", cf))}
        print("\nStrict cross-check of reads (first Write/Edit or real Bash write; %s): toolbox %d, SOP %d, both %d of %d" % ((tag,) + strict_reads(sd, cs) + (len(cs),)))
    print("\nReplay slips by road (Enver / student):")
    roads = sorted(set(B["byroad"]) | set(A["byroad"]) | set(B["sbyroad"]) | set(A["sbyroad"]))
    print("| road | BEFORE Enver | AFTER Enver | BEFORE student | AFTER student |\n|---|---|---|---|---|")
    for r in roads:
        print("| %s | %d | %d | %d | %d |" % (r, B["byroad"][r], A["byroad"][r], B["sbyroad"][r], A["sbyroad"][r]))
    print("| total | %d | %d | %d | %d |" % (sum(B["byroad"].values()), sum(A["byroad"].values()), sum(B["sbyroad"].values()), sum(A["sbyroad"].values())))


if __name__ == "__main__":
    main()
