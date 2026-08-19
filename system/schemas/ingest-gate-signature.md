---
id: root-schema-ingest-gate-signature
title: "Ingest Gate — frozen call signature (v1.0)"
record_type: schema
created_at: 2026-06-19
updated_at: 2026-08-15
status: active
authority: user
owners: [ingest-gate]
note: >
  The frozen call signature `shared/gate/ingest_gate.py` implements. PORTED (T9.7b) from
  claudeops-config, where this doc was a docstring-only dangle — cited by the implementation's
  module docstring but never shipped, since claudeops-config never migrated its own schema
  folder for it. Repointed here to the paths this repo actually has: the desk/sentinel-event
  wiring below describes `shared/gate/sentinel_response.py`, not a multi-desk model this
  product doesn't have (see `backlog_groom.py`'s own note on that). Implementation may evolve;
  this signature does not change without a schema_version bump.
---

# Ingest Gate — Frozen Call Signature (v1.0)

> **Frozen interface.** `shared/gate/ingest_gate.py` implements this exact signature — see its own
> module docstring, which cites this file back. The implementation evolves; the frozen call
> contract does not.

**schema_version: "1.0"**

---

## The hole this seals

Each inbound channel used to wire its own sanitize → scan → route path independently, and email
never routed injection findings to the Sentinel verdict path at all — flags were logged to stderr
only, visible in a terminal but invisible to the alarm. The gate makes every external read pass
through **one on-path entry point** that sanitizes, tags provenance, and routes findings to
Sentinel — so coverage is mechanical, not opt-in. See `shared/gate/ingest_gate.py`'s own docstring
("WHY") for the full account.

---

## Frozen signature

```python
def gate(
    desk_id: str,          # the consuming identity (a desk_id where a desk-registry.yaml exists;
                            # otherwise this product's single-user identity string)
    source_type: str,      # "email" | "web" | "file" | "calendar" | "api"
    raw_content: str,      # the unsanitized external content to screen
    message_id: str = "",  # Gmail message id — unlocks quarantine on DANGER (pass "" for non-Gmail)
    item: str = "",        # short human-readable identifier for the Sentinel event log
) -> dict:
    """
    Returns:
      {
        "content":        str,   # sanitized content ("" on DANGER)
        "provenance_tag": str,   # "{desk_id}/{source_type}/{sha256_8}" — tamper-evident (not a secret)
        "passed":         bool,  # True = FLAG or CLEAN (caller continues); False = DANGER (caller HALTS)
      }
    On DANGER (passed=False, non-email only — see the locked email invariant below): Sentinel has
    ALREADY logged + pushed + paused the source. The caller MUST NOT process the item and MUST NOT
    re-call gate() for it.
    """
```

Implemented at `shared/gate/ingest_gate.py:gate()`.

---

## Field mapping (a thin wrapper, not a reinvention)

| Gate parameter | Maps to existing tool/arg | Notes |
|---|---|---|
| `desk_id` | `sentinel_response.py --source` | The consuming identity string. |
| `source_type` | one of `email\|web\|file\|calendar\|api` | Load-bearing for provenance + the email FLAG-floor. |
| `raw_content` | — | Sanitized by `system/tools/sanitize.py`; scanned by `system/tools/safe_input.py` — both run INSIDE the gate. |
| `message_id` | `sentinel_response.py --message-id` | Unlocks the Gmail quarantine path; ignored (never passed) for email sources. |
| `item` | `sentinel_response.py --item` | Short id/subject for the event log, truncated to 120 chars. |

---

## `provenance_tag` format

```
{desk_id}/{source_type}/{sha256_8}
```
e.g. `me/email/a3f1c8b2` — `sha256_8` = first 8 hex of SHA-256 of the RAW (pre-sanitize)
`raw_content`, so the tag witnesses exactly what was screened. Tamper-evident, not a secret.
Written to the coverage breadcrumb ledger (`PROVENANCE_LOG`, resolved under the brain root via
`shared/brain_root.py`) alongside the verdict — see `_breadcrumb()` in the implementation.

---

## Implementation contract

1. `sanitize(raw_content)` → stripped text (`system/tools/sanitize.py`, uncapped via `NO_CAP`).
2. `scan_for_injection(clean)` → `[[match, label], …]` (`system/tools/safe_input.py`).
3. No findings → CLEAN: the verdict tool is never called (no event, no subprocess); a `clean`
   coverage breadcrumb is still written so a desk that only ever reads clean content shows as
   covered rather than false-flagging a gap.
4. Findings present → pipe them as JSON to `sentinel_response.py --source {desk_id} --item {item}
   --provenance {tag}` (`--message-id` added for non-email when given; `--flag-only` added for
   email — the locked invariant below).
5. Verdict tool exit 2 (DANGER, non-email only) → `{"content": "", "provenance_tag": tag,
   "passed": False}`.
6. Otherwise (FLAG/CLEAN) → `{"content": clean, "provenance_tag": tag, "passed": True}`.

**Posture-controlled since the implementation's own Window 5 cutover** (`INGEST_GATE_POSTURE`,
default `"enforce"`): on an internal error, a non-email read that can't be gated is DENIED
(fail-closed); email always fails open (it is FLAG-floored and can never DANGER, so failing it
open removes zero containment). `INGEST_GATE_POSTURE=warn` reverts every channel to fail-open —
the instant-revert lever if enforcement ever regresses a live read. The gate **never raises**
regardless of posture; see `gate()`'s own docstring for the exact except-branch behavior.

---

## Locked email invariant (never split from the wire-up commit)

When `source_type == "email"`, findings are constrained to **FLAG, never DANGER**, until a
provenance-aware classifier ships. This prevents a base64 attachment or a security-newsletter
snippet from triggering DANGER and quarantining real mail. The gate enforces it by passing
`--flag-only` to the verdict tool and never returning `passed=False` for email. **This clause is
part of the frozen contract — relaxing it requires a schema_version bump.** (Wiring email to the
alarm WITHOUT this constraint would trade a silent false-negative for an auto-quarantine of real
mail — strictly worse than not gating email at all.)

---

## Wiring

Callers go through `shared/gate/ingest_gate.py` directly (Python `import` + `gate(...)`) or via its
CLI (`python3 shared/gate/ingest_gate.py --desk <id> --source-type <type> [--item ...]
[--message-id ...]`, raw content on stdin, verdict dict as JSON on stdout, exit 0/2 mirroring the
verdict tool's own convention). There is no separate `ingest-run.lib.sh` shim in this repo — the
gate module itself is the on-path entry point every channel calls.
