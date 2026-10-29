#!/usr/bin/env python3
"""test_new_tool_gate.py — v2 step 1.3: the pre-commit NEW-TOOL REGISTRATION GATE, and harvest's
shared/ coverage + --update-register.

The gate is the block of system/githooks/pre-commit between its "NEW-TOOL REGISTRATION GATE" banner and
the "WIRING-DRIFT CHECK" banner. It is extracted and run alone in a throwaway git repo, so the test needs
no gitleaks / leak-scanner / identity file (the other stages fail closed without them).

Run directly:  python3 system/register/tests/test_new_tool_gate.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))
sys.path.insert(0, REGISTER_DIR)

HOOK = os.path.join(REPO_ROOT, "system", "githooks", "pre-commit")
REG = "system/register/register.jsonl"


def gate_script():
    text = open(HOOK, encoding="utf-8").read()
    a = text.index("# NEW-TOOL REGISTRATION GATE")
    a = text.rindex("# ───", 0, a)
    b = text.index("# WIRING-DRIFT CHECK")
    b = text.rindex("# ───", 0, b)
    return text[a:b]


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True,
                          env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"})


def make_repo(files, register_rows):
    d = tempfile.mkdtemp()
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    write(d, REG, "".join(json.dumps(r) + "\n" for r in register_rows))
    for p, c in files.items():
        write(d, p, c)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "base", "--no-verify")
    return d


def write(d, rel, content):
    full = os.path.join(d, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


def row(path):
    return {"id": f"tool:public:/{path}", "type": "tool", "repo": "public", "path": "/" + path}


def run_gate(d):
    r = subprocess.run(["sh", "-c", gate_script()], cwd=d, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def test_refuses_added_unregistered_tool():
    d = make_repo({}, [])
    write(d, "system/tools/zz_new.sh", "echo hi\n")
    git(d, "add", "system/tools/zz_new.sh")
    rc, out = run_gate(d)
    assert rc == 1 and "COMMIT REFUSED" in out and "harvest.py --update-register" in out, (rc, out)
    assert "system/tools/zz_new.sh" in out


def test_refuses_added_unregistered_shared_file():
    d = make_repo({}, [])
    write(d, "shared/tools/new_thing.py", "x = 1\n")
    git(d, "add", "shared/tools/new_thing.py")
    assert run_gate(d)[0] == 1


def test_allows_added_tool_with_staged_register_row():
    d = make_repo({}, [])
    write(d, "system/tools/zz_new.sh", "echo hi\n")
    write(d, REG, json.dumps(row("system/tools/zz_new.sh")) + "\n")
    git(d, "add", "-A")
    rc, out = run_gate(d)
    assert rc == 0, out


def test_row_must_be_staged_not_just_on_disk():
    d = make_repo({}, [])
    write(d, "system/tools/zz_new.sh", "echo hi\n")
    git(d, "add", "system/tools/zz_new.sh")
    write(d, REG, json.dumps(row("system/tools/zz_new.sh")) + "\n")  # edited, NOT staged
    assert run_gate(d)[0] == 1


def test_modification_does_not_fire():
    d = make_repo({"system/tools/old.sh": "a\n"}, [])  # tracked, unregistered (the backlog)
    write(d, "system/tools/old.sh", "b\n")
    git(d, "add", "-A")
    assert run_gate(d)[0] == 0


def test_deletion_does_not_fire():
    d = make_repo({"system/tools/old.sh": "a\n"}, [])
    git(d, "rm", "-q", "system/tools/old.sh")
    assert run_gate(d)[0] == 0


def test_test_class_and_other_paths_exempt():
    d = make_repo({}, [])
    for p in ("system/tools/test_x.py", "system/tools/tests/helper.py", "shared/test_y.py",
              "system/tools/fixtures/conform/a/run.sh", "system/tools/README.md",
              "docs/thing.sh", "system/hooks/h.sh"):
        write(d, p, "x\n")
    git(d, "add", "-A")
    rc, out = run_gate(d)
    assert rc == 0, out


def test_harvest_covers_shared_and_skips_tests():
    import harvest
    pub = tempfile.mkdtemp()
    write(pub, "shared/a.py", "")
    write(pub, "shared/sub/b.sh", "")
    write(pub, "shared/test_a.py", "")
    write(pub, "system/tools/fixtures/f/run.sh", "")
    rows = harvest.harvest_tools(pub, os.path.join(pub, "nonexistent"))
    assert sorted(r["path"] for r in rows) == ["/shared/a.py", "/shared/sub/b.sh"], rows


def test_update_register_keeps_hooks_and_curated_fields():
    import harvest
    d = tempfile.mkdtemp()
    reg = os.path.join(d, "r.jsonl")
    hook = {"id": "hook:public:/x@Stop:", "type": "hook", "repo": "public", "sha": "old"}
    tool = {**row("shared/a.py"), "sha": "old", "needs": ["lock.x"], "returns": []}
    gone = row("shared/gone.py")
    with open(reg, "w", encoding="utf-8") as f:
        for r in (hook, tool, gone):
            f.write(json.dumps(r) + "\n")
    fresh = [{**row("shared/a.py"), "sha": "new", "needs": [], "returns": []},
             {**row("shared/new.py"), "sha": "n"},
             {"id": "hook:public:/other@Stop:", "type": "hook", "repo": "public"}]
    out, added, dropped = harvest.merge_into_register(fresh, reg)
    by = {r["id"]: r for r in out}
    assert by[hook["id"]]["sha"] == "old"                      # hook row untouched
    assert by[tool["id"]]["sha"] == "new" and by[tool["id"]]["needs"] == ["lock.x"]
    assert added == ["tool:public:/shared/new.py"] and dropped == [gone["id"]]
    assert "hook:public:/other@Stop:" not in by                # fresh hook rows never imported


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\nRESULT: {len(TESTS) - failed} passed, {failed} failed.")
    sys.exit(1 if failed else 0)
