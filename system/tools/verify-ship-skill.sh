#!/bin/bash
# verify-ship-skill.sh -- prove the /ship front door is REAL, not just written.
#
# WHY THIS EXISTS. A skill is not shipped when its steps are written; it is shipped when
# something CALLS them. A reflection screen elsewhere in this system was built, unit-tested
# and rendered from fixtures -- and sat dead for three weeks because no skill file ever
# called it, while the project's own success criterion read as delivered. So this script
# does not READ the skill looking for the right words. It RUNS the sequence that file
# prescribes, against the real fixtures, and asserts the outcomes.
#
# WHAT IT CANNOT DO, stated rather than faked: it cannot run the judgment pass, because that
# pass IS a running session (reach = SESSION -- see the skill's own THE REACH section). So
# instead of stubbing a verdict -- which would prove nothing and would bake the fail-open
# escape hatch into the verification -- it asserts the STRUCTURAL property that matters:
# push_gate CANNOT be satisfied without a signed judge receipt. That is the exact hole a
# red-team pass found (the lock was built and the key never was), so it is the right thing
# to guard.
#
# ⚠ IT RUNS THE MECHANICAL CHECKS AGAINST THE LANE'S INVENTED IDENTITY FIXTURE, not against
# yours, so the result is the same on every machine and no real identity is involved. Your
# own identity file is checked SEPARATELY, in section 2 -- without it the lane refuses to
# run at all, which is a different failure and deserves its own line.
#
# Exit 0 = every check passed. Exit 1 = at least one FAILED. Nothing is written outside a
# temp dir, and the repo's git status must be byte-identical before and after.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
# ⚠ RESOLVED, NOT COUNTED. A "$HERE/../.." would be right today and wrong the moment this
# script moves one directory, and the symptom is a silent MISSING for every path below --
# which reads as "the skill is not installed" rather than "the script is lost".
REPO="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || (cd "$HERE/../.." && pwd))"
LANE="$REPO/system/shipping-lane"
SKILL="$REPO/.claude/skills/ship/SKILL.md"
IDENTITY_FIXTURE="$LANE/fixtures/identity-fixture.md"
PASS=0
FAIL=0

