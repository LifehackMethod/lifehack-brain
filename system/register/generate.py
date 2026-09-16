#!/usr/bin/env python3
"""generate.py — the register's GENERATOR, with ASSERT-ON-WRITE (Feature B1.3,
enforcement-layer Phase 2 plan).

Register JSONL in -> wiring files out. Two independent gates run BEFORE any byte
is written to disk:

  1. SCHEMA GATE (whole register, global) — every row must validate against
     schema v1 (`schema_v1.py` / `validate_register.py`, both Feature B1.1, reused
     here rather than re-implemented — one source of truth for "is this row
     well-formed"). A single malformed row refuses the ENTIRE run: nothing is
     written, for any target, because a register that fails to parse cannot be
     trusted for ANY of its rows.

  2. ASSERT-ON-WRITE GATE (per output target) — for each wiring file this tool
     can emit, every hook row that would land in it must resolve to a script
     that ACTUALLY EXISTS ON DISK, checked FRESH, right now, by this tool —
     never by trusting the register's own `exists` field, which could be
     stale (harvested an hour ago) or simply wrong (a human hand-edited the
     register per constraint 0.5's "files a human can open and fix by hand,"
     and typed a path that doesn't exist). A register row's stored `exists`
     is on-disk truth AT HARVEST TIME; this gate re-derives it AT WRITE TIME,
     which is what "assert-ON-WRITE" means.

     Refusal is scoped to the ONE target file whose rows are broken — the
     plan's own Verify line requires refusing the private wiring file while
     still emitting the public ones clean, so atomicity is per-target, not
     whole-run: "no partial file written" means a broken target gets NOTHING
     written (not a version missing the bad rows), while an unaffected
     target still gets written normally, via temp-file + rename.

  3. CACHE-DIVERGENCE CHECK (per public hook row, WARN only, never blocks) —
     constraint 0.5: "the plugin cache is platform-owned — the register
     accounts for it, never generates it." This tool only ever READS the
     cache to compare content; it never writes there, and a divergence never
     refuses a write (Enver's B1.4 severity ruling, 2026-09-15: WARN, not
     refuse, for the analogous omission check — the same posture is used
     here for cache drift since the plan does not rule otherwise for B1.3).

  4. OMISSION CHECK (Feature B1.4, `omission_check.py`, a sibling module this
     generator calls, not re-implemented here) — after the schema gate, a fresh
     disk walk of the GOVERNED FOLDERS (`system/hooks`, `system/tools`, both
     repos — T1's own `GOVERNED_DIRS`) is cross-referenced against this same
     register: any governed-folder file that is neither the `path` of a matching
     register row NOR listed in the hand-editable exemption file
     (`omission-exemptions.txt`, this folder) is NAMED. Severity is Enver's
     2026-09-15 ruling (WARN for v1): `--severity warn` (default) prints a
     clearly marked WARN section and does not affect the exit code; `--severity
     refuse` makes the identical finding a whole-run refusal, matching the
     schema gate's own all-or-nothing posture — nothing written, any target.

  5. CALLER LINT (Feature B1.5, `caller_lint.py`, a sibling module this generator
     calls, not re-implemented here — merged in and wired by Feature B1.5w) — a
     read-only report, run right after the omission check, over the same loaded
     register rows: which governed hook-plane/tool-plane units have NO known
     caller (T1's validated 7-class ontology: registered-hook, scheduled,
     script-invoked, skill-referenced, ci-invoked, cli-instructed, else
     UNCALLED). WARN severity always — informational only, this NEVER refuses a
     write and has no `--severity` knob of its own (unlike the omission check
     above, which can escalate to `refuse`), because T1 "lists; it never judges"
     what an UNCALLED unit means. `--no-caller-lint` skips this section entirely
     (mechanically, not by hiding output) — every other gate's behavior is
     unchanged either way.

Usage:
    python3 generate.py <register.jsonl> --out DIR
        [--public-root PATH] [--private-root PATH]
        [--cache-root PATH | --no-cache]
        [--severity warn|refuse] [--exemptions PATH]
        [--dedup PATH] [--install-root PATH]

With plain `--out DIR`, writes ONLY inside DIR — never a real checkout's
`.claude/settings.json` / `hooks/hooks.json` directly. `--install-root PATH`
(Feature B2.2, opt-in — the default behavior above is unchanged) additionally
merges the "settings"/"plugin" targets' generated "hooks" section straight
into `<PATH>/.claude/settings.json` / `<PATH>/hooks/hooks.json`, leaving every
other top-level key untouched (`install_into_repo()` below) — this is the
generator writing its own two real files, never a hand edit. No new
dependency: stdlib only, plus this folder's own `schema_v1.py` /
`validate_register.py` / `harvest.py`.
"""
import argparse
import json
import os
import re
import sys

