#!/bin/bash
# probe-actor-writes.sh — skill-tester-rig card TR2.0b (ii): what does a REAL headless actor try to write?
# ENTRY POINT, on-demand: a person (the main window) runs it by hand from a window's Bash, NEVER from a sub-agent
# (ruling 7); listed in README "Run by hand". actor-guard.sh calls it as its first stage.
#
# Launches ONE headless actor with EXACTLY run.sh's launch shape (actor.lib.sh: throwaway HOME, LHB_JOURNAL_PATH
# inside it, --plugin-dir <the Harness tree>, rendered lab settings, bypassPermissions, Read only, stdin /dev/null),
# on the cheapest tier (model_ids.py `small`), through `budget.sh call` (cap $0.25, 1 call, watchdog), running ONE
# canary-like step: Read one file in a throwaway run dir and reply with the token it holds.
# The actor process tree runs under a CENSUS profile of the write guard:
#   guard.sh profile <tag> <allowed> <rig> <none>      the real guard's profile, its allow root narrowed to <allowed>
#                                                      (= the throwaway run dir + the actor's TMPDIR), so EVERY other
#                                                      write is denied and logged with <tag>
#   + (allow file-write* (subpath <allowed>) (with report) (with message <tag>))
#   + (allow file-write* (subpath <home>)    (with report) (with message <tag>))
#                                                      the throwaway HOME is writable (as it is under run.sh, where it
#                                                      lies inside the scratch allow root), and every write there is
#                                                      REPORTED to the unified log too (seen working 2026-10-31: an
#                                                      allow rule `(with report)` logs `allow file-write-<op> <path>`,
#                                                      tagged, transient files included)
# So the log holds every write the actor attempted: inside HOME/run dir/TMPDIR as `allow`, everywhere else as `deny`
# (nothing lands outside). Two proofs before the list is trusted (ruling 12): a guarded self-check write into HOME
# must appear as an `allow` line, and a guarded barrier write outside must appear as a `deny` line (the log is
# readable AND flushed past every earlier line). Either missing -> CANNOT-RUN, never an empty list.
#
# Each path is classified:
#   a-home   inside the run's throwaway HOME     per-run, safe: under run.sh it lies inside the scratch allow root
#   a-run    inside the run dir or its TMPDIR    per-run, safe: run.sh's RUN_DIR and TMPDIR lie inside scratch
#   b-ruled  a denial matching guard-ruled-denies.txt (cc-socks socket, fswatch probe; ruled 2026-11-01): STAYS
#            denied, named, and does NOT block the write list (the canary must reach ok=12 with it denied)
#   b        system temp (/private/var/folders/..., /private/tmp, /tmp)   denied; a proposed allowance needs a ruling
#   c        ANYTHING ELSE (real ~/.claude, ~/Library, Drive, the rig...) denied; MUST STAY DENIED, flagged loudly
#            (`⛔ REAL-STATE`), tagged REAL-CLAUDE (~/.claude, ~/.claude.json*) / REAL-HOME / OTHER
# Then it writes a PROPOSED patch to guard.sh (never applied; applying it is a ruled step, plan TR2.0b): (a-home)
# rules gated on GUARD_ACTOR_HOME, refused unless that dir lies INSIDE the scratch allow root and is not the real
# home; (b) the narrowest regex per observed temp name. (c) paths never enter the patch.
#
# Output (stdout; also kept with every artefact in ~/lifehack-scratch/skill-tester-rig/probe-actor-writes/<ts>/):
#   PROBE / CMD / ACTOR (replied, cost, turns, model) / one `WRITE <class> <allowed|denied> <path> [tag]` per path /
#   `⛔ REAL-STATE ...` per (c) path / PATCH <file|none>, and as the LAST line exactly one of:
#     WRITELIST: PROVEN a=<n> b=0 c=0                       exit 0  every write is per-run; no allowance needed
#     WRITELIST: NEEDS-RULING a=<n> b=<n> c=<n> patch=<f>   exit 3  something outside the per-run tree was needed
#     WRITELIST: CANNOT-RUN <reason>                        exit 4  launch/auth/budget/watchdog, the actor did not
#                                                                   finish (census incomplete), or a proof missing
# Usage: probe-actor-writes.sh | --print-cmd | --selftest | --selftest-case <name>   (selftests: FAKE actor only)
# Env (tests/overrides): CLAUDE_BIN, PAW_OUT_ROOT, PAW_TOKEN_FILE, PAW_PLUGIN_DIR, PAW_LOG_WAIT (s, default 20),
#   SKILL_TESTER_SCRATCH (budget ledgers), LIFEHACK_V2. Exit 2 = usage/refused. macOS bash 3.2, BSD tools, no set -e.

