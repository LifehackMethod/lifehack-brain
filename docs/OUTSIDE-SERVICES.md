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
| `gws` + your Google account | No | no calendar/task reads, no spreadsheet writes |
| `clasp` | No | `/google-sheet` falls back to formulas only — almost never needed |
| `gh` + a GitHub account | No | you can't use the one-sentence "file a bug" flow yet |
| Google Chrome | No | `/design-lifehack` screenshots fail; nothing else touched |

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

### Calendar, tasks and spreadsheets — the `gws` CLI plus your own Google account

- **What it is.** A command-line tool that talks to Google on your behalf, so this package can read
  your calendar and tasks, and read or write a Google Sheet.
- **Do you need it?** Only if you want any of that. Most people setting this up for the first time
  don't need it right away.
- **Without it.** No calendar or task reads, no spreadsheet writes. Every other part of the package —
  including all of `/ingest` — is completely unaffected.
- **Getting it.** This is a sit-down, not a click — expect to do it with someone the first time.
  Full walkthrough in `INSTALL.md`, under **"THE GOOGLE-CONNECTED PARTS."** (That section is honest
  that it doesn't pin down one install command for `gws` itself — how you install command-line tools
  varies by machine — but it walks the login and the safety rule around it in full.)
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

---

**That's all eleven.** If something outside this package ever gets added later, this page is where it
belongs — not buried inside the one skill that happens to need it.
