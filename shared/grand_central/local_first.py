"""local_first.py - the ONE way a scheduled job reads a file that lives on Google Drive.

Why: Google Drive for desktop offloads files to the cloud. A background job (launchd) is not allowed to fetch them, so
open().read() fails with OSError errno 11 (EDEADLK, "Resource deadlock avoided"). Every Drive READ in the scheduled
paths therefore goes through here: a local working copy in <data_root>/drive-cache/ is read first, Drive is the
fallback, and if both fail the error is LOUD (DriveReadError naming both paths), never an empty result.

Freshness rule (one place):
  * a job that WRITES a Drive file also writes the local copy (write_local_copy), so the local copy is the newest truth;
  * if the Drive file's mtime can be read and is newer than the local copy's (he edited it), Drive is preferred and the
    local copy is refreshed from it;
  * any Drive read error falls back to the local copy; with no local copy it raises.
DriveReadError is NOT an OSError on purpose: callers that catch OSError to mean "file missing" must not swallow it.
A file that is truly missing (ENOENT on Drive and no local copy) raises FileNotFoundError, naming both paths.

Local copies mirror the path relative to the notes folder (mover folder: mover/<rel>; anything else: other/<abs path>).
They hold exactly the bytes of the Drive file, never anything else.
"""
import errno
import os
import sys
import tempfile
import time

import gc_settings


class DriveReadError(RuntimeError):
    """A Drive file could not be read and there is no local copy to fall back on. The message names both paths."""


def cache_root():
    return os.path.join(gc_settings.data_root(), "drive-cache")


def _under(path, root):
    path, root = os.path.abspath(os.path.expanduser(path)), os.path.abspath(os.path.expanduser(root))
    if path == root or path.startswith(root.rstrip(os.sep) + os.sep):
        return os.path.relpath(path, root)
    return None


def cache_path(drive_path):
    """The local working copy's path for a Drive path (mirrors the relative path under drive-cache/)."""
    p = os.path.abspath(os.path.expanduser(str(drive_path)))
    for prefix, getter in (("", gc_settings.notes_root), ("", gc_settings.configured_notes_root),
                           ("mover", lambda: gc_settings.gc("mover_dir"))):
        try:
            rel = _under(p, getter())
        except gc_settings.SettingsError:
            continue
        if rel is not None:
            return os.path.join(cache_root(), prefix, rel) if prefix else os.path.join(cache_root(), rel)
    return os.path.join(cache_root(), "other", p.lstrip(os.sep))


def _warn(msg):
    print("local_first: " + msg, file=sys.stderr)


def _mtime(path):
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None


def _read_file(path):
    with open(path, "rb") as f:
        return f.read()


