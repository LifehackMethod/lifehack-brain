#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: `system/organism/` is the description this repository keeps of its OWN attack surface —
#      `manual.md` (the reference index), `map-format-specs.md` (the label criteria), and the
#      `elements/*.md` encyclopedia — AND it is the ground truth that the honesty-label checker
#      (`system/tools/organism/label_checker.py`) grades every guard against. Nothing downstream
#      re-reads it to see whether it still describes reality, so a single full-content overwrite
#      could replace the whole map, or flip every maturity label to LIVE, in one shot, and the
#      system would report itself healthy while being blind to itself.
#      THE LOCAL INCIDENT, and it is the reason this file exists at this destination:
#      this guard was DROPPED during the port on one stated justification —
#      `system/tools/organism/label_manifest.yaml` recorded that "system/organism/ does not exist
#      in this repo at all (confirmed absent)". Phase 9 landed that whole tree on 2026-08-15:
#      `manual.md` (1206 lines), `map-format-specs.md`, and 42 files under `elements/`. The premise
#      died and nothing replaced it, which left the worst of the three available states — SIX
#      SHIPPED files described the organism tree as write-guarded while nothing guarded it —
#      `manual.md` (4 occurrences) and 5 `elements/*.md` (archivist · claude-md-pyramid ·
#      hook-plane · label-checker · pulse-cron), counted with grep rather than by hand.
#      `map-format-specs.md` §6.4 was the ONE file that described the guarantee and then honestly
#      admitted it was unenforced here — which is why the gap was findable at all. A protection that is
#      DOCUMENTED BUT ABSENT is the exact defect class this migration kept finding, and the house
#      rule ratified the same day (`T9.11b`, `system/build-rules-index.md`) names it.
#      The donor also measured the scope error worth inheriting: the guard originally covered only
#      2 of 51 map files and named `elements/` nowhere at all, while the always-loaded map pointed
#      at the elements as THE live map. The elements carry the routing-critical `generated_from`
#      field and the INTENT / CURRENT-VS-TARGET fields the map honesty rests on — they were the
#      unguarded 96%. They are in scope here from the first line.
# GUARDS: a full-content `Write` (whole-file overwrite) of `system/organism/manual.md`,
#      `system/organism/map-format-specs.md`, or ANY `system/organism/elements/*.md` INSIDE THIS
#      REPOSITORY. Paths are resolved to their real location first, so a relative path, a `..`
#      segment or a symlink cannot name a protected file in a spelling the comparison misses —
#      the donor version matched a raw glob and a plain relative path walked straight past it.
#      Surgical `Edit` calls are NOT guarded, deliberately: that is the normal authoring path.
# REDIRECT: author the map with SURGICAL Edits (old_string -> new_string). Those are ALLOWED —
#      this hook is registered on the `Write` matcher only, so an Edit never even reaches it.
#      Maturity labels are machine-owned: run
#      `python3 system/tools/organism/label_checker.py write-labels` to recompute them; never
#      hand-write a LIVE. If a whole file genuinely must be regenerated, do it through Bash with a
#      human OK, which is deliberate and visible in a way a tool call is not.
# SIGNPOST: the RULE lives in `system/organism/map-format-specs.md` §6.4 (the write-guard clause)
#      and the maintenance contract at the top of `system/organism/manual.md`. Change what is
#      protected THERE, with sign-off from the person who owns this repository, then update this
#      guard and its registration in `.claude/settings.json`. Hook mechanics:
#      `system/hook-contract.md`; the decision layer: `system/sops/hook-sop.md`.
# FAIL_POSTURE: closed — an unreadable or unparseable payload DENIES. This hook sees only `Write`,
#      never every Bash command, so denying on a malformed message costs one retry and cannot wall
#      off the session.
# KNOWN LIMITS (stated, not hidden — an honest gap beats a false guarantee):
#   1. BASH WRITES ARE NOT COVERED. A heredoc, `tee`, `cp` or a `>` redirect aimed at a map file
#      bypasses this guard entirely, because it matches a typed tool. That is the same accepted
#      gap `guard_write_paths.sh` carries and records. It is also, deliberately, the REDIRECT above:
#      regenerating a whole map file through the shell is meant to stay possible for a human.
#   2. LABEL WRITES BY THE CHECKER ITSELF ARE NOT COVERED. `label_checker.py write-labels` writes
#      through Python, not the Write tool, so it is not intercepted. That is correct — it is the
#      sanctioned writer, and it is the thing this guard redirects people TO.
# UPDATED: 2026-08-15 (ported from the donor system; scope re-derived against this repo — 42
#      elements here, not 49; path matching rebuilt on realpath + this repo root rather than a
#      glob; deny channel confirmed against the house standard in `system/hook-contract.md`)
# ─────────────────────────────────────────────────────────────────────────────
# guard_organism_map.sh — PreToolUse hook (matcher: Write).
#
# ── DENY CHANNEL — verified, not assumed. ────────────────────────────────────────────────
# The house standard here is deny text on STDERR with `exit 2` (`system/hook-contract.md`,
# "Canonical Deny Format"), which is what the live fleet uses — see `guard_canon_write.sh`, whose
# every deny path is exactly this shape. The dead channel this repo has on record is a PreToolUse
# hook that prints and then `exit 0`s (`system/sops/hook-sop.md`, the `guard_web_search.sh` entry:
# "the warning was security theater the model never saw"). That failure is about the ALLOW path.
# A BLOCK at `exit 2` is read. `hookSpecificOutput.permissionDecision` is NOT used here:
# `hook-contract.md` rules it out for the BLOCK case by name, and this hook has no ALLOW notice.
#
# ⚠ THE DENY JSON MUST RE-PARSE. Measured during this port, before registration: the deny
# message wrapped a command in BACKTICKS, and the bash-escaping needed to survive a double-quoted
# string emitted a literal `\` + backtick into the JSON string -- an invalid escape. json.load()
# refused it, exit 2 still fired, and the guard would have blocked with a message NEITHER channel
# could render: silently DARK, exactly the failure `system/sops/hook-sop.md` §4 names ("re-parse
# the deny JSON afterwards"). An exit-code-only test scores this a PASS. ⛔ So: no backticks in
# the deny text, and re-run `python3 -c 'import json,sys; json.load(sys.stdin)'` on the STDERR of
# every deny path after any edit to this file.
set -uo pipefail

