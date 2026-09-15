#!/usr/bin/env python3
"""caller_lint.py — the caller lint, GATE's surviving form (Feature B1.5,
enforcement-layer Phase 2 plan).

Promotes `records/2026-09-13-phase-1/t1_caller_detection.py` (T1, Phase 1) from a disposable
test instrument into a register-integrated lint: for every governed hook-plane and tool-plane
unit, determine whether ANYTHING calls it, using T1's validated closed 7-class ontology
(registered-hook, scheduled, script-invoked, skill-referenced, ci-invoked, cli-instructed,
UNCALLED) plus its exempt-test-class carve-out. Units with no caller surface are REPORTED, never
auto-removed or auto-fixed — "T1 lists; it never judges" (t1-result.md). This module makes no
judgment call about what an UNCALLED unit means (dead code vs. an intentionally hand-run tool vs.
a genuine gap) — that reading is a human's, same as it was for T1's own 32.

WHY TWO EVIDENCE SOURCES, NOT ONE:

T1's original script re-parsed six raw wiring JSON files (settings.json x3 + hooks.json x2 +
registrations.json) and pulse-config.md/crontab directly, with its own ad-hoc regex over the raw
command strings. This lint instead takes the already-parsed REGISTER (harvest.py, B1.2) as its
source for exactly the two surfaces the register already carries structurally and byte-for-byte
equivalently (T2's own round-trip proof, 0 semantic-diff rows, is the receipt that this switch
changes nothing):
  - 'registered-hook' evidence  <- register rows of type == "hook" (one row per registration
    entry; a governed unit is registered-hook'd if any hook row's (repo, path) matches it)
  - 'scheduled' evidence        <- register rows of type == "scheduled" (their `command` field is
    exactly the pulse-config.md ```jobs``` line T1 substring-matched), PLUS a verbatim-ported
    fallback scan of the whole pulse-config.md file text (`scheduled_text_evidence`) — the
    register's scheduled rows only cover the fenced ```jobs``` block (Ruling 5, schema-v1.md),
    but T1 substring-matched the WHOLE file, which also catches the separate ```crontab``` block
    (e.g. `health-deadman-check.sh`, deliberately wired outside Pulse's own dispatch — found
    during this task's own Verify 2, see the B1.5 report's named-diff section)
This is also the literal integration point generate.py's own docstring already names ("a report
function next to cache_divergence_warnings() below... using the same loaded rows").

The other five surfaces need FILE BODIES (script source, SKILL.md prose, doc prose, CI YAML) that
the register does not and should not carry (schema v1 stores identity + existence + a content
hash, not full text). Those five are disk-scanned with T1's own code, ported verbatim — same
regexes, same invocation-shape rules (a bare mention is not a call), same exempt-test-class
downgrade, so a test file invoking its subject still does not confer callerhood on the subject
(the exact defect class T1's own repairs fixed 13 times before PASSing).

The GOVERNED UNIT UNIVERSE (which files are even in scope) is disk-walked here exactly as T1 did
— system/hooks/ + system/tools/ in both repos, `is_test_class` exemption — rather than taken
from the register's own rows, because the register's "hook" type is a REGISTRATION ROW (harvested
only where a wiring entry exists) and therefore cannot see an UNREGISTERED hook-plane script; T1's
whole point is to also catch exactly those (e.g. `guard_mcp_connector_shape.sh`, present on disk,
absent from every wiring surface). The register's "tool" rows ARE already a disk-walk of
system/tools/ with T1's identical exemption rule (harvest.py's own `harvest_tools`, "T1's exact
governed/exempt rules verbatim") — this module re-walks rather than trusts that, purely so one
function does not need two different unit-discovery code paths; the two are expected to agree
(and disagreeing would itself be a finding, surfaced in `LintResult.tool_disk_vs_register_delta`).

ENTRY POINT for wiring into generate.py (B1.4's omission check lands first on a separate branch of
this same plan; wiring both in is the lead's next step, not this task's):

    lint_register(rows, public_root, private_root, cache_root=None, home_root=None) -> LintResult

`rows` — plain register row dicts (schema v1), e.g. `[row for _, row, _ in
generate.load_register(path) if row]`, matching the calling convention `cache_divergence_warnings`
already uses for `hook_rows` in generate.py. Read-only: never writes to disk, never mutates `rows`,
never raises on a clean run (a malformed *row* is simply schema-invalid input, not this module's
gate to enforce — generate.py's own schema gate already refuses those before this would ever run).

Standalone CLI (no dependency on generate.py or harvest.py's own CLI wiring):
    python3 caller_lint.py REGISTER.jsonl [--public-root P] [--private-root P] [--cache-root P]
        [--home-root P] [--verdict-table OUT.md]
"""
import argparse
import json
import os
import re
import sys

