#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# ── CORRECTION (2026-08-23, lifehack-brain port, phase G2/G3) ───────────────
# The STATUS line immediately below, and everything through "not rely on it
# having stayed silently registered," is STALE and self-contradicting: it
# claims this hook was removed from settings.json's UserPromptSubmit array
# and is "not a live self-activating backstop," in the same breath as saying
# PORTED + REGISTERED. Re-derived this session, for THIS repo (lifehack-brain):
# the hook IS live. It is registered in hooks/hooks.json's UserPromptSubmit
# array, shipped as part of the public plugin's guard plane, and it
# demonstrably fired on an ordinary buried slash command during this very
# build. The "permanently empty trigger set" claim below is also false as
# written: the detection code was widened on 2026-08-21 (see the "EVERY
# skill, not a flag-gated subset" comment inside the Python block further
# down) to fire on ANY skill's buried slash-command, not only the retired
# disable-model-invocation list the STATUS/GUARDS/SIGNPOST prose below still
# describes. That prose is left in place uncorrected below (not deleted,
# per this project's rule against silent overwrites) — read it as a
# historical record of the disable-model-invocation episode, not as a
# description of what this hook currently does or currently fires on.
# ──────────────────────────────────────────────────────────────────────────
# STATUS (2026-08-23): PORTED + REGISTERED (plan task T3.5) into ClaudeOps and
#      lifehack-brain from the retired claudeops-config donor clone. The operator retired disable-model-invocation
#      FLEET-WIDE on 2026-08-06 (authority: user, system/sops/skill-building-sop.md:605-622:
#      "I want all of my skills to be able to invoke each other. It's a guard that I don't
#      feel that I need."). ZERO skills carry the flag today (verified 2026-08-06) — so this
#      hook's dynamically-discovered trigger set is now permanently empty, and it was removed
#      from settings.json's UserPromptSubmit array the same day rather than running a
#      no-op glob-scan on every prompt forever. The script is INTENTIONALLY left in place
#      (not deleted) so the mechanism is not lost. It is not a live "self-activating backstop"
#      in practice: the flag can only return via a fresh ruling from the operator reversing 2026-08-06
#      PLUS a deliberate edit to system/hooks/guard_disable_model_invocation.sh (the new
#      PreToolUse hook that hard-blocks any write reinstating the frontmatter key) — whoever
#      does that maintenance is already touching hook code and should re-register this hook
#      (add it back to settings.json's UserPromptSubmit array) as part of that same change,
#      not rely on it having stayed silently registered.
# WHY (historical, still true if ever reactivated): a disable-model-invocation skill removes
#      the model-fallback path a normal skill has — the ONLY way it fires is the harness's
#      literal /name parser, which requires the command to be the message's own leading
#      token. 2026-08-03/04: the operator buried "/autoplan" at the end of a longer paragraph FOUR
#      times in one session — the parser never saw it, the model was forbidden from rescuing
#      it (by the flag), and the request evaporated with no error at all. skills/autoplan,
#      skills/onboard-probe, and skills/world-model-builder ALL CARRIED THE FLAG AT THE TIME
#      this hook was built (2026-08-04) — none of them do as of 2026-08-06; this note is kept
#      accurate rather than restating that as a current fact.
# GUARDS: Nothing — pure UserPromptSubmit OBSERVER, structurally incapable of blocking
#      (always exit 0; no deny path exists in this script at all). Detects a message
#      that contains one of the disable-model-invocation skills' slash-commands as its
#      LAST piece of content (i.e. buried, not the leading token that the real parser
#      would have caught) and injects a short notice telling the human to re-send it as
#      its own message. Deliberately narrow to avoid the documented false-positive scar
#      (a guard that matched a keyword fired on a benign MENTION and blocked its own
#      author's commit): a mid-sentence mention with real words trailing after the
#      command ("I tried /autoplan earlier and it didn't work") does NOT fire, and a
#      path-shaped occurrence ("skills/autoplan/SKILL.md") does NOT fire because the
#      token isn't preceded by whitespace/start-of-string.
# REDIRECT: N/A (non-blocking, informational only). The fix for the human is mechanical:
#      re-send the command as its own message, e.g. a message that is JUST "/autoplan".
# SIGNPOST: The disable-model-invocation guarantee is RETIRED fleet-wide; its former home
#      was each skill's own frontmatter. See system/sops/skill-building-sop.md:605-622 for
#      the retirement ruling and system/hooks/guard_disable_model_invocation.sh for the hook
#      that now keeps it retired. This script still derives its list dynamically from
#      frontmatter every run, so it needs no further edit to reactivate correctly if the
#      doctrine is ever reversed — only re-registration in settings.json.
# UPDATED: 2026-08-06 (marked DORMANT/UNREGISTERED + stale skill-specific claims corrected;
#      script logic unchanged)
# ─────────────────────────────────────────────────────────────────────────────
# buried_command_hint.sh — UserPromptSubmit hook (matcher: "")
# Advisory-only: flags a disable-model-invocation skill's slash-command when it is
# buried at the end of a longer message instead of being the message's own first line.

set +e

