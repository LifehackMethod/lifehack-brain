#!/usr/bin/env python3
"""schema_v1.py — the register schema (v1), as data, not prose.

Feature B1.1 (enforcement-layer Phase 2 plan). This module is the single
source of truth `validate_register.py` reads. It is deliberately NOT a
jsonschema/YAML file — the repo has no such dependency today, and a plain
Python dict a human can read top-to-bottom is the same "files you can open
and fix by hand" instinct the plan's constraint 0.5 asks for, just typed.

See `schema-v1.md` in this folder for the field-by-field rationale. This
file states the RULES; that file explains WHY each one exists.

Every field's plain-language meaning belongs in schema-v1.md, never only
here as a comment — comments here drift, the doc is what a human opens.
"""

# ---------------------------------------------------------------------------
# Unit classes (B1.1 (a)) — the full set this schema covers.
# ---------------------------------------------------------------------------
UNIT_TYPES = ("hook", "tool", "skill", "scheduled", "githook")

# Closed enum: the six live surfaces T2 harvested from. A hook entry names
# every surface it is CURRENTLY registered on; B2's de-dup collapses these
# files later, but v1 only describes what is true today.
SURFACES = (
    "settings", "plugin", "registrations", "user",
    "cache-settings", "cache-plugin",
)

# ---------------------------------------------------------------------------
# launch_mode — RESTORED to schema v1, 2026-09-15 (Enver's Option G ruling,
# enforcement-layer Phase 2 build, "Discoveries" §"RULINGS ... third set").
# History: B1.1 first drafted this field to mean "which SESSION mode loads
# this unit" (clone-only vs plugin-enabled vs plugin-folder-as-cwd); Enver's
# first-set ruling that same day DROPPED it as premature — the session-mode
# question was still open pending D5/T3 (see the struck-through history in
# schema-v1.md). Option G gives it a narrower, now-answerable meaning
# instead: for one HOOK registration, which of the two real PUBLIC wiring
# FILES carries it — `.claude/settings.json` ("project") and/or
# `hooks/hooks.json` ("plugin"). Harvested MECHANICALLY from the row's own
# `surfaces` (harvest.py's `derive_launch_mode()`, reading `hook_surfaces()`'s
# own surface names) — 0 hand-typed values, same discipline as every other
# T2-proven field. Closed to exactly the four combinations the live register
# actually produces (verified 2026-09-15 against a fresh 319-row harvest, 63
# hook rows): "both" (registered on both public files) · "project" (settings
# file only) · "plugin" (plugin file only — includes the post-B2.2 de-dup'd
# `emit_harness_brief.sh`) · "private" (a private-repo hook, carried by
# `registrations` and/or `user` — the public project/plugin split doesn't
# apply to it; `repo` already says "private", this value only says "not on
# either public wiring file"). Cache mirrors (`cache-settings`/
# `cache-plugin`) never decide this axis on their own — every cache surface
# observed in the live register accompanies its real settings/plugin
# counterpart, so folding them in would never change an answer today; a
# cache-only row (no repo-owned backing file at all) is a content-divergence
# finding the generator's own cache-divergence check already surfaces
# separately, not this field's job.
LAUNCH_MODES = ("project", "plugin", "both", "private")

# hook.group — NEW field, B5.2 (enforcement-layer Phase 2 plan, PHASE B5 "the
# map pilot"). Nullable, OPEN vocabulary (same non-closed-enum reasoning as
# `needs`/`returns` above — a second pilot group next quarter must not force a
# schema migration): rows sharing one non-null `group` value collapse onto ONE
# generated wiring entry (`generate.py`'s `collapse_group_rows()`), pointed at
# a single small dispatcher script that runs each member's own body in its own
# isolated subshell, sequentially, preserving each member's own byte-for-byte
# output and its own fire-journal line.
#
# ⛔ LEAD'S BINDING CONDITION (Discoveries, 2026-09-15): `group` is legal ONLY
# on a hook row whose `event` is in GROUPABLE_HOOK_EVENTS below — HARD-REJECTED
# by validate_register.py on every other event, never left as a convention or
# a code comment. This is the mechanical form of plan constraint 0.5's
# "weakest guard wins": collapsing N rows into one dispatcher process means
# their exit codes and decisions become entangled — fine for an INJECT hook
# (never blocks, so there is no "decision" to entangle), but a single point of
# failure if it ever reached a row whose event CAN deny a tool call
# (PreToolUse and its subclasses, Stop/SubagentStop, or any guard). Closing
# this to a small, explicitly non-blocking allowlist makes that misuse
# structurally impossible to introduce by accident, rather than relying on
# someone remembering a rule.
GROUPABLE_HOOK_EVENTS = ("UserPromptSubmit", "SessionStart", "Notification")

