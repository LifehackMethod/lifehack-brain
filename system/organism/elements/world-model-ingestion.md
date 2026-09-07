---
element: world-model-ingestion
maturity_label: LIVE
record_type: organism-element
altitude: index-line
---

Two-skill stack for mining and promoting personal chat history into active canon: `/ingest` (Vera the Curator — one skill, four phases each a unit of human attention: SORT → SCAN → DEEP-READ → PLACE across a ChatGPT export; the separate filer skill folded into `/ingest` as `phases/4-place.md` on 2026-08-05, confirm-gated on every placement) and `/chatgpt-historical` (human-in-the-loop promotion of ChatGPT-era facts into active desk canon, one approved write at a time). Both live under `.claude/skills/ingest` and `skills/chatgpt-historical`; the multi-agent tagger/reader/conclusions agents are the untrusted-content isolation layer beneath them. Normative behavioral contract: `.claude/skills/ingest/SPEC.md`. Whether `skills/chatgpt-historical` resolves from this repo's root as written is answered on its own line immediately below and in the CITATION BANNER that follows — not on this descriptive line.
⛔ `skills/chatgpt-historical` does not resolve from this repo's root as a citation: the skill genuinely ships, but only from the operator's own machine install, outside this repo — see the CITATION BANNER below, including its 2026-09-07 correction, for the full history.

> **CITATION BANNER — what this page names that is not here** (migration note, 2026-08-15).
> The line above describes the donor system as it was, and it is kept as written. The marker records what
> happened AT THIS DESTINATION; it does not change the description.
>
> ⛔ ~~`/chatgpt-historical` is not a skill here. It is one of the personal/desk skills deliberately held back
> from this migration and it moves in a second migration that has its own plan and does not exist yet. So the
> stack described above ships as ONE half: `/ingest` is here and running; the promotion half is not.~~
>
> **⚠ CORRECTED 2026-08-25:** `/chatgpt-historical` now exists. Verified this session: `~/.claude/skills/chatgpt-historical/SKILL.md` is present (11,832 bytes, real frontmatter and content, directory dated 2026-08-22). The struck text is left visible because it was true of the donor/this page when written; it stopped being true once the skill landed. The stack now ships as BOTH halves: `/ingest` and `/chatgpt-historical` are both here and running.
>
> **⚠ CORRECTED 2026-09-01:** ⛔ the line above's bare `skills/ingest` and skills/chatgpt-historical do not resolve from this repo's root as written — they are the
> donor's repo-relative form (missing the `.claude/` prefix for `ingest`). ~~Verified this session: `/ingest`
> ships from the installed plugin at `.claude/skills/ingest/` (plugin root, confirmed under
> `~/.claude/plugins/marketplaces/lifehack-brain/`); ~~`/chatgpt-historical` ships from the person's own
> `~/.claude/skills/chatgpt-historical/`, per the correction just above (this half is accurate — confirmed
> absent from this repo's own `.claude/skills/` this session too). Two different homes: `chatgpt-historical`
> is genuinely outside this repo; `ingest` is NOT.
> ⚠ **THIS 2026-09-01 CORRECTION IS ITSELF WRONG for `/ingest` (BUG window, 2026-09-07):**
> `.claude/skills/ingest/SKILL.md` (322 lines) and `.claude/skills/ingest/SPEC.md` (2302 lines) are BOTH
> tracked in THIS repo, confirmed by `git ls-files` and direct read this session. `/ingest` does not ship
> "only from the installed plugin" — it is a repo-tracked skill right here. Likely cause: the 2026-09-01
> audit tested the bare `skills/ingest` (missing `.claude/`), found nothing literal, and wrongly
> generalized non-existence in this repo — the same defect pattern found across this cluster (see
> `archivist.md` for the fullest write-up).
>
> **⚠ CORRECTED 2026-09-07:** ⛔ the 2026-08-25 correction above checked the WRONG SURFACE for `/chatgpt-historical`.
> "Verified this session" there meant the operator's OWN machine install — genuinely present, 11,832 bytes, real
> frontmatter and content, confirmed again this session at ~/.claude/skills/chatgpt-historical/SKILL.md — never
> THIS REPOSITORY's own .claude/skills/. Confirmed this session: no `skills/chatgpt-historical` directory exists
> here, and no chatgpt-related entry of any kind exists anywhere under this repo's own skills folder. So the skill
> is real on the machine and genuinely absent from the repo — the 2026-08-25 correction asserted the machine half
> as though it settled the repo half, and it does not. This does not conflict with the 2026-09-01 correction just
> above (which separately caught the missing `.claude/` prefix on the bare citation form): that correction's own
> conclusion — "`chatgpt-historical` is genuinely outside this repo" — was right, and this note only makes
> explicit why the 2026-08-25 verification could never have shown otherwise. Both citation forms stay ⛔ here:
> absent from this repo, present only on the operator's own machine.

### INTENT: recover the useful judgment buried in the operator's personal chat history and promote it into active canon, one human-confirmed placement at a time — never a bulk, unvetted dump.

> INDEX-LINE ONLY — no longer inactive as of 2026-08-06 (the skill is built and running on a live corpus); expand to a full entry only if it proves load-bearing.

generated_from: .claude/skills/ingest/SKILL.md, skills/chatgpt-historical/SKILL.md
