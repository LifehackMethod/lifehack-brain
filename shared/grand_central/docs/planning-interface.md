<!-- 4P.1: written as the code it documents landed (4P.4 + 4P.4b engine part, 2026-11-17); every command and
     field checked against the code this session (see tests/test_step4p_interface.py, which re-checks the page's
     JSON shapes against real --json output on every test run) -->
# Planning interface: what a planning skill uses from Grand Central

Contract for planning-weekly / planning-daily (and any desk). Everything goes through `gc` (or the named functions in `store.py`); never raw SQL, never the database file. Add `--json` to get one JSON document on stdout. Errors exit 1 (JSON `{"error": ...}` under `--json`, message on stderr).

**Two rules.**
1. Answers flow back only through the engine's write doors (`gc answer`, `gc decide`, `gc merge` / `gc unmerge`, `gc onboarding answer`; the full list is under "Write commands" below). Each appends to `kg_answers` (the model stays rebuildable) and applies the decision as his fact or link; a queue row is closed where the answer answers one.
2. Nothing here writes to Gmail, Calendar or Tasks. An approved task or calendar entry is written by the harness's existing shared write path; an approved rule or filter is made by the rule machinery from the logged answer. These commands only read, and record the decision.

Always start with `gc fresh` (exit 3 = stale: say so before planning on old data).

## Commands

