#!/usr/bin/env python3
"""layout.py — the ONE place the skill-tester-rig's run layout is defined (card TR2.0b, design (b), ruled 2026-11-01).

    <scratch>/actor-home/<run-id>/                                   ACTOR_HOME: the actor's throwaway HOME, ONE per run
    <scratch>/actor-home/<run-id>/.claude/run/skill-tester/<run-id>/ RUN_DIR: inside the actor's own $HOME/.claude
    <scratch>/seeds/<run-id>, <scratch>/plans/<run-id>/              OUTSIDE the throwaway HOME (unchanged; denied to the actor)

WHY. The Harness ingest gate (ingest_gate_enforce.sh) trusts the repo, $HOME/.claude and the notes root, and takes
$HOME from the actor's environment. A real headless actor with --plugin-dir had its Read of a step file in plain
scratch refused (TR2.0b census). Under the throwaway HOME the step files sit in the actor's own $HOME/.claude, the
same place a real skill keeps them (~/.claude/run/...). The gate trusts step files ONLY because they sit there; in
real use the same holds under the real ~/.claude (stated on every receipt). No "memory" segment in the path (the
gate excludes memory/). Fake and real runs use this layout identically; they differ only in the binary.

Imported by run_helper.py (CLI: `rundir`, `actorhome`, `scratch-of`), truth.py and anything else in Python; shell
callers go through `run_helper.py rundir <scratch> <run-id>`. Pure path arithmetic: creates nothing.
"""
import os

ACTOR_HOME_DIR = "actor-home"
RUN_SUBPATH = (".claude", "run", "skill-tester")


def actor_home(scratch, run_id):
    return os.path.join(scratch, ACTOR_HOME_DIR, run_id)


def run_dir(scratch, run_id):
    return os.path.join(actor_home(scratch, run_id), *RUN_SUBPATH, run_id)


def scratch_of(rd):
    """The scratch root of a run dir laid out as above, else None (a run dir passed by hand may be anywhere)."""
    rd = os.path.normpath(rd)
    parts = rd.split(os.sep)
    rid = parts[-1]
    # .../<scratch>/actor-home/<rid>/.claude/run/skill-tester/<rid>
    if len(parts) >= 7 and parts[-2:-5:-1] == ["skill-tester", "run", ".claude"] and parts[-5] == rid \
            and parts[-6] == ACTOR_HOME_DIR:
        return os.sep.join(parts[:-6]) or os.sep
    return None
