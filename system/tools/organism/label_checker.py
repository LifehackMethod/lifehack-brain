#!/usr/bin/env python3
"""
label_checker.py — the honesty-label checker (PORTED 2026-08-14 from claudeops-config's
system/tools/organism/label_checker.py, organism-audit Feature 1.5).

WHAT: For each guard `label_manifest.yaml` CLAIMS is enforced, this FIRES the named hook
against a SYNTHETIC violation and asserts it actually blocks (exit 2, or the honored
`{"decision":"block"}` forms — see `block_verdict()`). Registration in settings.json is
NOT proof — a hook can be registered and do nothing. This is the machine-computed half of
every LIVE/PARTIAL/TARGET label; without it a label is hand-typed prose in a machine
costume.

LABELS (computed, never asserted):
  LIVE    — the guard is git-tracked AND registered in the git-tracked settings.json AND
            fires + blocks (exit 2) on EVERY synthetic violation AND lets EVERY allow-case
            through (exit 0). A real, discriminating control.
  PARTIAL — the guard EXISTS on disk but is not fully enforcing: not git-tracked, or not
            registered, or a violation slipped through (didn't block), or an allow-case was
            wrongly blocked. Built, but its label may not be trusted as LIVE.
  TARGET  — the guard script does not exist yet (declared intent, not built).

DOWNGRADE: if the manifest CLAIMS `LIVE` but the computed label is lower, that is a
label-integrity failure — the checker exits non-zero and names it.

SAFETY: synthetic violations are inert payloads (a fake WebFetch URL, a non-existent
external path). The gate blocks BEFORE anything runs, so firing it is side-effect-free.

SOURCE OF TRUTH: reads the GIT-TRACKED settings.json — `.claude/settings.json` in THIS
repo's layout (the donor kept it at `system/reference/settings.json`; this repo's actual
hooks live at `.claude/settings.json`, confirmed against `citation_lint.py`'s own
`settings_rel = ".claude/settings.json"` and every ported hook's own header) — never a
machine-local copy. A guard registered only on one machine is PARTIAL by design.

WHAT CHANGED IN THIS PORT (generalisation, not a redesign):
  1. SETTINGS moved from `system/reference/settings.json` (donor path, absent here) to
     `.claude/settings.json` (this repo's real, git-tracked settings file).
  2. `REPO` is exported into the process environment right after it is resolved, so a
     manifest payload can write `$REPO/...` instead of a hardcoded clone folder name —
     the donor manifest assumed the clone sat at `$HOME/claudeops-config`, which is a
     personal, single-machine assumption this product cannot make (a student's clone can
     live anywhere, named anything). `expand()` already ran every payload through
     `os.path.expandvars`, so this is additive: any payload written before this change
     that used a literal `$HOME`/`~` still works exactly as before.
  3. `DEFAULT_ELEMENTS_DIR`/`DEFAULT_INDEX` point at `system/organism/elements` /
     `system/organism/manual.md`. ✅ CORRECTED 2026-08-15: ~~the donor's own self-documentation
     apparatus, which does not exist in this repo (confirmed absent)~~ — Phase 9 landed that
     tree HERE. `system/organism/` now holds `manual.md`, `map-format-specs.md` and 42
     `elements/*.md`, so both defaults resolve and `cmd_write_labels` has a real target.
     ⚠ This correction matters beyond tidiness: `system/hooks/guard_organism_map.sh` (shipped
     2026-08-15) REDIRECTS a blocked writer to `label_checker.py write-labels` as the sanctioned
     way to set a maturity label. Anyone following that redirect lands on this docstring, and it
     was telling them the directory did not exist. The degrade path below still stands as a
     genuine fallback; it is no longer the expected case.
     `check`/`selftest` never touch that path at all, so the fire-test engine is fully
     functional with or without an elements/ directory present.

Usage:
  label_checker.py check [--manifest PATH] [--json] [--guard ID]
  label_checker.py selftest        # who-watches-the-watcher: plant an inert guard, assert PARTIAL
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# ── locate the repo root (git-canonical clone) ──────────────────────────────
def repo_root() -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    # fallback: system/tools/organism/label_checker.py -> repo is parents[3]
    return Path(__file__).resolve().parents[3]

REPO = repo_root()
# Exported so a manifest payload can write `$REPO/...` and get the ACTUAL live checkout
# path via expand()'s os.path.expandvars — never a hardcoded clone folder name. See the
# module docstring's "WHAT CHANGED" item 2.
os.environ["REPO"] = str(REPO)

# Exported for the SAME payload-expansion reason as REPO: the tasks-readonly-list-guard protects
# whatever list <notes>/config/cal.md names as `goals_tasklist` — personal config no repo file may
# hardcode. Its violation case writes `$GOALS_TASKLIST` and fires against the REAL protected id on
# a configured install. On an UNCONFIGURED install this exports "" and the payload carries an empty
# tasklist — which the guard must fail-closed on anyway (an omitted/empty list may resolve to the
# protected default), so the case tests something true on every install. Added 2026-08-27: the old
# fixture id (`SYNTHETIC_GOALS_TASKLIST_ID`) could never equal anyone's configured id, so the case
# could never block anywhere and rendered a healthy guard as a permanent RED downgrade.
try:
    sys.path.insert(0, str(REPO / "shared"))
    import cal_config as _cal_config
    os.environ["GOALS_TASKLIST"] = str(_cal_config.load().get("goals_tasklist", "") or "")
except Exception:
    os.environ["GOALS_TASKLIST"] = ""

SETTINGS = REPO / ".claude" / "settings.json"
DEFAULT_MANIFEST = REPO / "system" / "tools" / "organism" / "label_manifest.yaml"
DEFAULT_INDEX = REPO / "system" / "organism" / "manual.md"
DEFAULT_ELEMENTS_DIR = REPO / "system" / "organism" / "elements"

# label ordering for downgrade detection (higher = more enforced)
RANK = {"TARGET": 0, "PARTIAL": 1, "LIVE": 2}


def expand(s: str) -> str:
    """Expand ~, $HOME and $REPO (see module docstring) in a payload path so synthetic
    paths resolve on any machine, at wherever this repo actually lives."""
    return os.path.expanduser(os.path.expandvars(s)) if isinstance(s, str) else s


def expand_payload(obj):
    """Recursively expand ~/$HOME/$REPO inside a payload dict (file_path, url, command, ...)."""
    if isinstance(obj, dict):
        return {k: expand_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_payload(v) for v in obj]
    return expand(obj)


def git_tracked(path: Path) -> bool:
    """True iff `path` is tracked by git (travels by pull; machine-local files are not)."""
    try:
        rel = path.relative_to(REPO)
    except ValueError:
        return False
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(rel)],
        cwd=REPO, capture_output=True, text=True, timeout=10,
    )
    return out.returncode == 0


def load_settings() -> dict:
    if not SETTINGS.exists():
        return {}
    try:
        return json.loads(SETTINGS.read_text())
    except Exception:
        return {}


def is_registered(settings: dict, script_name: str, wanted: list) -> tuple:
    """
    Is `script_name` (basename) wired into the git-tracked settings.json for EVERY
    (event, matcher) in `wanted`? Returns (ok, missing_list).
    `wanted` entries: {"event": "PreToolUse", "matcher": "Bash"}. A matcher of "" or
    absent matches any entry under that event.

    ⚠ PORT FIX (2026-08-14), found by RUNNING this against this repo's real settings.json,
    not assumed: the donor registered one hook under several SEPARATE matcher entries (one
    row for "Bash", one for "WebFetch", one for "WebSearch", ...), and this manifest's own
    `registered:` list already carried a combined form too ("Write|Edit", "Bash|Write|Edit")
    for a hook the donor registered as one row with a combined matcher. This repo's
    settings.json instead consolidates EVERY matcher for one hook into a SINGLE
    pipe-delimited entry (e.g. "Bash|WebFetch|WebSearch|Read|Grep|Glob", or "Bash|Write|Edit").
    The donor's exact-string comparison (`em != matcher`) matched neither shape correctly
    once the registered side became a combined string. Fixed by treating BOTH the wanted
    matcher and the registered matcher as pipe-delimited SETS and requiring the wanted set be
    a SUBSET of the registered set — this is a strict widening: a single wanted matcher
    ("Bash") against a single registered matcher ("Bash") still matches exactly as the
    donor's exact-match did (a 1-element subset check), and every combined shape on either
    side now also resolves correctly.
    """
    hooks = settings.get("hooks", {})
    missing = []
    for w in wanted:
        event = w.get("event", "")
        matcher = w.get("matcher", "")
        wanted_parts = {p.strip() for p in matcher.split("|")} if matcher else set()
        found = False
        for entry in hooks.get(event, []):
            em = entry.get("matcher", "")
            if wanted_parts:
                em_parts = {p.strip() for p in em.split("|")} if em else set()
                if not wanted_parts.issubset(em_parts):
                    continue
            for hk in entry.get("hooks", []):
                if script_name in hk.get("command", ""):
                    found = True
                    break
            if found:
                break
        if not found:
            missing.append(f"{event}[{matcher or '*'}]")
    return (len(missing) == 0, missing)


BLOCK_JSON = re.compile(r'"decision"\s*:\s*"block"')


def fire(script_abs: Path, payload, raw_stdin=None) -> tuple:
    """Fire the hook the way Claude Code delivers it: faithful JSON on stdin.
    Returns (rc, stdout, stderr).

    `raw_stdin` sends bytes VERBATIM instead of json.dumps(payload) — the only way to
    fire-test a guard's FAIL-CLOSED-on-unparseable-input claim, which by definition
    cannot be expressed as a well-formed payload dict. A guard that claims to fail
    closed on garbage must be provable on garbage.

    (NEVER echo — an echo'd \\n mangles the JSON and fail-opens, faking a pass.)"""
    body = raw_stdin if raw_stdin is not None else json.dumps(expand_payload(payload))
    proc = subprocess.run(
        ["bash", str(script_abs)],
        input=body, capture_output=True, text=True, timeout=30,
    )
    return (proc.returncode, proc.stdout, proc.stderr)


def block_verdict(rc: int, out: str, err: str) -> tuple:
    """
    Did this fire actually BLOCK, per the real Claude Code PreToolUse contract
    (`system/hook-contract.md` -> "Output to block")? Returns (blocked, note).

    HONORED block signals — either one is a real block:
      · exit 2                      -> deny text on stderr is shown to the model (house standard)
      · {"decision":"block"} on STDOUT with a non-zero exit -> also honored

    THE DARK TRAP (the whole reason this is a function and not `rc == expected`):
      · {"decision":"block"} on STDERR with exit 1 -> NEITHER channel is read.
        The guard looks like it blocks, prints a righteous deny message, and is
        SILENTLY DARK. A checker that only compares exit codes scores this a PASS
        and stamps the map LIVE — manufacturing exactly the false-green this whole
        project exists to kill.
    """
    if rc == 2:
        return (True, "")
    if rc != 0 and BLOCK_JSON.search(out or ""):
        return (True, "")
    if rc != 0 and BLOCK_JSON.search(err or ""):
        return (False, "SILENTLY DARK: deny JSON on STDERR with a non-2 exit — neither "
                       "channel is read by Claude Code, so this guard does NOT block "
                       "(hook-contract.md). Use stderr+exit 2, or the JSON on stdout.")
    return (False, "")


def evaluate(guard: dict) -> dict:
    """Compute a guard's honest label + the evidence behind it."""
    gid = guard.get("id", "?")
    claim = guard.get("label_claim", "LIVE")
    script_rel = guard.get("script", "")
    script_abs = (REPO / script_rel) if script_rel else None
    expect = int(guard.get("expect_block_exit", 2))
    result = {
        "id": gid, "claim": claim, "script": script_rel,
        "checks": {}, "label": None, "reasons": [],
    }

    # TARGET — not built yet
    if not script_rel or not script_abs.exists():
        result["label"] = "TARGET"
        result["reasons"].append("script does not exist (declared intent, not built)")
        return result

    checks = result["checks"]

    # git-tracked?
    tracked = git_tracked(script_abs)
    checks["git_tracked"] = tracked
    if not tracked:
        result["reasons"].append("script is NOT git-tracked (won't travel to another machine)")

    # registered in the git-tracked settings.json?
    settings = load_settings()
    wanted = guard.get("registered", [])
    reg_ok, missing = (True, [])
    if wanted:
        reg_ok, missing = is_registered(settings, script_abs.name, wanted)
        checks["registered"] = reg_ok
        if not reg_ok:
            result["reasons"].append(f"not registered for: {', '.join(missing)}")
    else:
        checks["registered"] = None  # nothing claimed

    # fire every synthetic violation — must actually BLOCK per the hook contract
    # (exit 2, OR decision:block on stdout with a non-zero exit — NOT a bare exit code
    # match, which would rubber-stamp the stderr+exit-1 dark trap).
    blocks_ok = True
    for v in guard.get("violations", []):
        rc, out, err = fire(script_abs, v.get("payload", v), v.get("raw_stdin"))
        blocked, note = block_verdict(rc, out, err)
        blocks_ok = blocks_ok and blocked
        if not blocked:
            desc = v.get("desc", json.dumps(v.get("payload", v))[:60])
            result["reasons"].append(
                f"violation NOT blocked (exit {rc}): {desc}" + (f" — {note}" if note else ""))
    checks["blocks_violations"] = blocks_ok

    # fire every allow-case — must pass (exit 0); proves the guard discriminates
    allows_ok = True
    for a in guard.get("allow", []):
        rc, out, err = fire(script_abs, a.get("payload", a), a.get("raw_stdin"))
        ok = (rc == 0)
        allows_ok = allows_ok and ok
        if not ok:
            desc = a.get("desc", json.dumps(a.get("payload", a))[:60])
            result["reasons"].append(f"allow-case wrongly blocked (exit {rc}, want 0): {desc}")
    checks["allows_pass"] = allows_ok

    # LIVE iff every applicable check is true
    live = tracked and reg_ok and blocks_ok and allows_ok
    result["label"] = "LIVE" if live else "PARTIAL"
    if live:
        result["reasons"] = ["git-tracked + registered + blocks every violation + passes every allow"]
    return result


def load_manifest(path: Path) -> dict:
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            print("ERROR: pyyaml not available; use a .json manifest", file=sys.stderr)
            sys.exit(3)
        return yaml.safe_load(text)
    return json.loads(text)


def cmd_check(args) -> int:
    manifest_path = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 3
    manifest = load_manifest(manifest_path)
    guards = manifest.get("guards", [])
    if args.guard:
        guards = [g for g in guards if g.get("id") == args.guard]
        if not guards:
            print(f"ERROR: no guard with id={args.guard}", file=sys.stderr)
            return 3

    results = [evaluate(g) for g in guards]

    # a downgrade = the manifest claims a HIGHER label than we could verify
    downgrades = [r for r in results if RANK[r["label"]] < RANK[r["claim"]]]

    if args.json:
        print(json.dumps({"results": results,
                          "downgrades": [r["id"] for r in downgrades]}, indent=2))
    else:
        print(f"honesty-label checker — {len(results)} guard(s) · settings={SETTINGS.relative_to(REPO)}")
        print("─" * 72)
        for r in results:
            flag = ""
            if RANK[r["label"]] < RANK[r["claim"]]:
                flag = f"  ⚠ DOWNGRADE (claimed {r['claim']})"
            print(f"  {r['label']:8} {r['id']}{flag}")
            for reason in r["reasons"]:
                print(f"           └ {reason}")
        print("─" * 72)
        if downgrades:
            print(f"⚠ {len(downgrades)} label DOWNGRADE(S): " +
                  ", ".join(r["id"] for r in downgrades))
        else:
            print("✓ every claimed label verified against live behavior")

    return 1 if downgrades else 0


def cmd_selftest(args) -> int:
    """
    Who-watches-the-watcher. Plant a KNOWN-INERT guard (always exit 0), claim it LIVE,
    and assert the checker refuses to rubber-stamp it — it must compute PARTIAL. If the
    checker ever labels an inert guard LIVE, the checker itself is silently broken.
    """
    with tempfile.TemporaryDirectory() as td:
        inert = Path(td) / "inert_guard.sh"
        inert.write_text("#!/bin/bash\n# always allows — a guard that enforces NOTHING\nexit 0\n")
        inert.chmod(0o755)

        guard = {
            "id": "selftest-inert-guard",
            "label_claim": "LIVE",
            "script": str(inert),            # absolute path; not under REPO -> also not git-tracked
            "registered": [],                # claim nothing, so ONLY the fire-test can fail it
            "violations": [
                {"desc": "any payload should be blocked by a real guard",
                 "payload": {"tool_name": "WebFetch", "tool_input": {"url": "http://x"}}}
            ],
            "expect_block_exit": 2,
        }
        # evaluate() uses REPO-relative paths; an absolute /tmp path isn't under REPO,
        # so patch it to run against the absolute script directly.
        r = _evaluate_abs(guard, inert)

        ok = (r["label"] == "PARTIAL")
        print("SELF-TEST — plant an inert guard (always exit 0), claim LIVE:")
        print(f"  computed label = {r['label']}   (expected PARTIAL)")
        for reason in r["reasons"]:
            print(f"    └ {reason}")
        if ok:
            print("✓ PASS — the checker refused to rubber-stamp an inert guard.")
            return 0
        print("✗ FAIL — the checker labeled an INERT guard as "
              f"{r['label']}. The checker itself is broken.")
        return 1


def _evaluate_abs(guard: dict, script_abs: Path) -> dict:
    """evaluate() variant for a script given by ABSOLUTE path (used by selftest)."""
    expect = int(guard.get("expect_block_exit", 2))
    result = {"id": guard["id"], "claim": guard["label_claim"],
              "script": str(script_abs), "checks": {}, "label": None, "reasons": []}
    if not script_abs.exists():
        result["label"] = "TARGET"
        result["reasons"].append("script does not exist")
        return result
    tracked = git_tracked(script_abs)           # /tmp script -> False (correctly)
    if not tracked:
        result["reasons"].append("script is NOT git-tracked")
    blocks_ok = True
    for v in guard.get("violations", []):
        rc, out, err = fire(script_abs, v.get("payload", v), v.get("raw_stdin"))
        blocked, note = block_verdict(rc, out, err)
        if not blocked:
            blocks_ok = False
            result["reasons"].append(
                f"violation NOT blocked (exit {rc}): {v.get('desc', '')}"
                + (f" — {note}" if note else ""))
    live = tracked and blocks_ok
    result["label"] = "LIVE" if live else "PARTIAL"
    return result


def cmd_write_labels(args) -> int:
    """
    Write each fire-tested guard's computed label INTO its element file
    (`system/organism/elements/<name>.md`) — updating ONLY `maturity_label:` (frontmatter +
    the `## AUTO-COMPUTED` line); never the human `## AUTHORED` block.

    ⚠ THIS REPO HAS NO `system/organism/elements/` DIRECTORY (confirmed absent — the
    donor's own self-documentation apparatus is not part of this port). This command
    degrades honestly: it reports "manifest or elements dir not found" and returns 3
    rather than crashing or inventing a location. `check`/`selftest` above never touch
    this path at all, so the fire-test engine itself works fully with no elements/ dir.

    TWO RULES, both inherited from the donor:

    1. WEAKEST-WINS. Several guards may back ONE element. That element's computed label is
       the WEAKEST of them — one dark guard drags the element down rather than being
       outvoted by healthy siblings. Silently letting the last guard win would print a
       label the element has not earned.

    2. NO SECOND SCOREBOARD. This command does NOT print a coverage percentage — only
       ACTIONABLE gaps: which guards reach no element, and which elements the writer
       cannot govern.
    """
    manifest_path = Path(args.manifest) if args.manifest else DEFAULT_MANIFEST
    elements_dir = Path(args.elements) if args.elements else DEFAULT_ELEMENTS_DIR
    if not manifest_path.exists() or not elements_dir.exists():
        print(f"ERROR: manifest or elements dir not found ({manifest_path}, {elements_dir})", file=sys.stderr)
        return 3
    manifest = load_manifest(manifest_path)

    # index every element file by its `element:` frontmatter slug
    by_slug = {}
    for p in sorted(elements_dir.glob("*.md")):
        m = re.search(r"^element:\s*(.+)$", p.read_text(), re.M)
        if m:
            by_slug[m.group(1).strip()] = p

    # RULE 1 — fold every guard onto its element, weakest label wins
    per_element = {}   # slug -> {"label": str, "guards": [ids]}
    unmapped = []      # guards that are fire-proven but reach no element file
    for guard in manifest.get("guards", []):
        gid = guard.get("id")
        computed = evaluate(guard)["label"]
        if gid not in by_slug:
            unmapped.append(f"{gid} → {computed}")
            continue
        cur = per_element.get(gid)
        if cur is None or RANK[computed] < RANK[cur["label"]]:
            per_element[gid] = {"label": computed, "guards": (cur or {}).get("guards", []) + [gid]}
        else:
            cur["guards"].append(gid)

    changed, no_label = [], []
    for slug, info in sorted(per_element.items()):
        p, computed = by_slug[slug], info["label"]
        text = p.read_text()
        new, na = re.subn(r"(?m)^(maturity_label:\s*)(LIVE|PARTIAL|TARGET)", rf"\g<1>{computed}", text)
        new, nb = re.subn(r"(\*\*maturity_label:\*\*\s*)(LIVE|PARTIAL|TARGET)", rf"\g<1>{computed}", new)
        if na == 0 and nb == 0:
            no_label.append(f"{slug} ({p.name}) — label is not LIVE/PARTIAL/TARGET-prefixed, so the "
                            f"writer cannot govern it; it stays HAND-SET")
            continue
        if new != text:
            if not args.dry_run:
                p.write_text(new)
            changed.append(f"{slug} → {computed} ({p.name})")

    verb = "would write" if args.dry_run else "wrote"
    print(f"label-writer → {elements_dir.relative_to(REPO)}/" + ("   [DRY RUN — nothing written]" if args.dry_run else ""))
    print("─" * 72)
    for c in changed:
        print(f"  {verb}: {c}")
    if not changed:
        print("  (no label changes — computed labels already match)")
    if no_label:
        print()
        print("  ⚠ MAPPED but UNGOVERNABLE (label not in the writer's vocabulary):")
        for m in no_label:
            print(f"      {m}")
    if unmapped:
        print()
        print("  ⚠ FIRE-PROVEN but NOT ON THE MAP (no element file claims these guards):")
        for m in unmapped:
            print(f"      {m}")
    print("─" * 72)
    return 0


def main():
    ap = argparse.ArgumentParser(description="honesty-label checker (fire-test, not grep)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("check", help="check every guard in the manifest")
    pc.add_argument("--manifest", help="path to the guard manifest (default: label_manifest.yaml)")
    pc.add_argument("--guard", help="check only this guard id")
    pc.add_argument("--json", action="store_true", help="emit JSON")
    pc.set_defaults(func=cmd_check)

    ps = sub.add_parser("selftest", help="who-watches-the-watcher: inert guard must label PARTIAL")
    ps.set_defaults(func=cmd_selftest)

    pw = sub.add_parser("write-labels", help="write fire-tested labels into the reference index (AUTO-COMPUTED only)")
    pw.add_argument("--manifest", help="path to the guard manifest")
    pw.add_argument("--elements", help="path to the elements dir (default: system/organism/elements)")
    pw.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    pw.set_defaults(func=cmd_write_labels)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
