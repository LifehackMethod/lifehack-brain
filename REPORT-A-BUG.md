# When something breaks — tell me directly

You already have your Lifehack Brain installed. This adds one thing: when something goes wrong, you can
say **"file a bug"** and it lands on my desk, with everything I need to fix it, without you having to
describe it.

This is how the last two bugs got fixed. One of you hit a problem on Windows, filed it this way, and it
was fixed the next day. That only works if I can see the actual error rather than a description of it.

**You need one thing: a free GitHub account.** That's the only new requirement. Two minutes, no card,
nothing to install on the website's side.

---

## What you do — about five minutes, once

**1. Make a free GitHub account.** Go to <https://github.com/signup>. You need an email address and a
username. Nothing else. Write the username down.

**2. Open your `lifehack-brain` folder in Claude's Code tab**, the same way you always do.

**3. Drag this file into the chat and say: "Set up bug reports."**

**4. Answer its questions.** There is one step where it shows you a short code and opens your browser —
you type the code in and click a green button. That's the whole sign-in.

That's it. From then on, whenever something goes wrong, say **"file a bug."**

---

## What happens when you file one

Claude writes the report for you — what you were doing, the exact error, and which version you're on.
**Then it shows you the whole thing and waits.** Nothing is sent until you say yes.

⚠ **Read it before you say yes.** A bug report is a public page on the internet. Anyone can find it, and
it stays there. Claude strips out your name and your folder paths before showing you, but you are the
last check, and you are the only one who knows whether a line of your own writing has ended up in there.
**If you see anything of yours in it, say no.** Nothing is lost by refusing — it will just take the
private bits out and show you again.

---
---

# INSTRUCTIONS FOR CLAUDE

**You are adding bug reporting to someone who already has this installed. Read all of this before you do
anything.**

**All the behaviour rules from `INSTALL.md` still apply** — whole sentences, never a status token, one
step at a time, say what you're about to do and what happened, and never invent a result you didn't
actually get.

> ## ⛔⛔ THE INSTALL IS ALREADY DONE. DO NOT RE-RUN IT.
>
> Do not check for git or Python, do not clone anything, do not touch their notes folder, do not run
> `bootstrap.py`, and do not offer to run `/ingest`. **All of that already happened.** If it turns out it
> didn't, say so and stop — send them back to `INSTALL.md`. Do not try to complete a half-install from
> inside this file.

---

## STEP A — Confirm you're in the right place

```bash
test -f .claude/skills/ingest/SKILL.md && git rev-parse --show-toplevel
```

If that prints a path, they're inside their tool folder and you can continue.

**If it doesn't, stop.** Tell them plainly: *"I need to be in your lifehack-brain folder to set this up —
could you open that folder in the Code tab and drag this file in again?"*

---

## STEP B — The GitHub account

Ask them: **"Do you have a GitHub account yet?"**

**If no:** send them to <https://github.com/signup>, tell them it's free and takes two minutes, and say
you'll wait. Do not walk them through the form — it changes, and it's self-explanatory. When they say
they're done, ask for their username and say it back to them.

**If yes:** ask for the username and move on.

⛔ **Never ask for their password, and never offer to sign up on their behalf.** The next step is how they
prove who they are, and it never involves you seeing a credential.

---

## STEP C — The GitHub command-line tool

```bash
command -v gh
```

**If that printed a path**, tell them it's already installed and move on.

**If it printed nothing — Mac:** send them to <https://github.com/cli/cli/releases/latest>. Tell them to
scroll to the list of files and download **the one file ending in `.pkg`** — there is only one, and it
works on every Mac. Then double-click it. It's a normal installer with a Continue button.

**If it printed nothing — Windows:**
```powershell
winget install --id GitHub.cli -e --source winget
```
If `winget` isn't available, same releases page, the file ending in `.msi`.

⛔ **Do not continue until `command -v gh` prints a path.** They may need to close and reopen the Code tab
before it's found — that's normal, and worth telling them before they think it failed.

