#!/usr/bin/env bash
# install-schedulers.sh — replay the schedule from the VERSIONED manifest (pulse-config.md) onto
# THIS machine's OS scheduler. This is what makes the schedule edit-once-and-run-everywhere: update
# the ```crontab``` block in pulse-config.md -> commit -> run this on a machine -> that machine is
# current. No hand-editing crontab, one declaration per job, no duplication.
#
# PORTED (2026-08-14) from claudeops-config's system/tools/install-schedulers.sh, under a 2026-08-13
# product ruling ("automation ships with its scheduler — if it ran on the donor author's laptop, it
# goes on a student's laptop"). The donor script only ever wrote a macOS/Linux crontab; this product's own
# INSTALL.md explicitly walks Windows students through a real install (Step 1's own rule: "Darwin
# means a Mac. Linux means Linux. Anything else, treat it as Windows.") — and Windows has no cron.
# That branch below is NEW DESIGN, not a port: no file in the donor answers "what does a Windows
# install need," because every install target there was implicitly a Mac.
#
# UPDATED 2026-10-27 (self-monitoring 5.2, THE DOOR): on macOS --install refuses an enabled row with a missing/TBD contract
# column, a runner outside the code root / private desk repo, a pinned absolute code path, or a raw gmail/calendar/
# sheets/curl/urllib/requests call (section 1a; `--check-row <name>` runs it alone). Refused = reason printed, no plist, exit 1.
# UPDATED 2026-10-27: macOS now installs one launchd LaunchAgent per enabled ```jobs``` row (section 1b,
# self-monitoring plan §B.1) instead of cron; Linux (crontab) and Windows (schtasks) are unchanged.
# CORRECTED 2026-10-27: everything below that says "cron on Mac", "CRON, NOT LAUNCHD, on Mac", or
# "Mac/Linux: crontab runs pulse.sh" is HISTORY and no longer true for macOS. On macOS, --install
# writes ~/Library/LaunchAgents/ai.lifehack.<job>.plist per `yes` row of the ```jobs``` block, each
# launching job-run.sh (<job> --if-overdue); job-run.sh's exit contract is 0 = output check passed ·
# 75 = stood down · 2 = transient · else failed, and its alarm is an ntfy text. pulse.sh and the
# ```crontab``` block are Linux/Windows only. See system/organism/manual.md (scheduler section).
#
# ⛔ A38, ADDRESSED DIRECTLY (found in the donor's own dead-end record, `system/sops/skill-building-
# sop.md:1207` / `records/logs/2026-05-26-cross-machine-sync-infrastructure.md`): launchd was tried
# for scheduled jobs once already and FAILED — "blocked by macOS Full Disk Access — 'Operation not
# permitted' on the Drive path" — and the donor system reverted to cron for exactly that reason.
# ⇒ CRON, NOT LAUNCHD, on Mac — but not by reflexively copying that outcome forward. A38's failure
# was specific to a job whose DATA PATH lived on a Google-Drive FUSE mount, which is what tripped
# TCC/Full-Disk-Access. This product's own INSTALL.md Step 4 now REFUSES to install into a
# Drive/Dropbox/OneDrive/iCloud folder at all (fire-tested 13/13, symlink bypass closed) — so the
# precondition that caused A38 cannot occur here; a student's data path is always a plain local
# folder, which launchd CAN read. A38 does not bind this decision. The reasons cron still won:
#   1. Windows already forces a THIRD mechanism (Task Scheduler, below) that neither cron nor
#      launchd covers — adding launchd as a mac-only FOURTH mechanism buys no cross-platform
#      unification; cron+schtasks already covers Mac+Linux+Windows with two.
#   2. The donor repo's `system/sops/cron-safety.md` documents cron's real quirks (its minimal PATH,
#      the /usr/sbin gap) from lived incidents — ⚠ VERIFIED THIS SESSION: that SOP has NOT been
#      ported to this repo yet (no `system/sops/cron-safety.md` here — it belongs to a different
#      migration category, not this one). Naming it here as a reason to prefer cron over an
#      unexplored launchd integration is directional, not a claim that the safety net already
#      exists in THIS repo — the PATH= prefix on the crontab lines below (mirroring that SOP's own
#      fix) is what actually carries the lesson forward until the doc itself lands.
#   3. Idempotent re-install is simpler for cron: ONE owned marked region in `crontab -l` (below),
#      vs juggling N per-job `.plist` files plus `launchctl load`/`unload` state. The donor's own
#      launchd block was never more than a straight copy of static plists — it never had to solve
#      the idempotent-diff problem cron's marked-region approach already solves cleanly here.
#
# ⭐ WHAT THIS MEANS FOR VERIFICATION — read together with A38's other half, the "printed PASSED for
# two months and wrote nothing" failure class this whole project is built to catch. A scheduler that
# REGISTERS successfully but is silently denied at FIRE time (permission, a wrong path, anything)
# would look identical to a healthy install if the only check is "is the crontab entry there." It is
# NOT the only check here: the proof this design relies on is downstream of the scheduler entirely —
# each job's OWN tile write (state/status/<job>.json, produced by that job's REAL work, not by this
# installer) and `health-deadman-check.sh` watching for that tile going stale. If cron itself were
# silently blocked, tiles would stop refreshing and the deadman would flag it within 45 minutes —
# UNLESS the deadman's OWN cron entry is equally blocked, which this design cannot rule out by
# construction (there is no second, independent watcher of the watcher here). That residual gap is
# named, not hidden: `--install`'s own success message below tells you how to verify EXECUTION, not
# just registration, precisely because `crontab -l` succeeding proves nothing about whether the job
# ever actually fires.
#
# THE DECISION, AND WHY: pulse.sh itself stays a Bash script rather than being rewritten in Python.
# Two things made that the smaller, safer move, not a bigger one:
#   1. Every job pulse.sh dispatches is ALSO a Bash script (system-health-run.sh, planning-health.py
#      launched via python3, etc.) — a Windows install already needs a working `bash` to run those,
#      independent of what runs the dispatcher itself. INSTALL.md's own Step 2 GUARANTEES Git Bash
#      is present on Windows (it installs Git for Windows via winget specifically so `bash` exists),
#      so that dependency is already paid for. Rewriting only pulse.sh in Python would remove Bash
#      from ONE call site while every job it dispatches still needs it — no real reduction in what a
#      Windows student's machine must have working.
#   2. pulse.sh's breaker/backoff/park-file state machine is proven (see that file's own header) —
#      re-deriving it in a second language is exactly the kind of behavioural-regression risk
#      port-manifest-04's own landmine list warns about, for a benefit (avoiding Git Bash) that
#      doesn't materialize per point 1.
#   ⇒ The generalization is in THIS file (how the dispatcher gets invoked on a schedule), not in
#     pulse.sh (what invokes it). Mac/Linux: crontab runs `bash pulse.sh` directly. Windows: Task
#     Scheduler runs Git Bash's `bash.exe pulse.sh` — same script, different trigger.
#
# ⛔ NOT PORTED, ON PURPOSE: the donor's `launchd` block (bootstrap/Supabase plists) and the
# lead-machine gate that stripped the manifest down to "rows for THIS machine". Neither concept
# exists here — this repo has one machine (docs/data-layout.md: "the two-machine plane is not part
# of this system") and nothing in this category's job list needs launchd specifically (the donor's
# own reasoning for needing it — a launchd agent cannot read a FUSE-mounted cloud-drive folder — does
# not apply to a plain local `data/` folder). If a future job genuinely needs launchd, that is new
# scope for whoever adds it, not a gap in this installer.
#
# Reads the ```crontab``` fenced block in pulse-config.md: `name | schedule(cron 5-field) | command`.
# Every row is installed (single machine — there is no `machine` column to filter on anymore).
#
# Usage:
#   install-schedulers.sh              # DRY-RUN (default, safe): print what it WOULD install
#   install-schedulers.sh --install    # actually install it
set -uo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${PULSE_CONFIG:-$CODE_ROOT/system/pulse-config.md}"
MODE="${1:---dry-run}"
BEGIN="# >>> LIFEHACK SCHEDULERS (managed by install-schedulers.sh — do not edit by hand) >>>"
END="# <<< LIFEHACK SCHEDULERS <<<"
PULSE_SH="$CODE_ROOT/system/tools/pulse.sh"

