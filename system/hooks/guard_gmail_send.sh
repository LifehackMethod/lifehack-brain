#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible.
#
#  MEASURED, 2026-08-14, in the system this was ported from. Four sibling guards were
#  fire-tested and then attacked by two independent auditors charged to break them:
#    · the first found 20 bypasses in ~20 minutes; 11 of 13 headline claims reproduced
#    · after a rewrite, the second found 13 more, all reproduced
#    · after three rounds of hardening, 1 of 27 tested attack forms still passes
#  Every one of those holes was in a guard reading a command STRING. The pattern that
#  system journal states: every guard that failed was on Bash — every guard that
#  fired correctly was on a typed tool.
#
#  PRIOR ART, same conclusion: CVE-2025-66032 — eight independent bypasses of Claude
#  Code own regex blocklist (man --html, sort --compress-program, sed e flag, IFS,
#  parameter-transform expansion), plus an independently reproduced command-substitution
#  bypass of an allowlist.
#
#  ⇒ IF YOU ARE ADDING A CONTROL THAT MUST NOT BE BYPASSED, DO NOT ADD IT HERE.
#    Put it on a typed tool, or make the dangerous act structurally impossible.
#    Adding a ninth pattern to this file buys less than it appears to.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: A fresh install of this system shipped a guard against an agent DELETING mail
#      (guard_gmail_destructive.sh) and none at all against an agent SENDING it. That is the
#      wrong way round: a delete sits recoverable in the Gmail bin, and a sent mail is gone the
#      instant it leaves — outward-facing, in the operator name, to a real person, with no undo
#      anywhere. The gap was not theorised: it was measured against the shipped hook set, and
#      system/tools/organism/label_manifest.yaml carried a standing FLAG FOR THE LEAD saying so
#      in writing before this hook existed. Every other irreversible Google surface reachable
#      with one gws login is already guarded here — which calendar a write lands on, destructive
#      sheet ops, credential logout, mail deletion. Sending was the one hole.
#      ⭐ THE ASYMMETRY IS THE WHOLE ARGUMENT: if you never granted Gmail send scope this guard
#      costs you literally nothing, because no such command can succeed anyway; if you did grant
#      it, this is the only thing standing between an unattended run and mail your contacts
#      believe you wrote.
# GUARDS: any gws gmail command whose OPERATION is a send — messages send, drafts send, and the
#      +send helper — plus any gmail operation this guard does not recognise (default-deny, see
#      below). DRAFTING IS EXPLICITLY ALLOWED and is the point: drafts create / update / get /
#      list / delete all pass, as do the reads (messages and threads get / list / read, labels,
#      settings, history, getProfile, attachments get) and the label-move verbs. Mail DELETION is
#      deliberately NOT this guard business — guard_gmail_destructive.sh owns that, and one
#      irreversible act per guard is how both stay legible.
# REDIRECT: compose it as a DRAFT with the same --params body —
#      gws gmail users drafts create --params <body>   (or drafts update to revise one)
#      — then open Gmail and press send yourself. The draft is the deliverable; the human is the
#      send button. If a legitimate READ was refused, add its verb to SAFE_VERBS in this file
#      deliberately; never append an allow-on-fallthrough to make one command fit.
# SIGNPOST: the RULE lives in this file GUARDS line above — an agent in this system drafts mail
#      and never sends it. Which Google services your agent can reach at all is YOUR setting,
#      decided at the sit-down in INSTALL.md ("grant only the scopes you actually intend to
#      use"). To change what is blocked, change that rule deliberately and amend this hook, then
#      update its row in system/tools/organism/label_manifest.yaml so the map and the guard
#      cannot disagree. ⚠ Do NOT read system/security-canon.md hook table as this rule home:
#      that table is a historical record of the donor system hooks and says so in its own scope
#      note.
# FAIL_POSTURE: closed — unreadable stdin, unparseable JSON, a missing shared parser, or a
#      python error all DENY (hook-sop.md §3.2). A guard that cannot read its input must never
#      allow: the cost of a false block is one retry through a draft, and the cost of a false
#      allow is a mail you cannot recall.
# KNOWN LIMITS (stated, not hidden — an honest gap beats a false guarantee):
#   1. TEXT MATCHER. See the banner. This raises the cost of a mistake; it does not make one
#      impossible. Do not put a control here that must not be bypassed.
#   2. SCOPE GATE. The hook only engages when a gws binary token is named somewhere in the
#      command AND the word gmail appears somewhere in it. A command that hides the SERVICE word
#      behind a variable and never mentions gmail at all is never seen by this guard. Same limit
#      as guard_gmail_destructive.sh; widening it would mean inspecting every gws call for every
#      service, trading a real over-block for a hypothetical under-block.
#   3. DEFAULT-DENY READS THE OPERATION WINDOW ONLY — the tokens between the service word and the
#      first flag or quoted argument. A flag placed BEFORE the operation truncates that window,
#      the operation becomes unrecognised, and the command is DENIED. That is fail-closed on
#      purpose, and it can refuse an unusual but legitimate spelling. The deny message says
#      exactly what to do about it: add the verb, deliberately.
#   4. ⛔ TYPED GMAIL TOOLS ARE NOT COVERED. This is a Bash matcher. An MCP or built-in Gmail
#      tool that sends mail (a send_message / reply / forward tool) does not go through Bash and
#      this guard never sees it. If such a tool is ever enabled here, the send path is open
#      through it and a SEPARATE control on that typed tool is required — which is also where
#      hook-contract.md says a must-not-be-bypassed control belongs in the first place.
# UPDATED: 2026-08-15
# PORTED 2026-08-15 from the donor system guard of the same name. Three deliberate changes, each
#      because this repo is not that one: (a) the donor deny message and header cited that system
#      own private policy docs and a dated personal ruling; a redirect to a file the reader does
#      not have is worse than no redirect at all, so the rule is restated in this header and the
#      REDIRECT points at commands and at this file. (b) The donor matched its verbs with an
#      inline regex over a hand-cut command HEAD; here the SHARED parser
#      system/hooks/lib/gws_guard.py does the segmentation, because this repo already learned
#      that four guards writing that parser privately got it wrong four different ways — it
#      handles assignment prefixes, wrapper words, a binary held in a variable, command
#      substitution and bash -c / eval, none of which the donor regex saw. (c) `read` was added
#      to the safe verb set: it is a real gmail body-read alias in THIS repo (named in
#      system/tools/organism/label_manifest.yaml) and it is already blocked upstream by
#      ingest_gate_enforce.sh, so refusing it here would be a second wall on a path that is
#      neither a send nor unguarded.
#
# ⚠ DEFAULT-DENY BY DESIGN, and the reason is a sibling that failed OPEN.
#   A calendar rail in the donor system listed the KNOWN write verbs and ended with an
#   allow-on-fallthrough. That is an allowlist of attack SPELLINGS, and the gws +insert helper
#   walked straight through it — exit 0, for months. So this guard does the inverse: it
#   recognises the SAFE gmail operations (reads + drafting) and denies everything else,
#   including a verb gws adds tomorrow. An unknown operation is UNKNOWN-therefore-DENIED, never
#   unknown-therefore-allowed.
#   ⛔ Do NOT "fix" a blocked read by appending an allow. Add the verb to SAFE_VERBS, deliberately.
# ─────────────────────────────────────────────────────────────────────────────
# guard_gmail_send.sh — PreToolUse hook (matcher: Bash)
# Two-sided suite: system/hooks/tests/test_gmail_send_guard.sh (ALLOW cases first).

