# The placement panel — imitate this exactly

The reference for how the `/save` panel looks, every time. The organising idea is **where-first,
grouped by destination**: the bucket is a header the person reads once, and the items sit under it.
Nobody should have to read to the end of a sentence to find out where something lands.

## The rules

1. **Group by destination. The bucket is the header, printed once.** Never repeat a per-item kind
   label — say "RECORDS" once, then list what goes there underneath.
2. **Order by permanence: CANON first**, then RECORDS, then CURRENT, then the rarer buckets (JOURNAL ·
   DEBT-LOG · LESSONS · TO-DO) **only when something actually lands there.**
3. **Always show CANON, even when empty** — print *"— nothing going here this time."* so *"nothing is
   touching your permanent truths"* is said out loud rather than left silent. Hide the other empty
   buckets.
4. **Name the canon altitude — never the bare word.** Canon lives at several levels, and a person can
   have canonical files at all of them, so "CANON" alone does not say **which** permanent-truth file is
   being touched. Label it: `CANON · global` · `CANON · project (<name>)` · `CANON · subject (<area>)`.
   Use the human-readable level, **not the file path** — the path appears only at the pre-write check.
   If canon items span several altitudes, sub-group them under the CANON header, one altitude per line.
5. **Canon is lifted out — never a one-liner in the flat list.** See the block below.
6. **Every other item is a number + a short bold name + one plain sentence.** The number is **global**
   across the whole panel, in bucket order, so approval can be by number. One line each. **No paths on
   this glance.**
7. **Mark anything sensitive** with a small `· private` on the name line. Nothing more.
8. **End with the pending banner, verbatim** — the very last lines of the output, so somebody scanning
   several windows can see this is not done without reading a word of it:

   ```
   ┌──────────────────────────────────────────────────────┐
   │  🟨🟨🟨  NOT SAVED YET — WAITING FOR YOUR APPROVAL     │
   └──────────────────────────────────────────────────────┘
   ```

   **A completed save never prints it.** It ends with the coverage note instead.

**The test:** reading only the bucket headers and the bold names tells them where everything is going,
in about two seconds. Detail is one step deeper, never in the way.

---

## The worked example

**Here's where it's all going:**

🔒 **CANON** *(your permanent core truths)*
— nothing going here this time.

📁 **RECORDS** *(dated notes / reference)*
1. **The old pricing model** — the whole "what to charge and why" working-out, stamped superseded.
2. **Venue comparison** — the two shortlisted options and what each costs, stamped low-confidence.

📌 **CURRENT** *(live project state)*
3. **Status correction** — the one-paragraph summary of this project was slightly off; fixed in place.

📓 **JOURNAL** *(the diary)*
4. **Today's entry** — a short account of what happened today and why.

📝 **LESSONS** *(what the system learned about itself)*
5. **Lessons log** — an honest note on where I slipped today.

✅ **DEBT-LOG** *(loose ends)*
6. **Loose ends** — two things to pick up later.

**What needs you:**
1. **Records (1–2)** — save?
2. **Everything else (3–6: the state edit and the logs)** — save?

Nothing writes until you weigh in. Approve, correct or cut by number. On your OK I show the exact file
paths and full content for each in a final pre-write check, then write.

```
┌──────────────────────────────────────────────────────┐
│  🟨🟨🟨  NOT SAVED YET — WAITING FOR YOUR APPROVAL     │
└──────────────────────────────────────────────────────┘
```

---

## When canon *is* being touched

It is lifted out into its own framed block. The proposed text appears **verbatim and in full — never
abbreviated, summarised or truncated** — and below it the three things a canon line has to earn.

```
╔═══════════════════════════════════════════════════════════════╗
║  📜  PROPOSED FOR CANON — permanent truth, pending your        ║
║      sign-off                                                 ║
║                                                               ║
║  "Sessions run from the project folder, never from a folder   ║
║   inside it. The harness only looks in the folder it was      ║
║   opened in, and never upwards."                              ║
╚═══════════════════════════════════════════════════════════════╝

  WHERE it lands:
    CANON · project (setup)  →  state/projects/setup/canon/current.md
    (this project's permanent-truth file — read by every session
     that picks the project up)

  WHY it belongs in canon — it has to earn this:
    • 2-year test: PASS — a property of how the tool works, not a
      number that expires.
    • What keeping it buys: stops the single most common setup
      failure being rediscovered from scratch. Wrong or missing,
      and every fresh install loses an hour to it.
    • Conflict scan: NEW — 0 existing lines duplicate or
      contradict it (4 canon files read).

  ── Approve to write it into canon? It is permanent once vetted. ──
```

**Hard:** the text inside the frame is the exact proposed line, never abbreviated. More than one canon
item → one full block each; **never merge or shorten them.** The path shown is the same one the
conflict scan read. All three justifications are mandatory — **a candidate that cannot fill all three
does not belong in canon.** Route it to RECORDS instead.

The three, precisely:

- **The 2-year test** — pass or fail, plus one line. Still true in two years, or a datum that expires?
- **What keeping it buys** — what it steers downstream, and what breaks if it is wrong or missing.
- **The conflict-scan verdict** — NEW / DUPLICATE / CONFLICT, from `canon_conflict_scan.py`, with the
  number of canon files it actually read.
