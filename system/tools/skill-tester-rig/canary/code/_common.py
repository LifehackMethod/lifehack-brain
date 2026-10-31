"""Shared bits for the canary's code-run steps. Seed comes ONLY from env CANARY_SEED (the runner exports it)."""
import json, os, pathlib, sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import expected  # noqa: E402


def seed():
    s = os.environ.get("CANARY_SEED", "")
    if not s.isdigit():
        sys.exit("canary: CANARY_SEED not set (the runner must export it)")
    return int(s)


def read_prev(run_dir, n):
    p = pathlib.Path(run_dir) / ("step-%d.json" % (n - 1))
    try:
        return json.loads(p.read_text())
    except Exception as e:
        sys.exit("canary: cannot read %s: %s" % (p, e))
