#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: The scratchpad AUTO-CAPTURE failed live (2026-07-14): capture was ignorable
#      + invisible. This Stop-gate makes capture UN-IGNORABLE + the receipt VISIBLE.
#      F1.5.1 (2026-07-15): fixed to gate on the project BRIEF (pm_flag), not just
#      scratch_flag. ALWAYS-SHOW (2026-07-15): every time capture comes due it
#      now shows a receipt of WHAT was captured — not only when it catches a miss —
#      so "whatever it runs, I see it ran AND what it wrote."
#      2026-08-14: the pad write used to happen IN the main window, then get reprinted
#      into the reply as a trust signal — three copies of the same text (the model's
#      output, the file write, the reprint) inside the window the gate exists to
#      protect. It now hands the write to a SONNET sub-agent (deciding what matters is
#      judgment, a lossy-compression call the caller can't cheaply check — the sonnet
#      floor) that returns one of exactly three bounded verdicts and never the content:
#      `WROTE <n> lines` · `NOTHING-TO-CAPTURE` · `FAILED <why>`. FAILED is the
#      no-outcome member and must never be reported as NOTHING-TO-CAPTURE — a dead
#      sub-agent and an empty session are different facts. See the comment block
#      further down for why the fired message itself stays terse.
# GUARDS: Stop-event gate. Resolves the active pad by precedence: (1) scratch_flag
#      armed -> its scratch_path (override); (2) ELSE pm_flag -> the brief's
#      `## SCRATCHPAD` section (default); (3) else dormant. When capture is DUE
#      (token bucket +100k past the last checkpoint) it BOUNCES once: it mechanically
#      diffs the pad vs the last checkpoint (a sidecar file) and hands the model the
#      exact ADDED lines plus the delegation instruction. Loop-safe (stop_hook_active
#      -> exit 0). Never calls a model itself — the sub-agent it instructs does.
# REDIRECT: N/A (Stop gate). State ~/.claude/run/scratch-capture/cap-sess-<id>.state
#      (bucket) + .pad sidecar (last-checkpoint section). Off: scratch_flag.sh clear /
#      pm_flag.sh clear. Resolvers: scratch_flag.sh, pm_flag.sh.
# SIGNPOST: Rule + design = plan good-let-s-plan-this-bright-parnas.md + project-system
#      brief. Receipt = ONE line, printed by the main window after the sub-agent
#      returns (a hook cannot write the reply pane); the ADDED lines are computed
#      MECHANICALLY here (proof-not-ask). Token signal reuses scratch_sweep_nudge.sh.
#      Change the RULE in the plan/brief first.
# FAIL_POSTURE: degrade-safe -- any error -> exit 0 (allow stop, never wedge a turn).
# UPDATED: 2026-08-14 (ported from claudeops-config commits dc9538a + f3db2d0 — the pad
#      write moved to a sonnet sub-agent, bounded to three verdicts, and the fired
#      message trimmed to the instruction only; the reasoning moved into a comment)
# PORTED: 2026-08-13 from claudeops-config — the scratch_flag.sh / pm_flag.sh calls below were
#      literal `~/claudeops-config/...` paths; they now resolve from this hook's own location.
#      The state paths ($HOME/.claude/run/scratch-capture etc.) are the harness's own per-user
#      global state, not operator-specific, so they are left as-is, matching the existing baseline.
# ─────────────────────────────────────────────────────────────────────────────
set +e
INPUT="$(cat 2>/dev/null)"
CAPTURE_EVERY=100000

read -r SID ACTIVE TP < <(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d=json.load(sys.stdin)
    print(d.get('session_id',''), str(d.get('stop_hook_active',False)), d.get('transcript_path',''))
except Exception:
    print('','False','')
" 2>/dev/null)

[ "$ACTIVE" = "True" ] && exit 0    # loop safety: already bounced this turn
[ -n "$SID" ] || exit 0

# Resolve THIS repo's root from the hook's own location — never a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"

# ── resolve the active pad by precedence (scratch_flag override -> else brief) ──
ST="$(CLAUDE_CODE_SESSION_ID="$SID" bash "$_REPO/system/hooks/scratch_flag.sh" status 2>/dev/null)"
if [ "$ST" = "armed" ]; then
  FLAG="$HOME/.claude/run/scratch/scratch-sess-$SID.flag"
  PAD="$(grep '^scratch_path=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
else
  PAD="$(CLAUDE_CODE_SESSION_ID="$SID" bash "$_REPO/system/hooks/pm_flag.sh" status 2>/dev/null)"
  [ "$PAD" = "none" ] && PAD=""
fi
[ -n "$PAD" ] && [ -f "$PAD" ] || exit 0

# ── token count = LAST assistant usage block in the transcript ────────────────
TOK="$(printf '%s' "$INPUT" | python3 -c "
import sys,json,os
try: d=json.load(sys.stdin)
except: print(''); sys.exit()
tp=d.get('transcript_path','')
if not tp or not os.path.exists(tp): print(''); sys.exit()
last=None
try:
    with open(tp) as f:
        for line in f:
            try: o=json.loads(line)
            except: continue
            m=o.get('message',o); u=m.get('usage')
            if m.get('role')=='assistant' and isinstance(u,dict): last=u
except: print(''); sys.exit()
if not last: print(''); sys.exit()
print((last.get('input_tokens',0) or 0)+(last.get('cache_creation_input_tokens',0) or 0)+(last.get('cache_read_input_tokens',0) or 0))
" 2>/dev/null)"
case "$TOK" in ''|*[!0-9]*) exit 0;; esac
BUCKET=$(( TOK / CAPTURE_EVERY )); K=$(( TOK / 1000 ))

