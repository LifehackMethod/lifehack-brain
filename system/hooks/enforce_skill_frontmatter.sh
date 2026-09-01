#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: The 46-skill remediation (2026-07) proved skills are born malformed one at a time — a missing
#      `description:` (the ONLY field the harness reads to auto-trigger), an unquoted colon-space that
#      crashes the frontmatter YAML (8 skills silently fell back to their body heading), or a bloated
#      >500-line file. Re-auditing forever is the failure; this guard makes a bad SKILL.md un-writable.
# GUARDS: a Write **or Edit** of any skills/*/SKILL.md whose RESULTING content (a) has no non-empty
#      `description:`, (b) does not parse as YAML, or (c) exceeds 500 lines. For an Edit the guard
#      RECONSTRUCTS the result (current file + old_string->new_string) and adjudicates that.
# REDIRECT: scaffold it right the first time — `bash <repo>/system/tools/new-skill.sh <name>`
#      stamps a conformant SKILL.md. Add a double-quoted `description:` line; if it contains ': ', quote
#      the whole value ("... : ..."). Split anything over 500 lines into reference files the skill points to.
# SIGNPOST: the skill shape is codified in system/sops/skill-building-sop.md (§0 six traits, §0.5 the
#      3-layer intent model) + docs/skill-conformance.md. To change the rule, edit there + get
#      sign-off, then update this guard.
# UPDATED: 2026-07-28  (S2.3 — the Edit path was DARK)
# ─────────────────────────────────────────────────────────────────────────────
# enforce_skill_frontmatter.sh — PreToolUse hook (matcher: Write|Edit)
#
# 2026-07-28 (organism-audit S2.3) — WHY THE MATCHER GREW TO `Write|Edit`:
#   The guard matched `Write` only AND additionally bailed whenever the payload had no `content`
#   field. Both conditions exempt every Edit, so it protected BIRTH and nothing after it. Not
#   theoretical: skills/save/SKILL.md reached 893 lines against a 500-line ceiling entirely through
#   Edits this guard could not see. (It was 871 when the audit plan was written hours earlier — it
#   grew 22 more lines through the same hole while the hole was being written up.)
#
# SIZE IS NOT A WALL (revised 2026-07-28: "we should not have a 500 strict cap"):
#   skill-building-sop.md:565 calls <500 lines an IDEAL, and hook-sop.md §1 says a preference forced
#   into a hook becomes wallpaper. This guard was hard-blocking on its own rulebook's ideal. Blocking
#   is now PATHOLOGICAL-ONLY (1500 lines = runaway generation); leanness against the 500 ideal is
#   REPORTED by the conformance sweep (S2.8) where a human can judge it.
#   The earlier /save grandfather + ratchet are RETIRED — no permanent per-file exemption to
#   remember. What this guard still blocks is CORRECTNESS, not style: a missing/empty
#   `description:` (invisible to the harness), unparseable frontmatter, a REPLACE placeholder.

INPUT=$(cat)
export INPUT
# GUARD_LIB: same convention as guard_gmail_send.sh's use of lib/gws_guard.py -- resolved once
# here, by $0's own directory, and handed to the python block below via the environment.
GUARD_LIB="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/lib/winpath_fold.py" python3 <<'PY'
import os, json, sys, re

raw = os.environ.get("INPUT", "")
try:
    data = json.loads(raw)
    ti = data.get("tool_input", {}) or {}
    path = ti.get("file_path", "") or ti.get("path", "")
    content = ti.get("content", None)
except Exception:
    # Can't parse the tool call at all → not our concern to adjudicate here; allow.
    sys.exit(0)

# WINDOWS FOLD: path arrives backslash-native on Windows, so every "/skills/" substring test
# below would silently never match there and this guard would enforce nothing. Load the shared
# fold helper and classify off a COMPARISON copy only; `path` itself stays the original spelling
# for the basename check and any message. Fail closed: a missing helper must not silently widen
# this guard's scope to "nothing is a skill".
def _deny_nolib(lib):
    sys.stderr.write("BLOCKED: enforce_skill_frontmatter could not load lib/winpath_fold.py "
                      "(looked for it at '%s'), the path-form normaliser this guard's skills/-tree "
                      "classification depends on -- failing closed rather than guessing whether "
                      "this write targets a SKILL.md. REDIRECT: confirm "
                      "system/hooks/lib/winpath_fold.py exists and is readable, then retry.\n" % lib)
    sys.exit(2)

_lib = os.environ.get("GUARD_LIB", "")
if not _lib or not os.path.isfile(_lib):
    _deny_nolib(_lib)
import importlib.util
_spec = importlib.util.spec_from_file_location("winpath_fold", _lib)
_wf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wf)
path_cmp = _wf.winfold(path)

