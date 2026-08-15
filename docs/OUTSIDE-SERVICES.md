# What this needs from outside itself

Every account, tool, and paid service this package can possibly touch — in one place, so you never
find out about one by hitting a wall.

## The split, first, because it's the whole point of this page

**Two things are required. The other nine are optional — genuinely optional, not "optional" in the
way that quietly means "you'll need it eventually."** Get the two required things, install this tool,
and use it completely. The other nine each unlock exactly one extra feature; skip every one of them
and nothing about the core tool notices.

| | Need it to install? | Skip it, and… |
|---|---|---|
| **git** | **Yes — always** | you can't get the tool onto your computer at all |
| **python3, version 3.9+** | **Yes — always** | nothing in the package runs |
| Serper (web search) | No | `/websearch` refuses and says so; everything else is fine |
| pdfplumber | No | opening a `.pdf` fails with a plain "install this" message |
| python-docx | No | opening a `.docx` fails the same way |
| openpyxl | No | opening a `.xlsx` fails the same way |
| ntfy (phone notifications) | No | no pushes to your phone; nothing else changes |
| `gws` + your Google account | No | no calendar/task/mail reads, no spreadsheet writes |
| `clasp` | No | `/google-sheet` falls back to formulas only — almost never needed |
| `gh` + a GitHub account | No | you can't use the one-sentence "file a bug" flow yet |
| Google Chrome | No | `/design-lifehack` screenshots fail; nothing else touched |
| LuLu (outbound firewall) | No | the two built-in egress speed bumps still run; you skip the one HARD wall of the three (see below) |

**If you only ever get the required two, this tool works, completely, forever.** Everything below the
line is a "come back to this later, if ever" decision — never a "now" decision.

---

## REQUIRED — both of these, no way around it

### git

- **What it is.** The tool that fetches this package onto your computer, and later fetches updates
  to it.
- **Do you need it?** Yes, always — there is no version of this tool that works without it.
- **Without it.** You can't clone the repository in the first place. Nothing else here is reachable.
- **Getting it.** You don't do anything yourself — `INSTALL.md` checks for it and installs it for you
  (Step 2), on both Mac and Windows.
- **Cost.** Free.

### python3, version 3.9 or higher

- **What it is.** The language every tool in this package is written in — the sorting, the safety
  checks, every skill. Nothing here runs without it.
- **Do you need it?** Yes, always.
- **Without it.** Nothing runs. Not "some things are limited" — nothing.
- **Getting it.** Same as git — `INSTALL.md` checks and installs it for you (Step 3), including two
  known Windows traps it walks you around.
- **Cost.** Free.

---

## OPTIONAL — skip every one of these today

None of what follows blocks your install or limits the core tool. Each one unlocks exactly one thing.
Skip it, and that one thing simply doesn't happen yet — nothing else notices, and nothing breaks.

### Web search — a Serper API key

- **What it is.** The key that powers `/websearch`, so a session can look something up on the live
  web instead of only what it already knows.
- **Do you need it?** Only if you want that lookup. Nothing else in the package uses it.
- **Without it.** `/websearch` refuses and tells you why. Every other skill works normally.
- **Getting it.** A free account at **serper.dev**, then the key goes in a file — the exact command
  is in `INSTALL.md`, under **"WEB SEARCH."**
- **Cost.** Free tier covers ordinary use. Paid tiers exist beyond that — check serper.dev's own
  pricing page for current numbers; they aren't reproduced here because they can change without this
  document knowing.

### Reading PDFs — pdfplumber

- **What it is.** A library that opens a `.pdf` and strips what you can't see in it — hidden text,
  the kind used to sneak instructions past a reader.
- **Do you need it?** Only if you plan to hand this tool a PDF.
- **Without it.** Opening a `.pdf` fails with a message telling you exactly what to install. Plain
  text, markdown and CSV files need nothing and always work.
- **Getting it.** `pip install pdfplumber` — see `INSTALL.md`, **"READING DOCUMENTS."**
- **Cost.** Free and open-source. No account.

### Reading Word documents — python-docx

- **What it is.** The same idea as pdfplumber, for `.docx` files — strips hidden Word runs you can't
  see on the page.
