#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: OBSERVE MODE (round 2, brief 2.1). After each turn of a watched skill, ONE medium-tier model call reads that
#      turn against the skill's design and the person's notes, and says what a skill designer would act on. It runs
#      DETACHED (launched by end_of_turn_checks.sh) because a model call takes ~15 s and a Stop hook must not wait.
# GUARDS: none — a background worker. Never blocks, never edits the skill. SOLE WRITER of findings.md. One job per
#      session at a time (the launcher's pid file). Read-only model call (run_model gives it Read only).
# REDIRECT: output goes to <notes folder>/findings.md (everything, timestamped) and to the inbox
#      ~/.claude/run/observe/inbox-<session>.txt (up to 5 SHOW lines, shown at the person's next prompt by
#      observe_ups.sh). On any failure the inbox gets ONE line "reviewer did not run: <reason>".
# SIGNPOST: model tier = `medium` via system/tools/model.lib.sh (never a model id). Switch = observe_flag.sh.
#      Run folder = run_pointer.sh / parts/stage_runner.py. Reviewer prompt: the 1.0 rerun template (build-skill-v2).
# FAIL_POSTURE: degrade-safe — every failure is reported through the inbox and findings.md, never as a crash.
# UPDATED: 2026-11-25 (new, 2.1)
# ─────────────────────────────────────────────────────────────────────────────
#   observe_review.sh <stop-payload-file> <session-id>
# Env: OBSERVE_WAIT (seconds before reading, default 2), OBSERVE_MODEL_TIMEOUT (default 240),
#      OBSERVE_TRANSCRIPT_CAP (chars, default 20000), LIFEHACK_MODEL_STUB (tests only, see model.lib.sh).
set +e
PAYLOAD="$1"; SID="$2"
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUG="$(cd "$_SELF_DIR/../.." && pwd -P)"
case "$SID" in ''|*[!A-Za-z0-9_-]*) exit 0;; esac
export CLAUDE_CODE_SESSION_ID="$SID"
OD="$HOME/.claude/run/observe"; mkdir -p "$OD"
trap 'rm -f "$OD/review-$SID.pid"' EXIT
sleep "${OBSERVE_WAIT:-2}"

FLAGTOOL="$_SELF_DIR/observe_flag.sh"
SKILL="$(bash "$FLAGTOOL" get skill)"
[ -n "$SKILL" ] || exit 0                       # cleared or expired while we waited: nothing to do
SKILL_FILE="$(bash "$FLAGTOOL" get skill_file)"
NOTES_DIR="$(bash "$FLAGTOOL" get notes_dir)"
OFFSET="$(bash "$FLAGTOOL" get offset)"
FINDINGS="$NOTES_DIR/findings.md"; NOTES="$NOTES_DIR/observe-notes.md"
INBOX="$OD/inbox-$SID.txt"; FAILMARK="$OD/failnotified-$SID"
mkdir -p "$NOTES_DIR" 2>/dev/null
TS() { date '+%Y-%m-%d %H:%M:%S'; }

fail() {   # fail <reason> — one line in findings.md, one line in the inbox (once per failure streak)
  printf -- '- [%s] REVIEWER FAILED: %s\n' "$(TS)" "$1" >> "$FINDINGS"
  if [ ! -f "$FAILMARK" ]; then
    printf 'reviewer did not run: %s\n' "$1" >> "$INBOX"; : > "$FAILMARK"
  fi
  exit 0
}

[ -f "$SKILL_FILE" ] || fail "the skill file is gone ($SKILL_FILE)"
[ -r "$PAYLOAD" ] || fail "the end-of-turn payload was unreadable"

# ── build the prompt ──
PROMPT="$OD/prompt-$SID.md"; REPLY="$OD/reply-$SID.txt"
INFO="$OD/info-$SID.txt"
RUN_WD="$(bash "$_SELF_DIR/run_pointer.sh" get 2>/dev/null)"
python3 - "$PAYLOAD" "$PROMPT" "$INFO" "$SKILL" "$SKILL_FILE" "$NOTES" "$OFFSET" "$PLUG" "$RUN_WD" <<'PY'
import json, os, re, subprocess, sys
payload_f, prompt_f, info_f, skill, skill_file, notes_f, offset, plug, run_wd = sys.argv[1:10]
CAP = int(os.environ.get("OBSERVE_TRANSCRIPT_CAP", "20000"))
try:
    p = json.load(open(payload_f, encoding="utf-8"))
