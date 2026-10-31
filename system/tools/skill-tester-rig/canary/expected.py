#!/usr/bin/env python3
"""expected.py — the canary's reference implementation. PURE CODE: no model, no network, no clock.

This file IS the contract in executable form (SPEC.md is the prose). The oracle (truth.py), the checks,
the code steps, the human-step writer, and the fake model all import it, so there is one formula, once.

CLI
  expected.py --seed S | --run-id R  [--answers s4=yes,s9=yes]  --out DIR
      write the correct step-N.json files for a whole run into DIR (stops after a human "no").
  expected.py next --step N --prev FILE --token T [--answer yes|no]
      print the ONE correct step-N.json line given the previous step file and the token (what a good
      model/fake should reply). Needs no seed — exactly the information a real model is given.
  expected.py render --step N --run-dir D (--seed S | --run-id R)
      print the rendered prompt for step N ({{RUN_DIR}} and {{TOKEN}} filled), as the runner must.
  expected.py seed --run-id R      print the seed a run-id maps to.
  expected.py --selftest           internal consistency checks; last line 'SELFTEST expected OK'.
"""
import argparse, hashlib, json, os, pathlib, re, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
CARD = HERE / "card.txt"
PROMPTS = HERE / "prompts"
N_STEPS = 12
MENU = ("yes", "no")                      # the only legal human answers, lowercase, exact
KEYS = ("step", "token", "value", "facts")  # + "answer" on human steps only

# Made-up surnames for the telephone facts. Not people; not real content.
NAMES = ("Bramwick", "Quillon", "Tessaly", "Orvane", "Delphrey", "Mirrow", "Caskell", "Fennick",
         "Holloway", "Pradel", "Vosquin", "Ulbright", "Sarnow", "Kettridge", "Lomax", "Wendle")


def _h(*parts):
    """sha256 hex of 'canary|p1|p2|...' — the only source of randomness."""
    return hashlib.sha256("|".join(["canary"] + [str(p) for p in parts]).encode()).hexdigest()


def seed_for_run(run_id):
    """Default seed when the runner is not given --seed: first 8 hex of sha256('canary|run|<id>') mod 1e6."""
    return int(_h("run", run_id)[:8], 16) % 1_000_000


def token(seed, n):
    """Step n's token: 'T<nn>-<8 hex>'. Delivered ONLY through step n's own channel (see SPEC §3)."""
    return "T%02d-%s" % (n, _h(seed, "token", n)[:8])


def value1(seed):
    return int(_h(seed, "value")[:8], 16) % 1000


def next_value(prev, n):
    """value_n = (value_{n-1} * 3 + n) mod 1000, for n >= 2."""
    return (prev * 3 + n) % 1000


def facts(seed):
    """Five 'Name=NNN' strings. Names: seeded Fisher-Yates pick of 5 distinct from NAMES; numbers 100-999."""
    pool = list(NAMES)
    for i in range(len(pool) - 1, 0, -1):
        j = int(_h(seed, "shuffle", i)[:8], 16) % (i + 1)
        pool[i], pool[j] = pool[j], pool[i]
    return ["%s=%d" % (pool[k], 100 + int(_h(seed, "fact", k)[:8], 16) % 900) for k in range(5)]


def load_card(path=CARD):
    """-> (steps, meta). steps: [{id,n,kind,what,check}]; meta: {'chatty': ['s3',...], ...} from '#@ key: v v' lines."""
    steps, meta = [], {}
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("#@"):
            k, _, v = line[2:].partition(":")
            meta[k.strip()] = v.split()
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        sid, kind, what, check = (line.split(" | ", 3) + ["", "", ""])[:4]
        steps.append(dict(id=sid, n=int(sid[1:]), kind=kind, what=what, check=check))
    return steps, meta


def kinds(path=CARD):
    return {s["n"]: s["kind"] for s in load_card(path)[0]}


def record_from_prev(n, prev, tok, answer=None):
    """The correct step-n record given step-(n-1)'s record. Used by code steps, human.py, the fake, the oracle."""
    rec = {"step": n, "token": tok, "value": next_value(prev["value"], n), "facts": list(prev["facts"])}
    if answer is not None:
        if answer not in MENU:
            raise ValueError("off-menu answer %r (menu: %s)" % (answer, "/".join(MENU)))
        rec["answer"] = answer
    return rec


def record1(seed):
    return {"step": 1, "token": token(seed, 1), "value": value1(seed), "facts": facts(seed)}


def parse_answers(s):
    """'s4=yes,s9=no' -> {4:'yes', 9:'no'}"""
    out = {}
    for part in filter(None, (s or "").split(",")):
        k, _, v = part.partition("=")
        out[int(k.strip().lstrip("s"))] = v.strip()
    return out