THIS_FILE = os.path.abspath(__file__)
# system/register/caller_lint.py -> repo root is three levels up (harvest.py's own convention).
REPO_ROOT_FROM_SCRIPT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_FILE)))
DEFAULT_PRIVATE_ROOT = os.path.expanduser("~/.claude/skills/ClaudeOps")

GOVERNED_DIRS = ["system/hooks", "system/tools"]
SCRIPT_EXTS = (".sh", ".py")
TEST_DIR = re.compile(r"/tests?/", re.I)

# Verdict precedence — T1's own STR list, unchanged.
CALLER_CLASSES = [
    "registered-hook", "scheduled", "script-invoked",
    "skill-referenced", "ci-invoked", "cli-instructed",
]


# ---------------------------------------------------------------------------
# 1. GOVERNED SET — T1's disk walk, verbatim rule
# ---------------------------------------------------------------------------
def is_test_class(relpath):
    """T1's exempt-class rule, verbatim: a file in a tests/ dir, or whose basename starts
    test_/test-/firetest, is EXEMPT — a test invoking its subject does not make the subject
    called, and a test itself is not a governed unit. Merely containing '-test-' elsewhere in
    the name (the guard-fire-test operational chain) does NOT exempt it — that chain is
    scheduled production machinery, per T1's own comment."""
    b = os.path.basename(relpath)
    return bool(
        TEST_DIR.search(relpath)
        or re.match(r"test[_-]", b, re.I)
        or re.match(r"firetest", b, re.I)
    )


def walk_governed(repo_roots):
    """Return (governed, exempt_units): lists of dicts {repo, rel, base, cls}, exactly T1's
    shape. `cls` is 'hook' for a file under system/hooks/, 'tool' for system/tools/ — a
    per-FILE class, distinct from a register row's `type` field (a registration ROW)."""
    governed, exempt_units = [], []
    for repo, root in repo_roots.items():
        for gd in GOVERNED_DIRS:
            base_dir = os.path.join(root, gd)
            for dp, dn, fn in os.walk(base_dir):
                dn[:] = [d for d in dn if d != "__pycache__"]
                for f in sorted(fn):
                    if f.endswith(".bak") or f.endswith(".pyc"):
                        continue
                    if not f.endswith(SCRIPT_EXTS):
                        continue
                    rel = os.path.relpath(os.path.join(dp, f), root)
                    row = {
                        "repo": repo, "rel": rel, "base": f,
                        "cls": "hook" if "hooks" in gd else "tool",
                    }
                    (exempt_units if is_test_class(rel) else governed).append(row)
    return governed, exempt_units


# ---------------------------------------------------------------------------
# 2a/2b. REGISTER-SOURCED EVIDENCE — registered-hook, scheduled
# ---------------------------------------------------------------------------
def _norm_register_path(path):
    """Register `path` is repo-relative with a leading '/' (schema-v1.md). T1's `rel` has no
    leading slash. Normalize to the same form (no leading slash) for comparison."""
    return path[1:] if path.startswith("/") else path


def registered_hook_evidence(rows, units_by_key, ev):
    """Evidence source 1/2 from the register (see module docstring): a governed unit is
    'registered-hook' if any register row of type=='hook' shares its (repo, rel). Detail cites
    the row's own `surfaces` list — the register already folds the cache mirrors and the user
    settings.json into that one list, so this single pass covers everything T1's six raw files
    did, per T2's proven equivalence."""
    seen = set()
    for row in rows:
        if row.get("type") != "hook":
            continue
        key = (row.get("repo"), _norm_register_path(row.get("path", "")))
        if key not in units_by_key:
            continue
        surf = ",".join(row.get("surfaces", [])) or "?"
        detail = f"register:hook:{surf}"
        dedupe = (key, detail)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        ev(key[0], key[1], "registered-hook", detail)


def scheduled_evidence(rows, governed_and_exempt, ev):
    """Evidence source 2/2 from the register: a governed unit is 'scheduled' if its basename
    appears in a register row of type=='scheduled' `command` field — the exact text T1
    substring-matched out of pulse-config.md's fenced job block directly."""
    sched_rows = [r for r in rows if r.get("type") == "scheduled"]
    for g in governed_and_exempt:
        for row in sched_rows:
            cmd = row.get("command", "") or ""
            if g["base"] in cmd:
                ev(g["repo"], g["rel"], "scheduled", f"register:scheduled:{row.get('schedule_name', '?')}")