# Sibling-module imports — same convention `validate_register.py` already
# relies on: running `python3 .../generate.py` puts this script's own
# directory at sys.path[0] automatically, so `schema_v1`/`validate_register`/
# `harvest` (all in this same `system/register/` folder) resolve with no
# path hacking. Reused, not re-implemented — one source of truth each for
# "is this row well-formed" (validate_row) and "where do the repo roots /
# cache root live" (harvest.py's own CLI defaults and derivation logic).
from schema_v1 import UNIT_TYPES  # noqa: F401  (re-exported for callers/tests)
from validate_register import validate_row
from harvest import REPO_ROOT_FROM_SCRIPT, DEFAULT_PRIVATE_ROOT, cache_root_for, short_sha
import omission_check  # Feature B1.4 — the omission check, a sibling module this
                       # generator calls; see omission_check.py for the design.
import caller_lint  # Feature B1.5 — the caller lint, a sibling module this generator
                    # calls (wired by B1.5w); see caller_lint.py for the design.

# Surface -> (form, repo_filter, output filename). Feature B2.2 (this task) applies
# a hand-editable, reason-required de-dup exception list (`surface-dedup.txt`,
# `load_surface_dedup()` below) ON TOP of this table's rows_for_surface() lookup, so
# a hook row that is registered on BOTH public surfaces still lands on both UNLESS a
# specific, evidenced line in that file says to drop it from ONE of them. This table
# itself never needed to change for that — the split lives in the exception file, not
# here, which is why B1.3 left this table as one small piece of data.
SURFACE_TARGETS = (
    ("settings",      "settings",      "public",  "settings.hooks-section.json"),
    ("plugin",        "plugin",        "public",  "hooks.json"),
    ("registrations", "registrations", "private", "registrations.json"),
    ("user",          "user",          "private", "user-settings.hooks-section.json"),
)

DEFAULT_DEDUP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "surface-dedup.txt")

# (repo-side surface, cache-side surface) pairs — only rows registered on BOTH
# have a cache mirror to compare against at all.
CACHE_PAIRS = (("settings", "cache-settings"), ("plugin", "cache-plugin"))


# ---------------------------------------------------------------------------
# load + schema gate (reuses B1.1's validator; never re-implements it)
# ---------------------------------------------------------------------------
def load_register(path):
    """Return a list of (line_no, row_or_None, parse_errors_or_None)."""
    entries = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                entries.append((i, None, [f"line {i}: invalid JSON ({e})"]))
                continue
            entries.append((i, row, None))
    return entries


def schema_check(entries):
    """Return [(line_no, [error_strings])] for every entry that fails to
    parse or fails schema v1 — the exact same check B1.1's Verify (c) proved
    against known-good and known-bad rows, reused here, not re-derived."""
    problems = []
    for line_no, row, parse_errs in entries:
        if parse_errs is not None:
            problems.append((line_no, parse_errs))
            continue
        errs = validate_row(row, line_no)
        if errs:
            problems.append((line_no, errs))
    return problems


# ---------------------------------------------------------------------------
# assert-on-write: fresh, live existence check (never trusts a stale field)
# ---------------------------------------------------------------------------
def resolve_full_path(row, public_root, private_root):
    root = public_root if row.get("repo") == "public" else private_root
    return os.path.join(root, row.get("path", "").lstrip("/"))


def live_exists(row, public_root, private_root):
    """The assert-on-write predicate: is the row's target script ACTUALLY on
    disk, right now? An UNPARSED path (the harvester's own escape hatch for a
    command it couldn't decompose) can never resolve to a real file and is
    therefore always broken — matching harvest.py's own behavior, not a new
    rule invented here."""
    path = row.get("path", "")
    if not path or path.startswith("UNPARSED"):
        return False
    return os.path.isfile(resolve_full_path(row, public_root, private_root))


# ---------------------------------------------------------------------------
# emit: register rows -> a surface's {"hooks": {...}} document
# ---------------------------------------------------------------------------
def emit_command(rel, args, form):
    if form == "settings":
        cmd = f'bash "${{CLAUDE_PROJECT_DIR}}{rel}"'
    elif form == "plugin":
        cmd = f'bash "${{CLAUDE_PLUGIN_ROOT}}{rel}"'
    elif form == "registrations":
        cmd = f'bash "$HOME/.claude/skills/ClaudeOps{rel}"'
    elif form == "user":
        cmd = f'bash "{rel}"'
    else:
        raise ValueError(f"unknown surface form {form!r}")
    return cmd + (f" {args}" if args else "")


