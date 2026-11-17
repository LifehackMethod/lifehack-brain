#!/usr/bin/env bash
# test_scheduled_jobs_check.sh — round five step 5: the Scheduled jobs component check, tested against the REAL repo.
# What it proves: --selftest exits 0 · a full --no-fetch run against the real repo exits 0, writes a JSON tile whose
# origin_sha equals `git rev-parse origin/V2` · clean_tree is true · all 5 probe ids are present · intervals-test and
# door-test PASS in the clean checkout · the three LIVE drifts are caught (no-send-verb FAIL with `send` in the
# GWS_WRITE list; refusal-rulebook-resolves FAIL naming system/sops/pr-sop.md; state-local-not-drive FAIL) ·
# no worktree is left behind · the repo's `git status --porcelain` is unchanged by the run.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CHECK="$ROOT/system/tools/organism/checks/scheduled_jobs_check.py"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
FAIL=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; FAIL=1; }
has()   { grep -qF -- "$2" "$1" && ok "$3" || { bad "$3 (wanted: $2)"; }; }

[ -f "$CHECK" ] || { bad "check script missing: $CHECK"; echo "FAIL (cannot proceed)"; exit 1; }

# ── 1. --selftest exits 0 ──
if python3 "$CHECK" --selftest > "$T/self.out" 2>&1; then ok "selftest exits 0"; else bad "selftest exits non-zero"; cat "$T/self.out"; fi
grep -q 'no-send-verb' "$T/self.out" && ok "selftest names no-send-verb" || bad "selftest output lacks no-send-verb"

