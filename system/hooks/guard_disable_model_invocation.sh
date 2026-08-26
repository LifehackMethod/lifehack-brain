#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the operator retired `disable-model-invocation` FLEET-WIDE on 2026-08-06 ("I want all of my
#      skills to be able to invoke each other. It's a guard that I don't feel that I need." —
#      authority: user, system/sops/skill-building-sop.md:605-622). THE SAME DAY, a build
#      session re-installed the flag on skills/skill-builder/SKILL.md anyway — not malice, but
#      the PLAN it was executing still cited the retired SOP clause as authority. A doctrine
#      change recorded only in prose does not stop a session working off a stale plan; nothing
#      mechanical stood between the write and the file. This hook is that mechanical stop.
# GUARDS: any Write, Edit, or MultiEdit whose resulting content would add the literal
#      FRONTMATTER-KEY line `disable-model-invocation: true` (start-of-line, `key: value`
#      form) to any SKILL.md. Deliberately narrow: a bare MENTION of the string in prose —
#      discussing, quoting, or documenting the retired flag — is NOT blocked. Five SKILL.md
#      files (autoplan, checkin, ship, onboard-probe, world-model-builder) legitimately carry
#      that historical prose today, and this system has a documented scar where a
#      keyword-matching guard fired on a benign mention and blocked its own author's commit.
#      Only the anchored frontmatter-key regex `^disable-model-invocation:\s*true\s*$` fires
#      this guard — a sentence like "carries `disable-model-invocation: true`… " does not
#      start the line with the key, so it passes.
# REDIRECT: the flag is RETIRED — do not re-add it to any skill, for any reason, including a
#      plan that still cites the old rule (the plan is stale, not this guard). If a skill has
#      a genuine side-effect that needs gating, the flag was NEVER the right tool for that (it
#      only ever gated who may START the skill, never what it DOES) — put the guard on the
#      DESTRUCTIVE ACT instead: a confirm-gate at the destructive step (see skills/ship/SKILL.md
#      push_gate), a PreToolUse hook (system/hook-contract.md), or a SAFE-HALT the skill's own
#      prose cannot skip.
# SIGNPOST: system/sops/skill-building-sop.md:605-622 — the operator's 2026-08-06 ruling, authority:
#      user. Changing this back is a doctrine call, not a build session's judgment: it needs a
#      fresh, explicit ruling from the operator, recorded the same way, before this guard is touched.
# FAIL_POSTURE: degrade-safe (declared exception to hook-sop.md §3.2's fail-closed default) — this
#      guard protects a retired STYLISTIC flag, not a security boundary (auth/credentials/the wrong
#      calendar/a destructive write). Failing closed here would risk blocking unrelated SKILL.md
#      edits on a parser hiccup, which is a worse outcome than the rare miss this guard would let
#      through on a malformed payload it cannot even read.
# UPDATED: 2026-08-06
# ─────────────────────────────────────────────────────────────────────────────
# guard_disable_model_invocation.sh — PreToolUse hook (matcher: Write|Edit|MultiEdit)
# Blocks any write that would reinstate `disable-model-invocation: true` in a SKILL.md's
# frontmatter. Degrade-safe: any parse failure ALLOWS the write through — this guards a
# retired stylistic flag, not a security boundary, and must never be the thing that breaks a
# turn.

# ── INPUT PARSING ─────────────────────────────────────────────────────────────
INPUT=$(cat)
export INPUT

python3 <<'PY'
import os, json, re, sys

def allow(*_):
    sys.exit(0)

try:
    raw = os.environ.get("INPUT", "")
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    # Can't even parse the tool call -- degrade-safe: allow, never break the turn.
    allow()

ti = data.get("tool_input", {}) or {}
path = ti.get("file_path") or ti.get("path") or ""

# Only SKILL.md files are in scope.
if not isinstance(path, str) or not path.endswith("SKILL.md"):
    allow()

# ── GUARD LOGIC ───────────────────────────────────────────────────────────────
# Anchored to the FRONTMATTER KEY FORM only -- start of line, "disable-model-invocation:
# true" and nothing else on that line. A prose mention ("...carries `disable-model-invocation:
# true`...") never starts its own line with the bare key, so it never matches. This is the
# exact narrowness the 2026-08-06 task calls for: block the ACT of installing the key, never
# a discussion of it.
PATTERN = re.compile(r'(?m)^disable-model-invocation:\s*true\s*$')

# Gather every chunk of NEW content this call would introduce, across all three tool shapes:
#   Write      -> tool_input.content              (the whole new file)
#   Edit       -> tool_input.new_string            (the fragment being spliced in)
#   MultiEdit  -> tool_input.edits[*].new_string    (each fragment being spliced in)
chunks = []
try:
    if ti.get("content") is not None:
        chunks.append(str(ti.get("content")))
    if ti.get("new_string") is not None:
        chunks.append(str(ti.get("new_string")))
    edits = ti.get("edits")
    if isinstance(edits, list):
        for e in edits:
            if isinstance(e, dict) and e.get("new_string") is not None:
                chunks.append(str(e.get("new_string")))
except Exception:
    allow()

if not chunks:
    allow()

hit = any(PATTERN.search(c) for c in chunks)
if not hit:
    allow()

# ── DENY ───────────────────────────────────────────────────────────────────────
reason = (
    "BLOCKED: this write introduces the frontmatter line `disable-model-invocation: true` "
    "into a SKILL.md. WHY: the operator retired this flag FLEET-WIDE on 2026-08-06, authority: user "
    "(\"I want all of my skills to be able to invoke each other. It's a guard that I don't "
    "feel that I need.\"). It came off the last three skills carrying it (/ship, "
    "/onboard-probe, /world-model-builder) that same day, after /autoplan's removal on "
    "2026-08-04 -- the fleet now has ZERO. A plan that still cites the retired rule is not "
    "authority to reinstate it; the plan is stale, not this guard. REDIRECT: do not add this "
    "flag, ever, for any reason. If this skill has a genuine side-effect that needs gating, "
    "the flag was never the right tool -- it only ever gated who may START the skill, never "
    "what it DOES. Put the guard on the DESTRUCTIVE ACT instead: a confirm-gate at the "
    "destructive step (see skills/ship/SKILL.md push_gate), a PreToolUse hook "
    "(system/hook-contract.md), or a SAFE-HALT the skill's own prose cannot skip. RULE: "
    "system/sops/skill-building-sop.md:605-622 -- changing this back needs a fresh explicit "
    "ruling from the operator, not a build session's judgment."
)
sys.stderr.write(json.dumps({"decision": "block", "reason": reason}) + "\n")
sys.exit(2)
PY
exit $?
