#!/usr/bin/env python3
# not-wired-yet: these checks stamp the planning-desk component page; the stamper wiring (component_page.py's receipt list) is step 6(a)/(b) machinery owned by other helpers, and the final stamp comes after step 7 — wired there, not here.
"""planning_data_path_check.py — the planning desk's data-path check (CR-9 step 6c, check iii).

A CHECK, never the checked thing. It verifies that the person's desks — read through the
ONE desk list reader, shared/desk_list.py — sit where canon/data-layout.md says they sit.

What data-layout.md requires of a desk folder (canon/data-layout.md, "The shape" and
"Types of record"):
  - every path the desk list names lives under <notes>/desks/<folder>/, and the folder
    named in the path is the folder on disk (the leaf-equals-slug rule's desk-side twin);
  - canon/purpose.md exists (what /ingest builds for each subject);
  - records/ exists;
  - the open_loops_path, when named, resolves to a real file under the desk folder.

This check contains NO literal desk name: it checks whatever desks the person's
desk-registry.yaml names, whatever they are called. The desk list is found through
shared/desk_list.py's own resolution (the LIFEHACK_DESK_LIST test seam, then
<notes>/desks/desk-registry.yaml); the notes root is found through person_roots/brain_root
(LIFEHACK_ROOT). A missing desk list means "no desks" and is a PASS (data-layout says a
new student has nothing to set up) — a list that is THERE but cannot be read is ERROR.

Usage:
    planning_data_path_check.py [--out PATH] [--selftest]

Exit codes: 0 every probe RAN (a FAIL is a finding, not a crash) · 2 a probe ERRORed ·
4 shared/desk_list.py or emit_status could not be read.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "shared"))


def probe_data_path(env=None) -> list:
    """Check every desk in the desk list against data-layout.md's shape.
    Returns probe dicts {id, result, evidence}."""
    if SHARED not in sys.path:
        sys.path.insert(0, SHARED)
    import desk_list

    path = desk_list.resolve_desk_list(env)
    desks, err = desk_list.load_desks(env)
    out = []
    if err:
        out.append({"id": "desk-list-readable", "result": "ERROR",
                    "evidence": err + " (fail-closed)"})
        return out
    if not desks:
        out.append({"id": "desk-list-readable", "result": "PASS",
                    "evidence": "no desk list (no desks) — data-layout's day-one state"})
        return out
    out.append({"id": "desk-list-readable", "result": "PASS",
                "evidence": "%d desk(s) in %s" % (len(desks), path)})

    notes = _notes_root(env)
    if not notes:
        out.append({"id": "notes-root", "result": "ERROR",
                    "evidence": "notes root not resolvable (fail-closed)"})
        return out

    for d in desks:
        desk_id = str(d.get("desk_id") or "").strip()
        if not desk_id:
            out.append({"id": "desk-entry", "result": "ERROR",
                        "evidence": "an entry with no desk_id (fail-closed)"})
            continue
        pid = "desk:" + desk_id
        folder, ferr = desk_list.desk_folder(desk_id, env)
        if ferr:
            out.append({"id": pid, "result": "ERROR", "evidence": ferr + " (fail-closed)"})
            continue
        if not folder:
            out.append({"id": pid, "result": "FAIL",
                        "evidence": "no purpose_path/open_loops_path naming desks/<folder>/"})
            continue
        desk_dir = os.path.join(notes, "desks", folder)
        probs = []
        # leaf-equals-folder: every named path's leaf under desks/ is this folder
        for key in ("purpose_path", "open_loops_path"):
            rel = str(d.get(key) or "").replace("\\", "/")
            if not rel:
                continue
            parts = rel.split("/")
            if parts[0] != "desks" or len(parts) < 3 or parts[1] != folder:
                probs.append("%s does not name desks/%s/" % (key, folder))
            elif not os.path.exists(os.path.join(notes, *parts)):
                probs.append("%s -> %s does not exist" % (key, rel))
        if not os.path.isfile(os.path.join(desk_dir, "canon", "purpose.md")):
            probs.append("canon/purpose.md missing")
        if not os.path.isdir(os.path.join(desk_dir, "records")):
            probs.append("records/ missing")
        if probs:
            out.append({"id": pid, "result": "FAIL", "evidence": "; ".join(probs)})
        else:
            out.append({"id": pid, "result": "PASS",
                        "evidence": "desks/%s/ matches data-layout's shape" % folder})
    return out


def _notes_root(env=None):
    e = dict(os.environ if env is None else env)
    if SHARED not in sys.path:
        sys.path.insert(0, SHARED)
    if e.get("LIFEHACK_ROOT"):
        return e["LIFEHACK_ROOT"]
    try:
        import person_roots
        return person_roots.notes_root()
    except Exception:
        return None


def _selftest() -> dict:
    """Planted-fault self-test in a TEMP notes root (never the person's real notes):
    a well-formed desk PASSes; each planted fault FAILs or ERRORs by name."""
    import tempfile
    results = {}
    def build(desk_body, tree=True):
        base = tempfile.mkdtemp(prefix="pdpc-")
        notes = os.path.join(base, "notes")
        os.makedirs(os.path.join(notes, "desks", "alpha", "canon"), exist_ok=True)
        os.makedirs(os.path.join(notes, "desks", "alpha", "records"), exist_ok=True)
        if tree:
            os.makedirs(os.path.join(notes, "desks", "alpha", "state"), exist_ok=True)
            with open(os.path.join(notes, "desks", "alpha", "canon", "purpose.md"), "w", encoding="utf-8") as f:
                f.write("# purpose\n")
            with open(os.path.join(notes, "desks", "alpha", "state", "open-loops.md"), "w", encoding="utf-8") as f:
                f.write("# loops\n")
        lst = os.path.join(base, "desk-registry.yaml")
        with open(lst, "w", encoding="utf-8") as f:
            f.write("schema_version: 2\ndesks:\n" + desk_body)
        e = dict(os.environ)
        e["LIFEHACK_DESK_LIST"] = lst
        e["LIFEHACK_ROOT"] = notes
        return e

    good = (" - desk_id: alpha\n"
            "   open_loops_path: desks/alpha/state/open-loops.md\n"
            "   backlog_mode: queue\n"
            "   purpose_path: desks/alpha/canon/purpose.md\n")
    probes = probe_data_path(build(good))
    results["good-desk-passes"] = all(p["result"] == "PASS" for p in probes)

    # planted fault 1: purpose file missing
    e = build(good, tree=False)
    probes = probe_data_path(e)
    pr = next(p for p in probes if p["id"] == "desk:alpha")
    results["missing-purpose-bites"] = pr["result"] == "FAIL" and "purpose" in pr["evidence"]

    # planted fault 2: the path names a folder that is not the folder on disk
    e = build(good.replace("desks/alpha/canon/purpose.md", "desks/beta/canon/purpose.md"))
    probes = probe_data_path(e)
    pr = next(p for p in probes if p["id"] == "desk:alpha")
    results["folder-mismatch-bites"] = pr["result"] == "FAIL"

    # planted fault 3: unreadable list ERRORs (fail-closed)
    e = dict(os.environ)
    lst = os.path.join(tempfile.mkdtemp(prefix="pdpc-"), "broken.yaml")
    with open(lst, "w", encoding="utf-8") as f:
        f.write("schema_version: 2\ndesks:\n  - \t bad\n")
    e["LIFEHACK_DESK_LIST"] = lst
    probes = probe_data_path(e)
    results["broken-list-errors"] = probes[0]["result"] == "ERROR"
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="planning_data_path_check.py",
        description="Named check (iii): the desks sit where canon/data-layout.md says.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        results = _selftest()
        for probe_id, okb in sorted(results.items()):
            print("%s %s (self-test)" % (probe_id, "OK" if okb else "DID-NOT-BITE"))
        return 0 if all(results.values()) else 1

    probes = probe_data_path()
    for p in probes:
        print("%s %s" % (p["id"], p["result"]) + (" " + p["evidence"] if p["evidence"] else ""))

    results = [p["result"] for p in probes]
    if any(r == "ERROR" for r in results):
        status, tile_rc = "ERROR", 2
    elif any(r == "FAIL" for r in results):
        status, tile_rc = "DRIFT", 1
    else:
        status, tile_rc = "OK", 0
    summary = "%d of %d path probes ok" % (sum(1 for r in results if r == "PASS"), len(results))

    repo = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
    try:
        sys.path.insert(0, os.path.join(repo, "system", "tools"))
        from emit_status import emit_status  # noqa: E402
    except Exception as e:
        print("ERROR: cannot import emit_status: %s" % e, file=sys.stderr)
        return 4
    try:
        if args.out:
            out_path = args.out
        else:
            import subprocess
            p = subprocess.run(["python3", os.path.join(repo, "shared", "brain_root.py"), "--quiet"],
                               capture_output=True, text=True)
            brain = (p.stdout or "").strip()
            if p.returncode != 0 or not brain:
                print("ERROR: brain root not resolvable; pass --out", file=sys.stderr)
                return 4
            out_path = os.path.join(brain, "status", "component-planning-desk-data-path.json")
        emit_status(out_path, desk="organism", pulse_job="planning-desk-data-path-check",
                    stale_after_s=604800, status=status, rc=tile_rc, summary=summary,
                    emit_mode="manual",
                    payload={"component": "planning-desk", "check": "data-path",
                             "probes": probes})
        print("receipt: %s" % out_path)
    except Exception as e:
        print("ERROR: could not write receipt: %s" % e, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
