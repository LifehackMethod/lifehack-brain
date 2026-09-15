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

Extension points for B1.4 (the omission check) and B1.5 (the caller lint) —
NOT implemented here, per this task's scope:
  - B1.4 would add a Phase 0.5 between the schema gate and the write gate:
    scan `system/hooks`, `system/tools` in both repos for files with NO
    matching register row (the inverse of this tool's "does the row's path
    exist" check) and warn/refuse per Enver's ruling. `load_register()`
    below already returns every row with its line number, which is exactly
    what an omission-diff needs to cross-reference against a fresh disk
    walk (reusing `harvest.harvest_tools`/`harvest_skills`'s own walk logic).
  - B1.5 would add a read-only lint pass over the same loaded rows using
    `needs`/`returns` plus T1's caller classes (not carried by schema v1
    today) to report units with no caller surface — a report function next
    to `cache_divergence_warnings()` below, not a new gate, since T1 "lists;
    it never judges."

Usage:
    python3 generate.py <register.jsonl> --out DIR
        [--public-root PATH] [--private-root PATH]
        [--cache-root PATH | --no-cache]

Writes only inside --out (never `.claude/settings.json` / `hooks/hooks.json`
in a real checkout — that overwrite is explicitly out of scope for this task
and stays a human/B3-runner decision). No new dependency: stdlib only, plus
this folder's own `schema_v1.py` / `validate_register.py` / `harvest.py`.
"""
import argparse
import json
import os
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

# Surface -> (form, repo_filter, output filename). This is TODAY's overlapping
# wiring shape (the double registration T2 proved) — Feature B2.2 (later, NOT
# this task) swaps this table for a non-overlapping split; nothing else in
# this module needs to change for that, which is the point of keeping it as
# one small piece of data instead of inlined per-target logic below.
SURFACE_TARGETS = (
    ("settings",      "settings",      "public",  "settings.hooks-section.json"),
    ("plugin",        "plugin",        "public",  "hooks.json"),
    ("registrations", "registrations", "private", "registrations.json"),
    ("user",          "user",          "private", "user-settings.hooks-section.json"),
)

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
        h = {"type": "command", "command": emit_command(row["path"], row["args"], form)}
        if row["status"]:
            h["statusMessage"] = row["status"]
        grp["hooks"].append(h)
    return {"hooks": hooks}


def rows_for_surface(hook_rows, surface, repo_filter):
    """hook_rows: [(line_no, row)]. Returns the matching subset, same shape."""
    return [
        (line_no, row) for line_no, row in hook_rows
        if row.get("repo") == repo_filter and surface in (row.get("surfaces") or [])
    ]


def sort_key(row):
    return (row["event"], row["matcher"], row["path"], row["args"])


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
def generate(register_path, out_dir, public_root, private_root, cache_root):
    """Returns a result dict; never raises for an ordinary refusal (schema or
    broken-path) — those are reported in the result, and the caller (main())
    decides the exit code. Only writes files after every gate that applies
    to that specific file has passed, via temp-file + os.replace (atomic
    rename on the same filesystem)."""
    entries = load_register(register_path)

    problems = schema_check(entries)
    if problems:
        return {
            "schema_ok": False,
            "schema_problems": problems,
            "targets": [],
            "warnings": [],
        }

    hook_rows = [(ln, row) for ln, row, _ in entries if row.get("type") == "hook"]

    os.makedirs(out_dir, exist_ok=True)

    target_results = []
    for surface, form, repo_filter, filename in SURFACE_TARGETS:
        matched = rows_for_surface(hook_rows, surface, repo_filter)
        if not matched:
            target_results.append({
                "filename": filename, "surface": surface, "status": "SKIP",
                "reason": "no rows registered on this surface", "broken": [],
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
            })
            continue
        ordered = sorted((row for _, row in matched), key=sort_key)
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
            "path": final_path,
        })

    warnings = cache_divergence_warnings(hook_rows, public_root, cache_root)

    return {
        "schema_ok": True,
        "schema_problems": [],
        "targets": target_results,
        "warnings": warnings,
    }


def report(result):
    lines = []
    if not result["schema_ok"]:
        lines.append("REFUSED: register fails schema v1 validation — writing NOTHING (no target touched).")
        for line_no, errs in result["schema_problems"]:
            for e in errs:
                lines.append(f"  {e}")
        return "\n".join(lines), 1

    any_refused = False
    for t in result["targets"]:
        if t["status"] == "OK":
            lines.append(f"  {t['filename']:<38} OK       ({t['rows_written']} rows) -> {t['path']}")
        elif t["status"] == "SKIP":
            lines.append(f"  {t['filename']:<38} SKIP     ({t['reason']})")
        else:
            any_refused = True
            lines.append(f"  {t['filename']:<38} REFUSED  ({t['reason']}) — nothing written for this target")
            for ln, row in t["broken"]:
                lines.append(
                    f"      line {ln}: id={row.get('id')!r} path={row.get('path')!r} "
                    f"repo={row.get('repo')} event={row.get('event')} matcher={row.get('matcher')!r}"
                )

    if result["warnings"]:
        lines.append("")
        lines.append("WARNINGS (cache-divergence, non-blocking):")
        for w in result["warnings"]:
            lines.append(f"  {w}")

    exit_code = 1 if any_refused else 0
    return "\n".join(lines), exit_code


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
    args = p.parse_args(argv)

    public_root = os.path.abspath(args.public_root)
    private_root = os.path.abspath(os.path.expanduser(args.private_root))
    if args.no_cache:
        cache_root = None
    elif args.cache_root:
        cache_root = os.path.abspath(os.path.expanduser(args.cache_root))
    else:
        cache_root = cache_root_for(public_root)

    result = generate(args.register, os.path.abspath(args.out), public_root, private_root, cache_root)
    text, exit_code = report(result)
    print(f"generate.py — {args.register} -> {args.out}")
    print(text)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