def build_hooks_doc(rows, form):
    """rows must already be in a deterministic order (see `sorted(...)` at the
    call site) — that, plus `json.dumps(..., sort_keys=False)` preserving
    Python's insertion-ordered dict, is what makes the emitted file
    byte-stable across two runs without needing to sort JSON keys (which
    would reorder `type`/`command`/`statusMessage` inside each hook entry
    away from the shape a human editing the live file already expects)."""
    hooks = {}
    for row in rows:
        entry_list = hooks.setdefault(row["event"], [])
        grp = next((g for g in entry_list if g.get("matcher", "") == row["matcher"]), None)
        if grp is None:
            grp = {"hooks": []}
            if row["matcher"]:
                grp["matcher"] = row["matcher"]
            entry_list.append(grp)
        h = {"type": "command"}
        if row.get("if"):
            h["if"] = row["if"]
        h["command"] = emit_command(row["path"], row["args"], form)
        if row["status"]:
            h["statusMessage"] = row["status"]
        grp["hooks"].append(h)
    return {"hooks": hooks}


def load_surface_dedup(path):
    """Return {(repo, path, event, matcher, args, drop_surface): reason}. Missing
    file == no exceptions (not an error — the same convention as B1.4's
    `omission_check.load_exemptions`: a fresh checkout with none declared yet is a
    legal state, not a defect)."""
    dedup = {}
    if not path or not os.path.isfile(path):
        return dedup
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 6)
            if len(parts) != 7:
                raise ValueError(
                    f"{path}:{lineno}: malformed dedup line "
                    f"(need repo|path|event|matcher|args|drop_surface|reason): {raw!r}"
                )
            repo, dp_path, event, matcher, args, drop_surface = (
                p.strip() for p in parts[:6]
            )
            reason = parts[6].strip()
            if repo not in ("public", "private"):
                raise ValueError(f"{path}:{lineno}: repo must be 'public' or 'private': {raw!r}")
            if not dp_path.startswith("/"):
                raise ValueError(f"{path}:{lineno}: path must start with '/': {raw!r}")
            if drop_surface not in ("settings", "plugin"):
                raise ValueError(
                    f"{path}:{lineno}: drop_surface must be 'settings' or 'plugin' "
                    f"(the only two surfaces this generator writes): {raw!r}"
                )
            if not reason:
                raise ValueError(f"{path}:{lineno}: dedup entry has no reason (required): {raw!r}")
            dedup[(repo, dp_path, event, matcher, args, drop_surface)] = reason
    return dedup


def rows_for_surface(hook_rows, surface, repo_filter, dedup=None, applied=None):
    """hook_rows: [(line_no, row)]. Returns the matching subset, same shape, minus
    any row a `surface-dedup.txt` entry (Feature B2.2) names for THIS surface
    specifically. `dedup`: the dict `load_surface_dedup()` returns. `applied`, if
    given, is a set this function adds every dedup KEY it actually STRIPPED off a
    row THIS run into — a key can be a no-op here (the row already doesn't carry
    that surface, e.g. because a prior `--install-root` already applied it) without
    that meaning the exception is stale; `dedup_identity_status()` below is what
    decides staleness, by asking whether the underlying hook still exists in the
    register AT ALL, regardless of which surfaces it currently carries."""
    dedup = dedup or {}
    matched = []
    for line_no, row in hook_rows:
        if row.get("repo") != repo_filter:
            continue
        surfaces = row.get("surfaces") or []
        if surface not in surfaces:
            continue
        key = (row.get("repo"), row.get("path"), row.get("event"),
               row.get("matcher"), row.get("args"), surface)
        if key in dedup:
            if applied is not None:
                applied.add(key)
            continue
        matched.append((line_no, row))
    return matched


def dedup_identity_status(hook_rows, dedup):
    """Split `dedup`'s keys into IN-EFFECT (the hook this key names still exists
    somewhere in the register, whether or not it currently carries the surface
    this key drops it from — a policy can be a standing no-op run after run, once
    a prior install already removed the row from that surface, and that is NOT
    staleness) vs STALE (no hook with this (repo, path, event, matcher, args)
    identity exists in the register at all anymore — the row was deleted or
    renamed, and this line should be removed, not left to mislead the next
    reader). Returns (in_effect: {key: reason}, stale: {key: reason})."""
    identities = {
        (row.get("repo"), row.get("path"), row.get("event"),
         row.get("matcher"), row.get("args"))
        for _, row in hook_rows
    }
    in_effect, stale = {}, {}
    for key, reason in dedup.items():
        repo, path, event, matcher, args, _drop_surface = key
        if (repo, path, event, matcher, args) in identities:
            in_effect[key] = reason
        else:
            stale[key] = reason
    return in_effect, stale


def sort_key(row):
    return (row["event"], row["matcher"], row["path"], row["args"])


# ---------------------------------------------------------------------------
# group collapse (Feature B5.2) — N member rows sharing one `group` -> 1 row
# ---------------------------------------------------------------------------
def dispatcher_path_for_group(group):
    """The dispatcher script's repo-relative path, DERIVED from the group
    string — never a hand-typed lookup table entry. Kept as its own function
    so the ONE naming rule lives in one place (the schema-v1.md `group`
    Addendum names this exact function)."""
    return f"/system/hooks/group_dispatch_{group}.sh"