[ -f "$MANIFEST" ] || { echo "[install-schedulers] FATAL: manifest not found: $MANIFEST" >&2; exit 1; }

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

# ── 1a) THE DOOR (self-monitoring 5.2) — refuse a job row that has no contract, a pinned code path, or a runner
# that makes a raw external call. A refused row gets NO plist. Usable alone: `install-schedulers.sh --check-row <name>`
# prints PASS or the refusal reasons (one per line) and exits 0 / 1 (2 = no such row). The rules:
#   (a) outcome, check, model, budget, source are all present and not `TBD`; model is none|small|medium|large;
#       budget is an integer > 0 unless model=none.
#   (b) every script the command runs resolves (after $LIFEHACK_CODE_ROOT / $HOME expansion) under the code root or the
#       private desk repo, and the command pins no absolute code path (a /Users/... clone, a plugin cache) instead of
#       $LIFEHACK_CODE_ROOT.
#   (c) a static scan of those scripts, of what they source, and of the python/bash scripts they invoke, finds no raw
#       Gmail / Calendar / Sheets-values-get / curl / urllib / requests call. Only the files in
#       system/tools/shared-fetch-allowlist.txt (the ONE list of the shared fetch) may hold one.
#   (a2) 5.9(a) the check must match real content: a regex that only tests an exit code in a file ("rc":0), that the file is
#       non-empty (^.+$), or that it exists / is fresh, is refused as "presence-grade check".
#   (d) the same scan refuses a literal model id (claude-haiku|sonnet|opus|fable-<n>) anywhere but model.lib.sh and
#       model_ids.py, and any literal passed as --model X / model="X" / MODEL=X: a runner names a TIER and the table turns it into an id, so a retired id can never rot silently.
# TEST SEAMS: LIFEHACK_JOBS_FILE (manifest for --check-row), LIFEHACK_CODE_ROOT (code root), LIFEHACK_DESK_REPO.
DOOR_ALLOWLIST="$CODE_ROOT/system/tools/shared-fetch-allowlist.txt"
door_check_row() {   # name enabled outcome check model budget source command -> reasons on stdout; rc 0 = pass
  python3 - "${LIFEHACK_CODE_ROOT:-$CODE_ROOT}" "${LIFEHACK_DESK_REPO:-$HOME/.claude/skills/ClaudeOps}" \
    "$DOOR_ALLOWLIST" "$@" <<'DOORPY'
import os, re, shlex, sys
code, desk, allow_file, name, enabled, outcome, check, model, budget, source, cmd = sys.argv[1:12]
code = os.path.realpath(code); desk = os.path.realpath(desk); home = os.path.expanduser("~")
reasons = []

# (a) the contract
for col, val in (("outcome", outcome), ("check", check), ("model", model), ("budget", budget), ("source", source)):
    if not val.strip() or val.strip().upper() == "TBD":
        reasons.append(f"missing contract: {col}")
m = model.strip()
if m and m.upper() != "TBD" and m not in ("none", "small", "medium", "large"):
    reasons.append(f"bad model '{m}': must be none|small|medium|large")
b = budget.strip()
if b and b.upper() != "TBD" and m != "none" and not (b.isdigit() and int(b) > 0):
    reasons.append(f"bad budget '{b}': must be an integer > 0 unless model=none")

# (a2) 5.9(a): a check must match REAL CONTENT. Refused: a regex that only tests an exit code written to a file ("rc":0), that the
# file is non-empty (^.+$, .*), or -- being a bare class/anchor -- that the file merely exists / is fresh. Content = at least one
# literal word that is not an exit-code word. (A `|` is not usable in a check anyway: it is the column separator of the row.)
EXIT_WORDS = {"rc", "exit", "code", "exitcode", "returncode", "retcode", "ret", "status"}
OK_WORDS = {"ok", "success", "pass", "passed", "done", "true"}
def presence_grade(rx):
    lit = re.sub(r"\[[^\]]*\]", "", rx)               # bracket expressions are classes, not content
    lit = re.sub(r"\\[A-Za-z]", "", lit)              # \S \w \d ... are classes too
    words = {w.lower() for w in re.findall(r"[A-Za-z]+", lit)}
    if not words:
        return "matches any non-empty line: it proves the file exists or is non-empty, not what is in it"
    if words & EXIT_WORDS and words <= (EXIT_WORDS | OK_WORDS):
        return "tests only an exit code / bare status written to a file: the exit code is never the proof"
    return ""
ck = check.strip()
if ck and ck.upper() != "TBD":
    if " ~ " not in ck:
        reasons.append("presence-grade check: not '<path> ~ <regex>', so it can only test that the file exists")
    else:
        _why = presence_grade(ck.split(" ~ ", 1)[1].strip())
        if _why: reasons.append(f"presence-grade check: {_why}")

def under(p, root):
    return p == root or p.startswith(root.rstrip("/") + "/")

def expand(tok):
    for k, v in (("LIFEHACK_CODE_ROOT", code), ("CODE_ROOT", code), ("HOME", home)):
        tok = tok.replace("${%s}" % k, v).replace("$%s" % k, v)
    if tok.startswith("~/"): tok = home + tok[1:]
    return tok

# (b) the runner
cmd = cmd.strip()
scripts = []
if cmd.startswith("@"):
    pass   # a builtin: no script of its own
elif cmd:
    if code in cmd or "/plugins/cache/" in cmd or re.search(r"/(Users|home)/[^/\s\"']+/[^\s\"']*(lifehack-v2|lifehack-brain)", cmd):
        reasons.append("pinned code path in command: use $LIFEHACK_CODE_ROOT, never an absolute clone/plugin path")
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True); lex.whitespace_split = True
        toks = list(lex)
    except ValueError as e:
        toks = []; reasons.append(f"unparseable command: {e}")
    for t in toks:
        e = expand(t)
        if re.search(r"\.(sh|py)$", e) and not e.startswith("-"):
            scripts.append(e)
    if not scripts and not any(r.startswith("unparseable") for r in reasons):
        reasons.append("no runner script found in command")
