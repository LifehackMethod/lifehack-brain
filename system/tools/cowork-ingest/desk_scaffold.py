#!/usr/bin/env python3
"""
desk_scaffold.py — one-punch FULL DESK scaffold (PORTED from the donor repo's
`system/tools/cowork-ingest/desk_scaffold.py`, migration F9.6 "THE DESK PLANE", "born like a deer").

⚖ The person, `authority: user`, verbatim: *"the new system should have a template and a way of creating
new desks, so that a new desk comes pre-filled with all of the folders that it needs and all of the
knowledge that it needs… It should be born like a deer or a cow — it comes out of the womb and it can
already start walking."*

**A full DESK is a strict SUPERSET of a knowledge folder — not a different format.** The sibling tool
`folder_scaffold.py` writes the LIGHT subset `/ingest` PHASE 4 generates for every confirmed subject:
`canon/current.md` + `canon/purpose.md` + `records/`, and nothing else — see that file's own docstring
and `docs/data-layout.md` §"Deliberate differences", which documents the light shape as the shipped
default and names THIS tool as the separate, deliberate, later act that promotes a folder to a full
desk. **Promotion is always a human call — this tool never runs itself.**

The full desk SHAPE is canonical in exactly one place: `system/sops/desk-building-sop.md` §"The shape".
This tool CREATES that shape deterministically so a desk build is one-punch, not hand-assembled.

Measured against the donor's own 9 real desks (2026-08-15, `desks/*` on the Drive-synced spine):
`projects/` exists in 8 of 9 (all but one) — added to the scaffold below. `views/` exists in 7 of 9 —
NOT universal, so it is opt-in here (`--views yes`), never created by default.

It writes the folder skeleton + stub files ONLY. It does NOT: edit your desk list
`<notes>/desks/desk-registry.yaml` (it prints the entry to add by hand — the list is yours, in your notes
folder, read through `shared/desk_list.py`; the plugin ships none), nor create the per-machine
`.claude/settings.json` (machine-local). Refuses to clobber an existing desk, in a preview too, and
refuses a desk name that is not a plain slug (lowercase letters, digits, `-` or `_`).

Usage:
  desk_scaffold.py --drive-root <notes root> --desk <slug> --purpose "<one line>" \\
      [--reads-external yes|no] [--views yes|no] [--dry-run]
"""
import argparse, os, re, sys, datetime


STUB = {
    "canon/current.md": ("---\ntopic: [desk-canon]\ntitle: {Desk} canon (standing)\nrecord_type: canon\n"
                         "desk: {desk}\ncreated_at: {d}\nupdated_at: {d}\nstatus: active\nauthority: user\n---\n\n"
                         "# {Desk} — standing canon\n\n_(Human-blessed, always-true facts for {desk}. Keep it TINY.)_\n"),
    "canon/purpose.md": ("---\ntopic: [desk-purpose]\ntitle: {Desk} — purpose\nrecord_type: canon\ndesk: {desk}\n"
                         "created_at: {d}\nupdated_at: {d}\nstatus: active\nauthority: user\n---\n\n"
                         "# {Desk} — purpose\n\n{purpose}\n"),
    "state/current.md": ("---\ntitle: {Desk} — current state\nrecord_type: state\ndesk: {desk}\n"
                         "updated_at: {d}\nstatus: active\nauthority: skill\n---\n\n# Where we are\n\n_(new desk)_\n"),
    "state/open-loops.md": ("---\ntitle: {Desk} — open loops\nrecord_type: state\ndesk: {desk}\n"
                            "updated_at: {d}\nstatus: active\nauthority: skill\n---\n\n# Open loops\n\n_(none yet)_\n"),
    "_registry.md": ("---\ntopic: [desk-registry]\ntitle: {Desk} — folder registry\nrecord_type: registry\n"
                     "desk: {desk}\ncreated_at: {d}\nupdated_at: {d}\nstatus: active\nauthority: skill\n---\n\n"
                     "# {Desk} registry\n\n## Starter files\n- `CLAUDE.md`\n- `_registry.md`\n"
                     "- `canon/current.md`\n- `canon/purpose.md`\n- `state/current.md`\n- `state/open-loops.md`\n"
                     "\n## Active records\n_(none yet)_\n"),
    "CLAUDE.md": ("# {Desk} — desk identity\n\n**Purpose:** {purpose}\n\n**Read order:** `canon/current.md` → "
                  "`state/current.md` → `state/open-loops.md`.\n\n**Scope:** {desk}-domain work only; route "
                  "other subjects to their desk.\n\n**Write rules:** canon = human-blessed only (`/save` stops "
                  "and shows you each canon line before it writes; guard_canon_write only keeps canon small and "
                  "free of expiring facts); records = dated; state = session-significant changes.\n\n"
                  "**Memory routing:** "
                  "durable→canon (human promotes) · dated finding→records/ · where-we-are→state/current.md.\n"),
}
# A desk name is a plain slug: it becomes a folder under desks/, so `..`, `/` and the like must never get through.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
DESK_LIST_REL = "desks/desk-registry.yaml"
# Core shape — always created. `views/` is opt-in (measured NOT universal; see module docstring).
DIRS = ["canon", "state", "records", "sources/inbox", "projects"]
OPTIONAL_DIRS = {"views": "views"}


