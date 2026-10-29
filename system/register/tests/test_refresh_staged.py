#!/usr/bin/env python3
"""test_refresh_staged.py -- v2 step 1.3b: pre-commit refreshes the register's derived fields for STAGED files.

Each test runs the REAL pre-commit hook (all stages) in a throwaway `git clone --no-hardlinks` of this repo,
with an ABSOLUTE core.hooksPath, so nothing here can touch the real repo. The clone's hook + refresh script
are overlaid from this working tree so the code under test is what is on disk now.

Run directly:  python3 system/register/tests/test_refresh_staged.py
Scratch parent: $REFRESH_TEST_SCRATCH if set, else the system temp dir.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))
REG = "system/register/register.jsonl"
OVERLAY = ("system/githooks/pre-commit", "system/register/refresh_staged.py", "system/register/toolbox.py",
           "system/githooks/report_checks.sh", "system/githooks/checks/connected.py",
           "system/githooks/checks/hides_failure.py", "system/githooks/checks/is_copy.py",
           "system/githooks/checks/safe_to_ship.py", "system/hooks/lib/journal.sh",
           "system/hooks/lib/build_mode.py", "system/tools/door_rules.py",
           ".github/scripts/check_no_internal_leakage.py", "system/hooks/placement.conf")
NOTICE = re.compile(r"^pre-commit: refreshed register sha for (\d+) staged file\(s\): (.+)$", re.M)
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "LHB_JOURNAL_DISABLE": "1",
       "LHB_PRECOMMIT_FINDINGS": "/dev/null"}


def git(cwd, *args, **kw):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, env=ENV, **kw)


def make_clone():
    parent = os.environ.get("REFRESH_TEST_SCRATCH") or tempfile.gettempdir()
    os.makedirs(parent, exist_ok=True)
    d = tempfile.mkdtemp(prefix="refresh-clone-", dir=parent)
    shutil.rmtree(d)
    r = subprocess.run(["git", "clone", "-q", "--no-hardlinks", REPO_ROOT, d], capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr
    for rel in OVERLAY:
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        shutil.copy2(os.path.join(REPO_ROOT, rel), os.path.join(d, rel))
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    git(d, "config", "core.hooksPath", os.path.join(d, "system", "githooks"))  # absolute
    # Bring the clone's register to a FRESH baseline so every test starts from "CI would pass".
    run_harvest_update(d)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "baseline", "--no-verify")
    return d


def run_harvest_update(d):
    r = subprocess.run([sys.executable, "system/register/harvest.py", "--no-cache", "--update-register", REG],
                       cwd=d, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr


def rows(text):
    return {json.loads(l)["id"]: json.loads(l) for l in text.splitlines() if l.strip()}


def head_rows(d):
    return rows(git(d, "show", "HEAD:" + REG).stdout)


def pick_tool(d):
    """A public, hand-annotated-or-not tool row whose file is a small .sh/.py with no special handling."""
    for rid, r in rows(open(os.path.join(d, REG), encoding="utf-8").read()).items():
        if r["type"] == "tool" and r["repo"] == "public" and r["path"].startswith("/system/tools/") \
                and r["path"].endswith(".sh") and os.path.isfile(d + r["path"]):
            return r["path"][1:], rid
    raise AssertionError("no suitable registered tool")


def append(d, rel, text):
    with open(os.path.join(d, rel), "a", encoding="utf-8") as f:
        f.write(text)


def commit(d, msg="t"):
    r = git(d, "commit", "-qm", msg)
    return r.returncode, r.stdout + r.stderr


def ci_freshness(d):
    """Run the CI 'Register freshness' step's own python, extracted from the workflow, against a fresh harvest."""
    wf = open(os.path.join(d, ".github/workflows/register-drift.yml"), encoding="utf-8").read()
    m = re.search(r"python3 - \"\$RUNNER_TEMP/fresh-register.jsonl\" <<'PY'\n(.*?)\n\s*PY\n", wf, re.S)
    body = m.group(1)
    indent = len(body) - len(body.lstrip(" "))
    body = "\n".join(l[indent:] for l in body.split("\n"))
    fresh = os.path.join(d, ".fresh-register.jsonl")
    h = subprocess.run([sys.executable, "system/register/harvest.py", "--no-cache", "--out", fresh],
                       cwd=d, capture_output=True, text=True, env=ENV)
    assert h.returncode == 0, h.stderr
    r = subprocess.run([sys.executable, "-c", body, fresh], cwd=d, capture_output=True, text=True, env=ENV)
    os.remove(fresh)
    return r.returncode, r.stdout + r.stderr


