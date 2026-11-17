#!/usr/bin/env python3
# not-wired-yet: these checks stamp the planning-desk component page; the stamper wiring (component_page.py's receipt list) is step 6(a)/(b) machinery owned by other helpers, and the final stamp comes after step 7 — wired there, not here.
"""planning_door_rows_check.py — the planning desk's job-door check (CR-9 step 6c, check i).

A CHECK, never the checked thing. It runs the job door's row check
(`install-schedulers.sh --check-row <name>`) over each job row the planning desk
relies on, and records the result in a receipt tile.

The rows, and why each is in (from system/jobs.md, the plugin's half of the job list):
  - calendar-store-sync    feeds the weekly run's calendar picture (the engine's staged
                           picture reads the calendar store this row refreshes).
  - tasks-store-sync       feeds the weekly run's tasks picture (same chain, tasks store).
  - planning-diary         the desk's diary writer. OFF by canon — canon/data-layout.md:242
                           and canon/circulatory-system-sop.md:251 both keep this row off —
                           so it is DORMANT (built, not in use), not checked for PASS.
  - planning-weekly-prime  LEGACY plumbing (2026-11-17, the owner's Fable answer 6),
                           replaced by Grand Central's engine; stays off, its contract stays
                           unfilled → DORMANT, not checked for PASS.

A DORMANT row that is enabled (`yes`) is a FAULT: it is running something canon and the
owner deliberately keep off. A relied-on live row the door refuses is a FAIL that names
the door's reason. A row missing from the manifest is ERROR — fail-closed, never a
vacuous pass.

Extra rule from the task: if a placement guard ever offers an `own_list_add.py --keep`
route, this check never takes it — it reports instead (see report-s6-page.md).

Receipt: a status tile via the shared single writer, like every other check.

Usage:
    planning_door_rows_check.py [--repo DIR] [--out PATH] [--selftest]

Exit codes: 0 every probe RAN (a FAIL is a finding, not a crash) · 2 a probe ERRORed ·
4 the repo or emit_status could not be read.
"""
import argparse
import os
import subprocess
import sys

# rows the planning desk relies on: name -> (why in, expected disposition)
ROWS = {
    "calendar-store-sync": ("feeds the weekly run's calendar picture", "live-relied"),
    "tasks-store-sync": ("feeds the weekly run's tasks picture", "live-relied"),
    "planning-diary": ("the desk's diary writer; off by canon (data-layout.md:242)", "dormant"),
    "planning-weekly-prime": ("LEGACY plumbing, replaced by the engine (Fable answer 6)", "dormant"),
}

INSTALLER = "system/tools/install-schedulers.sh"
MANIFEST = "system/jobs.md"


def _run(cmd, env=None) -> "tuple[int, str]":
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _enabled(manifest_text, name):
    """The enabled column of row `name` in a ```jobs block, or (None, reason)."""
    fence = None  # None = not in a fence; a name is a row line when inside a ```jobs
    # fence OR when the manifest carries no fences at all (the self-test's bare form)
    saw_fence = False
    in_jobs = False
    for line in manifest_text.splitlines():
        st = line.strip()
        if st.startswith("```"):
            if fence is None:
                fence = st[3:].strip()
                saw_fence = True
                in_jobs = fence == "jobs"
            else:
                fence = None
                in_jobs = False
            continue
        if (saw_fence and not in_jobs) or st.startswith("#") or not st:
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 2 or cols[0] != name:
            continue
        return cols[1], None
    return None, "row '%s' not found in the jobs manifest" % name


def probe_door_rows(repo, manifest_text, door_env=None) -> list:
    """Door-check every row in ROWS against manifest_text. Returns probe dicts
    {id, why, expected, door, door_rc, result, evidence}."""
    installer = os.path.join(repo, INSTALLER)
    out = []
    for name, (why, expected) in ROWS.items():
        enabled, err = _enabled(manifest_text, name)
        if err:
            out.append({"id": "door-row:" + name, "why": why, "expected": expected,
                        "door": "not-run", "door_rc": None, "result": "ERROR",
                        "evidence": err + " (fail-closed)"})
            continue
        rc, text = _run(["bash", installer, "--check-row", name], env=door_env)
        door = "PASS" if rc == 0 else ("REFUSED: " + " ".join(text.split())[:160])
        if expected == "dormant":
            # DORMANT: built, deliberately not in use. The door MAY refuse (these rows'
            # contracts are unfilled by design); what is a fault is the row running.
            if enabled == "yes":
                res, ev = "FAIL", "row is enabled=yes but canon/owner keep it off (DORMANT)"
            else:
                res, ev = "DORMANT", ("declared disposition '%s'; door: %s" % (enabled, door))
        else:
            res = "PASS" if rc == 0 else "FAIL"
            ev = "" if rc == 0 else "door refused: %s" % " ".join(text.split())[:160]
        out.append({"id": "door-row:" + name, "why": why, "expected": expected,
                    "door": door, "door_rc": rc, "result": res, "evidence": ev})
    return out