deny() {
  printf '%s\n' "$1" >&2
  exit 2
}

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${CLAUDE_PROJECT_DIR:-${_HOOKDIR%/system/hooks}}"

INPUT=$(cat 2>/dev/null) || deny '{"decision":"block","reason":"BLOCKED: guard_organism_map could not read its input, so it is failing closed. WHY: this guard stands over system/organism/ — the description this repository keeps of its own attack surface, and the ground truth the honesty-label checker grades against. An unreadable payload and a harmless one must never look the same. REDIRECT: retry the write; author the map with surgical Edits (old_string -> new_string), which are allowed and are the normal authoring path. RULE: system/organism/map-format-specs.md section 6.4 + the maintenance contract atop system/organism/manual.md."}'

export _ORG_REPO="$REPO"

# Resolve the target to its REAL path before comparing, and resolve the repo the same way, so both
# sides of the comparison are in one form. A relative path, a `..` segment or a symlink would each
# otherwise be a spelling of a protected file that a string test does not recognise.
read -r TOOL CONTENT_PRESENT FP <<EOF2
$(printf '%s' "$INPUT" | python3 -c "
import sys, json, os
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {}) or {}
    tool = (d.get('tool_name') or '').strip() or '__NONE__'
    has = '1' if ti.get('content') is not None else '0'
    p = ti.get('file_path') or ti.get('path') or ''
    if p:
        base = os.environ.get('_ORG_REPO') or os.getcwd()
        if not os.path.isabs(p):
            p = os.path.join(base, p)
        p = os.path.realpath(p)
    print(tool, has, p)
except Exception:
    print('__ERR__ __ERR__ __ERR__')
" 2>/dev/null)
EOF2

[ "$TOOL" = "__ERR__" ] && deny '{"decision":"block","reason":"BLOCKED: guard_organism_map could not parse the tool call, so it is failing closed. WHY: this guard stands over system/organism/ — the description this repository keeps of its own attack surface, and the ground truth the honesty-label checker grades against. A payload it cannot inspect must not pass. REDIRECT: retry the write; author the map with surgical Edits (old_string -> new_string), which are allowed and are the normal authoring path. RULE: system/organism/map-format-specs.md section 6.4 + the maintenance contract atop system/organism/manual.md."}'

# Not a full-content Write -> nothing for this guard to say. Edits fall out here even if the
# registration is ever widened past matcher=Write.
[ "$TOOL" = "Write" ] || exit 0
[ "$CONTENT_PRESENT" = "1" ] || exit 0
[ -n "$FP" ] || exit 0

REPO_REAL=$(python3 -c "
import os, sys
try: print(os.path.realpath(sys.argv[1]))
except Exception: print('')" "$REPO" 2>/dev/null)
[ -n "$REPO_REAL" ] || exit 0     # cannot locate the repo; this guard has nothing to say

case "$FP" in
  "$REPO_REAL"/system/organism/manual.md \
  |"$REPO_REAL"/system/organism/map-format-specs.md \
  |"$REPO_REAL"/system/organism/elements/*.md)
    deny "{\"decision\":\"block\",\"reason\":\"BLOCKED: a wholesale Write (full-file overwrite) of the self-schematic map — ${FP#$REPO_REAL/}. WHY: system/organism/ is the description this repository keeps of its OWN attack surface AND the ground truth the honesty-label checker (system/tools/organism/label_checker.py) grades every guard against. Nothing downstream re-reads it, so one full-content overwrite could replace the whole map, or flip every maturity label to LIVE, in a single shot — and the system would go on reporting itself healthy while blind to itself. REDIRECT: author the map with SURGICAL Edits (old_string -> new_string). Edits are ALLOWED and are the normal authoring path — this guard is registered on the Write matcher only, so an Edit never reaches it. Maturity labels are machine-owned: run: python3 system/tools/organism/label_checker.py write-labels -- to recompute them, never hand-write a LIVE. If a whole file genuinely must be regenerated, do it through Bash with a human OK. RULE: system/organism/map-format-specs.md section 6.4 (the write-guard clause) + the maintenance contract atop system/organism/manual.md. To change what is protected, change it THERE with sign-off, then update this guard and its registration in .claude/settings.json.\"}"
    ;;
esac

exit 0