def test_a_edit_registered_tool_refreshes_sha_in_same_commit():
    d = make_clone()
    path, rid = pick_tool(d)
    before = head_rows(d)[rid]["sha"]
    append(d, path, "\n# edited by test\n")
    git(d, "add", path)
    code, out = commit(d)
    assert code == 0, out
    m = NOTICE.search(out)
    assert m and m.group(1) == "1" and m.group(2).strip() == path, out
    assert len(NOTICE.findall(out)) == 1
    after = head_rows(d)[rid]["sha"]
    assert after != before
    assert git(d, "status", "--porcelain").stdout.strip() == "", "tree should be clean: register in the commit AND working copy"
    code, out = ci_freshness(d)
    assert code == 0, out
    print("  (a) notice: " + m.group(0))
    print("  (a) CI freshness: " + out.strip().splitlines()[-1])


def test_b_unrelated_unstaged_register_edit_is_not_committed():
    d = make_clone()
    path, rid = pick_tool(d)
    other = next(i for i, r in rows(open(os.path.join(d, REG), encoding="utf-8").read()).items()
                 if r["type"] == "tool" and i != rid)
    append(d, path, "\n# edited by test\n")
    git(d, "add", path)
    text = open(os.path.join(d, REG), encoding="utf-8").read().split("\n")
    for i, l in enumerate(text):
        if l.strip() and json.loads(l)["id"] == other:
            r = json.loads(l)
            r["needs"] = ["UNSTAGED-MARKER"]
            text[i] = json.dumps(r, sort_keys=True, ensure_ascii=False)
    with open(os.path.join(d, REG), "w", encoding="utf-8") as f:
        f.write("\n".join(text))
    code, out = commit(d)
    assert code == 0, out
    committed = head_rows(d)
    assert committed[other]["needs"] != ["UNSTAGED-MARKER"], "unstaged edit leaked into the commit"
    assert "UNSTAGED-MARKER" not in git(d, "show", "HEAD:" + REG).stdout
    work = rows(open(os.path.join(d, REG), encoding="utf-8").read())
    assert work[other]["needs"] == ["UNSTAGED-MARKER"], "the unstaged edit must survive in the working copy"
    assert work[rid]["sha"] == committed[rid]["sha"], "working copy should carry the refreshed row too"
    print("  (b) unstaged edit stayed out of the commit and survived in the working copy")


def test_c_hand_written_fields_unchanged():
    d = make_clone()
    path, rid = pick_tool(d)
    # give the row hand-written values, commit them, then edit the tool
    lines = open(os.path.join(d, REG), encoding="utf-8").read().split("\n")
    for i, l in enumerate(lines):
        if l.strip() and json.loads(l)["id"] == rid:
            r = json.loads(l)
            r.update(needs=["x"], returns=["y"], cost_bytes=123, cost_ms=7)
            lines[i] = json.dumps(r, sort_keys=True, ensure_ascii=False)
    with open(os.path.join(d, REG), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    git(d, "add", REG)
    git(d, "commit", "-qm", "hand fields", "--no-verify")
    old = head_rows(d)[rid]
    append(d, path, "\n# edited by test\n")
    git(d, "add", path)
    code, out = commit(d)
    assert code == 0, out
    new = head_rows(d)[rid]
    assert new["sha"] != old["sha"]
    for k in old:
        if k != "sha":
            assert new[k] == old[k], "field %s changed: %r -> %r" % (k, old[k], new[k])
    assert (new["needs"], new["returns"], new["cost_bytes"], new["cost_ms"]) == (["x"], ["y"], 123, 7)
    print("  (c) only `sha` changed; needs/returns/cost_bytes/cost_ms intact")


def test_d_corrupt_staged_register_refuses_commit():
    d = make_clone()
    path, rid = pick_tool(d)
    append(d, path, "\n# edited by test\n")
    with open(os.path.join(d, REG), "a", encoding="utf-8") as f:
        f.write("{this is not json\n")
    git(d, "add", path, REG)
    head = git(d, "rev-parse", "HEAD").stdout
    code, out = commit(d)
    assert code != 0, "commit must be refused"
    assert "COMMIT REFUSED" in out and "not valid JSON" in out, out
    assert git(d, "rev-parse", "HEAD").stdout == head
    print("  (d) refused: " + [l.strip() for l in out.splitlines() if "REFUSED:" in l][0])


def test_e_commit_touching_no_registered_file_is_silent():
    d = make_clone()
    with open(os.path.join(d, "NOTES-test.md"), "w", encoding="utf-8") as f:
        f.write("hello\n")
    git(d, "add", "NOTES-test.md")
    before = git(d, "show", "HEAD:" + REG).stdout
    code, out = commit(d)
    assert code == 0, out
    assert "refreshed register" not in out
    assert git(d, "show", "HEAD:" + REG).stdout == before
    assert git(d, "show", "--stat", "--format=", "HEAD").stdout.count(REG) == 0
    print("  (e) no notice, register untouched")


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS " + name)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print("FAIL %s: %s" % (name, e))
    sys.exit(1 if failed else 0)
