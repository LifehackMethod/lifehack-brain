# conform-rules — skills-SOP-v2 conformance rules as data

Read by `conform.py`. One line per rule: `id | scope | check | rule | SOP v2 source`. Source = skill-building-sop-v2 draft (line numbers of 2026-10-28).
This is ONE layer, not perfect enforcement: code rules catch the common shapes; judge rules are listed for a human reviewer and never pass or fail a verdict alone.
Scope: ALWAYS rules apply to anything that runs code. ORDERED rules apply on top when step order must hold (a card, or a runner that writes a record).
NOT APPLICABLE is said out loud with a reason (documents, research, design, one-offs: "no executable code"). A silent pass is a fail.
Exceptions are declared, one per line, in `conform.decl` or the plan: `exception: <RULE-ID> because <reason>`.
An undeclared exception (e.g. an inline "allow" comment) is a fail. Every declared exception is listed in the report.

ALW-1 | always | code: on a fetch/send/write command (curl, wget, gws, gog, gh, git push, osascript mail, python requests) flag `|| true`, `2>/dev/null`, `>/dev/null 2>&1` | never silence an external command's errors; a failed fetch must not read as "nothing new" | SOP v2 PART 0 "New rules" l.278 (LAW 1)
ALW-2 | always | code: flag a marker/state file advanced on rc alone (`if cmd; then touch marker`, `cmd && echo ok > state`, `[ $? -eq 0 ] && date > last_run`) with no content check between | exit 0 is never the only proof of work; a marker advances only on rc 0 AND a passing content check | SOP v2 PART 0 "New rules" l.277 and audit l.289 (LAW 3)
ALW-3 | always | code: flag a check/verify whose only test is `test -s/-f/-e`, `[ -s ]`, `ls`, `wc -l`, or "non-empty" | every check tests CONTENT, never presence; "non-empty" is not a check | SOP v2 PART 0 "New rules" l.274 (LAW 3, l.870; §V.4b)
ALW-4 | always | code: every ai step's output is parsed by a check with a FIXED shape (exact field, pick from list, number, exact yes); fail if the check is missing or only tests non-empty/presence | the AI-to-code handoff is a contract: fixed shape, code checks shape and content, loud fail on anything else | SOP v2 PART 0 "The AI-to-code handoff is a contract" l.189
ORD-1 | ordered | code: a `*.card` file exists with `id | kind | action | check` lines | an ordered skill has a card: ordered steps, each of a kind (code/ai/human), each with a check | SOP v2 PART 0 "The default shape" l.214 (card, runner, record, scorer)
ORD-2 | ordered | code: no ai prompt or ai step action names the record path (`record.tsv` or the declared record) | only the runner writes the record; the AI never does | SOP v2 LAW 3 l.863; PART 0 "New rules" l.268 (§V.9)
ORD-3 | ordered | code: runner contains a truncation / last-line-complete guard before resume | the runner detects a truncated or malformed record before resuming and fails loudly | SOP v2 PART 0 "New rules" l.276 (LAW 1)
ORD-4 | ordered | code: every `claude -p` call in the runner carries `--allowedTools Read` | ai steps run read-only; only the runner writes outputs and the record | SOP v2 PART 0 audit additions l.291
ORD-5 | ordered | code: `--model <x>` on every `claude -p` AND the runner writes `ccv=` per run | model pinned per ai step and the claude version recorded per run | SOP v2 PART 0 audit additions l.290 (ccv) and l.294 (model pin)
ORD-6 | ordered | judge | every side-effect step is safe to run twice (idempotent), or records what it did BEFORE acting so a resume can skip it | SOP v2 PART 0 "New rules" l.275 (LAW 1)
ORD-7 | ordered | judge | card only if order must hold AND (losing progress costs real time/money, OR a human pause mid-run, OR it spans sessions, OR more than one ai step); a short rerun-from-scratch job gets per-step checks and loud failure, not a card; ALWAYS rules apply either way | SOP v2 PART 0 "When NOT to use a card", decision rule l.313
