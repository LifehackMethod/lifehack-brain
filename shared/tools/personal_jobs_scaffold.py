#!/usr/bin/env python3
"""personal_jobs_scaffold.py -- make the places YOUR scheduled jobs are saved, in your own folder, never overwriting.

WHY: a plugin update replaces the plugin folder, so a job of yours saved inside it is lost. Your jobs live in your
personal code folder (shared/personal_code_root.py). This creates each piece that is missing, with a short template,
and leaves every piece that already exists exactly as it is (an existing file is never opened for writing).

Pieces (relative to your personal code folder):
  jobs.md                     your job rows (read by shared/jobs_manifest.py)
  job-fetch-hosts.txt         websites your jobs may read (added to the plugin's list by system/tools/job-run.sh)
  vendor-read-allowlist.txt   your vendor-read lines (read by the install door, install-schedulers.sh rule (f))
  job-sim/README.txt          how to override a generated test receipt (job-sim/<job>.json)
  tools/                      job code goes in tools/<job>/ (the door allows runners under your folder)
  JOBS-README.txt             one page: what goes where

Usage:
  personal_jobs_scaffold.py [FOLDER]   FOLDER defaults to the resolved personal code folder; it must already exist
                                       (python3 system/tools/bootstrap.py makes it). Prints created / skipped lines.
Safe to run again: the second run creates nothing. Exit 0 ok, 1 when there is no folder to scaffold.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import personal_code_root  # noqa: E402

JOBS_MD = """# My scheduled jobs

One row per job, inside the block below, nine columns separated by ` | `:
  name | enabled | interval | outcome | check | model | budget | source | command
`command` is last because it may contain `|`; no other column may. The meaning of each column, how to add a row,
and how to bring a job into line is in the plugin's `system/sops/cron-jobs-sop.md`. Plain names for your jobs go in
`job-names.txt` here (`<job> = <plain name>` lines). To change a plugin job, copy it under a NEW name: the copy is yours and the plugin does not support it. A row with a plugin job's own name replacing it is not the way. A broken plugin job is reported (the plugin's GitHub issues, or system/sops/pr-sop.md once it exists).

```jobs
```
"""

HOSTS = """# job-fetch-hosts.txt -- websites YOUR scheduled jobs may read. One host per line, `#` for comments.
# These are ADDED to the plugin's own list (system/tools/job-fetch-hosts.txt); the plugin's list is never replaced.
# A job can only read a site that is on one of the two lists. Add a host here on purpose.
"""

VENDOR = """# vendor-read-allowlist.txt -- vendor reads the install door allows for YOUR jobs (rule (f)).
# One line per job: `<job> <file>`. <file> is relative to the job's folder under tools/: it matches a script whose
# path ends in /tools/<job>/<file>. Applies only while the row's model column is exactly `none`, and only to python
# requests/urllib. Gmail reads and the web-fetch tools are never a vendor read. Empty means nothing is exempted.
"""

JOBSIM = """job-sim/ -- optional test-receipt overrides for your jobs.

The test rig (system/tools/tests/job-sim.sh) builds a test receipt for each of your rows by itself. Only if the
generated lines or the model-call count do not fit a job, add `job-sim/<job>.json` here:

  {"good": "a receipt line that must pass the check", "bad": "a line that must fail it", "calls": 0}

Give only the keys you want to replace. A file that is not JSON, has wrong types or an unknown key is reported as a
named failure. The real job never runs in the rig.
"""

README = """Your scheduled jobs: what goes where (this folder is yours; a plugin update never touches it)

  jobs.md                     your job rows. Format and columns: the plugin's system/sops/cron-jobs-sop.md
  job-names.txt               optional plain names, `<job> = <plain name>` per line
  job-fetch-hosts.txt         websites your jobs may read, one host per line (added to the plugin's list)
  vendor-read-allowlist.txt   `<job> <file>` lines for vendor reads (only for jobs with model none)
  tools/<job>/                the code of each job; a row's command points at a script here
  job-sim/<job>.json          optional override of the generated test receipt (see job-sim/README.txt)

This file and the others were made by personal_jobs_scaffold.py. It only ever creates what is missing, so you can
edit everything here freely and run it again.
"""

PIECES = [
    ("jobs.md", JOBS_MD),
    ("job-fetch-hosts.txt", HOSTS),
    ("vendor-read-allowlist.txt", VENDOR),
    (os.path.join("job-sim", "README.txt"), JOBSIM),
    ("tools", None),   # a folder
    ("JOBS-README.txt", README),
]


def scaffold(folder):
    """-> (created, skipped) lists of relative names. Anything already there (file, folder, link) is skipped untouched."""
    created, skipped = [], []
    for rel, text in PIECES:
        path = os.path.join(folder, rel)
        if os.path.lexists(path):
            skipped.append(rel)
            continue
        if text is None:
            os.makedirs(path)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "x", encoding="utf-8") as f:   # "x": refuses to overwrite, by construction
                f.write(text)
        created.append(rel)
    return created, skipped


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("usage: personal_jobs_scaffold.py [FOLDER]", file=sys.stderr)
        return 64
    if args:
        folder = os.path.expanduser(args[0])
    else:
        source, folder = personal_code_root.resolve_personal_code_root()
        if source not in ("pointer", "default"):
            print("NOT-SET: no personal code folder to scaffold. Fix: python3 system/tools/bootstrap.py", file=sys.stderr)
            return 1
    if not os.path.isdir(folder):
        print("NO-FOLDER: %s is not a folder; make it first (python3 system/tools/bootstrap.py)." % folder, file=sys.stderr)
        return 1
    created, skipped = scaffold(folder)
    for rel in created:
        print("created: %s" % rel)
    for rel in skipped:
        print("skipped (already there): %s" % rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
