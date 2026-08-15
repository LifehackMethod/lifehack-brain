#!/usr/bin/env python3
"""email_service_contract.py — Single Source of Truth for email-ingestion decisions (ENF-A).

This module is the BINDING CONTRACT for the ClaudeOps Email Summary service.  Every operational
constant that governs how email is ingested, which model summarizes it, and who is allowed to
touch Gmail is declared HERE and only here.  The janitor (email_summary_sync.py) imports these
constants at startup; if the import fails it hard-stops.

═══════════════════════════════════════════════════════════════════════════════
  CONSTANT       VALUE                            RATIONALE + EVIDENCE
═══════════════════════════════════════════════════════════════════════════════

  SUMMARY_MODEL  claude-haiku-4-5-20251001        internal A/B test 2026-05-07:
                                                   Haiku matched Sonnet output
                                                   quality 100% on sanitized
                                                   email text; ~4x cheaper.
                                                   Injection-safety is upstream
                                                   (ingest_gate), not the model.
                                                   Locked to the specific dated
                                                   version slug for reproducibility.

  MAX_WORKERS    5                                 internal scale-up 2026-05-08:
                                                   10 workers hit Gmail rate
                                                   limits; 5 is reliable on
                                                   CLEAN text only.  Never raise
                                                   without a new load test.

  EXTRACTION_METHOD  first+stripped-last           internal corpus analysis 2026-05-07:
                                                   93% of last-message body is
                                                   boilerplate (footers, quoted
                                                   chains).  first+stripped-last
                                                   removes it before the claude
                                                   -p call.  Locked.

  CONVERTER      email_convert.py                 The universal email converter.
                                                   Desk-specific prompt is injected
                                                   at call-site; the binary is the
                                                   canonical safe body path.

  SERVICE_ENTRYPOINT email_summary_sync.py        The ONLY file that may touch
                                                   Gmail (gws gmail / threads API).
                                                   validate_contract() greps the
                                                   whole tree at runtime and
                                                   hard-stops on any violation.

═══════════════════════════════════════════════════════════════════════════════

⚠  TO CHANGE ANY CONSTANT: edit THIS file and get the operator's explicit sign-off.
   Do NOT edit inline in email_summary_sync.py or anywhere else.
   The janitor hard-stops (DEGRADED tile) if its running code drifts from
   these constants — drift is a contract violation, not a configuration choice.

"""

# ENF-A.1 — model pinned to the Haiku version that A/B-matched Sonnet at 4x lower cost
# (internal scale-up 2026-05-07/08).  The dated slug pins the exact release so a new model
# release cannot silently change behaviour.  Injection-safety lives in ingest_gate upstream.
SUMMARY_MODEL = "claude-haiku-4-5-20251001"

# ENF-A.2 — parallel worker count ceiling.  10 workers hit Gmail rate limits in the internal
# scale-up (2026-05-08); 5 is the proven safe ceiling.  Haiku is reliable on CLEAN text only
# (ingest_gate filters before the pool starts).
MAX_WORKERS = 5

# ENF-A.3 — body extraction method locked after internal corpus analysis (2026-05-07):
# 93% of the last message is quoted chain / signature boilerplate.  first+stripped-last
# removes it before any call to claude -p, reducing token spend and injection surface.
EXTRACTION_METHOD = "first+stripped-last"

# ENF-A.4 — the universal email converter script name.  Desk-specific prompts are injected
# at call-site (email_summary_sync.py → run_email_convert()).
CONVERTER = "email_convert.py"

# ENF-A.5 — the ONLY code allowed to call Gmail APIs (gws gmail, threads.get, etc.).
# validate_contract() greps the whole shared/tools + system/tools + desks tree at runtime
# and hard-stops if any OTHER file contains Gmail-access patterns.
SERVICE_ENTRYPOINT = "email_summary_sync.py"

# ENF-A.6 — additional sanctioned Gmail accessor (the body converter; called BY the entrypoint,
# not a standalone Gmail caller — but it legitimately contains Gmail-API strings in comments).
CONVERTER_SANCTIONED = "email_convert.py"

# ENF-A.7 — sanctioned METADATA-ONLY Gmail readers.  Files listed here read Gmail METADATA ONLY
# (Subject/From/Date fields, never message bodies) and are invoked on-demand/interactively — NOT on
# a schedule.  This is a PERMANENT exception class, not a migration target; these files are doing
# the right thing (metadata-only) and will NOT be migrated to the Email Service.
#
# Current members:
#   planning-light-sweep.py — reads Gmail thread/message metadata (Subject/From/Date) to populate the
#                        planning-daily inbox-at-a-glance tile; invoked interactively from
#                        planning-daily, never from a cron.  Body content never touches this script.
#
# ⚠ THIS TUPLE IS KEYED ON A FILENAME. Renaming the file on disk without renaming it here silently
# un-sanctions it: validate_contract()'s ENF-B.3 grep then reports the (unchanged, still-correct)
# script as a Gmail-access violation. Renamed 2026-08-15 with the cal desk → planning desk rename;
# the old basename is kept below so a not-yet-pulled machine still validates.
#
# TO CHANGE: edit this tuple + get the operator's explicit sign-off (match the change-control posture
# above for all ENF-A constants).
GMAIL_METADATA_ALLOWED = ("planning-light-sweep.py", "cal-light-sweep.py")