| command | does | writes? |
|---|---|---|
| `gc proposals [--kind K] [--status open\|answered\|dismissed\|all] [--limit N]` | queue rows, oldest first | no |
| `gc answer ID ANSWER [--by WHO]` | answer one open proposal (`yes`, `no`, or free text) | kg_answers + queue row (the old answer_log is no longer written) |
| `gc answer --subject-kind K --subject NAME --fact KEY --value V --words "his words" --question Q [--said-on D] [--until D]` | one decision (the one door) | kg_answers + his fact/link |
| `gc decide --draft DRAFT.json --decisions DECISIONS.json [--day D] [--desk NAME] [--said-on D]` | a session's decisions on a draft: records them, checks the snapshot, stages the validated weekly picture (below) | kg_answers (yeses only) + the staged picture |
| `gc decide --show [--day D] [--desk NAME]` | the newest staged validated picture with its check result re-run now (the weekly run's receipt, contract §5.7); exit 0 only when valid | no |
| `gc urgent [--limit N]` | open items ranked by computed urgency with overrides (pin up, quiet-until hidden) | no |
| `gc week [--start YYYY-MM-DD]` | digest of `[start, start+7d)`; start defaults to today | no |
| `gc queue` | open queue, human text | no |
| `gc person KEY` / `gc org KEY` / `gc upcoming [--start D] [--days N]` / `gc due` | the PRM pages (people, organizations, events, relation to him) | no |

Existing doors: `gc new LABEL`, `gc who ADDRESS`, `gc thread ID`, `gc fresh`, `gc status`.

## JSON shapes

`gc fresh --json` shape (exit 0 fresh, 3 stale):
```json
{"source": null, "last_success_at": null, "age_min": 0, "newest_message_ms": 0, "newest_message_at": null, "threshold_min": 0, "stale": false, "reason": null}
```

`gc proposals --json` shape: P = `{id, kind, subject_ref, question, proposed_answer, status, created_at, answered_at, answer}`.
```json
{"kind": null, "status": null, "count": 0, "proposals": [{"id": 0, "kind": null, "subject_ref": null, "question": null, "proposed_answer": null, "status": null, "created_at": null, "answered_at": null, "answer": null}]}
```
Kinds written today by `daily.py`: `who-is-this`, `apply-label`, `flag-urgent`. Others written by engine code today: `possible_duplicate` (a suspected duplicate person/organization, store_graph.propose_merge), `picture-q` (synthesize.py's questions), `onboarding-org-type` (held for the onboarding sitting), `confirm-guess` (retire_machine_guesses). Expected as the rig grows: `task`, `calendar`, `decision`, `expiry`, `filter`, `unsubscribe`, `project`. `subject_ref` names the thing asked about, e.g. `item:<id>`, `address:<addr>`, `person:<key>`, `rule:<key>`.

`gc answer ID ANSWER --json` shape:
```json
{"id": 0, "kind": null, "subject_ref": null, "answer": null, "decided_by": null, "accepted": true, "proposed_answer": null, "answer_log_id": null, "answer_id": 0}
```
`accepted` is true for yes/y, false for no/n, null for free text (the skill interprets it). Answering a closed or unknown id exits 1. Answering a `possible_duplicate` proposal with yes also performs the merge (his word recorded, then carried out, in one transaction).

`gc answer --subject-kind K --subject NAME --fact KEY --value V --words W --question Q --json` shape:
```json
{"answer_id": 0, "applied": null, "row_id": null}
```
`applied` is `fact`, `link`, `merge`, `unmerge`, or null (an answer that records no fact). A yes/no/free-text decision: checked against the allowed words (kg_vocab / kg_fact_keys); anything not allowed is refused and nothing is written.

`gc urgent --json` shape (highest urgency first; each item gains an optional `relation`):
```json
{"count": 0, "items": [{"item_id": 0, "source": null, "kind": null, "title": null, "person_address": null, "due_at": null, "status": null, "urgency": 0, "pinned": false, "projects": [null], "relation": {"person": null, "projects": [null]}}]}
```
Urgency is computed from `due_at` (or the earliest due date of the item's projects) and never stored; no date and no pin means no opinion, so the item is absent.

`gc week --json` shape:
```json
{"start": null, "end": null, "as_of": null,
 "counts": {"arrived": {}, "arrived_total": 0, "open_proposals": 0, "due_in_window": 0, "expiry_questions": 0},
 "top_urgent": [{"item_id": 0, "source": null, "kind": null, "title": null, "person_address": null, "due_at": null, "status": null, "urgency": 0, "pinned": false, "projects": [null], "relation": {"person": null, "projects": [null]}}],
 "due_in_window": [{"item_id": 0, "kind": null, "title": null, "due_at": null, "status": null}],
 "open_proposals": {},
 "overdue_reviews": [{"id": 0, "level": null, "subject_id": null, "type": null, "reason": null, "review_by": null}]}
```
`counts.arrived` is a mapping of `"<source>/<kind>"` to a count (its keys are whatever sources arrived that week); `{}` above means "a mapping, keys vary". `overdue_reviews` holds overrides past their `review_by` as of `end`.

`gc new LABEL --json` shape:
```json
{"label": null, "count": 0, "threads": [{"thread_id": null, "newest_ms": 0, "message_ids": [0], "from_addr": null, "from_name": null, "subject": null, "list_unsubscribe_present": false, "label_ids": [null]}]}
```

`gc decide --show --json` shape — the weekly run's receipt (contract §5.7):
```json
{"schema": null, "file": null, "day": null, "desk": null,
 "snapshot": {"snapshot_version": 1, "draft_id": null, "validated_on": null, "status": null, "pending": [null], "decisions": [{"id": null, "decision": null, "answer_ids": [0]}], "draft_digest": null, "digest": null},
 "check": {"errors": []}, "valid": true}
```
`check.errors` is re-computed at read time by `store.check_snapshot` against the current database: a picture edited after validation, or one whose answers left the database, reads back `valid: false` with the errors (exit 1). `snapshot.status` is `validated` when every suggestion was decided, `partial` while some are still `later`.

`gc decide --draft D --decisions C --day D --json` shape (the same snapshot, plus where it was staged):
```json
{"schema": null, "ok": true, "day": null, "desk": null, "staged": null, "md": null, "snapshot": {"snapshot_version": 1, "draft_id": null, "validated_on": null, "status": null, "pending": [null], "decisions": [{"id": null, "decision": null, "answer_ids": [0]}], "draft_digest": null, "digest": null}, "check": {"errors": []}}
```

`gc thread ID --json` prints `{thread_id, messages, context}`; `context` = `{thread_id, items, projects, urgency}` (envelopes + meaning for one thread; `urgency` null when no item has a date).

## `gc decide`: the door for a session's decisions, and the validated weekly picture (4P.4 / 4P.4b)

The **draft of suggestions** (a JSON file, never the database — defined in `store_graph.py`):
```json
{"draft_id": null, "made_on": null,
 "suggestions": [{"id": null, "kind": "fact", "question": null, "subject_kind": null, "subject_name": null,
                  "fact_key": null, "value": null, "condition": null, "true_until": null, "basis": null}]}
```
`kind` is `fact`, `lean` or `rule_item`; a `lean` carries `fact_key: "lean"`; a `rule_item` carries `rule_kind` (`topic`|`exception`) and `target_key` (`<kind>:<name>`). `id` is 1-16 of letters, digits, `_`, `-`; `draft_id` is 1-40 of letters, digits, `.`, `_`, `-`. Every field is validated before anything is written; a draft can never carry an approval (approvals come only through `gc approve`).

His **decisions** (a JSON file): `{suggestion id: {"decision": "yes"|"no"|"later", "words": "his own words"}}`. A yes without his words is refused. Only the yeses are written (through `record_answer`, the one door); noes and laters live in the snapshot and nowhere in the database.

On success the validated weekly picture is staged in the planning desk's `records/context/` — the desk's folder is found through `shared/desk_list.py` (the notes folder's `desks/desk-registry.yaml`); a desk with no registry entry is refused, never guessed — under ONE file name both readers use: **`<day>-<desk>-validated.json`** (the receipt) and **`<day>-<desk>-validated.md`** beside it (readable; the morning read's baseline when validated). Staging is exclusive: a day's picture is staged once; a second `decide` for the same day is refused. If the snapshot fails `check_snapshot` the decisions stay recorded (they were his word) but NOTHING is staged, and the command exits 1.

Errors (exit 1, JSON `{"error": ...}`): a refused decision (no such suggestion id, a yes without words, an already-used draft_id + id pair for different content, a word not in the allowed vocabulary); a failed snapshot check; a day already staged; a desk not in the desk list; no staged picture for `--show`.

## Expiry questions

`store.expiry_questions(now=None, limit=None)` returns `[{item_id, kind, title, person_address, age_days, due_at, reason, question}]`: inbox mail older than 30 days, tasks overdue by 14 days; pinned, quiet and already-asked items skipped. Pure read, never an action: the skill turns one into a queue row (kind `expiry`, `subject_ref` `item:<id>`) if it wants his answer recorded.

## Using it in a session

1. `gc fresh`, then `gc week --json` for the picture, `gc urgent` for the ordering.
2. Read proposals to him by kind; he says yes, no or something else.
3. For each answer run `gc answer ID ...` (`--by` defaults to the owner); for the session's decisions on the week's draft, write his decisions file and run `gc decide`. Then do the follow-through (write the task or event through the harness path; rules/filters follow from the logged answer).
4. Overdue override reviews in `overdue_reviews` are questions too: keep, retire, or change.
5. End the session with `gc decide` (the validated weekly picture) and `gc backup`.

## Write commands (the complete list)

The engine's commands that write: `gc answer` (both forms), `gc merge` / `gc unmerge` (need his words), `gc onboarding answer`, `gc approve` (his yes to one staged filter pair, by sha256), `gc decide` (a session's decisions; `--show` writes nothing), `gc engine` (runs the engine: window, signals, episodes, rank, gaps), `gc migrate --apply` (with `--backup-ok`), `gc backup`, `gc snapshot`, `gc check` (writes the health-light result file). **The planning skill uses only `gc answer`, `gc onboarding answer` (for the onboarding sheet), `gc decide` and `gc backup`.** Nothing writes to Gmail, calendar or tasks.

## Relation to him (step 3.5)

`gc who --json` gains an optional top-level `relation`; each item in `gc urgent --json` and in `gc week --json` `top_urgent` gains an optional `relation: {person, projects: [R]}`. R = `{key, kind, name, empty, text, relationship, direct, level, organizations, projects, events, events_total}` (each of `relationship`, `level` present only when the database says it); `direct` is a list of `{kind, direction, role}`; empty R means nothing certain is known (his word or code-certain rows only; never a guess). Computed on demand by `store_relation.relation_to_me`, stored nowhere. Every old key is unchanged; the field is omitted if the database is too old to compute it.

## Known behaviour (independent verification, 2026-11-17)

- `gc person`, `gc org` and `gc thread` print a valid JSON body with `"found": false` AND exit 1 for a key that is not found. A skill should read the body, not the exit code alone, to tell "not found" from a failure.
- The morning read prefers the newest **validated** weekly picture over any later daily draft, with no age limit (plan 4P.4b). If weekly sessions lapse, the baseline keeps starting from the last validated picture; the day's draft still sits beside it. An age signal is a 4P.3 question, not built yet.
- `gc decide` refuses a day that is already staged BEFORE recording anything: a refused call writes nothing to the database.