RIG="$(cd "$(dirname "$0")" && pwd)"
SELF="$RIG/$(basename "$0")"
V2="${LIFEHACK_V2:-$HOME/lifehack-v2}"
SCRATCH_ROOT="$HOME/lifehack-scratch/skill-tester-rig"
TIER="small"; CAP_USD="0.25"
. "$RIG/wait.lib.sh" || { echo "WRITELIST: CANNOT-RUN cannot source wait.lib.sh"; exit 4; }
. "$RIG/actor.lib.sh" || { echo "WRITELIST: CANNOT-RUN cannot source actor.lib.sh"; exit 4; }
realp() { python3 -I -B -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"; }

# census_read <tag> <start> <barrier> <out> : one `log show`; writes "<allow|deny>\t<op>\t<path>" lines to <out>;
# returns 0 only if the barrier's deny line is in it (the handshake for wait_until)
census_read() {
  /usr/bin/log show --start "$2" --style ndjson --predicate "sender == \"Sandbox\" AND eventMessage CONTAINS \"$1\"" 2>/dev/null |
  python3 -I -B -c '
import json, re, sys
tag, barrier, out = sys.argv[1:4]
rx = re.compile(r"Sandbox: .*?\(\d+\) (allow|deny)(?:\(\d+\))? (file-write[a-z-]*) (.*)$")
rows, seen = [], False
for line in sys.stdin:
    try:
        m = json.loads(line).get("eventMessage") or ""
    except Exception:
        continue
    first, _, rest = m.partition("\n")
    if rest.strip() != tag:
        continue
    r = rx.search(first)
    if not r:
        continue
    kind, op, p = r.groups()
    if p == barrier and kind == "deny":
        seen = True
        continue
    rows.append("%s\t%s\t%s" % (kind, op, p))
with open(out, "w") as fh:
    fh.write("".join(x + "\n" for x in rows))
sys.exit(0 if seen else 4)
' "$1" "$3" "$4"
}

# classify <raw> <home> <allowed> <real-home> <selfcheck> <tsv> : one row per unique path:
#   class \t outcome \t ops \t path \t tag     (exit 0; exit 4 if the self-check allow line is missing)
classify() {
  python3 -I -B - "$@" <<'PY'
import os, sys
raw, home, allowed, realhome, selfcheck, tsv, ruledf = sys.argv[1:8]
import re
RULED = [l.strip() for l in open(ruledf, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
def under(p, root):
    root = root.rstrip("/")
    return p == root or p.startswith(root + "/")
TEMP = ["/private/var/folders", "/var/folders", "/private/tmp", "/tmp"]
paths = {}
seen_self = False
for ln in open(raw, encoding="utf-8", errors="replace"):
    kind, _, rest = ln.rstrip("\n").partition("\t")
    op, _, p = rest.partition("\t")
    if not p:
        continue
    if p == selfcheck:
        seen_self = seen_self or kind == "allow"
        continue
    d = paths.setdefault(p, {"ops": set(), "kinds": set()})
    d["ops"].add(op.replace("file-write-", "")); d["kinds"].add(kind)
rows = []
for p in sorted(paths):
    d = paths[p]
    outcome = "denied" if "deny" in d["kinds"] else "allowed"
    tag = "-"
    if under(p, home): cls = "a-home"
    elif under(p, allowed): cls = "a-run"
    elif any(re.fullmatch(r, p) for r in RULED): cls = "b-ruled"   # guard-ruled-denies.txt: STAYS denied, named
    elif any(under(p, t) for t in TEMP): cls = "b"
    else:
        cls = "c"
        if under(p, os.path.join(realhome, ".claude")) or os.path.basename(p).startswith(".claude.json") and os.path.dirname(p) == realhome:
            tag = "REAL-CLAUDE"
        elif under(p, realhome): tag = "REAL-HOME"
        else: tag = "OTHER"
    rows.append("%s\t%s\t%s\t%s\t%s" % (cls, outcome, ",".join(sorted(d["ops"])), p, tag))
with open(tsv, "w") as fh:
    fh.write("class\toutcome\tops\tpath\ttag\n" + "".join(r + "\n" for r in rows))
sys.exit(0 if seen_self else 4)
PY
}

# make_patch <tsv> <home> <guard.sh> <out-patch> <stamp> : the PROPOSED guard.sh patch (never applied here).
# prints the patch path, or `none <why>`
make_patch() {
  python3 -I -B - "$@" <<'PY'
import os, re, subprocess, sys
tsv, home, guard, outp, stamp = sys.argv[1:6]
rows = [l.rstrip("\n").split("\t") for l in open(tsv)][1:]
A = [r[3] for r in rows if r[0] == "a-home"]
B = [r[3] for r in rows if r[0] == "b"]
if not A and not B:
    print("none (no a-home or b writes observed)"); sys.exit(0)
SPECIAL = set(".^$*+?()[]{}|\\")
def esc(s): return "".join("\\" + c if c in SPECIAL else c for c in s)
def gen(name):
    # narrowest generalisation of ONE path component: digit runs and long hex/uuid runs become classes
    out, i = "", 0
    for m in re.finditer(r"[0-9A-Fa-f-]{8,}|[0-9]+", name):
        tok = m.group(0)
        if not tok.isdigit() and not re.search(r"[0-9]", tok):
            continue
        out += esc(name[i:m.start()]) + ("[0-9]+" if tok.isdigit() else "[0-9A-Fa-f-]+"); i = m.end()
    return out + esc(name[i:])
lines = []
if A:
    rels = sorted(set(os.path.relpath(p, home) for p in A))
    tops = {}   # key: the first component, or the first TWO when the write lies deeper (".claude/run", not ".claude")
    for r in rels:
        parts = r.split("/")
        key = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        tops.setdefault(key, set()).add(len(parts) - len(key.split("/")) + 1)
    lines += ['  # (a) the actor\'s throwaway HOME, gated: GUARD_ACTOR_HOME must lie INSIDE <scratch> and is never the real',
              '  #     home. Redundant while <scratch> is allowed wholesale; it is the actor\'s allowance if that is narrowed.',
              '  if [ -n "${GUARD_ACTOR_HOME:-}" ]; then',
              '    case "$GUARD_ACTOR_HOME/" in "$scratch"/?*) ;; *) echo "guard: GUARD_ACTOR_HOME must lie inside $scratch" >&2; return 1 ;; esac',
              '    [ "$GUARD_ACTOR_HOME" != "$HOME" ] || { echo "guard: GUARD_ACTOR_HOME is the real home" >&2; return 1; }']
    for top in sorted(tops):
        n = sum(1 for r in rels if r == top or r.startswith(top + "/"))
        if max(tops[top]) > 1:
            lines.append('    echo "(allow file-write* (subpath $(sbq "$GUARD_ACTOR_HOME/%s")))"   # observed %d path(s) below it' % (top, n))
        elif gen(top) == esc(top):
            lines.append('    echo "(allow file-write* (literal $(sbq "$GUARD_ACTOR_HOME/%s")))"' % top)
        else:
            lines.append('    echo "(allow file-write* (regex #\\"^$(rxq "$GUARD_ACTOR_HOME")/%s\\$\\"))"   # observed: %s' % (gen(top), top))
    lines.append('  fi')
if B:
    lines.append('  # (b) system temp: the narrowest generalisation of each observed name (a TMPDIR bypass); needs a ruling')
    # the per-user temp/cache dirs are RESOLVED AT RUN TIME (getconf), never typed: no machine path enters guard.sh
    def conf(k):
        try:
            v = subprocess.run(["getconf", k], capture_output=True, text=True).stdout.strip()
            return os.path.realpath(v) if v else None
        except OSError:
            return None
    roots = [(conf("DARWIN_USER_TEMP_DIR"), '$(rxq "$(cd "$(getconf DARWIN_USER_TEMP_DIR)" && pwd -P)")'),
             (conf("DARWIN_USER_CACHE_DIR"), '$(rxq "$(cd "$(getconf DARWIN_USER_CACHE_DIR)" && pwd -P)")'),
             ("/private/tmp", "/private/tmp")]
    rules = {}
    for p in B:
        hit = [(r, expr) for r, expr in roots if r and p.startswith(r + "/")]
        if not hit:
            rules[esc(p).replace("$", "\\$") + "\\$"] = p; continue
        r, expr = hit[0]
        rest = p[len(r) + 1:].split("/")
        shown = (("<%s>" % expr.split("getconf ")[1].split(")")[0]) if expr.startswith("$(") else r) + "/" + "/".join(rest)
        rules[(expr if expr.startswith("$(") else esc(expr)) + "/" + gen(rest[0]) + ("(/.*)?\\$" if len(rest) > 1 else "\\$")] = shown
    for rx in sorted(rules):
        lines.append('  echo "(allow file-write* (regex #\\"^%s\\"))"   # observed: %s' % (rx, rules[rx]))
block = ["  # -- TR2.0b PROPOSED by probe-actor-writes.sh %s: NOT APPLIED; applying it is a ruled step --" % stamp,
         "  rxq() { printf '%s' \"$1\" | sed 's/[][\\.^$*+?(){}|]/\\\\&/g'; }   # ERE-escape a path for an SBPL regex"] + lines
src = open(guard).read().split("\n")
anchor = [i for i, l in enumerate(src) if 'sh-thd-[0-9]+' in l and l.lstrip().startswith("echo")]
if len(anchor) != 1:
    print("none (anchor line not found exactly once in guard.sh)"); sys.exit(0)
new = src[:anchor[0] + 1] + block + src[anchor[0] + 1:]
prop = outp + ".guard.sh.proposed"
open(prop, "w").write("\n".join(new))
d = subprocess.run(["diff", "-u", "--label", "a/guard.sh", "--label", "b/guard.sh", guard, prop], capture_output=True, text=True)
open(outp, "w").write(d.stdout)
print(outp)
PY
}

probe() {
  local mode="$1" BIN="${CLAUDE_BIN:-}" STAMP OUT T0 TAG PH AL RUNW TMPD SETTINGS TOKEN TOKEN_FILE PLUGIN MODEL_ID
  local RUN_ID PROMPT RES BLOG rc SELFCHK BARRIER REALHOME
  if [ -n "${RIG_GUARD_TAG:-}" ]; then echo "WRITELIST: CANNOT-RUN refused: running inside a guarded run (log show cannot run sandboxed)"; exit 2; fi
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  OUT="${PAW_OUT_ROOT:-$SCRATCH_ROOT/probe-actor-writes}/$STAMP"
  case "$(realp "${PAW_OUT_ROOT:-$SCRATCH_ROOT}")/" in "$(realp "$HOME/lifehack-scratch")"/*) ;;
    *) echo "WRITELIST: CANNOT-RUN refused: output root outside ~/lifehack-scratch (ruling 6)"; exit 2 ;; esac
  RUN_ID="probe-actor-writes-$STAMP"
  # TR2.0b design (b), exactly as run.sh (layout.py): ONE throwaway HOME; the step's input lives in its .claude/run
  mkdir -p "$OUT/allowed/tmp" "$(python3 -I "$RIG/run_helper.py" rundir "$OUT" "$RUN_ID")" || { echo "WRITELIST: CANNOT-RUN cannot create $OUT"; exit 4; }
  OUT="$(realp "$OUT")"; PH="$(python3 -I "$RIG/run_helper.py" actorhome "$OUT" "$RUN_ID")"; AL="$OUT/allowed"
  RUNW="$(python3 -I "$RIG/run_helper.py" rundir "$OUT" "$RUN_ID")"; TMPD="$AL/tmp"; REALHOME="$(realp "$HOME")"
  exec > >(tee "$OUT/result.txt") 2>&1
  cannot() { echo "WRITELIST: CANNOT-RUN $1"; exit 4; }
  PLUGIN="${PAW_PLUGIN_DIR:-$(realp "$RIG/../../..")}"
  [ -f "$PLUGIN/hooks/hooks.json" ] || cannot "no Harness at $PLUGIN (hooks/hooks.json): --plugin-dir would load nothing"
  MODEL_ID="$(python3 -I -B -c 'import sys; sys.path.insert(0, sys.argv[1]); from model_ids import model_id; print(model_id(sys.argv[2]))' "$V2/shared/tools" "$TIER")"
  [ -n "$MODEL_ID" ] || cannot "no-model-id (shared/tools/model_ids.py)"
  SETTINGS="$OUT/lab-settings.json"
  mkdir -p "$SCRATCH_ROOT" && python3 -I -B "$RIG/run_helper.py" render-settings "$RIG/lab-settings.template.json" "$SETTINGS" \
    "$(realp "$SCRATCH_ROOT")" "$RIG" "$PH" || cannot "lab-settings-render-failed"
  TOKEN="TOK$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"
  printf '%s\n' "$TOKEN" > "$RUNW/canary.txt"
  PROMPT="Use the Read tool exactly once to read the file $RUNW/canary.txt, then reply with its single line verbatim and nothing else. Do not use any other tool and do not retry."
  TAG="PAWCENSUS-$STAMP-$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
  SELFCHK="$PH/.census-selfcheck-$TAG"; BARRIER="$OUT/.census-barrier-$TAG"
  bash "$RIG/guard.sh" profile "$TAG" "$AL" "$RIG" "$AL/.standin-none" > "$OUT/census.sb" || cannot "guard.sh profile failed"
  { echo ";; TR2.0b census additions: report every write into the per-run tree (allow), deny-and-log the rest"
    echo "(allow file-write* (subpath \"$AL\") (with report) (with message \"$TAG\"))"
    echo "(allow file-write* (subpath \"$PH\") (with report) (with message \"$TAG\"))"; } >> "$OUT/census.sb"
  BIN_SHOWN="${BIN:-$(command -v claude)}"
  actor_argv_build "$PH" "${BIN_SHOWN:-claude}" "$PROMPT" "$MODEL_ID" "$SETTINGS" "$PLUGIN" || cannot "actor argv incomplete"
  echo "PROBE: out=$OUT model=$MODEL_ID tag=$TAG plugin=$PLUGIN home=$PH cwd=$RUNW TMPDIR=$TMPD cap=\$$CAP_USD"
  echo "CMD: (cd $RUNW && TMPDIR=$TMPD budget.sh call $RUN_ID -- /usr/bin/sandbox-exec -f $OUT/census.sb ${ACTOR[*]}) </dev/null  [CLAUDE_CODE_OAUTH_TOKEN exported]"
  [ "$mode" = print ] && exit 0
  BIN="$BIN_SHOWN"
  [ -n "$BIN" ] && [ -x "$BIN" ] || cannot "no-claude-binary"
  TOKEN_FILE="${PAW_TOKEN_FILE:-$HOME/.config/lifehack/claude-oauth-token}"
  if [ -r "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ]; then
    CLAUDE_CODE_OAUTH_TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"; export CLAUDE_CODE_OAUTH_TOKEN
  elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then unset CLAUDE_CODE_OAUTH_TOKEN
  else cannot "no-auth (no $TOKEN_FILE and no ANTHROPIC_API_KEY)"; fi
  actor_argv_build "$PH" "$BIN" "$PROMPT" "$MODEL_ID" "$SETTINGS" "$PLUGIN" || cannot "actor argv incomplete"
  BLOG="$OUT/budget.log"; RES="$OUT/result.json"
  bash "$RIG/budget.sh" open "$RUN_ID" --usd "$CAP_USD" --calls 1 >> "$BLOG" 2>&1 || cannot "budget-open-failed (see $BLOG)"
  T0="$(date -v-2S '+%Y-%m-%d %H:%M:%S')"
  # proof 1 (before the actor): a guarded write into HOME must show up as a tagged `allow` report
  /usr/bin/sandbox-exec -f "$OUT/census.sb" /bin/bash -c ': > "$1"' _ "$SELFCHK" 2>> "$OUT/census.err" || cannot "census profile refused a write into the throwaway HOME (see $OUT/census.err)"
  ( cd "$RUNW" && TMPDIR="$TMPD" bash "$RIG/budget.sh" call "$RUN_ID" -- /usr/bin/sandbox-exec -f "$OUT/census.sb" "${ACTOR[@]}" ) \
    > "$RES" 2>> "$BLOG" </dev/null
  rc=$?
  # proof 2 (after the actor's tree is gone): the barrier, a denied write through the same profile
  /usr/bin/sandbox-exec -f "$OUT/census.sb" /bin/bash -c '( : > "$1" ) 2>/dev/null && { rm -f "$1"; exit 9; }; exit 0' _ "$BARRIER"
  [ $? = 9 ] && cannot "barrier write LANDED: the census profile does not deny outside the per-run tree"
  wait_until "${PAW_LOG_WAIT:-20}" "census log barrier $BARRIER" census_read "$TAG" "$T0" "$BARRIER" "$OUT/census.raw" \
    || cannot "census log unreadable: barrier not seen (WAIT-TIMEOUT)"
  classify "$OUT/census.raw" "$PH" "$AL" "$REALHOME" "$SELFCHK" "$OUT/writes.tsv" "$RIG/guard-ruled-denies.txt" \
    || cannot "self-check write into HOME not reported: the census would miss home writes"
  # the actor's own result
  local K; K="$(python3 -I -B -c '
import json, sys
tok = sys.argv[2]; r = {}
try:
    for ln in open(sys.argv[1]):
        ln = ln.strip()
        if ln.startswith("{"):
            j = json.loads(ln)
            if j.get("type") == "result": r = j
except (OSError, ValueError):
    pass
print("REPLIED=%s" % ("yes" if tok in str(r.get("result", "")) and not r.get("is_error") else "no"))
print("COST=%s" % r.get("total_cost_usd", "UNKNOWN")); print("TURNS=%s" % r.get("num_turns", "UNKNOWN"))
print("MODEL=%s" % r.get("model", "unknown"))' "$RES" "$TOKEN")"
  kv() { printf '%s\n' "$K" | sed -n "s/^$1=//p"; }
  echo "ACTOR: replied=$(kv REPLIED) total_cost_usd=$(kv COST) num_turns=$(kv TURNS) model=$(kv MODEL) rc=$rc result=$RES"
  local na nb nc
  tail -n +2 "$OUT/writes.tsv" | while IFS="$(printf '\t')" read -r cls oc ops p tag; do
    echo "WRITE $cls $oc $p ($ops)$( [ "$tag" != - ] && printf ' %s' "$tag")"
  done
  tail -n +2 "$OUT/writes.tsv" | awk -F'\t' '$1=="c"{print "⛔ REAL-STATE write attempted (" $2 ", MUST STAY DENIED, " $5 "): " $4}'
  na="$(awk -F'\t' 'NR>1 && $1 ~ /^a-/' "$OUT/writes.tsv" | wc -l | tr -d ' ')"
  local nr; nr="$(awk -F'\t' 'NR>1 && $1=="b-ruled"' "$OUT/writes.tsv" | wc -l | tr -d ' ')"
  nb="$(awk -F'\t' 'NR>1 && $1=="b"' "$OUT/writes.tsv" | wc -l | tr -d ' ')"
  nc="$(awk -F'\t' 'NR>1 && $1=="c"' "$OUT/writes.tsv" | wc -l | tr -d ' ')"
  local PATCH; PATCH="$(make_patch "$OUT/writes.tsv" "$PH" "$RIG/guard.sh" "$OUT/proposed-guard.patch" "$STAMP" 2>> "$OUT/patch.err")"
  [ -n "$PATCH" ] || PATCH="none (PATCH-GENERATOR-FAILED, see $OUT/patch.err)"
  echo "PATCH: $PATCH"
  case "$rc" in
    75) cannot "budget-refused (cap \$$CAP_USD)" ;;
    124) cannot "watchdog (budget.sh killed the actor tree)" ;;
  esac
  [ "$(kv REPLIED)" = yes ] || cannot "census-incomplete: the actor did not finish the step (rc=$rc; stderr: $(grep -v '^budget' "$BLOG" | tail -2 | tr '\n\t' '  ' | cut -c1-160))"
  echo "CAVEAT: the gate trusts step files only because they sit in the actor's own \$HOME/.claude; in real use the same holds under the real ~/.claude"
  [ "$nr" = 0 ] || echo "RULED: $nr write(s) matched guard-ruled-denies.txt: denied, named, not blocking (ruling 2026-11-01)"
  if [ "$nb" = 0 ] && [ "$nc" = 0 ]; then echo "WRITELIST: PROVEN a=$na b=0 c=0"; exit 0; fi
  echo "WRITELIST: NEEDS-RULING a=$na b=$nb c=$nc patch=$PATCH"; exit 3
}

# ───────────────────────────────────────── selftest (FAKE actor only) ─────────────────────────────────────────
FX="$RIG/probe-actor-writes-fixture/fake-actor.sh"
st_base() { echo "$SCRATCH_ROOT/selftest/probe-actor-writes-$1"; }
# st_case <name> <base> : one scenario against THIS copy of the probe; prints `  ok|FAIL <name> ...`; rc 0/1
st_case() {
  local name="$1" B="$2" out rc last o fails="" systmp
  mkdir -p "$B/real-state/.claude" "$B/out" || return 1
  printf 'fake-token\n' > "$B/token"
  systmp="$(realp "$(getconf DARWIN_USER_TEMP_DIR)")"
  local W="" M=""
  # the RULED denial's own fixed location (guard-ruled-denies.txt: the fswatch probe under /private/tmp/claude-<uid>):
  # the test must aim at exactly that path, and asserts the write is DENIED and never lands
  local RULED_T="/private/tmp/claude-$(id -u)"   # allow-silence: deliberate denied-write target named by the TR2.0b ruling; asserted never to land
  case "$name" in
    three) W="@systmp:$B/real-state/.claude/state.json" ;;
    clean) W="" ;;
    ruled) W="$RULED_T/fswatch-probe-pawst$$" ;;
    noreply) M=noreply ;;
    launchfail) M=launchfail ;;
    *) echo "  FAIL unknown case $name"; return 1 ;;
  esac
  out="$(env CLAUDE_BIN="$FX" PAW_OUT_ROOT="$B/out" PAW_TOKEN_FILE="$B/token" PAW_PLUGIN_DIR="$(realp "$V2")" \
        SKILL_TESTER_SCRATCH="$B" FAKE_ACTOR_REAL_HOME="$HOME" FAKE_ACTOR_WRITES="$W" FAKE_ACTOR_MODE="$M" \
        BUDGET_WATCHDOG_FLOOR=20 bash "$SELF" 2>&1)"; rc=$?
  last="$(printf '%s\n' "$out" | tail -1)"
  o="$(ls -d "$B/out"/*/ 2>/dev/null | tail -1)"; o="${o%/}"
  case "$name" in
    three)
      [ "$rc" = 3 ] || fails="$fails rc=$rc"
      printf '%s' "$last" | grep -qE '^WRITELIST: NEEDS-RULING a=[0-9]+ b=1 c=1 patch=/' || fails="$fails last-line"
      printf '%s\n' "$out" | grep -qE "^WRITE a-home allowed $o/actor-home/probe-actor-writes-[^/]+/\.claude\.json \(" || fails="$fails no-a-home"
      printf '%s\n' "$out" | grep -qE "^WRITE b denied $systmp/claude-fake-[0-9]+\.tmp \(" || fails="$fails no-b-systmp"
      printf '%s\n' "$out" | grep -qE "^WRITE c denied $(realp "$B")/real-state/\.claude/state\.json \(.*\) REAL-HOME$" || fails="$fails no-c"
      printf '%s\n' "$out" | grep -qF "⛔ REAL-STATE write attempted (denied, MUST STAY DENIED, REAL-HOME): $(realp "$B")/real-state/.claude/state.json" || fails="$fails no-flag"
      [ ! -e "$B/real-state/.claude/state.json" ] || fails="$fails c-write-LANDED"
      ls "$systmp" 2>/dev/null | grep -q '^claude-fake-' && fails="$fails b-write-LANDED"
      st_patch "$o" "$B" || fails="$fails patch"
      ;;
    clean)
      [ "$rc" = 0 ] || fails="$fails rc=$rc"
      printf '%s' "$last" | grep -qE '^WRITELIST: PROVEN a=[1-9][0-9]* b=0 c=0$' || fails="$fails last-line"
      printf '%s\n' "$out" | grep -qE "^WRITE a-home allowed $o/actor-home/probe-actor-writes-[^/]+/\.claude/run/fire-journal\.jsonl " || fails="$fails no-journal-write"
      ;;
    ruled)
      [ "$rc" = 0 ] || fails="$fails rc=$rc"
      printf '%s' "$last" | grep -qE '^WRITELIST: PROVEN a=[1-9][0-9]* b=0 c=0$' || fails="$fails last-line"
      printf '%s\n' "$out" | grep -qE "^WRITE b-ruled denied $RULED_T/fswatch-probe-pawst[0-9]+ " || fails="$fails no-b-ruled"
      ls "$RULED_T/" | grep -q '^fswatch-probe-pawst' && fails="$fails ruled-write-LANDED"
      grep -q 'fswatch-probe' "$o/proposed-guard.patch" 2>/dev/null && fails="$fails ruled-path-in-patch"
      ;;
    noreply)
      [ "$rc" = 4 ] || fails="$fails rc=$rc"
      printf '%s' "$last" | grep -q '^WRITELIST: CANNOT-RUN census-incomplete' || fails="$fails last-line" ;;
    launchfail)
      [ "$rc" = 4 ] || fails="$fails rc=$rc"
      printf '%s' "$last" | grep -q '^WRITELIST: CANNOT-RUN census-incomplete' || fails="$fails last-line"
      printf '%s\n' "$out" | grep -q '^WRITE ' && fails="$fails writes-listed-for-a-launch-failure" ;;
  esac
  if [ -z "$fails" ]; then echo "  ok   $name → $last"; return 0; fi
  echo "  FAIL $name:$fails → $last"; printf '%s\n' "$out" | grep -E '^(WRITE|ACTOR|PATCH|⛔)' | sed 's/^/       | /'; return 1
}
# st_patch <out> <base> : the proposed patch applies to a COPY of guard.sh, yields a profile sandbox-exec accepts,
# carries the gated (a) rules and the (b) regex, never the (c) path, and refuses a GUARD_ACTOR_HOME at the real home
st_patch() {
  local o="$1" B="$2" C="$2/patchcopy" bad=""
  [ -s "$o/proposed-guard.patch" ] || { echo "       | no patch file"; return 1; }
  rm -rf "$C"; mkdir -p "$C" && cp "$RIG/guard.sh" "$RIG/receipt.sh" "$C/" || return 1
  ( cd "$C" && patch -s -p1 < "$o/proposed-guard.patch" ) > "$B/patch.log" 2>&1 || bad="$bad apply"
  grep -qF "$(realp "$B")/real-state" "$o/proposed-guard.patch" && bad="$bad c-path-in-patch"
  grep -q 'GUARD_ACTOR_HOME' "$o/proposed-guard.patch" || bad="$bad no-gate"
  grep -qE 'claude-fake-\[0-9\]\+' "$o/proposed-guard.patch" || bad="$bad no-b-regex"
  mkdir -p "$B/scr/ahome"
  local S; S="$(realp "$B/scr")"
  GUARD_ACTOR_HOME="$S/ahome" bash "$C/guard.sh" profile PT "$S" /x/rig /x/standin > "$B/p1.sb" 2>> "$B/patch.log" || bad="$bad gated-profile-failed"
  grep -qF "(literal \"$S/ahome/.claude.json\")" "$B/p1.sb" || bad="$bad no-a-rule"
  /usr/bin/sandbox-exec -f "$B/p1.sb" /usr/bin/true 2>> "$B/patch.log" || bad="$bad sbpl-rejected"
  # the (b) rule BITES narrowly: the observed name pattern is writable under the patched profile, a sibling is not
  local TD; TD="$(cd "$(getconf DARWIN_USER_TEMP_DIR)" && pwd -P)"
  /usr/bin/sandbox-exec -f "$B/p1.sb" /bin/bash -c ': > "$1"' _ "$TD/claude-fake-1$$.tmp" 2>> "$B/patch.log" || bad="$bad b-rule-does-not-match"
  /usr/bin/sandbox-exec -f "$B/p1.sb" /bin/bash -c ': > "$1"' _ "$TD/claude-fakeX$$.tmp" 2>> "$B/patch.log" && bad="$bad b-rule-too-wide"
  rm -f "$TD/claude-fake-1$$.tmp" "$TD/claude-fakeX$$.tmp"
  GUARD_ACTOR_HOME="$HOME" bash "$C/guard.sh" profile PT "$S" /x/rig /x/standin > "$B/p2.sb" 2>> "$B/patch.log" && bad="$bad real-home-accepted"
  GUARD_ACTOR_HOME="$HOME/.claude" bash "$C/guard.sh" profile PT "$S" /x/rig /x/standin > "$B/p3.sb" 2>> "$B/patch.log" && bad="$bad outside-scratch-accepted"
  cmp -s "$RIG/guard.sh" "$C/guard.sh" && bad="$bad copy-unchanged"
  [ -z "$bad" ] && return 0
  echo "       | patch:$bad (see $B/patch.log)"; return 1
}
selftest() {
  local B fails=0 n=0 c FFB
  [ -x "$FX" ] || { echo "SELFTEST probe-actor-writes FAILED: no fixture $FX"; exit 1; }
  B="$(st_base "$(date -u +%Y%m%dT%H%M%SZ)-$$")"
  echo "SELFTEST probe-actor-writes (FAKE actor $FX; base $B)"
  for c in three clean ruled noreply launchfail; do
    n=$((n+1)); st_case "$c" "$B/$c" || fails=$((fails+1))
  done
  # FAIL-FIRST: broken copies of this rig must FAIL the 'three' case
  ff() {  # ff <label> <sed-expr> : copy, break, run the copy's 'three' case; it must fail
    local C="$B/ff-$1"; n=$((n+1))
    rm -rf "$C"; cp -Rp "$RIG" "$C" && find "$C" -name __pycache__ -prune -exec rm -rf {} +
    sed -i.bak "$2" "$C/probe-actor-writes.sh" && rm -f "$C/probe-actor-writes.sh.bak"
    if cmp -s "$SELF" "$C/probe-actor-writes.sh"; then echo "  FAIL ff-$1: the break did not apply"; fails=$((fails+1)); return; fi
    if bash "$C/probe-actor-writes.sh" --selftest-case three "$B/ff-$1-run" > "$B/ff-$1.log" 2>&1; then
      echo "  FAIL ff-$1: the broken copy PASSED"; fails=$((fails+1))
    else echo "  ok   ff-$1: broken copy FAILED as it must ($(grep -m1 'FAIL three' "$B/ff-$1.log" | cut -c1-110))"; fi
    rm -rf "$C"
  }
  ff no-deny-side   's/^    rows.append("%s\\t%s\\t%s" % (kind, op, p))$/    rows.append("%s\\t%s\\t%s" % (kind, op, p)) if kind == "allow" else None/'
  ff temp-as-home   's|^TEMP = \["/private/var/folders", "/var/folders", "/private/tmp", "/tmp"\]|TEMP = []|'
  if [ "$fails" = 0 ]; then echo "SELFTEST probe-actor-writes $n/$n ALL OK"; exit 0; fi
  echo "SELFTEST probe-actor-writes FAILED ($fails/$n)"; exit 1
}

case "${1:-}" in
  "") probe run ;;
  --print-cmd) probe print ;;
  --selftest) selftest ;;
  --selftest-case) [ -n "${2:-}" ] && [ -n "${3:-}" ] || { echo "usage: --selftest-case <name> <base>" >&2; exit 2; }
                   [ -x "$FX" ] || exit 1; st_case "$2" "$3" ;;
  *) echo "usage: probe-actor-writes.sh [--print-cmd|--selftest|--selftest-case <name> <base>]" >&2; exit 2 ;;
esac
