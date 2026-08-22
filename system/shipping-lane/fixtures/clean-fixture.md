# CLEAN fixture — must survive every rule untouched

This file is the other half of the two-sided test. It is written to look like real shipped
documentation and must produce **zero** hits: exit 0 against the effective refuse rules,
and zero substitutions from the rewrite rules.

⭐ **THE LOAD-BEARING LINES ARE THE NEAR-MISSES.** A guard that only ever fires is not a
guard — it is a wall that gets taken down the first week. Every paragraph below is written
to sit as close to a rule as prose can get without being the thing the rule hunts. If one
of them ever starts failing, the rule that caught it has widened, and the next thing that
happens is somebody deletes the rule rather than narrowing it.

## Where your files live

Your notes live in one folder, and you choose where. Write paths the portable way — `$HOME`
or `~/notes` — and nothing has to be rewritten when the folder moves or when somebody else
runs the same instructions on their own machine. Code and content sit in separate zones, so
an update can replace the code without touching a word you wrote.

## Credentials, and where they are not

⚠ Nothing in this project ever asks you to paste a key into a file it tracks. When a doc
shows the shape of a request, it shows a placeholder and never a value:

    Authorization: Bearer <your token>
    api_key: <paste yours here, outside this repo>
    export SERVICE_PASSWORD=<read from your keychain, never written down>

Those three lines are the point of this section. Each names a credential, and none is one.
A rule that fired on the word `password` in prose, or on `Bearer <your token>`, would block
a publish over documentation — and a gate that blocks on documentation is a gate somebody
turns off before the week is out.

## Names that are not the name

The identity tier matches whole words, which is what makes it safe to be aggressive. Real
words that merely contain a listed term must survive: a renewal notice, a drawn-out review,
Oakleyville's town charter, a demarcation line. Each of those has the hunted letters inside
it and a letter on at least one side, so the boundary holds and nothing fires.

## Links, IDs and addresses that are not one

⭐ These four paragraphs are near-misses for the identifier rules, and they are the ones most
likely to break. Each one names a service, a link shape or an address family in ordinary
documentation prose — the way a real page has to — while stopping one character short of
being the identifier itself. If a line here starts failing, the rule that caught it has
stopped distinguishing "talking about a resource" from "naming one".

A shared file lives wherever you put it, and its link is the address of that one file in
that one account, so no doc in this project ever writes a real one out. Where a link has to
be shown, it is shown with its tail removed — `docs.google.com/spreadsheets/d/…` and
`drive.google.com/drive/folders/…` — because the part after the last slash is the whole
identity of the thing.

Config keys are named here, never filled. A setup page says `sheet_id: <paste yours>` and
`calendar_id: <the one you created>`; the value stays in your own config, outside anything
this repo tracks. A rule that fired on the KEY rather than on a real value would block a
publish over a blank example, which is the fastest way to get the gate switched off.

Push notifications go through a topic-based service — ntfy.sh is the one these docs assume —
and the topic string is an unauthenticated inbox, so it belongs in your config and never in
a page like this one. Likewise the numeric examples: reserved documentation addresses such
as 203.0.113.10, and loopback at 127.0.0.1, are safe to print precisely because they point
at nobody's network.

## Naming

Skills use plain verbs — read, save, checkin. A skill does one job and says so in its first
line. Tools take their paths as arguments rather than baking them in, which is why none of
them has to know whose machine it is running on.

<!-- 2026-08-22: the two documented FORMS the narrowed rules must let through (see refuse-rules.json) -->
- discovery looks under `~/Library/CloudStorage/GoogleDrive-*` — a glob, not an account
- agent_calendar: abc123...@group.calendar.google.com — the placeholder, not a calendar
