#!/usr/bin/env python3
"""harvest.py — the register's HARVESTER (Feature B1.2, enforcement-layer Phase 2 plan).

Promotes the harvest half of `records/2026-09-13-phase-1/t2_generation.py` (T2, Phase 1) into a
real tool: walks disk + wiring sources across BOTH repos (public V2 checkout + the private
`egjokaj/ClaudeOps` checkout) and emits a schema-v1 JSONL register (`schema_v1.py` /
`validate_register.py`, both in this folder — Feature B1.1).

Four unit classes (schema v1's `UNIT_TYPES`):

  hook      — a registration entry on any of the 6 live wiring surfaces (T2's original shape,
              unchanged: public settings.json + public hooks/hooks.json + private
              registrations.json + the user's global settings.json, plus the platform plugin
              cache's mirrors of the first two). One row per (repo, path, event, matcher, args).
              Also carries the entry's optional "if" narrowing condition (e.g.
              "Skill(checkin)"), a real Claude Code hook field T2/B1.1/B1.2/B1.3 never
              harvested — found and closed by B2.2 (2026-09-15) the first time this
              register was used to write the real wiring files, not a new capability
              added on purpose (schema-v1.md's "if" section has the incident).
  tool      — every `.py`/`.sh` file under `system/tools/` in either repo, T1's exact governed-dir
              + exempt-test-class rules (`t1_caller_detection.py`), disk-walked.
  skill     — every `.claude/skills/**/SKILL.md` in either repo, `name`/`description` read
              straight off its own frontmatter — no re-summarizing (B1.1 (b)'s "0 hand-annotation"
              rule).
  scheduled — one row per line of the public repo's `system/pulse-config.md` ```jobs``` block.
              All scheduled rows share one `path` (the manifest itself) — Enver's Ruling 5,
              schema-v1.md.

Constraint 0.5 (binding on every task in this plan): **the platform plugin cache is accounted
for, never generated.** This tool only ever READS the cache (to fold its two hook surfaces into a
hook row's `surfaces` list, and to detect content divergence in a caller); it never writes there,
and `repo` is NEVER `"cache"` for any row — a cache-mirrored hook is attributed to `repo: "public"`,
exactly as T2 did.

No re-run of T1/T2 here — this is new code, independently reproducing the shape they proved, not
re-executing their measurement.

Usage:
    python3 harvest.py [--public-root PATH] [--private-root PATH] [--cache-root PATH]
                        [--no-cache] [--out FILE]

Defaults: --public-root = the repo containing this script (three directories up from
`system/register/harvest.py`) · --private-root = `~/.claude/skills/ClaudeOps` · --cache-root =
derived from `<public-root>/.claude-plugin/plugin.json`'s own `version` field (never hardcoded —
T2's own hardcoded `0.3.20` was a portability wart this tool does not repeat). `--no-cache` skips
the two cache surfaces entirely (useful for a scratch/planted-fixture run that has no matching
cache checkout).

With no `--out`, the JSONL register is written to stdout (so it composes in a pipeline) and a
one-line summary goes to stderr; with `--out FILE`, the register is written to FILE and the summary
goes to stdout.
"""
import argparse
import hashlib
import json
import os
import re
import sys

import switch_state  # S1/K1 — sibling module, one shared semantics for the
                     # register-backed switch (see switch_state.py's docstring)

THIS_FILE = os.path.abspath(__file__)
# system/register/harvest.py -> repo root is three levels up.
REPO_ROOT_FROM_SCRIPT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_FILE)))
DEFAULT_PRIVATE_ROOT = os.path.expanduser("~/.claude/skills/ClaudeOps")

TEST_DIR = re.compile(r"/tests?/", re.I)
SCRIPT_EXTS = (".sh", ".py")


