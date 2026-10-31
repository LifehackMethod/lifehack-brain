#!/usr/bin/env python3
"""run_helper.py — the small pure-code parts of run.sh (TR1.4) that bash 3.2 does badly. No model, no network.

  rowsum F1 F2 F3 F4 F5 F6         first 12 hex of sha256("\\t".join(F1..F6)), no trailing newline (CONTRACT §2;
                                   byte-for-byte the rule truth.py's parse_record checks)
  scan RECORD RUN_ID               one line per record row that the runner must NOT trust, in file order:
                                     FOREIGN <k>          the row's run-id differs from RUN_ID
                                     REFUSED <sN|s?> <k>  malformed: wrong field count, bad status/step, bad rowsum,
                                                          or no final newline (k = 1-based line number)
  last-valid RECORD RUN_ID sN      "<status> <sha> <model> <epoch>" of the LAST valid row for sN (exit 1 if none)
  last-valid-any RECORD RUN_ID     "<epoch>" of the last valid row of any step (exit 1 if none)
  last-ai-model RECORD RUN_ID      model id of the last valid row whose model is not "-" (exit 1 if none)
  has-vouch RECORD RUN_ID sN SHA   exit 0 iff the last valid done/skipped-done row for sN carries SHA
  result RAW OUT DEFAULT_MODEL     RAW = claude --output-format json stdout. Writes the `result` string,
                                   whitespace-trimmed, to OUT and prints the model id. Exit 5 (nothing written)
                                   if RAW is not one JSON object with a string `result`, or is_error is true.
  today                            "<YYYY-MM-DD> <epoch>" of the fake clock STRESS_TODAY (UTC midnight). Unset ->
                                   exit 1 (run.sh decides the default; it never reads the wall clock in --fake)
  day N                            drive.py day(): BASE 2026-11-01 + (N-1) days
  yes-swap IN OUT                  copy a human step file with "answer" set to "yes" (to content-check a "no")
  realpath P                       os.path.realpath (works for paths that do not exist)
  render-settings TPL OUT SCRATCH RIG
                                   render lab-settings.template.json -> OUT: every "{{SCRATCH}}" / "{{RIG}}" inside a
                                   JSON string becomes realpath(SCRATCH) / realpath(RIG) (both must be absolute,
                                   existing dirs). Written atomically (OUT.partial -> OUT). Exit 2, nothing written, if
                                   the template is not JSON, a placeholder is unknown/left over, or no deny list.
  seed                             a fresh random seed 0..999999 (secrets module)
  cost RUN_DIR                     sum of total_cost_usd over RUN_DIR/s*.raw.json ("0" if none)
  judge-key RIG EMIT KIND CHECK    the pre-flight judge cache key (TR1.4 amendment): sha256 of a manifest naming
                                   KIND, the python version, and "<relpath> <sha256>" for EVERY file the
                                   `checks/selftest.sh --judge CHECK KIND` verdict depends on: CHECK itself,
                                   checks/{_check.py,_lib.sh,selftest.sh}, every file under checks/fixtures/ (recursive),
                                   canary/{expected.py,card.txt}, every canary/prompts/* file, EMIT/verdicts.py.
                                   Exit 1 (no key, so no caching) if any of them is missing or unreadable.
"""
import calendar, datetime, glob, hashlib, json, os, re, secrets, sys

STATUSES = ("done", "skipped-done", "waiting", "halted")
# from orchestrator-v2/rig/stress/drive.py @ 2026-10-28  (day(): the fake clock's calendar; nothing else taken)
BASE = datetime.date(2026, 11, 1)


def day(n):  # 1-based
    return (BASE + datetime.timedelta(days=n - 1)).isoformat()
# end stolen part


def rowsum(fields):
    return hashlib.sha256("\t".join(fields).encode()).hexdigest()[:12]