def collapse_group_rows(rows):
    """`rows`: hook rows already filtered to ONE surface (settings, plugin,
    registrations, or user). Rows carrying a null/absent `group` pass through
    unchanged. Rows sharing a non-null `group` AND an identical
    (event, matcher, launch_mode, if, args) — the only combination that can
    legitimately share one wiring entry, since anything else would mean the
    members do not actually agree on how they're invoked — collapse onto ONE
    synthetic row whose `path` is that group's dispatcher script
    (`dispatcher_path_for_group`). The schema/validator gate (`schema_check`,
    already run before this is ever called) is what makes it structurally
    impossible for a collapsed group to include a blocking-capable event row
    — this function does not re-check that; it trusts the gate that already
    ran, same as every other step in `generate()` trusts the schema gate.

    Raises ValueError on a group whose members disagree on repo (a public/
    private mix would need a dispatcher in two places at once — unsupported,
    and no such case exists in this register today) — fail loud rather than
    silently pick one.
    """
    buckets = {}
    passthrough = []
    for row in rows:
        group = row.get("group")
        if not group:
            passthrough.append(row)
            continue
        key = (group, row["event"], row["matcher"], row.get("launch_mode"),
               row.get("if"), row["args"])
        buckets.setdefault(key, []).append(row)

    out = list(passthrough)
    for (group, event, matcher, launch_mode, if_cond, args), members in buckets.items():
        repos = {m.get("repo") for m in members}
        if len(repos) != 1:
            raise ValueError(
                f"group {group!r} has members in more than one repo ({sorted(repos)}) "
                f"— a single dispatcher script cannot live in two repos at once"
            )
        member_names = sorted(m["path"].rsplit("/", 1)[-1] for m in members)
        out.append({
            "event": event,
            "matcher": matcher,
            "path": dispatcher_path_for_group(group),
            "args": args,
            "if": if_cond,
            "status": f"Running the \"{group}\" group ({', '.join(member_names)})...",
            "repo": repos.pop(),
            "launch_mode": launch_mode,
            "group": group,
        })
    return out


