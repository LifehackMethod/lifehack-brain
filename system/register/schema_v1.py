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
UNIT_TYPES = ("hook", "tool", "skill", "scheduled")

# Closed enum: the six live surfaces T2 harvested from. A hook entry names
# every surface it is CURRENTLY registered on; B2's de-dup collapses these
# files later, but v1 only describes what is true today.
SURFACES = (
    "settings", "plugin", "registrations", "user",
    "cache-settings", "cache-plugin",
)

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