for e in scripts:
    if "$" in e:
        reasons.append(f"unresolvable variable in runner path: {e}")
    elif not (under(os.path.realpath(e), code) or under(os.path.realpath(e), desk)):
        reasons.append(f"runner outside the code root and the private desk repo: {e}")

# (c) the static scan
allow = set()
try:
    for ln in open(allow_file, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#"): allow.add(os.path.realpath(os.path.join(code, ln)))
except OSError:
    reasons.append(f"shared-fetch allowlist unreadable: {allow_file}")
G = r'(?:\bgws\b|\bGWS\w*\b|\$\{?GWS\w*\}?)["\'\]]*[\s,]+["\']?'
RAW = [("gws gmail", re.compile(G + r"gmail\b")),
       ("gws calendar", re.compile(G + r"calendar\b")),
       ("gws sheets values get", re.compile(r"\bsheets\b.*\bvalues\b.*\bget\b|\bvalues\s*(\(\s*\))?\.get\b")),
       ("curl", re.compile(r"\bcurl\s")),
       ("urllib", re.compile(r"\burllib\b")),
       ("requests", re.compile(r"\brequests\.|^\s*(?:import requests|from requests\b)"))]
MODEL_ID = re.compile(r"claude-(?:haiku|sonnet|opus|fable)-[0-9]")   # (d) no literal model id outside the table
MODEL_TABLE_FILES = ("model.lib.sh", "model_ids.py")
# a literal passed as a model flag/assignment (any future family name): --model X, "--model", "X", model="X", MODEL=X.
# A variable/expansion ($MODEL_ID_*, model_id(tier), run_model's tier) never matches: a value must START with a letter/digit.
MODEL_LIT = [re.compile(p) for p in (
    r"""--model(?:=|[ \t]+)["']?([A-Za-z0-9][\w.\-]*)""",
    r"""["']--model["']\s*,\s*["']([\w.\-]+)["']""",
    r"""\b[Mm][Oo][Dd][Ee][Ll]\s*=\s*["']([\w.\-]+)["']""",
    r"""^\s*(?:export\s+)?MODEL\s*=\s*([A-Za-z0-9][\w.\-]*)\s*(?:#.*)?$""")]
SRC = re.compile(r"""^\s*(?:source|\.)\s+["']?([^"'\s;&|]+)""")
INV = re.compile(r"""\b(?:python3?|bash|sh)\s+["']?([^"'\s;&|]+\.(?:py|sh))""")
seen, todo = set(), [os.path.realpath(e) for e in scripts if "$" not in e]
while todo:
    f = todo.pop()
    if f in seen or not os.path.isfile(f) or not (under(f, code) or under(f, desk)):
        continue
    seen.add(f)
    try: lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
    except OSError: continue
    scan = f not in allow
    for i, ln in enumerate(lines, 1):
        if ln.lstrip().startswith("#"): continue
        if os.path.basename(f) not in MODEL_TABLE_FILES and (MODEL_ID.search(ln) or any(r.search(ln) for r in MODEL_LIT)):
            rel = os.path.relpath(f, code) if under(f, code) else f
            reasons.append(f"hard-coded model id at {rel}:{i} \u2014 name a tier (small|medium|large); ids live only in system/tools/model.lib.sh")
        if scan:
            for kind, rx in RAW:
                if rx.search(ln):
                    rel = os.path.relpath(f, code) if under(f, code) else f
                    reasons.append(f"raw {kind} call at {rel}:{i} — go through the shared fetch"); break
        for rx in (SRC, INV):
            for mm in rx.finditer(ln):
                p = expand(mm.group(1))
                if "$" not in p and not p.startswith("-"):
                    todo.append(os.path.realpath(p if os.path.isabs(p) else os.path.join(os.path.dirname(f), p)))
if reasons:
    print("\n".join(dict.fromkeys(reasons))); sys.exit(1)
print("PASS")
DOORPY
}

