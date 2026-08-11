# corpus-map.json — schema v2 (the shared state file for the ingest-1..4 chain)

> The corpus-map is the ONE file the four numbered ingestion skills share. It **is the state machine**:
> a skill figures out what to do next by *querying this file* (`pipeline.py next`), never from memory —
> so you can stop between any two skills and resume cleanly. The canonical definition lives in
> **`pipeline.py`** (`SCHEMA_VERSION`, `CHAT_V2_DEFAULTS`, `BASKET_DEFAULTS`); this doc is the readable
> map + the **column-ownership table** (who writes what). `corpus_map.py migrate` brings a v1 map to v2.

## Shape

```json
{
  "schema_version": 2,
  "source": "world-tags.json",
  "rows":    { "<chat-file>.txt": { ...per-chat columns... }, ... },
  "baskets": { "<basket-name>":   { ...per-basket columns... }, ... }
}
```

- **A CHAT is the tracked unit** (one `rows` entry — carries its rung + fate).
- **A BASKET is the invocation scope** (one `baskets` entry — you run a skill "on basket X").

## Per-chat columns (`rows[<file>]`)

| Column | Values | Owner (writes it) | Meaning |
|---|---|---|---|
| `file` / `conversation_id` / `tags` / `freshness` | — | ingest-1 | identity + low-res tags (v1) |
| `basket` | a basket name | ingest-1 | which basket this chat belongs to |
| `resolution_rung` | `unprocessed → skimmed`/`skim-skip → read-complete`/`deep-complete → committed` | 1→4 | how far down the ladder |
| `status` | `pending`/`in-progress`/`done`/`error` | 2/3/4 | processing state (fail-visible) |
| `scan_summary` | one line (gate-sanitized) | **ingest-2 / SCAN** | the gist a tool-less reader produced from a sanitized SLICE — what the human rules on (NOT a bare title) |
| `scan_guess` | `toss`/`research`/`park`/`null` | **ingest-2 / SCAN** | the machine's best-guess verdict — a HINT for the human, NEVER the ruling. (Optional/additive: absent on a pre-SCAN v2 map, which still asserts clean.) |
| `skim_verdict` | `toss`/`research`/`park`/`null` | **ingest-2 / the HUMAN** | the human's low-res 3-way ruling (toss→declined · research→DEEP-READ · park→deferred). SCAN fills the gist; the HUMAN sets this. |
| `skim_note` | one line | **ingest-2** | `research` carries its scoped deep-read reason |
| `deep_flag` | bool | — | DEPRECATED (superseded by `skim_verdict=research`); unused |
| `extraction` | path/inline (scratch) | **ingest-3** | staged findings — NOT yet in a desk |
| `filing_status` / `verdict` | terminal set (`filed`/`pointer-only`/`deferred`/`declined`) | **ingest-4** only | the human-ruled fate (via `wmb_commit`, gated) |
| `desk` / `learned_note` | — | ingest-4 | where it filed + a one-line note |
| `skim_ts` / `read_ts` / `commit_ts` | ISO ts | 2/3/4 | when each rung ran |

**Rule:** each skill writes ONLY its own columns and asserts the schema on open (`pipeline.py assert`).
A chat is never re-opened at the wrong rung; a human ruling (`filing_status` terminal) is never
re-touched by an earlier skill.

## Per-basket columns (`baskets[<name>]`)

| Column | Values | Owner | Meaning |
|---|---|---|---|
| `basket_status` | `queued → skim-complete`/`skim-interrupted → read-complete`/`read-interrupted → committed` | 1→4 | the loop position (drives `next_basket`) |
| `basket_lock` | `null` \| `"<machine>:<skill>:<iso-ts>"` | 2/3/4 | advisory, self-expiring (TTL ~30m) — the two-machine race guard |
| `sort_order` | int | ingest-1 | processing order |

## The loop (how the skills chain)

`ingest-1` (SORT) runs WIDE once (fills `basket`, seeds `baskets`, sets the full v2 schema). Then, per basket:
`ingest-2` (SCAN: slice-read → human rules) → `ingest-3` (DEEP-READ) → `ingest-4` (COMMIT) → back to `ingest-2` (SCAN) on `next_basket`.
Each skill ends by printing `pipeline.py suggest --skill ingest-N --basket B` — the next pointer,
**computed from this file**, so the chain self-heals and is resumable.

## Residency + the race
The corpus-map holds personal chat titles (medical, etc.) → it lives on **Drive, never git**. Writes
are atomic (tmp-then-rename). Cross-basket concurrent writes from two machines still rely on the
`basket_lock` + "one machine per corpus at a time" — an accepted residual for a one-person system
(visibility, not HA). `wmb_commit`/`pipeline` do whole-file read-modify-write; do not run two skills
on the same map on two machines simultaneously.