except Exception as e:
    open(info_f, "w").write("FAIL payload not JSON: %s\n" % e); sys.exit(0)
def rd(path, default=""):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return default
design = rd(skill_file)

# step prompt: only if an open run of THIS skill exists
step_note = "(no open run of this skill was found; no step prompt)"
step_text = ""
try:
    sys.path.insert(0, os.path.join(plug, "system", "parts"))
    import stage_runner
    found = None
    for start in (p.get("cwd") or "", run_wd):
        if start and os.path.isdir(start):
            try:
                found = stage_runner.find_run(start)
            except Exception:
                found = None
            if found: break
    if found:
        wd, run_dir = found
        if not os.path.isabs(run_dir): run_dir = os.path.join(wd, run_dir)
        st = subprocess.run([sys.executable, os.path.join(plug, "system", "parts", "stage_runner.py"),
                             "status", "--json", "--workdir", wd], capture_output=True, text=True, timeout=30)
        j = json.loads(st.stdout)
        if j.get("skill") == skill and not j.get("complete"):
            n = int(j.get("index"))
            cand = os.path.join(run_dir, "stage", "%02d.prompt.md" % n)
            if os.path.exists(cand):
                step_text = rd(cand); step_note = "step %d of %d" % (n, int(j.get("total", 0)))
except Exception as e:
    step_note = "(step prompt unavailable: %s)" % str(e)[:120]

# transcript since the saved offset: person + assistant text only
tp = p.get("transcript_path") or ""
turns = []; new_off = ""
def text_of(content):
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""
SR = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
try:
    size = os.path.getsize(tp)
    start = int(offset) if offset.isdigit() and int(offset) <= size else None
    with open(tp, "rb") as f:
        if start: f.seek(start)
        raw = f.read()
    raw = raw[:raw.rfind(b"\n") + 1]   # whole lines only: a half-written last line is read next time
    new_off = str((start or 0) + len(raw))
    for line in raw.split(b"\n"):
        line = line.strip()
        if not line: continue
        try: d = json.loads(line)
        except Exception: continue
        t = d.get("type")
        if t not in ("user", "assistant") or d.get("isMeta") or d.get("isSidechain"): continue
        txt = SR.sub("", text_of((d.get("message") or {}).get("content"))).strip()
        if not txt or txt.startswith("[harness-injected") or txt.startswith("<command-") or txt.startswith("<local-command"): continue
        turns.append(("PERSON" if t == "user" else "SKILL", txt))
    if start is None:   # first review of this watch: just the last turn (from the last person message)
        last_u = max([i for i, (w, _) in enumerate(turns) if w == "PERSON"] or [0])
        turns = turns[last_u:]
except Exception:
    turns = []; new_off = ""
if not turns:
    lam = p.get("last_assistant_message") or ""
    turns = [("SKILL", lam or "(no text found for this turn)")]
body = "\n\n".join("%s: %s" % (w, t) for w, t in turns)
if len(body) > CAP:
    body = "(earlier text cut)\n" + body[-CAP:]