# Only guard a SKILL.md that lives under a skills/ tree, and NOT in a retired/archived holding area
# or the templates dir (those legitimately need no description).
# base: split on either separator from the ORIGINAL path (never the folded copy, which is
# lowercased) so the "SKILL.md" comparison stays case-sensitive and correct.
base = re.split(r"[\\/]+", path)[-1] if path else ""
if base != "SKILL.md" or "/skills/" not in path_cmp:
    sys.exit(0)
if "/skills/_" in path_cmp or "/templates/" in path_cmp:
    sys.exit(0)

def deny(reason):
    msg = ("BLOCKED: " + reason +
           " WHY: a SKILL.md with no readable description is invisible to the harness's auto-trigger, and"
           " unparseable frontmatter (often an unquoted value containing ': ') silently falls back to the body"
           " heading. REDIRECT: scaffold with `bash <repo>/system/tools/new-skill.sh <name>`;"
           " double-quote any description containing ': '; split a >500-line file into reference files."
           " RULE: system/sops/skill-building-sop.md §0.5 + docs/skill-conformance.md — edit there + get"
           " sign-off to change, then update this guard.")
    sys.stderr.write(msg + "\n")
    sys.exit(2)

# ── Resolve the RESULTING content (Write = given; Edit = reconstructed) ──────────────────
# SIZE (2026-07-28): the <500-line figure is an IDEAL, not a wall. skill-building-sop.md:565
# states it as "<500 lines **ideal** — a table of contents, not a manual", and hook-sop.md §1 is
# explicit that a PREFERENCE forced into a hook becomes wallpaper ("style/tone/'usually do X' live
# in CLAUDE.md or a skill"). This guard was hard-blocking on its own rulebook's ideal — stricter
# than the rule it enforces.
#   BLOCKING threshold is now PATHOLOGICAL-ONLY: it catches runaway generation (an agent dumping a
#   file), not authorship style. Leanness against the 500 ideal is a REPORTING job, owned by the
#   per-skill conformance sweep (S2.8), where it can be seen and judged instead of silently walling
#   an edit.
#   This also RETIRES the /save grandfather + ratchet added earlier today: with a pathological-only
#   cap there is no permanent exemption for one file, which is strictly better than an allowance
#   that has to be remembered.
HARD_CAP = 1500

def _lines(s):
    if not s:
        return 0
    return s.count("\n") + (0 if s.endswith("\n") else 1)

def _read_current():
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return None

cur = _read_current()

if content is None:
    # An Edit carries old_string/new_string, not the whole file. Reconstruct the result the same
    # way the harness will apply it, then adjudicate THAT.
    if "new_string" not in ti:
        sys.exit(0)                      # neither a Write nor an Edit we can reason about
    if cur is None:
        sys.exit(0)                      # cannot read the target -> cannot reconstruct; prior behaviour
    o, n = ti.get("old_string", ""), ti.get("new_string", "")
    if o and o not in cur:
        # The harness itself will reject this edit; reconstructing would silently produce a
        # NO-OP and adjudicate a file that never existed. (The Edit no-op trap, S2.2.)
        sys.exit(0)
    content = cur.replace(o, n) if ti.get("replace_all") else cur.replace(o, n, 1)

# (c) size — pathological runaway only; the 500 ideal is reported, not walled
nlines = _lines(content)
if nlines > HARD_CAP:
    deny("SKILL.md is %d lines, past the %d-line PATHOLOGICAL cap. This threshold exists to catch "
         "runaway generation, not authorship style — the <500-line figure in skill-building-sop.md "
         "is an IDEAL reported by the conformance sweep, not a wall. A file this size is almost "
         "certainly an accident: split it into reference files the skill points to." % (nlines, HARD_CAP))

# frontmatter block
m = re.match(r"^---\n(.*?)\n---", content, re.S)
if not m:
    deny("SKILL.md has no YAML frontmatter block (must open with a --- ... --- header).")
fm = m.group(1)

# (b) frontmatter must parse; (a) description must exist and be non-empty
desc = None
try:
    import yaml
    parsed = yaml.safe_load(fm)
    if not isinstance(parsed, dict):
        deny("SKILL.md frontmatter did not parse into a mapping.")
    desc = parsed.get("description")
except ImportError:
    # No yaml lib on this machine — regex fallback for the description presence check only.
    fb = re.search(r"^description:\s*(.+\S)\s*$", fm, re.M)
    desc = fb.group(1) if fb else None
except Exception:
    deny("SKILL.md frontmatter failed to parse as YAML (an unquoted value containing ': ' is the usual cause — double-quote it).")

if not desc or not str(desc).strip():
    deny("SKILL.md frontmatter has no non-empty `description:` field (the harness reads ONLY this to trigger the skill).")

# Guard against the placeholder scaffold being committed as a live skill.
if str(desc).strip().startswith("REPLACE"):
    deny("SKILL.md still has the scaffold's placeholder `description:` (starts with REPLACE) — fill it in.")

sys.exit(0)
PY
exit $?