def _selftest(repo) -> dict:
    """Planted-fault self-test: each planted fault must FAIL (or ERROR) BY NAME, the good
    case must PASS/DORMANT. Uses temp manifests and a temp personal-code folder through the
    door's own test seams (LIFEHACK_JOBS_FILE, LIFEHACK_DESK_REPO) — nothing in the repo
    is touched."""
    import tempfile
    results = {}
    tmp = tempfile.mkdtemp(prefix="pdrc-")
    os.makedirs(os.path.join(tmp, "tools"))

    def env_for(path):
        e = dict(os.environ)
        e["LIFEHACK_JOBS_FILE"] = path
        e["LIFEHACK_DESK_REPO"] = tmp
        return e

    def write_manifest(text):
        p = os.path.join(tempfile.mkdtemp(prefix="pdrc-m-"), "jobs.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("```jobs\n" + text + "```\n")
        return p

    def run_probes(manifest_text):
        p = write_manifest(manifest_text)
        probes = probe_door_rows(repo, manifest_text, env_for(p))
        return probes

    # a door-clean personal runner + a door-clean live row
    with open(os.path.join(tmp, "tools", "ok.sh"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\necho ok\n")
    os.chmod(os.path.join(tmp, "tools", "ok.sh"), 0o755)
    log = os.path.join(os.path.expanduser("~"), ".config", "lifehack", "selftest-ok.log")
    _row_tpl = ("{name} | yes | 86400 | a good outcome happened | " + log +
                " ~ ok items=[1-9] | none | 0 | none |"
                ' bash "$LIFEHACK_PERSONAL_CODE/tools/ok.sh"\n')
    good = {r: _row_tpl.format(name=r) for r in ROWS}
    # dormant rows ship with TBD contracts, exactly as system/jobs.md ships them
    good["planning-diary"] = ("planning-diary | off | 86400 | TBD | TBD | TBD | 0 | TBD"
                              " | bash \"$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh\"\n")
    good["planning-weekly-prime"] = ("planning-weekly-prime | off | 86400 | TBD | TBD | TBD | 0 | TBD"
                                     " | bash \"$LIFEHACK_CODE_ROOT/system/tools/planning-weekly-prime-run.sh\"\n")

    # 1. good manifest: live rows PASS, dormant rows DORMANT (the door may refuse a dormant
    #    row's unfilled contract; that is by design, not a fault)
    probes = run_probes("".join(good.values()))
    results["good-manifest"] = (
        next(x for x in probes if x["id"] == "door-row:calendar-store-sync")["result"] == "PASS"
        and next(x for x in probes if x["id"] == "door-row:tasks-store-sync")["result"] == "PASS"
        and next(x for x in probes if x["id"] == "door-row:planning-diary")["result"] == "DORMANT"
        and next(x for x in probes if x["id"] == "door-row:planning-weekly-prime")["result"] == "DORMANT")

    # 2. planted fault: a relied-on live row the door refuses (TBD contract) FAILS by name
    bad = dict(good)
    bad["calendar-store-sync"] = (
        "calendar-store-sync | yes | 86400 | TBD | TBD | none | 0 | none"
        " | bash \"$LIFEHACK_PERSONAL_CODE/tools/ok.sh\"\n")
    probes = run_probes("".join(bad.values()))
    pr = next(x for x in probes if x["id"] == "door-row:calendar-store-sync")
    results["refused-live-row-bites"] = pr["result"] == "FAIL" and "refused" in pr["evidence"].lower()

    # 3. planted fault: a DORMANT row enabled=yes FAILS
    bad = dict(good)
    bad["planning-diary"] = good["planning-diary"].replace("| off |", "| yes |")
    probes = run_probes("".join(bad.values()))
    pr = next(x for x in probes if x["id"] == "door-row:planning-diary")
    results["enabled-dormant-row-bites"] = pr["result"] == "FAIL"

    # 4. planted fault: a relied-on row missing from the manifest ERRORs (never a vacuous pass)
    partial = "".join(v for k, v in good.items() if k != "tasks-store-sync")
    probes = run_probes(partial)
    pr = next(x for x in probes if x["id"] == "door-row:tasks-store-sync")
    results["missing-row-errors"] = pr["result"] == "ERROR"
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="planning_door_rows_check.py",
        description="Named check (i): the planning desk's job rows through the job door.")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--manifest", default=None, help="jobs manifest text override (tests only)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(args.repo or os.path.join(here, "..", "..", "..", ".."))

    if args.selftest:
        results = _selftest(repo)
        for probe_id, okb in sorted(results.items()):
            print("%s %s (self-test)" % (probe_id, "OK" if okb else "DID-NOT-BITE"))
        return 0 if all(results.values()) else 1

    if args.manifest:
        manifest_text = args.manifest
    else:
        try:
            with open(os.path.join(repo, MANIFEST), encoding="utf-8") as f:
                manifest_text = f.read()
        except OSError as e:
            print("ERROR: cannot read %s: %s" % (MANIFEST, e), file=sys.stderr)
            return 2

    probes = probe_door_rows(repo, manifest_text)
    for p in probes:
        print("%s %s" % (p["id"], p["result"]) + (" " + p["evidence"] if p["evidence"] else ""))

    results = [p["result"] for p in probes]
    if any(r == "ERROR" for r in results):
        status, tile_rc = "ERROR", 2
    elif any(r == "FAIL" for r in results):
        status, tile_rc = "DRIFT", 1
    else:
        status, tile_rc = "OK", 0
    summary = "%d of %d rows ok (%d dormant)" % (
        sum(1 for r in results if r in ("PASS", "DORMANT")), len(results),
        sum(1 for r in results if r == "DORMANT"))

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
            rc, brain = _run(["python3", os.path.join(repo, "shared", "brain_root.py"), "--quiet"])
            brain = brain.strip()
            if rc != 0 or not brain:
                print("ERROR: brain root not resolvable; pass --out", file=sys.stderr)
                return 4
            out_path = os.path.join(brain, "status", "component-planning-desk-door-rows.json")
        emit_status(out_path, desk="organism", pulse_job="planning-desk-door-rows-check",
                    stale_after_s=604800, status=status, rc=tile_rc, summary=summary,
                    emit_mode="manual",
                    payload={"component": "planning-desk", "check": "door-rows",
                             "rows": probes})
        print("receipt: %s" % out_path)
    except Exception as e:
        print("ERROR: could not write receipt: %s" % e, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
