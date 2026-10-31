# Canary SPEC: the contract TR1.2–TR1.5 build against

The canary is twelve deliberately boring steps. Nothing in it is a judgment call; every byte of every correct
output can be recomputed by code from **the card plus one integer seed**. `expected.py` is this spec written as
code. If this file and `expected.py` ever disagree, `expected.py` wins, and the disagreement is a bug to fix
here.

## 1. Files

| file | role |
|---|---|
| `card.txt` | 12 step rows, `id \| kind \| what \| check`, in the October rig format, plus `#@` directive lines |
| `prompts/sN.md` | 2 lines each, for the 8 `ai` steps and the 2 `human` steps. Code steps have no prompt |
| `code/s1.py`, `code/s7.py` | the two code steps |
| `code/human.py` | writes a human step's file once the runner has the answer |
| `expected.py` | reference implementation and CLI (see its docstring) |

Kinds: `s1 code · s2 ai · s3 ai · s4 human · s5 ai · s6 ai · s7 code · s8 ai · s9 human · s10 ai · s11 ai · s12 ai`
(8 ai, 2 code, 2 human).

## 2. `step-N.json`: the exact schema

The file lives at `$RUN_DIR/step-N.json`. It is one JSON object, and its keys must be exactly these, no more
and no fewer:

```
{"step": N, "token": "<token_N>", "value": <int 0..999>, "facts": [<5 strings>]}            # ai, code
{"step": N, "token": "<token_N>", "value": <int 0..999>, "facts": [<5 strings>], "answer": "yes"|"no"}   # human only
```

- `step` is an int equal to N.
- `facts` is a list in the planted order, each string compared exactly.
- Correctness compares the **parsed** JSON: key order and whitespace do not matter, but a missing key, an
  extra key, a wrong type or a wrong value all fail. The canonical byte form is `expected.dumps()`, which is
  compact, uses this key order, and ends with a newline.
- No repair is done. A reply wrapped in code fences or prose is NOT valid JSON, so it fails. Only
  leading/trailing whitespace may be stripped.

## 3. Derivations from the seed

All derivations use `H(parts…) = sha256("canary|" + "|".join(parts)).hexdigest()`.

| thing | formula |
|---|---|
| seed (default) | `int(H("run", run_id)[:8], 16) % 1_000_000`. `--seed S` overrides it and must then be recorded |
| `token_N` | `"T%02d-" % N + H(seed, "token", N)[:8]`, e.g. `T05-26e0b647` |
| `value_1` | `int(H(seed, "value")[:8], 16) % 1000` |
| `value_N`, N≥2 | **`(value_{N-1} * 3 + N) mod 1000`**. This holds for every kind, human steps included |
| facts | 5 `"Name=NNN"` strings. Names are a seeded Fisher–Yates shuffle of `NAMES` (16 made-up surnames) with swap index `int(H(seed,"shuffle",i)[:8],16) % (i+1)`, taking the first 5. Numbers are `100 + int(H(seed,"fact",k)[:8],16) % 900` for k = 0..4 |

The facts are planted at s1 and copied verbatim by s2–s12. Dropping, reordering or editing a fact makes the
step `lost`.

**The token invariant:** token_N reaches the world through step N's own channel only, and no file in `$RUN_DIR`
contains token_N before step N has run.

- **ai**: `prompts/sN.md` carries the placeholder `{{TOKEN}}`. The runner renders `{{TOKEN}}` → token_N and
  `{{RUN_DIR}}` → the absolute run dir, with exactly the logic of `expected.render()`. The token is never
  written anywhere before the call.
- **code**: the script computes token_N from `CANARY_SEED`. For a code step, the script plays the part of the
  prompt.
- **human**: `code/human.py` computes token_N from `CANARY_SEED`. The human never sees it.

## 4. Steps, by kind

