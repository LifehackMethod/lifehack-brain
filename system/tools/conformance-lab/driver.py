#!/usr/bin/env python3
"""
conformance-lab/driver.py — Conformance Laboratory dispatch driver.

Parses the rule registry (a markdown pipe-table), hands each rule to the probe registered for its
category, records the verdict in the world-model store, and prints a coverage headline.

WHAT THE LAB IS FOR, in one line: to tell the difference between a rule that is ENFORCED and a rule
that is merely WRITTEN DOWN. Prose asks nicely; a guard refuses. This driver is what proves which
one you have, per rule, by firing the forbidden thing and watching what happens.

Modes:
  --rule <id>            Run one rule by rule-id (the tight loop)
  --sweep                Run every rule in the registry
  --category <name>      Run one category (letter A-H, or its full name)
  --level <L1|L2|L3|L4>  Run rules at one importance level
  --selftest             ⭐ THE NEGATIVE CONTROL — see below. Run this before trusting a green sweep.

Exit codes:
  0 = clean (no red findings)   1 = red findings present   2 = tool error

────────────────────────────────────────────────────────────────────────────────────────────────
⭐ --selftest — A LAB NEVER SEEN CATCHING SOMETHING IS NOT A LAB
────────────────────────────────────────────────────────────────────────────────────────────────
A green sweep has two possible causes: the guards work, or the lab cannot tell the difference. Those
look identical from the outside, and only one of them is worth anything.

`--selftest` distinguishes them. It builds a throwaway directory of INERT guards — one stub per hook
named in the registry, each of them nothing but `exit 0` — points the probe at that directory
instead of `system/hooks/`, and re-runs. Every rule must come back `theater` (the mechanism is
present and does not fire). If even one comes back `fires`, the lab is rubber-stamping and its
green sweep means nothing; the selftest exits 1 and says which rule lied.

It never touches `system/hooks/`. The stubs live in a temp directory that is deleted on the way out,
and the redirect happens through `CONFORMANCE_LAB_HOOKS_DIR`, which `probes/guard.py` reads per call.
The world-model store is NOT written during a selftest — it is a test of the instrument, not a
measurement of the system.

────────────────────────────────────────────────────────────────────────────────────────────────
WHAT IS BUILT HERE, AND WHAT IS NOT (rebuilt T9.8c, 2026-08-15)
────────────────────────────────────────────────────────────────────────────────────────────────
Built: the driver, the registry, and ONE real probe — `probes/guard.py`, category C, which fires
paired forbidden/allowed payloads at this repo's actual hooks.

NOT built: the static-parse (A/B), session (D/E/F), judgment (G) and completeness (H) probes. This
is a deliberate stopping point, not an oversight — a small lab that genuinely runs beats a large one
that does not, and the session probes in particular each cost real LLM runs and need scenarios
authored one at a time against this repo's own skills.

An unregistered category does NOT fail loudly and it does NOT quietly pass: it falls through to
`_stub_probe`, which returns `unscored` ("a probe ran, there was nothing to score"). So adding an
A-category row to the registry tomorrow gets you an honest blank, never a fabricated green. The
`unscored` / `unvisited` distinction is load-bearing and the two words are deliberately not shared:
`unscored` means the row was visited and had no scorer, `unvisited` means the row was never
dispatched at all.

────────────────────────────────────────────────────────────────────────────────────────────────
PROBE INTERFACE (for probe-builders)
────────────────────────────────────────────────────────────────────────────────────────────────
    def probe(rule: dict, ctx: dict) -> dict:
        # rule: one parsed registry row (every column as a string value)
        # ctx:  run context (reserved; currently {})
        # returns {"verdict": str, "evidence": str}   verdict ∈ VALID_VERDICTS
Register it in PROBES, keyed by category letter.

RED FINDING — a row is red if:
    (struct_judg == "structural" AND mechanism == "none" AND test_binding in ("", "∅"))
    OR verdict in {"dark", "theater", "error"}

House style: stdlib-only · fail-closed exit discipline · no path is ever a literal.
"""

import sys
import os
import re
import json
import shutil
import tempfile
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# probes -> conformance-lab -> tools -> system -> <clone root>
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
sys.path.insert(0, os.path.join(_REPO, "shared"))