STATEDIR="$HOME/.claude/run/scratch-capture"; mkdir -p "$STATEDIR" 2>/dev/null
SFILE="$STATEDIR/cap-sess-$SID.state"
SIDECAR="$STATEDIR/cap-sess-$SID.pad"
LASTBUCKET="$(grep '^bucket=' "$SFILE" 2>/dev/null | cut -d= -f2-)"; [ -n "$LASTBUCKET" ] || LASTBUCKET=""

# ── extract the current SCRATCHPAD section (fallback: whole file), write it out ─
CURSEC_FILE="$(mktemp)"
python3 -c "
import sys,re
p='$PAD'
try: t=open(p,encoding='utf-8',errors='replace').read()
except: sys.exit()
lines=t.splitlines(); start=None
for i,ln in enumerate(lines):
    if re.match(r'^##+\s', ln) and 'SCRATCHPAD' in ln.upper(): start=i; break
if start is None: sec=lines
else:
    end=len(lines)
    for j in range(start+1,len(lines)):
        if re.match(r'^##+\s', lines[j]): end=j; break
    sec=lines[start:end]
open('$CURSEC_FILE','w',encoding='utf-8').write('\n'.join(sec)+'\n')
" 2>/dev/null

# first sight this session: seed the watermark + sidecar, never bounce on turn one
if [ -z "$LASTBUCKET" ]; then
  echo "bucket=$BUCKET" > "$SFILE" 2>/dev/null
  cp "$CURSEC_FILE" "$SIDECAR" 2>/dev/null
  rm -f "$CURSEC_FILE"; exit 0
fi

# not due yet -> silent (common path)
if [ "$BUCKET" -le "$LASTBUCKET" ]; then rm -f "$CURSEC_FILE"; exit 0; fi

# DUE -> compute the ADDED lines (current section minus last checkpoint), then bounce
ADDED="$(python3 -c "
import sys
cur=open('$CURSEC_FILE',encoding='utf-8',errors='replace').read().splitlines()
try: old=set(open('$SIDECAR',encoding='utf-8',errors='replace').read().splitlines())
except: old=set()
added=[l for l in cur if l.strip() and l not in old and not l.strip().startswith('##')]
shown=added[:20]
extra=len(added)-len(shown)
out='\n'.join(shown)
if extra>0: out+='\n… (+%d more lines)'%extra
print(out)
" 2>/dev/null)"

# advance the watermark (bucket + sidecar) so this checkpoint is banked
echo "bucket=$BUCKET" > "$SFILE" 2>/dev/null
cp "$CURSEC_FILE" "$SIDECAR" 2>/dev/null
rm -f "$CURSEC_FILE"

# ─────────────────────────────────────────────────────────────────────────────
# WHY THE MESSAGES BELOW ARE TERSE — read this before you "improve" them.
# Ported 2026-08-14: this gate used to ask the MAIN WINDOW to write the pad itself and then
# reprint the lines back into its reply as a trust signal — three copies of the same text
# (the model's output, the file write, and the reprint) in the exact window the gate exists
# to protect. It was rewritten to delegate the pad write to a sub-agent instead, but the
# first version of THAT rewrite put the full rationale for every rule into the fired
# message: measured at 1,392 chars / ~348 tokens, fired at EVERY checkpoint — the gate had
# become an instance of the injection-creep problem it exists to guard against.
# => RULE: the MESSAGE carries the INSTRUCTION. The SCRIPT carries the REASONING.
#   hook-sop.md §3 rule 3 (anti-wallpaper): a static per-turn inject the model has already
#   seen stops being read. Background prose in a repeated message is paid for on every fire
#   and read on none of them.
#
# THE REASONING, kept here so it is not lost:
#  - SONNET, NOT HAIKU: deciding what matters in a session is judgment, and it is lossy
#    compression the caller cannot cheaply check. Haiku lost this exact bet when /ingest
#    SCAN dropped to haiku and "lost the intuition" (779157c, reverted — see build-sop.md
#    and skill-building-sop.md for the incident).
#  - THE THREE VERDICTS ARE A BOUNDED SET. FAILED is the no-outcome member. A dead
#    sub-agent and an empty session are DIFFERENT FACTS; conflating them loses a session's
#    decisions silently, which is the failure this gate exists to stop.
#  - NO REPRINT: the pad is already on disk; echoing it back is a second copy of saved text
#    in the very window the gate is trying to protect.
#  - THE PAD IS CLEARED only at the approval-gated compaction in /save or /checkin, never here.
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$ADDED" ]; then
  REASON="SCRATCHPAD CHECKPOINT (~${K}k tokens). Already captured since the last checkpoint — verify it covers the recent work; anything missing, spawn ONE sonnet sub-agent to append it. Reply ONE line: '📝 Scratchpad: N lines captured, verified'. ⛔ Do not reprint the lines.

CAPTURED SINCE LAST CHECKPOINT:
${ADDED}"
else
  REASON="SCRATCHPAD CHECKPOINT (~${K}k tokens) — nothing captured since the last checkpoint.

⛔ Do NOT write the pad from this window. Spawn ONE sub-agent, model: sonnet: read this session and append the decisions / observations / loose-threads worth keeping to the '## SCRATCHPAD' section of ${PAD}. Nothing new ⇒ it appends a dated '— (no new decisions) —' line.

It returns EXACTLY ONE of: 'WROTE <n> lines' · 'NOTHING-TO-CAPTURE' · 'FAILED <why>' — never the content, and never FAILED reported as NOTHING-TO-CAPTURE.

Then print ONE line: '📝 Scratchpad: <that verdict>'."
fi
printf '{"decision":"block","reason":%s}\n' "$(printf '%s' "$REASON" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')"
exit 0
