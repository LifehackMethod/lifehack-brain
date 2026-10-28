> Design contract conform.py was built to (rule ids, scope, declarations, output).
> If this differs from system/tools/conform-rules.md or conform.py, those two are the source of truth.

# conform — shared design contract (build-skill plan, Phase 1)

Written by the build window so BS1.1 / BS1.2 / BS1.3 agree. Not a deliverable.

## Rule ids (fixed — 11 lines)
| id | scope | check | rule |
|---|---|---|---|
| ALW-1 | always | code | no silenced errors: `\|\| true`, `2>/dev/null`, `>/dev/null 2>&1` on a fetch/send/write command (curl, wget, gws, gog, gh, git push, osascript mail, python -c requests…) |
| ALW-2 | always | code | exit 0 is never the only proof: a marker/tick/state file advanced on rc alone (e.g. `if cmd; then touch marker`, `cmd && echo ok > state`, `[ $? -eq 0 ] && date > last_run`) with no content check between |
| ALW-3 | always | code | checks test content: a check/verify whose only test is `test -s/-f/-e`, `[ -s ]`, `ls`, `wc -l`, or "non-empty" |
| ALW-4 | always | code | AI→code handoff is a contract: every ai step's output is parsed by a check with a FIXED shape (exact field / pick from list / number / exact yes). Fail when an ai step's check is missing, or only tests non-empty / presence |
| ORD-1 | ordered | code | a card exists (`*.card` with `id \| kind \| action \| check` lines) |
| ORD-2 | ordered | code | only the runner writes the record — no ai prompt or ai step action names the record path (`record.tsv` or the declared record) |
| ORD-3 | ordered | code | the runner refuses a truncated record (runner contains a truncation/last-line-complete guard) |
| ORD-4 | ordered | code | ai steps run read-only: every `claude -p` call in the runner carries `--allowedTools Read` |
| ORD-5 | ordered | code | model pinned per ai step (`--model <x>` on every `claude -p`) AND the runner records `ccv=` per run |
| ORD-6 | ordered | judge | side-effect steps are safe to run twice |
| ORD-7 | ordered | judge | order genuinely matters — SOP v2 card-or-not rule |

## Scope classification (an artifact = a folder, or a single file)
- **not-applicable** — no executable code: no `*.sh *.py *.js *.ts *.card`, no shebang file. Reason printed: `no executable code`. Also N/A if declared `scope: not-applicable because <reason>`.
- **ordered** — has code AND (a `*.card` file, OR a runner that writes a record — `record.tsv`/`--record`, OR declared `scope: ordered`).
- **always** — has code otherwise. Declared `scope: always because …` is honoured.
- ⛔ A declared scope that is LOWER than the evidence (declared always, but a card exists) → the evidence wins, and a `FAIL SCOPE` line is printed.

## Declarations
Read from `conform.decl` in the artifact root, and/or from a plan file given with `--plan <file>` (lines anywhere in the plan). Grammar, one per line, leading `- ` / backticks tolerated:
- `scope: <always|ordered|not-applicable> because <reason>`
- `exception: <RULE-ID> because <reason>` — reason must be non-empty, else invalid.
A FAIL finding whose rule id has a valid exception → printed as `EXCEPTION`. An exception for a rule that never fired is listed too (`EXCEPTION <id> - unused`), not an error.
"bad-undeclared-exception" = a file that carries an *inline* waiver comment (e.g. `# conform: allow ALW-1`) with no declaration → still FAIL ALW-1 (inline waivers are not declarations).

## Output (conform.py)
One line per finding: `FAIL|PASS|N/A|EXCEPTION|JUDGE <rule-id> <file:line> <why>`
Final line: `verdict=<PASS|FAIL|N/A> scope=<scope> examined=<n> fail=<n> exceptions=<n> judge=<n>`
Exit: 0 PASS · 1 FAIL · 3 N/A · 4 could-not-read. Never 0 on error.
JUDGE lines (ORD-6, ORD-7) are listed for a reviewer whenever scope=ordered; they never make the verdict PASS on their own and never FAIL it.

## Fixtures (`~/lifehack-v2/system/tools/fixtures/conform/`)
10 bad: `bad-ALW-1 … bad-ALW-4`, `bad-ORD-1 … bad-ORD-5`, `bad-undeclared-exception`. Each breaks exactly ONE rule and is otherwise clean.
3 good/na: `good-ordered` (card + runner that satisfies all ORD code rules + ALW rules), `good-declared-exception` (breaks ALW-1 once, `conform.decl` declares it) , `na-document` (only a .md).
`expected.tsv`: `fixture<TAB>verdict<TAB>rule` — e.g. `bad-ALW-1	FAIL	ALW-1`, `good-ordered	PASS	-`, `good-declared-exception	PASS	ALW-1`, `na-document	N/A	-`.
check.log line: `<fixture> EXPECTED <verdict>/<rule> GOT <verdict>/<rules-failed> MATCH|MISMATCH`.