---

## STEP D — Sign in

Before you run anything, tell them what is about to appear:

> **"This is going to show you a short code — something like `A1B2-C3D4` — and then open your browser.
> Type the code in and click the green Authorize button. Come back and tell me when you've done it."**

```bash
gh auth login --hostname github.com --git-protocol https --web
```

⚠ **The code expires after a few minutes.** If they wander off and it times out, just run it again —
nothing is broken and there's no limit on retries.

Confirm it worked:
```bash
gh auth status
```

Tell them in a sentence which account is now connected. **If it says they're not logged in, say so
plainly and run this step again** — do not tell them it probably worked.

---

## STEP E — Prove they can reach the project

```bash
gh issue list --repo LifehackMethod/lifehack-brain --limit 3
```

If that returns anything — even an empty list — they can reach it.

⛔ **Do NOT file a test issue.** There is already one on there called "test", and thirty more would bury
the real reports. **Their first genuine bug is the test.** Say that to them, so they don't think
something is unfinished.

---

## STEP F — Tell them the phrase, then stop

> **"You're set. Whenever something goes wrong — anything at all, even if you're not sure it's a bug —
> just say 'file a bug'. I'll write it up, show it to you, and only send it once you say yes."**

Then stop. Do not file anything now.

---
---

# HOW TO FILE ONE — read this when they say "file a bug"

## What goes in it

**A report that names the exact thing that broke gets fixed in a day. A report that says "it didn't work"
gets a conversation instead of a fix.** Gather all of this before you write anything:

- **What they were trying to do**, in their own words. Ask if you don't know.
- **The exact command or step** that failed.
- **The real error text** — the actual last lines, not your summary of them.
- **Which version they're on:** `git rev-parse --short HEAD`
- **What kind of computer:** `uname -s`
- **Whether it happens every time**, if they know.

## What must NOT go in it — this is the part that matters

**This is a public page on the internet and it is permanent.** Before you show them anything, take out:

- **Their home folder path.** Replace `/Users/theirname/...` with `~/...`. Their real name is very often
  in that path and they will not notice it.
- **Anything they have written.** Note content, journal lines, project names, file names from their own
  notes folder. **The error is the evidence, not what they were writing when it happened.**
- **Anything from their `config/` folder** — sheet ids, calendar ids, email addresses.
- **API keys and tokens**, obviously, in any form.

⛔ **If you cannot tell whether something is theirs or ours, leave it out and say in the report that you
left something out.** A slightly thinner bug report is a rounding error. A leaked line of someone's
private writing is not retrievable — GitHub keeps it, and search engines index it.

## Then show them, and wait

Print the whole report — title and body, exactly as it will appear — and ask:

> **"Here's what I'd send. It goes on a public page that anyone can read and it stays there. Have a look,
> and tell me if anything in it is yours."**

⛔ **Wait for an actual yes.** Silence is not a yes, and "ok" to a different question is not a yes. **If
they say no, ask what to take out, remove it, and show them again.** There is no limit on how many times
you do this.

## Then send it

Write the approved body to a scratch file **outside this folder**, then send it:

```bash
cat > /tmp/lifehack-bug.md <<'EOF'
<the body they approved, exactly as they saw it>
EOF

gh issue create --repo LifehackMethod/lifehack-brain \
  --title "<one line naming the thing that broke>" \
  --body-file /tmp/lifehack-bug.md
```

⛔ **The scratch file goes in `/tmp`, never inside this folder.** Anything written inside the tool folder
gets picked up by git, which is the one thing this whole system is arranged to prevent.

That prints a web address. **Give it to them and tell them what it is:** *"That's your report — that link
is where you can watch it get fixed."*

**If the command fails**, read them the actual error. The two likely causes are that their sign-in
expired (run `gh auth status`, and STEP D again if needed) or they have no internet. Do not retry
silently.
