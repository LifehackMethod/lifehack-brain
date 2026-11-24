#!/bin/sh
# Registered 2026-11-24 through system/register/register.jsonl + generate.py (run pickup, spec G6).
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a talk step's move is the person's decision (spec run-pickup, id run-pickup-spec-2026-11-23,
#      G3 + invariant 3). The mover runs the step runner from the person's typed /next or /back;
#      this guard closes the plain side door: the AI running stage_runner.py's person-turn, or
#      advance/back on a talk step, out of a Bash call. Friction, not perfect enforcement: a
#      disguised command can get past it — the runner's person-turn rule is the second check, and a
#      forged record shows as damage or an unlogged person line (verify reports it).
# GUARDS: PreToolUse on Bash. Refuses (exit 2, deny on stderr) when the parsed command RUNS
#      stage_runner.py with subcommand person-turn, or advance/back while the run's current step is
#      a talk step (mode read read-only via run_pickup.py mode --workdir; the workdir comes from the
#      command's --workdir, else the Bash call's cwd). back always needs the person. Every runner
#      call in the command is checked (status && advance), global options are skipped before the
#      subcommand, and a name built from fragments or a glob counts as the runner. Also refused:
#      the runner wrapped in bash -c / sh -c / eval / xargs, imported in python -c, or held in a
#      variable. Allowed: advance on an alone step, resume, abandon, snooze, recover, check, start,
#      status, verify, statusline — and any command that merely MENTIONS the file (grep, cat,
#      git commit -m, echo): a preceding read-ish command, or a quoted message that only names the
#      file, is a mention, not a run.
# REDIRECT: "BLOCKED: only the person moves a talk step. WHY: the step order is the person's.
#      REDIRECT: ask them to type /next or /back. RULE: system/parts/stage_runner.py header + this spec."
# SIGNPOST: the mover is system/hooks/run_step_hook.sh (UserPromptSubmit); the runner contract is
#      system/parts/stage_runner.py header + RUNNER.md; the spec is the run-pickup spec (G3).
# UPDATED: 2026-11-23 (Phase 4c fix pass: every runner call checked, options
#      skipped before the subcommand, built/globbed names counted as the runner,
#      bash -c / sh -c / eval / xargs / python -c and variable-held paths refused, and a
#      `python3 -m stage_runner` module run counted as the runner (phase 4e),
#      blank verdict printf dropped).
# FAIL_POSTURE: degrade-safe (unparseable stdin, a command that does not parse as shell tokens, or
#      a missing payload field: allow, and say so on stderr). The only exit-2 paths are the
#      deliberate denies. A mode that cannot be read for a REAL advance/back is a deny with the
#      reason ("can't tell"), per the spec — not a fail-open.
# NAMED LIMIT: this is friction for a plain hand, not a wall. A command built inside bash -c /
#      sh -c / eval / xargs / python -c, or a runner name assembled from fragments or a glob, is
#      REFUSED on sight — but a disguised command outside those shapes can still get past; the
#      runner's person-turn rule is the second check, and a forged record shows as damage or an
#      unlogged person line (verify reports it).
# ─────────────────────────────────────────────────────────────────────────────
payload=`cat`
case "$payload" in
  *"stage_r"*) ;;
  *) exit 0 ;;  # sh prefilter: nothing here can even name the runner (catches built names)
esac
DIR=`CDPATH= cd -- "$(dirname -- "$0")" && pwd`
python3 - "$DIR" "$payload" <<'PY'
import json, os, shlex, subprocess, sys
hooks, raw = sys.argv[1], sys.argv[2]
parts = os.path.abspath(os.path.join(hooks, "..", "parts"))
DENY = ("BLOCKED: only the person moves a talk step. WHY: %s The step order is the person's. "
        "REDIRECT: ask them to type /next or /back. "
        "RULE: system/parts/stage_runner.py header + this spec.")
def deny(why=None):
    sys.stderr.write((DENY % (why or "the step order is the person's.")) + "\n")
    sys.exit(2)
try:
    j = json.loads(raw)
except Exception as e:
    sys.stderr.write("guard_run_commands: unparseable stdin (%r); allowing\n" % e)
    sys.exit(0)  # degrade-safe: a payload we cannot read is not a command we can judge
cmd = None
if isinstance(j, dict):
    ti = j.get("tool_input")
    if isinstance(ti, dict):
        cmd = ti.get("command")
if not isinstance(cmd, str):
    sys.exit(0)
try:
    toks = shlex.split(cmd)
except ValueError as e:
    sys.stderr.write("guard_run_commands: command does not tokenize (%r); allowing\n" % e)
    sys.exit(0)
