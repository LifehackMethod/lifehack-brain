#!/usr/bin/env python3
"""Tests for system/githooks/checks/hides_failure.py -- plant one mistake per rule in a scratch repo, watch each REFUSE.
Scratch repo lives under $TMPDIR (set it to the session scratchpad); the real repo is only read.
Run: python3 system/githooks/tests/test_check_hides_failure.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(os.path.dirname(HERE), "checks", "hides_failure.py")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FAILS = []


def sh(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


def new_repo():
    d = tempfile.mkdtemp(prefix="chk2-")
    for c in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"]):
        sh(d, *c)
    return d


def put(d, rel, text):
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)
    sh(d, "git", "add", rel)


def run(d, *args):
    r = subprocess.run([sys.executable, CHECK, *args], cwd=d, capture_output=True, text=True)
    fs = [json.loads(l[8:]) for l in r.stderr.splitlines() if l.startswith("FINDING ")]
    return r.returncode, fs, r.stderr


def expect(name, ok, extra=""):
    print(("ok   " if ok else "FAIL ") + name + (" -- " + extra if extra and not ok else ""))
    if not ok:
        FAILS.append(name)


# one planted mistake per rule: (rule, file, text, expected line)
PLANTS = [
    ("silenced-error", "a.sh", "#!/usr/bin/env bash\nset -u\ngws gmail users messages list --params x || true\n", 3),
    ("silenced-error", "a2.sh", "#!/usr/bin/env bash\ncurl -s https://x.example/api 2>/dev/null\n", 2),
    ("empty-except", "a.py", "import os\ntry:\n    os.remove('x')\nexcept Exception:\n    pass\n", 4),
    ("empty-except", "a2.py", "try:\n    int('x')\nexcept:\n    print('hi')\n", 3),
    ("model-id", "m.sh", "#!/usr/bin/env bash\nclaude -p --model claude-haiku-5-5 \"hi\"\n", 2),
    ("model-id", "m.py", "ID = 'claude-sonnet-5-5'\n", 1),
    ("tmp-path", "t.sh", "#!/usr/bin/env bash\necho hi > /tmp/out.txt\n", 2),
    ("python-path", "p.sh", "#!/usr/bin/env bash\n/usr/bin/python3 tool.py\n", 2),
    ("python-path", "p2.py", "#!/usr/bin/python3\nprint(1)\n", 1),
    ("raw-google-curl", "g.sh", "#!/usr/bin/env bash\ncurl -s -H \"Authorization: Bearer $T\" https://gmail.googleapis.com/gmail/v1/users/me/messages\n", 2),
    ("raw-google-curl", "g2.sh", "#!/usr/bin/env bash\ncurl -s \\\n  https://www.googleapis.com/gmail/v1/users/me/threads\n", 2),
    ("vacuous-checker", "check_skills.sh", "#!/usr/bin/env bash\nfor f in skills/*/SKILL.md; do\n  grep -q name \"$f\" || echo bad >&2\ndone\n", 2),
    ("vacuous-checker", "lint_x.py", "import glob\nfor p in glob.glob('skills/*.md'):\n    print(p)\n", 2),
    ("vacuous-checker", "run.sh", "#!/usr/bin/env bash\n# validates every skill file\nfind skills -name '*.md' | while read -r f; do echo \"$f\"; done\n", 3),
]
for rule, f, text, line in PLANTS:
    d = new_repo()
    put(d, f, text)
    rc, fs, err = run(d)
    hit = [x for x in fs if x["rule"] == rule and x["line"] == line and x["file"] == f and x["status"] == "refused"]
    expect(f"REFUSED {rule} at {f}:{line}", rc == 1 and bool(hit), err.strip()[:200])
    if rc == 1 and hit:
        print(f"       -> {err.splitlines()[0]}")

# the same lines with allow-silence -> pass, reported
ALLOWED = [
    ("a.sh", "#!/usr/bin/env bash\ngws gmail users messages list --params x || true  # allow-silence: probe, absence is fine\n"),
    ("a.py", "try:\n    int('x')\nexcept Exception:  # allow-silence: best-effort cleanup\n    pass\n"),
    ("m.py", "ID = 'claude-sonnet-5-5'  # allow-silence: documents a retired id\n"),
    ("t.sh", "#!/usr/bin/env bash\necho hi > /tmp/out.txt  # allow-silence: fixed path is the contract\n"),
    ("p.sh", "#!/usr/bin/env bash\n/usr/bin/python3 tool.py  # allow-silence: system tool\n"),
    ("g.sh", "#!/usr/bin/env bash\ncurl -s https://gmail.googleapis.com/gmail/v1/x  # allow-silence: one-off probe\n"),
    ("check_skills.sh", "#!/usr/bin/env bash\nfor f in skills/*/SKILL.md; do  # empty-ok: caller guarantees a non-empty set\n  echo \"$f\"\ndone\n"),
    ("c.sh", "#!/usr/bin/env bash\ngws gmail users messages list \\\n  --params x || true  # allow-silence: continued line\n"),
]
for f, text in ALLOWED:
    d = new_repo()
    put(d, f, text)
    rc, fs, err = run(d)
    expect(f"allow-silence passes and is reported ({f})", rc == 0 and len(fs) >= 1 and all(x["status"] == "allowed" and x["reason"] for x in fs), err.strip()[:200])

# an empty reason is NOT an escape hatch
d = new_repo()
put(d, "a.sh", "#!/usr/bin/env bash\ngws gmail users messages list --params x || true  # allow-silence:\n")
expect("allow-silence with no reason still refuses", run(d)[0] == 1)

# old backlog: existing `|| true`, unrelated line changed -> pass
d = new_repo()
put(d, "old.sh", "#!/usr/bin/env bash\ngws gmail users messages list --params x || true\necho one\n")
sh(d, "git", "commit", "-qm", "base")
put(d, "old.sh", "#!/usr/bin/env bash\ngws gmail users messages list --params x || true\necho two\n")
rc, fs, err = run(d)
expect("old || true with an unrelated changed line passes", rc == 0 and not fs, err.strip()[:200])

# clean script (tier names, $TMPDIR, env python3, harmless 2>/dev/null) -> pass
d = new_repo()
put(d, "ok.sh", "#!/usr/bin/env bash\n. \"$ROOT/model.lib.sh\"\nrun_model small p.txt o.txt || exit 1\nW=\"${TMPDIR:-/tmp}/w\"\nkill -0 \"$$\" 2>/dev/null\nif ! gws x; then echo bad >&2; exit 1; fi\n")
put(d, "ok.py", "#!/usr/bin/env python3\nimport tempfile\ntry:\n    int('1')\nexcept ValueError as e:\n    raise SystemExit(str(e))\n")
rc, fs, err = run(d)
expect("clean scripts pass", rc == 0 and not fs, err.strip()[:300])

# tests and fixtures are exempt
d = new_repo()
put(d, "system/tools/tests/t.sh", "#!/usr/bin/env bash\necho x > /tmp/a || true\n")
put(d, "system/tools/fixtures/f.py", "ID = 'claude-opus-5-5'\n")
put(d, "pkg/test_x.py", "try:\n    pass\nexcept:\n    pass\n")
rc, fs, err = run(d)
expect("tests and fixtures are exempt", rc == 0 and not fs, err.strip()[:200])

# non-script files are ignored
d = new_repo()
put(d, "notes.md", "run `x || true` against /tmp/ with claude-haiku-5-5\n")
expect("markdown ignored", run(d)[0] == 0)

# allowed variants: guarded checker, non-checker loop, exempt shared tool / safe reader, non-Google curl
d = new_repo()
put(d, "check_ok.sh", "#!/usr/bin/env bash\nn=0\nfor f in skills/*/SKILL.md; do n=$((n+1)); done\n[ \"$n\" -eq 0 ] && { echo 'nothing checked' >&2; exit 1; }\n")
put(d, "lint_ok.py", "import glob\nfiles = glob.glob('*.md')\nif not files:\n    raise SystemExit('0 files checked')\nfor p in files:\n    print(p)\n")
put(d, "copy_all.sh", "#!/usr/bin/env bash\nfor f in src/*; do cp \"$f\" dst/; done\n")
put(d, "shared/tools/email_fetch.py", "import subprocess\nsubprocess.run(['curl','https://gmail.googleapis.com/gmail/v1/users/me/messages'])\n")
put(d, "system/tools/safe_mail.sh", "#!/usr/bin/env bash\ncurl -s https://gmail.googleapis.com/gmail/v1/x\n")
put(d, "api.sh", "#!/usr/bin/env bash\ncurl -s https://x.example/v1/x\n")
rc, fs, err = run(d)
expect("guarded checker / non-checker loop / exempt gmail tools / non-Google curl pass", rc == 0 and not fs, err.strip()[:300])

# the real repo, nothing staged -> exit 0
rc, fs, err = run(REPO)
staged = sh(REPO, "git", "diff", "--cached", "--name-only").stdout.strip()
if staged:
    print("SKIP real-repo nothing-staged case: something is staged in the real repo")
else:
    expect("real repo with nothing staged exits 0", rc == 0 and not fs, err.strip()[:200])

print("\n%d FAILED" % len(FAILS) if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