- **ai (s2 s3 s5 s6 s8 s10 s11 s12)**: the model has `--allowedTools Read` only, so **it cannot write files.
  Its reply IS the step file.** The runner takes the `result` field of the `claude -p --output-format json`
  output and writes it unmodified (whitespace-trimmed) to `step-N.json` through a temp file and a rename. It
  keeps the raw JSON as `sN.raw.json` for cost and turn counts. Each prompt reads exactly one file,
  `{{RUN_DIR}}/step-(N-1).json`.
- **code (s1, s7)**: `CANARY_SEED=S python3 canary/code/sN.py "$RUN_DIR"`. The step is deterministic and
  idempotent (temp file then rename), so a re-run after a kill gives a byte-identical file.
- **human (s4, s9)**: the first time the runner reaches the step it records `waiting` and exits 70. On a re-run
  with `--answer sN=<a>` it writes `$RUN_DIR/sN.answer`, then runs
  `CANARY_SEED=S python3 canary/code/human.py "$RUN_DIR" N <a>`, then the check.
  **Answer encoding:** `<a>` must be exactly `yes` or `no`, lowercase, with no whitespace. Anything else
  makes `human.py` exit 3 and write nothing (off-menu, F-M3). `"no"` is written to `step-N.json` as
  `"answer":"no"` and is a legitimate halt. The human check fails on `no`, and the run must stop there. A
  correct run after `sN=no` therefore has exactly steps 1..N, and any later step file is a fault.

## 5. Card directives (do not break the row regex)

Lines that start with `#@ key: v v …` are metadata. The October `run.sh` skips every `#` line, so they never
count as a step.

- `#@ chatty: s3 s6 s10` lists the ai steps the persona controller (TR3.1) drives turn by turn. Every other ai
  step stays one-shot.
- `#@ human-menu: yes no` is the closed answer menu.

`expected.load_card()` returns `(steps, meta)`, with meta for example `{"chatty": ["s3","s6","s10"], ...}`.

## 6. The check column (TR1.3 must create these)

`bash checks/{ai,code,human}.sh "$RUN_DIR" N`, with paths relative to the rig root and `CANARY_SEED` in the
env. Each check compares the parsed `step-N.json` to the `expected` record for (seed, N) on **content**:
token, value and facts, plus answer for human steps. A human check also fails when the answer is `no`. A
check that cannot read its inputs exits 2 and prints `CANNOT-READ`.

## 7. Using `expected.py`

```
expected.py --seed S --answers s4=yes,s9=yes --out DIR   # the oracle's answer key (12 files; stops at a "no")
expected.py next --step N --prev step-(N-1).json --token T [--answer yes|no]   # a good fake's reply
expected.py render --step N --run-dir D --seed S        # the runner's prompt render
expected.py seed --run-id R
expected.py --selftest                                   # -> SELFTEST expected OK
```

`next` needs no seed. It gets exactly what a real model gets: the previous file plus the token, which comes
from the rendered prompt via the regex `"token":"([^"]+)"`. A fake in `good` mode built on `next` therefore
fails exactly when its input was faulted, which is what the injector needs.
Imports: `sys.path.insert(0, "<rig>/canary"); import expected`. Functions: `token, value1, next_value, facts,
record1, record_from_prev, expected_run, load_card, kinds, render, dumps, write_step, seed_for_run,
parse_answers`.

## 8. Hygiene the runner owns (TR1.4)

- `RUN_DIR` is absolute and sits under `~/lifehack-scratch/skill-tester-rig/` (ruling 6), never under `out/`
  inside the rig.
- Run `claude` with its cwd **outside the rig folder**, ideally `$RUN_DIR`. Keep the seed out of `$RUN_DIR`
  (put it in the record or a meta file one level up). A model that has Read access and sits in the rig can
  open `expected.py` and compute any token, which makes fabrication possible.
- Do not persist rendered prompts in `$RUN_DIR` before their step runs. That would break the token invariant.