# Look a row up by name in a manifest and run the door on it (the --check-row entry point).
door_check_named() {   # name manifest
  local want="$1" mf="$2" line n en iv oc ck md bg sr cm found=0 in=0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    if [ "$line" = '```jobs' ]; then in=1; continue; fi
    if [ "$in" -eq 1 ] && [ "$line" = '```' ]; then in=0; continue; fi
    [ "$in" -eq 1 ] || continue
    case "$line" in ''|\#*) continue;; esac
    IFS='|' read -r n en iv oc ck md bg sr cm <<< "$line"
    [ "$(trim "$n")" = "$want" ] || continue
    found=1
    door_check_row "$(trim "$n")" "$(trim "$en")" "$(trim "$oc")" "$(trim "$ck")" "$(trim "$md")" "$(trim "$bg")" "$(trim "$sr")" "$(trim "$cm")"
    return $?
  done < "$mf"
  [ "$found" -eq 1 ] || { echo "no such row: $want" >&2; return 2; }
}
if [ "${1:-}" = "--check-row" ]; then
  [ -n "${2:-}" ] || { echo "usage: install-schedulers.sh --check-row <name>" >&2; exit 2; }
  door_check_named "$2" "${LIFEHACK_JOBS_FILE:-$MANIFEST}"
  exit $?
fi
DOOR_REFUSED=0

# ── 1) OS detection — THE SAME RULE this product's own INSTALL.md states to a human installer
# (Step 1: "Darwin means a Mac. Linux means Linux. Anything else, treat it as Windows.") — one rule,
# stated once, followed by both the human-facing doc and this script. ──────────────────────────────
_UNAME="$(uname -s 2>/dev/null || true)"
case "$_UNAME" in
  Darwin) OS="mac" ;;
  Linux)  OS="linux" ;;
  *)      OS="windows" ;;   # includes MSYS/MINGW/CYGWIN (Git Bash) and a bare uname failure
esac
# TEST-ONLY override — there is no Windows box in this build environment, so the Windows branch is
# verified by forcing this rather than by claiming it works unread. Never set outside a test.
OS="${LIFEHACK_TEST_OS_OVERRIDE:-$OS}"

# ── 1b) macOS — one launchd LaunchAgent per enabled row of the ```jobs``` block ─────────────────
# (self-monitoring plan §B.1, 2026-10-27.) SUPERSEDES the cron-on-Mac decision in the header above
# for macOS ONLY: Linux keeps the crontab path and Windows keeps schtasks, both untouched below.
# Each enabled job gets ~/Library/LaunchAgents/ai.lifehack.<job>.plist whose launch line is
#   /bin/bash -c 'exec /bin/bash "$(cat "$HOME/.config/lifehack/code-root")/system/tools/job-run.sh" <job> --if-overdue'
# so no plist carries a code path (the pointer file does). $HOME stays literal for bash to expand.
# Schedule: StartCalendarInterval derived from the interval; only intervals that are a whole number
# of hours dividing 86400 are supported — anything else FAILS LOUDLY, nothing is touched.
# TEST SEAMS: LAUNCHAGENTS_DIR (default ~/Library/LaunchAgents); LIFEHACK_INSTALL_DRY_RUN=1 writes
# the plists there but skips every launchctl call (and the state-dir mkdir), printing what it would run.
# Without --install and without LIFEHACK_INSTALL_DRY_RUN=1 this only prints the plan.
_xml_escape() {
  local s="$1"
  s="${s//&/&amp;}"; s="${s//</&lt;}"; s="${s//>/&gt;}"; s="${s//\"/&quot;}"
  printf '%s' "$s"
}

