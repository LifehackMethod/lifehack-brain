#!/usr/bin/env python3
# not-wired-yet: TEST-RIG helper called by rig_live_free.py (--drive) to give a live session a real Google Drive folder to share into; never part of the product
"""rig_drive.py - the dedicated Drive test area for the live rig (2026-11-01, Enver approved).

WHY: exam cases D-B08 / D-B09 ("share this skill with my team") end in a Google Drive shared folder. A throwaway HOME has no Drive at all, so
     the case could never be checked for real. This gives each run ONE folder inside a dedicated area of the real Drive, and nothing else.
WHAT: Drive/Lifehack test area/<run-id>/   one folder per run (the ONLY real Drive place a rig session may write; rig_fence.py enforces it)
      Drive/Lifehack test area/_archive/   finished runs are MOVED here (mv), never deleted
      <throwaway HOME>/Library/CloudStorage/GoogleDrive-rigtest/My Drive  -> symlink to the run folder. That is all a real person's
      machine has too: a Drive folder sitting on disk where Drive for Desktop puts it. NO setting, pointer or instruction is given to the session:
      the shipped product has no "Drive shared folder" setting (see the 2026-11-01 record), so the session finds the folder the way a person would.
ORDER per run: begin() -> session -> snapshot_end_state() (JSON of every file + sha256) -> unlink_mount() -> archive().
Only this module touches the area; it refuses any run id that could leave it."""
import glob, hashlib, json, os, re, subprocess, sys, time

AREA_NAME = "Lifehack test area"
MOUNT_NAME = "GoogleDrive-rigtest"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")


def my_drive():
    """The local Drive-for-Desktop 'My Drive' folder of the account that holds the AI Brain (the 'My Drive' ancestor of the brain root), else the only one
    on the machine. RIG_DRIVE_MYDRIVE overrides (tests). Exits if it cannot tell: never guesses between accounts."""
    o = os.environ.get("RIG_DRIVE_MYDRIVE")
    if o:
        return os.path.realpath(o)
    here = os.path.dirname(os.path.abspath(__file__))
    r = subprocess.run([sys.executable, os.path.join(here, "..", "..", "..", "shared", "brain_root.py"), "--quiet"], capture_output=True, text=True)
    p = os.path.realpath(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else ""
    while p and p != os.sep:
        if os.path.basename(p) == "My Drive":
            return p
        p = os.path.dirname(p)
    hits = sorted(glob.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/My Drive")))
    if len(hits) != 1:
        raise SystemExit("REFUSED: cannot tell which local 'My Drive' folder to use (%d found, brain root is not inside one)" % len(hits))
    return os.path.realpath(hits[0])


def area():
    return os.path.join(my_drive(), AREA_NAME)


def run_dir(run_id):
    if not RUN_ID_RE.match(run_id or "") or run_id.lower() == "_archive" or ".." in run_id:
        raise SystemExit("REFUSED: bad run id %r" % run_id)
    return os.path.join(area(), run_id)


def make_run_id(label, case_id):
    return re.sub(r"[^A-Za-z0-9._-]", "-", "%s-%s-%s" % (time.strftime("%Y%m%dT%H%M%S"), label, case_id))[:100]


def begin(run_id, home):
    """Create the parent if missing, the run folder (must be new), and the Drive mount inside the throwaway HOME. -> the run folder's realpath."""
    rd = run_dir(run_id)
    os.makedirs(os.path.join(area(), "_archive"), exist_ok=True)
    if os.path.exists(rd):
        raise SystemExit("REFUSED: run folder already exists: " + rd)
    os.mkdir(rd)
    home = os.path.abspath(os.path.expanduser(home))
    if os.path.basename(home) != "rig-iso-home":
        raise SystemExit("REFUSED: not a throwaway HOME: " + home)
    cs = os.path.join(home, "Library", "CloudStorage", MOUNT_NAME)
    os.makedirs(cs, exist_ok=True)
    link = os.path.join(cs, "My Drive")
    if os.path.lexists(link):
        os.unlink(link)
    os.symlink(os.path.realpath(rd), link)
    return os.path.realpath(rd)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def snapshot_end_state(run_id, out_path):
    """Write a JSON listing every file under the run folder with its sha256 (symlinks are recorded as links, never followed; empty dirs listed). -> the dict."""
    rd = run_dir(run_id)
    files, dirs = [], []
    for dp, dn, fn in os.walk(rd):               # os.walk does not follow symlinked dirs
        for d in sorted(dn):
            full = os.path.join(dp, d)
            (files if os.path.islink(full) else dirs).append(
                {"path": os.path.relpath(full, rd), "link_to": os.readlink(full)} if os.path.islink(full) else os.path.relpath(full, rd))
        for f in sorted(fn):
            full = os.path.join(dp, f)
            if os.path.islink(full):
                files.append({"path": os.path.relpath(full, rd), "link_to": os.readlink(full)})
            else:
                files.append({"path": os.path.relpath(full, rd), "sha256": sha256(full), "size": os.path.getsize(full)})
    files.sort(key=lambda x: x["path"])
    snap = {"run_id": run_id, "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "run_folder": rd,
            "archived_to": os.path.join(area(), "_archive", run_id), "files": files, "empty_or_all_dirs": sorted(dirs)}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    return snap


def unlink_mount(home):
    """Remove the symlink (the link only, never what it points at) so nothing in the throwaway HOME still reaches the run folder."""
    link = os.path.join(os.path.abspath(os.path.expanduser(home)), "Library", "CloudStorage", MOUNT_NAME, "My Drive")
    if os.path.islink(link):
        os.unlink(link)


def archive(run_id):
    """MOVE the run folder to _archive/ with mv; never deletes. A name clash gets a time suffix. -> the new path."""
    src = run_dir(run_id)
    arc = os.path.join(area(), "_archive")
    os.makedirs(arc, exist_ok=True)
    dst = os.path.join(arc, run_id)
    if os.path.exists(dst):
        dst += "-" + time.strftime("%H%M%S")
    r = subprocess.run(["mv", src, dst], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("archive move failed: " + r.stderr.strip())
    return dst


def seed_invoice_skill(home):
    """D-B08 / D-B09 fixture ('a built skill ~/.claude/skills/invoice-checker/ exists'): a tiny real skill in the throwaway HOME, as if the person had just built it."""
    d = os.path.join(os.path.abspath(os.path.expanduser(home)), ".claude", "skills", "invoice-checker")
    os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: invoice-checker\ndescription: Check a supplier invoice against its purchase order and flag mismatched totals. Use on \"check this invoice\".\n---\n\n"
                "# Invoice checker\n\nRead the invoice and the purchase order, compare line totals, and list every mismatch.\nRun `scripts/total.py INVOICE.csv` for the arithmetic.\n")
    with open(os.path.join(d, "scripts", "total.py"), "w", encoding="utf-8") as f:
        f.write("import csv, sys\nprint(sum(float(r[-1]) for r in csv.reader(open(sys.argv[1])) if r and r[-1].replace('.', '', 1).isdigit()))\n")
