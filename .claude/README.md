# .claude/

This folder is how Claude finds the skills in this repo.

`skills/ingest` is a symlink pointing at `../../system/skills/ingest`. That's what makes
`/ingest` work the moment you open this folder — no install step, no configuration, and it
works wherever you put the folder because the link is relative.

You don't need to touch anything in here.