# ---------------------------------------------------------------------------
# cache-divergence: WARN only, read-only against the platform cache
# ---------------------------------------------------------------------------
def cache_divergence_warnings(hook_rows, public_root, cache_root):
    """hook_rows: [(line_no, row)]. Never writes to cache_root — read-only,
    per constraint 0.5. A row missing its script on the repo side is already
    reported by the assert-on-write gate above; this function skips it
    rather than double-reporting. One warning per PATH (not per surface
    pair) — a script double-registered on both settings/cache-settings and
    plugin/cache-plugin is still the same one file being compared against
    the same one cache mirror, so a single sha mismatch is one finding, not
    two, even though it lists every cache surface the drift shows up on."""
    warnings = []
    if not cache_root:
        return warnings
    checked = set()
    for _, row in hook_rows:
        if row.get("repo") != "public":
            continue
        path = row["path"]
        if path in checked:
            continue
        surfaces = set(row.get("surfaces") or [])
        mirrored_on = sorted(
            cache_surface for repo_surface, cache_surface in CACHE_PAIRS
            if repo_surface in surfaces and cache_surface in surfaces
        )
        if not mirrored_on:
            continue
        checked.add(path)
        repo_full = os.path.join(public_root, path.lstrip("/"))
        cache_full = os.path.join(cache_root, path.lstrip("/"))
        if not os.path.isfile(repo_full):
            continue  # already named by the assert-on-write gate
        if not os.path.isfile(cache_full):
            warnings.append(
                f"WARN cache-divergence: {path} registered on {'/'.join(mirrored_on)} "
                f"but absent from the plugin cache ({cache_full})"
            )
            continue
        repo_sha = short_sha(repo_full)
        cache_sha = short_sha(cache_full)
        if repo_sha != cache_sha:
            warnings.append(
                f"WARN cache-divergence: {path} content differs (mirrored on "
                f"{'/'.join(mirrored_on)}) — repo={repo_sha} cache={cache_sha}"
            )
    return warnings


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def generate(register_path, out_dir, public_root, private_root, cache_root,
             severity="warn", exemptions_path=None, dedup_path=None,
             skip_caller_lint=False, home_root=None, targets="all"):
    """Returns a result dict; never raises for an ordinary refusal (schema,
    broken-path, or a refuse-severity omission) — those are reported in the
    result, and the caller (main()) decides the exit code. Only writes files
    after every gate that applies to that specific file has passed, via
    temp-file + os.replace (atomic rename on the same filesystem).

    `dedup_path` (Feature B2.2, default `surface-dedup.txt` next to this script
    when None and the default file exists): a hand-editable, reason-required
    exception list narrowing which of the "settings"/"plugin" surfaces a
    currently-both-registered hook row is generated onto. See
    `load_surface_dedup()`'s and the file's own docstrings for the safety
    reasoning — this NEVER adds a row to a surface, only ever removes one, and
    only for a row a human has named with evidence.

    `skip_caller_lint` (Feature B1.5w): when True, the caller-lint report
    section below is skipped entirely — a mechanical opt-out, never a
    disguised gate, since the lint is WARN-only and cannot affect what gets
    written regardless.

    `targets` (Feature B3.2 fix, 2026-09-15 — the "public commit gate must not
    depend on the private repo's live disk state" repair): default "all" is
    UNCHANGED behavior — a broken path on ANY target (public or private)
    refuses that target and contributes to a non-zero exit code, exactly as
    before this flag existed. "public" is the new, opt-in, additive mode a
    caller passes deliberately (`check_drift.py` does, for its on-commit
    gate): every target is still ATTEMPTED and reported identically, but a
    REFUSED target whose `repo_filter` is "private" is downgraded to a
    non-blocking WARN (named, never silent) and excluded from the exit-code
    computation — the public wiring drift check this tool exists for must not
    fail because someone else's private-repo checkout is stale or absent on
    this machine."""
    entries = load_register(register_path)

    problems = schema_check(entries)
    if problems:
        return {
            "schema_ok": False,
            "schema_problems": problems,
            "targets": [],
            "warnings": [],
            "omission": None,
            "caller_lint": None,
        }

    # Feature B1.4 — the omission check, run right after the schema gate (every
    # row it reads is already known well-formed) and before any target is
    # written. `--severity refuse` behaves like the schema gate above: a real
    # finding refuses the WHOLE run, nothing written for any target, because an
    # omission is a register-wide integrity finding, not a single target's
    # problem. `--severity warn` (default) never blocks; its findings are
    # carried into the result and printed as a clearly marked WARN section.
    omission_result = omission_check.run(
        entries, public_root, private_root, exemptions_path, severity,
    )

    # Feature B1.5w — the caller lint, run right after the omission check, over
    # the same loaded rows (every row here is already schema-valid). Always
    # WARN severity, never a gate: computed before the omission-refusal branch
    # below so the report section appears whichever way that branch resolves,
    # exactly like the omission check itself. `rows` matches the entry point's
    # own documented calling convention (`caller_lint.py`'s module docstring).
    caller_lint_result = None
    if not skip_caller_lint:
        rows = [row for _, row, _ in entries if row]
        caller_lint_result = caller_lint.lint_register(
            rows, public_root, private_root, cache_root=cache_root, home_root=home_root,
        )

    if severity == "refuse" and omission_result["flagged_count"] > 0:
        return {
            "schema_ok": True,
            "schema_problems": [],
            "targets": [],
            "warnings": [],
            "omission": omission_result,
            "omission_refused": True,
            "caller_lint": caller_lint_result,
        }

    hook_rows = [(ln, row) for ln, row, _ in entries if row.get("type") == "hook"]

    # launch_mode distribution (Option G, restored 2026-09-15) — purely a
    # report over already-validated rows; never influences what gets
    # written (build_hooks_doc() never reads this field).
    launch_mode_distribution = {}
    for _, row in hook_rows:
        lm = row.get("launch_mode")
        launch_mode_distribution[lm] = launch_mode_distribution.get(lm, 0) + 1

    os.makedirs(out_dir, exist_ok=True)

    dedup_path = dedup_path if dedup_path is not None else DEFAULT_DEDUP_PATH
    dedup = load_surface_dedup(dedup_path)
    dedup_applied = set()

    # A REFUSED target's own broken-path finding only refuses the WHOLE run
    # (contributes to generate.py's exit code) when it is "blocking" — always
    # true at targets="all" (unchanged default); false for a private-repo
    # target at targets="public" (the check_drift.py on-commit-gate mode).
    def _blocking(repo_filter):
        return not (targets == "public" and repo_filter == "private")

    target_results = []
    for surface, form, repo_filter, filename in SURFACE_TARGETS:
        matched = rows_for_surface(hook_rows, surface, repo_filter,
                                    dedup=dedup, applied=dedup_applied)
        if not matched:
            target_results.append({
                "filename": filename, "surface": surface, "status": "SKIP",
                "reason": "no rows registered on this surface", "broken": [],
                "blocking": _blocking(repo_filter),
            })
            continue
        broken = [
            (ln, row) for ln, row in matched
            if not live_exists(row, public_root, private_root)
        ]
        if broken:
            target_results.append({
                "filename": filename, "surface": surface, "status": "REFUSED",
                "reason": "target path does not exist on disk", "broken": broken,
                "blocking": _blocking(repo_filter),
            })
            continue
        ordered = sorted((row for _, row in matched), key=sort_key)

        # Feature B5.2 — collapse any rows sharing a `group` onto their one
        # dispatcher row BEFORE building the doc, so the dispatcher's command
        # is what actually gets emitted for the whole group. The schema gate
        # (already run, above, before ANY target is touched) is what makes a
        # blocking-capable event row structurally unable to reach here with a
        # non-null `group` — see collapse_group_rows()'s own docstring.
        ordered = sorted(collapse_group_rows(ordered), key=sort_key)

        # The assert-on-write gate above already checked every ORIGINAL
        # member's own file — but a dispatcher's path is synthetic (derived
        # from the group string, not a register row), so it never went
        # through that check. Re-run the identical check on just the
        # synthetic rows: a missing dispatcher script refuses this target
        # exactly like a missing member script would, never a silent skip.
        group_broken = [
            row for row in ordered
            if row.get("group") and not live_exists(row, public_root, private_root)
        ]
        if group_broken:
            target_results.append({
                "filename": filename, "surface": surface, "status": "REFUSED",
                "reason": "group dispatcher script does not exist on disk",
                "broken": [(None, row) for row in group_broken],
                "blocking": _blocking(repo_filter),
            })
            continue

        doc = build_hooks_doc(ordered, form)
        content = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
        final_path = os.path.join(out_dir, filename)
        tmp_path = final_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, final_path)
        target_results.append({
            "filename": filename, "surface": surface, "status": "OK",
            "reason": None, "broken": [], "rows_written": len(ordered),
            "path": final_path, "doc": doc, "blocking": _blocking(repo_filter),
        })

    warnings = cache_divergence_warnings(hook_rows, public_root, cache_root)

    dedup_in_effect, dedup_stale = dedup_identity_status(hook_rows, dedup)

    return {
        "schema_ok": True,
        "schema_problems": [],
        "targets": target_results,
        "warnings": warnings,
        "omission": omission_result,
        "caller_lint": caller_lint_result,
        "dedup_applied": {k: dedup[k] for k in dedup_applied},
        "dedup_in_effect": dedup_in_effect,
        "dedup_stale": dedup_stale,
        "launch_mode_distribution": launch_mode_distribution,
    }