# Closed enum: which checkout owns this unit's source. NOT the same axis as
# "surfaces" — the plugin cache is a derived surface, never a repo of record
# (constraint 0.5: "the plugin cache is platform-owned — the register
# accounts for it, never generates it").
REPOS = ("public", "private")

# hook.event — CLOSED enum (Enver's ruling, 2026-09-15; see schema-v1.md
# "Rulings" section). Two sources, unioned (the union equals the documented
# set below — every event this repo's own wiring uses is already in it):
#   1. THIS REPO'S WIRING — grepped 2026-09-15 from `.claude/settings.json`
#      and `hooks/hooks.json` for event keys under `"hooks": {...}`: 6 events
#      actually fire here today — PreToolUse, PostToolUse, UserPromptSubmit,
#      UserPromptExpansion, SessionStart, Stop.
#   2. THE DOCUMENTED SET — Claude Code "Hooks reference",
#      https://code.claude.com/docs/en/hooks (cross-linked from
#      https://code.claude.com/docs/en/hooks-guide), fetched 2026-09-15: the
#      full fixed set Claude Code itself supports, 33 events across three
#      handler-support tiers.
# Closing the enum to this documented set (not just the 6 wired today) means
# a hook this repo hasn't wired yet still validates — only a genuinely
# unknown/typo'd event name gets rejected.
HOOK_EVENTS = (
    # support all 5 handler types (command/http/mcp_tool/prompt/agent) — 13
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "PostToolBatch",
    "PermissionRequest", "PermissionDenied", "Stop", "SubagentStop",
    "TaskCreated", "TaskCompleted", "TeammateIdle", "UserPromptSubmit",
    "UserPromptExpansion",
    # command/http/mcp_tool only — 18
    "Notification", "MessageDisplay", "SubagentStart", "StopFailure",
    "PreCompact", "PostCompact", "PreModelSwitch", "PostModelSwitch",
    "Elicitation", "ElicitationResult", "ConfigChange", "CwdChanged",
    "DirectoryAdded", "FileChanged", "InstructionsLoaded",
    "WorktreeCreate", "WorktreeRemove", "SessionEnd",
    # command/mcp_tool only — 2
    "SessionStart", "Setup",
)

# scheduled.enabled — an open, DECLARED-disposition word per pulse-config.md
# ("yes" to run; anything else is a stated reason, not just "off"). Kept
# open for the same reason: closing it would freeze vocabulary a human
# still writes by hand in that file today.

# ---------------------------------------------------------------------------
# Field definitions.
# ---------------------------------------------------------------------------
# Each field: (python_type_or_tuple, nullable, extra) where `extra` is an
# optional validation hint consumed by validate_register.py:
#   ('enum', (...))       — value must be one of these
#   ('enum_list', (...))  — value is a list, each item must be one of these
#   ('list_of_str', None) — value is a list of strings, any content (chaining
#                           seed — B1.1 (c) — must never be closed to a fixed
#                           vocabulary, that would foreclose composition)
#   ('nonempty_list', enum_tuple_or_None) — list of length >= 1

COMMON_FIELDS = {
    # identity ---------------------------------------------------------
    "id":     (str,  False, None),
    "type":   (str,  False, ("enum", UNIT_TYPES)),
    "repo":   (str,  False, ("enum", REPOS)),
    "path":   (str,  False, None),

    # on-disk truth (T2-proven, mechanical) -----------------------------
    "exists": (bool, False, None),
    "sha":    (str,  True,  None),   # null iff exists is False

    # B1.1 (c) — chaining seed. Required keys, but an empty list is the
    # honest mechanical default (not a hand-annotation) until a unit
    # actually declares something.
    "needs":   (list, False, ("list_of_str", None)),
    "returns": (list, False, ("list_of_str", None)),

    # B1.1 (d) — cost fields, left empty until Phase B4 (the fire-journal)
    # fills them from real measurement. Never guessed, never zero-filled.
    "cost_bytes": ((int, float), True, None),
    "cost_ms":    ((int, float), True, None),
}

