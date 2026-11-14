---
title: "Managed File Frontmatter Spec: history log"
what: "Retired and moved text from managed-file-frontmatter.md, kept verbatim and dated so nothing is lost. Not read in normal use."
read_in_normal_use: false
base_file: "system/schemas/managed-file-frontmatter.md as frozen 2026-11-14 (freeze-2026-11-14, V2 HEAD 0037ccb)"
created: 2026-11-14
status: "draft — lands with the fine-china edit pass, round three"
---

# Managed File Frontmatter Spec: history log

Each entry is one passage moved out of the document on 2026-11-14 (round three 'lowerbooks'). Line numbers are the frozen base's. The original is copied word for word inside each fenced block. Append-only.

## 2026-11-14 · MOVE · lines 113-120 · G3-101

- Reason: Settled (c) "managed-file-frontmatter: repoint to canon/data-layout.md"; round two B4 (`state/` and `state/current.md` retire); K6, K10 — the old naming table. ⛔ retired 2026-11-11 (round two B4); kept as history.

~~~~
| Location | Pattern | Example |
|----------|---------|---------|
| `state/projects/{slug}/records/{type}/` | `YYYY-MM-DD-{slug}.md` | `2026-03-25-discovery.md` |
| `state/projects/{slug}/state/` | fixed names | `current.md`, `open-loops.md` |
| `state/projects/{slug}/` | `brief.md` (the project doc) | `<notes>/state/projects/widget/brief.md` |
| `state/projects/{slug}/canon/` | fixed name | `current.md` |
| `state/projects/{slug}/sources/` | subdirs: `inbox/`, `reference/`, `research/` | `2026-03-25-transcript.md` |
| `state/projects/{slug}/_registry.md` | fixed name | — |
~~~~

## 2026-11-14 · MOVE · lines 124-135 · G3-102

- Reason: "stale documents fixed ... never deleted"; K10; round two B4 — it writes the `daily` type this file dropped 2026-08-11 and `state/current.md`, which retired. ⛔ retired 2026-11-11 (round two B4); kept as history.

~~~~
## Desk-Specific Write Rules

### Planning

Every session:
- `records/daily/{YYYY-MM-DD}.md` — session wrap-up
- `<notes>/state/current.md` — update live posture
- `<notes>/state/open-loops.md` — update domino list
- `records/decisions/{YYYY-MM-DD}-{slug}.md` — only on durable state change

No logs, no insights, no proposals.

~~~~