# ---------------------------------------------------------------------------
# Paths — resolved, never typed
# ---------------------------------------------------------------------------
#
# ⛔ THE DONOR'S VERSION HARDCODED BOTH OF THESE as absolute paths into one person's cloud-drive
# mount, complete with their email address in the folder name. Neither literal survives the port.
# The split below is deliberate and is the answer to "is the registry code or is it data?":
#
#   REGISTRY   = part of the PRODUCT. It says which rules this system claims to enforce, and it
#                ships with the code, versioned alongside the guards it describes. In-repo.
#   WORLD MODEL = a RUN RESULT. Verdicts, timestamps, per-rule history, the deltas between runs.
#                That is the reader's own operating record, so it lives in the reader's own notes
#                root, resolved through `shared/brain_root.py` like every other store here.
#
# Both accept an env override so a trial run can point at throwaway copies without polluting either.

REGISTRY_PATH = os.environ.get("CONFORMANCE_LAB_REGISTRY") or os.path.join(
    _HERE, "rule-registry.md"
)


def _world_model_path():
    """Where run verdicts are persisted. None if the reader has no notes root configured yet."""
    override = os.environ.get("CONFORMANCE_LAB_WORLD_MODEL")
    if override:
        return override
    try:
        import brain_root
        _src, root = brain_root.resolve_brain_root()
    except Exception:
        root = None
    if not root:
        # NOT-SET is a real outcome, not an error to paper over. The lab still RUNS and still
        # prints every verdict — refusing to test the guards because a notes folder is unconfigured
        # would be the wrong failure. It just has nowhere durable to put the history, and says so.
        return None
    return os.path.join(root, "state", "conformance-lab", "world-model.json")


WORLD_MODEL_PATH = _world_model_path()

# ---------------------------------------------------------------------------
# Verdict vocabulary
# ---------------------------------------------------------------------------
#
#   unscored  — a probe RAN and produced no score (no probe for this category, or no scenario
#               authored for this rule-id). The row WAS visited.
#   unvisited — a COVERAGE term only: a rule the driver never dispatched this run. Never returned
#               by a probe. (Also the registry's seed value before a first run.)
#   parked    — an HONEST, documented non-test: the rule IS enforced by a live guard, but the guard
#               cannot be isolation-probed (it needs live external state, or the install has not
#               been configured far enough for a valid positive case). NOT a red finding and NOT a
#               forced green — it counts against the denominator until a fixture makes it testable.
VALID_VERDICTS = {
    "fires", "dark", "prose-wish", "theater", "error", "unscored", "unvisited", "parked",
}
RED_VERDICTS = {"dark", "theater", "error"}

# ---------------------------------------------------------------------------
# Category letter <-> full name
# ---------------------------------------------------------------------------

CATEGORY_NAMES = {
    "A": "static-parse-skill-file",
    "B": "static-parse-bundle",
    "C": "guard-provoke-assert-blocked",
    "D": "run-fresh-session-read-artefact",
    "E": "multi-turn-cross-turn-state",
    "F": "provoke-and-assert-guard-behavior",
    "G": "compound-or-judgment",
    "H": "set-diff-completeness",
}
CATEGORY_LETTERS = {v: k for k, v in CATEGORY_NAMES.items()}

# ---------------------------------------------------------------------------
# Probe registry
# ---------------------------------------------------------------------------


def _stub_probe(rule, ctx):
    """Fallback for any category with no probe built. Returns `unscored` — never a pass.

    This is the honest-blank path described in the header. It exists so that a registry row in an
    unbuilt category produces a visible gap in the coverage headline instead of silently inflating
    the enforced count.
    """
    cat = rule.get("category", "").strip()
    return {
        "verdict": "unscored",
        "evidence": f"no probe built for category {cat!r} — see driver.py header",
    }


def _load_probe(module_name, func_name):
    """Import a probe callable. On failure return a stub that reports `error` with the reason.

    An import failure IS a red finding: the registry says a category is covered and the code that
    covers it will not load. That must be loud, not silently downgraded to `unscored`.
    """
    try:
        import importlib
        mod = importlib.import_module(module_name)
        return getattr(mod, func_name)
    except Exception as exc:
        def _import_fail_stub(rule, ctx, _exc=exc):
            return {"verdict": "error", "evidence": f"probe import failed: {_exc}"}
        return _import_fail_stub