DENY='{"decision":"block","reason":"BLOCKED: this Gmail command SENDS mail, or uses a gmail operation this guard does not recognise. WHY: a send is irreversible and outward-facing — it leaves in your name, to a real person, and nothing anywhere undoes it. This system may DRAFT mail; the human presses send. Every other irreversible Google surface reachable with one gws login is already guarded here (which calendar a write lands on, destructive sheet ops, credential logout, mail deletion) and the send path was the one hole. This guard is DEFAULT-DENY on purpose: a sibling rail once listed the known write verbs and ended with an allow, and an unlisted helper verb walked straight through it for months. REDIRECT: compose it as a DRAFT with the same --params body — run gws gmail users drafts create (or drafts update to revise one) — then open Gmail and send it yourself. The draft is the deliverable. Reads are untouched: messages and threads get / list / read, labels, settings, history, getProfile and attachments get all pass, and mail deletion belongs to guard_gmail_destructive.sh, not to this guard. RULE: the GUARDS line in system/hooks/guard_gmail_send.sh — an agent in this system drafts mail and never sends it. Change that rule deliberately and amend this hook, then update its row in system/tools/organism/label_manifest.yaml. If a legitimate READ was refused, add its verb to SAFE_VERBS in that file on purpose; never append an allow-on-fallthrough to make one command fit."}'

