# If you ran `/ingest` before August 11

Two bugs were fixed today. Both were silent — the tool told you it had saved your work when it hadn't.
If you ran `/ingest` before today, some of your work may be sitting somewhere you can't see.

**You do not need to re-run `/ingest`. Nothing here asks you to start over.**

---

## Do this

**1. Get the fixes.** Open the tool folder in Claude and say:

&nbsp;&nbsp;&nbsp;&nbsp;*"check if there is an update to my brain and install it"*

That's the same update you'd do any other time. It replaces the tool folder and cannot touch your notes —
they live somewhere else entirely.

**2. Then find out whether any of this touched you.** In the same window:

&nbsp;&nbsp;&nbsp;&nbsp;*"run the notes check"*

or, in a terminal in that folder:

&nbsp;&nbsp;&nbsp;&nbsp;`bash system/tools/check-my-notes.sh`

It reads your files and tells you what it sees, in plain words. **It changes nothing** — it never moves,
writes, or deletes anything. Run it as often as you like.

If it says *"Nothing to do,"* you're done. Close this page.

---

## What it's looking for, and what to do about each

### Notes filed under a folder with the wrong name

The most common one. Your notes were saved correctly — just under the name of a *file* instead of the
name of your history. So the tool wrote them, then looked somewhere else for them, and each sitting
started with no memory of the last.

**Nothing was deleted.** The script tells you which folder and how many notes are in it, and gives you
the copy command with your real paths already filled in. **Copy, don't move** — look in the new place
first, and delete the old folder later, or never.

### Notes that were dropped and can't come back

The harder one, and I'd rather say it plainly than let you find out later.

When a pile's notes file **didn't exist yet**, the notes you'd just written were thrown away and a blank
template was saved instead. **That text was never written to disk anywhere. Nothing recovers it —
not this script, not a better one, not later.**

The script lists any notes file with no dated entries in it. If you never worked that pile, that's
correct and expected. **If you did work it, those rulings are gone, and re-screening that pile is the
only way back.**

I'm sorry. Knowing *which* piles is worth more than not knowing anything went missing — which is where
everyone was until today.

### Things you approved that never got filed

If your canon files are empty, that's the third thing fixed today, and it isn't a mistake you made.

The old design parked everything you approved in a `records/proposals/` folder, waiting for a second,
separate act to move it into canon. **That second act was never built.** So you could say yes fifty
times and end up with empty files.

**Your approvals aren't lost** — the yes is recorded inside each file. The script counts them for you.
Two ways to finish the job:

- **By hand.** They're small markdown files. Anything still true in two years goes into the
  `canon/current.md` of the folder it belongs to. Anything true only *right now* is a record — leave it.
- **Or with your session.** Open a window in your repo and say: *"Read my `records/proposals/` files and
  help me decide which belong in canon and at what level. Show me each one before writing anything."*

**Don't bulk-move them all into one file.** Canon gets loaded into every conversation you have, so a
file stuffed with things that expire is worse than an empty one. That's the whole reason it stays small.

### A canon file at the top

New today: `canon.md` at the top of your notes — the handful of things true for **every** conversation
on any subject. Your name, how you like to be spoken to, how you want the system to work. If you don't
have one, the script tells you the one command that makes it. It never overwrites anything.

---

## What was actually fixed

- Your notes are now written whether or not the file already existed.
- After writing, the file is **read back** and checked that your words are really in it. If they aren't,
  it stops and says so instead of carrying on.
- The folder is worked out from your corpus, and when it can't be worked out the tool **refuses** rather
  than guessing. **A file saved to the wrong place looks exactly like success** — which is why none of
  this was visible to anyone.

From today, `/ingest` also writes canon directly as you go, shows you your folders before it builds
them, and asks you once at the end whether the permanent things look right.

Thanks to the person who found and reported the first two. Exact line numbers, a repro, and a suggested
fix — better than most paid QA.