# SKILLS LIVE IN DIFFERENT PLACES PER REPO (measured 2026-08-21):
#   ~/claudeops-config/skills (57) · ~/ClaudeOps/.claude/skills (46) ·
#   ~/lifehack-brain/.claude/skills (34)
# Probe BOTH layouts against the CURRENT project before falling back, or this hook
# resolves an empty/foreign skill set and silently does nothing in the very repo the
# operator is standing in -- the "silently dark" class hook-contract.md names.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
SKILLS_DIR=""
for _cand in "${REPO}/skills" "${REPO}/.claude/skills"; do
  [ -n "$_cand" ] && [ -d "$_cand" ] && { SKILLS_DIR="$_cand"; break; }
done
[ -n "$SKILLS_DIR" ] || exit 0

INPUT="$(cat 2>/dev/null)"

# Degrade-safe: any parse failure below prints nothing and this hook still exits 0 --
# it must NEVER be the thing that breaks a turn. Runs directly (not nested inside a
# command substitution) so its stdout IS the hook's stdout.
SKILLS_DIR="$SKILLS_DIR" python3 - "$INPUT" <<'PY' 2>/dev/null
import sys, os, re, glob, json

try:
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    sys.exit(0)

prompt = data.get("prompt") or ""
if not isinstance(prompt, str) or not prompt.strip():
    sys.exit(0)

skills_dir = os.environ.get("SKILLS_DIR", "")

# 1) Discover skills gated by disable-model-invocation: true -- read ONLY the YAML
#    frontmatter (between the first two '---' lines), never the body prose, so a skill
#    that merely DISCUSSES the flag (e.g. skills/checkin/SKILL.md, which quotes it in a
#    prose paragraph about /autoplan) is never mistaken for one that carries it itself.
names = []
try:
    for path in sorted(glob.glob(os.path.join(skills_dir, "*", "SKILL.md"))):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
        if not m:
            continue
        frontmatter = m.group(1)
        # EVERY skill, not a flag-gated subset (2026-08-21, the operator: "make it so all my
        # system skills will fire even if it's buried in a line"). The old gate keyed on
        # disable-model-invocation, retired fleet-wide 2026-08-06, so the set was empty and
        # this hook was a permanent no-op. Frontmatter must still PARSE (that is what makes
        # it a real skill dir); we just no longer require a particular key in it.
        names.append(os.path.basename(os.path.dirname(path)))
except Exception:
    sys.exit(0)

names = sorted(set(names))
if not names:
    sys.exit(0)

# Blank out fenced blocks and inline-backtick spans so a QUOTED command never fires.
# Structural, not keyword-narrowing: we are excluding a REGION, not a word.
scan = re.sub(r'```.*?```', lambda m: ' ' * len(m.group(0)), prompt, flags=re.S)
scan = re.sub(r'`[^`\n]*`', lambda m: ' ' * len(m.group(0)), scan)

stripped = prompt.strip()
hits = []

for name in names:
    # Command-token shape: a "/" immediately followed by the skill name, NOT preceded by
    # a word/slash/dash char (so "skills/autoplan/SKILL.md" never matches -- "autoplan" is
    # preceded by "s", not whitespace/start), and NOT followed by a word/dash char (so
    # "/autoplanning" never matches "/autoplan").
    pattern = re.compile(r'(?<![A-Za-z0-9_/-])/' + re.escape(name) + r'(?![A-Za-z0-9_-])')
    matches = list(pattern.finditer(scan))
    if not matches:
        continue

    # Working case already: the command IS the message's own leading token -> the real
    # harness parser catches this, no nag needed.
    leading = re.match(r'^/' + re.escape(name) + r'(?![A-Za-z0-9_-])', stripped)
    if leading:
        continue

    # Buried case: fire ONLY when a match sits at the very END of the message (nothing
    # after it but whitespace/trailing punctuation). This is the literal "buried at the
    # end of a longer paragraph" shape the operator hit four times, and it deliberately does NOT
    # fire on a mid-sentence mention like "I tried /autoplan earlier and it didn't work"
    # (real words trail the match there) -- narrower recall, zero false-positive risk.
    # ANY non-leading position counts (2026-08-21). The old rule fired only when the
    # command sat at the very END of the message -- deliberately narrow, "zero false
    # positive risk", but it misses the mid-sentence shape the operator actually hits.
    # WHY WIDENING IS SAFE HERE: code decides only MEMBERSHIP (is this token present,
    # outside code spans?) -- a thing it cannot be wrong about. Whether it was an
    # INVOCATION or a MENTION is judgment, and the injected text below hands that call to
    # the model with an explicit escape. Code detects; the model decides.
    hits.append(name)

if not hits:
    sys.exit(0)

cmds = ["/" + n for n in hits]
cmd_list = ", ".join(cmds)
first = cmds[0]
plural = "these commands" if len(cmds) > 1 else "this command"
print(
    "[BURIED COMMAND -- harness-injected, NOT the user's typed text] " + cmd_list +
    " appears in this message but NOT as its own leading token, so Claude Code's slash "
    "parser did NOT fire it. Burying it is silent: nothing runs and no error is shown, "
    "which reads exactly like the skill ran and found nothing.\n"
    "\u26d4 IF THE USER MEANT TO INVOKE IT, INVOKE Skill(" + hits[0] + ") NOW -- before "
    "any other tool call, before answering anything else in the message. Their invocation "
    "is not optional just because the parser missed it.\n"
    "IF THEY WERE REFERRING TO " + plural + " IN DISCUSSION rather than invoking, say so "
    "in ONE line and carry on -- do not silently do neither. This detection is mechanical "
    "(the token is present, outside code spans); deciding invocation-vs-mention is YOUR "
    "call, and going quiet is the one answer that is always wrong."
)
PY

exit 0
