#!/usr/bin/env python3
"""Independent hand-verifier for the Tier-1 safety-guard probes (writer!=verifier).

Deliberately SEPARATE from probes/guard.py: fires slightly-varied payloads at the
live guards and prints RAW exit codes + output, so a human can eyeball that each
block is real (and each allow passes for the right reason, not a fail-open).

PORTED (T9.8c) from claudeops-config's conformance-lab/_verify_guards_manual.py. Two
hardcoded personal paths generalized: the hooks dir now resolves relative to THIS file
(never a hardcoded ~/claudeops-config), and DRIVE resolves through the one shared
resolver (shared/brain_root.py) — these test payloads only need a DRIVE-SHAPED path
string to exercise the guards' path-matching, never real content on disk, so a NOT-SET
data root degrades to a placeholder string rather than aborting.

Run:  python3 _verify_guards_manual.py     (payloads live IN this file — never pass
them on a Bash command line, or the live PreToolUse guards block the harness itself.)
"""
import json, subprocess, os, sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "..", "shared"))
try:
    import brain_root
    _SRC, _DATA = brain_root.resolve_brain_root()
except Exception:
    _DATA = None

H = os.path.join(_ROOT, "hooks")
DRIVE = _DATA or os.path.expanduser("~/lifehack-notes")  # placeholder shape only — no real
                                                          # content is read at this path.


def fire(hook, payload):
    r = subprocess.run(["bash", os.path.join(H, hook)], input=json.dumps(payload),
                       capture_output=True, text=True, timeout=10)
    blob = (r.stdout + " " + r.stderr).replace("\n", " ").strip()[:90]
    return r.returncode, blob


_CLONE = os.path.dirname(_ROOT)  # the clone root (one level above system/) — guard_write_paths.sh
                                  # resolves its protected paths against this, not _ROOT (=system/).

CASES = [
    # (label, hook, payload, expect)  expect: "block" | "allow"
    ("gws-logout FORBID",              "guard_gws_logout.sh",        {"tool_input": {"command": "gws auth logout"}}, "block"),
    ("gws-logout ALLOW",               "guard_gws_logout.sh",        {"tool_input": {"command": "gws auth status"}}, "allow"),
    # NOTE: the donor's "no authority: user -> block" canon case is DELIBERATELY NOT reproduced
    # here. guard_canon_write.sh's own header documents dropping that rail on this port
    # (2026-08-11): it was self-attestation theater that blocked this product's own /save output
    # on day one. Testing for it would assert a regression against a ratified fix, not a guard.
    ("canon FORBID (oversized)",       "guard_canon_write.sh",       {"tool_input": {"file_path": DRIVE + "/canon/x.md", "content": "x" * 3300}}, "block"),
    ("canon ALLOW (small)",            "guard_canon_write.sh",       {"tool_input": {"file_path": DRIVE + "/canon/x.md", "content": "a small canon line"}}, "allow"),
    ("egress-AL FORBID (off-list)",    "enforce_egress_allowlist.sh",{"tool_input": {"command": "curl -s https://evil.exfil-host.test/x"}}, "block"),
    ("egress-AL ALLOW (github)",       "enforce_egress_allowlist.sh",{"tool_input": {"command": "curl -s https://api.github.com/x"}}, "allow"),
    ("sheet FORBID (destructive)",     "guard_sheet_writes.sh",      {"tool_input": {"command": "gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"1Bxi\",\"range\":\"A1:Z9\"}'"}}, "block"),
    ("sheet ALLOW (read _LLM_GUIDE)",  "guard_sheet_writes.sh",      {"tool_input": {"command": "gws sheets spreadsheets values get --params '{\"spreadsheetId\":\"1Bxi\",\"range\":\"_LLM_GUIDE!A:Z\"}'"}}, "allow"),
    ("tasks FORBID (Life Map write)",  "guard_tasks_writes.sh",      {"tool_input": {"command": "gws tasks tasks insert --params '{\"tasklist\":\"cDJFQjd4dF94UjNiRzFRSg\",\"title\":\"x\"}'"}}, "block"),
    ("tasks ALLOW (Life Map read)",    "guard_tasks_writes.sh",      {"tool_input": {"command": "gws tasks tasks list --params '{\"tasklist\":\"cDJFQjd4dF94UjNiRzFRSg\"}'"}}, "allow"),
    # NOTE: the donor's write-paths guard is a general write-CONTAINMENT wall (denies anything
    # outside four approved zones). THIS repo's guard_write_paths.sh is a narrower, DIFFERENT
    # guard by ratified decision (its own header: "ports only the half that needs no [product]
    # decision" — the general wall is F9.12 item 3, open, explicitly NOT to be built ahead of
    # that conversation). Cases below test what this guard ACTUALLY protects: hook scripts and
    # settings.json, never a general path-containment rule like /tmp.
    ("write-paths FORBID (hook edit)", "guard_write_paths.sh",       {"tool_input": {"file_path": os.path.join(_CLONE, "system", "hooks", "guard_gws_logout.sh"), "content": "y"}}, "block"),
    ("write-paths FORBID (settings)",  "guard_write_paths.sh",       {"tool_input": {"file_path": os.path.join(_CLONE, ".claude", "settings.json"), "content": "y"}}, "block"),
    ("write-paths ALLOW (ordinary file)", "guard_write_paths.sh",    {"tool_input": {"file_path": DRIVE + "/records/findings/_x.md", "content": "y"}}, "allow"),
]

ok = True
for label, hook, payload, expect in CASES:
    rc, blob = fire(hook, payload)
    blocked = rc != 0 and ("BLOCKED" in blob or ('"decision"' in blob and '"block"' in blob))
    got = "block" if blocked else ("allow" if rc == 0 else f"other(rc={rc})")
    verdict = "MATCH" if got == expect else "MISMATCH"
    if got != expect:
        ok = False
    print(f"{verdict}  {label:34s} expect={expect:5s} got={got:6s} rc={rc}  {blob[:60]}")

print("\nALL MATCH" if ok else "\n*** MISMATCH — investigate ***")
sys.exit(0 if ok else 1)