install_mac_launchd() {
  local la_dir="${LAUNCHAGENTS_DIR:-$HOME/Library/LaunchAgents}"
  local dry=0 apply=0
  [ "${LIFEHACK_INSTALL_DRY_RUN:-}" = "1" ] && dry=1
  if [ "$dry" -eq 1 ] || [ "$MODE" = "--install" ]; then apply=1; fi
  local uid; uid="$(id -u)"
  local state_root="$HOME/.config/lifehack/state/jobs"

  # --- parse the ```jobs``` block: name | enabled | interval | outcome | check | model | budget | source | command ---
  local -a names=() ivals=()
  local in=0 fence_seen=0 line name enabled interval cmd reasons
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    if [ "$line" = '```jobs' ]; then in=1; fence_seen=1; continue; fi
    if [ "$in" -eq 1 ] && [ "$line" = '```' ]; then in=0; continue; fi
    [ "$in" -eq 1 ] || continue
    case "$line" in ''|\#*) continue;; esac
    IFS='|' read -r name enabled interval _outcome _check _model _budget _source cmd <<< "$line"
    name="$(trim "$name")"; enabled="$(trim "$enabled")"; interval="$(trim "$interval")"
    [ -n "$name" ] || continue
    [ "$enabled" = "yes" ] || continue
    # THE DOOR (5.2): a row that fails it is refused -- reason printed, no plist, non-zero exit at the end.
    if ! reasons="$(door_check_row "$name" "$enabled" "$(trim "$_outcome")" "$(trim "$_check")" "$(trim "$_model")" "$(trim "$_budget")" "$(trim "$_source")" "$(trim "$cmd")")"; then
      while IFS= read -r _r; do echo "[install-schedulers] REFUSED $name: $_r" >&2; done <<< "$reasons"
      DOOR_REFUSED=$((DOOR_REFUSED + 1)); continue
    fi
    names+=("$name"); ivals+=("$interval")
  done < "$MANIFEST"
  if [ "$fence_seen" -eq 0 ]; then
    echo "[install-schedulers] FATAL: the \`\`\`jobs\`\`\` fence was never found in $MANIFEST (CRLF or edited marker?). Nothing was installed." >&2
    exit 2
  fi

  # --- validate every enabled row BEFORE touching launchd ---
  local i bad=0
  for i in "${!names[@]}"; do
    name="${names[$i]}"; interval="${ivals[$i]}"
    if ! [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
      echo "[install-schedulers] FATAL: job name '$name' is not a safe launchd label fragment." >&2; bad=1; continue
    fi
    if ! [[ "$interval" =~ ^[0-9]+$ ]] || [ "$interval" -lt 3600 ] || [ $((86400 % interval)) -ne 0 ] || [ $((interval % 3600)) -ne 0 ]; then
      echo "[install-schedulers] FATAL: job '$name' has interval '$interval'; launchd StartCalendarInterval is only generated for whole-hour intervals that divide 86400 (3600, 7200, 10800, 14400, 21600, 28800, 43200, 86400). Set the row off or extend install_mac_launchd()." >&2
      bad=1
    fi
  done
  [ "$bad" -eq 0 ] || { echo "[install-schedulers] nothing was changed." >&2; exit 1; }

  echo "[install-schedulers] macOS launchd: ${#names[@]} enabled job(s); agents dir: $la_dir"
  if [ "$apply" -eq 0 ]; then
    for i in "${!names[@]}"; do echo "  WOULD WRITE $la_dir/ai.lifehack.${names[$i]}.plist (every ${ivals[$i]}s)"; done
    echo "[install-schedulers] plan only (re-run with --install to apply)."
    [ "$DOOR_REFUSED" -eq 0 ] || echo "[install-schedulers] $DOOR_REFUSED enabled row(s) REFUSED by the door." >&2
    return 0
  fi

  _run() { if [ "$dry" -eq 1 ]; then echo "  DRY-RUN would run: $*"; else "$@"; fi; }

  # --- idempotent: bootout every loaded ai.lifehack.* label, delete stale plists ---
  local label
  if [ "$dry" -eq 1 ]; then
    echo "  DRY-RUN would run: launchctl list | (bootout each loaded ai.lifehack.* label)"
  else
    while IFS= read -r label; do
      [ -n "$label" ] || continue
      launchctl bootout "gui/$uid/$label" >/dev/null 2>&1 || true
    done < <(launchctl list 2>/dev/null | awk '{print $3}' | grep '^ai\.lifehack\.' || true)
  fi
  mkdir -p "$la_dir"
  rm -f "$la_dir"/ai.lifehack.*.plist

  # --- write, lint, bootstrap ---
  local plist hours h launch launch_x cal err
  for i in "${!names[@]}"; do
    name="${names[$i]}"; interval="${ivals[$i]}"
    label="ai.lifehack.$name"
    plist="$la_dir/$label.plist"
    err="$state_root/$name/launch.err"
    [ "$dry" -eq 1 ] || mkdir -p "$state_root/$name"
    launch="exec /bin/bash \"\$(cat \"\$HOME/.config/lifehack/code-root\")/system/tools/job-run.sh\" $name --if-overdue"
    launch_x="$(_xml_escape "$launch")"
    cal=""
    for ((h=0; h<24; h+=interval/3600)); do
      cal+="    <dict><key>Hour</key><integer>$h</integer><key>Minute</key><integer>0</integer></dict>"$'\n'
    done
    cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>$launch_x</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
${cal}  </array>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>$(_xml_escape "$err")</string>
</dict>
</plist>
PLIST
    if ! plutil -lint "$plist" >/dev/null; then
      echo "[install-schedulers] FATAL: plutil -lint rejected $plist" >&2; exit 1
    fi
    echo "[install-schedulers] wrote $plist"
    _run launchctl bootstrap "gui/$uid" "$plist"
  done
  echo "[install-schedulers] REGISTRATION is not proof it fires: check ~/.config/lifehack/state/jobs/<job>/last-success after the first scheduled run."
  [ "$DOOR_REFUSED" -eq 0 ] || echo "[install-schedulers] $DOOR_REFUSED enabled row(s) REFUSED by the door -- no plist written for them." >&2
}

if [ "$OS" = "mac" ]; then
  install_mac_launchd
  _rc=$?
  [ "$DOOR_REFUSED" -eq 0 ] || _rc=1   # any refused enabled row = non-zero at the end
  exit $_rc
fi

# ── 2) Parse the ```crontab``` block → [(name, schedule, command)] ─────────────────────────────
declare -a JOB_NAMES=() JOB_SCHEDS=() JOB_CMDS=()
in=0
fence_seen=0   # did the ```crontab``` fence EVER match, this run? (ABSENT-SUBJECT-RULE — see below)
while IFS= read -r line || [ -n "$line" ]; do
  # Strip a trailing \r on EVERY line, not just the fence line: Git for Windows' default
  # core.autocrlf=true checks this .md file out with CRLF endings, and the row-parsing below
  # (`[ "$line" = '```crontab' ]`, the `case` blank/comment test, the `IFS='|' read`) is exact-string
  # matching throughout — a lone \r on the fence line alone would still leave every DATA row carrying
  # one on its trailing field. Measured: before this strip, a CRLF manifest produced 0 rows here.
  line="${line%$'\r'}"
  if [ "$line" = '```crontab' ]; then in=1; fence_seen=1; continue; fi
  if [ "$in" -eq 1 ] && [ "$line" = '```' ]; then in=0; continue; fi
  [ "$in" -eq 1 ] || continue
  case "$line" in ''|\#*) continue;; esac
  IFS='|' read -r name sched cmd <<< "$line"
  name="$(trim "$name")"; sched="$(trim "$sched")"; cmd="$(trim "$cmd")"
  [ -n "$name" ] || continue
  # ⚠ LITERAL TEXT SUBSTITUTION, not shell expansion. These crontab-block rows run OUTSIDE this
  # process (as independent OS-scheduled entries) and can never inherit an `export` from here — a
  # crontab line of the shape `VAR=val bash "$VAR/x"` does NOT do what it looks like it does: the
  # outer shell expands "$VAR" in the argument word BEFORE the same-line prefix assignment takes
  # effect, so it silently resolves to empty (measured: `LIFEHACK_CODE_ROOT=/x bash
  # "$LIFEHACK_CODE_ROOT/pulse.sh"` fails with "bash: /pulse.sh: No such file or directory" — the
  # leading slash is the tell). pulse.sh's OWN jobs (the ```jobs``` block, dispatched at runtime via
  # a plain `export` as a separate statement, then a separate `bash -c "$cmd"`) don't have this
  # problem — only these OS-level rows do. Fixed here, once, by baking in the real resolved path.
  cmd="${cmd//\$LIFEHACK_CODE_ROOT/$CODE_ROOT}"
  JOB_NAMES+=("$name"); JOB_SCHEDS+=("$sched"); JOB_CMDS+=("$cmd")
done < "$MANIFEST"

# ⛔ ABSENT-SUBJECT-RULE (system/build-rules-index.md): "the block parsed and is genuinely empty"
# and "the block was never found at all" are DIFFERENT claims and must never share an exit code.
# The latter is exactly the CRLF failure mode this file exists to catch (a line-ending mismatch
# breaks the fence's exact-string match, so `in` never goes to 1, JOB_NAMES stays empty, and the
# code below used to report "nothing to install" — success — for a manifest that was never actually
# read). fence_seen distinguishes them: it is set ONLY inside the fence-open branch above, so it is
# 0 here iff the ```crontab``` fence line never matched a single line of $MANIFEST.
if [ "$fence_seen" -eq 0 ]; then
  echo "[install-schedulers] FATAL: the \`\`\`crontab\`\`\` fence was never found in $MANIFEST." >&2
  echo "  This is NOT the same as an empty block — the manifest could not be evaluated at all," >&2
  echo "  so nothing was installed. Likely causes: the file has CRLF line endings (check with" >&2
  echo "  'file $MANIFEST'; .gitattributes should prevent this, but a stale checkout predating" >&2
  echo "  that fix can still carry one), or the fence marker itself was edited/typo'd." >&2
  exit 2
fi
if [ "${#JOB_NAMES[@]}" -eq 0 ]; then
  echo "[install-schedulers] no rows in the \`\`\`crontab\`\`\` block of $MANIFEST — nothing to install." >&2
  exit 0
fi

echo "[install-schedulers] detected OS: $_UNAME -> $OS"
echo "[install-schedulers] ${#JOB_NAMES[@]} scheduled entr$([ "${#JOB_NAMES[@]}" -eq 1 ] && echo y || echo ies) in the manifest."

# ── 3a) Mac / Linux — crontab ───────────────────────────────────────────────────────────────────
install_mac_linux() {
  if ! command -v crontab >/dev/null 2>&1; then
    # LANDMINE the donor script never checked: a bare `crontab -` on a system with no cron binary
    # exits non-zero but the donor didn't look — it would have reported success anyway. Refuse
    # loudly instead of guessing this ever works.
    echo "[install-schedulers] FATAL: no 'crontab' binary found on PATH. This machine (uname=$_UNAME)" >&2
    echo "  claims to be Mac/Linux but has no cron. Nothing was installed. If this is a minimal" >&2
    echo "  container/server image, install a cron package (e.g. 'cronie' or 'cron') and re-run." >&2
    exit 1
  fi

  local region_body=""
  local i
  for i in "${!JOB_NAMES[@]}"; do
    region_body+="${JOB_SCHEDS[$i]} ${JOB_CMDS[$i]}"$'\n'
  done
  local region="$BEGIN"$'\n'"$region_body$END"

  local existing stripped
  existing="$(crontab -l 2>/dev/null || true)"
  # strip the old managed region (exact-line awk match — robust against the marker's special chars)
  stripped="$(printf '%s\n' "$existing" | awk -v b="$BEGIN" -v e="$END" '
    $0==b {skip=1; next} $0==e {skip=0; next} !skip {print}')"
  # absorb any pre-existing standalone lines for the runners THIS installer owns, so re-running
  # after a manual edit doesn't duplicate them.
  local rn
  for rn in pulse.sh health-deadman-check.sh; do
    stripped="$(printf '%s\n' "$stripped" | grep -vF "$rn" || true)"
  done
  stripped="$(printf '%s\n' "$stripped" | sed '/^[[:space:]]*$/d')"   # drop blank lines
  local newcron="$stripped"$'\n'"$region"

  if [ "$MODE" = "--install" ]; then
    mkdir -p "$HOME/.config/lifehack/crontab-backups"
    local bk="$HOME/.config/lifehack/crontab-backups/crontab.$(date +%Y%m%d-%H%M%S).bak"
    printf '%s\n' "$existing" > "$bk"
    printf '%s\n' "$newcron" | crontab -
    echo "[install-schedulers] CRONTAB installed (backup: $bk)."
    echo "[install-schedulers] REGISTRATION check (proves the entry exists, NOT that it will fire): crontab -l"
    echo "[install-schedulers] REAL verification (proves it actually RAN — do this in ~10 min): "
    echo "  bash system/tools/pulse.sh --status   # shows DUE/waiting per job, no side effects"
    echo "  then check a tile's own last_run, e.g.: cat <your notes folder>/state/status/sentinel.json"
    echo "  A fresh last_run there was written by that job's REAL work — a registered-but-silently-"
    echo "  denied cron entry (the A38 failure class) would leave that timestamp stuck, not fake-fresh."
  else
    echo "[install-schedulers] CRONTAB dry-run (re-run with --install to apply):"
    echo "----------------------------------------------------------------------"
    printf '%s\n' "$newcron"
    echo "----------------------------------------------------------------------"
  fi
}

# ── 3b) Windows — Task Scheduler via Git Bash ───────────────────────────────────────────────────
# schtasks.exe is a native Windows binary and is reachable from Git Bash's PATH (it lives in
# C:\Windows\System32, which Windows always puts on PATH, and Git Bash inherits the Windows PATH).
# The task's own ACTION must be an absolute WINDOWS-style path — Task Scheduler does not understand
# POSIX paths like /usr/bin/bash or /c/Users/<name>/... — so both bash.exe and pulse.sh's own path are
# converted with `cygpath -w`, which Git for Windows ships specifically for this.
_win_path() { cygpath -w "$1" 2>/dev/null; }   # POSIX path -> "C:\..." ; empty on failure

_resolve_bash_exe() {
  local cand
  cand="$(command -v bash 2>/dev/null || true)"
  if [ -n "$cand" ]; then
    _win_path "$cand" && return 0
  fi
  # Known default Git-for-Windows install locations, in case PATH resolution above failed for some
  # reason (e.g. invoked from a non-Git-Bash shell that still has bash.exe on disk).
  local guess
  for guess in "/c/Program Files/Git/bin/bash.exe" "/c/Program Files (x86)/Git/bin/bash.exe"; do
    if [ -f "$guess" ]; then _win_path "$guess"; return 0; fi
  done
  return 1
}

# A DELIBERATELY SMALL cron-schedule -> schtasks translator: it understands exactly the two shapes
# this manifest actually uses (`*/N * * * *` = every N minutes; `M * * * *` = once an hour, minute
# M) and refuses anything else rather than guessing a wrong schedule. Prints schtasks /SC + /MO (+
# /ST for the hourly form) args on stdout, or nothing + returns 1 if the shape is unrecognized.
# Escapes a value for embedding inside a PowerShell SINGLE-quoted string literal.
# PowerShell single-quoted strings are verbatim except for one rule: a literal `'` inside
# one must be doubled (`''`) or it closes the string early -- exactly what happens, unescaped,
# to a Windows path containing an apostrophe (e.g. `C:\<user-dir>\<name-with-quote>\...`, a real username
# shape) or a `cmd` string that happens to contain one. Every value interpolated into the
# single-quoted ArgumentList/FilePath literals below MUST be passed through this first.
_ps_squote() {
  local sq="'"
  printf '%s' "${1//$sq/$sq$sq}"
}

_cron_to_schtasks() {
  local sched="$1" minute hour
  minute="$(echo "$sched" | awk '{print $1}')"
  hour="$(echo "$sched" | awk '{print $2}')"
  if [[ "$minute" =~ ^\*/([0-9]+)$ ]] && [ "$hour" = "*" ]; then
    echo "/SC MINUTE /MO ${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "$minute" =~ ^[0-9]+$ ]] && [ "$hour" = "*" ]; then
    printf '/SC HOURLY /MO 1 /ST 00:%02d:00\n' "$minute"
    return 0
  fi
  return 1
}

install_windows() {
  local bash_win
  if ! bash_win="$(_resolve_bash_exe)" || [ -z "$bash_win" ]; then
    echo "[install-schedulers] FATAL: could not find Git Bash's bash.exe (tried PATH + the two" >&2
    echo "  standard Git-for-Windows install locations). Task Scheduler needs an absolute .exe" >&2
    echo "  path — it cannot run a POSIX script directly. Install Git for Windows (INSTALL.md" >&2
    echo "  Step 2 covers this), then re-run." >&2
    exit 1
  fi
  local pulse_win
  pulse_win="$(_win_path "$PULSE_SH")"
  if [ -z "$pulse_win" ]; then
    echo "[install-schedulers] FATAL: could not resolve a Windows path for $PULSE_SH (cygpath failed)." >&2
    exit 1
  fi
  local bash_win_ps
  bash_win_ps="$(_ps_squote "$bash_win")"

  local i name sched cmd schtasks_args task_name log_win
  for i in "${!JOB_NAMES[@]}"; do
    name="${JOB_NAMES[$i]}"; sched="${JOB_SCHEDS[$i]}"; cmd="${JOB_CMDS[$i]}"
    task_name="Lifehack-$(echo "$name" | sed -E 's/[^A-Za-z0-9]+/-/g')"
    if ! schtasks_args="$(_cron_to_schtasks "$sched")"; then
      echo "[install-schedulers] SKIP '$name' — schedule '$sched' isn't one of the two shapes this" >&2
      echo "  installer understands (*/N * * * * or M * * * *). Add it to Windows Task Scheduler" >&2
      echo "  by hand, or extend _cron_to_schtasks() in this script." >&2
      continue
    fi
    # ⚠ Every job's OWN command (from the manifest) is a *nix-shaped Bash command string
    # (e.g. `bash "<path>/system-health-run.sh"`) — it runs UNCHANGED, inside the bash.exe process
    # Task Scheduler launches, exactly the same string pulse.sh's own `bash -c "$cmd"` would run on
    # Mac/Linux. Only the ENTRY POINT (what Task Scheduler itself invokes) differs by OS: here it is
    # `bash.exe "<pulse.sh-win-path>"`, not the manifest command directly — pulse.sh is always the
    # thing the scheduler calls; pulse.sh is what parses the ```jobs``` block and runs each job's
    # own command in turn. This crontab-block row IS pulse.sh's own entry for the `pulse` name (and
    # health-deadman's dedicated entry) — see pulse-config.md.
    #
    # ⚠ WINDOW HIDING: bash.exe is a console-subsystem binary, so if Task Scheduler ran it directly
    # a visible console window would flash open on EVERY fire — every 5 minutes for the pulse job.
    # We keep the task INTERACTIVE (no /RU — see the block comment above _resolve_bash_exe's callers
    # for why: a non-interactive S4U task only sees local resources and risks not seeing a
    # Google-Drive-synced folder) and instead route through powershell.exe, which ships on every
    # Windows 10/11 machine and needs no admin:
    #   powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command
    #     "$p = Start-Process -FilePath '<bash.exe>' -ArgumentList <args> -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode"
    # -WindowStyle Hidden is set on BOTH the outer powershell.exe and the inner Start-Process, since
    # each is its own console-window-capable process. -Wait (+ -PassThru, + relaying $p.ExitCode) is
    # deliberate, not default Start-Process behavior: without it, Start-Process would return
    # immediately after LAUNCHING bash.exe, so the powershell.exe task instance would exit almost
    # instantly while bash.exe kept running detached — defeating Task Scheduler's own
    # already-running-instance overlap protection on the 5-minute pulse cadence (a job that overruns
    # 5 minutes would get a second overlapping copy started on top of it), and silently discarding
    # the job's real exit code (Task Scheduler would only ever see powershell.exe's own 0). -Wait
    # keeps the task's process lifetime equal to bash.exe's, matching the pre-existing direct-invoke
    # behavior on both counts.
    # ⚠ KNOWN LIMITATION: `-WindowStyle Hidden` on the OUTER powershell.exe is documented by
    # Microsoft to still flash a console briefly on some Windows builds before the window is hidden.
    # This is a MITIGATION, not a guaranteed zero-flash fix — do not "fix" a residual flash by
    # swapping this for a VBScript/wscript.exe shim: that path was deliberately rejected (VBScript is
    # in Microsoft's own deprecation pipeline and matches Defender ASR rule
    # d3e037e1-3eb8-44c8-a917-57927947596d).
    #
    # Quoting: the paths in ArgumentList/FilePath are wrapped in PowerShell SINGLE quotes
    # deliberately, not double quotes — a Windows path can contain spaces (`C:\<user-dir>\<name-with-quote> Smith\...`)
    # and single-quoted PowerShell strings are verbatim (no backslash- or $-interpolation to worry
    # about), and critically it means the whole -Command payload contains NO embedded double-quote
    # characters, so it survives as a single Win32 argv token with no backslash-doubling needed when
    # Task Scheduler re-parses the stored /TR command line at fire time.
    # A single-quoted PowerShell string is verbatim EXCEPT for the closing quote character itself --
    # a path or cmd string carrying a literal `'` (e.g. `C:\<user-dir>\<name-with-quote>\...`) would otherwise
    # terminate the literal early and corrupt the parsed command. _ps_squote() above doubles every
    # embedded `'` before interpolation, which is PowerShell single-quote escaping's own rule.
    local ps_body ps_cmd action
    if [ "$name" = "pulse" ]; then
      ps_body="-ArgumentList '$(_ps_squote "$pulse_win")'"
    else
      # health-deadman (and any future non-Pulse crontab row) runs its OWN command directly, not
      # through pulse.sh — same distinction the manifest draws between the ```jobs``` block (Pulse-
      # dispatched) and the ```crontab``` block (OS-dispatched). bash.exe needs two args here
      # (`-c` and the command string), so ArgumentList takes a comma-separated PowerShell array.
      ps_body="-ArgumentList '-c','$(_ps_squote "$cmd")'"
    fi
    ps_cmd="\$p = Start-Process -FilePath '$bash_win_ps' $ps_body -WindowStyle Hidden -Wait -PassThru; exit \$p.ExitCode"
    action="powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command \"$ps_cmd\""
    if [ "$MODE" = "--install" ]; then
      # shellcheck disable=SC2086
      schtasks /Create $schtasks_args /TN "$task_name" /TR "$action" /F
      echo "[install-schedulers] installed Windows Task Scheduler entry '$task_name' ($schtasks_args)."
    else
      echo "[install-schedulers] WOULD RUN: schtasks /Create $schtasks_args /TN \"$task_name\" /TR $action /F"
    fi
  done
  if [ "$MODE" != "--install" ]; then
    echo "[install-schedulers] Windows dry-run (re-run with --install to apply)."
  else
    echo "[install-schedulers] REGISTRATION check (proves the task exists, NOT that it will fire): schtasks /Query /TN Lifehack-Pulse"
    echo "[install-schedulers] REAL verification (proves it actually RAN — do this in ~10 min): "
    echo "  bash pulse.sh --status   # from Git Bash, in this repo's system/tools/"
    echo "  then check a tile's own last_run under your notes folder's state/status/ — see the"
    echo "  Mac/Linux branch's identical note above for why registration alone is not proof."
  fi
}

case "$OS" in
  mac)       install_mac_launchd ;;   # normally handled (and exited) earlier, in section 1b
  linux)     install_mac_linux ;;
  windows)   install_windows ;;
esac
