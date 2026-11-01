#!/usr/bin/env python3
"""test_on_failure_field.py — PHASE 3b.7 A2: a hook row may carry an OPTIONAL `on_failure`
("continue" | "block"), emitted into the wiring as the command hook's `onFailure` field.

Why: Claude Code's hooks page (code.claude.com/docs/en/hooks, read 2026-11-01) lists, in the
command-hook field table: "onFailure — Whether the action that triggered the hook goes ahead when
the hook fails: "continue" or "block"", and "To block the action instead, set "onFailure": "block"
on a command or http hook. Requires Claude Code v2.1.295 or later." Without it, a hook that cannot
start (missing file, no bash) is a non-blocking error and the action goes ahead. The connector door
(sanitize_connector_output.sh) fails closed for every error it can see; this closes the one it
cannot: not being started at all.

Run directly (no pytest): python3 system/register/tests/test_on_failure_field.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))
sys.path.insert(0, REGISTER_DIR)

import generate  # noqa: E402
import validate_register  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(("  ok   " if ok else "  FAIL ") + name + ("" if ok else "  :: " + str(detail)))


def hook_row(**over):
    row = {"args": "", "cost_bytes": None, "cost_ms": None, "event": "PostToolUse", "exists": True,
           "expiry": None, "group": None, "id": "hook:public:/system/hooks/x.sh@PostToolUse:mcp__.*",
           "if": None, "launch_mode": "both", "matcher": "mcp__.*", "needs": [],
           "path": "/system/hooks/x.sh", "protects_permissions": [], "repo": "public", "returns": [],
           "sha": "", "state": "active", "status": "", "status_conflicts": [],
           "surfaces": ["plugin", "settings"], "type": "hook"}
    row.update(over)
    return row


def errs(row):
    return validate_register.validate_row(row, 1)


print("-- schema: on_failure is optional, closed to continue|block, hooks only --")
base = hook_row()
check("a hook row WITHOUT on_failure is still valid (every other row is untouched)", errs(base) == [], errs(base))
for v in ("block", "continue"):
    e = errs(hook_row(on_failure=v))
    check("on_failure=%r accepted" % v, e == [], e)
e = errs(hook_row(on_failure="maybe"))
check("on_failure='maybe' rejected", e and any("on_failure" in x for x in e), e)
e = errs(hook_row(on_failure=True))
check("on_failure=True (not a string) rejected", e and any("on_failure" in x for x in e), e)
e = errs(hook_row(onFailure="block"))
check("the wiring spelling 'onFailure' is NOT a register key (strict unknown keys)", e and any("onFailure" in x for x in e), e)

print("-- generator: onFailure emitted only where the row carries it --")
doc = generate.build_hooks_doc([hook_row(on_failure="block"), hook_row(path="/system/hooks/y.sh", status="s")], "plugin")
hs = doc["hooks"]["PostToolUse"][0]["hooks"]
check("row with on_failure=block -> entry has onFailure: block", hs[0].get("onFailure") == "block", hs[0])
check("row without on_failure -> entry has no onFailure key", "onFailure" not in hs[1], hs[1])
check("onFailure comes after command/statusMessage (existing key order kept)",
      list(hs[0].keys())[:2] == ["type", "command"], list(hs[0].keys()))
col = generate.collapse_group_rows([hook_row(on_failure="block")])
check("collapse_group_rows passes an ungrouped row's on_failure through", col[0].get("on_failure") == "block", col)

print("-- the committed wiring: the connector door carries onFailure: block on both surfaces --")
for rel in ("hooks/hooks.json", ".claude/settings.json"):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as f:
        d = json.load(f)
    hits = [h for e in d["hooks"].get("PostToolUse", []) for h in e["hooks"]
            if "sanitize_connector_output.sh" in h.get("command", "")]
    check("%s: exactly one connector-door entry" % rel, len(hits) == 1, hits)
    check("%s: it carries onFailure: block" % rel, hits and hits[0].get("onFailure") == "block", hits)
    others = [h for e in d["hooks"].values() for g in e for h in g["hooks"]
              if "onFailure" in h and "sanitize_connector_output.sh" not in h.get("command", "")]
    check("%s: no other hook gained onFailure" % rel, others == [], others[:2])

with open(os.path.join(REGISTER_DIR, "register.jsonl"), encoding="utf-8") as f:
    rows = [json.loads(l) for l in f if l.strip()]
mine = [r for r in rows if r.get("path") == "/system/hooks/sanitize_connector_output.sh"]
check("register row for the connector door carries on_failure=block", len(mine) == 1 and mine[0].get("on_failure") == "block", mine)
check("no other register row carries on_failure", [r["id"] for r in rows if "on_failure" in r and r not in mine] == [])

print("-- a hook that cannot start is a FAILURE the harness sees (what onFailure: block turns into a block) --")
# The registered command, pointed at a plugin root where the script is missing: bash cannot open the
# file and exits non-zero (127) with nothing on stdout. Without onFailure that is a non-blocking error
# and the raw connector result goes through; with onFailure: block (asserted above) the harness blocks.
missing_root = os.path.join(REPO_ROOT, "system", "register", "tests", "no-such-plugin-root")
cmd = 'bash "${CLAUDE_PLUGIN_ROOT}/system/hooks/sanitize_connector_output.sh"'
p = subprocess.run(["/bin/sh", "-c", cmd], input='{"tool_name":"mcp__x__y","tool_response":"raw"}',
                   capture_output=True, text=True, env=dict(os.environ, CLAUDE_PLUGIN_ROOT=missing_root))
check("missing script: non-zero exit, nothing on stdout (a hook failure, not a verdict)",
      p.returncode not in (0, 2) and p.stdout == "", (p.returncode, p.stdout, p.stderr[:120]))

print("")
print("RESULT: %d passed, %d failed." % (sum(RESULTS), len(RESULTS) - sum(RESULTS)))
sys.exit(0 if all(RESULTS) else 1)
