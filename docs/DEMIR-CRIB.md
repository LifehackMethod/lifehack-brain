# Demir's Crib Sheet — Lifehack Brain Live Class

## 1. What this is (say this out loud to open)

Lifehack Brain is a free tool that gives your Claude AI one new command, `/ingest`. It takes a pile of your own material — an old ChatGPT export, a folder of notes, a stack of documents — and sorts it into a folder structure you and your AI can both work from. Today we're just installing it and getting to the first questions it asks; you finish the sorting on your own time.

## 2. The happy path (narrate it in this order)

1. Make a folder called **Lifehack Brain**. Anywhere on their computer they'll find again.
2. Open that folder in the Claude desktop app's **Code** tab.
3. Drag **INSTALL.md** into the chat.
4. Say: **"Set up my brain."**
5. When Claude says it's done, **quit Claude completely and reopen it** — not a new chat, the whole app.
6. Type **`/ingest`**.

## 3. ⛔ THE ONE RULE — repeat it all class

**After the files are downloaded, they must quit Claude entirely and reopen it.**

If they skip this: Claude was already running before the new files existed, so it can't see them. It reads the skill file as a *document* instead of *running* it. The result looks roughly right, takes ages, and is not the actual tool. **Nothing shows an error.** This is the single most common failure in this class, and it is silent — the student won't know anything is wrong, so ask every stuck student this question first.

## 4. The three breakout rooms

**Room 1 — "I don't have a folder for my brain yet."**
Symptom: they haven't made the folder, or don't know where to put it.
Cause: step 1 was skipped or unclear.
Fix: have them make any real folder on their own computer — ideally inside a cloud folder they already use (Google Drive, Dropbox, OneDrive), otherwise plain Documents. It must be a real folder on the machine, not a website they log into.

**Room 2 — "I can't install git or Python, or the download failed."**
Symptom: an install step errors out, or files never arrive.
Cause: git or Python missing, or (Windows) Python not on PATH.
Fix: walk INSTALL.md's Step 2 (git) and Step 3 (Python) with them, one at a time. ⚠ On Windows, the single most common cause is the un-ticked **"Add python.exe to PATH"** checkbox on the first screen of the Python installer. Fix: re-run the Python installer and tick that box.

**Room 3 — "I have it but it's behaving strangely."**
First question, always: **did you quit and reopen Claude?** If yes and it's still off:
Second question: does the folder contain a **`.claude`** folder? It's hidden by default — on a Mac, **Cmd+Shift+.** in Finder shows hidden files.
Still stuck: fall back to **`.claude/skills/ingest/PLAN-B.md`**. Drag it into a **fresh** Claude chat and say **"help me."** It's a complete manual backup that walks through the same process by hand, with no tools required to work.

## 5. ⚠ Expect version drift

Fixes may get pushed live during class. If someone installed earlier and is now behaving oddly, have them **delete their folder and re-run INSTALL.md from scratch** — not `git pull`. Files moved recently, so a pull can leave old copies behind and Claude may load the stale ones.

## 6. Don't do this in class

Once running, `/ingest` asks a lot of human-in-the-loop questions (keep / toss / explore, one per item). **Do not spend class time answering them.** Get every student installed and to the point where those questions appear, show them the folder structure, then move on. They finish sorting on their own time.

## 7. What good looks like (closing check)

- **Phase 1:** their material gets sorted into a handful of named piles, and Claude asks whether the piles look right.
- **Phase 2:** each item shows up with a name and a 2–3 sentence description, and Claude asks keep / toss / explore.

If a student sees either of these, it's working — send them on their way.
