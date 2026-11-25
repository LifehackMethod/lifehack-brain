#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "observe_ups.sh" "UserPromptSubmit" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: OBSERVE MODE (round 2, brief 2.1): a person uses a skill while a background reviewer reads each turn. This is
#      the person-facing half, run by code on the person's raw prompt (never by the model): (1) /skill-builder-observe
#      <skill> arms the watch, /skill-builder-observe off clears it; (2) /skill-builder-note <text> files the words
#      BYTE FOR BYTE in the notes folder (a command's `!` bash line would put the text through the shell and break on
#      quotes, $ and backticks; a hook reads the raw JSON, so nothing is re-interpreted); (3) /skill-builder-wrap tells
#      the model where the notes and findings are; (4) at the next prompt, any findings the reviewer left in the inbox
#      appear on the PERSON'S screen under "🛠 Skill builder here:" and are handed to the model as context.
#      It is its OWN register row, not a member of the pilot-map-ups group: the group dispatcher concatenates every
#      member's stdout, and this hook's stdout is one JSON object, which plain text from a sibling would break.
# GUARDS: UserPromptSubmit, every prompt. Never blocks. Quiet path: no python, no model, no process beyond this shell
#      unless the prompt names a /skill-builder-* command OR this session's inbox file has content.
# REDIRECT: arm/clear = system/tools/observe_flag.sh; notes + findings = <notes folder>/notes.md, findings.md (the folder
#      is stored in the switch). A person who never typed an observe command sees nothing from this hook.
# SIGNPOST: design = brief 2.1 (build-skill-v2). The reviewer = system/tools/observe_review.sh; the Stop launcher =
#      end_of_turn_checks.sh. Cap: 5 lines, ~1,200 characters on screen.
# FAIL_POSTURE: degrade-safe — any error exits 0 with no output (a prompt hook's failure must never stop a prompt).
# UPDATED: 2026-11-25 (new, 2.1)
# ─────────────────────────────────────────────────────────────────────────────
IFS= read -r -d '' P || true
re_sid='"session_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]+)"'
[[ $P =~ $re_sid ]] || exit 0; SID="${BASH_REMATCH[1]}"
OD="$HOME/.claude/run/observe"; INBOX="$OD/inbox-$SID.txt"
CMD=""; case "$P" in *skill-builder-observe*|*skill-builder-note*|*skill-builder-wrap*) CMD=1;; esac
[ -n "$CMD" ] || [ -s "$INBOX" ] || exit 0          # the quiet path: nothing typed, nothing waiting
TOOLS="$(cd "${_lhb_dir}/../tools" 2>/dev/null && pwd -P)"
[ -n "$TOOLS" ] || exit 0
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 CLAUDE_CODE_SESSION_ID="$SID" OD="$OD" TOOLS="$TOOLS" python3 - "$P" 2>/dev/null <<'PY'
import json, os, re, subprocess, sys, time
TAG = "[harness-injected, not user input]"
try:
    j = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
sid = os.environ["CLAUDE_CODE_SESSION_ID"]; od = os.environ["OD"]; tools = os.environ["TOOLS"]
flagtool = os.path.join(tools, "observe_flag.sh")
prompt = j.get("prompt") if isinstance(j.get("prompt"), str) else ""
ctx = []; show = []

def flag(*args):
    r = subprocess.run(["bash", flagtool] + list(args), capture_output=True, text=True, timeout=20)
    return r.returncode, r.stdout.strip()

m = re.match(r"^/(?:[A-Za-z0-9_-]+:)?skill-builder-(observe|note|wrap)(?:[ \t\r\n]+|$)", prompt)
if m:
    verb = m.group(1); rest = prompt[m.end():]
    if verb == "observe":
        arg = rest.strip()
        if arg in ("off", "clear", "stop"):
            rc, out = flag("clear")
            ctx.append("OBSERVE OFF: no skill is being watched in this window now.")
        else:
            rc, out = flag("arm", arg)
            if out.startswith("OBSERVE ARMED: "):
                skill, nd = out[len("OBSERVE ARMED: "):].split("|", 1)
                ctx.append("OBSERVE ARMED: Observing %s; notes go to %s; /skill-builder-note to jot, /skill-builder-wrap at the end" % (skill, nd))
                ctx.append("SKILL TO START: %s" % skill)
            else:
                ctx.append(out or "OBSERVE NOT ARMED: the arming tool printed nothing")
    elif verb == "note":
        rc, nd = flag("get", "notes_dir")
        if not nd:
            ctx.append("OBSERVE NOTE NOT FILED: no skill is being observed in this window, so nothing was written")
        elif not rest.strip():
            ctx.append("OBSERVE NOTE NOT FILED: the note was empty, so nothing was written")
        else:
            try:
                os.makedirs(nd, exist_ok=True)
                with open(os.path.join(nd, "notes.md"), "a", encoding="utf-8", newline="", errors="surrogatepass") as f:
                    f.write("\n### %s\n%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), rest))
                ctx.append("OBSERVE NOTE FILED: the person's words went into %s word for word. The reviewer will weigh the note after this turn." % os.path.join(nd, "notes.md"))
            except OSError as e:
                ctx.append("OBSERVE NOTE NOT FILED: could not write the notes file (%s)" % str(e)[:150])
    else:
        rc, nd = flag("get", "notes_dir")
        rc2, sk = flag("get", "skill")
        if nd:
            ctx.append("OBSERVE WRAP: skill %s; notes file %s; findings file %s (either may not exist yet)" % (sk, os.path.join(nd, "notes.md"), os.path.join(nd, "findings.md")))
        else:
            ctx.append("OBSERVE WRAP: no skill is being observed in this window (the watch was never armed here, was turned off, or timed out); ask the person which skill and notes folder to wrap")

inbox = os.path.join(od, "inbox-%s.txt" % sid)
if os.path.isfile(inbox) and os.path.getsize(inbox) > 0:
    try:
        lines = [l.strip() for l in open(inbox, encoding="utf-8", errors="replace").read().splitlines() if l.strip()]
        os.replace(inbox, os.path.join(od, "inbox-%s.shown" % sid))     # moved aside: shown once
    except OSError:
        lines = []
    budget = 1200; kept = []
    for i, l in enumerate(lines[:5], 1):
        item = "%d. %s" % (i, l)
        if len(item) > budget:
            item = item[:max(budget - 1, 20)].rstrip() + "…"
        budget -= len(item) + 1
        kept.append(item)
        if budget <= 0: break
    if kept: show = kept

if not ctx and not show:
    sys.exit(0)
out = {}
head = "🛠 Skill builder here:"
if show:
    out["systemMessage"] = head + "\n" + "\n".join(show)
parts = []
if show:
    parts.append("%s %s\n%s" % (TAG, head, "\n".join(show)))
for c in ctx:
    parts.append("%s %s" % (TAG, c))
out["hookSpecificOutput"] = {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(parts)}
print(json.dumps(out, ensure_ascii=False))
PY
exit 0
