# origin: 92a9739:mover/tests/gsrun.py
"""Run Code.gs under node with the pretend Gmail + Drive (harness.js). Test helper."""
import json, subprocess, tempfile
from pathlib import Path

MOVER = Path(__file__).resolve().parent.parent
LABELS = [{"id": "INBOX", "name": "INBOX", "type": "system"}, {"id": "TRASH", "name": "TRASH", "type": "system"},
          {"id": "Label_1", "name": "Projects/Alpha", "type": "user"}, {"id": "Label_2", "name": "Archive-Me", "type": "user"}]


def ids(n, start=0):
    return ["%016x" % (0xabc000 + start + i) for i in range(n)]


def req(actions, rid="req-test-0001"):
    return {"request_id": rid, "created_at": "2026-11-12T10:00:00Z", "actions": actions}


def gs(steps, messages=None, constants=None, labels=None, per_call_ms=0, read_mode=None):
    spec = {"labels": labels or LABELS, "messages": messages or {}, "constants": constants or {},
            "per_call_ms": per_call_ms, "steps": steps}
    if read_mode:
        spec["read_mode"] = read_mode
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "spec.json"
        p.write_text(json.dumps(spec))
        r = subprocess.run(["node", str(MOVER / "tests" / "harness.js"), str(MOVER / "Code.gs"), str(p)],
                           capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def submit(rq):
    return [{"mac_write": {"name": "request.json", "content": json.dumps(rq)}}, {"call": "run"}]


def result(out):
    return json.loads(out["files"]["result.json"]["content"])