# ---------------------------------------------------------------------------
# small shared helpers
# ---------------------------------------------------------------------------
def short_sha(path):
    """T2's mode-12 drift check: short sha256 of a file's bytes, or None if unreadable."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:8]
    except OSError:
        return None


def is_test_class(relpath):
    """T1's exempt-class rule, verbatim (`t1_caller_detection.py`): a file in a tests/ dir, or
    whose basename starts test_/test-/firetest, is EXEMPT from the governed tool set — a test
    invoking its subject does not make the subject called, and a test itself is not a governed
    unit. Merely containing '-test-' elsewhere in the name does NOT exempt it."""
    b = os.path.basename(relpath)
    return bool(
        TEST_DIR.search(relpath)
        or re.match(r"test[_-]", b, re.I)
        or re.match(r"firetest", b, re.I)
    )


def cache_root_for(public_root):
    """Derive the platform plugin cache root from the public repo's OWN declared version —
    never a hardcoded version string (constraint 0.5's cache-accounting rule extends to not
    silently going stale the moment the plugin version bumps)."""
    plugin_json = os.path.join(public_root, ".claude-plugin", "plugin.json")
    try:
        with open(plugin_json, encoding="utf-8") as f:
            version = json.load(f).get("version")
    except (OSError, json.JSONDecodeError):
        return None
    if not version:
        return None
    return os.path.expanduser(f"~/.claude/plugins/cache/lifehack-brain/lifehack-brain/{version}")


def to_repo_path(root, full_path):
    """repo-relative path, forward slashes, one leading slash — schema-v1.md's `path` shape."""
    rel = os.path.relpath(full_path, root)
    return "/" + rel.replace(os.sep, "/")


def base_row(unit_id, unit_type, repo, path, exists, sha):
    """The common envelope every unit type carries (schema_v1.py COMMON_FIELDS), with the
    chaining-seed and cost fields at their honest mechanical defaults: `needs`/`returns` empty
    (nothing has been hand-declared), `cost_bytes`/`cost_ms` null (Phase B4's job, not this one)."""
    return {
        "id": unit_id,
        "type": unit_type,
        "repo": repo,
        "path": path,
        "exists": exists,
        "sha": sha,
        "needs": [],
        "returns": [],
        "cost_bytes": None,
        "cost_ms": None,
    }


# ---------------------------------------------------------------------------
# type: hook — the six wiring surfaces (T2's harvest, promoted verbatim in shape)
# ---------------------------------------------------------------------------
def hook_surfaces(public_root, private_root, cache_root):
    """(surface, path, declared_repo, command-prefix-this-surface-declares) — same six as T2's
    `SURFACES`, generalized to take repo roots as arguments instead of T2's hardcoded `~/lifehack-
    brain` (a portability wart this tool does not repeat: a harvester run from a worktree, not the
    main checkout, must still find the right files)."""
    home = os.path.expanduser("~")
    surfaces = [
        ("settings", f"{public_root}/.claude/settings.json", "public", "${CLAUDE_PROJECT_DIR}"),
        ("plugin", f"{public_root}/hooks/hooks.json", "public", "${CLAUDE_PLUGIN_ROOT}"),
        ("registrations", f"{private_root}/system/hooks/registrations.json", "private",
         "$HOME/.claude/skills/ClaudeOps"),
        ("user", f"{home}/.claude/settings.json", "private", None),
    ]
    if cache_root:
        surfaces.append(("cache-settings", f"{cache_root}/.claude/settings.json", "cache",
                          "${CLAUDE_PROJECT_DIR}"))
        surfaces.append(("cache-plugin", f"{cache_root}/hooks/hooks.json", "cache",
                          "${CLAUDE_PLUGIN_ROOT}"))
    return surfaces


