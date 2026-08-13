# This folder is a leftover. Your writing is NOT here.

**Everything you write lives in `data/`**, in the folder you opened, beside this one.

This directory is left over from an earlier layout, before the tool started
unpacking into the folder you open. Until 2026-08-12 your notes did live here.
They do not any more, and nothing reads this folder.

**If you have put anything in here, move it into `data/`** — otherwise no command
will ever find it. Nothing is lost either way: git ignores both folders, so an
update cannot touch what you wrote in either place.

You do not need to create anything by hand. Run `/ingest` and it builds the shape
inside `data/` as it goes: a folder per subject, and inside each one a place for
the things that stay true and a place for the things that happened on a date.