def report(result):
    lines = []
    if not result["schema_ok"]:
        lines.append("REFUSED: register fails schema v1 validation — writing NOTHING (no target touched).")
        for line_no, errs in result["schema_problems"]:
            for e in errs:
                lines.append(f"  {e}")
        return "\n".join(lines), 1

    if result.get("omission_refused"):
        lines.append(
            "REFUSED (--severity refuse): omission check found governed script(s) neither "
            "registered nor exempt — writing NOTHING (no target touched)."
        )
        lines.extend(omission_check.report_lines(result["omission"]))
        if result.get("caller_lint") is not None:
            lines.append("")
            lines.extend(caller_lint.report_lines(result["caller_lint"]))
        return "\n".join(lines), 1

    any_refused = False
    non_blocking_refusals = []
    for t in result["targets"]:
        if t["status"] == "OK":
            lines.append(f"  {t['filename']:<38} OK       ({t['rows_written']} rows) -> {t['path']}")
        elif t["status"] == "SKIP":
            lines.append(f"  {t['filename']:<38} SKIP     ({t['reason']})")
        elif not t.get("blocking", True):
            # targets="public" mode (check_drift.py's on-commit gate): a
            # REFUSED private target is real information (named below, in
            # its own WARN section) but never refuses the run — the public
            # wiring drift check must not depend on the private repo's live
            # disk state on this machine.
            lines.append(f"  {t['filename']:<38} WARN     ({t['reason']}, non-blocking: private target) "
                         f"— nothing written for this target")
            non_blocking_refusals.append(t)
        else:
            any_refused = True
            lines.append(f"  {t['filename']:<38} REFUSED  ({t['reason']}) — nothing written for this target")
            for ln, row in t["broken"]:
                lines.append(
                    f"      line {ln}: id={row.get('id')!r} path={row.get('path')!r} "
                    f"repo={row.get('repo')} event={row.get('event')} matcher={row.get('matcher')!r}"
                )

    if non_blocking_refusals:
        lines.append("")
        lines.append("WARN — non-blocking private-target finding(s), STALE ROW(S) NAMED "
                     "(targets=public mode; a maintainer should still refresh the register — "
                     "see FIX_COMMAND — this just never refuses the PUBLIC commit for it):")
        for t in non_blocking_refusals:
            for ln, row in t["broken"]:
                lines.append(
                    f"  {t['filename']}: line {ln}: id={row.get('id')!r} path={row.get('path')!r} "
                    f"repo={row.get('repo')} event={row.get('event')} matcher={row.get('matcher')!r}"
                )

    if result["warnings"]:
        lines.append("")
        lines.append("WARNINGS (cache-divergence, non-blocking):")
        for w in result["warnings"]:
            lines.append(f"  {w}")

    if result.get("dedup_applied"):
        lines.append("")
        lines.append("SURFACE-DEDUP APPLIED THIS RUN (Feature B2.2, surface-dedup.txt):")
        for (repo, path, event, matcher, args, drop_surface), reason in sorted(
                result["dedup_applied"].items()):
            lines.append(
                f"  DROPPED from {drop_surface!r}: {repo}:{path} event={event} "
                f"matcher={matcher!r} args={args!r}"
            )
            lines.append(f"      reason: {reason}")

    dormant = {
        k: v for k, v in (result.get("dedup_in_effect") or {}).items()
        if k not in result.get("dedup_applied", {})
    }
    if dormant:
        lines.append("")
        lines.append("SURFACE-DEDUP DORMANT (already off that surface — a prior install already "
                      "applied this policy; not a finding, the entry is still correct):")
        for (repo, path, event, matcher, args, drop_surface) in sorted(dormant):
            lines.append(f"  {repo}:{path} event={event} matcher={matcher!r} "
                         f"drop_surface={drop_surface!r}")

    if result.get("dedup_stale"):
        lines.append("")
        lines.append("WARN surface-dedup.txt entries are STALE (no hook with this identity exists "
                      "in the register at ALL anymore — the underlying row was deleted or renamed; "
                      "remove this line, it names nothing real):")
        for (repo, path, event, matcher, args, drop_surface), reason in sorted(
                result["dedup_stale"].items()):
            lines.append(
                f"  {repo}:{path} event={event} matcher={matcher!r} args={args!r} "
                f"drop_surface={drop_surface!r}"
            )

    if result.get("launch_mode_distribution") is not None:
        lines.append("")
        lines.append("LAUNCH_MODE DISTRIBUTION (hook registrations, Option G restored 2026-09-15):")
        dist = result["launch_mode_distribution"]
        for value in ("project", "plugin", "both", "private"):
            lines.append(f"  {value:<8} {dist.get(value, 0)}")
        unrecognized = {k: v for k, v in dist.items()
                        if k not in ("project", "plugin", "both", "private")}
        if unrecognized:
            lines.append(f"  UNRECOGNIZED VALUE(S) — a finding, not expected: {unrecognized}")

    if result.get("omission") is not None:
        lines.append("")
        lines.extend(omission_check.report_lines(result["omission"]))

    if result.get("caller_lint") is not None:
        lines.append("")
        lines.extend(caller_lint.report_lines(result["caller_lint"]))

    exit_code = 1 if any_refused else 0
    return "\n".join(lines), exit_code


