#!/usr/bin/env python3
# from orchestrator-v2/rig/stress/inject.sh @ 2026-10-28
#   (kept: the record-truncate transform — cut ONE row to run/step/status + a partial 4th field, newline kept,
#    nothing earlier/later touched; rewritten: it targets the row of a named step instead of the last row,
#    and the rest of this file is new — contract-template matching and synthetic worlds for the selftest.)
"""inject/helper.py — small pure-code helpers for inject.sh (TR1.5). No model, no network, no clock.

  helper.py realpath P                       print os.path.realpath(P)
  helper.py truncate-row RECORD sN           damage the first row whose field 2 == sN; print its 1-based line no
  helper.py valid-row RECORD RUN_ID sN       exit 0 iff a VALID row (CONTRACT §2) exists for sN
  helper.py mkrow RUN_ID sN STATUS EPOCH SHA MODEL     print one valid record row (with rowsum), no newline
  helper.py mkworld RUN_DIR SEED RIG PID [--upto N] [--open N]
        synthetic run for the selftest: step files from canary/expected.py (its CLI), record.tsv with valid
        rows, exec.log begin/end lines carrying PID. --open N leaves sN begun (no end, no file, no row).
  helper.py edit-fact STEPFILE               F-06b: change one fact's number in a committed step file
  helper.py match CONTRACT.md FILE...        every row's 3rd field must FULLY match one CONTRACT §3 fixed form;
                                             prints 'TEMPLATES <n>' and one 'BAD ...' line per miss; exit 0/1
"""
import hashlib, json, os, pathlib, re, subprocess, sys

CATS = ("ok", "silent_wrong", "double_ran", "stuck", "lost", "skipped", "out_of_order", "false_done")


def rowsum(fields6):
    return hashlib.sha256("\t".join(fields6).encode()).hexdigest()[:12]


def mkrow(run_id, sid, status, epoch, sha, model):
    f = [run_id, sid, status, str(epoch), sha, model]
    return "\t".join(f + [rowsum(f)])


def valid_rows(path, run_id):
    """-> list of (lineno, fields) for VALID rows: 7 fields, this run-id, correct rowsum, final newline."""
    out = []
    data = pathlib.Path(path).read_bytes().decode("utf-8", "replace")
    lines = data.split("\n")
    for i, line in enumerate(lines[:-1], 1):          # last element is after the final newline (or a partial row)
        f = line.split("\t")
        if len(f) == 7 and f[0] == run_id and rowsum(f[:6]) == f[6]:
            out.append((i, f))
    return out


def truncate_row(path, sid):
    b = pathlib.Path(path).read_bytes()
    lines = b.split(b"\n")
    for i, line in enumerate(lines):
        f = line.split(b"\t")
        if len(f) > 1 and f[1] == sid.encode():
            new = b"\t".join(f[:3]) + b"\t" + f[3][:10] if len(f) > 3 else f[0][:20]
            lines[i] = new
            tmp = path + ".inject.tmp"
            with open(tmp, "wb") as fh:
                fh.write(b"\n".join(lines))
            os.replace(tmp, path)
            print(i + 1)
            return 0
    print("no row for %s" % sid, file=sys.stderr)
    return 1


def mkworld(run_dir, seed, rig, pid, upto=12, open_step=None):
    run_dir = pathlib.Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    gen = run_dir.parent / (".gen-" + run_dir.name)
    subprocess.run([sys.executable, "-I", str(pathlib.Path(rig) / "canary" / "expected.py"), "--seed", str(seed),
                    "--answers", "s4=yes,s9=yes", "--out", str(gen)], check=True, stdout=subprocess.DEVNULL)
    run_id = run_dir.name
    rec, ex = [], []
    last = upto if open_step is None else open_step - 1
    for n in range(1, last + 1):
        src = gen / ("step-%d.json" % n)
        dst = run_dir / src.name
        dst.write_bytes(src.read_bytes())
        sha = hashlib.sha256(dst.read_bytes()).hexdigest()
        ex.append("%d\ts%d\tbegin\t%s" % (1000 + n, n, pid))
        ex.append("%d\ts%d\tend\t%s" % (1000 + n, n, pid))
        rec.append(mkrow(run_id, "s%d" % n, "done", 1000 + n, sha, "-" if n in (1, 4, 7, 9) else "fake-model-A"))
    if open_step is not None:
        ex.append("%d\ts%d\tbegin\t%s" % (1000 + open_step, open_step, pid))
    for f in gen.iterdir():
        f.unlink()
    gen.rmdir()
    (run_dir / "record.tsv").write_text("".join(r + "\n" for r in rec))
    (run_dir / "exec.log").write_text("".join(e + "\n" for e in ex))
    (run_dir / "meta.env").write_text("RUN_ID=%s\nCARD=canary\nMODEL_ID=fake-model-A\nFAKE_MODE=good\nSTART=0\n" % run_id)


