---
title: Connecting an Outside Service
status: approved
approved_by: "Enver on 2026-11-16, round four's 'land it'"
last_reviewed: 2026-11-16
purpose: Add an outside account, API key, token or connector so the harness can use it without the secret reaching the model, a log, a repo or a stranger.
read_when: Before adding a key, token, login or MCP connector; before a scheduled job uses one; before letting a raw network call reach a new host; when replacing or retiring a credential.
history: "canon/connecting-an-outside-service-sop.history.md"
---

## Read This First

- **Purpose:** the harness works with nothing connected; each outside service (an account, API key, token or connector the harness talks to) unlocks one feature and opens one more door. This SOP is the procedure for opening that door so the secret (credential: the key, token or password that proves who you are to the service) is held by the person's own files and the harness's shared code, not by the model, a log, a repo or the chat. The posture behind it — what the real risks are and how they rank — is `canon/security-canon.md` ("What the Actual Risks Are (Ranked)"); this SOP points to it and does not restate it.
- **Use it when:** you add a key, token or login for a service; you add an MCP connector (a server that gives the session new tools, such as a mail or chat service); a scheduled job needs a credential; a raw network call has to reach a host the harness does not already allow; a credential needs replacing or retiring.
- **Don't use it when:** writing or installing the scheduled job itself — `canon/cron-jobs-sop.md`. Writing a new guard hook — `canon/hook-sop.md` and `canon/hook-contract.md`. Deciding which model a helper uses — `canon/helpers-and-model-routing-sop.md`. The inbound scanning of what a service sends back — `canon/security-canon.md` ("Inbound Channel Inventory"). What a session receives at start, per turn, or after a connector tool runs — `canon/context-injection-sop.md`.
- **Covers:** researching a service before connecting it; where a credential goes; how code reads it; MCP connectors; a scheduled job's credential; the two outbound host lists; replacing a key and retiring a key.
- **Doesn't cover:** the threat model and posture (`canon/security-canon.md`); the Sentinel Auditor's checklist itself (`.claude/agents/sentinel.md`); moving a whole install to a new computer (Enver's ruling: out of this SOP for now).
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the history file named in the header.
- **Which situation are you in?**
  - Deciding whether and how to connect a service → The Procedure, "Research the service first".
  - Adding a key or token → "Adding a key or token".
  - Adding an MCP connector → "Adding an MCP connector".
  - A scheduled job needs the credential → "A scheduled job uses the credential".
  - A web read is refused for its host → "Letting web reads reach a new host".
  - A raw call is refused for its host → "Letting a raw call reach a new host".
  - A key is old, exposed or no longer needed → "Replacing or retiring a key".

## Desired Outcome

The service works through the skill or job that needs it; its credential sits outside every git repo and every synced folder, in a store the person trusts — an owner-only file in the local config folder (`~/.config/lifehack/`), the keychain, or a password manager; it is read by the harness's shared code, not by code a desk wrote for itself; the secret appears in no transcript, log or shell history; and every list touched for it (outbound hosts, web-read hosts, job fetch hosts, vendor reads) is one the person can name.

**How to check:** `ls -l ~/.config/lifehack/` shows the new file as `-rw-------` in a `700` folder; the skill or job that uses it succeeds without printing the key; the Sentinel Auditor (`.claude/agents/sentinel.md`) run with `scope=secrets` reports no exposure and no loose permission, and with `scope=inventory` lists the new MCP server.

## Before You Start

- What each optional service unlocks and what happens without it: `docs/OUTSIDE-SERVICES.md`.
- The exact setup commands for the services the harness already knows (web search, phone pushes, Google, Apps Script): `INSTALL.md`, its "WEB SEARCH" section and the Google sections that follow.
- The posture this procedure serves: `canon/security-canon.md` — "What the Actual Risks Are (Ranked)"; "Local secrets caveat" (why credentials sit in `~/.config/lifehack/` and not in a synced folder); and the egress paragraph (why the outbound check is friction and the operating system's firewall is the hard outbound wall).
- An account with the service, made by the person in their own browser.

## Principles

- **The person enters a secret through a hidden-read prompt, so it stays out of the model's context, the chat, shell history and every log.** Why: canon §6.4 — "Build a script that prompts for it with a hidden read. The secret never enters context and never lands in a log."; a key typed as a command argument is saved in the shell's history file. Change if: transcripts, logs and shell history of setups done without a hidden read are shown, over time, to hold no secrets. Evidence: OBSERVED — `canon/canonical-principles-sop.md:804-806` (§6.4, tagged AUTHORITATIVE with one receipt, 2026-06-08; THE FRAME maps that to OBSERVED).
- **A credential is held by the shared fetch (the short list of files allowed a raw outside call, `system/tools/shared-fetch-allowlist.txt`), not by a job's own runner.** Why: a desk that holds its own credential can bypass every lock the shared layer carries. Change if: runners holding their own credentials show no more unscanned reads or bypasses than runners using the shared fetch. Evidence: CANDIDATE — `canon/cron-jobs-sop.md:150` and `canon/hook-sop.md:176-184` (2026-10-27).
- **Credentials sit outside every git repo and every synced folder, in a store the person trusts.** Why: a private repo is not a security boundary — secret scanning is paid-only, accidental public exposure is the common failure, and deleted commits stay recoverable by hash; and file permissions on a synced mount may not reflect who can really read a file. Change if: the git host in use offers free secret scanning and a deleted commit becomes unrecoverable, and sync clients are shown to honour owner-only permissions end to end. Evidence: RESEARCHED — `canon/canonical-principles-sop.md` §9 (2026-07-21, outside practitioners' convergence: keep sensitive data off git; canon) and `canon/security-canon.md:102-106` (canon); Enver ruled on 2026-11-15 that credentials sit outside git and synced folders, with the keychain or a password manager taken as a safe store.
- **Read a credential from portable sources first (an environment variable, then an owner-only file) and from the macOS keychain last, because a scheduled job cannot read the login keychain.** Why: the login keychain belongs to the desktop session; a job running unattended got an empty answer, and the failure stayed hidden for two weeks; and `gws` run where the login keychain cannot be unlocked deletes its own stored credentials, ending Google sign-in for every window. Change if: a scheduled job is shown reading the login keychain reliably on a current macOS. Evidence: OBSERVED — `system/tools/safe_search_api.sh:56-63` and `INSTALL.md:2803-2805`; `system/tools/gws-audit.sh:3-6` (root-caused 2026-06-01, recurred 2026-07-26/27).
- **A missing credential says every place it looked, and a scheduled job without one stands down as "not set up yet", not as broken.** Why: "no key" alone sends the person hunting, and a job that reports a missing login as a failure trips the breaker and disables a feature the person did not choose to use. Change if: people fix missing credentials as fast from a bare "no key" as from the named-places report. Evidence: OBSERVED — `system/tools/safe_search_api.sh:64-65` and `:86-99`; `system/tools/claude-auth.lib.sh:15-34` (fix dated 2026-08-15).
- **Keep the outbound host list narrow, and give a service one governed door rather than an allowed host.** Why: every entry widens the wall, and the push service was taken off the list so its one governed sender is the only road to the phone. Change if: a wider list is shown to stop as many outbound leaks as a narrow one. Evidence: OBSERVED — `system/egress-allowlist.md:26-27` and `:44-45`; commit `5c83725` (2026-10-29).
- **Before naming a credential as the cause of a failed job, confirm the failure class from evidence.** Why: a job failure was once put down to an authentication error when the record held no authentication failures at all, and canon retracted it. Change if: credential errors turn out to be the cause of most job failures whenever they are suspected. Evidence: REFINED — `canon/canonical-principles-sop.md:1023` (§10).

## The Procedure

### Research the service first

1. **Do:** decide whether the service is needed at all.
   - **Why:** each optional service unlocks exactly one feature; skipping it changes nothing else (`docs/OUTSIDE-SERVICES.md`).
2. **Do:** reason about the new path with `canon/security-canon.md`'s "The Governing Lens — Lethal Trifecta + Blast Radius" before connecting it, then find out, from the provider's own pages, what the key or login unlocks (read only, or read and write), what it costs, and which host the harness will talk to.
   - **Expect:** for Google, every scope you accept turns on read and write both; `INSTALL.md` ("What each scope reaches, and what refuses it") lists what a guard here still refuses.
   - **Check:** you can name the host, the access level and the cost before creating the key.
3. **Do:** create the account and the key yourself, in your own browser.
   - **Why:** a key that passes through the chat sits in the transcript.

### Adding a key or token

1. **Do:** in your own terminal (not through a session), save the key with a hidden read, so it is not shown on screen or saved in shell history: `(umask 077; mkdir -p ~/.config/lifehack; read -rs KEY && printf %s "$KEY" > ~/.config/lifehack/<file-name>)`, then paste the key at the silent prompt and press Return. Use the file name the service's reader looks for; for a service `INSTALL.md` covers, that is the path its command names.
   - **Why:** one owner-only file per service, in the local config folder, outside every repo and synced folder (canon §6.4: a hidden read, so the secret lands in no log).
   - **Expect:** the file holds only the key; nothing about it is echoed to a session. A key kept in each person's own local settings file (`settings.local.json`), which is not shipped, is an exception to the line above: the file sits inside the repo folder, chosen deliberately for this release (`.gitignore:34-44`), and only `.gitignore` keeps it out of commits (passive conformance friction: no message, it simply is not staged).
   - **Check:** `ls -l ~/.config/lifehack/` shows the file as `-rw-------`, one file per service, named as its reader expects, with no second copy under another name — two names for one key leave nothing saying which is read. List names only; a key file is not opened or printed in a session.
2. **Do:** if code has to read the key, read it inside a file on `system/tools/shared-fetch-allowlist.txt`, looking in order: an environment variable, the owner-only file, then (macOS only) the keychain.
   - **Expect:** a scheduled job's runner that makes a raw outside call itself is refused at install by the scheduler door (`system/tools/install-schedulers.sh`, a hard block), and a session typing one is refused by `system/hooks/ingest_gate_enforce.sh`; a desk runner is not added to the list, which names only the shared fetch. With no key, the reader prints each place it looked and the command that fixes it, as `system/tools/safe_search_api.sh` does.
3. **Do:** test the service through the skill that uses it.
   - **Check:** the call succeeds and the key appears in no output; if it fails, the error names where it looked.

### Adding an MCP connector

1. **Do:** add the server in your own Claude Code configuration or your claude.ai connectors.
   - **Why:** the harness ships no MCP server configuration; the connector is the person's, and the harness guards what comes back.
   - **Expect:** every result from any `mcp__` tool passes through the connector door (`system/hooks/sanitize_connector_output.sh`), which strips hidden characters, redacts flagged spans, and swaps the cleaned text in; an error inside the script withholds the result.
2. **Do:** before turning on a connector that can send, write or delete (mail, calendar, tasks, sheets, files), the person decides whether to accept those actions, and mail is never sent without the person's approval of that send (drafts are fine).
   - **Why:** a connector that sends or deletes acts on the person's own accounts directly, and a sent message or a cloud delete cannot be taken back.
3. **Do:** record it — run the Sentinel Auditor (`.claude/agents/sentinel.md`) with `scope=inventory`.
   - **Expect:** the server listed with its transport (local, local HTTP, or networked) and the sensitivity of its data.
4. **Do:** after the first real use, review the sentinel event log and paused-source list, as `canon/security-canon.md` ("Cadence") asks after any new outside-content channel.

### A scheduled job uses the credential

1. **Do:** build the job through `canon/cron-jobs-sop.md`; its reads go through the shared fetch (§7 there), and the shared credential preflights (`system/tools/claude-auth.lib.sh`, `system/tools/gws-auth.lib.sh`) find the credential for it.
2. **Do:** for a job that calls a model, the person runs `claude setup-token` and saves the token to `~/.config/lifehack/claude-oauth-token` (`docs/OUTSIDE-SERVICES.md`).
3. **Do:** for a job that reads Google, the person exports a keychain-free credential file from their own terminal after `gws` login: `gws auth export --unmasked > ~/.config/lifehack/gws-credentials.json && chmod 600 ~/.config/lifehack/gws-credentials.json`.
   - **Why:** an unattended job cannot reach the login keychain, and `gws` run without it deletes its own stored credentials (`system/tools/gws-audit.sh`); the shared preflight (`system/tools/gws-auth.lib.sh`) points `gws` at this keychain-free file instead.
   - **Check:** `bash system/tools/gws-audit.sh` reads the whole Google credential setup in one pass.
4. **Do:** if the job reads a new web host, add it to your own `<personal-code>/job-fetch-hosts.txt`; if it is a vendor's logged-in read of your own account, add one `<job> <file>` line to your own `<personal-code>/vendor-read-allowlist.txt` (model column exactly `none`).
   - **Why:** your own list survives updates; an update overwrites the plugin's copy (`canon/cron-jobs-sop.md:150`).
   - **Expect:** with the credential missing, the job stands down with a line naming the missing file and the command to create it, and is counted as skipped, not failed; if it keeps standing down for more than twice its interval, one 'paused' text goes out (`canon/cron-jobs-sop.md` §4; `system/tools/claude-auth.lib.sh`, `system/tools/gws-auth.lib.sh`).

### Letting web reads reach a new host

1. **Do:** check the web-read seal: `python3 system/tools/safe_fetch.py --l2-status`.
   - **Expect:** `system/safe-fetch-allowlist.md` ships OFF; while it is ON, `safe_fetch.py` (what `/websearch`, `/research` and content-reading skills use) refuses any host not listed, before the socket opens.
2. **Do:** if the seal is ON, or you plan to arm it, add the service's base domain between that file's `ALLOWLIST-START` and `ALLOWLIST-END` markers.
   - **Expect:** a switch set ON with nothing listed, or domains listed with the switch OFF, refuses every web read until fixed (the AMBIGUOUS state).
3. **Do:** for a scheduled job, use the job's own list instead (see "A scheduled job uses the credential", step 4): jobs are sealed to their fetch-host lists whether or not this switch is on.

### Letting a raw call reach a new host

1. **Do:** first check whether a raw call is needed — reading a web page goes through `system/tools/safe_fetch.py`, which does not use this list; reading mail goes through `shared/tools/email_fetch.py`, because Python that speaks a mail protocol (IMAP, POP, SMTP, the Gmail API client) is refused whatever the list says (`system/hooks/enforce_egress_allowlist.py:92-110`, switch `email_reader_block`, on in `system/hooks/roundB.conf`).
2. **Do:** add the host's base domain (`example.com`, not `www.example.com`) between the `ALLOWLIST-START` and `ALLOWLIST-END` markers in `system/egress-allowlist.md`.
   - **Expect:** a host is allowed if it equals a listed domain or is a subdomain of it; a destination written as a shell variable or command substitution is refused whatever the list says (`system/hooks/enforce_egress_allowlist.py`, commit `09ab2fc`). The check refuses an unlisted host every time it fires (a hard block), but it matches command text and fails open on what it cannot parse, so it can be worded around; why, and where the hard wall is, is in `canon/security-canon.md`.
   - **Check:** `echo '{"tool_input":{"command":"curl -sI https://<host>"}}' | bash system/hooks/enforce_egress_allowlist.sh; echo "rc=$?"` prints `rc=0` (the form in `canon/hook-contract.md`, "Testing a Hook Locally"; the hook reads the text, it does not make the call).

### Replacing or retiring a key

1. **Do:** to replace a key, revoke the old one at the provider, then save the new one with the same hidden-read command as when it was added.
   - **Expect:** the Sentinel Auditor (`scope=secrets`) flags credential files older than 90 days as a warning (a sign: it reports, it changes nothing).
2. **Do:** to retire a key and its service, revoke the key, delete its file, and remove the lines added for it — the outbound host, the web-read host, the job fetch host, the vendor-read line, and the job row.
   - **Check:** the Sentinel Auditor (`scope=secrets` and `scope=inventory`) no longer lists it.

## When Something Goes Wrong

- **If a skill says there is no key:** read the places it looked and fix the one named; the message carries the command.
- **If a scheduled job stands down:** its line names the missing credential and how to supply it; supply it, and the next run proceeds.
- **If a scheduled job fails and a credential looks like the cause:** confirm the failure class from the job's error file and `last-run` before touching the credential.
- **If the outbound check blocks a call:** read the host it names; for reading, use `system/tools/safe_fetch.py`; add the base domain only if the host belongs to a service you connected on purpose.
- **If a call is blocked for carrying a secret and a network command together** (`system/hooks/guard_egress.sh`, a hard block; matches command text, so it can be worded around): reference the secret from its file, or use the shared fetch; do not paste it inline.
- **If a connector result is replaced by a "content withheld" note:** retry the call; repeated withholding means the sanitizer is failing, which is the door holding.
- **If a Google login goes stale:** the person signs in again themselves; an agent does not log `gws` out (`system/hooks/guard_gws_logout.sh` blocks it).
- **If a secret appeared in the chat, a transcript, a log or a commit:** treat it as exposed — revoke and replace it at the provider first, then find where it landed.
- **To undo:** a key file or a list line is removed by deleting it; revoking a key at the provider cannot be undone — stop and ask first.
- **Stop and ask the person when:** a service would need write access; a credential would have to live in a repo or a synced folder; a job seems to need its own credential outside the shared fetch; a secret may have been exposed; a guard blocks a step and the fix is not obvious.

## Don't Retry

- **The macOS keychain as the only source for a scheduled job** — the job got an empty answer and failed silently for weeks. Proof: `system/tools/safe_search_api.sh:56-63`.
- **Each runner carrying its own copy of the credential check** — the same wrong exit code sat in every copy, and fixing two left the rest broken. Proof: `system/tools/claude-auth.lib.sh:5-13`.
- **Allowing the push service's host for raw calls** — replaced by one governed sender. Proof: `system/egress-allowlist.md:44-45`; commit `5c83725`.
- **Running `gws` from a context that cannot unlock the login keychain** (a scheduled job, or a launcher outside the desktop session) — `gws` deletes its own stored credentials and Google sign-in ends for every window. Proof: `system/tools/gws-audit.sh:3-6`.
- **Logging `gws` out to clear a stale token** — it destroys every Google credential for every window at once. Proof: `system/hooks/guard_gws_logout.sh`.
- **Blaming an authentication error for a job failure without checking** — retracted in canon. Proof: `canon/canonical-principles-sop.md:1023`.

## Pointers

- **Rulings behind this SOP:** `canon/canonical-principles-sop.md` §6.4 (hidden read; canon) and §9 (2026-07-21, sensitive data off git; canon). Enver, 2026-11-15: a safe keychain or password manager is assumed for now ("we are going to assume ... that there is a way"); credentials sit outside git and synced folders as this SOP's principle (`canon/security-canon.md:102-106`); the SOP covers replacing and retiring a key, not moving computers.
- **Evidence:** `system/egress-allowlist.md`; `system/hooks/enforce_egress_allowlist.py`; `system/hooks/guard_egress.sh`; `system/hooks/sanitize_connector_output.sh`; `system/hooks/guard_gws_logout.sh`; `system/tools/shared-fetch-allowlist.txt`; `system/tools/vendor-read-allowlist.txt`; `system/tools/safe_search_api.sh`; `system/tools/claude-auth.lib.sh`; `system/tools/gws-auth.lib.sh`; `shared/notify/notify-send.sh`; `.claude/agents/sentinel.md`; tests `system/hooks/tests/test_egress_wall.sh`, `test_sanitize_connector_output.sh`, `test_gws_logout_guard.sh`, `test_ingest_gate_enforce.sh`; registrations in `system/register/register.jsonl`; commits `5c83725`, `09ab2fc`.
- **Words used here:** **credential** — a key, token or password that proves who you are to a service. **Shared fetch** — the files on `system/tools/shared-fetch-allowlist.txt`, the only code allowed a raw outside call and a credential. **Runner** — the script a scheduled job runs. **Raw call** — a hand-written network command (`curl`, `wget`, inline Python HTTP). **Outbound host list** — `system/egress-allowlist.md`, the hosts a raw call may reach. **Connector** — an MCP server that adds tools to a session. **Stand down** — a job declining to run because its setup is missing, counted as skipped.

## History

- 2026-11-15 — first draft, written as built from the V2 tree. Older wording: none.

## References (work in progress)

Everything real this SOP points at, with what it is. Strength words, by what a guard does when it fires (the full ladder is `canon/build-conformance-sop.md` §5.11): sign (a refusal on a first attempt that gives one specific instruction), speed bump (a first attempt refused with a message, where a later try gets through or gets an ask), hard block (refused every time). A guard that only matches shell text says so: "matches command text, so it can be worded around" (`canon/hook-sop.md` §1). Entries marked **not built yet** are slots for a mechanism Enver has called for.

**Where credentials live and how code reads them**
- `~/.config/lifehack/` — the person's local, non-synced config folder; one owner-only file per credential.
- `system/tools/shared-fetch-allowlist.txt` — the list of files allowed a raw outside call and a credential (the shared fetch).
- `system/tools/safe_search_api.sh` — the web-search reader; looks for its key in an environment variable, then a file, then the keychain, and names every place it looked.
- `shared/notify/notify-send.sh` — the one governed sender of phone pushes; reads the push topic from the config folder.
- `shared/tools/email_fetch.py` — the one shared mail reader; holds the Google mail credential.
- `system/tools/claude-auth.lib.sh` — shared preflight for a scheduled model call; finds the token or stands the job down by name.
- `system/tools/gws-auth.lib.sh` — shared preflight for a scheduled Google job; points `gws` at the keychain-free credential file or stands the job down by name.
- `system/tools/gws-audit.sh` — read-only health read of the whole Google credential setup.
- `system/tools/install-schedulers.sh` — the scheduler door; refuses a job runner that makes its own raw outside call (hard block, at install).
- `.gitignore` — keeps each person's own local settings files (`settings.local.json`, `local.settings.json`), which are not shipped, out of commits (passive; no message).
- `docs/OUTSIDE-SERVICES.md` — what each optional service unlocks and what happens without it.
- `INSTALL.md` — the setup commands for the services the harness knows.
- **not built yet:** a hidden-read entry script in `system/tools/` that prompts for a secret without showing it and writes the owner-only file, with `INSTALL.md` and the no-key messages pointing to it. Serves: `canon/canonical-principles-sop.md` §6.4.
- **not built yet:** the credentials template that ships empty, with the keychain or a password manager as the store behind it. Serves: `canon/canonical-principles-sop.md` §9 (2026-10-29, one copy in the shared layer).
- **not built yet:** credentials kept inside the shared fetch — the job scripts stop exporting the Google credential, and the two credential preflights join the shared-fetch list. Serves: not yet in canon.
- **not built yet:** the Google keychain-free export step in `INSTALL.md`. Serves: `canon/canonical-principles-sop.md` §6.4.

**Stopping a secret from leaving**
- `.claude/settings.json` — permission deny list; refuses the Read and Edit tools on `.ssh`, `.gnupg`, `.aws`, `.kube`, the keychains and `.env` files (a hard block for those tools; a shell command is not covered, so it reduces casual access and is not a wall, `canon/security-canon.md`).
- `system/hooks/guard_egress.sh` — refuses a shell command that carries a credential and makes a network call at once (hard block; matches command text, so it can be worded around; fails open on unreadable input).
- `system/hooks/guard_git_push_signpost.sh` — shows what a push would send before it leaves; with `system/hooks/roundB.conf`, its leakage findings are a sign (warn mode).
- `system/hooks/guard_gws_logout.sh` — refuses `gws` logout, which would destroy every Google credential (hard block; matches command text, so it can be worded around).
- `.claude/agents/sentinel.md` — the Sentinel Auditor; read-only checklist for secret exposure, folder permissions, key age and the MCP inventory (sign).
- **not built yet:** a session stopped from reading the key folder `~/.config/lifehack/`. Serves: `canon/canonical-principles-sop.md` §6.4.
- **not built yet:** a hard block on the push scan for the secret class of finding only, other leakage findings staying on warn; it waits for the launcher-lanes step, and until then the push scan is warn-only. Serves: `canon/canonical-principles-sop.md` §9 (2026-07-21).
- **not built yet:** the Sentinel Auditor covering connectors added on claude.ai and checking the key-folder read block. Serves: not yet in canon.
- **not built yet:** a rotation path beyond the Sentinel's age warning. Serves: not yet in canon.

**Outbound host lists**
- `system/egress-allowlist.md` — Level 1: the base domains a raw network call may reach.
- `system/hooks/enforce_egress_allowlist.sh` / `.py` — reads that list; refuses an unlisted host, a variable destination, and Python that speaks a mail protocol (hard block when it fires; matches command text, so it can be worded around; fails open on what it cannot parse).
- `system/hooks/roundB.conf` — switches for several guards, including `email_reader_block` and the push scan's mode.
- `system/safe-fetch-allowlist.md` — Level 2: the web-read seal; ships off; when on, `safe_fetch.py` refuses unlisted hosts before connecting.
- `system/tools/safe_fetch.py` — the sanitising web reader every content skill uses.
- `system/tools/job-fetch-hosts.txt` and `<personal-code>/job-fetch-hosts.txt` — the hosts a scheduled job's web reads are sealed to.
- `system/tools/vendor-read-allowlist.txt` and `<personal-code>/vendor-read-allowlist.txt` — per-job vendor-read exceptions; the shipped list is empty on purpose.
- **not built yet:** a personal copy of the Level 1 outbound list, so an update does not overwrite the person's additions. Serves: not yet in canon.

**Connectors**
- `system/hooks/sanitize_connector_output.sh` (logic in `system/hooks/lib/connector_sanitize.py`) — the connector door: cleans every `mcp__` tool result and withholds it on error.
- `system/tools/sanitize.py`, `system/tools/safe_input.py` — the sanitizer and injection scanner the door uses.
- **not built yet:** guards on connectors' own send, write and delete actions, matching the shell-command write guards (`system/hooks/guard_gmail_send.sh` and its siblings). Serves: not yet in canon.

**Tests and records**
- `system/hooks/tests/test_egress_wall.sh`, `test_sanitize_connector_output.sh`, `test_gws_logout_guard.sh`, `test_ingest_gate_enforce.sh` — the tests for the hooks above.
- `system/hooks/ingest_gate_enforce.sh` — refuses a session's raw outside read and routes outside text through `system/tools/safe_read.py` (hard block on the typed read tools; its shell-command checks match command text, so they can be worded around).
- `system/register/register.jsonl` — one row per hook and tool, from which the hook settings are generated.
