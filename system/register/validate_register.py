#!/usr/bin/env python3
"""validate_register.py — the schema v1 checker (Feature B1.1's "small validator").

Usage:
    python3 validate_register.py <path-to-register.jsonl> [--quiet]

Reads a JSONL register file (one JSON object per line — schema-v1.md), checks
every row against schema_v1.py, and prints a PASS/REJECT count. Exit code is
0 iff every row passed. Never mutates its input; never guesses a missing
value into existence.

This is the instrument Feature B1.1's Verify names — it must itself be shown
passing known-good input AND failing known-bad input (the collapse rule,
plan §0.1 rule 3) before its verdict counts for anything downstream.
"""
import json
import re
import sys
from datetime import date

from schema_v1 import fields_for, UNIT_TYPES, STRICT_UNKNOWN_KEYS, GROUPABLE_HOOK_EVENTS

# S1/K1 (2026-09-16): the register-backed switch's expiry shape. Date REALITY
# (2026-02-31 is a reject, not a suspension) is checked with fromisoformat in
# validate_row(); this regex only anchors the YYYY-MM-DD shape first.
EXPIRY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _isinstance_strict(value, expected_type):
    """isinstance(), but a bool never satisfies an int/float/(int,) check —
    Python's `bool` is a subclass of `int` and would otherwise sneak past
    a numeric field (cost_ms: true would validate as a number)."""
    numeric_types = (int, float)
    is_numeric_check = expected_type == numeric_types or expected_type in (int, float, (int,))
    if is_numeric_check and isinstance(value, bool):
        return False
    return isinstance(value, expected_type)


