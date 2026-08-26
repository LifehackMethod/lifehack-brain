#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Claude Code plan mode saves plans to ~/.claude/plans/ with RANDOM two-word
#      names, silently — users can't find them, and one intended plan silently
#      fragments into several unnamed files (project-system incident, 2026-07-15;
#      research: records/research/2026-07-15-agent-plan-file-management.md). This
#      makes plan creation VISIBLE + DURABLE without ever blocking plan mode.
# GUARDS: OBSERVE/INJECT only — NEVER blocks (UserPromptSubmit, plain stdout + exit 0).
#      Each turn it diffs ~/.claude/plans/*.md vs a per-session state file; for a plan
#      created or modified since last turn it injects a visible `📋 plan written: …`
#      line. For a NEW plan it ALSO records a durable pointer: into the active project
#      BRIEF's `## SCRATCHPAD` if pm_flag is armed, else into ~/.claude/run/plan-ledger.md.
#      First run seeds silently (pre-existing plans are not "new"). Degrade-safe.
# REDIRECT: N/A (non-blocking). State ~/.claude/run/plan-announce/<key>.state.
#      Test overrides: PLAN_ANNOUNCE_PLANSDIR / PLAN_ANNOUNCE_STATEDIR /
#      PLAN_ANNOUNCE_LEDGER / PLAN_ANNOUNCE_BRIEF. Brief resolved via pm_flag.sh.
# SIGNPOST: Rule + design = plan good-let-s-plan-this-bright-parnas.md (PHASE 1 F1.1/F1.2/F1.3)
#      + the research record above. This is the transparency half of the plan-fork fix
#      (the blocking guard_plan_fork.sh was RETIRED — see its banner). Change the RULE there.
# FAIL_POSTURE: degrade-safe — any error -> exit 0 silent (never wedge a turn).
# UPDATED: 2026-07-15 (new — F1.1/F1.2/F1.3)
# PORTED: 2026-08-13 from claudeops-config — the pm_flag.sh call below was a literal
#      `~/claudeops-config/...` path; it now resolves from this hook's own location. Everything
#      else ($HOME/.claude/plans etc.) is the harness's own per-user global state, not
#      operator-specific, so it is left as $HOME-derived, matching plan_flag.sh's existing baseline.
# ─────────────────────────────────────────────────────────────────────────────
set +e
INPUT="$(cat 2>/dev/null)"

# shasum is NOT guaranteed on PATH (Git Bash on Windows ships without it). Called bare (with
# 2>/dev/null swallowing the error) it silently produces an empty key, collapsing every window's
# state file onto one path. python3 fallback matches hash_key() in guard_cross_project_write.sh.
_hashcwd() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$PWD" | shasum | cut -c1-12
  else
    printf '%s' "$PWD" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12
  fi
}

if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
elif [ -n "$PWD" ]; then KEY="cwd-$(_hashcwd)"
else exit 0; fi

# CLAUDE_CONFIG_DIR moves the whole harness folder; a bare $HOME/.claude then points at an empty
# place and new-plan announcements stop with no error. Same pattern as agent_output.py:59-60.
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PLANSDIR="${PLAN_ANNOUNCE_PLANSDIR:-$CLAUDE_DIR/plans}"
STATEDIR="${PLAN_ANNOUNCE_STATEDIR:-$CLAUDE_DIR/run/plan-announce}"
LEDGER="${PLAN_ANNOUNCE_LEDGER:-$CLAUDE_DIR/run/plan-ledger.md}"
mkdir -p "$STATEDIR" 2>/dev/null
STATE="$STATEDIR/$KEY.state"

# Resolve THIS repo's root from the hook's own location — never a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"

# resolve the active project brief (test override wins; else pm_flag)
if [ -n "$PLAN_ANNOUNCE_BRIEF" ]; then BRIEF="$PLAN_ANNOUNCE_BRIEF"
else BRIEF="$(bash "$_REPO/system/hooks/pm_flag.sh" status 2>/dev/null)"; [ "$BRIEF" = "none" ] && BRIEF=""; fi

python3 - "$PLANSDIR" "$STATE" "$BRIEF" "$LEDGER" <<'PY'
import sys, os, glob, datetime
plansdir, state, brief, ledger = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
cur = {}
for f in glob.glob(os.path.join(plansdir, "*.md")):
    try: cur[f] = int(os.path.getmtime(f))
    except Exception: pass
first = not os.path.exists(state)
old = {}
if not first:
    try:
        for ln in open(state):
            ln = ln.rstrip("\n")
            if "\t" in ln:
                p, m = ln.rsplit("\t", 1)
                try: old[p] = int(m)
                except Exception: pass
    except Exception: pass
try:
    with open(state, "w") as fh:
        for p, m in sorted(cur.items()): fh.write(f"{p}\t{m}\n")
except Exception: pass
if first: sys.exit(0)   # seed silent — pre-existing plans are not "new"
deltas = []
for p, m in cur.items():
    if p not in old: deltas.append(("NEW", p))
    elif old[p] != m: deltas.append(("updated", p))
if not deltas: sys.exit(0)
try: today = datetime.date.today().isoformat()
except Exception: today = ""
for tag, p in sorted(deltas):
    name = os.path.basename(p)
    print(f"📋 plan written: {name} @ {p} ({tag})")     # USER-VISIBLE inject (UserPromptSubmit stdout)
    if tag != "NEW":
        continue
    rec = f"> 📋 plan created: {name} @ {p} ({today})"
    wrote = False
    if brief and os.path.exists(brief):
        try:
            t = open(brief, encoding="utf-8", errors="replace").read().splitlines()
            idx = None
            for i, ln in enumerate(t):
                if ln.lstrip().upper().startswith("## ") and "SCRATCHPAD" in ln.upper():
                    idx = i; break
            if idx is None: t += ["", rec]
            else: t.insert(idx + 1, rec)
            open(brief, "w", encoding="utf-8").write("\n".join(t) + "\n")
            wrote = True
        except Exception: wrote = False
    if not wrote:
        try: open(ledger, "a", encoding="utf-8").write(rec + "\n")
        except Exception: pass
PY
exit 0
