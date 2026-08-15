---
element: label-checker
title: "label-checker — element detail (ground/base altitude)"
subsystem: organism-integrity
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C5 unguarded ground truth (label_manifest.yaml) + C4 (downgrade detection never wired to cron). Guard lands AFTER S2.2 (premortem)"
generated_from:
  - system/tools/organism/label_checker.py
  - system/tools/organism/label_manifest.yaml
  - system/reference/settings.json
  - system/hooks/guard_organism_map.sh
  - system/hooks/nudge_flow_drift.sh
  - system/hooks/validate_on_write.sh
  - system/organism/elements/security-ingest-gate.md
  - system/organism/manual.md
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# label-checker — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#label-checker ; ground truth → the live artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the honesty-integrity loop.
> The MIDDLE manual (`system/organism/manual.md`) carries only a one-line pointer here; the TIP
> (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **One-line:** fire-test every guard the self-schematic map CLAIMS is enforced — against a synthetic
> violation — and compute LIVE/PARTIAL/TARGET from the result; then stamp the computed label into the
> element file. Without this, the map's labels are hand-typed prose in a machine costume.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

> **CITATIONS — what the paths below resolve to here.** The body describes the donor system truthfully; the three lines below record what happened to each named file at THIS destination, and they cover every mention of them in the body.
>
> ⛔ `system/reference/settings.json` — does not ship: the donor kept a git-tracked reference COPY there because its real settings lived outside the repo. Here the real, git-tracked settings file is `.claude/settings.json`, so the copy has no job. The port is recorded in the engine itself — `system/tools/organism/label_checker.py` lines 28-36: *"SETTINGS moved from `system/reference/settings.json` (donor path, absent here) to `.claude/settings.json`."* Every sentence below naming the donor path is describing the donor.
>
> ✅ `system/hooks/guard_organism_map.sh` — **SHIPPED 2026-08-15.** Present, registered under `PreToolUse` / `matcher: "Write"` in `.claude/settings.json`, fire-tested through a real session launched from this repo, and carrying a live row (`organism-map-write-guard`) in `system/tools/organism/label_manifest.yaml` with 6 violations and 5 allow-cases. Suite: `system/hooks/tests/test_organism_map_guard.sh`.
> ~~⛔ `system/hooks/guard_organism_map.sh` — never ships, DROPPED by ruling. `label_manifest.yaml` records the decision verbatim: three donor guards "DO NOT EXIST HERE AND STRUCTURALLY CANNOT". Its fire-test row is gone from the manifest, so nothing here claims it is enforced.~~ ← struck 2026-08-15. The ruling it cited rested on a single premise — that `system/organism/` did not exist here — and Phase 9 landed that tree, killing it. The last sentence was the costly one: *"nothing here claims it is enforced"* was FALSE even when written, because six shipped files already described the tree as write-guarded — `manual.md` (4 occurrences) and 5 `elements/*.md` (archivist, claude-md-pyramid, hook-plane, label-checker, pulse-cron), counted with grep rather than asserted. `map-format-specs.md` §6.4 was the honest one: it described the guarantee and admitted it was unenforced here. A drop-note that mis-states what the rest of the repo claims is how a documented-but-absent protection survives review (house rule `T9.11b`).
>
> ⏳ unruled — `system/hooks/nudge_flow_drift.sh`. It is not on disk, it is absent from the manifest, and it was NOT one of the three guards that manifest explicitly dropped —
> yet `system/organism/manual.md` line 49 still cites it as a live drift nudge. Cited by something shipped, on no ship list, awaiting a decision: a DEBT, not a pass.

---

## AUTHORED   (human-only)

### THE HONESTY PROBLEM THIS SOLVES

The `validate_on_write` inert-guard lesson (named explicitly in `label_checker.py:7`): a hook can be
registered in `settings.json` and still do nothing — registration alone is not proof of enforcement. A
hand-typed `LIVE` label is just an authored belief. This element is the machine-verification loop that
turns that belief into a claim backed by a real fire-test: the real guard script, given a synthetic
violation payload, must produce `exit 2`. Only then is the label not lying.

---

### MODES / SUBCOMMANDS

`label_checker.py` is a CLI tool invoked manually (no cron wiring exists in the live codebase today).
It has three subcommands (label_checker.py:389-409):

**1. `check [--manifest PATH] [--guard ID] [--json]`**
(label_checker.py:393-397)
Evaluates every guard in `label_manifest.yaml` (or the one named by `--guard`). The optional
`--manifest PATH` overrides the default manifest path (`system/tools/organism/label_manifest.yaml`).
For each guard:
- Checks git-tracking of the hook script (`git ls-files --error-unmatch`).
- Checks registration in the git-tracked `settings.json` (`system/reference/settings.json`) — the
  repo-canonical copy only, never a machine-local file. A guard registered only on one machine is
  PARTIAL by design.
- Expands `~` and `$HOME` in all payload values via `expand_payload()` (label_checker.py:79-85),
  then fires every synthetic violation payload (JSON on stdin via `bash <script>`) and asserts `exit 2`.
- Fires every allow-case and asserts `exit 0` — proves the guard discriminates rather than fail-closes
  on everything indiscriminately.
- Labels: LIVE (all checks pass) · PARTIAL (any check fails) · TARGET (script doesn't exist).
- Detects **downgrades**: if the manifest claims LIVE but the computed label is lower, exits non-zero
  and names the downgraded guard. The weekly Archivist cron (not yet wired — see GAPS) is the
  declared caller that turns that non-zero into a phone-ping via notify-plane.
- Exit codes: `0` (all claimed labels verified), `1` (any downgrade), `3` (error: manifest not found,
  yaml module absent, guard id not found).
- `--json` emits a machine-readable JSON object `{"results": [...], "downgrades": [...]}`.

**2. `selftest`**
(label_checker.py:269-305)
Who-watches-the-watcher. Creates a `tempfile.TemporaryDirectory()` and writes
`/{tmp_dir}/inert_guard.sh` inside it (an always-`exit 0` script — enforces nothing). Wraps it in a
synthetic manifest entry that CLAIMS LIVE, then calls `_evaluate_abs()` and asserts the checker
computes PARTIAL. If the checker labels an inert guard LIVE, the checker itself is silently broken.
The `/tmp`-path is not under REPO, so `git_tracked()` correctly returns False (not git-tracked)
regardless of the random directory name. Confirmed: exits 0 on pass (the checker correctly computes
PARTIAL for the inert guard). Story log #17 confirms this selftest was proven.
- Exit codes: `0` (PASS — checker refused to rubber-stamp the inert guard), `1` (FAIL — checker mislabeled LIVE).

**3. `write-labels [--manifest PATH] [--elements PATH] [--dry-run]`**
(label_checker.py:332-386)
The label-writer half of Feature 1.5. The optional `--manifest PATH` and `--elements PATH` flags
override the defaults (`system/tools/organism/label_manifest.yaml` and `system/organism/elements/`
respectively). After computing each guard's label via the same fire-test path as `check`, writes ONLY:
- The `maturity_label:` field in frontmatter (regex `(?m)^(maturity_label:\s*)(LIVE|PARTIAL|TARGET)`
  — label_checker.py:366).
- The `**maturity_label:**` line in the `## AUTO-COMPUTED` block (regex
  `(\*\*maturity_label:\*\*\s*)(LIVE|PARTIAL|TARGET)` — label_checker.py:367).
- The `**last_checked:**` date (today's ISO date, regex
  `(\*\*last_checked:\*\*\s*)\d{4}-\d{2}-\d{2}` — label_checker.py:368).
It never touches the `## AUTHORED` block. Guards that have no element file (e.g., infrastructure guards
without a corresponding `elements/<slug>.md`) are skipped with a logged warning. Element files whose
`element:` frontmatter slug does not match any manifest guard id are also untouched (hand-set labels are
preserved). Matching: the element file's `element:` frontmatter value must equal the guard's `id`.
`--dry-run` shows what would change without writing.

**Edge case — `pending` in `last_checked:`:** The `last_checked:` regex requires an ISO date
(`\d{4}-\d{2}-\d{2}` — label_checker.py:368). If the field currently holds `pending` (as in this
file's initial draft state), the regex does NOT match and `last_checked:` is silently left as `pending`
even after a successful write-labels run that updates `maturity_label:`. The field will only be stamped
with a real date on a run where the regex finds a date to replace — or if manually set to an ISO date
first. See GAPS #6.

---

### LABEL SEMANTICS (the definitions this element enforces)

| Label | Meaning |
|---|---|
| **LIVE** | Script git-tracked AND registered in git-tracked settings.json AND blocks every synthetic violation (`exit 2`) AND passes every allow-case (`exit 0`). A real, discriminating control. |
| **PARTIAL** | Script exists but ≥1 check fails: not git-tracked, or not registered, or a violation didn't block, or an allow-case was wrongly blocked. Works on one machine or sometimes — not reliably everywhere. |
| **TARGET** | Script does not exist yet. Declared intent only. |

**Downgrade is fail-closed:** the moment any check fails, the checker writes PARTIAL (never silently
upgrades). Upgrading from PARTIAL to LIVE requires re-running and passing the full fire-test.

---

### FULL HAND-OFF CHAIN

#### check mode

```
operator → Bash: python3 label_checker.py check [--manifest PATH] [--guard ID] [--json]
  → label_manifest.yaml (REPO/system/tools/organism/label_manifest.yaml)  [honor: no gate on this read]
  → REPO/system/reference/settings.json                                    [honor: direct file read, no gate]
  → git ls-files --error-unmatch <rel-path>                                [honor: subprocess, no gate]
  → expand_payload(payload)   [expand ~ and $HOME in all values]           [skill: built-in expansion step]
  → bash <hook-script> stdin=JSON-payload, timeout=30                      [the guard under test IS the gate]
  → exit code → LIVE/PARTIAL/TARGET + reasons
  → stdout (human-readable) or JSON on --json
  → overall exit 0 (all verified) | 1 (any downgrade) | 3 (error)
```

Step grammar:

1. `operator → Bash port → label_manifest.yaml (REPO/system/tools/organism/label_manifest.yaml) → [honor] no gate`
   The manifest is read directly; no hook intercepts this internal-clone read (trusted zone;
   `ingest_gate_enforce.sh` allows internal reads via the trusted-zone allow-case).

2. `label_checker.py → load_settings() → system/reference/settings.json → [honor] (direct file read, no gate)`
   (label_checker.py:101-107) Uses ONLY the REPO-canonical path — never `~/.claude/settings.json` or
   any local copy. A guard registered only locally is PARTIAL by this design: the repo copy is the
   two-machine truth.

3. `label_checker.py → git_tracked(path) → git ls-files --error-unmatch → [honor] (subprocess, exit code only)`
   (label_checker.py:88-98) Determines whether the hook script travels to both machines. A script not in
   git is PARTIAL regardless of what it does.

4. `label_checker.py → is_registered(settings, script_name, wanted) → in-memory settings dict → [honor]`
   (label_checker.py:110-135) Checks each `(event, matcher)` row in the guard's `registered:` list
   against the settings dict. Missing any → not registered → PARTIAL.

5. `label_checker.py → expand_payload(payload) → in-memory dict → [skill: built-in step]`
   (label_checker.py:79-85, called at label_checker.py:141) Recursively expands `~` and `$HOME` in all
   string values of the payload dict (file_path, url, command, etc.) before serialization. Without this
   step, `$HOME`-bearing paths in manifest payloads (e.g., allow-case
   `$HOME/lifehack-brain/README.md`) would be sent as literal strings, causing allow-case fire-tests
   to fail on paths that don't exist verbatim. This is a load-bearing pre-serialization step.

6. `label_checker.py → fire(script_abs, payload) → bash <script> stdin=JSON, capture_output=True, timeout=30 → exit code → [skill] the checker's mandatory fire() logic runs the guard script as a subprocess; no Claude Code hook fires at this step`
   (label_checker.py:138-146) The decisive step. `fire()` delivers the payload the same way Claude Code
   does: `body = json.dumps(expand_payload(payload))` — faithful JSON on stdin (NOT echoed — an echoed
   `\n` mangles the JSON and fail-opens, faking a pass). Timeout = 30 s to prevent a hanging guard from
   blocking the suite. `fire()` returns `proc.returncode` — it does NOT assert anything itself. The assertion `ok=(rc==expect_block_exit)` (default 2 for denial) is performed in `evaluate()` at line 191. For
   allow-cases, `evaluate()` asserts `ok=(rc==0)` at lines 200-202 — `fire()` asserts nothing for either case.

7. `evaluate(guard) → label + reasons dict → stdout or JSON [honor: the output is informational, not a gate]`
   (label_checker.py:149-214) LIVE iff: `tracked AND reg_ok AND blocks_ok AND allows_ok`.

#### write-labels mode

```
operator → Bash: python3 label_checker.py write-labels [--manifest PATH] [--elements PATH] [--dry-run]
  → label_manifest.yaml (same default path)             [honor]
  → evaluate(guard) per guard (same fire-test chain as check, steps 1–7 above)
  → glob elements_dir (REPO/system/organism/elements/*.md) for element: <slug>  (label_checker.py:350-354)
  → regex rewrite of system/organism/elements/<slug>.md  (label_checker.py:366-368)
  → p.write_text(new_content) if not dry_run             [Python direct write, NOT the Claude Write tool]
```

Critical design note: `write-labels` writes via Python's `p.write_text()` (label_checker.py:374) — it
is NOT mediated by the Claude Write tool. This means `guard_organism_map.sh` (PreToolUse Write) does NOT
intercept these writes. This is correct by design: `write-labels` is an authorized maintainer CLI tool
that writes only the `## AUTO-COMPUTED` block, never `## AUTHORED`. The guard protects against
Claude-session Write-tool wholesale overwrites of `manual.md` and `map-format-specs.md`; it was never
designed to intercept a trusted Python script's targeted regex-rewrite. (See GAPS for the
manifest-unguarded corollary.)

#### selftest mode

```
operator → Bash: python3 label_checker.py selftest
  → tempfile.TemporaryDirectory() → writes /{tmp_dir}/inert_guard.sh (always exit 0, not under REPO)
  → _evaluate_abs(guard, inert_path)   (label_checker.py:308-329)
       → git_tracked(/{tmp_dir}/path) → False (not under REPO → correctly not git-tracked)
       → fire(inert_path, violation_payload) → exit 0 (allows the violation → NOT blocked)
  → assert computed label == "PARTIAL"
  → exits 0 on PASS, 1 on FAIL
```

(label_checker.py:269-305) Uses `tempfile.TemporaryDirectory()` — a random-named temp dir such as
`/tmp/tmpXXXXXX/inert_guard.sh` (not the literal `/tmp/inert_guard.sh`). The `/tmp`-path is outside
REPO, so `git_tracked()` correctly returns False regardless of the exact random name. If selftest exits
1, the checker is silently broken: it would label inert guards LIVE and the whole map honesty system is
compromised. This mode is the meta-test that guards the guard.

---

### PORTS TOUCHED

**Reads:**
- `system/tools/organism/label_manifest.yaml` — guard specifications (id, script, payloads, registrations,
  claimed labels)
- `system/reference/settings.json` — authoritative two-machine registration source
- `system/hooks/*.sh` (each guard script listed in the manifest) — read by `fire()` via Bash stdin
- `system/organism/elements/*.md` — scanned for `element:` frontmatter to match guard ids (write-labels
  mode); also the destination of the label writes

**Writes (write-labels mode only):**
- `system/organism/elements/<slug>.md` — rewrites ONLY `maturity_label:` + `last_checked:` fields via
  targeted regex (label_checker.py:366-368); never touches `## AUTHORED` content
  Via Python `p.write_text()` — NOT the Claude Write tool; `guard_organism_map.sh` does not intercept.
  NOTE: `nudge_flow_drift.sh` (PostToolUse Write|Edit, settings.json:263) does NOT fire on these
  Python-direct writes — PostToolUse hooks are triggered only by the Claude Write/Edit tool, not by
  Python's `p.write_text()`. There is no seam between write-labels and nudge_flow_drift.

**Subprocess calls:**
- `git ls-files --error-unmatch <rel>` (cwd=REPO) — git-tracking check (label_checker.py:93-96)
- `bash <script>` stdin=JSON — the fire-test itself (label_checker.py:142-145)

**No network, no Drive, no session-external resources.**

---

### OUTCOME

For each guard in `label_manifest.yaml`: a computed LIVE/PARTIAL/TARGET label backed by a real fire-test,
not an assertion. Downgrades exit non-zero. `write-labels` stamps those labels into the corresponding
element files' `## AUTO-COMPUTED` blocks so the map's stated labels reflect real behavior. The selftest
proves the checker itself cannot be fooled by an inert guard.

---

### GENERATED_FROM

`system/tools/organism/label_checker.py` (the engine) · `system/tools/organism/label_manifest.yaml`
(the guard specs + payloads) · `system/reference/settings.json` (registration source; line 98 =
guard_organism_map.sh Write-matcher registration; line 263 = nudge_flow_drift.sh PostToolUse
Write|Edit registration; line 273 = validate_on_write.sh PostToolUse Write|Edit registration)
· `system/hooks/guard_organism_map.sh` (guard under test #2 — organism-map-write-guard fire-test target)
· `system/hooks/nudge_flow_drift.sh` (PostToolUse advisory; fires after element-file edits)
· `system/hooks/validate_on_write.sh` (PostToolUse advisory; inert by design for element files)
· `system/organism/elements/security-ingest-gate.md` (the reference LIVE element; proved the checker
pattern — NOTE: the `:8` proof citation is invalid; label_checker.py:8 contains no reference to this element) · `system/organism/manual.md` (honesty-label criteria and
LIVE/PARTIAL/TARGET definitions)

---

### ENFORCEMENT POINTS (the honest map)

**On `label_checker.py` itself (what gates the checker's environment):**

1. **`guard_organism_map.sh` (PreToolUse Write, matcher=Write)** `[hook]` — BLOCKING. Protects
   `manual.md` and `map-format-specs.md` from wholesale Write-tool overwrite. Registered at
   `settings.json:98-105` (PreToolUse, matcher=Write). **Edit calls never reach this hook — the hook's
   matcher is `Write` only; Claude Code does not route Edit tool calls to a Write-matcher hook. The
   authoring path (Edit) bypasses this guard by scope exclusion, not by the hook inspecting and
   returning exit 0 — the hook has no Edit-aware logic.** Fire-tested LIVE: 2 violations blocked, 2
   allow-cases pass. Git-tracked confirmed.

2. **`nudge_flow_drift.sh` (PostToolUse Write|Edit)** `[honor]` — advisory only, always exits 0.
   (settings.json:263) Fires after any Write or Edit to a file cited in an element's `generated_from`
   list. Nudges a human to re-run the checker or re-author the element when a source file is edited.
   Does NOT block. PostToolUse hooks never block by design. This is the detect-and-nudge layer, not a
   blocking gate.

3. **`validate_on_write.sh` (PostToolUse Write|Edit)** — advisory / inert by known history (the
   "validate_on_write inert-guard lesson" that `label_checker.py:7` names). (settings.json:273) Fires on
   any Write/Edit; no blocking behavior for element files. PostToolUse never blocks. Not a gate on this
   element's stores.

4. **`ingest_gate_enforce.sh` (PreToolUse Read/Bash)** `[hook]` — fires on every Read and on Bash
   calls. Reads of files inside the clone (`$HOME/lifehack-brain/*`) are in the trusted zone and
   PASS (exit 0 per the trusted-zone allow-case). This is not a gate on the checker's operation; it's a
   pass-through for the checker's source files.

**NOT gated (by design):**

- **`label_manifest.yaml`** — the manifest is the checker's ground-truth (violation payloads, guard ids,
  claimed labels). No registered hook guards Write or Edit to it. `guard_organism_map.sh` guards only
  `manual.md` and `map-format-specs.md`. A Write to the manifest passes all hooks. The manifest comment
  (`label_manifest.yaml:13`) names this: "Feature 1.6 adds a write-guard on it" — this guard is NOT
  built. See GAPS #1.

- **`label_checker.py` itself** — a CLI tool, not a hook. No hook fires on execution of the script.
  No registration needed (it is not in the Claude-tool path). This is correct by design.

- **`write-labels` writes to element files** — Python `p.write_text()` (label_checker.py:374), not the
  Claude Write tool. `guard_organism_map.sh` does not intercept; `nudge_flow_drift.sh` does NOT fire
  at all for Python direct writes — PostToolUse hooks are triggered only by the Claude Write/Edit tool,
  not by `p.write_text()`, so no condition on `generated_from` membership applies. No
  blocking gate on these writes by design (the checker is a trusted maintainer tool).

---

### INTENT / CURRENT-VS-TARGET

**Intent:** make every LIVE/PARTIAL/TARGET label in the self-schematic map a machine-verifiable claim,
not a hand-typed assertion. The map's honesty is only as good as this checker's coverage — every guard
the map claims must have a corresponding fire-test in `label_manifest.yaml`. The checker is the
integrity loop that prevents the map from lying about what it enforces.

**Current → LIVE.** Both guards in `label_manifest.yaml` (`security-ingest-gate` and
`organism-map-write-guard`) are git-tracked, registered, and fire-tested. Both compute LIVE as of
2026-07-22 (`security-ingest-gate.md:76` AUTO-COMPUTED block; confirmed this session). Selftest mode
proven (inert guard correctly computes PARTIAL — story log #17). `write-labels` mode proven adversarially
(corrupt label corrected, non-manifest element untouched — story log #19). The checker is git-tracked
(`system/tools/organism/label_checker.py`) and travels with the clone.

**Qualification:** the LIVE label applies to the checker's proven operation within its current manifest
scope (2 guards). The gaps below document where the checker's coverage or automation is not yet complete.

**TARGET items:**

1. **Wire the weekly cron** — `label_checker.py check` is the intended input to the weekly Archivist
   cron (brief story log pairs with Feature 2.1 desk-freshness check). Not yet wired. The
   "downgrade → phone-ping" path (`label_checker.py:262`: `"(weekly cron would phone-ping)"`) is prose,
   not a live escalation. Until wired, downgrade detection requires a manual run.

2. **Add Feature 1.6 manifest write-guard** — `label_manifest.yaml` is unguarded (see GAPS #1). The
   manifest comment names it; the guard was not built as part of the initial Feature 1.5 work.

3. **Grow manifest coverage** — as T2/T3 elements are authored and their guards are built, a
   corresponding manifest entry must be added. The checker's coverage is 2 guards today; every new
   `[hook]` element adds a guard entry to reach full map coverage.

---

### GAPS   (documented fail-open conditions — source for `·gap` on the label)

> These are documented, accepted conditions in the code and prior audit that reduce enforcement
> certainty for a tip-only reader trusting the bare `LIVE` label.

**GAP 1 — `label_manifest.yaml` is unguarded (the checker's ground-truth has no write-guard).**
The manifest declares which guards to fire-test, what violation payloads to use, and what the claimed
labels are. A Write to `label_manifest.yaml` passes all hooks — `guard_organism_map.sh` guards only
`manual.md` and `map-format-specs.md`; the manifest is at a different path and has no registered
Write/Edit guard. `label_manifest.yaml:13` names this explicitly: "Feature 1.6 adds a write-guard on
it" — this guard is NOT built. An attacker who can Write to the manifest can change violation payloads
to trivially-passing ones, change claimed labels to TARGET (suppressing LIVE claims), or add guards
pointing at inert scripts. The checker would then produce clean output from a corrupt ground-truth.
**ACCEPTED GAP, named in the code. Real blast-radius: map honesty integrity.**

**GAP 2 — Weekly cron is not wired; downgrade detection requires a manual run.**
`label_checker.py:262` prints `"(weekly cron would phone-ping)"` as a prose comment. No cron entry
calls the checker. The brief (story log #17) names this: "not yet wired to the weekly Archivist cron
(pairs with the 2.1 desk-freshness check per the pre-mortem — wire both together)." Until wired, a
guard that silently degrades (hook script modified, settings.json de-registered, git-tracking lost) will
not be detected until a human manually runs `label_checker.py check`. The downgrade path exists in code;
the automation that acts on it does not. **NAMED GAP, target behavior.**

**GAP 3 — `write-labels` bypasses `guard_organism_map.sh` on element writes.**
`write-labels` uses Python `p.write_text()` (label_checker.py:374) — not the Claude Write tool — so the
PreToolUse hook cannot intercept. This is correct by design (the checker is a trusted maintainer CLI,
not a Claude session write). No false claim of hook protection exists; the gap is that someone invoking
`write-labels` with a corrupt manifest (GAP 1) can silently overwrite labels in all element files
without any hook firing. The design intent is that the CLI is a trusted path, but the trust rests on
GAP 1 being closed. **BY DESIGN for the CLI path; residual risk is the cascade from GAP 1.**

**GAP 4 — Two-machine deploy verification is owed.**
`guard_organism_map.sh` and `nudge_flow_drift.sh` are git-tracked and registered in
`system/reference/settings.json`, but the second machine's registration has not been confirmed by a human
this session. Brief story log #17: "2-machine deploy-verify owed: the 2 new hooks (guard_organism_map,
nudge_flow_drift) need git pull + watch-fire on the second machine (only the operator can confirm the other machine)."
The checker classifies any non-git-tracked hook as PARTIAL — but this machine confirmation is a human
step that the code cannot enforce. **HUMAN VERIFICATION OWED.**

**GAP 5 — `pyyaml` soft dependency.**
`label_checker.py:44-47` imports `yaml` with a try/except; if `pyyaml` is absent the manifest load
exits 3 on the yaml-parse step. Not a hook gap; a runtime reliability gap that renders the checker
inoperable without a clear error message distinguishing missing-module from enforcement failure.
**SOFT DEPENDENCY, no hook mitigation.**

**GAP 6 — `write-labels` silently skips `last_checked:` when the field holds `pending`.**
The `last_checked:` regex (`(\*\*last_checked:\*\*\s*)\d{4}-\d{2}-\d{2}` — label_checker.py:368)
requires an ISO date. New element files initialised with `**last_checked:** pending` (as is common for
drafts) will NOT have the field updated on the first `write-labels` run — the regex does not match
`pending`, so the field is left as-is even though `maturity_label:` is correctly stamped. The field only
receives a live ISO date when the regex can match an existing date. A reader of the element file will see
a current `maturity_label:` but a stale/unset `last_checked:` with no warning.
**BEHAVIOR GAP — no code mitigation; a `pending` sentinel is not handled as a special-case date target.**

---

### ★ INTEROP SEAMS (shared-state edges — the organism view)

Each seam uses a verb from the closed vocabulary (`map-format-specs.md §8.3`).

```
READS        hook-plane         · system/reference/settings.json is the checker's canonical registration
                                   source; hook-plane owns this store; label-checker reads it to verify
                                   every claimed LIVE registration (two-machine truth by git-canonical path)

READS        hook-plane         · system/hooks/*.sh — label-checker fires each guard script directly via
                                   bash stdin to assert it blocks (exit 2); hook-plane owns and maintains
                                   the hook fleet that label-checker fire-tests

WRITES->     security-ingest-gate · system/organism/elements/security-ingest-gate.md ## AUTO-COMPUTED —
                                   write-labels stamps maturity_label: + last_checked: from fire-test
                                   results into this element's file (the reference LIVE element)

WRITES->     security-ingest-gate · write-labels matches element files by `element:` frontmatter slug
                                   == manifest guard id. Manifest has two guards: `security-ingest-gate`
                                   (element file exists → written) and `organism-map-write-guard` (no
                                   element file carries `element: organism-map-write-guard` —
                                   `egress-allowlist-wall.md.draft` has `element: egress-allowlist-wall`,
                                   which does NOT match). So write-labels logs '⚠ skipped (no
                                   section/label): organism-map-write-guard' and writes nothing into
                                   `egress-allowlist-wall.md.draft`. Only `security-ingest-gate.md` is
                                   stamped by write-labels today. Source: label_checker.py:350-376.

GUARDED-BY   hook-plane         · guard_organism_map.sh (PreToolUse matcher=Write) blocks wholesale
                                   Write-tool overwrites of system/organism/manual.md and
                                   system/organism/map-format-specs.md — the two files that carry the
                                   label criteria + format specs the checker reads and enforces; Edit
                                   calls are out of scope for this hook (matcher=Write only — they bypass
                                   by scope, not by any hook permit logic)

FEEDS        archivist          · system/organism/elements/*.md are the shared store — label-checker
                                   stamps computed labels into element files; Archivist's weekly
                                   drift-check (Feature 2.1, manual.md line 49) reads those same files
                                   to detect stale entries; label-checker is the upstream that keeps
                                   the labels current

FEEDS        notify-plane       · label-checker exits non-zero (exit 1) on any downgrade; the weekly
                                   Archivist cron (TARGET — not yet wired) is the declared caller that
                                   turns that non-zero into a phone-ping via notify-plane; the signal
                                   path exists in code (label_checker.py:262); the automation that fires
                                   it does not yet

COMPLEMENTS  conformance-lab    · system/hooks/*.sh (shared fire-test target) — conformance-lab
                                   (system/tools/conformance-lab/: bakeoff.py, probes/guard.py,
                                   driver.py, bakeoff_blind_chain.py) also fires hook scripts against
                                   payloads via bash stdin using the same HOOKS_DIR; label-checker runs
                                   manifest-declared probes for map-honesty; conformance-lab runs
                                   adversarial bake-off suites for enforcement-tournament selection;
                                   both read the same hook scripts but neither reads the other's
                                   ground-truth file; neither subsumes the other
```

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)
- **maturity_label:** LIVE·gap
- **check_detail:** "pending label_checker.py"
