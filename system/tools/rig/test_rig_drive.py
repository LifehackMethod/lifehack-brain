#!/usr/bin/env python3
# not-wired-yet: run by hand; checks rig_drive.py (run folder, end-state JSON, archive move) in a temp dir, no Drive and no model call
import hashlib, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig_drive as d

T = os.path.realpath(tempfile.mkdtemp(prefix="rigdrive-"))
os.environ["RIG_DRIVE_MYDRIVE"] = T + "/My Drive"
os.makedirs(T + "/My Drive")
home = T + "/rig-iso-home"
os.makedirs(home)
ok = n = 0


def check(name, cond):
    global ok, n
    n += 1; ok += bool(cond); print("%s %s" % ("ok  " if cond else "MISS", name))


rid = d.make_run_id("t", "D-B08")
rd = d.begin(rid, home)
check("parent + _archive + run folder made", os.path.isdir(rd) and os.path.isdir(T + "/My Drive/Lifehack test area/_archive"))
mnt = home + "/Library/CloudStorage/GoogleDrive-rigtest/My Drive"
check("mount in throwaway HOME is a link to the run folder only", os.path.islink(mnt) and os.path.realpath(mnt) == rd)
open(mnt + "/a.txt", "w", encoding="utf-8").write("hello")
os.makedirs(mnt + "/sub/deep"); open(mnt + "/sub/b.txt", "w", encoding="utf-8").write("bee"); os.symlink("/etc", mnt + "/lnk")
snap = d.snapshot_end_state(rid, T + "/streams/end.json")
j = json.load(open(T + "/streams/end.json", encoding="utf-8"))
byp = {f["path"]: f for f in j["files"]}
check("snapshot lists every file with sha256", byp["a.txt"]["sha256"] == hashlib.sha256(b"hello").hexdigest() and byp["sub/b.txt"]["size"] == 3)
check("symlink recorded as a link, not followed", byp["lnk"]["link_to"] == "/etc" and "sha256" not in byp["lnk"])
check("dirs listed", "sub/deep" in j["empty_or_all_dirs"])
d.unlink_mount(home)
check("unlink_mount removes only the link", not os.path.lexists(mnt) and os.path.exists(rd + "/a.txt"))
dst = d.archive(rid)
check("run folder MOVED to _archive with contents intact", not os.path.exists(rd) and open(dst + "/a.txt", encoding="utf-8").read() == "hello" and "/_archive/" in dst)
rid2 = rid
os.makedirs(d.area() + "/" + rid2); open(d.area() + "/" + rid2 + "/z", "w", encoding="utf-8").write("z")
dst2 = d.archive(rid2)
check("name clash in _archive gets a suffix, nothing overwritten", dst2 != dst and os.path.exists(dst + "/a.txt") and os.path.exists(dst2 + "/z"))
for bad in ("../x", "_archive", "a/b", "", ".hidden", "x y"):
    try:
        d.run_dir(bad); check("refuses run id %r" % bad, False)
    except SystemExit:
        check("refuses run id %r" % bad, True)
try:
    d.begin(rid, T + "/not-a-throwaway-home"); check("refuses a non-throwaway HOME", False)
except SystemExit:
    check("refuses a non-throwaway HOME", True)
import shutil; shutil.rmtree(T, ignore_errors=True)   # only the temp dir this run made
print("RIG DRIVE: %d of %d" % (ok, n))
sys.exit(0 if ok == n else 1)