def derive_launch_mode(surfaces):
    """Mechanical mapping from a hook row's raw `surfaces` set to schema
    v1's coarser `launch_mode` axis (RESTORED 2026-09-15, Option G — see
    `schema_v1.LAUNCH_MODES` for the full history/derivation). 0 hand-typed
    values: this only ever reads the same `surfaces` set `harvest_hooks()`
    already built from `hook_surfaces()`'s own names, never a separately
    typed judgment. Cache mirrors (`cache-settings`/`cache-plugin`) are
    deliberately NOT part of this decision — they mirror an already-real
    `settings`/`plugin` row, never decide the axis alone (every combination
    in the live register bears this out: no row has ever been cache-only)."""
    has_settings = "settings" in surfaces
    has_plugin = "plugin" in surfaces
    if has_settings and has_plugin:
        return "both"
    if has_settings:
        return "project"
    if has_plugin:
        return "plugin"
    if surfaces & {"registrations", "user"}:
        return "private"
    raise ValueError(
        f"hook row has no recognized launch-mode surface: {sorted(surfaces)} "
        "— a cache-only or otherwise unmodeled surface set; this is a real "
        "finding (a content divergence the cache-divergence check should "
        "also be seeing), not a case to silently default."
    )


def parse_hook_file(path):
    """Yield (event, matcher, command, statusMessage, if_cond) tuples from one
    registration file. T2's `parse_file`, extended by ONE field, B2.2 (2026-09-15):
    live-writing the real `.claude/settings.json`/`hooks/hooks.json` for the first
    time (B1.3 only ever wrote to a scratch --out dir) surfaced that Claude Code's
    own hook-entry shape carries an OPTIONAL "if" narrowing condition (e.g.
    "Skill(checkin)") that T2/B1.1/B1.2/B1.3 never harvested — dropping a live
    `guard_checkin_needs_project.sh` entry's `if=Skill(checkin)` on regeneration,
    silently widening it to fire on every Skill, not just /checkin. `if_cond` is
    `None` when the key is absent (every other hook entry today)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    hooks = data.get("hooks", {}) if isinstance(data, dict) else {}
    for event, entries in hooks.items():
        for entry in entries:
            matcher = entry.get("matcher", "")
            for h in entry.get("hooks", []):
                yield (event, matcher, h.get("command", ""), h.get("statusMessage", ""),
                       h.get("if"))


def norm_command(cmd, surface_prefix):
    """Strip the surface's OWN declared prefix -> (repo-rel path, args). T2's `norm_command`,
    unchanged: anything not carrying the declared prefix is UNPARSED, itself a finding (e.g. a
    hardcoded absolute path in a file meant to be portable)."""
    s = cmd.strip()
    if surface_prefix and s.startswith(f'bash "{surface_prefix}'):
        rest = s[len(f'bash "{surface_prefix}'):]
        m = re.match(r'([^"]+)"(.*)$', rest)
        if m:
            return m.group(1), m.group(2).strip()
    return None, None


def harvest_hooks(public_root, private_root, cache_root):
    """T2's harvest loop, unchanged in substance, re-shaped into schema-v1 rows. Returns a list
    of dicts; callers are responsible for sorting before serialization (determinism, not this
    function's job)."""
    register = {}
    for surface, path, declared_repo, prefix in hook_surfaces(public_root, private_root, cache_root):
        for event, matcher, cmd, status, if_cond in parse_hook_file(path):
            rel, args = norm_command(cmd, prefix)
            if rel is None:
                rel, args = f"UNPARSED:{cmd[:60]}", ""
            if rel.startswith("UNPARSED"):
                home_repo = declared_repo
            elif prefix == "$HOME/.claude/skills/ClaudeOps":
                home_repo = "private"
            else:
                home_repo = "public"
            key = (home_repo, rel, event, matcher, args)
            e = register.setdefault(key, {
                "repo": home_repo, "path": rel, "event": event, "matcher": matcher,
                "args": args, "status": status, "surfaces": set(), "status_conflicts": set(),
                "if_cond": if_cond, "if_conflicts": set(),
            })
            e["surfaces"].add(surface)
            if status and status != e["status"]:
                e["status_conflicts"].add(status)
            # Same T2-proven pattern as `status` above: the FIRST surface visited
            # (hook_surfaces()'s own fixed order) sets `if_cond`; any surface that
            # disagrees is recorded, never silently overwritten or averaged away.
            if if_cond and if_cond != e["if_cond"]:
                e["if_conflicts"].add(if_cond)
            elif e["if_cond"] is None and if_cond:
                e["if_cond"] = if_cond

    rows = []
    for (home_repo, rel, event, matcher, args), e in register.items():
        root = public_root if home_repo == "public" else private_root
        full = os.path.join(root, rel.lstrip("/"))
        exists = os.path.exists(full)
        sha = short_sha(full) if exists else None
        row = base_row(
            unit_id=f"hook:{home_repo}:{rel}@{event}:{matcher}",
            unit_type="hook", repo=home_repo, path=rel, exists=exists, sha=sha,
        )
        row.update({
            "event": event,
            "matcher": matcher,
            "args": args,
            "status": e["status"],
            "if": e["if_cond"],
            "surfaces": sorted(e["surfaces"]),
            "status_conflicts": sorted(e["status_conflicts"]),
            "launch_mode": derive_launch_mode(e["surfaces"]),
            # B5.2, 2026-09-15 — `group` is a HAND-CURATED chaining field (like
            # `needs`/`returns` above `base_row()`'s own honest-default
            # comment already describes for those two): a fresh harvest has
            # no way to know a maintainer wants N rows to share a dispatcher,
            # so it always mechanically defaults to null here. A maintainer
            # re-applies any `group`/`needs`/`returns` values by hand after
            # running this tool — see system/register/register.jsonl's own
            # git history for exactly that two-step workflow (B5.2).
            "group": None,
            # S1/K1, 2026-09-16 — `state`/`expiry` are HAND-CURATED
            # ENFORCEMENT fields (the register-backed switch), NOT disk facts
            # a fresh harvest can derive: every row defaults to active/null
            # here, and main() then carries any declared, unexpired suspension
            # FORWARD from the committed register via
            # carry_forward_switch_state(). Unlike `group`, a suspension LOST
            # to re-harvest silently re-arms a guard the lane declared off —
            # so preservation is mechanical, never a re-apply-by-hand step.
            "state": "active",
            "expiry": None,
        })
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# S1/K1 — carry switch declarations forward from the committed register
# ---------------------------------------------------------------------------
def carry_forward_switch_state(rows, prior_register_path, today=None):
    """`state`/`expiry` are hand-curated ENFORCEMENT declarations (S1/K1,
    2026-09-16), not disk facts: a fresh harvest can never derive them, and a
    suspension LOST to re-harvest would silently re-arm a guard the lane
    declared off (and the on-commit drift gate would then read the lane's
    wiring as drift — the exact failure Enver's binding constraint names).
    So each prior hook row's suspension is carried onto the fresh rows, keyed
    by the row's synthetic `id`, from the COMMITTED register — NOT the --out
    path (CI harvests to $RUNNER_TEMP; reading the committed file is also what
    keeps the freshness byte-diff stable across a declared suspension).

    One direction is deliberately NOT carried: an EXPIRED suspension drops
    back to the active/null default (self-heal, protection re-armed) and is
    NAMED in the return value's `dropped` list for the caller to ALARM — a
    silent drop would be the "forgotten switch" failure the expiry exists to
    detect. A missing/unreadable prior register is NOT an error (first-ever
    harvest is a legal state): every row keeps its defaults.

    Returns (carried, dropped): lists of (row_id, expiry) tuples."""
    today = switch_state.resolve_today() if today is None else today
    prior = {}
    try:
        with open(prior_register_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    prow = json.loads(line)
                except json.JSONDecodeError:
                    continue  # a malformed prior line carries nothing
                if prow.get("type") == "hook" and prow.get("state") == "suspended":
                    prior[prow.get("id")] = prow.get("expiry")
    except OSError:
        return [], []

    carried, dropped = [], []
    for row in rows:
        if row.get("type") != "hook":
            continue
        expiry = prior.get(row.get("id"))
        if expiry is None:
            continue
        verdict = switch_state.classify(
            {"type": "hook", "state": "suspended", "expiry": expiry}, today)
        if verdict == "honored":
            row["state"] = "suspended"
            row["expiry"] = expiry
            carried.append((row["id"], expiry))
        elif verdict == "expired":
            dropped.append((row["id"], expiry))
        # an unparseable prior expiry classifies "active": leave the defaults
        # and do NOT carry — a malformed suspension must never silently extend
    return carried, dropped


# ---------------------------------------------------------------------------
# type: tool — system/tools/, both repos, T1's exact governed/exempt rules
# ---------------------------------------------------------------------------
def harvest_tools(public_root, private_root):
    rows = []
    for repo, root in (("public", public_root), ("private", private_root)):
        base = os.path.join(root, "system", "tools")
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for f in sorted(filenames):
                if f.endswith(".bak") or f.endswith(".pyc"):
                    continue
                if not f.endswith(SCRIPT_EXTS):
                    continue
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, root)
                if is_test_class(rel):
                    continue  # exempt class (T1) — a test fixture is not a governed unit
                path = to_repo_path(root, full)
                language = "py" if f.endswith(".py") else "sh" if f.endswith(".sh") else "other"
                row = base_row(
                    unit_id=f"tool:{repo}:{path}", unit_type="tool", repo=repo, path=path,
                    exists=True, sha=short_sha(full),
                )
                row["language"] = language
                rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# type: skill — .claude/skills/**/SKILL.md, both repos
# ---------------------------------------------------------------------------
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def frontmatter_body(text):
    m = FRONTMATTER_RE.match(text)
    return m.group(1) if m else ""


def frontmatter_field(body, key):
    """Read one `key: value` line straight off a frontmatter body — no re-summarizing (B1.1's
    0-hand-annotation rule). Handles a double- or single-quoted scalar (with \\" escapes, the
    convention this repo's SKILL.md files use) or a bare unquoted scalar. Does NOT attempt a
    block scalar (`|`/`>`) — no field this harvester reads (`skill`, `name`, `description`) uses
    one in this repo today; a block-scalar description would need YAML, a dependency this repo
    does not carry (constraint 0.5)."""
    m = re.search(rf"(?m)^{re.escape(key)}:[ \t]*(.*)$", body)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] == val[-1] == '"':
        return val[1:-1].replace('\\"', '"')
    if len(val) >= 2 and val[0] == val[-1] == "'":
        return val[1:-1]
    return val


