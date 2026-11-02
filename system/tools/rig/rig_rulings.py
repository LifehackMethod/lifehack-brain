#!/usr/bin/env python3
"""rig_rulings.py - person rulings that change how the rig SCORES a case (never how a guard behaves).

PUSH SCAN WARN MODE (Enver's ruling 2026-11-02; record <notes>/state/projects/v2/records/2026-11-02-push-scan-warn-mode.md):
  while system/hooks/roundB.conf says fc_private_push_mode=warn, a public-remote push the leakage scan flags is ALLOWED
  (warned, logged, reported at end of turn) instead of hard-stopped. The exam cases that expect that push to be STOPPED
  (Round D D-F15 / D-F16, and the replay cases that plant a leaky commit) are then scored
      "push scan in warn mode until launcher lanes: NOT-EVALUATED"
  -- never FAIL, never PASS, and out of the denominator. block mode (or no line) = scored as before.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "hooks", "lib"))
import roundb  # noqa: E402  (the one switch reader)

PUSH_WARN_TEXT = ("push scan in warn mode until launcher lanes: NOT-EVALUATED "
                  "(Enver's ruling 2026-11-02, records/2026-11-02-push-scan-warn-mode.md)")
PUSH_SCAN_CASES = ("D-F15", "D-F16", "fc-public-push-private", "fc-private-push-bash-c")

PLAIN_PUSH_TEXT = ("plain/local push quiet by design: NOT-EVALUATED "
        "(Enver's rulings 2026-10-30, commits e194370 + f166bd0; switches fc_plain_push_quiet / "
        "fc_local_push_quiet in system/hooks/roundB.conf — a plain tracked push, above all to a "
        "remote that is a folder on this same machine, draws no signpost on purpose)")
PLAIN_PUSH_CASES = ("n2-push-direct-bash", "n2-push-bash-heredoc", "n2-push-bash-script-file",
    "n2-push-one-line-script", "n2-push-git-C", "r-s46-compound-cd-push", "r-s46c-push-after-pipe",
    "fs-push-plain-push-cwd", "fs-push-cd-chain-pipe", "fs-push-cd-newline", "fs-push-git-C")


def push_scan_warn_mode():
    return roundb.roundb_on("fc_private_push") and roundb.roundb_val("fc_private_push_mode") == "warn"


def plain_push_quiet():
    """The replay fixture's remote is ALWAYS a local bare repo, so fc_local_push_quiet (the
    "a push to a folder on this same machine draws no signpost" ruling) is the ONE switch that
    governs these cases; fc_plain_push_quiet is the sibling ruling for non-local remotes and
    must not keep the ruling alive here when the local one is switched off."""
    return roundb.roundb_on("fc_local_push_quiet")


def not_evaluated(case_id):
    """-> the NOT-EVALUATED text for this case under a standing ruling, or None (score it as usual)."""
    if case_id in PUSH_SCAN_CASES and push_scan_warn_mode():
        return PUSH_WARN_TEXT
    if case_id in PLAIN_PUSH_CASES and plain_push_quiet():
        return PLAIN_PUSH_TEXT
    return None
