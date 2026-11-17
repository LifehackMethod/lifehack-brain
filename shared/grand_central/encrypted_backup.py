#!/usr/bin/env python3
# not-wired-yet: scheduled after the backup key sitting, plan step 1.6
"""Encrypted backup of the front room's transcripts + catalogue (plan step 4b).

One encrypted DMG (AES-256, hdiutil — the only standard tool already on the Mac).
The archive is BUILT outside the Drive folder, verified there (passphrase round-trip
+ sha256 manifest), and only then copied into Drive. No unencrypted byte ever lands
under the Drive path, not even a temp file: the only drive-side temp is the .dmg
itself, renamed to final after the copy.

  backup.py backup  --passphrase-file FILE [--transcripts DIR] [--catalogue DIR] [--keep N]
                    pack -> encrypt -> verify -> copy to <drive>/<state folder>/backups/
                    encrypted-<YYYYMMDD>.dmg (same-day replaced, keep newest N, default 14)
  backup.py restore ARCHIVE --to DIR --passphrase-file FILE
                    mount read-only, copy out to a NEW path (never overwrites), unmount
  backup.py verify  ARCHIVE --passphrase-file FILE
                    mount read-only, sha256-manifest check, print verdict

The passphrase ALWAYS comes from a file passed with --passphrase-file. It is never
hard-coded and never taken from an env var. Missing/unreadable key file -> loud
failure, nothing written anywhere.

Env (for tests): AGE_FRONT_ROOM, AGE_BACKUP_DRIVE_DIR, (hdiutil only: AGE_HDIUTIL).
"""
import argparse, datetime as dt, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gc_settings  # noqa: E402

KEEP = 14
DRIVE_DELAY_S = 2.0  # grace before re-listing the drive dir (sync lag)

def front_room():
    return Path(gc_settings.front_room_dir())

def transcripts_dir():
    return front_room() / "transcripts"

def catalogue_dir():
    return front_room() / "catalogue"

def drive_backup_dir():
    notes = os.environ.get("AGE_BACKUP_DRIVE_DIR")
    if notes:
        return Path(notes) / gc_settings.state_subdir() / "backups"
    return Path(gc_settings.configured_notes_root()) / gc_settings.state_subdir() / "backups"

def hdiutil():
    return os.environ.get("AGE_HDIUTIL") or "/usr/bin/hdiutil"

def die(msg):
    raise SystemExit("FAIL: " + msg)

def read_passphrase(path):
    """The key comes ONLY from a file passed by the caller. Missing -> fail loudly, write nothing."""
    p = Path(path).expanduser()
    try:
        data = p.read_bytes()
    except OSError as e:
        die(f"passphrase file unreadable: {p} ({e}) — wrote nothing")
    if not data.strip():
        die(f"passphrase file is empty: {p} — wrote nothing")
    if b"\0" in data:
        die(f"passphrase file contains a NUL byte: {p} — wrote nothing")
    return data.rstrip(b"\n")