def rows(path, run_id):
    """-> list of (k, fields, verdict) with verdict in VALID | FOREIGN | REFUSED."""
    if not os.path.exists(path):
        return []
    with open(path, "rb") as fh:
        content = fh.read().decode("utf-8", "replace")
    lines = content.split("\n")
    out = []
    for i, line in enumerate(lines):
        last = i == len(lines) - 1
        if last and line == "":
            break                                    # the file ended in a newline
        f = line.split("\t")
        if f[0] != run_id and f[0] != "":
            out.append((i + 1, f, "FOREIGN"))
            continue
        ok = (not last and len(f) == 7 and f[0] == run_id and re.fullmatch(r"s\d+", f[1] or "")
              and f[2] in STATUSES and re.fullmatch(r"\d+", f[3] or "") and rowsum(f[:6]) == f[6])
        out.append((i + 1, f, "VALID" if ok else "REFUSED"))
    return out


def valid(path, run_id):
    return [(k, f) for k, f, v in rows(path, run_id) if v == "VALID"]


def main(a):
    cmd = a[0] if a else ""
    if cmd == "rowsum" and len(a) == 7:
        print(rowsum(a[1:7])); return 0
    if cmd == "scan" and len(a) == 3:
        for k, f, v in rows(a[1], a[2]):
            if v == "FOREIGN":
                print("FOREIGN %d" % k)
            elif v == "REFUSED":
                sid = f[1] if len(f) > 1 and re.fullmatch(r"s\d+", f[1]) else "s?"
                print("REFUSED %s %d" % (sid, k))
        return 0
    if cmd == "last-valid" and len(a) == 4:
        r = [f for _, f in valid(a[1], a[2]) if f[1] == a[3]]
        if not r:
            return 1
        print("%s %s %s %s" % (r[-1][2], r[-1][4], r[-1][5], r[-1][3])); return 0
    if cmd == "last-valid-any" and len(a) == 3:
        r = valid(a[1], a[2])
        if not r:
            return 1
        print(r[-1][1][3]); return 0
    if cmd == "last-ai-model" and len(a) == 3:
        r = [f for _, f in valid(a[1], a[2]) if f[5] != "-"]
        if not r:
            return 1
        print(r[-1][5]); return 0
    if cmd == "has-vouch" and len(a) == 5:
        r = [f for _, f in valid(a[1], a[2]) if f[1] == a[3] and f[2] in ("done", "skipped-done")]
        return 0 if r and r[-1][4] == a[4] else 1
    if cmd == "result" and len(a) == 4:
        try:
            with open(a[1], encoding="utf-8") as fh:
                d = json.loads(fh.read())
        except Exception:
            return 5
        if not isinstance(d, dict) or not isinstance(d.get("result"), str) or d.get("is_error") is True:
            return 5
        model = d.get("model")
        if not isinstance(model, str) or not model:
            mu = d.get("modelUsage")
            model = next(iter(mu), None) if isinstance(mu, dict) and mu else None
        model = re.sub(r"[\s\t]", "", model or a[3]) or a[3]
        with open(a[2], "w", encoding="utf-8") as fh:
            fh.write(d["result"].strip() + ("\n" if d["result"].strip() else ""))
        print(model); return 0
    if cmd == "today" and len(a) == 1:
        t = os.environ.get("STRESS_TODAY", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
            return 1
        d = datetime.date.fromisoformat(t)
        print("%s %d" % (t, calendar.timegm(d.timetuple()))); return 0
    if cmd == "day" and len(a) == 2:
        print(day(int(a[1]))); return 0
    if cmd == "yes-swap" and len(a) == 3:
        with open(a[1], encoding="utf-8") as fh:
            d = json.loads(fh.read())
        d["answer"] = "yes"
        with open(a[2], "w", encoding="utf-8") as fh:
            fh.write(json.dumps(d, separators=(",", ":")) + "\n")
        return 0
    if cmd == "render-settings" and len(a) == 5:
        tpl, out, scratch, rig = a[1:5]
        for label, d in (("SCRATCH", scratch), ("RIG", rig)):
            if not os.path.isabs(d) or not os.path.isdir(d):
                print("render-settings: %s must be an absolute existing dir: %r" % (label, d), file=sys.stderr); return 2
        subs = {"{{SCRATCH}}": os.path.realpath(scratch), "{{RIG}}": os.path.realpath(rig)}
        def sub(v):
            if isinstance(v, str):
                for k, r in subs.items():
                    v = v.replace(k, r)
                if "{{" in v or "}}" in v:
                    raise ValueError("unknown placeholder left in %r" % v)
                return v
            if isinstance(v, list):
                return [sub(x) for x in v]
            if isinstance(v, dict):
                return {sub(k): sub(x) for k, x in v.items()}
            return v
        try:
            with open(tpl, encoding="utf-8") as fh:
                d = sub(json.load(fh))
            deny = d["permissions"]["deny"]
            if not isinstance(deny, list) or not deny:
                raise ValueError("empty deny list")
        except (OSError, ValueError, KeyError, TypeError) as e:
            print("render-settings: %s: %s" % (tpl, e), file=sys.stderr); return 2
        part = out + ".partial"
        try:
            with open(part, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(d, indent=2) + "\n")
            os.replace(part, out)
        except OSError as e:
            print("render-settings: cannot write %s: %s" % (out, e), file=sys.stderr); return 2
        return 0
    if cmd == "realpath" and len(a) == 2:
        print(os.path.realpath(a[1])); return 0
    if cmd == "seed" and len(a) == 1:
        print(secrets.randbelow(1_000_000)); return 0
    if cmd == "cost" and len(a) == 2:
        s = 0.0
        for p in glob.glob(os.path.join(a[1], "s*.raw.json")):
            try:
                with open(p, encoding="utf-8") as fh:
                    v = json.loads(fh.read()).get("total_cost_usd")
                s += float(v or 0)
            except (OSError, ValueError, TypeError, AttributeError) as e:
                # a reply still being written, cut, or not a JSON object: the display total is then a LOWER BOUND and
                # says so on stderr (budget.sh's ledger, not this sum, is what enforces the cap)
                print("cost: %s unreadable (%s: %s); total excludes it" % (p, type(e).__name__, e), file=sys.stderr)
        print("%.4f" % s); return 0
    if cmd == "judge-key" and len(a) == 5:
        rig, emit, kind, check = a[1], a[2], a[3], a[4]
        files = [("check", check)]
        for n in ("_check.py", "_lib.sh", "selftest.sh"):
            files.append(("checks/" + n, os.path.join(rig, "checks", n)))
        fx = os.path.join(rig, "checks", "fixtures")
        if not os.path.isdir(fx):
            return 1
        for root, dirs, names in os.walk(fx):
            dirs.sort()
            for n in sorted(names):
                p = os.path.join(root, n)
                files.append((os.path.relpath(p, rig), p))
        files += [("canary/expected.py", os.path.join(rig, "canary", "expected.py")),
                  ("canary/card.txt", os.path.join(rig, "canary", "card.txt"))]
        pr = os.path.join(rig, "canary", "prompts")
        if not os.path.isdir(pr):
            return 1
        files += [("canary/prompts/" + n, os.path.join(pr, n)) for n in sorted(os.listdir(pr))]
        files.append(("emit/verdicts.py", os.path.join(emit, "verdicts.py")))
        man = ["judge-key-v1", "kind " + kind, "python " + sys.version.replace("\n", " ")]
        for label, p in files:
            try:
                with open(p, "rb") as fh:
                    man.append("%s %s" % (label, hashlib.sha256(fh.read()).hexdigest()))
            except OSError:
                return 1
        print(hashlib.sha256("\n".join(man).encode()).hexdigest()); return 0
    print("usage: see run_helper.py docstring", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