_probe_guard = _load_probe("probes.guard", "probe")

# ⚠ REGISTER A CATEGORY ONLY WHEN ITS PROBE ACTUALLY EXISTS. Every unregistered letter falls
# through to `_stub_probe` (an honest `unscored`). Mapping a letter to a probe that is not built —
# or deleting a mapping that is — is how a lab starts lying about its own coverage.
PROBES = {
    "C": _probe_guard,   # guard-provoke-assert-blocked  ->  probes/guard.py
    # "A"/"B": static.py       — NOT BUILT
    # "D"/"E"/"F": session.py  — NOT BUILT (each costs real LLM runs; scenarios authored one at a time)
    # "G": parked.py           — NOT BUILT
    # "H": completeness.py     — NOT BUILT
}

# ---------------------------------------------------------------------------
# Registry parser
# ---------------------------------------------------------------------------

# Column order, as written in rule-registry.md.
COL_NAMES = [
    "rule_id", "ref", "claim", "category", "outlier",
    "struct_judg", "mechanism", "subject", "sentinel",
    "session", "test_binding", "last_verdict", "learned_note",
    "verified_at", "importance",
]


def _is_separator_row(cells):
    """True if the row is a |---|---| separator (every non-blank cell is dashes/colons/spaces)."""
    return all(re.match(r'^[-: ]+$', c) for c in cells if c.strip())