def harvest_skills(public_root, private_root):
    rows = []
    for repo, root in (("public", public_root), ("private", private_root)):
        base = os.path.join(root, ".claude", "skills")
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            if "SKILL.md" not in filenames:
                continue
            full = os.path.join(dirpath, "SKILL.md")
            rel = os.path.relpath(full, root)
            try:
                with open(full, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            body = frontmatter_body(text)
            name = frontmatter_field(body, "skill") or frontmatter_field(body, "name") or ""
            description = frontmatter_field(body, "description") or ""
            path = to_repo_path(root, full)
            row = base_row(
                unit_id=f"skill:{repo}:{path}", unit_type="skill", repo=repo, path=path,
                exists=True, sha=short_sha(full),
            )
            row["name"] = name
            row["description"] = description
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# type: scheduled — one manifest, one ```jobs``` fenced block, public repo only
# ---------------------------------------------------------------------------
JOBS_BLOCK_RE = re.compile(r"```jobs\r?\n(.*?)\r?\n```", re.S)


def harvest_scheduled(public_root):
    manifest = os.path.join(public_root, "system", "pulse-config.md")
    rows = []
    if not os.path.isfile(manifest):
        return rows
    with open(manifest, encoding="utf-8") as f:
        text = f.read()
    path = to_repo_path(public_root, manifest)
    exists = True
    sha = short_sha(manifest)
    for block in JOBS_BLOCK_RE.findall(text):
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|", 3)]
            if len(parts) < 4:
                continue  # malformed row — not this tool's job to repair (B1.4's lint, later)
            name, enabled, interval, command = parts
            try:
                interval_seconds = int(interval)
            except ValueError:
                interval_seconds = None
            row = base_row(
                unit_id=f"scheduled:{name}", unit_type="scheduled", repo="public", path=path,
                exists=exists, sha=sha,
            )
            row.update({
                "schedule_name": name,
                "enabled": enabled,
                "interval_seconds": interval_seconds,
                "command": command,
            })
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def _sort_key(row):
    return (
        row.get("type", ""), row.get("repo", ""), row.get("path", ""),
        row.get("event", ""), row.get("matcher", ""), row.get("args", ""),
        row.get("schedule_name", ""),
    )


def harvest_all(public_root, private_root, cache_root):
    rows = []
    rows.extend(harvest_hooks(public_root, private_root, cache_root))
    rows.extend(harvest_tools(public_root, private_root))
    rows.extend(harvest_skills(public_root, private_root))
    rows.extend(harvest_scheduled(public_root))
    rows.sort(key=_sort_key)
    return rows


def write_jsonl(rows, fileobj):
    for row in rows:
        fileobj.write(json.dumps(row, sort_keys=True, ensure_ascii=False))
        fileobj.write("\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--public-root", default=REPO_ROOT_FROM_SCRIPT,
                   help="public repo root (default: this script's own repo)")
    p.add_argument("--private-root", default=DEFAULT_PRIVATE_ROOT,
                   help="private repo root (default: ~/.claude/skills/ClaudeOps)")
    p.add_argument("--cache-root", default=None,
                   help="platform plugin cache root (default: derived from "
                        "<public-root>/.claude-plugin/plugin.json's version)")
    p.add_argument("--no-cache", action="store_true",
                   help="skip the two cache surfaces entirely (e.g. a scratch fixture run)")
    p.add_argument("--out", default=None, help="write JSONL here instead of stdout")
    args = p.parse_args(argv)

    public_root = os.path.abspath(args.public_root)
    private_root = os.path.abspath(os.path.expanduser(args.private_root))
    if args.no_cache:
        cache_root = None
    elif args.cache_root:
        cache_root = os.path.abspath(os.path.expanduser(args.cache_root))
    else:
        cache_root = cache_root_for(public_root)

    rows = harvest_all(public_root, private_root, cache_root)

    # S1/K1 (2026-09-16) — carry the register-backed switch's declarations
    # forward from the COMMITTED register (never the --out path: CI harvests
    # to $RUNNER_TEMP, and reading the committed file keeps the freshness
    # byte-diff stable across a declared suspension). Expired suspensions
    # drop to active/null and are ALARMED, not silently carried — the
    # self-heal is the design.
    carried, dropped = carry_forward_switch_state(
        rows, os.path.join(public_root, "system", "register", "register.jsonl"))
    for rid, expiry in carried:
        print(f"  NOTICE — suspension carried forward (still honored until "
              f"{expiry}): {rid}", file=sys.stderr)
    for rid, expiry in dropped:
        print(f"  ⛔ ALARM — suspension EXPIRED ({expiry}) and was NOT carried "
              f"forward; row is ACTIVE again (protection re-armed): {rid}. "
              f"Re-declare with a fresh expiry in system/register/register.jsonl "
              f"if the lift is still intended.", file=sys.stderr)

    by_type = {}
    for row in rows:
        by_type[row["type"]] = by_type.get(row["type"], 0) + 1
    broken = sum(1 for r in rows if not r["exists"])
    summary = (
        f"harvest.py — {len(rows)} rows "
        f"(hook={by_type.get('hook', 0)} tool={by_type.get('tool', 0)} "
        f"skill={by_type.get('skill', 0)} scheduled={by_type.get('scheduled', 0)}) "
        f"· broken (exists=false): {broken} "
        f"· public={public_root} private={private_root} cache={cache_root or '(none)'}"
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            write_jsonl(rows, f)
        print(summary)
    else:
        write_jsonl(rows, sys.stdout)
        print(summary, file=sys.stderr)


if __name__ == "__main__":
    main()