def _real_date(value):
    """YYYY-MM-DD-shaped string -> is it a date that actually exists?
    date.fromisoformat raises on 2026-02-31-shaped impossibilities; the shape
    itself is anchored by EXPIRY_RE before this is ever called."""
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_row(row, line_no):
    """Return a list of error strings; empty list means the row is valid."""
    errors = []

    if not isinstance(row, dict):
        return [f"line {line_no}: row is not a JSON object"]

    unit_type = row.get("type")
    if unit_type not in UNIT_TYPES:
        errors.append(f"line {line_no}: 'type' is {unit_type!r}, must be one of {UNIT_TYPES}")
        return errors  # can't check type-specific fields without a valid type

    schema = fields_for(unit_type)

    # 1. every required (or nullable-but-present) field must be present.
    for field, (ftype, nullable, extra) in schema.items():
        if field not in row:
            errors.append(f"line {line_no}: missing required field {field!r} (type={unit_type})")
            continue
        value = row[field]
        if value is None:
            if not nullable:
                errors.append(f"line {line_no}: field {field!r} is null but is not nullable")
            continue
        # basic type check
        if not _isinstance_strict(value, ftype):
            errors.append(f"line {line_no}: field {field!r} must be {ftype}, got {type(value).__name__}")
            continue
        # extra validation hints
        if extra:
            kind = extra[0]
            if kind == "enum":
                allowed = extra[1]
                if value not in allowed:
                    errors.append(f"line {line_no}: field {field!r}={value!r} not in {allowed}")
            elif kind == "enum_list":
                allowed = extra[1]
                bad = [v for v in value if v not in allowed]
                if bad:
                    errors.append(f"line {line_no}: field {field!r} has values outside {allowed}: {bad}")
            elif kind == "nonempty_list":
                allowed = extra[1]
                if len(value) < 1:
                    errors.append(f"line {line_no}: field {field!r} must be a non-empty list")
                if allowed:
                    bad = [v for v in value if v not in allowed]
                    if bad:
                        errors.append(f"line {line_no}: field {field!r} has values outside {allowed}: {bad}")
            elif kind == "list_of_str":
                bad = [v for v in value if not isinstance(v, str)]
                if bad:
                    errors.append(f"line {line_no}: field {field!r} must be a list of strings")

    # 2. cross-field constraint: exists=False <=> sha is None (T2's own rule).
    if row.get("exists") is False and row.get("sha") is not None:
        errors.append(f"line {line_no}: exists=False but sha is not null")
    if row.get("exists") is True and row.get("type") in ("hook", "tool", "skill", "githook") and row.get("sha") is None:
        # scheduled rows have no single backing file, so this constraint is
        # hook/tool/skill/githook only (see schema-v1.md). A githook row DOES
        # have one backing file (one row per git-hook script, K2, 2026-09-16),
        # same one-row-one-file shape as hook/tool/skill above.
        errors.append(f"line {line_no}: exists=True but sha is null")

    # 3. cross-field constraint: `group` (B5.2) is legal ONLY on a hook row
    #    whose event structurally cannot block a tool call (schema_v1's
    #    GROUPABLE_HOOK_EVENTS). HARD REJECT, never a WARN — the lead's
    #    binding condition for B5.2: collapsing rows into one dispatcher
    #    process must never be reachable for a row whose exit code can deny
    #    something (PreToolUse and its subclasses, Stop/SubagentStop, any
    #    guard). This is enforced HERE (not as a per-field enum in
    #    schema_v1.py) because it depends on a SECOND field's value, which a
    #    single-field ('enum', ...) hint cannot express.
    if row.get("type") == "hook" and row.get("group") is not None:
        event = row.get("event")
        if event not in GROUPABLE_HOOK_EVENTS:
            errors.append(
                f"line {line_no}: field 'group'={row.get('group')!r} is set on "
                f"event={event!r}, but 'group' is only legal on "
                f"{GROUPABLE_HOOK_EVENTS} — a blocking-capable event's row must "
                f"never be merged into a shared dispatcher (constraint 0.5, "
                f"'weakest guard wins')"
            )

    # 4. cross-field constraint: the register-backed switch (S1/K1, 2026-09-16 —
    #    Enver's stamped binding constraint: the hook-edit protection's switch
    #    STATE and EXPIRY live in the register as data). state="suspended"
    #    REQUIRES a valid, real YYYY-MM-DD `expiry`: a suspension with no
    #    expiry is a permanent lift, and the design's whole point is that a
    #    forgotten switch self-heals AT its expiry. state="active" requires
    #    expiry null: an active row carrying a date is an ambiguous switch,
    #    and the register never stores ambiguity. HARD REJECT, like `group`
    #    above — never a WARN.
    if row.get("type") == "hook":
        state = row.get("state")
        expiry = row.get("expiry")
        if state == "suspended":
            if expiry is None:
                errors.append(
                    f"line {line_no}: state='suspended' but 'expiry' is null — a "
                    "suspension with no expiry is a permanent lift, which S1 "
                    "forbids (the self-heal IS the expiry)"
                )
            elif not EXPIRY_RE.match(expiry) or not _real_date(expiry):
                errors.append(
                    f"line {line_no}: 'expiry'={expiry!r} is not a real "
                    "YYYY-MM-DD date (required when state='suspended')"
                )
        elif state == "active" and expiry is not None:
            errors.append(
                f"line {line_no}: state='active' but 'expiry'={expiry!r} — an "
                "active row carries expiry=null; the register never stores an "
                "ambiguous switch"
            )

    # 5. no unregistered fields — "encode only what has already converged"
    #    (constraint 0.5): a stray key is either dead weight or an
    #    un-ruled extension, and either way it doesn't belong in v1 silently.
    if STRICT_UNKNOWN_KEYS:
        allowed_keys = set(schema.keys())
        unknown = set(row.keys()) - allowed_keys
        if unknown:
            errors.append(f"line {line_no}: unknown field(s) not in schema v1: {sorted(unknown)}")

    return errors


def validate_file(path):
    passed, rejected = [], []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                rejected.append((i, [f"line {i}: invalid JSON ({e})"]))
                continue
            errs = validate_row(row, i)
            if errs:
                rejected.append((i, errs))
            else:
                passed.append(i)
    return passed, rejected


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    path = sys.argv[1]
    quiet = "--quiet" in sys.argv
    passed, rejected = validate_file(path)
    print(f"validate_register.py v1 — {path}")
    print(f"rows checked: {len(passed) + len(rejected)}  PASS: {len(passed)}  REJECT: {len(rejected)}")
    if rejected and not quiet:
        print("\nrejections:")
        for line_no, errs in rejected:
            for e in errs:
                print(f"  {e}")
    sys.exit(0 if not rejected else 1)


if __name__ == "__main__":
    main()