# ⭐ A SEPARATE MESSAGE FOR "I COULD NOT READ THIS". Measured 2026-08-23 (ported from ClaudeOps,
# same guard): this guard used to fail closed on an unreadable payload, a missing parser, or its
# own decision script crashing by reusing $DENY above -- so a failure that had nothing to do with
# sending mail came back "this Gmail command SENDS mail, or uses a gmail operation this guard does
# not recognise". Failing closed here is still correct; blaming a send that never happened is not.
PARSE_DENY='{"decision":"block","reason":"BLOCKED: guard_gmail_send could not read, parse, or evaluate this command, so it is refusing rather than guessing. This is NOT a report that the command sends mail or uses an unrecognised gmail operation -- it is a report that the guard itself could not get far enough to make that call (unreadable input, a missing parser file, or the decision script failing to run). WHY: an unevaluable command aimed at Gmail is refused rather than assumed safe. REDIRECT: re-run the tool call so its JSON payload is well-formed; if this keeps happening, check that system/hooks/lib/gws_guard.py is present and readable. If what you actually wanted was to send mail, note this guard never allows that regardless: compose it as a draft instead -- gws gmail users drafts create (or drafts update) -- then send it yourself from Gmail. RULE: system/hooks/guard_gmail_send.sh, FAIL_POSTURE."}'

deny() { printf '%s\n' "$DENY" >&2; exit 2; }
deny_parse() { printf '%s\n' "$PARSE_DENY" >&2; exit 2; }

# Fail-closed: a guard that cannot read its own input must DENY, never pass. This is a "could not
# read the input" failure, not a rule match -- say so honestly rather than naming a send.
INPUT=$(cat 2>/dev/null) || deny_parse

# House __ERR__ sentinel rather than jq: jq exits 0 on EMPTY stdin, which fail-OPENED a sibling
# calendar guard in the donor system.
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception:
    print('__ERR__')" 2>/dev/null)
[ "$COMMAND" = "__ERR__" ] && deny_parse
[ -z "$COMMAND" ] && exit 0

# ── SCOPE GATES — deliberately WIDER than the check they guard ────────────────────────────
# A scope gate must never be narrower than the decision behind it. The sibling destructive
# guard learned this the hard way: its pre-filter demanded a literal binary adjacent to the
# service word, so a binary held in a variable exited here and the real parser never ran. A
# guard that never SEES a command has not allowed it on purpose — it has not seen it, which is
# worse, because every presence-based audit still scores it green. Two loose gates: is a gws
# binary NAMED anywhere, and is this service named anywhere. A mere mention costs nothing; the
# parser below is what decides, and it is what should decide.
SCOPE="$(printf '%s' "$COMMAND" | tr -d "\\'\"")"
printf '%s' "$SCOPE" | grep -qE "(^|[^A-Za-z0-9_])gws([^A-Za-z0-9_]|$)|bin/gws" 2>/dev/null || exit 0
printf '%s' "$SCOPE" | grep -qi "gmail" 2>/dev/null || exit 0

# ⭐ THE SEGMENT PARSER LIVES IN ONE PLACE — system/hooks/lib/gws_guard.py — because several
# guards need exactly this and each private copy got it wrong differently. It resolves what a
# shell would actually RUN: assignment prefixes, wrapper words (env / command / nohup / xargs),
# a binary held in a variable, command substitution, and bash -c / eval bodies. A gws invocation
# QUOTED inside a heredoc, an echo, a commit message or a python string is never in command
# position, so it is data and it passes — that distinction is the whole point.
LIB="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/lib/gws_guard.py"
[ -r "$LIB" ] || deny_parse   # fail-closed: no parser, no permission -- not a rule match, say so