# ---------------------------------------------------------------------------
# install: merge the "settings"/"plugin" targets into a REAL checkout's own
# .claude/settings.json / hooks/hooks.json (Feature B2.2 — opt-in, `--install-
# root`; plain `--out DIR` behavior above is unchanged and remains the default)
# ---------------------------------------------------------------------------
_INDENT_RE = re.compile(r'(?m)^([ \t]+)"')


def detect_indent(raw_text, default=2):
    """The two real files use DIFFERENT indent widths today (`.claude/settings.json`
    is 2-space, `hooks/hooks.json` is 1-space) — detected from the file's own first
    indented line rather than hardcoded per filename, so install stays correct if
    either file's house style ever changes."""
    m = _INDENT_RE.search(raw_text)
    return len(m.group(1)) if m else default


def install_into_repo(result, repo_root):
    """Merge ONLY the "hooks" key of each OK'd "settings"/"plugin" target doc into
    the REAL `<repo_root>/.claude/settings.json` / `<repo_root>/hooks/hooks.json` —
    every other top-level key (permissions/statusLine, description, ...) is parsed
    and re-serialized untouched, in its original position (Python dicts preserve
    insertion order; assigning to an EXISTING key never moves it). This is the only
    code in this repo that writes those two files (task rule: the generator is the
    only writer, never a hand edit) and it only ever merges into a file that already
    exists — it never creates `.claude/settings.json` or `hooks/hooks.json` from
    nothing. A target this run did not mark "OK" (SKIP or REFUSED) is left alone in
    the real file — install never partially applies a target its own gates rejected."""
    installed, skipped = [], []
    real_path_for_surface = {
        "settings": os.path.join(repo_root, ".claude", "settings.json"),
        "plugin": os.path.join(repo_root, "hooks", "hooks.json"),
    }
    by_surface = {t["surface"]: t for t in result["targets"]}
    for surface, real_path in real_path_for_surface.items():
        t = by_surface.get(surface)
        if t is None or t["status"] != "OK":
            skipped.append((surface, real_path,
                            t["status"] if t else "MISSING-FROM-REGISTER",
                            (t.get("reason") if t else None) or "no OK'd target to install"))
            continue
        if not os.path.isfile(real_path):
            skipped.append((surface, real_path, "NO-REAL-FILE",
                             "real file does not exist — install merges into an "
                             "existing file only, it never creates one"))
            continue
        with open(real_path, encoding="utf-8") as f:
            raw = f.read()
        existing = json.loads(raw)
        existing["hooks"] = t["doc"]["hooks"]
        indent = detect_indent(raw)
        new_content = json.dumps(existing, indent=indent, ensure_ascii=False,
                                  sort_keys=False) + "\n"
        tmp_path = real_path + ".install.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, real_path)
        installed.append((surface, real_path, t["rows_written"]))
    return {"installed": installed, "skipped": skipped}