def scheduled_text_evidence(governed_and_exempt, repo_roots, ev):
    """Fallback / completeness pass, ported from T1 verbatim: the register's `scheduled` rows
    (harvest.py's `harvest_scheduled`) parse ONLY the fenced ```jobs``` block of pulse-config.md
    — by design, that block is the OS-scheduler-installable source of truth. But T1 substring-
    matched the WHOLE pulse-config.md file text, which also catches the separate ```crontab```
    block below it — used for entries deliberately wired OUTSIDE Pulse's own dispatch (e.g.
    `health-deadman-check.sh`, wired as its own dedicated crontab line specifically so a Pulse
    wedge cannot also silence its watchdog; see that block's own comment). Also re-checks the
    live (disarmed) `crontab -l`, comment-stripped, exactly as T1 did — contributes nothing today
    but is not this module's place to assume that stays true forever."""
    import subprocess

    sched_texts = []
    for repo, root in repo_roots.items():
        p = os.path.join(root, "system/pulse-config.md")
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                sched_texts.append((f"{repo}:pulse-config.md", f.read()))
    try:
        cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        cron = "\n".join(l for l in cron.splitlines() if not l.lstrip().startswith("#"))
        sched_texts.append(("crontab", cron))
    except OSError:
        pass
    for tag, text in sched_texts:
        for g in governed_and_exempt:
            if g["base"] in text:
                ev(g["repo"], g["rel"], "scheduled", tag)


# ---------------------------------------------------------------------------
# 2c. SCRIPT BODIES — governed+exempt units reference each other (T1, verbatim)
# ---------------------------------------------------------------------------
# A reference only counts as an INVOCATION if it is shaped like one: an invocation token on the
# line (bash|source|python|exec|subprocess|Popen|backtick|$() or an assignment (LIB=...base, for
# later execution). Anything else is a MENTION — recorded but non-conferring. \bsh\b is
# deliberately NOT a token — it matches the 'sh' inside every '.sh' filename (T1 defect #4).
INVOKE_TOK = re.compile(
    r"\b(bash|source|python3?|exec|subprocess|Popen|os\.system|check_output|check_call)\b"
    r"|`|\$\(|(^|[\s;|&])\.[\s]+['\"]"
)
# Prose tokens valid only in shell-citing bodies; in .py bodies a backtick is quotation and
# 'source' is an English word (T1 defect: false invocations in the hand-check sample).
INVOKE_TOK_PY = re.compile(r"\b(python3?|exec|subprocess|Popen|os\.system|check_output|check_call)\b")


def ref_kind(line, base, citing_ext):
    s = line.strip()
    if s.startswith("#"):
        return None
    s = re.sub(r"\s+#.*$", "", s)  # trailing comment is not code
    if base not in s:
        return None
    tok = INVOKE_TOK if citing_ext == ".sh" else INVOKE_TOK_PY
    if tok.search(s) or re.search(r"=[^\n]*" + re.escape(base), s):
        return "script-invoked"
    return "mentioned"


def script_body_evidence(governed, exempt_units, repo_roots, ev):
    all_units = governed + exempt_units
    bodies = {}
    for g in all_units:
        p = os.path.join(repo_roots[g["repo"]], g["rel"])
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                bodies[(g["repo"], g["rel"])] = f.read()
        except OSError:
            bodies[(g["repo"], g["rel"])] = ""
    for g in governed:
        mod = g["base"][:-3] if g["base"].endswith(".py") else None
        import_pat = (
            re.compile(r"\b(?:import\s+" + re.escape(mod) + r"\b|from\s+" + re.escape(mod) + r"\s+import\b)")
            if mod else None
        )
        for (repo2, rel2), body in bodies.items():
            if (repo2, rel2) == (g["repo"], g["rel"]):
                continue
            ext2 = os.path.splitext(rel2)[1]
            kinds = set()
            if g["base"] in body:
                for line in body.splitlines():
                    if g["base"] in line:
                        k = ref_kind(line, g["base"], ext2)
                        if k:
                            kinds.add(k)
            # Python imports name the MODULE, not the file (T1 defect: missed class).
            if import_pat and ext2 == ".py":
                for line2 in body.splitlines():
                    s2 = line2.strip()
                    if s2.startswith("#"):
                        continue
                    s2 = re.sub(r"\s+#.*$", "", s2)
                    if import_pat.search(s2):
                        kinds.add("script-invoked")
                        break
            if not kinds:
                continue
            if is_test_class(rel2):
                kinds = {f"EXEMPT:test-{k}" for k in kinds}
            for k in sorted(kinds):
                ev(g["repo"], g["rel"], k, f"{repo2}:{rel2}")