ok()   { printf '  [PASS] %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL+1)); }

printf '\nverify-ship-skill -- proving the /ship front door runs, not just reads\n'
printf -- '------------------------------------------------------------\n'

# ---------------------------------------------------------------- 0. the snapshot
BEFORE=$(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git status --porcelain | sort)

# ---------------------------------------------------------------- 1. the file itself
if [ -f "$SKILL" ]; then
  ok ".claude/skills/ship/SKILL.md exists"
else
  bad ".claude/skills/ship/SKILL.md is MISSING -- nothing else here is meaningful"
  exit 1
fi

# Frontmatter must parse. `disable-model-invocation` must be ABSENT: what protects a
# push-to-public skill is not a gate on who may START it -- everything before the push is
# reversible -- it is the structural check in 3d below, that push_gate cannot be satisfied
# without a signed judge receipt, plus the human-only push itself.
python3 - "$SKILL" <<'PY'
import sys, re
src = open(sys.argv[1], encoding="utf-8").read()
m = re.match(r'^---\n(.*?)\n---', src, re.S)
if not m:
    print("  [FAIL] frontmatter does not parse (no leading --- block)"); sys.exit(1)
block = m.group(1)
try:
    import yaml
    fm = yaml.safe_load(block)
    if not isinstance(fm, dict):
        print("  [FAIL] frontmatter is not a mapping"); sys.exit(1)
    desc = str(fm.get("description", "") or "").strip()
    dmi = fm.get("disable-model-invocation")
except ImportError:
    desc = (re.search(r'^description:\s*(.+\S)\s*$', block, re.M) or [None, ""])[1]
    dmi = bool(re.search(r'^disable-model-invocation:\s*true\s*$', block, re.M))
fails = 0
if not desc or desc.startswith("REPLACE"):
    print("  [FAIL] description: is empty or a placeholder"); fails += 1
else:
    print("  [PASS] description: present and non-placeholder")
if dmi in (None, False, ""):
    print("  [PASS] disable-model-invocation is correctly ABSENT -- the protection lives in "
          "push_gate and in the human-only push, not in a gate on starting the lane")
else:
    print("  [FAIL] disable-model-invocation is set -- remove it; starting the lane is safe "
          "and reversible, and the real gate is push_gate"); fails += 1
sys.exit(1 if fails else 0)
PY
if [ $? -eq 0 ]; then PASS=$((PASS+2)); else FAIL=$((FAIL+1)); fi

# The skill must state its reach. A seam whose only reach is SESSION does not exist in a
# scheduled runner, and if that is not written down a background path will silently skip the
# model step and report success.
if grep -q 'DOES NOT EXIST IN CRON' "$SKILL"; then
  ok "the skill states its reach (SESSION -- therefore absent from any scheduled runner)"
else
  bad "the skill does not state that its reach is SESSION-only"
fi

# The no-outcome member must be named. Without it, 'I could not look' and 'I looked and it
# was fine' are spelled the same way.
if grep -q 'NOT-EVALUATED' "$SKILL"; then
  ok "the seam's NO-OUTCOME member (NOT-EVALUATED) is named in the skill"
else
  bad "NOT-EVALUATED is not named -- the seam has no way to say 'no outcome was reached'"
fi

# ---------------------------------------------------------------- 2. the personal tier
#
# ⚠ THIS SECTION REPLACED A SYMLINK CHECK, AND THE REASON IS WORTH KEEPING. The donor system
# registered skills by symlinking them out of a clone into ~/.claude/skills/, so its version
# of this section asked whether that link resolved back into the clone. There is no symlink
# layer here -- skills are real files inside the repo -- so that check would test an
# impossible failure and report PASS for ever, which is worse than no check.
#
# What IS true here and can silently break: the lane's personal tier comes from a file
# outside the repo. Without it the lane refuses to run, by design.
SETUP=0
if python3 "$LANE/identity_rules.py" --show >/dev/null 2>&1; then
  ok "your own identity file resolves -- the personal tier will compile"
else
  printf '  [SETUP] no identity file yet, so the lane will refuse every run until there is one\n'
  printf '          make one with: python3 system/shipping-lane/identity_rules.py --write-example\n'
  SETUP=$((SETUP+1))
fi

# ---------------------------------------------------------------- 3. THE REAL RUN
WORK=$(mktemp -d /tmp/verify-ship-XXXXXX)
trap "rm -rf '$WORK'" EXIT

# The composed set, once, from the INVENTED fixture identity -- so scrub and the gate below
# provably see the same rules and the result does not depend on whose machine this is.
python3 "$LANE/identity_rules.py" --identity "$IDENTITY_FIXTURE" \
  --out-refuse "$WORK/refuse.json" --out-rewrite "$WORK/rewrite.json" --quiet
RULES="--refuse-rules $WORK/refuse.json --rewrite-rules $WORK/rewrite.json"

# 3a. the refuse fixture must REFUSE. A gate that has not been watched refusing is not a gate.
printf '%s\n' 'system/shipping-lane/fixtures/refuse-fixture.md' > "$WORK/refuse-manifest.txt"
(cd "$REPO" && python3 "$LANE/scrub.py" $RULES --manifest "$WORK/refuse-manifest.txt" \
   --staging "$WORK/refuse-staging" --report-json "$WORK/refuse-report.json") >"$WORK/refuse.out" 2>&1
RC=$?
if [ "$RC" -eq 1 ]; then
  ok "REFUSE fixture drives scrub.py to a REFUSAL (exit 1) -- the lane has been seen refusing"
else
  bad "REFUSE fixture produced exit $RC, expected 1 -- the lane did NOT refuse a file full of planted secrets"
fi

# 3b. the clean fixture must pass the mechanical pass.
printf '%s\n' 'system/shipping-lane/fixtures/clean-fixture.md' > "$WORK/clean-manifest.txt"
(cd "$REPO" && python3 "$LANE/scrub.py" $RULES --manifest "$WORK/clean-manifest.txt" \
   --staging "$WORK/clean-staging" --report-json "$WORK/clean-report.json") >"$WORK/clean.out" 2>&1
RC=$?
if [ "$RC" -eq 0 ]; then
  ok "CLEAN fixture passes the mechanical pass (exit 0) -- no false positive"
else
  bad "CLEAN fixture produced exit $RC, expected 0 -- the lane false-positived on known-good content"
fi

# 3c. --prepare must produce bundles and a coverage manifest.
(cd "$REPO" && python3 "$LANE/judge.py" --prepare --staging "$WORK/clean-staging" \
   --out "$WORK/bundles") >"$WORK/prepare.out" 2>&1
if [ -f "$WORK/bundles/manifest.json" ] && ls "$WORK/bundles"/*.prompt.md >/dev/null 2>&1; then
  ok "judge.py --prepare emits bundles + a coverage manifest for the session to read"
else
  bad "judge.py --prepare did not produce bundles/manifest.json -- the model half has nothing to read"
fi

# 3d. THE STRUCTURAL ONE: the gate must refuse to certify an UNJUDGED tree.
#     This is the hole the red team found -- the lock existed and nothing produced the key.
(cd "$REPO" && python3 "$LANE/push_gate.py" $RULES --tree "$WORK/clean-staging" \
   --receipt "$WORK/should-not-exist.json") >"$WORK/nojudge.out" 2>&1
RC=$?
if [ "$RC" -eq 2 ] && [ ! -f "$WORK/should-not-exist.json" ]; then
  ok "push_gate REFUSES an unjudged tree (exit 2, no receipt) -- the judge is structurally required"
else
  bad "push_gate returned $RC on an UNJUDGED tree (receipt present: $([ -f "$WORK/should-not-exist.json" ] && echo yes || echo no)) -- the judgment pass is bypassable"
fi

# 3e. THE OTHER STRUCTURAL ONE, and it is new here: no identity file must STOP the lane
#     rather than quietly run it with an empty personal tier. A run with no personal tier
#     reports a file carrying your own name as clean, which is the failure this whole lane
#     exists to prevent -- so it has to be a refusal, not a quieter run.
(cd "$REPO" && SHIP_IDENTITY="$WORK/nonexistent-identity.md" LIFEHACK_ROOT="$WORK/no-notes" \
   python3 "$LANE/scrub.py" --manifest "$WORK/clean-manifest.txt" \
   --staging "$WORK/noid-staging") >"$WORK/noid.out" 2>&1
RC=$?
if [ "$RC" -eq 2 ] && grep -qi 'identity' "$WORK/noid.out"; then
  ok "no identity file -> CANNOT EVALUATE (exit 2) naming it -- never a run with an empty personal tier"
else
  bad "no identity file produced exit $RC -- the lane must refuse, not scan for nobody"
fi

# ---------------------------------------------------------------- 4. the originals
AFTER=$(cd "$REPO" && GIT_OPTIONAL_LOCKS=0 git status --porcelain | sort)
if [ "$BEFORE" = "$AFTER" ]; then
  ok "git status --porcelain in the repo is BYTE-IDENTICAL before and after -- originals untouched"
else
  bad "the repo's git status CHANGED during this run -- something wrote to the originals"
fi

printf -- '------------------------------------------------------------\n'
# ⚠ TWO DIFFERENT NON-GREEN STATES, KEPT APART ON PURPOSE. "The machinery is broken" and
# "you have not set it up yet" want different reactions, and a single red FAIL for both
# teaches people to ignore the red one that matters. A missing identity file is exit 0 with
# a loud SETUP line: nothing here is wrong, and the lane will still refuse to run until it
# exists, which is its own fail-closed refusal at the moment of use.
if [ "$FAIL" -eq 0 ] && [ "$SETUP" -eq 0 ]; then
  printf 'VERIFY-SHIP: PASS -- %d checks green\n\n' "$PASS"
  exit 0
fi
if [ "$FAIL" -eq 0 ]; then
  printf 'VERIFY-SHIP: PASS -- %d checks green, but SETUP IS INCOMPLETE (%d item).\n' "$PASS" "$SETUP"
  printf 'The lane works; it does not yet know who you are, and will refuse until it does.\n\n'
  exit 0
fi
printf 'VERIFY-SHIP: FAIL -- %d passed, %d FAILED, %d setup item(s) outstanding\n\n' \
  "$PASS" "$FAIL" "$SETUP"
exit 1
