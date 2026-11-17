#!/usr/bin/env bash
# test_component_page.sh — round five step 5: the component page's generator (as-built from ORIGIN) and stamper (status from receipts).
# Scratch repo with a local bare "origin"; no network. What it proves:
#   as-built lists committed files with their last commit, hook wiring, register rows, job rows, tests · it reads origin, never the working tree
#   (an uncommitted file is not listed; an edited file is counted under "not on origin") · broken pointers (missing path, line past the end) and
#   in-scope unregistered code are flagged · a hand edit inside either fence is refused, overwritten and reported · `home: false` paths leave scope
#   · the stamper's roll-up: no receipt = unproven (missing, refused by name); no origin sha = unproven; past the window = unproven; a covered
#   file changed on origin since the receipt's sha = unproven; a FAIL = PARTIAL; no refusal seen = suspect, never LIVE; an expected check absent
#   from every receipt = untested, with the best earned label beside it; all good = LIVE · the deliberate drift: a file deleted on origin is caught.
#   step 6(b): a check declared DORMANT (built, deliberately not in use) stands outside the weakest-wins
#   roll-up and is counted beside it (mixed page rolls up the rest with "N dormant"; an all-DORMANT page
#   reads DORMANT) · a check declared not_run reads "not run here" with its reason, never green, never hidden.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TOOL="$ROOT/system/tools/organism/component_page.py"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
FAIL=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; FAIL=1; }
has()   { grep -qF -- "$2" "$1" && ok "$3" || { bad "$3 (wanted: $2)"; }; }
hasnt() { grep -qF -- "$2" "$1" && bad "$3 (did not want: $2)" || ok "$3"; }
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid

git init -q --bare -b main "$T/origin.git"
git clone -q "$T/origin.git" "$T/w" 2>/dev/null
W="$T/w"; cd "$W" || exit 1
mkdir -p system/tools/tests system/register hooks canon system/hooks system/organism/components
printf '#!/bin/bash\necho a\n' > system/tools/a.sh
printf 'print("b")\n' > system/tools/b.py
printf '#!/bin/bash\necho lib\n' > system/tools/lib.sh
printf '#!/bin/bash\necho test\n' > system/tools/tests/test_a.sh
printf '#!/bin/bash\nexit 0\n' > system/hooks/h.sh
printf '{"id": "tool:public:/system/tools/a.sh", "path": "/system/tools/a.sh", "type": "tool", "sha": "aaaa1111"}\n' > system/register/register.jsonl
cat > hooks/hooks.json <<'J'
{"hooks": {"PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/system/hooks/h.sh\""}]}]}}
J
cat > system/jobs.md <<'J'
```jobs
demo-on | yes | 600 | Keeps demo fresh. | ~/x.log ~ ok | small | 5 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/a.sh"
demo-tbd | off | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/a.sh"
# comment-row | a | b | c | d | e | f | g | h
Bad_Name | yes | 600 | c | l | s | 5 | none | bash x
```
J
for i in 1 2 3 4 5 6 7 8 9 10; do echo "line $i" >> canon/demo-sop.md; done
echo "References: system/organism/components/demo.md" >> canon/demo-sop.md
git add -A && git commit -qm base && git push -q origin main 2>/dev/null