def main():
    ap = argparse.ArgumentParser(description="scaffold a new conformant FULL DESK")
    ap.add_argument("--drive-root", required=True, help="the notes root (desks/ lives under it)")
    ap.add_argument("--desk", required=True, help="desk slug (lowercase)")
    ap.add_argument("--purpose", required=True, help="one-line purpose")
    ap.add_argument("--reads-external", default="no", choices=["yes", "no"])
    ap.add_argument("--views", default="no", choices=["yes", "no"],
                     help="create views/ too — opt-in; measured present in only 7 of 9 real desks")
    ap.add_argument("--dry-run", action="store_true",
                     help="print what would be created; write nothing")
    a = ap.parse_args()

    desk = a.desk.strip().lower()
    if not SLUG_RE.match(desk):
        sys.exit(f"REFUSED: desk name {a.desk!r} is not a plain slug — use lowercase letters, digits, "
                 "'-' or '_' (starting with a letter or digit, at most 64 characters).")
    base = os.path.join(a.drive_root, "desks", desk)
    if os.path.lexists(base):
        sys.exit(f"REFUSED: desk '{desk}' already exists at {base} — will not clobber.")

    dirs = list(DIRS)
    if a.views == "yes":
        dirs.append(OPTIONAL_DIRS["views"])

    d = datetime.datetime.now().strftime("%Y-%m-%d")
    fields = {"desk": desk, "Desk": desk.capitalize(), "purpose": a.purpose, "d": d}

    if a.dry_run:
        print(f"DRY-RUN: would scaffold desk '{desk}' at {base}")
        print("   folders:", ", ".join(dirs))
        print("   files  :", ", ".join(STUB.keys()))
        if a.views != "yes":
            print("   (views/ NOT created — opt-in via --views yes; not universal, see docstring)")
        return

    for sub in dirs:
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    for rel, tmpl in STUB.items():
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(tmpl.format(**fields))

    print(f"OK: scaffolded desk '{desk}' at {base}")
    print("   folders:", ", ".join(dirs))
    print("   files  :", ", ".join(STUB.keys()))
    desk_list = os.path.join(a.drive_root, DESK_LIST_REL)
    print("\n── NEXT (2 hand steps the jig deliberately does NOT auto-do) ──")
    print(f"1. Add this desk to YOUR desk list, {desk_list} (in your notes, not the plugin).")
    print("   If that file does not exist yet, create it with the two lines `schema_version: 2` and `desks:`.")
    print("   Then add this entry under `desks:` (if the line reads `desks: []`, change it to `desks:` first):\n")
    print(f"""  - desk_id: {desk}
    open_loops_path: desks/{desk}/state/open-loops.md
    purpose_path: desks/{desk}/canon/purpose.md
    reads_external: {a.reads_external}
    backlog_mode: register
    notes: "Scaffolded by desk_scaffold.py {d}."\n""")
    print("2. Per machine: a desk needs its own .claude/settings.json only if it launches its own")
    print("   session — add that by hand. A desk's scheduled jobs are rows in the job list")
    print("   (system/sops/cron-jobs-sop.md), not settings in the desk list.")
    print("\nShape source & procedure: system/sops/desk-building-sop.md (the ONE canonical desk-shape doc)")
    print("Sibling tool: system/tools/cowork-ingest/folder_scaffold.py — the LIGHT knowledge-folder")
    print("scaffold /ingest uses by default. This tool is the separate, later, deliberate promotion act.")


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