# Per-type additional required fields, layered on top of COMMON_FIELDS.
TYPE_FIELDS = {
    "hook": {
        "event":  (str,  False, ("enum", HOOK_EVENTS)),   # closed — see HOOK_EVENTS above
        "matcher": (str, False, None),   # may be ""
        "args":    (str, False, None),   # may be ""
        "status":  (str, False, None),   # may be ""
        "surfaces": (list, False, ("nonempty_list", SURFACES)),
        "status_conflicts": (list, False, ("list_of_str", None)),
        # Discovered live, B2.2 (2026-09-15): Claude Code's own hook-entry schema
        # carries an OPTIONAL "if" narrowing condition (e.g. "Skill(checkin)") that
        # T2/B1.1/B1.2/B1.3 never harvested — a real, pre-existing gap, not a new
        # capability being added on purpose. Required-but-nullable (schema-v1.md's
        # own convention: a missing KEY is always a reject; null means "no
        # condition on this entry", the honest default for every other hook row).
        # See schema-v1.md's "if" section for the incident this field closes.
        "if": (str, True, None),
        # RESTORED 2026-09-15 (Option G) — see the LAUNCH_MODES block above
        # for the full history and the ('enum', ...) closure's derivation.
        "launch_mode": (str, False, ("enum", LAUNCH_MODES)),
        # NEW 2026-09-15 (B5.2) — see the GROUPABLE_HOOK_EVENTS block above.
        # Required-but-nullable, same convention as "if": a missing KEY is
        # always a reject; null is the honest default for every row not in a
        # group. The event-allowlist cross-check lives in
        # validate_register.py (a single-field enum can't express "legal
        # combined with THIS OTHER field's value").
        "group": (str, True, None),
        # NEW 2026-09-16 (S1/K1) — the register-backed switch. Enver's stamped
        # binding constraint (system/journal.md, 2026-09-16): the hook-edit
        # protection's switch STATE and EXPIRY live IN THE REGISTER as data —
        # otherwise the on-commit drift gate reads the guard-rebuild lane's
        # local flip as drift and refuses their legitimate commits.
        #   "state":   "active" (DEFAULT — every student's row; generate.py
        #              emits the hook normally = protection ON) or "suspended"
        #              (generate.py OMITS the row from all generated wiring
        #              until `expiry` = protection OFF, declared, temporary).
        #   "expiry":  YYYY-MM-DD, required when state="suspended" (a
        #              suspension with no expiry is a permanent lift — the
        #              design's self-heal IS the expiry), must be null when
        #              state="active" (no ambiguous switches in the register).
        # The suspended⇔expiry cross-rules live in validate_register.py (same
        # pattern as `group` above); the honored/expired/active semantics live
        # in switch_state.py (this folder), shared by generate.py + harvest.py.
        "state": (str, False, ("enum", ("active", "suspended"))),
        "expiry": (str, True, None),
    },
    "tool": {
        "language": (str, False, ("enum", ("py", "sh", "other"))),
    },
    "skill": {
        "name":        (str, False, None),
        "description": (str, False, None),   # may be "" if frontmatter has none
    },
    "scheduled": {
        "schedule_name":    (str, False, None),
        "enabled":          (str, False, None),   # declared word, open vocab
        "interval_seconds": ((int,), True, None),
        "command":          (str, False, None),
    },
    # githook — NEW type, 2026-09-16 (K2, enforcement-layer Phase 2 plan, "the register's
    # git-hooks blind spot"). The register held ZERO rows for git hooks, so a tool invoked
    # ONLY by a local git hook (activated via `git config core.hooksPath system/githooks`,
    # never any of the six wiring surfaces the `hook` type above already covers) read as
    # UNCALLED to caller_lint.py — the incident that nearly retired `encoding_lint.py`
    # (system/journal.md, 2026-09-16: its only caller is `system/githooks/pre-commit`).
    # One row per git-hook SCRIPT (`system/githooks/pre-commit`, `system/githooks/pre-push`,
    # one per repo that has one) — NOT one row per invoked command, because a single git
    # hook fires many commands in one process, unlike pulse-config.md's one-job-per-line
    # `scheduled` shape above.
    #   "hook_name": the git-hooks filename itself (e.g. "pre-commit") — deliberately NOT
    #                called `event`, to keep this axis visually and semantically distinct
    #                from the `hook` type's Claude-Code-specific `event` enum (HOOK_EVENTS
    #                above); a git hook has no such concept.
    #   "commands":  the invocation-shaped lines harvest.py's `harvest_githooks()`
    #                mechanically extracts from the script's own body — never the whole
    #                file text (constraint 0.5: "the register stores identity + existence +
    #                a content hash, not full text"). caller_lint.py's `githook_evidence()`
    #                re-applies its own invocation-vs-mention judgment (`ref_kind()`) to
    #                each line before crediting a governed unit — harvest.py does the
    #                mechanical extraction, caller_lint.py keeps the judgment, same division
    #                of labor as every other evidence surface in that module.
    "githook": {
        "hook_name": (str, False, None),
        "commands":  (list, False, ("list_of_str", None)),
    },
}

# Fields the validator will accept overlapping across types but that must
# NEVER appear on a type that doesn't declare them — enforced by rejecting
# any key not in COMMON_FIELDS ∪ TYPE_FIELDS[row['type']]. Enver's ruling,
# 2026-09-15 (see schema-v1.md "Rulings" section): STRICT, permanently — the
# validator's error must name the offending key (see validate_register.py).
STRICT_UNKNOWN_KEYS = True


def fields_for(unit_type):
    """Return the full {field: (type, nullable, extra)} map for one type."""
    merged = dict(COMMON_FIELDS)
    merged.update(TYPE_FIELDS.get(unit_type, {}))
    return merged