# ---------------------------------------------------------------------------
# 2d. SKILL surface — every .md under any .claude/skills/ tree (T1, verbatim)
# ---------------------------------------------------------------------------
def skill_evidence(governed, repo_roots, home_root, ev):
    skill_files = []
    for repo, root in repo_roots.items():
        for dp, dn, fn in os.walk(os.path.join(root, ".claude", "skills")):
            for f in fn:
                if f.endswith(".md"):
                    skill_files.append((repo, os.path.join(dp, f)))
    sk_root = os.path.join(home_root, ".claude", "skills")
    for dp, dn, fn in os.walk(sk_root):
        dn[:] = [d for d in dn if d != "ClaudeOps"]
        for f in fn:
            if f.endswith(".md"):
                skill_files.append(("installed", os.path.join(dp, f)))
    for tag, p in skill_files:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for g in governed:
            if g["base"] in text:
                ev(g["repo"], g["rel"], "skill-referenced", f"{tag}:{os.path.relpath(p, home_root)}")
    return skill_files


# one instruction-line matcher, shared by docs + CI surfaces (T1, verbatim): a word-bounded
# shell token, path-ish chars, then the basename. Prose never fires it.
def instr_match(line, base):
    return re.search(r"\b(python3?|bash|source|sh)\s+['\"$.\w/-]*" + re.escape(base), line)


# ---------------------------------------------------------------------------
# 2d2. CI surface — .github/workflows + .github/scripts (T1, verbatim)
# ---------------------------------------------------------------------------
def ci_evidence(governed, repo_roots, ev):
    for repo, root in repo_roots.items():
        gh = os.path.join(root, ".github")
        if not os.path.isdir(gh):
            continue
        for dp, dn, fn in os.walk(gh):
            for f in fn:
                if not f.endswith((".yml", ".yaml", ".py", ".sh", ".md")):
                    continue
                p = os.path.join(dp, f)
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    continue
                for g in governed:
                    if g["base"] in text:
                        for line in text.splitlines():
                            if g["base"] in line and not line.strip().startswith("#"):
                                kind = "ci-invoked" if instr_match(line, g["base"]) else "doc-mentioned"
                                ev(g["repo"], g["rel"], kind, f"{repo}:{os.path.relpath(p, root)}")


# ---------------------------------------------------------------------------
# 2e. docs / organism / sops — MENTION class only, cli-instructed if imperative (T1, verbatim)
# ---------------------------------------------------------------------------
def doc_evidence(governed, repo_roots, ev):
    doc_files = []
    for repo, root in repo_roots.items():
        for f in os.listdir(root):
            if f.endswith(".md"):
                doc_files.append((repo, os.path.join(root, f)))
        for sub in ["docs", "system/organism", "system/sops"]:
            p = os.path.join(root, sub)
            if os.path.isdir(p):
                for dp, dn, fn in os.walk(p):
                    for f in fn:
                        if f.endswith(".md"):
                            doc_files.append((repo, os.path.join(dp, f)))
    for tag, p in doc_files:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        for g in governed:
            if g["base"] in text:
                for line in text.splitlines():
                    if g["base"] not in line:
                        continue
                    if instr_match(line, g["base"]):
                        ev(g["repo"], g["rel"], "cli-instructed", f"{tag}:{os.path.basename(p)}")
                        break
                else:
                    ev(g["repo"], g["rel"], "doc-mentioned", f"{tag}:{os.path.basename(p)}")
    return doc_files


# ---------------------------------------------------------------------------
# Orchestration — the entry point
# ---------------------------------------------------------------------------
class LintResult:
    """rows: one dict per governed unit — {repo, rel, cls, verdict, evidence: [(surface, detail)]}.
    uncalled: the subset with verdict == 'UNCALLED' (T1's list; never judged, only reported).
    exempt_count: test-class units excluded from the governed set (not graded)."""

    def __init__(self, rows, exempt_count, counts):
        self.rows = rows
        self.exempt_count = exempt_count
        self.counts = counts

    @property
    def uncalled(self):
        return [r for r in self.rows if r["verdict"] == "UNCALLED"]

    def find(self, repo, rel):
        for r in self.rows:
            if r["repo"] == repo and r["rel"] == rel:
                return r
        return None


