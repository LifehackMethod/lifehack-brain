<!-- carried forward 2026-11-17 from the engine's earlier private working branch (plan step 4M.6), scrubbed by the personal-values lock; starting material for plan step 4P.1, not yet checked against the code -->
# Source contract: what any new source must hand over

A "source" is anything that produces things the rig should know about (Gmail, Calendar, Tasks today; others later).
Adding one must not change `items`, `item_events` or the readers of them. To qualify, a source hands over all of this.

## 1. Identity
- `source`: a short lowercase name, fixed forever (`gmail`, `calendar`, `tasks`).
- `source_id`: the source's own stable id for one thing. `(source, source_id)` is unique; re-handing the same pair updates, never duplicates.
- `kind`: what the thing is (`email`, `event`, `task`, or a new plain word).

## 2. The common shape (one `items` row)
| field | rule |
|---|---|
| `title` | subject / summary / title; short; may be NULL |
| `person_address` | the one address that matters (sender, organizer), lowercased; NULL if none |
| `occurred_at` | ISO-8601 text: when it happened or starts. Sortable as text, so UTC `Z` or the source's own offset form, consistent per source |
| `due_at` | ISO-8601 text if it has a due date, else NULL |
| `status` | the source's own state in plain words (`inbox`, `confirmed`, `needsAction`) |
| `created_at` | set by the rig, not the source |

## 3. Thin detail, by link
The raw row stays in its own table (`messages`, `calendar_events`, `tasks`, or a new raw table the source owns). The source adds one
small table `item_<source>(item_id PRIMARY KEY, <raw_id> UNIQUE, ...)` that points at it. Never copy raw columns into `items`.
The raw table's rows have already passed the security gate before they are stored (Sentinel; a stranger's words are scanned first).

## 4. History
Every state change is one `item_events` line: `item_id, at, kind, detail, actor`. Kinds in use: `arrived`, `labeled`, `archived`,
`replied`, `returned`. A source may add kinds; names are plain words. The table is append-only: triggers refuse UPDATE and DELETE.
A correction is a new line, never an edit. `detail` is a short note, never body text.

## 5. Bulky text
Anything long (email bodies, event descriptions, documents) is a file in the `handoff/` folder under the engine's data root (found through the shared path helper), local only,
never Drive, never in the database. The database holds a `text_pointers` row: `path`, `sha256`, `bytes`. `add_text_pointer`
refuses paths outside that folder.

## 6. Freshness and failure
- Update `source_state(source, last_success_at, rows)` on every successful pull.
- A failed item goes to `errors`, a gated item to `quarantine`; neither becomes an `items` row.

## 7. Backfill and tests
- Provide a backfill that is idempotent (running it twice changes nothing) and whose count equals the raw table's row count.
- Add a test: counts equal raw rows, re-run is a no-op, links resolve.
- All access goes through `store_items.py` functions; nobody passes SQL.