def _split_pipe_row(line):
    r"""Split a pipe-delimited table row into stripped cell values, honouring `\|` escapes.

    ⚠ THE ESCAPE HANDLING IS NOT PEDANTRY — it was a live defect. A naive `.split('|')` breaks on
    any cell containing a literal pipe, which in markdown is written `\|`. The first run of this
    driver hit exactly that: a rule whose learned-note quoted a sed expression using `|` as its
    delimiter got split into two extra columns, and every field after it shifted one place left —
    so that rule silently reported the wrong IMPORTANCE. Nothing errored. A registry parser that
    quietly mis-columns a row poisons every verdict downstream of it, so it splits properly.
    """
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|') and not line.endswith('\\|'):
        line = line[:-1]

    cells, buf, i = [], [], 0
    while i < len(line):
        ch = line[i]
        if ch == '\\' and i + 1 < len(line) and line[i + 1] == '|':
            buf.append('|')      # a literal pipe inside a cell
            i += 2
            continue
        if ch == '|':
            cells.append(''.join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append(''.join(buf).strip())
    return cells


def parse_registry(path):
    """
    Parse the markdown pipe-table registry. Returns (rules: list[dict], error: str|None).

    Skips separator rows, header rows, prose, and the categories summary table. A row is a rule
    iff its first cell starts with `SOP-` or `GUARD-` — GUARD-* rows are safety rails rather than
    SOP clauses, and they are legitimately not §-numbered.
    """
    if not os.path.isfile(path):
        return None, f"registry not found: {path}"

    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        return None, f"cannot read registry: {e}"

    rules = []
    seen = set()
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        cells = _split_pipe_row(stripped)
        if not cells or _is_separator_row(cells):
            continue
        if not (cells[0].startswith("SOP-") or cells[0].startswith("GUARD-")):
            continue
        while len(cells) < len(COL_NAMES):
            cells.append("")
        row = dict(zip(COL_NAMES, cells[:len(COL_NAMES)]))
        # A duplicate rule-id would silently double-count in the coverage headline.
        if row["rule_id"] in seen:
            return None, f"duplicate rule-id in registry: {row['rule_id']!r}"
        seen.add(row["rule_id"])
        rules.append(row)

    if not rules:
        return None, "no rules parsed from registry"

    return rules, None

# ---------------------------------------------------------------------------
# World-model store
# ---------------------------------------------------------------------------


def load_world_model(path):
    """Load the world-model JSON store, keyed by rule_id. Empty dict if absent or unreadable."""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_world_model(path, model):
    """Write the world-model JSON store. Returns (ok: bool, error: str|None)."""
    if not path:
        return False, (
            "no notes root configured — brain_root.resolve_brain_root() returned NOT-SET, so there "
            "is nowhere durable to keep run history. Verdicts above are still real. Fix: "
            "python3 shared/brain_root.py --set <path>, or set CONFORMANCE_LAB_WORLD_MODEL."
        )
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(model, f, indent=2, ensure_ascii=False)
        return True, None
    except OSError as e:
        return False, f"cannot write world-model: {e}"


def update_world_model(model, rule, result):
    """
    Update (in place) the world-model record for one rule. Creates it if absent, archives the
    previous verdict into history, and records the transition as `last_delta`.

    The delta is the point. A rule moving prose-wish -> fires means a mechanism landed; a rule
    moving fires -> theater is a REGRESSION, and it is the thing you most want to be told about.
    """
    rid = rule["rule_id"]
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    verdict = result.get("verdict", "unscored")
    evidence = result.get("evidence", "")

    if rid not in model:
        model[rid] = {
            "rule_id": rid,
            "category": rule.get("category", ""),
            "importance": rule.get("importance", ""),
            "verdict": verdict,
            "evidence": evidence,
            "verified_at": now,
            "learned_note": rule.get("learned_note", ""),
            "history": [],
        }
        return

    rec = model[rid]
    prev_verdict = rec.get("verdict")
    if prev_verdict not in (None, "", "unvisited", "unscored"):
        rec.setdefault("history", []).append({
            "verdict": prev_verdict,
            "evidence": rec.get("evidence", ""),
            "verified_at": rec.get("verified_at", ""),
        })
    if prev_verdict and prev_verdict != verdict:
        rec["last_delta"] = {"from": prev_verdict, "to": verdict, "at": now}
    rec["verdict"] = verdict
    rec["evidence"] = evidence
    rec["verified_at"] = now
    rec["category"] = rule.get("category", "")
    rec["importance"] = rule.get("importance", "")

# ---------------------------------------------------------------------------
# Red-finding check
# ---------------------------------------------------------------------------


def is_red_finding(rule, verdict):
    """
    True if this rule+verdict is a red finding.

    RED if the verdict is dark/theater/error, OR if the row is structurally enforceable and has no
    mechanism and no test binding at all — a rule that claims to be structural while nothing
    enforces it and nothing tests it is the exact shape this lab exists to surface.
    """
    if verdict in RED_VERDICTS:
        return True
    struct_judg = rule.get("struct_judg", "").strip().lower()
    mechanism = rule.get("mechanism", "").strip().lower()
    test_binding = rule.get("test_binding", "").strip()
    return (
        struct_judg == "structural"
        and mechanism in ("", "none")
        and test_binding in ("", "∅")  # ∅ is U+2205
    )

# ---------------------------------------------------------------------------
# Dispatch + filters
# ---------------------------------------------------------------------------


def dispatch(rule, ctx=None):
    """Dispatch one rule to its registered probe. Returns {"verdict", "evidence"}."""
    if ctx is None:
        ctx = {}
    cat = rule.get("category", "").strip()
    if cat in CATEGORY_LETTERS:          # accept the full name as well as the letter
        cat = CATEGORY_LETTERS[cat]
    probe = PROBES.get(cat, _stub_probe)
    try:
        result = probe(rule, ctx)
    except Exception as exc:             # a probe that raises is an error, never a silent pass
        return {"verdict": "error", "evidence": f"probe raised {type(exc).__name__}: {exc}"}
    if not isinstance(result, dict) or result.get("verdict") not in VALID_VERDICTS:
        got = result.get("verdict") if isinstance(result, dict) else result
        return {"verdict": "error", "evidence": f"probe returned invalid verdict: {got!r}"}
    return result


def matches_level(rule, level):
    """True if the rule's importance field starts with the given level prefix (L1..L4)."""
    return rule.get("importance", "").strip().startswith(level)


def matches_category(rule, category_arg):
    """True if the rule's category matches the argument, given as a letter or a full name."""
    cat = rule.get("category", "").strip()
    arg = category_arg.strip()
    if arg in CATEGORY_LETTERS:
        arg = CATEGORY_LETTERS[arg]
    return cat == arg or cat == category_arg.strip()

# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


def compute_coverage(rules, verdicts_this_run):
    """
    Returns (enforced, total_structural, unvisited_ids, red_count).

    enforced         = structural rules whose verdict is `fires` this run
    total_structural = every structural rule in scope
    unvisited        = rule_ids never dispatched this run
    red_count        = red findings this run

    Note what is NOT counted as enforced: `parked`. A park is an honest admission that a rule is
    not yet proven, so it sits in the denominator and not the numerator. That is the whole
    difference between a coverage number and a comfort number.
    """
    by_id = {r["rule_id"]: r for r in rules}
    unvisited_ids = set(by_id) - set(verdicts_this_run)

    structural = [r for r in rules if r.get("struct_judg", "").strip().lower() == "structural"]
    enforced = sum(
        1 for r in structural
        if verdicts_this_run.get(r["rule_id"], {}).get("verdict") == "fires"
    )
    red_count = sum(
        1 for rid, result in verdicts_this_run.items()
        if is_red_finding(by_id.get(rid, {}), result.get("verdict", "unscored"))
    )
    return enforced, len(structural), unvisited_ids, red_count

# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------


def print_rule_result(rule, result):
    """Print one rule's verdict."""
    verdict = result.get("verdict", "unscored")
    evidence = result.get("evidence", "")
    cat = rule.get("category", "").strip()
    print(f"{rule['rule_id']}  [{verdict}]  ({rule.get('importance', '').strip()})  "
          f"cat={CATEGORY_NAMES.get(cat, cat)}")
    if evidence:
        print(f"  evidence: {evidence}")


def print_headline(enforced, total_structural, unvisited_ids, red_count):
    """Print the coverage headline."""
    print(
        f"\n{enforced} of {total_structural} structural rules enforced"
        f"  ·  {len(unvisited_ids)} unvisited"
        f"  ·  {red_count} red findings"
    )

# ---------------------------------------------------------------------------
# Run engine
# ---------------------------------------------------------------------------


def run_rules(rules, model):
    """Dispatch every rule, update the model, and return {rule_id: result}."""
    verdicts = {}
    for rule in rules:
        result = dispatch(rule)
        update_world_model(model, rule, result)
        verdicts[rule["rule_id"]] = result
    return verdicts


def _finish(rules, verdicts, model):
    """Print every result + the headline, persist, and return the exit code."""
    for rule in rules:
        print_rule_result(rule, verdicts[rule["rule_id"]])
    enforced, total_structural, unvisited_ids, red_count = compute_coverage(rules, verdicts)
    print_headline(enforced, total_structural, unvisited_ids, red_count)

    ok, err = save_world_model(WORLD_MODEL_PATH, model)
    if not ok:
        # A store failure never rewrites the verdicts — it is reported alongside them.
        print(f"WARNING (verdicts above stand, history not saved): {err}", file=sys.stderr)
    return 1 if red_count > 0 else 0

# ---------------------------------------------------------------------------
# ⭐ SELFTEST — the negative control
# ---------------------------------------------------------------------------


def _registry_hook_names(rules):
    """Every hook script named in the registry's `mechanism` column."""
    return sorted({
        r["mechanism"].strip() for r in rules
        if r.get("mechanism", "").strip().endswith(".sh")
    })


def cmd_selftest(rules):
    """
    Prove the lab can FAIL. Point the guard probe at a directory of inert `exit 0` stubs and
    assert every category-C rule comes back `theater`.

    Returns the exit code: 0 = the lab caught every inert guard, 1 = it rubber-stamped at least
    one, 2 = the selftest could not be set up (which is itself a failure to trust).

    Reads as a control experiment, and is one: identical probe, identical payloads, only the
    guards swapped for guards that do nothing.
    """
    c_rules = [r for r in rules if matches_category(r, "C")]
    if not c_rules:
        print("ERROR: selftest needs at least one category-C rule in the registry", file=sys.stderr)
        return 2

    hook_names = _registry_hook_names(c_rules)
    if not hook_names:
        print("ERROR: no hook filenames in the registry's mechanism column", file=sys.stderr)
        return 2

    tmpdir = tempfile.mkdtemp(prefix="conformance-lab-selftest-")
    prior = os.environ.get("CONFORMANCE_LAB_HOOKS_DIR")
    try:
        for name in hook_names:
            stub = os.path.join(tmpdir, name)
            with open(stub, "w", encoding="utf-8") as f:
                f.write("#!/bin/bash\n# INERT selftest stub — allows everything, on purpose.\nexit 0\n")
            os.chmod(stub, 0o755)

        os.environ["CONFORMANCE_LAB_HOOKS_DIR"] = tmpdir

        print("=== SELFTEST — the negative control ===")
        print(f"Planted {len(hook_names)} INERT guards (each one just `exit 0`) in a temp dir")
        print("and re-aimed the probe at them. Every rule MUST now come back `theater`.")
        print("Any rule that still says `fires` is the lab rubber-stamping a guard that does")
        print("nothing — which would mean a green sweep proves nothing at all.\n")

        rubber_stamped, caught, skipped = [], [], []
        for rule in c_rules:
            result = dispatch(rule)
            verdict = result.get("verdict")
            if verdict == "theater":
                caught.append(rule["rule_id"])
                mark = "CAUGHT  "
            elif verdict == "parked":
                # A parked rule never fires a hook, so swapping the hooks cannot change its answer.
                # Correctly outside the assertion — but named, never silently dropped.
                skipped.append(rule["rule_id"])
                mark = "n/a     "
            else:
                rubber_stamped.append((rule["rule_id"], verdict))
                mark = "RUBBER-STAMPED"
            print(f"  [{mark}] {rule['rule_id']:34s} verdict={verdict}")

        print(f"\ncaught {len(caught)} · parked-so-not-applicable {len(skipped)} "
              f"· rubber-stamped {len(rubber_stamped)}")

        if rubber_stamped:
            print("\n*** SELFTEST FAILED — the lab passed a guard that does nothing: "
                  + ", ".join(f"{rid}({v})" for rid, v in rubber_stamped), file=sys.stderr)
            return 1

        print("\nSELFTEST PASSED — the lab refuses to rubber-stamp an inert guard. "
              "A green sweep from this lab means something.")
        return 0
    finally:
        if prior is None:
            os.environ.pop("CONFORMANCE_LAB_HOOKS_DIR", None)
        else:
            os.environ["CONFORMANCE_LAB_HOOKS_DIR"] = prior
        shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_rule(rule_id, rules, model):
    matched = [r for r in rules if r["rule_id"] == rule_id]
    if not matched:
        print(f"ERROR: rule-id not found: {rule_id!r}", file=sys.stderr)
        return 2
    return _finish(matched, run_rules(matched, model), model)


def cmd_sweep(rules, model):
    return _finish(rules, run_rules(rules, model), model)


def cmd_category(category_arg, rules, model):
    filtered = [r for r in rules if matches_category(r, category_arg)]
    if not filtered:
        print(f"ERROR: no rules found for category: {category_arg!r}", file=sys.stderr)
        return 2
    return _finish(filtered, run_rules(filtered, model), model)


def cmd_level(level_arg, rules, model):
    filtered = [r for r in rules if matches_level(r, level_arg)]
    if not filtered:
        print(f"ERROR: no rules found for level: {level_arg!r}", file=sys.stderr)
        return 2
    return _finish(filtered, run_rules(filtered, model), model)

# ---------------------------------------------------------------------------

USAGE = """Usage: driver.py <mode> [args]

Modes:
  --rule <rule-id>       Run one rule (e.g. GUARD-gws-logout)
  --sweep                Run every rule in the registry
  --category <name>      Run one category (letter A-H, or its full name)
  --level <L1|L2|L3|L4>  Run rules at one importance level
  --selftest             Plant inert guards and prove the lab catches them (run this first)

Verdicts: fires · dark · prose-wish · theater · error · unscored · unvisited · parked
  dark, theater and error count AGAINST. parked counts against the denominator, never as a pass.

Exit codes: 0 = clean · 1 = red findings · 2 = tool error
"""


def main():
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        sys.exit(2)

    rules, err = parse_registry(REGISTRY_PATH)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(2)
    print(f"[registry] {len(rules)} rules loaded from {REGISTRY_PATH}", file=sys.stderr)

    if args[0] == "--selftest":
        sys.exit(cmd_selftest(rules))

    model = load_world_model(WORLD_MODEL_PATH)

    if args[0] == "--sweep":
        sys.exit(cmd_sweep(rules, model))

    if args[0] in ("--rule", "--category", "--level"):
        if len(args) < 2:
            print(f"ERROR: {args[0]} requires an argument", file=sys.stderr)
            sys.exit(2)
        handler = {"--rule": cmd_rule, "--category": cmd_category, "--level": cmd_level}[args[0]]
        sys.exit(handler(args[1], rules, model))

    print(f"ERROR: unknown mode: {args[0]!r}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
