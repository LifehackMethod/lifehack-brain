#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: WEEKLY structural audit leg of the Standing Archivist. Fires a read-only headless
#      `claude -p` that walks the whole notes tree per `.claude/skills/archivist-audit/SKILL.md`,
#      writes an audit log (+ a proposals file only if there's something actionable) and a JSON
#      summary sidecar, then the shared lib writes the status tile and pings.
# GUARDS: read-only forever; exits 0 EVEN when it finds drift (non-zero = tool broke -> Pulse
#      auto-disables after 3). Lock+watchdog-bounded (1800s).
# REDIRECT: registered as `archivist-audit` in system/pulse-config.md (interval 604800 = weekly).
#      Findings flow to the next /save (main session, human-gated) — the skill's own doc: "there
#      is no /archivist-review... the scanner just FLAGS, and the next /save picks it up."
#      Shared machinery: system/tools/archivist-run.lib.sh.
#
# ⚖ PORT NOTE (donor: system/tools/archivist-audit-run.sh): the Drive-upload / tappable-link /
# hardcoded folder-id machinery is dropped — see archivist-run.lib.sh's own port note. Output
# paths follow `.claude/skills/archivist-audit/SKILL.md`'s OWN documented contract
# (`<notes>/records/logs/` + `<notes>/records/proposals/`), not the donor's `system/logs/` path.
# Territory-map regen (SKILL.md check 8, `<notes>/system/canon-purpose-map.md`) is left to the
# skill's own text, which already names it the ORCHESTRATOR's write, not the subagent's — this
# runner does not additionally instruct it or forbid it; it defers entirely to the skill file.
# ─────────────────────────────────────────────────────────────────────────────
set -u
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
DATESTAMP="$(date +%F)"

ARCH_MODE="audit"
ARCH_LABEL="archivist-audit"
ARCH_WATCHDOG=1800
ARCH_PING_TITLE="Archivist — weekly audit"
ARCH_QUEUE_FILE="${DATA:+$DATA/records/logs/archivist-${DATESTAMP}-audit.md}"
ARCH_SUMMARY_FILE="${DATA:+$DATA/system/logs/archivist_${DATESTAMP}_audit.summary.json}"

ARCH_PROMPT="Your notes root is: $DATA
You are the Standing Archivist, running HEADLESS and UNATTENDED on a weekly cadence. You are READ-ONLY ON THE SYSTEM: you DETECT and PROPOSE — you NEVER fix, move, rename, or delete anything.
Read and follow $CODE_ROOT/.claude/skills/archivist-audit/SKILL.md exactly (it is delegated to the pinned read-only \`.claude/agents/archivist.md\` subagent — Read/Grep/Glob only). Resolve every '<notes>' path in that skill against the root above. Run the FULL audit (no scope filter) — every check the skill lists as surviving (it documents which of the donor's checks were removed and why; do not attempt those).

WRITE:
1) The audit log (markdown) → $ARCH_QUEUE_FILE
   Group findings SAFEST-FIRST: PROMOTE, then ROUTE/REFILE, then SCOPE, then DELETE. One line per finding: check name · path · proposed action · risk(low|med|high) · reversible(y/n) · dep-gate(n/a|clear|BLOCKED). Lead with a one-line count-by-group summary. If the tree is clean, say so plainly.
2) If (and only if) there is something actionable, ALSO write the proposals file the skill documents at <notes>/records/proposals/archivist-${DATESTAMP}-audit.md (frontmatter record_type: proposal) — a person rules on it at their next /save.
3) A machine-readable summary sidecar (JSON, one object) → $ARCH_SUMMARY_FILE
   EXACTLY: {\"status\":\"OK\"|\"NEEDS_REVIEW\",\"finding_count\":<integer>,\"headline\":\"<=8 word teaser\"}
   Use status OK with finding_count 0 ONLY if the tree is genuinely clean; otherwise NEEDS_REVIEW with the true count and a short headline.

Do NOT send any notification — the runner pings deterministically from the summary sidecar above. Do not touch any file outside the ones named here plus whatever the skill's own check 8 (territory-map regenerate) names."

# shellcheck source=/dev/null
source "$CODE_ROOT/system/tools/archivist-run.lib.sh"
run_archivist
exit $?