# ── 1b. probe unit tests: new patterns must bite, vacuous targets must ERROR ──
python3 - "$CHECK" <<'PY' || FAIL=1
import importlib.util, sys
spec = importlib.util.spec_from_file_location("sjc", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
fails = []
def want(cond, label):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond: fails.append(label)

INSTALLER = m.INSTALLER
# multi-line GWS_WRITE: the statement is joined up to its closing brace before matching
bad_ml = 'GWS_WRITE = {\n  "gmail": re.compile(r"\\s*users (?:messages (?:modify|send))\\b"),\n}\n'
good_ml = 'GWS_WRITE = {\n  "gmail": re.compile(r"\\s*users (?:messages (?:modify|drafts create))\\b"),\n}\n'
want(m.probe_no_send_verb({INSTALLER: bad_ml})[0] == "FAIL", "multi-line GWS_WRITE with send FAILs")
want(m.probe_no_send_verb({INSTALLER: good_ml})[0] == "PASS", "multi-line GWS_WRITE without send PASSes")
# vacuous passes are forbidden: a probe whose target is missing or matches zero lines ERRORs
want(m.probe_no_send_verb({INSTALLER: "x = 1\n"})[0] == "ERROR", "no GWS_WRITE definition ERRORs (no vacuous PASS)")
want(m.probe_no_send_verb({})[0] == "ERROR", "missing installer file ERRORs")
# a comment merely NAMING GWS_WRITE is not its definition: the real definition's `send` must still bite
bad_comment = '# see GWS_WRITE policy in the door docs\n' + bad_ml
good_comment = '# see GWS_WRITE policy in the door docs\n' + good_ml
want(m.probe_no_send_verb({INSTALLER: bad_comment})[0] == "FAIL", "comment naming GWS_WRITE plus real definition with send FAILs")
want(m.probe_no_send_verb({INSTALLER: good_comment})[0] == "PASS", "comment naming GWS_WRITE plus good definition PASSes")
want(m.probe_no_send_verb({INSTALLER: "# GWS_WRITE is discussed below\n"})[0] == "ERROR", "comment naming GWS_WRITE alone ERRORs (no definition)")
want(m.probe_refusal_rulebook({INSTALLER: "echo hi\n"}, "/")[0] == "ERROR", "no Rulebook line ERRORs (no vacuous PASS)")
# state-local widened: export form, $LIFEHACK_ROOT, My Drive
bad_export = 'export PARK_FILE="$LIFEHACK_ROOT/state/x.json"\n'
good_export = 'export PARK_FILE="$HOME/.config/lifehack/state/x.json"\n'
bad_drive = 'PARK_FILE="/Users/x/My Drive/notes/state.json"\n'
# the probe requires BOTH pulse files; give each case the benign park twin
park_good_line = 'PARK_FILE="$HOME/.config/lifehack/state/x.json"\n'
def both(main_text):
    return {"system/tools/pulse.sh": main_text, "system/tools/pulse-park.sh": park_good_line}
want(m.probe_state_local(both(bad_export))[0] == "FAIL", "export PARK_FILE with $LIFEHACK_ROOT FAILs")
want(m.probe_state_local(both(good_export))[0] == "PASS", "export PARK_FILE local PASSes")
want(m.probe_state_local(both(bad_drive))[0] == "FAIL", "PARK_FILE under My Drive FAILs")
want(m.probe_state_local({"system/tools/pulse.sh": "OTHER=1\n", "system/tools/pulse-park.sh": "OTHER=1\n"})[0] == "ERROR", "no PARK_FILE assignment ERRORs (no vacuous PASS)")
want(m.probe_state_local({})[0] == "ERROR", "both target files missing ERRORs")
want(m.probe_state_local({"system/tools/pulse.sh": 'PARK_FILE="$HOME/.config/lifehack/state/x.json"\n'})[0] == "ERROR",
     "only one of the two pulse files present ERRORs")
sys.exit(1 if fails else 0)
PY
[ $? -eq 0 ] || FAIL=1

# ── 2. full run against the real repo, --no-fetch ──
BEFORE="$(git -C "$ROOT" status --porcelain)"
if python3 "$CHECK" --no-fetch --out "$T/tile.json" > "$T/run.out" 2>&1; then ok "full run exits 0"; else bad "full run exits non-zero"; cat "$T/run.out"; fi

[ -f "$T/tile.json" ] && ok "tile written" || bad "tile missing at $T/tile.json"
if command -v python3 >/dev/null && [ -f "$T/tile.json" ]; then
  python3 - "$T/tile.json" "$ROOT" "$T" <<'PY'
import json, subprocess, sys
tile = json.load(open(sys.argv[1]))
root, T = sys.argv[2], sys.argv[3]
fails = []
def want(cond, label):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond: fails.append(label)

sha = subprocess.run(["git", "-C", root, "rev-parse", "origin/V2"],
                     capture_output=True, text=True).stdout.strip()
want(tile.get("payload", tile).get("origin_sha", tile.get("origin_sha")) == sha,
     "tile origin_sha == rev-parse origin/V2")
pay = tile.get("payload", tile)
want(pay.get("clean_tree") is True, "clean_tree is true")
checks = pay.get("checks", [])
ids = {c.get("id") for c in checks}
want({"intervals-test", "door-test", "no-send-verb",
      "refusal-rulebook-resolves", "state-local-not-drive"} <= ids,
     "all 5 probe ids present")
by = {c.get("id"): c for c in checks}
want(by.get("intervals-test", {}).get("result") == "PASS", "intervals-test PASS")
want(by.get("door-test", {}).get("result") == "PASS", "door-test PASS")
want(by.get("no-send-verb", {}).get("result") == "FAIL", "no-send-verb FAIL (live drift)")
rb = by.get("refusal-rulebook-resolves", {})
want(rb.get("result") == "FAIL" and "system/sops/pr-sop.md" in json.dumps(rb),
     "refusal-rulebook-resolves FAIL naming pr-sop.md")
want(by.get("state-local-not-drive", {}).get("result") == "FAIL", "state-local-not-drive FAIL")

# refused_once has two meanings: bite_tested for the three text probes (planted fault caught —
# a planted fault is NOT a refusal seen in use, so refused_once stays False there),
# the plain refusal-seen-in-output meaning for the two test-suite probes
for tid in ("no-send-verb", "refusal-rulebook-resolves", "state-local-not-drive"):
    c = by.get(tid, {})
    want(c.get("bite_tested") is True and c.get("refused_once") is False,
         tid + " bite_tested from the self-test, refused_once False (planted fault is not a refusal in use)")
for tid in ("intervals-test", "door-test"):
    want(by.get(tid, {}).get("bite_tested") is False,
         tid + " carries no bite_tested (test-suite meaning of refused_once)")

# no leftover worktree
wt = subprocess.run(["git", "-C", root, "worktree", "list", "--porcelain"],
                    capture_output=True, text=True).stdout
want(str(T) not in wt, "no leftover worktree from the run")
sys.exit(1 if fails else 0)
PY
  [ $? -eq 0 ] || FAIL=1
fi

AFTER="$(git -C "$ROOT" status --porcelain)"
[ "$BEFORE" = "$AFTER" ] && ok "git status --porcelain unchanged by the run" || bad "run changed git status"

echo; [ "$FAIL" -eq 0 ] && echo "ALL PASS" || echo "FAILURES PRESENT"
exit "$FAIL"