def expected_run(seed, answers, card=CARD):
    """-> list of the records a correct run produces. Stops after the first human 'no' (the gate halts the run).
    A human step with no answer given ends the list BEFORE that step (the run is waiting)."""
    ks = kinds(card)
    recs = [record1(seed)]
    for n in range(2, N_STEPS + 1):
        ans = None
        if ks[n] == "human":
            if n not in answers:
                break
            ans = answers[n]
        recs.append(record_from_prev(n, recs[-1], token(seed, n), ans))
        if ans == "no":
            break
    return recs


def dumps(rec):
    """Canonical one-line form (key order step,token,value,facts[,answer]). Comparison is on PARSED JSON."""
    return json.dumps(rec, separators=(",", ":"))


def write_atomic(path, text):
    path = pathlib.Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def write_step(run_dir, rec):
    write_atomic(pathlib.Path(run_dir) / ("step-%d.json" % rec["step"]), dumps(rec) + "\n")


def render(n, run_dir, seed):
    """Rendered prompt for step n: {{RUN_DIR}} -> run_dir, {{TOKEN}} -> token(seed, n)."""
    text = (PROMPTS / ("s%d.md" % n)).read_text()
    return text.replace("{{RUN_DIR}}", str(run_dir)).replace("{{TOKEN}}", token(seed, n))


def _seed(args):
    if getattr(args, "seed", None) is not None:
        return args.seed
    if getattr(args, "run_id", None):
        return seed_for_run(args.run_id)
    sys.exit("expected.py: need --seed or --run-id")


def selftest():
    bad = []
    for s in (0, 1, 42, 999999):
        f = facts(s)
        if len(f) != 5 or len({x.split("=")[0] for x in f}) != 5:
            bad.append("facts-%d" % s)
        if len({token(s, n) for n in range(1, 13)}) != 12:
            bad.append("tokens-%d" % s)
    if token(1, 3) == token(2, 3) or facts(1) == facts(2):
        bad.append("seed-insensitive")
    steps, meta = load_card()
    k = [s["kind"] for s in steps]
    if (len(steps), k.count("ai"), k.count("code"), k.count("human")) != (12, 8, 2, 2):
        bad.append("card-shape")
    if [s["n"] for s in steps if s["kind"] == "human"] != [4, 9]:
        bad.append("human-at-4-9")
    if any(c not in [s["id"] for s in steps if s["kind"] == "ai"] for c in meta.get("chatty", [])):
        bad.append("chatty-not-ai")
    for n in range(1, 13):
        p = PROMPTS / ("s%d.md" % n)
        if steps[n - 1]["kind"] != "code":
            t = p.read_text()
            if len(t.rstrip("\n").split("\n")) != 2:
                bad.append("prompt-lines-s%d" % n)
            if re.search(r"/(Users|home)/|~/", t):
                bad.append("prompt-path-s%d" % n)
            if steps[n - 1]["kind"] == "ai" and "{{TOKEN}}" not in t:
                bad.append("prompt-token-s%d" % n)
    r = expected_run(7, {4: "yes", 9: "yes"})
    if len(r) != 12 or any(r[i]["value"] != next_value(r[i - 1]["value"], i + 1) for i in range(1, 12)):
        bad.append("chain")
    if len(expected_run(7, {4: "no"})) != 4 or len(expected_run(7, {})) != 3:
        bad.append("gate-stop")
    print("SELFTEST expected " + ("OK" if not bad else "FAIL " + ",".join(bad)))
    return 0 if not bad else 1


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    if argv[:1] in (["next"], ["render"], ["seed"]):
        cmd, argv = argv[0], argv[1:]
    else:
        cmd = "run"
    ap = argparse.ArgumentParser(prog="expected.py " + cmd)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--run-id")
    if cmd == "run":
        ap.add_argument("--answers", default="")
        ap.add_argument("--out", required=True)
    elif cmd == "next":
        ap.add_argument("--step", type=int, required=True)
        ap.add_argument("--prev", required=True)
        ap.add_argument("--token", required=True)
        ap.add_argument("--answer")
    elif cmd == "render":
        ap.add_argument("--step", type=int, required=True)
        ap.add_argument("--run-dir", required=True)
    a = ap.parse_args(argv)
    if cmd == "seed":
        print(seed_for_run(a.run_id)); return 0
    if cmd == "next":
        prev = json.loads(pathlib.Path(a.prev).read_text())
        print(dumps(record_from_prev(a.step, prev, a.token, a.answer))); return 0
    if cmd == "render":
        sys.stdout.write(render(a.step, a.run_dir, _seed(a))); return 0
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    recs = expected_run(_seed(a), parse_answers(a.answers))
    for r in recs:
        write_step(out, r)
    print("wrote %d step files to %s (seed=%d)" % (len(recs), out, _seed(a)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