def _store(lp, data, mtime=None):
    """Atomically write the local copy (0600, folder 0700). mtime: the Drive mtime to mirror (None = now)."""
    d = os.path.dirname(lp)
    os.makedirs(d, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".lf-", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        if mtime is not None:
            os.utime(tmp, (mtime, mtime))
        os.replace(tmp, lp)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


RETRY_ERRNOS = (errno.EDEADLK, errno.EAGAIN)      # Drive "busy": worth a few short retries before falling back
_NOTES = []                                       # stale notes a caller must surface: [{"path", "why"}]


def _note(path, why):
    _NOTES.append({"path": str(path), "why": why})
    _warn("STALE: %s: %s" % (path, why))


def notes():
    """The stale notes recorded since the last take_notes()."""
    return [dict(n) for n in _NOTES]


def take_notes():
    """Return the stale notes and clear them. A job surfaces each one in its own output (a stale read is never silent)."""
    out = [dict(n) for n in _NOTES]
    del _NOTES[:]
    return out


def _drive_read(drive_path, retries, backoff):
    """Read the Drive file, retrying a Drive-busy error (EDEADLK/EAGAIN) up to `retries` times with a short backoff."""
    for i in range(max(1, retries)):
        try:
            return _read_file(drive_path)
        except OSError as e:
            if e.errno not in RETRY_ERRNOS or i >= max(1, retries) - 1:
                raise
            time.sleep(backoff)


def read_ex(drive_path, local_copy_path=None, retries=3, backoff=1.0):
    """-> (bytes, stale_note or None). stale_note is set when the local copy was used although Drive was newer or could not be
    checked (Drive unreadable): the content may be older than what is on Drive, and the caller must say so (the note is also
    recorded for take_notes()). Otherwise as the module doc."""
    drive_path = str(drive_path)
    lp = str(local_copy_path) if local_copy_path else cache_path(drive_path)
    lm = _mtime(lp) if os.path.isfile(lp) else None
    dm = _mtime(drive_path)
    if lm is not None and dm is not None and dm <= lm:
        try:
            return _read_file(lp), None
        except OSError as e:
            _warn("local copy %s unreadable (%s); trying Drive" % (lp, e))
            lm = None
    try:
        data = _drive_read(drive_path, retries, backoff)
    except OSError as e:
        if lm is not None or (dm is None and os.path.isfile(lp)):
            try:
                data = _read_file(lp)
            except OSError as e2:
                raise DriveReadError("cannot read %s (%s) nor the local copy %s (%s)" % (drive_path, e, lp, e2))
            why = "Drive unreadable (%s), older local copy %s used" % (errno.errorcode.get(e.errno, e.errno), lp)
            _note(drive_path, why)
            return data, why
        if isinstance(e, FileNotFoundError):
            raise FileNotFoundError(e.errno, "no such file on Drive (%s) and no local copy (%s)" % (drive_path, lp), drive_path)
        raise DriveReadError("cannot read %s (%s: %s) and there is no local copy at %s" % (
            drive_path, errno.errorcode.get(e.errno, e.errno), e.strerror or e, lp))
    try:
        _store(lp, data, dm)
    except OSError as e:
        _warn("could not refresh the local copy %s (%s)" % (lp, e))
    return data, None


def read_bytes(drive_path, local_copy_path=None, retries=3, backoff=1.0):
    """The file's bytes (see read_ex); a stale read is recorded for take_notes()."""
    return read_ex(drive_path, local_copy_path, retries, backoff)[0]


def read_text(drive_path, local_copy_path=None, encoding="utf-8", errors="strict", retries=3, backoff=1.0):
    return read_bytes(drive_path, local_copy_path, retries, backoff).decode(encoding, errors)


read_local_first = read_text      # the name the plan uses: read_local_first(drive_path, local_copy_path)


def write_local_copy(drive_path, data, local_copy_path=None):
    """Call right after the job writes a Drive file: the local copy becomes the newest truth. data: str or bytes.
    A failure is said on stderr (the Drive write already happened and must not be lost); returns True when stored."""
    lp = str(local_copy_path) if local_copy_path else cache_path(drive_path)
    if isinstance(data, str):
        data = data.encode("utf-8")
    try:
        _store(lp, data)
        return True
    except OSError as e:
        _warn("WROTE %s BUT COULD NOT WRITE THE LOCAL COPY %s (%s)" % (drive_path, lp, e))
        return False


def local_file(drive_path, local_copy_path=None):
    """A LOCAL path holding the file's current bytes, for tools that need a path (sqlite). Same rule as read_bytes."""
    lp = str(local_copy_path) if local_copy_path else cache_path(drive_path)
    data = read_bytes(drive_path, lp)
    if not os.path.isfile(lp):          # read from Drive and the refresh failed: say so, never hand back a missing path
        raise DriveReadError("read %s but the local copy %s could not be made" % (drive_path, lp))
    del data
    return lp


def local_mtime(drive_path, local_copy_path=None):
    """The local copy's mtime (None when there is no copy)."""
    return _mtime(str(local_copy_path) if local_copy_path else cache_path(drive_path))


def mtime(drive_path):
    """The file's mtime: Drive's when it can be read (a stat does not need the file downloaded), else the local copy's."""
    m = _mtime(drive_path)
    if m is not None:
        return m
    m = _mtime(cache_path(drive_path))
    if m is None:
        raise FileNotFoundError(errno.ENOENT, "no mtime: not on Drive (%s) and no local copy (%s)" % (drive_path, cache_path(drive_path)), str(drive_path))
    return m


def list_names(drive_dir):
    """Names in a Drive folder. When the Drive listing works it is the ONLY source (a file deleted or renamed on Drive must not
    come back from the cache). When the listing itself fails, the local mirror's names are used and the read is flagged stale
    (take_notes()); with no mirror either that is a DriveReadError. A folder missing on Drive and in the mirror -> []."""
    try:
        return sorted(os.listdir(drive_dir))
    except FileNotFoundError:
        derr = None
    except OSError as e:
        derr = e
    cd = cache_path(drive_dir)
    try:
        names = sorted(n for n in os.listdir(cd) if not n.startswith("."))
    except OSError:
        if derr is not None:
            raise DriveReadError("cannot list %s (%s) and there is no local mirror at %s" % (drive_dir, derr, cd))
        return []
    if derr is None:
        return []                         # Drive says the folder is not there: nothing, whatever the mirror holds
    _note(drive_dir, "Drive folder listing failed (%s), local mirror %s listed instead" % (errno.errorcode.get(derr.errno, derr.errno), cd))
    return names


# ---- seeding: run once from an interactive session so the first scheduled run already has local copies ----------------
def seed(out=print):
    """Copy the CURRENT Drive version of every content-read file into drive-cache/: the newest write-up of the default desk,
    the life map, every diary entry, the mover's result.json and the newest snapshot database. Needs a session that may
    download Drive files (a terminal, not launchd). -> (copied, failed); each failure is said, never skipped quietly."""
    import re
    import diary_names
    notes, desk = gc_settings.notes_root(), gc_settings.default_desk()
    files, missing = [], []
    rec = os.path.join(notes, "desks", desk, "records", "context")
    pic = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-%s(-topup[0-9]+)?\.md" % re.escape(desk))
    try:
        names = sorted((n for n in os.listdir(rec) if pic.fullmatch(n)), key=lambda n: os.stat(os.path.join(rec, n)).st_mtime)
    except OSError as e:
        names = []
        missing.append("%s (%s)" % (rec, e))
    files += [os.path.join(rec, n) for n in names[-1:]]
    files.append(gc_settings.life_map_path())
    for d in diary_names.load()["desks"]:
        for dp, _dn, fns in os.walk(diary_names.diary_folder(notes, d)):
            files += [os.path.join(dp, f) for f in sorted(fns) if f.endswith(".md") and not f.startswith(".")]
    files.append(os.path.join(str(gc_settings.gc("mover_dir")), "result.json"))
    snaps = os.path.join(notes, gc_settings.state_subdir(), "snapshots")
    try:
        dbs = sorted(f for f in os.listdir(snaps) if re.fullmatch(r"rig-\d{8}\.db", f))
    except OSError as e:
        dbs = []
        missing.append("%s (%s)" % (snaps, e))
    files += [os.path.join(snaps, n) for n in dbs[-1:]]
    copied, failed = 0, list(missing)
    for p in files:
        try:
            lp = cache_path(p)
            # read_bytes refreshes the copy when Drive is newer or there is none
            read_bytes(p)
            copied += 1
            out("seeded %s -> %s" % (p, lp))
        except (OSError, DriveReadError) as e:
            failed.append("%s (%s)" % (p, e))
    for f in failed:
        out("NOT SEEDED: " + f)
    out("seed: %d copied, %d not seeded" % (copied, len(failed)))
    return copied, failed


if __name__ == "__main__":
    if sys.argv[1:] == ["--seed"]:
        sys.exit(1 if seed()[1] else 0)
    print("usage: python3 local_first.py --seed", file=sys.stderr)
    sys.exit(2)
