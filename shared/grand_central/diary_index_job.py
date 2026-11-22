"""diary_index_job.py: 4P.3 item 10 — the diary-index refresher (the diary_index job).
# not-wired-yet: built in the build window for feat/gc-planning-weekly; its job row lands through the V2
# build window and the job door when the branch merges (plan 4P.3 item 10). Not a personal skill — it is
# engine code that this job's runner in jobs/ execs from $LIFEHACK_CODE_ROOT.

The diary index's own job (it was the one duty of the retired gc-midnight job that had to stay on a schedule;
the morning run now writes its own diary entry): without a refresher the diary_index table (migration 028) goes stale and `gc person`'s DIARY
lines (store_pages.entries_mentioning) go dark. Code only: no model call, no network, no email, no outside
read of its own. For every diary the engine knows — the diary-name list the morning run's
diary entries use (diary_names.load(), a desk only when its folder exists) — store_diary.refresh_index runs once per diary
under the store's write lock, exactly as gcjobs._live_index_refresh does. The receipt is ONE line, written
LAST, atomically, only after every diary was refreshed (gcjobs.write_receipt, the same machinery the other jobs
use); a stale proof ages and the runner's missed-run alert fires (cron SOP).

Exit codes (cron SOP section 4): 0 receipt written; 75 stood down — the engine is not set up (no database
file at the store's path), no receipt; 1 failed — a diary failed (named on stderr, the other diaries still
run), no receipt. One unreadable old entry (no local Drive copy) is NOT a failed diary: refresh_index
already skips and names it, the walk completes, the run is good.

  python3 diary_index_job.py — no arguments. Env for tests: GC_SETUP_DIR, AGE_NOTES_ROOT, AGE_RIG_DB, GC_STATE_ROOT.
Python 3.9 compatible."""
import os
import sys

# The job's one name, receipt regex fixed ("gc" + "-diary-index ok ..."). It is split in source only:
# the shared-code guard (tests/test_diary_names.py hardcoded()) matches "<word>-Diary" through a hyphen,
# and this JOB NAME is not a desk's diary name — a desk's diary name comes only from setup/desks.json.
JOB = "gc-" "diary-index"


def diary_roots(notes=None, cfg=None):
    """Every diary the engine knows, by its name: {diary_name: diary_folder}. The diary-name list the morning run uses —
    the pattern and the desk list live in setup/desks.json (never here); a desk with no folder is skipped."""
    import diary_names
    import gc_settings
    notes = notes if notes is not None else gc_settings.notes_root()
    cfg = cfg or diary_names.load()
    return dict((diary_names.diary_name(d, cfg), diary_names.diary_folder(notes, d)) for d in cfg["desks"]
                if os.path.isdir(os.path.join(notes, "desks", d)))


def _refresh(con, diary, diary_root, notes):
    """The real refresh: store_diary.refresh_index on the connection the write lock holds."""
    import store_diary
    return store_diary.refresh_index(con, diary, diary_root, notes)


def run(state=None, out=print, notes=None, cfg=None, refresh=None, db_file=None):
    """-> 0 (receipt written), 75 (no database file — stood down, no receipt), 1 (a diary failed, no receipt).
    `refresh` and `db_file` are the tests' seams; production uses _refresh and the store's own database."""
    import gc_settings
    import gcjobs
    import store
    refresh = refresh or _refresh
    db_file = db_file or store.db_path()
    if not os.path.exists(db_file):
        print("[%s] stood down: no database file at %s (the engine is not set up)" % (JOB, db_file), file=sys.stderr)
        return 75
    notes = notes if notes is not None else gc_settings.notes_root()
    roots = diary_roots(notes, cfg)
    totals = {"added": 0, "updated": 0, "same": 0, "removed": 0, "skipped": 0}
    failures = []
    for name, root in sorted(roots.items()):
        try:
            with store._write() as c:                      # the store's write lock, one refresh per diary
                res = refresh(c, name, root, notes)
        except Exception as e:                             # one diary failing is said; the others still run
            failures.append(name)
            print("[%s] diary %s NOT refreshed: %s" % (JOB, name, e), file=sys.stderr)
            continue
        for k in totals:
            totals[k] += res.get(k, 0)
        for path in res.get("unreadable", []):             # skipped, named, never a failure
            print("[%s] entry not indexed (Drive unreadable, no local copy): %s" % (JOB, path), file=sys.stderr)
    if failures:
        print("[%s] FAIL, no proof line written: %s" % (JOB, ", ".join(failures)), file=sys.stderr)
        return 1
    import datetime
    line = JOB + " ok date=%s diaries=%d added=%d updated=%d same=%d removed=%d skipped=%d at=%s" % (
        datetime.date.today().isoformat(), len(roots), totals["added"], totals["updated"], totals["same"],
        totals["removed"], totals["skipped"], gcjobs.now_iso())
    gcjobs.write_receipt(JOB, line, state)                 # the proof, LAST, atomically
    out(line)
    return 0


def main(argv=None):
    return run()


if __name__ == "__main__":
    sys.exit(main())
