# When something breaks, tell me — without having to explain it

Right now, when something goes wrong, you have to describe it to me and I have to guess. This changes
that. Once it's set up, you just say **"file a bug"** and the whole thing — what you were doing, the
actual error, which version you're on — comes straight to me.

This is not theoretical. Someone in this class hit a problem on Windows, sent it this way, and it was
fixed the next day.

**It takes about five minutes and you need one thing: a free GitHub account.** That's it. No card, no
downloads on your end.

---

## What you do

**Open your `lifehack-brain` folder the way you always do, drag this file into the chat, and say:**

> **"Set up bug reports."**

Then just answer its questions. There are only two moments where it needs you: making the free account
(it'll give you the link and wait), and clicking one button in your browser to prove the account is
yours.

Everything else it does itself. **You will not have to type any commands.**

---

## Afterwards

Whenever something goes wrong — anything, even if you're not sure it's a bug — say **"file a bug."**

It writes the report, **shows you the whole thing, and waits.** Nothing is sent until you say yes.

⚠ **Do read it before you say yes.** A bug report is a public page on the internet and it stays there.
It takes your name and your folder paths out before showing you, but you're the last check — you're the
only one who knows whether a line of your own writing has crept in. **If you spot anything of yours,
just say no.** It'll take it out and show you again. There's no limit and nothing is lost.

---
---
---

# ⬇ EVERYTHING BELOW THIS LINE IS FOR CLAUDE. YOU DON'T NEED TO READ IT.

*(It's the setup instructions. It's meant to look like this. Nothing here is for you to do.)*

---
---
---

# INSTRUCTIONS FOR CLAUDE

**You are adding bug reporting for a non-technical person who already has this installed.**

> ## ⛔⛔ THEY MUST NEVER SEE A COMMAND. THIS IS THE WHOLE BRIEF.
>
> **This person did not open a terminal to get here — they typed a sentence.** A block of shell in the
> chat reads to them as *"this was supposed to be easy and now it isn't."*
>
> - ⛔ **Never print a command, never ask them to run one, never ask them to approve one.** Run it
>   yourself and say in one plain sentence what happened.
> - ⛔ **Never send them to a download page and never make them choose between two files.** Anything that
>   can be fetched, you fetch.
> - ⛔ **Never show them a status token.** Not `OK`, not `✓`, not an exit code. Whole sentences.
> - ⛔ **Never invent a result.** If you couldn't check something, say you couldn't. They cannot tell a
>   confident guess from a fact, and they will act on it.
>
> **There are exactly TWO things they do themselves**, because nobody can do them for them: create the
> account, and click Authorize in their browser. **Everything else is yours.**

> ## ⛔ THE INSTALL IS ALREADY DONE. DO NOT RE-RUN IT.
>
> Do not check for git or Python, do not clone anything, do not touch their notes folder, do not run
> `bootstrap.py`, do not offer to run `/ingest`. If it turns out they aren't actually installed, say so
> and send them to `INSTALL.md`. **Do not finish a half-install from inside this file.**

---

## STEP 0 — Say what's about to happen

Tell them, in about three sentences: you're setting up bug reporting, it takes about five minutes,
there are two moments where you'll need them and you'll do the rest, and you'll say what's happening as
you go. Then ask if they're ready and wait.

---

## STEP A — Quietly confirm you're in the right folder

```bash
test -f .claude/skills/ingest/SKILL.md && git rev-parse --show-toplevel
```

**Say nothing about this if it works** — just continue. It's a sanity check, not a milestone, and
narrating it makes the setup feel longer than it is.

**If it fails**, say: *"I need to be in your lifehack-brain folder for this — could you open that folder
and drag this file in again?"* Then stop.

---

## STEP B — The account

Ask: **"Do you already have a GitHub account?"**

**If yes**, move on. Don't ask for the username — you don't need it and it's one more thing for them to
go and look up.

**If no**, say roughly: *"You'll need a free one — it's the only thing I can't do for you. Go to
https://github.com/signup, it takes about two minutes and just needs an email address and a username
you pick. Tell me when you're back."* **Then wait.** Do not narrate the signup form; it changes, and
they can read.

⛔ **Never ask for their password.** The next step is how they prove who they are and it never involves
you seeing a credential.

---

## STEP C — Make sure the GitHub tool is available, installing it yourself if it isn't

```bash
command -v gh
```

**If that printed a path, it's already here.** Say one sentence — *"Good, the tool I need is already on
your machine"* — and go to STEP D. Use `gh` as the command for the rest of this file.

**If it printed nothing, install it yourself. Do not send them anywhere.** Tell them first:
*"You're missing one small tool. I'll fetch it — about thirty seconds, and it goes in your own home
folder, so nothing needs an administrator password."*

```bash
set -e
# ⛔ macOS ONLY. This downloads a macOS_*.zip, so it is wrong everywhere else. The gate used to be
# PROSE sitting BELOW this block ("on Windows use winget instead") — and a prose gate is a wish, not
# a control: nothing stopped the block being run first and failing halfway. Now it refuses itself.
if [ "$(uname -s 2>/dev/null || echo Windows)" != "Darwin" ]; then
  echo "NOT-MACOS: skip this block. Windows -> winget install --id GitHub.cli"
  echo "           Linux   -> your package manager, or https://cli.github.com"
  exit 0
fi
mkdir -p "$HOME/.local/bin"
case "$(uname -m)" in
  arm64|aarch64) GH_ARCH=arm64 ;;
  *)             GH_ARCH=amd64 ;;
esac
GH_URL="$(curl -sSL https://api.github.com/repos/cli/cli/releases/latest \
  | python3 -c "import sys,json,os
d=json.load(sys.stdin)
want='macOS_'+os.environ['GH_ARCH']+'.zip'
print(next(a['browser_download_url'] for a in d['assets'] if a['name'].endswith(want)))")"
curl -sSL "$GH_URL" -o /tmp/gh.zip
unzip -qo /tmp/gh.zip -d /tmp/gh-unpack
find /tmp/gh-unpack -type f -name gh -perm -u+x -exec cp {} "$HOME/.local/bin/gh" \;
rm -rf /tmp/gh.zip /tmp/gh-unpack
"$HOME/.local/bin/gh" --version
```

⚠ **On Windows this won't work — the download is a Mac build.** If `uname -s` isn't `Darwin`, install it
for them with `winget install --id GitHub.cli -e --source winget` instead, and if `winget` isn't there,
that is the one case where you have to send them to
<https://github.com/cli/cli/releases/latest> for the file ending in `.msi`. Say sorry for the detour.

⛔ **From here on, if you installed it, the command is `~/.local/bin/gh`, not `gh`.** Their shell won't
find the bare name yet and you will spend ten confusing minutes on it. **Use the full path everywhere
below.**

⛔ **If the install fails, stop and read them the real error.** Don't try a second method, don't
improvise, and don't tell them to install it themselves. Say the setup can't finish and that they should
send you the error — the rest of their system is unaffected.

---

## STEP D — Sign them in

**Tell them what's coming before you run it**, because this step waits on them:

> **"This is going to show you a short code — something like `A1B2-C3D4` — and open your browser. Type
> that code in and click the green Authorize button. Come back and tell me when it's done."**

```bash
gh auth login --hostname github.com --git-protocol https --web
```

⚠ **The code expires after a few minutes.** If they take too long, just run it again — nothing is broken
and there's no limit.

Then check it took:

```bash
gh auth status
```

Say in a sentence which account is connected. **If it says they're not signed in, say so plainly and run
it again.** Never tell them it probably worked.

---

## STEP E — Check they can reach the project

```bash
gh issue list --repo LifehackMethod/lifehack-brain --limit 3
```

Anything back — even nothing — means they can reach it.

⛔ **Do NOT file a test issue.** There's already one on there called "test", and thirty more would bury
the real reports. **Their first real bug is the test.** Tell them that, so they don't think it's
unfinished.

---

## STEP F — Give them the phrase, then stop

> **"You're set. Whenever something goes wrong — anything, even if you're not sure it's a bug — just say
> 'file a bug'. I'll write it up, show it to you, and only send it once you say yes."**

**Then stop. Do not file anything now.**

---
---

# HOW TO FILE ONE — read this when they say "file a bug"

## Gather this before you write anything

**A report naming the exact thing that broke gets fixed in a day. "It didn't work" gets a conversation
instead of a fix.**

- **What they were trying to do**, in their own words — ask if you don't know.
- **The exact step or command** that failed.
- **The real error text.** The actual last lines, not your summary of them.
- **Their version:** `git rev-parse --short HEAD`
- **Their machine:** `uname -s`
- **Whether it happens every time**, if they know.

## The profile — a separate, small addition, offered not forced

Before you show them the report, build a four-line technical profile and ask about it **separately from**
the report body — it is optional, and saying no to it is not saying no to filing the bug:

```bash
PLATFORM="$(uname -s 2>/dev/null || echo Windows)"
VERSION="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
PYBIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
DRIVE="$("$PYBIN" - "$PWD" <<'PY'
import os, sys
low = os.path.abspath(sys.argv[1]).replace("\\", "/").lower() + "/"
cloud = ["dropbox", "google drive", "googledrive", "onedrive", "icloud", "mobile documents"]
hit = next((t for t in cloud if t in low), None)
print(hit if hit else "none")
PY
)"
printf 'platform: %s\nharness: Claude Desktop (Code tab)\ndrive-sync: %s\nversion: %s\n' "$PLATFORM" "$DRIVE" "$VERSION"
```

**It never phones home** — this is not a separate channel, git is pull-only and that IS the privacy
guarantee. It only ever travels as a labeled block inside the same report, the one channel that exists.

Show them exactly those four lines, plainly — this carries no personal data by construction, only the
kind of thing that tells us which install to picture: which OS, whether their folder syncs through a
cloud drive (a real source of confusing failures — see `INSTALL.md` Step 4), and which version they're
on. Ask: *"I can add this small technical profile to the report — your OS, whether your folder syncs
through a cloud drive, and which version you're on. Nothing of yours is in it. Want it added?"*

**If they say no, leave it out and carry on** — the report is complete and useful without it, and nothing
else about filing it changes. If yes, append it to the body you write next as its own labeled section,
titled exactly `Technical profile` so a maintainer reading the issue knows it is machine-generated, not
something the student wrote.

## What must NOT go in it — this is the part that matters

**This becomes a public page, it is permanent, and search engines index it.** Before you show them
anything, take out:

- **Their home folder path.** A path starting `/Users/` (macOS) or `/home/` (Linux) is followed by their
  account name — replace the whole thing with `~/...`. **Their real name is usually baked into that
  account-name segment and they will not notice it.**
- **Anything they have written.** Note content, journal lines, project names, filenames from their notes
  folder. **The error is the evidence — not what they happened to be writing when it appeared.**
- **Anything from their `config/` folder:** sheet ids, calendar ids, email addresses.
- **Keys and tokens**, in any form.

⛔ **If you can't tell whether something is theirs or ours, take it out and say in the report that you
did.** A thinner bug report costs nothing. A leaked line of someone's private writing cannot be taken
back.

## Show them, and wait

Print the whole report — title and body, exactly as it will appear — then ask:

> **"Here's what I'd send. It goes on a public page anyone can read, and it stays there. Have a look and
> tell me if anything in it is yours."**

⛔ **Wait for a real yes.** Silence isn't a yes, and "ok" to a different question isn't a yes. **If they
say no, ask what to take out, take it out, and show them again.** No limit.

## Then send it

Write the approved body to a scratch file **outside this folder**, then send:

```bash
ROOT="$(git rev-parse --show-toplevel)"
BUGFILE="$(python3 "$ROOT/shared/paths.py" scratchfile lifehack-bug.md)"
cat > "$BUGFILE" <<'EOF'
<the body they approved, exactly as they saw it>
EOF

gh issue create --repo LifehackMethod/lifehack-brain \
  --title "<one line naming the thing that broke>" \
  --body-file "$BUGFILE"
```

⛔ **The scratch file goes in the OS scratch folder (`paths.py scratchfile`, never a literal `/tmp`, which is not a real location on Windows), never inside this folder.** Anything written in the tool folder
gets picked up by git, which is the single thing this whole system is arranged to prevent.

That prints a web address. **Hand it to them and say what it is:** *"That's your report — that link is
where you can watch it get fixed."*

**If it fails**, read them the real error. It's almost always an expired sign-in (check `gh auth status`,
redo STEP D) or no internet. **Do not retry silently.**