def templates(contract):
    """Parse CONTRACT §3's fenced block into full-line regexes. Lines are '  FORM   description'."""
    text = pathlib.Path(contract).read_text()
    m = re.search(r"^## 3\..*?```\n(.*?)```", text, re.S | re.M)
    if not m:
        return []
    out, forms, cats = [], [], None
    for raw in m.group(1).splitlines():
        if re.match(r"  \S", raw):                         # a form line: exactly two leading spaces
            form, _, desc = raw.strip().partition("  ")
            forms.append(form.strip())
            c = re.search(r"<cat> ∈ ([a-z -]+)", desc)
            if c:
                cats = c.group(1).split()
        elif raw.startswith("   "):                        # continuation: an extra form named as ALSO `FORM`
            forms += re.findall(r"ALSO `([^`]+)`", raw)
        # anything else (section labels like "events.log (runner):") is not a form
    for form in forms:
        rx = ""
        for tok in re.split(r"(sN|<[a-z-]+>|\.\.)", form):
            if tok == "sN":
                rx += r"s(?:[1-9]|1[0-2])"
            elif tok == "..":
                rx += r"\d+"
            elif tok in ("<rc>", "<k>"):
                rx += r"-?\d+"
            elif tok in ("<old>", "<new>"):
                rx += r"\S+"
            elif tok in ("<path>", "<relpath>"):
                rx += r".+"
            elif tok == "<cat>":
                if not cats:
                    raise SystemExit("CONTRACT §3: <cat> used but its set ('<cat> ∈ ...') was not found")
                rx += "(?:" + "|".join(map(re.escape, cats)) + ")"
            elif tok in ("<d>",):
                rx += r"\d+"
            elif tok == "<check>":
                rx += r"\S+"
            elif tok == "<category>":
                rx += "(?:" + "|".join(CATS) + ")"
            elif tok.startswith("<"):
                rx += r".+"
            else:
                rx += re.escape(tok)
        out.append((form, re.compile(rx + r"\Z")))
    return out


def edit_fact(path):
    """F-06b: change the NUMBER of the first fact in a committed step file (name kept, list length kept);
    rewrite in the canonical one-line form. Prints 'old -> new'."""
    p = pathlib.Path(path)
    rec = json.loads(p.read_text())
    name, num = rec["facts"][0].split("=")
    new = "%s=%d" % (name, 100 + (int(num) - 100 + 1) % 900)
    old, rec["facts"][0] = rec["facts"][0], new
    tmp = str(p) + ".inject.tmp"
    pathlib.Path(tmp).write_text(json.dumps(rec, separators=(",", ":")) + "\n")
    os.replace(tmp, p)
    print("%s -> %s" % (old, new))


def match(contract, files):
    t = templates(contract)
    print("TEMPLATES %d" % len(t))
    bad = 0
    for fn in files:
        for i, line in enumerate(pathlib.Path(fn).read_text().splitlines(), 1):
            f = line.split("\t")
            if len(f) != 3:
                print("BAD %s:%d field-count %d" % (fn, i, len(f))); bad += 1; continue
            if not any(rx.match(f[2]) for _, rx in t):
                print("BAD %s:%d no-form %r" % (fn, i, f[2])); bad += 1
    return 0 if (bad == 0 and len(t) >= 17) else 1


def main(a):
    cmd = a[0] if a else ""
    if cmd == "realpath":
        print(os.path.realpath(a[1])); return 0
    if cmd == "truncate-row":
        return truncate_row(a[1], a[2])
    if cmd == "valid-row":
        return 0 if any(f[1] == a[3] for _, f in valid_rows(a[1], a[2])) else 1
    if cmd == "mkrow":
        sys.stdout.write(mkrow(*a[1:7])); return 0
    if cmd == "mkworld":
        upto, open_step = 12, None
        rest = a[5:]
        while rest:
            if rest[0] == "--upto":
                upto = int(rest[1])
            elif rest[0] == "--open":
                open_step = int(rest[1])
            rest = rest[2:]
        mkworld(a[1], int(a[2]), a[3], a[4], upto, open_step); return 0
    if cmd == "edit-fact":
        edit_fact(a[1]); return 0
    if cmd == "match":
        return match(a[1], a[2:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