def install_report_lines(install_result):
    lines = ["INSTALL (Feature B2.2, --install-root):"]
    for surface, path, rows in install_result["installed"]:
        lines.append(f"  INSTALLED {surface!r} -> {path} ({rows} rows)")
    for surface, path, status, reason in install_result["skipped"]:
        lines.append(f"  SKIPPED {surface!r} -> {path} ({status}: {reason})")
    return lines


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("register", help="path to the input schema-v1 JSONL register")
    p.add_argument("--out", required=True,
                   help="output directory — files are written ONLY here, never into a real "
                        "checkout's .claude/settings.json or hooks/hooks.json")
    p.add_argument("--public-root", default=REPO_ROOT_FROM_SCRIPT,
                   help="public repo root, for resolving public hook paths (default: this "
                        "script's own repo, three directories up)")
    p.add_argument("--private-root", default=DEFAULT_PRIVATE_ROOT,
                   help="private repo root, for resolving private hook paths "
                        "(default: ~/.claude/skills/ClaudeOps)")
    p.add_argument("--cache-root", default=None,
                   help="platform plugin cache root, read-only, for the cache-divergence "
                        "warning only (default: derived from <public-root>/.claude-plugin/"
                        "plugin.json's own version field)")
    p.add_argument("--no-cache", action="store_true",
                   help="skip the cache-divergence check entirely")
    p.add_argument("--severity", choices=("warn", "refuse"), default="warn",
                   help="omission-check severity (Feature B1.4; Enver's ruling, 2026-09-15: "
                        "default WARN for v1). 'warn': name every omission, exit code "
                        "unaffected. 'refuse': the same finding refuses the WHOLE run, "
                        "nothing written — a one-flag escalation, never a code change.")
    p.add_argument("--exemptions", default=None,
                   help="omission-check exemption file (default: omission-exemptions.txt "
                        "next to this script)")
    p.add_argument("--dedup", default=None,
                   help="Feature B2.2 surface-dedup exception file (default: "
                        "surface-dedup.txt next to this script, if it exists)")
    p.add_argument("--install-root", default=None,
                   help="Feature B2.2: ALSO merge the generated 'settings'/'plugin' targets "
                        "into <PATH>/.claude/settings.json and <PATH>/hooks/hooks.json "
                        "(existing files only, other keys untouched). Opt-in; omitting this "
                        "leaves plain --out DIR behavior above unchanged.")
    p.add_argument("--no-caller-lint", action="store_true",
                   help="Feature B1.5w: skip the caller-lint report section entirely. The "
                        "lint is informational (WARN only) and never affects what gets "
                        "written or the exit code either way — this flag only silences it.")
    p.add_argument("--targets", choices=("all", "public"), default="all",
                   help="B3.2 fix, 2026-09-15: default 'all' is UNCHANGED prior behavior — "
                        "a broken path on ANY target (public or private) refuses that "
                        "target and contributes to a non-zero exit code. 'public' is the "
                        "new, opt-in mode check_drift.py's on-commit gate passes: a REFUSED "
                        "PRIVATE target (registrations.json / user-settings.hooks-section."
                        "json) is downgraded to a named, non-blocking WARN and excluded "
                        "from the exit code — the public wiring drift check must not "
                        "depend on the private repo's live disk state on this machine.")
    args = p.parse_args(argv)

    public_root = os.path.abspath(args.public_root)
    private_root = os.path.abspath(os.path.expanduser(args.private_root))
    if args.no_cache:
        cache_root = None
    elif args.cache_root:
        cache_root = os.path.abspath(os.path.expanduser(args.cache_root))
    else:
        cache_root = cache_root_for(public_root)

    result = generate(
        args.register, os.path.abspath(args.out), public_root, private_root, cache_root,
        severity=args.severity, exemptions_path=args.exemptions, dedup_path=args.dedup,
        skip_caller_lint=args.no_caller_lint, targets=args.targets,
    )
    text, exit_code = report(result)
    print(f"generate.py — {args.register} -> {args.out}")
    print(text)

    if args.install_root and exit_code == 0:
        install_result = install_into_repo(result, os.path.abspath(args.install_root))
        print()
        print("\n".join(install_report_lines(install_result)))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
