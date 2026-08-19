# What we know is not fixed yet — and how a fix reaches you

**Written 2026-08-13, at the point this library went out to the class.**

This page exists because the honest thing is to tell you what is still rough, rather than let you
find it. The posture is **push forward, not roll back**: when something breaks we fix it and push,
usually the same day. That is only credible if you know what to expect and how to reach us — so
that is what this page is.

## The channel — it is already proven, not a promise

Report anything through **GitHub Issues** on `LifehackMethod/lifehack-brain`. If you are not sure how,
ask your brain: *"help me report a bug"* — there is a `REPORT-A-BUG.md` in the repo that walks it
through filing one for you, including gathering the details we need.

**This is not theoretical.** In the first week: **eight issues came back through GitHub, and three
were closed by a collaborator** — someone who was not the author, reading the code cold. The loop
works.

**To get a fix, run `git pull`.** ⛔ Do NOT delete the folder and re-clone — that throws away the
`.brain-root` line, which is the only thing connecting this folder to your AI Brain.

## Known unfixed, ranked by how likely you are to hit it

1. **Windows is the weak platform, and we know it.** Five of the first five installs were on Windows
   and every one of them stalled somewhere different. A whole class of hardcoded-path bug was swept
   this week, but Windows remains the least-tested surface. **If something fails on Windows, it is
   more likely our bug than your mistake — please report it rather than assuming you did it wrong.**

2. **A guard can block a read it should allow.** The safety rails occasionally refuse something
   harmless because they match on a name rather than on what a command actually does. If you get a
   "BLOCKED" message that makes no sense for what you were doing, that is a false alarm on our side.
   Report it with the exact message.

3. **One security rail is narrower than it looks.** The wall that keeps untrusted text away from the
   main session can be walked around by a symlink, because it inspects the text of a command rather
   than the filesystem. It holds for ordinary use and for accidents; it is not a hard boundary against
   someone deliberately trying. Stated plainly so nobody over-trusts it.

4. **Phone notifications do not work on Windows.** The notifications helper depends on a Unix-only
   piece of Python. It is not a path bug and it is not a quick fix. Notifications are optional and off
   until you set them up, so this costs you nothing unless you wanted them.

5. **Some skills need accounts you have not connected.** Anything touching Google — calendar, tasks,
   email — needs you to connect your own account first; `INSTALL.md` walks through it. Web search
   needs a free API key. **Until then those skills will tell you they cannot proceed. That is them
   working correctly, not failing.**

## How fast a fix comes back

A path or crash bug: same day, usually within hours of a clear report. Something structural: it goes
on the list and you will see it in the repo's issues. **Nothing is fixed in secret** — the commit
history is the whole record, and you can read it.

## What we would most like from you

The single most useful thing is **the exact error text and what you were doing when it happened**. A
screenshot of the message beats a description of it. Second most useful: telling us when something was
merely *confusing* — that is a real defect in a tool meant for people who have never opened a terminal,
and it is the kind we are least able to find ourselves.

---

## What was actually tested before this reached you — added 2026-08-13

**Every one of the 32 tools was run, not just read.** A fake user drove each one start to finish and each
returned a real verdict: **24 worked · 4 failed · 3 could not run without an account you have not
connected yet · 1 did not return.** **All four failures were fixed before this went out.** The three that
could not run are the Google-connected ones, and that is them behaving correctly, not breaking.

**Then the whole thing was installed from scratch, the way you will install it** — a clean copy fetched
into an empty folder, `INSTALL.md` followed top to bottom, a small pile of notes ingested, and a save and
a read run against the result. The install steps all passed, including the one that matters most: after
setup, `git status` shows nothing at all, which is how you know none of your own writing is staged to go
anywhere.

### One real problem was found doing that, and fixed the same hour

**The safety catch was guarding the wrong folder.** The check that refuses to let your own notes into the
repository was written when your writing lived in a folder called `memory`. Everything moved into `data`
on 2026-08-12, the ignore-list was updated that day, **and this check was not.** A test deliberately
forced a note into the repository and the commit was accepted.

To be clear about the actual exposure: this only ever mattered if something went out of its way to force
a file in — normal use was never affected, because `data` is on the ignore list either way. But the catch
is precisely the backstop for the abnormal case, and it was not doing its job. It now is, and that was
proven by repeating the same attack and watching it get refused.

**If you cloned before 2026-08-13, run `git pull`.**

### Three more things we know about, added to the list above

6. **Some text loses its line breaks when a tool reads it for you.** The safe reader that strips hidden
   characters out of a document also flattens paragraphs into one block. The words are all there and
   nothing is lost; it just reads badly. Cosmetic, and on the list.

7. **One of the auditing tools claims a restriction we have not proven.** It says it cannot modify
   anything. We believe that is true and have not independently verified it. Stated here rather than
   left as an assumption you would have no way to check.

8. **A few tools do not yet say where they put what they write.** Most of them declare it plainly. A handful
   are still vague about it, so if one writes something and you cannot find it, that is us, not you —
   ask, and we will tell you exactly where it went.

### The honest boundary on all of the above

**None of this was found by guessing.** Everything on this page is either something a real install did in
front of us, or something we know is unfinished and chose to tell you rather than hope you would not hit
it. **What we have not done is run this on every version of Windows that exists.** Five installs, five
different stumbles, all fixed — but five is a small number, and yours may be the sixth kind. That is the
whole reason this page opens by telling you how to reach us.

## Who fixes it, and can you fix it yourself — added 2026-08-13

**A small group of maintainers looks after this repository**, and any one of them can take a report and
push a fix. It is not routed through one person, so a bug does not sit waiting on somebody's calendar.

**You are welcome to fix it yourself.** If you find a bug and you can see the repair, open the issue
*and* send the fix as a pull request — both, in the same breath. That is genuinely useful and we would
rather have it than not.

⚠ **A pull request does not go straight in.** Every change is reviewed and approved by a maintainer
before it becomes part of what everyone else pulls. That is not distrust — it is the only thing standing
between one person's good intention and thirty people's working installs. Expect a read, possibly a
question, and then a merge.

**If you would rather not touch the code at all, that is completely fine and is the normal path.** Report
it in plain words and let us do the rest. The most useful bug report is still the exact error text and
what you were doing — not a diagnosis.
