#!/usr/bin/env python3
"""identity_secret_drift_check.py — one-fact preflight nudge for the /ship lane.

WHY THIS EXISTS. `<notes>/config/ship-identity.md` (the local, `authority: user` ruling on
what counts as personal identity) and the GitHub Actions secret `SHIP_IDENTITY_TERMS` (what
actually gates every public CI run) are two independently hand-maintained stores with no
sync between them. GitHub secrets are provably write-only (no read path exists), so no
checker can ever confirm their CONTENTS agree — only whether the secret was touched more
recently than the local file was last edited. That is the one honest, content-free signal
available, and this script produces exactly that signal and nothing more.

WHAT THIS IS NOT. This is not a scheduled watcher and it does not run unattended. It is
meant to be called from the ONE place a human is already looking at this decision — the
`/ship` skill's Step 0 preflight, which already reads the identity file to compose the
lane's rule set. Bolting a second, separate always-on watcher onto two already-drifting
hand-maintained stores is the exact shape CLAUDE.md's anti-spiral rule forbids (a third
part whose only job is checking the other two). This script is not that third part — it is
a one-line addition to the existing first step, using facts that step already needs.

FOUR OUTCOMES, NEVER FOLDED TOGETHER (mirrors system/hooks/tests/verify-pm-guard.sh's
ABSENT-SUBJECT pattern: a checker that cannot reach its subject says so as its own outcome,
never as a silent pass):

  OK             (exit 0) — local file's mtime is NOT after the secret's updated_at.
                             No evidence of drift. (Not a positive proof of agreement --
                             content can never be read -- only an absence of the one signal
                             this script can see.)
  DRIFT          (exit 1) — local file was edited AFTER the secret was last touched. The
                             ruling may not be reflected in what CI actually gates.
  ABSENT-SUBJECT (exit 2) — the local identity file could not be found/read. There is
                             nothing to compare. This is NOT "OK" and NOT "DRIFT".
  CANNOT-CHECK   (exit 3) — the secret's metadata could not be fetched (gh missing, not
                             authenticated, network down, secret renamed/deleted, malformed
                             response). There is nothing to compare against. This is NOT
                             "OK" and NOT "DRIFT" either -- a failed check must never read
                             as a clean one.

NEVER prints the identity file's contents, term count, or the secret's value -- only
timestamps and the verdict. This mirrors the workflow's own stated principle ("a count is a
small fact about a private list, and this log is public").

USAGE
    identity_secret_drift_check.py [--identity-file PATH] [--repo OWNER/NAME]
                                    [--secret-name NAME] [--quiet]

    Exit code IS the outcome (0/1/2/3 as above) -- a caller (e.g. /ship Step 0) can branch
    on it without parsing output. --quiet suppresses the human-readable line and prints
    only the outcome word, for scripting.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

DEFAULT_REPO = "LifehackMethod/lifehack-brain"
DEFAULT_SECRET_NAME = "SHIP_IDENTITY_TERMS"

OK = 0
DRIFT = 1
ABSENT_SUBJECT = 2
CANNOT_CHECK = 3

OUTCOME_WORDS = {OK: "OK", DRIFT: "DRIFT", ABSENT_SUBJECT: "ABSENT-SUBJECT", CANNOT_CHECK: "CANNOT-CHECK"}


def resolve_identity_file(explicit):
    """Return the identity file path to check, or None if it cannot be resolved/found.

    Mirrors identity_rules.py's own resolution order (env var, then <notes>/config/...)
    but never reads the file's CONTENT -- only needs its existence + mtime.
    """
    if explicit:
        return explicit if os.path.isfile(explicit) else None

    env_path = os.environ.get("SHIP_IDENTITY")
    if env_path:
        return env_path if os.path.isfile(env_path) else None

    # Resolve <notes-root> the same way the rest of this repo does: shared/brain_root.py.
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if repo_root.returncode != 0:
        return None
    root = repo_root.stdout.strip()
    brain_root_script = os.path.join(root, "shared", "brain_root.py")
    if not os.path.isfile(brain_root_script):
        return None
    proc = subprocess.run(
        [sys.executable, brain_root_script], capture_output=True, text=True
    )
    if proc.returncode != 0 or "RESOLVED:" not in proc.stdout:
        return None
    notes_root = proc.stdout.split("RESOLVED:", 1)[1].split("(source:", 1)[0].strip()
    if not notes_root:
        return None
    candidate = os.path.join(notes_root, "config", "ship-identity.md")
    return candidate if os.path.isfile(candidate) else None


def fetch_secret_updated_at(repo, secret_name):
    """Return the secret's updated_at as a tz-aware datetime, or None on any failure.

    Deliberately treats EVERY failure mode the same way (returns None) -- gh missing,
    not authenticated, network down, secret not found, malformed JSON -- because the
    caller only needs to know "can I trust a comparison right now", not why not.
    """
    if shutil.which("gh") is None:
        return None
    try:
        proc = subprocess.run(
            ["gh", "api", "repos/%s/actions/secrets/%s" % (repo, secret_name)],
            capture_output=True, text=True, timeout=20,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
        raw = data["updated_at"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def local_mtime(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path), tz=datetime.timezone.utc)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--identity-file", help="override the identity file path")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="owner/name (default: %s)" % DEFAULT_REPO)
    ap.add_argument("--secret-name", default=DEFAULT_SECRET_NAME,
                     help="default: %s" % DEFAULT_SECRET_NAME)
    ap.add_argument("--quiet", action="store_true", help="print only the outcome word")
    args = ap.parse_args(argv)

    path = resolve_identity_file(args.identity_file)
    if path is None:
        outcome = ABSENT_SUBJECT
        if not args.quiet:
            print("ABSENT-SUBJECT -- could not find/read the local identity file.")
            print("  Nothing was compared. This is not a pass. See the /ship skill's")
            print("  \"FIRST RUN\" section for how to create it.")
        else:
            print(OUTCOME_WORDS[outcome])
        return outcome

    secret_updated_at = fetch_secret_updated_at(args.repo, args.secret_name)
    if secret_updated_at is None:
        outcome = CANNOT_CHECK
        if not args.quiet:
            print("CANNOT-CHECK -- could not fetch %s's metadata for %s." % (args.secret_name, args.repo))
            print("  (gh missing, not authenticated, network down, or secret renamed/deleted.)")
            print("  Nothing was compared. This is not a pass -- ship with this fact in mind,")
            print("  or re-run once you can reach the GitHub API.")
        else:
            print(OUTCOME_WORDS[outcome])
        return outcome

    file_mtime = local_mtime(path)
    if file_mtime > secret_updated_at:
        outcome = DRIFT
        if not args.quiet:
            print("DRIFT -- the local identity file was edited AFTER the CI secret was last touched.")
            print("  local file mtime:      %s" % file_mtime.isoformat())
            print("  secret last updated:   %s" % secret_updated_at.isoformat())
            print("  Update the %s secret (Settings -> Secrets and variables -> Actions)" % args.secret_name)
            print("  to match the local file before shipping publicly -- content cannot be")
            print("  verified from here (GitHub secrets are write-only), only this timing signal.")
        else:
            print(OUTCOME_WORDS[outcome])
        return outcome

    outcome = OK
    if not args.quiet:
        print("OK -- no evidence of drift (secret touched at/after the local file's last edit).")
        print("  local file mtime:      %s" % file_mtime.isoformat())
        print("  secret last updated:   %s" % secret_updated_at.isoformat())
        print("  (This does not prove the CONTENTS match -- only that no edit-after-secret-update")
        print("  window is currently open.)")
    else:
        print(OUTCOME_WORDS[outcome])
    return outcome


if __name__ == "__main__":
    sys.exit(main())
