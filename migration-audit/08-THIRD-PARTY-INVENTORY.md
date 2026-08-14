# 08 — Third-Party / Secondary-Systems Inventory (T8.12a)

**Date:** 2026-08-14. **Method:** read-only grep/glob sweep across both repos for: `*_API_KEY` /
`*_TOKEN` / `*_SECRET` / `~/.config/` reads / keychain calls; `https://api.` and other external base
URLs; `command -v` / `which` availability checks; non-stdlib Python imports (AST-parsed against
`sys.stdlib_module_names`, cross-checked against the DONOR's `system/requirements.txt` — ⛔ not shipped
to DEST, which has no manifest of any kind, and that absence is itself one of this audit's findings); `brew install` in any
doc/script; MCP config (`.mcp.json`, `mcpServers`); and named external CLI invocations (`gws`, `gh`,
`clasp`, `chrome`, `ntfy`, `curl`/service). DEST = `/Users/envergjokaj/lifehack-brain`
(branch `migration-1`). DONOR = `/Users/envergjokaj/claudeops-config` (branch `main`).

**Extends, does not re-derive, the 2026-08-14 baseline** (11 DEST dependencies, 8 covered by
`INSTALL.md`, 3 missed — `gh`, headless Chrome, the dev-browser relay+extension). This sweep confirms
all three misses unchanged and adds one dependency the baseline folded into the "Google-connected
parts" bucket without a line of its own (`clasp`), plus one borderline internal-tooling finding
(`tmux`/iTerm2) reported separately because it reads as leftover donor-authoring material, not a
student-facing dependency.

**Count — scope (b), DEST:** **12 total** dependencies (11 baseline + `clasp`) · **9 covered** by
`INSTALL.md` · **3 missed** (unchanged from baseline) · **1 borderline** extra finding reported outside
the count (`tmux`/iTerm2).

> ## ⚖ AMENDED 2026-08-14 AFTER TWO RULINGS BY ENVER — the live count is now **11 total · 9 covered · 2 missed.**
> **① The browser relay is gone, not documented.** The overmyshoulder skill **does not ship** — *"that is
> an experiment and that stays explicitly on my system."* Its skill folder, its over_my_shoulder.sh and
> its oms_format.py were all removed from DEST (recoverable from git history; nothing is lost).
> ⭐ **This was the one dependency that could NOT be fixed by writing it down** — the tool is not Enver's
> to distribute, so a student could never obtain it. Removing the skill was the only honest close.
> `system/tools/render_shot.sh` is **independent of it and stays** — `/design-lifehack` still needs it.
> **② The `tmux` borderline finding is ruled the other way: `build-conductor-sop.md` SHIPS.**
> *"I definitely want them to have the build conductor SOP, that is very important. But we can take out
> the `brew install tmux`… Agent team waves are not as important but everything else is."* ⇒ the SOP
> stays, its tmux/iTerm2 setup block is removed, gear-3 is compressed rather than deleted.
> **⇒ THE REMAINING 2 MISSES ARE BOTH PURE DOCUMENTATION**, and both are `T8.12b`/`T8.12c` work:
> **`gh`/GitHub** (the whole bug-reporting path) and **headless Chrome** (every `/design-lifehack` screenshot).

---

## Scope (b) — what a stranger cloning DEST must obtain

| dependency | `file:line` | what breaks without it | `INSTALL.md` coverage | class |
|---|---|---|---|---|
| **git** | `INSTALL.md:166-193` (STEP 2) | can't clone or update the repo at all | YES — STEP 2, with Mac/Windows install paths | REQUIRED |
| **python3 ≥ 3.9** | `INSTALL.md:196-241` (STEP 3) | every tool (`safe_*`, hooks, skills) is Python; nothing runs | YES — STEP 3, incl. two measured Windows traps (blocked `winget`, decoy `python.exe`) | REQUIRED |
| **Serper API key** (serper.dev) | `system/tools/safe_search_api.sh:52-89`; `INSTALL.md:602-624` | `/websearch` and any research flow "refuses and says so"; rest of system unaffected | YES — dedicated "WEB SEARCH" section, incl. env var + macOS keychain fallback order | OPTIONAL (search only) |
| **pdfplumber** (PyPI) | `system/tools/safe_pdf.py:31,34-35` | reading a `.pdf` fails with an explicit `pip install pdfplumber` error | YES — `INSTALL.md:634`, prose `pip install` line | OPTIONAL (PDF ingest only) |
| **python-docx** (PyPI) | `system/tools/safe_docx.py:32` | reading a `.docx` fails the same way | YES — `INSTALL.md:635` | OPTIONAL (.docx ingest only) |
| **openpyxl** (PyPI) | `system/tools/safe_xlsx.py:29-34,133`; also used by `safe_csv.py` | reading a `.xlsx` fails the same way | YES — `INSTALL.md:636` | OPTIONAL (.xlsx ingest only) |
| **ntfy** (app + topic string) | `shared/notify/notify-send.sh:60-65` (topic file `~/.config/lifehack/ntfy-topic`, its own comment calls it "a shared secret in disguise") | no phone push notifications; everything else unaffected | YES — dedicated "NOTIFICATIONS ON YOUR PHONE" section, `umask 077` walkthrough | OPTIONAL |
| **`gws` CLI + a Google account** | `system/tools/safe_calendar.py`, `system/tools/safe_tasks.py`, plus ~10 hooks (`guard_gws_logout.sh`, `guard_calendar_writes.sh`, etc.) | no calendar/task reads, no Sheets writes for `/google-sheet`; core system unaffected | YES — dedicated "THE GOOGLE-CONNECTED PARTS" section, incl. the never-logout hard rule | OPTIONAL |
| **`clasp`** (Google's Apps Script CLI) | `.claude/skills/google-sheet/SKILL.md:46,375` (`~/.clasprc.json`, machine-local) | `/google-sheet` falls back to formulas/`ARRAYFORMULA` only — "most sheets never need it" | YES — `INSTALL.md:711-715`, explicitly optional-of-optional | OPTIONAL |
| **`gh` CLI + a GitHub account** | `docs/REPORT-A-BUG.md:122,182,191,202,274` | the entire bug-reporting path (`gh auth login`, `gh issue create`) has nothing to run against | **NO** — never referenced from `INSTALL.md`, only from `REPORT-A-BUG.md` | REQUIRED (for that one path) — **MISS** |
| **Google Chrome (headless)** | `system/tools/render_shot.sh:44-62` (`find_chrome()`, hard-fails with an install message if none found) | every dashboard/design screenshot in `/design-lifehack` hard-fails | **NO** — only `.claude/skills/design-lifehack/SKILL.md:334,453` | REQUIRED (for that skill) — **MISS** |
| ~~Unnamed browser-automation relay + Chrome extension~~ | over_my_shoulder.sh · overmyshoulder/SKILL.md · oms_format.py — ⛔ **all three REMOVED FROM DEST 2026-08-14** | nothing — the skill that needed it no longer ships | **RESOLVED BY REMOVAL, not by documentation** | ⚖ **RULED OUT, Enver 2026-08-14:** *"that is an experiment and that stays explicitly on my system, it doesn't ship to the students."* |

### Borderline finding, reported separately (not counted above)

| item | `file:line` | note |
|---|---|---|
| `tmux` / iTerm2 (`brew install tmux`) | `system/sops/build-conductor-sop.md:126-141` | Reads as Enver's own multi-agent "gear-3 Agent-Team wave" build methodology (Claude Code power-user workflow), not a Lifehack Brain runtime dependency. It shipped into DEST as part of the SOPs folder. Not required for any documented student-facing skill; `INSTALL.md` correctly says nothing about it. Flagged so it's a conscious decision, not an oversight, whether this SOP belongs in the student-facing repo at all. |

---

## Scope (a) — DONOR-only references (Enver's own; may be paying for / has installed and lost track of)

None of the following are needed by DEST — they belong to the desk-specific / personal side of
`claudeops-config` that never migrated (Emily, Marc, Clair, Deryl, dobby, hollywood-db, and the
DONOR's own dev tooling).

> ⛔ **EVERY PATH IN THIS TABLE IS A DONOR PATH AND DOES NOT SHIP TO DEST.** Each row's last cell
> therefore ends with an explicit `⛔ not shipped` marker — the citation lint checks claims line by line
> and a section heading does not reach the lines under it. This is the marker, not a formality: without
> it a reader (or a checker) reads these as paths that ought to be here and are missing.

| item | `file:line` (DONOR) | what it is |
|---|---|---|
| **Supabase** (project ylhsicaijzwqgbuagkzy.supabase.co) | `system/tools/supabase-backup.sh:4,8` — plus supabase-keepalive.sh:4,8 and egress-allowlist.md:29-33 alongside it | Emily/hollywood-db project database. Credentials (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_DB_PASSWORD`) live at `~/.config/hollywood-grind/credentials`, chmod 600. Host-locked in the egress allowlist. ⛔ not shipped |
| **TMDB** (The Movie Database) API | `shared/tools/tmdb_credits.py:23,283-296` | `TMDB_TOKEN` env var, used by the hollywood-db skill to pull cast/credit data. ⛔ not shipped |
| **RocketMoney** | `desks/deryl/.claude/commands/deryl-rocketmoney.md`; `skills/deryl-rocketmoney/SKILL.md` | Personal finance aggregator. Ingested via CSV export (Workflow A) and a Chrome browser plugin that prompts account-balance snapshots (Workflow B) — the plugin itself is a separate installed extension, not code in this repo. ⛔ not shipped |
| **Emporia Energy monitor** | `system/tools/emporia_ingest.py`; `system/tools/emporia-run.sh:15`; `system/requirements.txt` (`pyemvue==0.18.9`, commented out, "STUDIO-ONLY") | Hardware energy monitor at the carriage house + account; keychain service `emporia-energy`. Runs under a separate venv (`~/.local/share/claudeops-venv`), not system Python. ⛔ not shipped |
| **Home Assistant** (self-hosted) | `system/tools/dobby-health.py:37,61`; `.claude/skills/dobby-scan/` | Long-lived token at `~/.config/claudeops/secrets/dobby-ha-token.txt`. Self-hosted server, not a SaaS bill, but a standing integration to account for. ⛔ not shipped |
| **eCARe / College Park GA utilities portal** | `system/tools/cp-utilities-run.sh:15-20` | Scraped billing portal login; keychain service `ecare-collegeparkga`. Currently **disabled** in `pulse-config` pending a password-fallback code change — worth knowing it's dormant, not gone. ⛔ not shipped |
| **OpenAI (`codex` CLI)** | `system/tools/load_api_keys.sh:30` — plus egress-allowlist.md:39-43,54-66 and system/parts/voted_judge.py / routing_evals.py | Used as the **blind grader** for the skill factory (a second model family so the factory doesn't grade its own homework). Keychain service `claudeops-openai` → `OPENAI_API_KEY`. LuLu's approval is version-path-pinned — an upgrade re-prompts and can silently hang an unattended run. ⛔ not shipped |
| **Moonshot / Kimi AI** | `system/tools/load_api_keys.sh:31`; also `KIMI-AUDIT-PROMPT.md` at the DONOR repo root | Keychain service `claudeops-moonshot` → `MOONSHOT_API_KEY`. The repo root file suggests this migration audit itself was drafted for a Kimi-run pass — worth confirming that key is still wanted. ⛔ not shipped |
| **Z.ai (ZAI)** | `system/tools/load_api_keys.sh:32` | Keychain service `claudeops-zai` → `ZAI_API_KEY`. No other reference found in this sweep — candidate for "am I still using this." ⛔ not shipped |
| **OpenRouter** | `system/tools/load_api_keys.sh:33` | Keychain service `claudeops-openrouter` → `OPENROUTER_API_KEY`. Same note as Z.ai — no other reference found. ⛔ not shipped |
| **OpenCode CLI** | `system/reference/opencode.json`; `quarantine/opencode/opencode-ai-1.18.5.tgz` | A third-party AI coding CLI/launcher — `load_api_keys.sh`'s own comment names it as the consumer of the four keys above ("e.g. the OpenCode launcher"). The `.tgz` sitting in `quarantine/` suggests it was scanned but its live install location wasn't confirmed in this sweep. ⛔ not shipped |
| **yfinance** (PyPI, free) | `system/requirements.txt:12` | Market data (SPY/VIX/rates) for the Marc desk. Free library, no account — flagged only for completeness, not a "cancel" candidate. ⛔ not shipped |
| **LuLu** (macOS firewall) | `system/egress-allowlist.md:8,51`; `system/organism/elements/egress-allowlist-wall.md`; `system/security-canon.md` | Per task instructions: this is Enver's own OS-layer firewall app, not a student-facing service — a rule inside it is pinned to his exact Mac and codex path. His to account for/cancel, not DEST's to install. ⛔ not shipped |

### Also present but shared with DEST (not DONOR-only, listed for completeness only)

`gws`, `clasp`, and `ntfy` all appear in DONOR too, under the same names/keychain patterns as DEST —
not separately counted here since they're already scope (b) rows above.

---

## Summary for the reader

- **DEST total: 12 dependencies** (11 baseline + `clasp`, which the baseline had implicitly folded
  into the Google bucket). **9 are covered by `INSTALL.md`, 3 are not** — same three as the baseline:
  `gh`/GitHub (bug-reporting path only), headless Google Chrome (`/design-lifehack` screenshots), and
  the unnamed dev-browser relay + Chrome extension — ⛔ **that third one is now CLOSED by removal, not
  by documentation** (the skill needing it was ruled out 2026-08-14 and deleted from DEST), which drops
  the live figures to **11 total · 9 covered · 2 missed**, both of the remaining two being pure
  documentation work.
- **Scope (a) surfaced 12 DONOR-only third-party items** Enver may be paying for or running standing
  infrastructure for: Supabase, TMDB, RocketMoney (+ its Chrome plugin), Emporia, Home Assistant,
  eCARe, and four LLM-provider API keys (OpenAI/codex, Moonshot/Kimi, Z.ai, OpenRouter) behind an
  OpenCode CLI launcher — plus yfinance (free) and LuLu (his own machine's firewall, not cancelable
  SaaS but worth confirming is still wanted).