notes = "".join(rd(notes_f).splitlines(True)[-30:]) or "(no notes yet)"
prompt = """You are the SKILL BUILDER'S REVIEWER, watching a person use a skill. You run in the background after each turn.
You are a thinking partner, not a note-taker. You look for four kinds of thing only:
DIDN'T HAPPEN: something the skill's design says should happen that this turn did not do.
SPEC GAP: something the design is missing, which this turn showed.
LIKELY CAUSE: a likely cause behind something the person seems unhappy or confused about.
BETTER WAY: something the harness or design already has that would do this better.

Quiet rule: only findings a skill designer would act on. Never praise. Never restate the turn.
Rank your findings, most important first. Give at most 5, each one line:
"<KIND>: <finding> (evidence: <short quote from the turn>)", where <KIND> is exactly one of
DIDN'T HAPPEN, SPEC GAP, LIKELY CAUSE, BETTER WAY.
Start a line with "SHOW: " (then the kind) if a skill designer would want to be interrupted for it right now, and with
"LOG: " otherwise. Most findings are LOG. Use SHOW only for the few that matter now.
If nothing is worth saying at all, reply exactly NOTHING.
End your reply with the line END-REVIEW on its own line.

=== THE SKILL'S DESIGN (its SKILL.md) ===
%s

=== THE STEP PROMPT FOR THE STEP BEING RUN (%s) ===
%s

=== THE PERSON'S OWN NOTES (last lines; their words, verbatim) ===
%s

=== THE TURN(S) TO REVIEW ===
%s
""" % (design, step_note, step_text or "(none)", notes, body)
open(prompt_f, "w", encoding="utf-8").write(prompt)
open(info_f, "w").write("OK %s\n" % new_off)
PY
INFO_LINE="$(head -1 "$INFO" 2>/dev/null)"
case "$INFO_LINE" in OK*) ;; *) fail "could not build the prompt: ${INFO_LINE:-no reason}";; esac
NEW_OFF="${INFO_LINE#OK }"; [ "$NEW_OFF" = "OK" ] && NEW_OFF=""

# ── the one model call ──
. "$_SELF_DIR/model.lib.sh" 2>/dev/null || fail "cannot load model.lib.sh"
export MODEL_TIMEOUT="${OBSERVE_MODEL_TIMEOUT:-240}"
if ! RMSG="$(run_model medium "$PROMPT" "$REPLY" END-REVIEW 2>&1)"; then
  reason="$(printf '%s\n' "$RMSG" | grep -F '[run_model] FAILED:' | head -1 | sed 's/.*FAILED: //' | cut -c1-200)"
  fail "${reason:-the model call failed}"
fi

# ── parse by prefix, append to findings.md, fill the inbox ──
SHOWN=0; ANY=0; TMPIN="$OD/inbox-$SID.new"; : > "$TMPIN"
[ -s "$INBOX" ] && SHOWN="$(grep -c . "$INBOX")" && cp "$INBOX" "$TMPIN"
KINDRE="^(DIDN'T HAPPEN|SPEC GAP|LIKELY CAUSE|BETTER WAY):[[:space:]]*"
while IFS= read -r line; do
  line="${line%$'\r'}"
  case "$line" in
    "SHOW:"*) tag=SHOW; rest="${line#SHOW:}";;
    "LOG:"*)  tag=LOG;  rest="${line#LOG:}";;
    *) continue;;
  esac
  rest="${rest#"${rest%%[![:space:]]*}"}"
  [ -n "$rest" ] || continue
  ANY=1
  printf -- '- [%s] %s %s\n' "$(TS)" "$tag" "$rest" >> "$FINDINGS"
  if [ "$tag" = SHOW ] && [ "$SHOWN" -lt 5 ]; then printf '%s\n' "$rest" >> "$TMPIN"; SHOWN=$((SHOWN+1)); fi
done < "$REPLY"
if [ "$ANY" = 0 ] && ! grep -qx 'NOTHING' <(sed 's/END-REVIEW//; s/^[[:space:]]*//; s/[[:space:]]*$//' "$REPLY"); then
  printf -- '- [%s] UNPARSED reviewer reply (no SHOW:/LOG: lines): %s\n' "$(TS)" "$(tr '\n' ' ' < "$REPLY" | cut -c1-300)" >> "$FINDINGS"
fi
if [ -s "$TMPIN" ]; then mv "$TMPIN" "$INBOX"; else rm -f "$TMPIN"; fi
rm -f "$FAILMARK"
[ -n "$NEW_OFF" ] && bash "$FLAGTOOL" set offset "$NEW_OFF"
rm -f "$PROMPT" "$REPLY" "$INFO"
exit 0