def lint_register(rows, public_root, private_root, cache_root=None, home_root=None):
    """The entry point. `rows` = plain register row dicts (schema v1). Read-only; returns a
    LintResult; never mutates `rows`, never touches disk beyond reading. `cache_root` is accepted
    for signature symmetry with `cache_divergence_warnings` but unused here — a hook row's
    `surfaces` list already folds in the cache mirrors (see `registered_hook_evidence`), so no
    separate cache scan is needed for caller detection specifically."""
    home_root = home_root or os.path.expanduser("~")
    repo_roots = {"public": public_root, "private": private_root}

    governed, exempt_units = walk_governed(repo_roots)
    units_by_key = {(g["repo"], g["rel"]): g for g in governed}
    # exempt units are also addressable for cross-checking, but never receive a verdict.
    exempt_by_key = {(g["repo"], g["rel"]): g for g in exempt_units}

    evidence = {}

    def ev(repo, rel, surface, detail):
        evidence.setdefault((repo, rel), []).append((surface, detail))

    registered_hook_evidence(rows, units_by_key, ev)
    scheduled_evidence(rows, governed + exempt_units, ev)
    scheduled_text_evidence(governed + exempt_units, repo_roots, ev)
    script_body_evidence(governed, exempt_units, repo_roots, ev)
    skill_evidence(governed, repo_roots, home_root, ev)
    ci_evidence(governed, repo_roots, ev)
    doc_evidence(governed, repo_roots, ev)

    out_rows = []
    for g in sorted(governed, key=lambda r: (r["repo"], r["rel"])):
        evs = evidence.get((g["repo"], g["rel"]), [])
        surfaces = {s for s, _ in evs}
        verdict = next((s for s in CALLER_CLASSES if s in surfaces), "UNCALLED")
        out_rows.append({
            "repo": g["repo"], "rel": g["rel"], "cls": g["cls"],
            "verdict": verdict, "evidence": evs,
        })

    counts = {v: sum(1 for r in out_rows if r["verdict"] == v) for v in CALLER_CLASSES + ["UNCALLED"]}
    result = LintResult(out_rows, len(exempt_units), counts)

    # Sanity cross-check (reported, not enforced): the register's own tool rows SHOULD equal
    # this module's disk-walked tool-class governed set 1:1 (harvest.py's harvest_tools uses
    # T1's identical rule). A mismatch here is itself a finding worth surfacing, never a crash.
    register_tool_keys = {
        (row.get("repo"), _norm_register_path(row.get("path", "")))
        for row in rows if row.get("type") == "tool"
    }
    disk_tool_keys = {(g["repo"], g["rel"]) for g in governed if g["cls"] == "tool"}
    result.tool_disk_vs_register_delta = {
        "disk_only": sorted(disk_tool_keys - register_tool_keys),
        "register_only": sorted(register_tool_keys - disk_tool_keys),
    }
    return result


# ---------------------------------------------------------------------------
# Verdict-table rendering (T1's own markdown shape, for a hand-check)
# ---------------------------------------------------------------------------
def render_verdict_table(result):
    out = ["| repo | file | class | verdict | surfaces |", "|---|---|---|---|---|"]
    for r in result.rows:
        surf = "; ".join(f"{s} ({d})" for s, d in r["evidence"][:6]) or "—"
        out.append(f"| {r['repo']} | {r['rel']} | {r['cls']} | {r['verdict']} | {surf} |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def load_register_rows(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("register", help="register JSONL file")
    p.add_argument("--public-root", default=REPO_ROOT_FROM_SCRIPT)
    p.add_argument("--private-root", default=DEFAULT_PRIVATE_ROOT)
    p.add_argument("--cache-root", default=None)
    p.add_argument("--home-root", default=os.path.expanduser("~"))
    p.add_argument("--verdict-table", default=None, help="write the full verdict table here")
    args = p.parse_args(argv)

    rows = load_register_rows(args.register)
    result = lint_register(
        rows, args.public_root, args.private_root,
        cache_root=args.cache_root, home_root=args.home_root,
    )

    if args.verdict_table:
        with open(args.verdict_table, "w", encoding="utf-8") as f:
            f.write(render_verdict_table(result))

    governed_n = len(result.rows)
    print(f"governed={governed_n} exempt={result.exempt_count}")
    print(f"verdicts: {result.counts}")
    if result.tool_disk_vs_register_delta["disk_only"] or result.tool_disk_vs_register_delta["register_only"]:
        print(f"WARN tool disk-vs-register delta: {result.tool_disk_vs_register_delta}")
    unc = result.uncalled
    print(f"\nUNCALLED ({len(unc)}):")
    for r in sorted(unc, key=lambda x: (x["repo"], x["rel"])):
        print(f"  {r['repo']}:{r['rel']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