def manifest(d):
    """{relpath: sha256} for every file under d."""
    out = {}
    for p in sorted(Path(d).rglob("*")):
        if p.is_file():
            out[p.relative_to(d).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def _hdi(args, passphrase=None):
    """Run hdiutil; passphrase (bytes) on stdin when given; fail loudly on non-zero."""
    r = subprocess.run([hdiutil()] + args, input=passphrase, capture_output=True)
    if r.returncode != 0:
        die("hdiutil %s failed (rc=%d): %s" % (args[0], r.returncode, r.stderr.decode(errors="replace").strip()))
    return r.stdout.decode()

def _dmg_encrypted(path):
    """True if hdiutil itself says the image is encrypted (UDZO compresses the header,
    so byte-sniffing finds nothing — this asks the tool, which never lies)."""
    r = subprocess.run([hdiutil(), "isencrypted", str(path)], capture_output=True)
    if r.returncode != 0:
        return False, "hdiutil isencrypted failed (not a dmg or unreadable)"
    return b"encrypted: YES" in r.stdout, None

def pack_encrypted(sources, out_dmg, passphrase_file):
    """sources: list of dirs (each must exist and be non-empty). Builds the encrypted dmg
    OUTSIDE drive in staging, verifies the round-trip, then copies to out_dmg (any path)."""
    pw = read_passphrase(passphrase_file)
    sources = [Path(s).expanduser() for s in sources]
    for s in sources:
        if not s.is_dir() or not any(s.iterdir()):
            die(f"source missing or empty: {s} — wrote nothing")

    staging = Path(tempfile.mkdtemp(prefix="age-backup-"))
    try:
        payload = staging / "payload"
        payload.mkdir()
        for s in sources:
            shutil.copytree(s, payload / s.name)
        m = manifest(payload)
        if not m:
            die("nothing to back up — wrote nothing")
        mf = payload / "_backup_manifest.json"
        mf.write_text(json.dumps(m, indent=1, sort_keys=True))
        os.chmod(mf, 0o600)

        stage_dmg = staging / "archive.dmg"
        _hdi(["create", "-srcfolder", str(payload), "-encryption", "AES-256",
              "-stdinpass", "-format", "UDZO", "-ov", str(stage_dmg)], passphrase=pw)
        enc, why = _dmg_encrypted(stage_dmg)
        if not enc:
            die("built archive is not encrypted — refusing to publish it" + (f" ({why})" if why else ""))
        ok, probs = verify_archive(stage_dmg, passphrase_file)  # wrong key / corrupt -> loud, here
        if not ok:
            die("staged archive failed verification: " + "; ".join(probs))

        out_dmg = Path(out_dmg)
        out_dmg.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_dmg.parent / f".{out_dmg.name}.tmp"
        shutil.copyfile(stage_dmg, tmp)
        os.chmod(tmp, 0o600)
        enc, _ = _dmg_encrypted(tmp)
        if not enc:
            tmp.unlink()
            die("drive-side temp copy is not the encrypted archive — removed it")
        os.replace(tmp, out_dmg)
        return out_dmg
    finally:
        shutil.rmtree(staging, ignore_errors=True)

def _payload_root(mount):
    """The mounted volume holds either the payload directly or one finder-wrapped dir."""
    entries = [e for e in Path(mount).iterdir() if not e.name.startswith("._")]
    if len(entries) == 1 and entries[0].is_dir() and not (entries[0] / "_backup_manifest.json").exists():
        entries = [e for e in entries[0].iterdir() if not e.name.startswith("._")]
    return Path(mount)

def restore(archive, to_dir, passphrase_file):
    """Mount read-only, copy out to a NEW path, unmount. Never overwrites."""
    pw = read_passphrase(passphrase_file)
    archive = Path(archive).expanduser()
    if not archive.is_file():
        die(f"no such archive: {archive}")
    to = Path(to_dir).expanduser()
    if to.exists():
        die(f"refused: --to must be a NEW path (never overwrites): {to}")
    to.parent.mkdir(parents=True, exist_ok=True)
    mount = Path(tempfile.mkdtemp(prefix="age-restore-"))
    try:
        _hdi(["attach", "-stdinpass", "-readonly", "-mountpoint", str(mount), str(archive)], passphrase=pw)
        try:
            shutil.copytree(_payload_root(mount), to)
        finally:
            _hdi(["detach", str(mount)])
    except SystemExit:
        shutil.rmtree(to, ignore_errors=True)  # nothing half-restored
        raise
    finally:
        shutil.rmtree(mount, ignore_errors=True)
    return to

def verify_archive(archive, passphrase_file):
    """Mount read-only and check the manifest hashes. Returns (ok, problems)."""
    pw = read_passphrase(passphrase_file)
    archive = Path(archive).expanduser()
    if not archive.is_file():
        die(f"no such archive: {archive}")
    mount = Path(tempfile.mkdtemp(prefix="age-verify-"))
    probs = []
    try:
        _hdi(["attach", "-stdinpass", "-readonly", "-mountpoint", str(mount), str(archive)], passphrase=pw)
        try:
            src = _payload_root(mount)
            mf_path = src / "_backup_manifest.json"
            if not mf_path.is_file():
                probs.append("archive has no manifest")
            else:
                mf = json.loads(mf_path.read_text())
                have = manifest(src)
                for rel, h in mf.items():
                    if rel == "_backup_manifest.json":
                        continue
                    if rel not in have:
                        probs.append(f"missing from archive: {rel}")
                    elif have[rel] != h:
                        probs.append(f"hash mismatch: {rel}")
                extra = set(have) - set(mf) - {"_backup_manifest.json"}
                if extra:
                    probs.append(f"unexpected files in archive: {sorted(extra)}")
        finally:
            _hdi(["detach", str(mount)])
    finally:
        shutil.rmtree(mount, ignore_errors=True)
    return (not probs), probs

def prune(d, keep=KEEP):
    """encrypted-YYYYMMDD.dmg only, oldest first (same-day replaced above). Reuses the
    keep-14 pattern from CODE/backup.py (_prune / KEEP_SNAPSHOTS)."""
    d = Path(d)
    pat = re.compile(r"encrypted-\d{8}\.dmg")
    files = sorted(p for p in d.iterdir() if pat.fullmatch(p.name))
    for p in files[:-keep]:
        p.unlink()

def backup(transcripts=None, catalogue=None, passphrase_file=None, keep=KEEP):
    if passphrase_file is None:
        die("--passphrase-file is required — wrote nothing")
    sources = [transcripts or transcripts_dir(), catalogue or catalogue_dir()]
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    final = drive_backup_dir() / f"encrypted-{day}.dmg"
    pack_encrypted(sources, final, passphrase_file)
    time.sleep(DRIVE_DELAY_S)
    prune(drive_backup_dir(), keep)
    return final

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--transcripts"); b.add_argument("--catalogue")
    b.add_argument("--passphrase-file", required=True)
    b.add_argument("--keep", type=int, default=KEEP)
    r = sub.add_parser("restore"); r.add_argument("archive")
    r.add_argument("--to", required=True); r.add_argument("--passphrase-file", required=True)
    v = sub.add_parser("verify"); v.add_argument("archive"); v.add_argument("--passphrase-file", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "backup":
        print(backup(a.transcripts, a.catalogue, a.passphrase_file, a.keep))
    elif a.cmd == "restore":
        print(f"restored -> {restore(a.archive, a.to, a.passphrase_file)}")
    else:
        ok, probs = verify_archive(a.archive, a.passphrase_file)
        print("verify: OK" if ok else "verify: FAIL")
        for p in probs:
            print(" PROBLEM:", p)
        return 0 if ok else 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