PT = "person-" + "turn"   # assembled, so this file never quotes its own trigger
READISH = {"grep", "cat", "git", "echo", "ls", "head", "tail", "less", "sed", "awk", "rg", "man",
           "find", "wc", "diff", "file", "stat", "tee", "sort", "uniq", "chmod", "touch", "nano",
           "vim", "code", "open", "realpath", "basename", "dirname", "readlink", "md5", "shasum"}
# wrappers first: bash -c / sh -c / python -c / eval / xargs hide their payload from this
# guard, so ANY token naming the runner inside a wrapper payload is a run.
wrapzones = set()
for i, t in enumerate(toks):
    if t in ("bash", "sh", "python", "python3") and i + 1 < len(toks) and toks[i + 1] == "-c":
        wrapzones.update(range(i + 2, len(toks)))
    elif t in ("eval", "xargs"):
        wrapzones.update(range(i + 1, len(toks)))
if any("stage_r" in t and i in wrapzones for i, t in enumerate(toks)):
    deny("the command wraps or hands the runner to bash -c / sh -c / eval / xargs / python -c, "
         "where this guard cannot see it.")
# word-split FIRST: every token that names the runner -- exactly, globbed, or fragment-built --
# is a runner call, unless it is a mention (a read-ish command before it, or a quoted message
# that only names the file). A quoted message that merely names the file (a commit message, a
# grep pattern) never becomes a run: its text sits inside one token, so it is not the runner's
# own token.
runners = []
for i, t in enumerate(toks):
    if "stage_r" not in t:
        continue
    if i and toks[i - 1].strip("/") in READISH:
        continue  # a mention (grep/cat/... of the file), not a run
    tt = t.rstrip(";")  # a trailing command separator rides on the token
    if tt.endswith("stage_runner.py") or tt.rsplit("/", 1)[-1] == "stage_runner.py" \
            or tt.rsplit("/", 1)[-1] == "stage_runner":
        runners.append(i) # the bare module name too: `python3 -m stage_runner` IS the runner
    elif "*" in tt or "$" in tt or "?" in tt:
        runners.append(i)  # a built or globbed name: friction says treat it as the runner
for t in toks:
    if "import stage_runner" in t:
        deny("the command imports the runner in python, which would write the record directly.")
for i in runners:
    if "=" in toks[i] and toks[i].rstrip(";").endswith("stage_runner.py"):
        deny("the runner's path is held in a variable, which this guard cannot follow.")
for i in runners:
    rest = toks[i + 1:]
    if PT in rest:
        deny("person-turn writes a person line, and only the mover (the person's typed /next "
             "or /back) may.")
    # skip global options before taking the subcommand
    k, sub = 0, ""
    while k < len(rest):
        t = rest[k]
        if t == "--workdir" and k + 1 < len(rest):
            k += 2
            continue
        if t.startswith("--workdir="):
            k += 1
            continue
        sub = t
        break
    if sub not in ("advance", "back"):
        continue  # status, check, resume, abandon, snooze, recover, verify, start, statusline
    wd = None
    for kk, t2 in enumerate(rest):
        if t2 == "--workdir" and kk + 1 < len(rest):
            wd = rest[kk + 1]
        elif t2.startswith("--workdir="):
            wd = t2.split("=", 1)[1]
    if not wd:
        c = j.get("cwd") if isinstance(j, dict) else None
        wd = c if isinstance(c, str) and c else os.getcwd()
    try:
        p = subprocess.run([sys.executable, os.path.join(parts, "run_pickup.py"), "mode",
                            "--workdir", wd], capture_output=True, text=True, timeout=30)
        mode = p.stdout.strip()
    except Exception as e:
        sys.stderr.write("guard_run_commands: mode lookup failed (%r)\n" % e)
        mode = ""
    if mode == "alone" and sub == "advance":
        continue  # an alone step advances on a verified pass; that is the AI's own work
    if mode not in ("talk", "alone"):
        deny("the current step's mode could not be read for %s (run_pickup.py mode said %r)."
             % (wd, mode or "nothing"))
    if sub == "back":
        deny("back re-opens a step, and back always needs the person.")
    deny("the current step is a talk step.")
sys.exit(0)
PY
rc=$?
if [ "$rc" -eq 2 ]; then
  exit 2            # the deny message went to stderr from python directly
fi
if [ "$rc" -ne 0 ]; then
  # degrade-safe: an internal failure of the guard itself never blocks a Bash call
  printf '%s the guard could not run (python failed, exit %s); allowing this call\n' \
    '[RUN GUARD — harness-injected, not user input]' "$rc" >&2
fi
exit 0