# The DECISION. Exit 0 = allow, 7 = block, anything else = the guard itself broke -> also block.
GUARD_CMD="$COMMAND" GUARD_LIB="$LIB" python3 -c '
import os, sys, importlib.util

spec = importlib.util.spec_from_file_location("gws_guard", os.environ["GUARD_LIB"])
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

Q = chr(39)      # apostrophe, spelled this way so this program can live in a single-quoted string
BT = chr(96)     # backtick

def norm(t):
    return t.replace(Q, "").replace(chr(34), "").replace(chr(92), "").lower()

def nonlit(s):
    return ("$" in s) or (BT in s)

# Resources whose EVERY operation is a read or a metadata op. Derived from the gmail users
# sub-resources; widen only on purpose.
SAFE_HEAD = {"getprofile", "history", "labels", "settings", "attachments", "+triage", "help", "--help"}

# messages / threads: reads, label moves, and the destructive verbs that belong to
# guard_gmail_destructive.sh rather than to this guard. "read" is a real body-read alias in this
# repo and is already gated upstream by ingest_gate_enforce.sh.
READS = {"get", "list", "read", "modify", "batchmodify", "trash", "untrash",
         "insert", "import", "delete", "batchdelete"}
SAFE_VERBS = {
    "drafts": {"create", "update", "get", "list", "read", "delete"},
    "messages": READS,
    "threads": READS,
}

def service_of(toks):
    for t in toks[1:]:
        if t.startswith("-"):
            continue
        return norm(t)
    return ""

def window(toks):
    """The OPERATION WINDOW: tokens after the service word, up to the first flag or quoted
    argument. Everything from there on is PAYLOAD -- a --params body containing the word list
    must never talk this guard into passing a send."""
    idx = None
    for i, t in enumerate(toks):
        if norm(t) == "gmail":
            idx = i
            break
    if idx is None:
        return None
    out = []
    for t in toks[idx + 1:]:
        if t.startswith("-"):
            break
        if (chr(34) in t) or (Q in t):
            break
        out.append(t)
    return out

def is_send(low):
    for t in low:
        if t == "send" or t.endswith("+send"):
            return True
    return False

def blocked(cmd):
    for toks in g.gws_segments(cmd):
        svc = service_of(toks)
        if svc and svc != "gmail" and not nonlit(svc):
            continue                       # another gws service entirely -- not ours to judge
        w = window(toks)
        if w is None:
            # gmail is not legible in this segment and something in it is hidden behind a
            # variable or a substitution. UNKNOWN must never be read as permission.
            if g.has_nonliteral(toks):
                return True
            continue
        low = [norm(t) for t in w]
        if is_send(low):
            return True                    # explicit SEND, judged FIRST and unconditionally,
                                           # so no allowlist ordering accident can pass one
        if g.has_nonliteral(w):
            return True                    # unresolvable operation
        if low and low[0] == "users":
            low = low[1:]
        if not low:
            continue                       # a bare service call prints help; harmless
        head = low[0]
        if head in SAFE_HEAD:
            continue
        if head in SAFE_VERBS:
            rest = low[1:]
            if head == "messages" and rest and rest[0] == "attachments":
                if len(rest) > 1 and rest[1] == "get":
                    continue
                return True
            if rest and rest[0] in SAFE_VERBS[head]:
                continue
            return True
        return True                        # unrecognised gmail operation -> DEFAULT DENY
    return False

sys.exit(7 if blocked(os.environ["GUARD_CMD"]) else 0)
' 2>/dev/null
RC=$?

# 7 = block, a real decision -- use the rule message. Any OTHER non-zero means the decision
# program itself failed to run to completion (not a rule match) -> FAIL CLOSED, per FAIL_POSTURE
# above, with the honest "could not evaluate" message. Never append an allow here.
if [ "$RC" -eq 7 ]; then
  deny
elif [ "$RC" -ne 0 ]; then
  deny_parse
fi

exit 0
