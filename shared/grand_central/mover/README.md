<!-- origin: 92a9739:mover/README.md -->
# The mover : a drop box that moves mail, and nothing else

**What it is.** A small Google Apps Script ("GC-mover") plus two Mac scripts. The Mac writes a request file into a
Drive folder; every 15 minutes the script reads it, moves the listed messages, and writes back what it did.

## What it can do
- Five actions only: **add a label**, **remove a label**, **archive** (archive = remove INBOX, nothing else), **trash** (adds the TRASH label to approved always-junk; recoverable, Gmail empties Trash itself; max 1,000 ids per request) and **untrash** (removes TRASH; the undo of trash).
- Works on Gmail message IDs you give it, in bulk (1,000 ids per call).
- Undo: every batch is logged as its own small file in the folder, `move-<request_id>-b<NNNN>.json` (one JSON object:
  ts, request_id, batch, action, op, label, count, `undo`) with its inverse action. `result.json` `undo_log` gives the
  pattern. (Older runs wrote `moves-YYYY-MM.jsonl`; those files stay valid, one JSON object per line, and are never
  touched again.) An undo entry is already in request-action shape, so submitting the inverse actions as a new request reverses the move
  (undo of archive is `addLabel` of `INBOX`).
  `addLabel` of `INBOX` is the single allowed system-label exception, used only to undo an archive; every other
  system label is refused.
  Be honest about what undo is: it restores what a request did, and it cannot know whether a message already had a
  label before the request (undoing an `addLabel` removes the label even if the message carried it already).

## What it can't do
Read mail, send, forward, spam, delete or empty Trash, create or delete labels, touch settings or filters, call the web.
The label must already exist as a user label; system labels (TRASH, SPAM, UNREAD, ...) are refused. Any unknown
op or field refuses the **whole** request. A static test fails if the code, or its scopes, ever grow past this.
Scopes, exactly: `gmail.modify` (needed for batchModify), `drive.file`, `script.scriptapp`.

## The lock
**Nothing on the Mac can edit the script.** There is no web address and no execution API (the manifest has neither;
a test fails if they appear). The only way in is the request file, and the script treats its contents as data to
validate, never as instructions. The script owns its folder (`drive.file` only covers files the script made) and
finds `request.json` / `result.json` by name. The Mac must write `request.json` in place (never temp-then-rename),
which `mover_request.py` does. Known limit: the lock is complete only once the old full-access Gmail login is removed
from the Mac (the cut-over).

## Google limits: tracked, not enforced
Google's ceilings (confirmed 2026-11-12, `limits.py`): timer runtime 90 min/day, 6 min per run, email read/write
20,000/day, properties read/write 50,000/day, 1,000 ids per batchModify. We do **not** impose our own quota.
Instead every run logs `runtime_ms, gmail_calls, ids_modified, drive_ops, properties_ops` into `result.json`
(30 days kept). `mover_usage.py` totals them per Pacific day and writes a status tile: **WARN at >=50% of any Google
ceiling**, otherwise OK. That tile alerts the owner and the system.

Two things that look like limits but are not quota rules:
- `MAX_IDS_PER_REQUEST` (5,000) and 20 actions per request: a typo guard on each request.
- Each run stops at about 2 minutes and carries the rest over (a cursor in Script Properties), so Google's 6-minute
  hard stop never cuts a batch in half. Also at most 10 batch calls per run.

## Using it
```
python3 mover_request.py actions.json            # dry run (default): validate + print the summary
python3 mover_request.py actions.json --write    # write request.json in place
python3 mover_usage.py --tile <path-to-tile.json>   # both read the Drive folder from your setup gc.json key mover_dir
bash push.sh                                     # owner-run only: the one way the mover is created or pushed (needs clasp and your .clasp.json)
```
`actions.json` is a list like `[{"op":"addLabel","label":"Projects/Alpha","ids":["18c..."]},{"op":"archive","ids":["18c..."]}]`.
A request is applied once (by `request_id`); `result.json` shows `status` (done, in_progress, refused, failed).
"Request changed" is judged by `request_id` plus a hash of the **parsed** request (sorted keys, no whitespace), never the raw bytes, so a multi-run request survives Drive returning the same file as text, bytes or an object. `result.json` keeps `errors_history` (last 20 errors: ts, request_id, batch, error) plus `last_error`; the cursor is saved before the move log is written, and a move-log failure is recorded, not fatal.

## Pause
Run `pause()` in the Apps Script editor (sets Script Property `PAUSED=1`): `run()` then does nothing and logs
"paused". `resume()` clears it. `teardownTriggers()` removes the timer; `setup()` is idempotent and reinstalls it.

## Tests
`python3 -m unittest discover -s tests` (needs node for the Code.gs tests; no network, no Google).
Drive access uses the Advanced Drive service v3 (`Drive.Files.*`), never `DriveApp`, because `DriveApp` needs the full drive scope and we hold only `drive.file`.

## Setup (yours, never in the plugin)
The Drive folder the script owns is `mover_dir` in your setup `gc.json`. The Apps Script `scriptId` lives in your own `.clasp.json` (kept in your setup, e.g. `<personal code folder>/tools/grand-central/mover/.clasp.json`); `push.sh` copies it in from `$CLASP_JSON` or that folder. Fixed words in tests are invented placeholders.