- **Do you need it?** Only if you plan to hand this tool a `.docx` file.
- **Without it.** Opening a `.docx` fails the same clear way.
- **Getting it.** `pip install python-docx` — see `INSTALL.md`, **"READING DOCUMENTS."**
- **Cost.** Free and open-source. No account.

### Reading spreadsheets — openpyxl

- **What it is.** The same idea again, for `.xlsx` files — strips hidden rows and cells that are
  secretly formulas.
- **Do you need it?** Only if you plan to hand this tool an Excel file.
- **Without it.** Opening a `.xlsx` fails the same clear way.
- **Getting it.** `pip install openpyxl` — see `INSTALL.md`, **"READING DOCUMENTS."**
- **Cost.** Free and open-source. No account.

### Phone notifications — ntfy

- **What it is.** A doorbell to your phone — a "something happened, go look" push, never the actual
  content of whatever happened.
- **Do you need it?** Only if you want that push. Nothing else depends on it.
- **Without it.** Nothing pushes to your phone. Everything that would have notified you still runs;
  it just doesn't buzz you about it.
- **Getting it.** The free **ntfy** app, plus a private topic string you pick yourself — the exact
  steps are in `INSTALL.md`, under **"NOTIFICATIONS ON YOUR PHONE."**
- **Cost.** Free app. It uses the public `ntfy.sh` service by default, so treat your topic string
  like a password — anyone who knows it can read what you send.

### Calendar, tasks, spreadsheets and Gmail — the `gws` CLI plus your own Google account

- **What it is.** A command-line tool that talks to Google on your behalf, so this package can read
  your calendar and tasks, read or write a Google Sheet, and — if you grant that scope too — read your
  Gmail (subjects/senders/dates freely, bodies only through the sanitizer) and move labels. **There is
  no send or compose capability anywhere in this package**, connected or not.
- **Do you need it?** Only if you want any of that. Most people setting this up for the first time
  don't need it right away, and each scope is independent — grant Calendar without Gmail, or none of
  it at all.
- **Without it.** No calendar or task reads, no spreadsheet writes, no mail reads. Every other part of
  the package — including all of `/ingest` — is completely unaffected.
- **Getting it.** This is a sit-down, not a click — expect to do it with someone the first time.
  Full walkthrough in `INSTALL.md`, under **"THE GOOGLE-CONNECTED PARTS"** — including a table, under
  **"What each scope reaches, and what refuses it,"** naming exactly what each scope turns on and what
  the guards in this package refuse regardless. (That section is honest that it doesn't pin down one
  install command for `gws` itself — how you install command-line tools varies by machine — but it
  walks the login and the safety rules around it in full.)
- **Cost.** `gws` itself is free. You connect your own Google account — nothing here requires buying
  anything from Google.

### Apps Script inside a spreadsheet — `clasp`

- **What it is.** Google's own command-line tool for Apps Script — logic a plain formula can't
  express.
- **Do you need it?** Almost never. Formulas, `ARRAYFORMULA`, and the self-check layer all work with
  no `clasp` installed at all. This is the optional-of-the-optional item — skip it unless you
  specifically hit a wall a formula can't get past.
- **Without it.** `/google-sheet` simply stays on formulas, which is what it does for almost every
  sheet anyway.
- **Getting it.** Not walked step-by-step here, precisely because so few people ever need it —
  `INSTALL.md`, under **"THE GOOGLE-CONNECTED PARTS,"** names it and what its credential file is; ask
  when you actually hit the wall and it'll be installed then, not before.
- **Cost.** Free, official Google tool.

### Filing bugs the fast way — `gh` CLI plus a free GitHub account

- **What it is.** The tool behind saying "file a bug" and having the whole report — what you were
  doing, the real error, your version — written up and sent, instead of you having to describe it.
- **Do you need it?** Only if you want that flow. You can always just describe a problem in chat
  instead — this only makes it faster and trackable.
- **Without it.** Nothing breaks. You just don't have the one-sentence "file a bug" shortcut yet.
- **Getting it.** Its own five-minute setup, separate from the main install: drag
  `docs/REPORT-A-BUG.md` into the chat and say **"Set up bug reports."** It installs `gh` for you on
  a Mac; on Windows it uses `winget`, or sends you to the one page that works if `winget` isn't there.
  You never type a command yourself.