PAGE="$W/system/organism/components/demo.md"
cat > "$PAGE" <<'P'
---
component: demo
title: "Demo"
source: origin/main
scope:
  - system/tools/**          # the demo's code
  - system/hooks/h.sh
  - system/jobs.md
shared:
  - {paths: [system/tools/lib.sh], home: false, role_here: data, file_home: other}
checks:
  - {id: probe-a, watches: "a works"}
  - {id: probe-b, watches: "b works"}
receipts:
  - <brain>/status/component-demo.json
  - <brain>/status/component-demo-extra.json
---
# Demo

## Purpose/Responsibility
Governs: `canon/demo-sop.md:5`; also `canon/demo-sop.md:99` and `system/tools/nope.sh` and `system/tools/a.sh`.
Bare prose mentions: canon/demo-sop.md:99 plus canon/demo-sop.md:3-5 and system/absent-bare.sh without backticks.

## Directory/file location
<!-- AS-BUILT:BEGIN -->
<!-- AS-BUILT:END -->

## Status
<!-- STATUS:BEGIN -->
<!-- STATUS:END -->
P
BRAIN="$T/brain"; mkdir -p "$BRAIN/status"
printf 'this is { not json' > "$BRAIN/status/component-demo-extra.json"
ORIG_SHA="$(git rev-parse HEAD)"

# uncommitted noise in the working tree: a new in-scope file, and an edit to a committed one
printf 'echo c\n' > system/tools/c.sh
printf '#!/bin/bash\necho a-edited\n' > system/tools/a.sh

python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > "$T/out1" 2>&1 || bad "asbuilt exit $?: $(cat "$T/out1")"
has "$PAGE" "source=origin/main@${ORIG_SHA:0:7}" "as-built names the origin sha it read"
has "$PAGE" "| file | system/tools/a.sh |" "committed file listed"
has "$PAGE" "| test | system/tools/tests/test_a.sh |" "test file listed as a test"
hasnt "$PAGE" "system/tools/c.sh |" "uncommitted file NOT listed (origin, never the working tree)"
has "$PAGE" "not on origin: 2" "working-tree differences counted, never listed as built"
has "$PAGE" "PreToolUse · Write" "hook wiring read from origin hooks.json"
has "$PAGE" "tool:public:/system/tools/a.sh" "register row listed"
has "$PAGE" "| demo-on | yes | 600 | filled |" "job row with contract filled"
has "$PAGE" "| demo-tbd | off | 86400 | TBD |" "job row with TBD contract"
has "$PAGE" "named but missing: \`system/tools/nope.sh\`" "missing path flagged"
has "$PAGE" "named but missing: \`system/tools/nope.sh\` ⛔ not on origin" "missing path carries a ⛔ reason (the citation lint needs one)"
has "$PAGE" "named but missing: \`canon/demo-sop.md:99\` (file has 11 lines)" "line past the end flagged"
hasnt "$PAGE" "named but missing: \`canon/demo-sop.md:5\`" "a good pointer is not flagged"
has "$PAGE" "in scope, unregistered: \`system/tools/b.py\`" "unregistered code flagged"
hasnt "$PAGE" "| file | system/tools/lib.sh |" "home:false path left scope"
has "$PAGE" "pointed at by: \`canon/demo-sop.md\`" "SOPs pointing at the page found on origin"

# hand edit inside the as-built fence -> refused, overwritten, reported
python3 - "$PAGE" <<'PY'
import sys; p=sys.argv[1]; s=open(p).read(); s=s.replace("| file | system/tools/a.sh |","| file | system/tools/a.sh | HAND-EDITED |",1); open(p,"w").write(s)
PY
python3 "$TOOL" verify "$PAGE" > "$T/v1" 2>&1; [ $? -eq 1 ] && ok "verify exits 1 on a hand edit" || bad "verify did not exit 1"
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > "$T/out2" 2>&1
hasnt "$PAGE" "HAND-EDITED" "hand edit overwritten"
has "$PAGE" "hand edit refused, overwritten" "hand edit reported in the block"
has "$T/out2" "hand edit refused, overwritten" "hand edit reported on stdout"
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > /dev/null 2>&1
hasnt "$PAGE" "hand edit refused" "report clears on the next clean run"
python3 "$TOOL" verify "$PAGE" > /dev/null 2>&1 && ok "verify exits 0 when clean" || bad "verify not clean after regeneration"

# ── stamper ──
stamp() { python3 "$TOOL" stamp "$PAGE" --repo "$W" --brain "$BRAIN" "$@" > "$T/st" 2>&1; }
status_line() { grep -m1 '^Status:' "$PAGE"; }
stamp
status_line | grep -qF "unproven (receipt missing)" && ok "no receipt -> unproven, refused by name" || bad "no receipt: $(status_line)"
has "$PAGE" "<brain>/status/component-demo.json" "missing receipt named (in the <brain> form; the page is public)"
hasnt "$PAGE" "$BRAIN" "no expanded personal path on the page"
has "$PAGE" "receipt refused (corrupt): <brain>/status/component-demo-extra.json" "corrupt receipt refused by name in the block"

tile() { # $1 origin sha  $2 clean  $3 last_run  $4 probe-a result  $5 probe-a refused_once  $6 include probe-b (1/0)  $7 not_tested (pipe-separated)  $8 component
  python3 - "$BRAIN/status/component-demo.json" "$@" <<'PY'
import json, sys
out, sha, clean, last, ra, refa, incb = sys.argv[1:8]
nt = sys.argv[8].split("|") if len(sys.argv) > 8 and sys.argv[8] else []
comp = sys.argv[9] if len(sys.argv) > 9 else "demo"
ct = True if clean == "1" else (False if clean in ("0", "") else clean)
checks = [{"id": "probe-a", "watches": "a works", "result": ra, "refused_once": refa == "1", "covers": ["system/tools/a.sh"], "untested": "nothing"}]
if incb == "1":
    checks.append({"id": "probe-b", "watches": "b works", "result": "PASS", "refused_once": True, "covers": ["system/tools/b.py"], "untested": "nothing"})
t = {"desk": "organism", "schema_version": 2, "pulse_job": "component-demo-check", "emit_mode": "manual", "stale_after_s": 604800,
     "last_run": last, "rc": 0, "status": "OK", "summary": "x",
     "component": comp, "origin_sha": sha or None, "clean_tree": ct, "checks": checks}
if nt:
    t["not_tested"] = nt
json.dump(t, open(out, "w"))
PY
}
NOW=2026-11-16T12:00:00+00:00
tile "$ORIG_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qE "^Status: LIVE · checked 2026-11-16 · valid until 2026-11-23" && ok "all good -> LIVE with dates" || bad "LIVE: $(status_line)"
tile "" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (no origin sha)" && ok "no origin sha -> unproven" || bad "no sha: $(status_line)"
tile "$ORIG_SHA" 0 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (dirty tree)" && ok "dirty tree -> unproven" || bad "dirty: $(status_line)"
tile "$ORIG_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now 2026-11-30T12:00:00+00:00
status_line | grep -qF "unproven (past window)" && ok "past window -> unproven" || bad "window: $(status_line)"
tile "$ORIG_SHA" 1 2026-11-16T10:00:00+00:00 FAIL 1 1; stamp --now "$NOW"
status_line | grep -qF "Status: PARTIAL" && ok "a FAIL -> PARTIAL" || bad "fail: $(status_line)"
tile "$ORIG_SHA" 1 2026-11-16T10:00:00+00:00 PASS 0 1; stamp --now "$NOW"
status_line | grep -qF "Status: PARTIAL" && ok "no refusal seen -> not LIVE" || bad "suspect: $(status_line)"
has "$PAGE" "suspect" "no refusal seen -> marked suspect"
tile "$ORIG_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 0; stamp --now "$NOW"
status_line | grep -qF "untested (1 of 2 checks missing) · best earned LIVE" && ok "expected check absent -> untested + best earned" || bad "untested: $(status_line)"

# covered file changes on origin after the receipt's sha -> unproven (code changed since)
git checkout -q -- system/tools/a.sh; rm -f system/tools/c.sh
printf '#!/bin/bash\necho a2\n' > system/tools/a.sh; git commit -qam "change a" && git push -q origin main 2>/dev/null
tile "$ORIG_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (code changed since)" && ok "covered file changed on origin -> unproven" || bad "changed: $(status_line)"

# hand edit inside the status fence -> refused, overwritten
python3 - "$PAGE" <<'PY'
import sys,re; p=sys.argv[1]; s=open(p).read(); s=re.sub(r"^Status: .*$","Status: LIVE · forged",s,count=1,flags=re.M); open(p,"w").write(s)
PY
stamp --now "$NOW"
hasnt "$PAGE" "forged" "forged status overwritten"
has "$PAGE" "hand edit refused, overwritten" "forged status reported"

# ── reviewer fixes: label honesty, receipt honesty ──
CUR_SHA="$(git rev-parse origin/main)"
tile "$CUR_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 1 "" other; stamp --now "$NOW"
status_line | grep -qF "unproven (receipt is for another component)" && ok "receipt for another component refused" || bad "other component: $(status_line)"
tile "$CUR_SHA" yes 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (dirty tree)" && ok "clean_tree must be the JSON boolean true" || bad "string clean: $(status_line)"
tile "$CUR_SHA" 1 2026-11-16T13:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (dated in the future)" && ok "last_run in the future (beyond 5 min skew) -> unproven" || bad "future: $(status_line)"
tile "$CUR_SHA" 1 2026-11-16T10:00:00+00:00 ERROR 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (check did not pass or fail: ERROR)" && ok "a non-PASS/FAIL result cannot earn above PARTIAL" || bad "ERROR: $(status_line)"
tile "$CUR_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 1 "edge|timing"; stamp --now "$NOW"
has "$PAGE" "not tested by these checks: edge; timing" "receipt not_tested list carried into the block"

# ── round-2 fixes ──
printf '#!/bin/bash\necho b2\n' > system/tools/b.py
git commit -qam "change b" && git push -q origin main 2>/dev/null
CUR2="$(git rev-parse origin/main)"

# fix 1: covered paths come from the page's scope, not the receipt's covers field
tile "$ORIG_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (code changed since)" && ok "page-scope covers: b.py changed since the receipt sha -> unproven" || bad "page-scope covers: $(status_line)"
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qE "^Status: LIVE ·" && ok "receipt at the current sha over the page's whole scope -> LIVE" || bad "page-scope LIVE: $(status_line)"

# fix 2: origin_sha must be 40 hex; a receipt with no component key is for another component; unreadable origin
tile "deadbeef" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (no origin sha)" && ok "origin_sha not 40-hex -> unproven (no origin sha)" || bad "sha fmt: $(status_line)"
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p)); d.pop("component", None); json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
status_line | grep -qF "unproven (receipt is for another component)" && ok "receipt with no component key -> unproven (another component)" || bad "no comp key: $(status_line)"
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1
PAGE3="$W/system/organism/components/nosource.md"
cat > "$PAGE3" <<'P3'
---
component: demo
title: "Demo (unreadable origin)"
source: origin/missing-branch
checks:
  - {id: probe-a, watches: "a works"}
receipts:
  - <brain>/status/component-demo.json
---
# Demo (unreadable origin)

## Status
<!-- STATUS:BEGIN -->
<!-- STATUS:END -->
P3
python3 "$TOOL" stamp "$PAGE3" --repo "$W" --brain "$BRAIN" --now "$NOW" > /dev/null 2>&1
grep -m1 '^Status:' "$PAGE3" | grep -qF "unproven (origin unreadable)" && ok "unresolvable source sha -> every reading unproven (origin unreadable)" || bad "origin unreadable: $(grep -m1 '^Status:' "$PAGE3")"

# fix 3: bad field types
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p)); d["stale_after_s"] = 3000000; json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
status_line | grep -qF "unproven (bad window)" && ok "stale_after_s over 30 days -> unproven (bad window)" || bad "big window: $(status_line)"
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p)); d.pop("stale_after_s", None); json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
status_line | grep -qF "unproven (bad window)" && ok "missing stale_after_s -> unproven (bad window)" || bad "no window: $(status_line)"
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p)); d["stale_after_s"] = "604800"; json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
status_line | grep -qF "unproven (bad window)" && ok "non-integer stale_after_s -> unproven (bad window)" || bad "str window: $(status_line)"
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p)); d["stale_after_s"] = 604800; d["checks"][0]["refused_once"] = "true"; json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
status_line | grep -qF "Status: PARTIAL" && ok "refused_once must be the JSON boolean true (a string is suspect)" || bad "str refused: $(status_line)"
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p)); d["checks"][0]["refused_once"] = True; d["checks"].append("not-a-dict"); json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
has "$PAGE" "malformed" "a non-dict checks entry is skipped and named as malformed in the block"
status_line | grep -qE "^Status: LIVE ·" && ok "a malformed entry alone does not cap the label" || bad "malformed LIVE: $(status_line)"

# fix 4: --no-fetch (or a failed fetch) caps the overall label below LIVE
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p))
d["checks"] = [c for c in d["checks"] if isinstance(c, dict)]
json.dump(d, open(p, "w"))
PY
python3 "$TOOL" stamp "$PAGE" --repo "$W" --brain "$BRAIN" --now "$NOW" --no-fetch > /dev/null 2>&1
status_line | grep -qE "^Status: PARTIAL ·" && ok "--no-fetch caps the overall label below LIVE" || bad "no-fetch cap: $(status_line)"
has "$PAGE" "origin not fetched (--no-fetch); cannot read LIVE" "the block says why LIVE is unreachable"

# fix 7: a check found only in a receipt still counts in the roll-up
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p))
d["checks"].append({"id": "probe-hidden", "watches": "hidden", "result": "FAIL", "refused_once": True, "covers": ["system/tools/a.sh"], "untested": ""})
json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
status_line | grep -qF "Status: PARTIAL" && ok "a receipt-only FAIL check holds the roll-up down" || bad "receipt-only FAIL: $(status_line)"
has "$PAGE" "check in receipt but not on the page: probe-hidden" "receipt-only FAIL check named in the block"
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p))
d["checks"].append({"id": "probe-extra", "watches": "extra", "result": "PASS", "refused_once": True, "covers": ["system/tools/a.sh"], "untested": ""})
json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
status_line | grep -qE "^Status: LIVE ·" && ok "a receipt-only PASS check does not cap the label" || bad "receipt-only PASS: $(status_line)"
has "$PAGE" "check in receipt but not on the page: probe-extra" "receipt-only PASS check also named"

# fix 8: the untested column falls back to the receipt's not_tested list
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1
python3 - "$BRAIN/status/component-demo.json" <<'PY'
import json, sys; p = sys.argv[1]; d = json.load(open(p))
d["checks"] = [c for c in d["checks"] if isinstance(c, dict)]
d["checks"][0]["untested"] = ""
d["not_tested"] = ["edge-case-x"]
json.dump(d, open(p, "w"))
PY
stamp --now "$NOW"
grep -F "| probe-a |" "$PAGE" | grep -qF "edge-case-x" && ok "untested column falls back to the receipt's not_tested list" || bad "untested col: $(grep -F '| probe-a |' "$PAGE")"

# receipt sha not an ancestor of the current origin sha
git checkout -q --orphan side && git commit -qam side
ORPHAN_SHA="$(git rev-parse HEAD)"
git checkout -q main
tile "$ORPHAN_SHA" 1 2026-11-16T10:00:00+00:00 PASS 1 1; stamp --now "$NOW"
status_line | grep -qF "unproven (sha not on origin)" && ok "receipt sha not an ancestor of origin -> unproven" || bad "ancestor: $(status_line)"

# ── reviewer fixes: bare tokens, jobs junk rows, hand-edit accounting ──
has "$PAGE" "named but missing: \`system/absent-bare.sh\`" "bare repo-path token flagged"
sed -n '/<!-- AS-BUILT:BEGIN/,/<!-- AS-BUILT:END/p' "$PAGE" > "$T/ab"
hasnt "$T/ab" "canon/demo-sop.md:3-5" "a bare range whose last line exists is not flagged"
hasnt "$PAGE" "# comment-row |" "jobs comment row excluded"
hasnt "$PAGE" "Bad_Name |" "jobs row with a bad name excluded"
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > /dev/null 2>&1  # regenerate so the diff is only the hand edit
python3 - "$PAGE" <<'PY'
import sys; p=sys.argv[1]; s=open(p).read()
s=s.replace("| file | system/tools/a.sh |", "| file | system/tools/a.sh | X |", 1)
open(p,"w").write(s)
PY
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > /dev/null 2>&1
has "$PAGE" "hand edit refused, overwritten (2 lines changed since the last generation)" "changed-line count uses difflib (added plus removed), not length"
python3 - "$PAGE" <<'PY'
import sys,re; p=sys.argv[1]; s=open(p).read()
s=re.sub(r"^(<!-- AS-BUILT:BEGIN .*) sha256=[0-9a-f]{64}", r"\1", s, count=1, flags=re.M)
open(p,"w").write(s)
PY
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > /dev/null 2>&1
has "$PAGE" "hand edit refused, overwritten" "a BEGIN line that lost its sha256 (non-empty body) is a hand edit"

# ── reviewer fixes: fetch honesty ──
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" --no-fetch > /dev/null 2>&1
grep -q "^<!-- AS-BUILT:BEGIN .* fetched=none (--no-fetch; ref as of " "$PAGE" && ok "--no-fetch: BEGIN says fetched=none with the ref's as-of time" || bad "no-fetch BEGIN: $(grep -m1 'AS-BUILT:BEGIN' "$PAGE")"
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > /dev/null 2>&1
hasnt "$PAGE" "fetched=none" "a real fetch clears fetched=none"
git remote set-url origin "$T/origin-does-not-exist.git"
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > /dev/null 2>&1
has "$PAGE" "origin as of last fetch (fetch failed)" "a failed fetch is recorded inside the block"
git remote set-url origin "$T/origin.git"

# ── reviewer fixes: a page with no checks does not crash ──
PAGE2="$W/system/organism/components/noprobes.md"
cat > "$W/system/organism/components/noprobes.md" <<'P2'
---
component: demo
title: "Demo (no probes)"
source: origin/main
---
# Demo (no probes)

## Status
<!-- STATUS:BEGIN -->
<!-- STATUS:END -->
P2
python3 "$TOOL" stamp "$PAGE2" --repo "$W" --brain "$BRAIN" --now "$NOW" > /dev/null 2>&1
has "$PAGE2" "Status: untested — no check exists · not built yet: (no check declared) · Serves: see the page's Quality characteristics" "page with no checks: exact untested line, no crash"

# ── step 6(b): DORMANT and "not run here" ──
tile "$CUR2" 1 2026-11-16T10:00:00+00:00 PASS 1 1

PAGE4="$W/system/organism/components/dormant-demo.md"
cat > "$PAGE4" <<'PAGE4'
---
component: demo
title: "Demo (dormant part)"
source: origin/main
checks:
  - {id: probe-a, watches: "a works"}
  - {id: probe-d, watches: "d is built but deliberately not in use", dormant: true}
receipts:
  - <brain>/status/component-demo.json
---
# Demo (dormant part)

## Status
<!-- STATUS:BEGIN -->
<!-- STATUS:END -->
PAGE4
python3 "$TOOL" stamp "$PAGE4" --repo "$W" --brain "$BRAIN" --now "$NOW" > /dev/null 2>&1
grep -m1 '^Status:' "$PAGE4" | grep -qE "^Status: LIVE · .* · 1 dormant" && ok "mixed page: the non-DORMANT checks roll up, dormant counted beside" || bad "mixed dormant: $(grep -m1 '^Status:' "$PAGE4")"
grep -F "| probe-d |" "$PAGE4" | grep -qF "DORMANT (built, not in use)" && ok "dormant check row reads DORMANT, outside the roll-up" || bad "dormant row: $(grep -F '| probe-d |' "$PAGE4")"

PAGE5="$W/system/organism/components/all-dormant.md"
cat > "$PAGE5" <<'PAGE5'
---
component: demo
title: "Demo (all dormant)"
source: origin/main
checks:
  - {id: probe-d1, watches: "d1 built, not in use", dormant: true}
  - {id: probe-d2, watches: "d2 built, not in use", dormant: true}
---
# Demo (all dormant)

## Status
<!-- STATUS:BEGIN -->
<!-- STATUS:END -->
PAGE5
python3 "$TOOL" stamp "$PAGE5" --repo "$W" --brain "$BRAIN" --now "$NOW" > /dev/null 2>&1
grep -m1 '^Status:' "$PAGE5" | grep -qF "Status: DORMANT (all 2 checks dormant)" && ok "an all-DORMANT page reads DORMANT" || bad "all dormant: $(grep -m1 '^Status:' "$PAGE5")"

PAGE6="$W/system/organism/components/notrun.md"
cat > "$PAGE6" <<'PAGE6'
---
component: demo
title: "Demo (not run here)"
source: origin/main
checks:
  - {id: probe-a, watches: "a works"}
  - {id: probe-r, watches: "the job-sim rig", not_run: "the rig is benched on this machine (it rewrote real state, 2026-11-17)"}
receipts:
  - <brain>/status/component-demo.json
---
# Demo (not run here)

## Status
<!-- STATUS:BEGIN -->
<!-- STATUS:END -->
PAGE6
python3 "$TOOL" stamp "$PAGE6" --repo "$W" --brain "$BRAIN" --now "$NOW" > /dev/null 2>&1
grep -m1 '^Status:' "$PAGE6" | grep -qF "untested (1 of 3 checks missing) · best earned LIVE" && ok "'not run here' reads as untested with the best earned label beside it" || bad "not run status: $(grep -m1 '^Status:' "$PAGE6")"
grep -F "| probe-r |" "$PAGE6" | grep -qF "not run here: the rig is benched" && ok "'not run here' row carries its reason, never green" || bad "not run row: $(grep -F '| probe-r |' "$PAGE6")"

# ── the deliberate drift: a file the page names is deleted on origin ──
git rm -q system/tools/a.sh && git commit -qm "drift: delete a.sh" && git push -q origin main 2>/dev/null
python3 "$TOOL" asbuilt "$PAGE" --repo "$W" > "$T/out3" 2>&1
has "$PAGE" "named but missing: \`system/tools/a.sh\`" "deliberate drift caught: deleted file named but missing"
hasnt "$PAGE" "| file | system/tools/a.sh |" "deleted file no longer listed as built"

[ "$FAIL" = 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