- **Cost.** Both free. `gh` is GitHub's own tool, and the free tier of a GitHub account covers
  everything this needs — no card.

### Screenshots for design work — Google Chrome, headless

- **What it is.** `/design-lifehack` looks at its own work by rendering a page to an image first
  (`system/tools/render_shot.sh`), so Claude can actually see what it built instead of guessing from
  the markup.
- **Do you need it?** Only if you use `/design-lifehack`. No other skill touches it.
- **Without it.** That one skill's screenshots fail outright — it tells you plainly rather than
  producing a broken image. Every other skill is unaffected.
- **Getting it.** The ordinary free download at <https://www.google.com/chrome/>, installed like any
  other application. No account, no extension, nothing to configure afterwards.
- **Cost.** Free.
  ⚠ Verified on macOS only — the tool also checks the standard Linux and Windows install locations,
  but nobody has confirmed those work yet.

### Outbound protection — LuLu, and the three honest levels (T9.5g, 2026-08-15)

Everything else on this page protects the INCOMING side — a page, a PDF, an email body gets sanitized
before the model ever reads it. This package does not promise the same strength on the OUTGOING side,
and this section says so plainly rather than letting you assume it's covered. **Read this, decide for
yourself, and if you want the hard floor, it's a five-minute install — not a switch this package flips
for you.**

**Level 1 — the raw-command allowlist (`system/egress-allowlist.md`). ON by default, no setup.** Blocks
a `curl`/`wget`/raw Python HTTP call from reaching anywhere outside a short approved domain list.
It is a speed bump, not a wall: if it can't parse a command or read its own list, it **fails OPEN** —
allows the call rather than freezing your shell on an edge case — and it only reads the text of a shell
command, so a compiled program opening its own connection is invisible to it.

**Level 2 — the domain seal on ordinary web reads (`system/safe-fetch-allowlist.md`). OFF by
default, and it is a real switch.** Ordinary web reading — what `/websearch` and most
content-reading skills actually use — can be sealed to a set of domains you choose. Everything
outside that set is refused before the connection opens.

- **Turning it on.** Open `system/safe-fetch-allowlist.md`, list your base domains, change the
  switch line from `off` to `on`. That is the whole procedure; nothing else has to be installed.
- **Checking where it stands.** `python3 system/tools/safe_fetch.py --l2-status` prints ON or OFF
  and, if on, what it is sealed to.
- **While it is off, it tells you so** — every unsealed web read prints one line saying the seal is
  not in force. You are never left assuming a wall that is not there.
- **Half-configured refuses rather than pretends.** Domains listed with the switch still off, or the
  switch on with nothing listed, stops web reads with a message naming the line to fix. That state
  is the one that would otherwise look like protection and provide none.
- ⚠ **What it is not.** It governs `safe_fetch.py` only. A raw `curl` is Level 1's business, and a
  compiled program opening its own connection is invisible to both — that is Level 3.

**Level 3 — your own operating-system firewall. Not included. The only HARD wall of the three.**
Levels 1 and 2 both work by reading the text of a command or a URL before deciding, and Level 1 fails
open by design — neither can see a compiled binary phoning home on its own. An OS-level firewall sits
underneath both, and asks you, by name, the first time anything tries to leave your machine at all.
**LuLu** (by Objective-See, macOS) is the free, open-source option this page recommends; **Little
Snitch** (paid, macOS) and `ufw` (Linux) do the same job if you already have one.

- **Do you need it?** Only if you want that hard floor. Nothing here stops working without it — same
  "genuinely optional" bar as everything else on this page.
- **Without it.** Levels 1 and 2 still run and still catch the ordinary case. What you lose is the one
  layer that would notice a compiled tool doing something neither of them can see.
- **Getting it.** Free, at <https://objective-see.org/products/lulu.html> — download, install like any
  other Mac app, and the first time anything tries to reach the network it asks you, by name, allow or
  deny. Point it at the same base-domain list in `system/egress-allowlist.md` if you want your two
  walls to agree.
- **Cost.** Free, open-source, no account.

---

**That's all twelve.** If something outside this package ever gets added later, this page is where it
belongs — not buried inside the one skill that happens to need it.
