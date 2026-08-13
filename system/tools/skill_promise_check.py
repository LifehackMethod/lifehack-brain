#!/usr/bin/env python3
"""skill_promise_check.py — a skill's own promise vs. its own instructed commands.

WHEN: auditing whether a SKILL.md's stated contract ("never touches the Sheet",
      "propose-only, never executes fixes", "never deletes") is honored by the very
      commands that same file instructs a session to run.

WHAT: extracts a small, curated vocabulary of NEGATIVE/BOUNDARY promise-phrases from a
      SKILL.md's body text, and cross-checks each one against that file's OWN fenced code
      blocks (```bash / ```python / ...) — the literal instructions a session executes
      when it follows the skill. A promise contradicted by an instruction in the SAME
      file is a real, provable defect: the file cannot honor its own contract,
      independent of whether any session has ever actually run it.

WHY (the receipt): criterion 4 ("skills are TRUSTABLE — they do what they say ...
      demonstrated rather than claimed") was proven exactly ONCE by hand, for one real
      skill (a real supervised run), and a second check covers a single trigger string.
      Nothing made contract-vs-behavior checking GENERAL across the skills in this repo.
      This is Law 2's link-1 detector (SPEC -> SKILL FILE) turned inward: instead of
      diffing an EXTERNAL spec against the shipped file, it diffs a skill's own promise
      language against its own instructed-command language — two structurally different
      regions of the same document, checkable with NO live run and no model self-report.

THE GOVERNING TEST APPLIED HERE (SOP §V.4b): "what independent trace proves the work
      happened, and does this check read THAT?" The trace read here is the skill's own
      fenced code blocks — not a description of what the skill does, but the literal
      operative instructions a session will execute. That is not the actor's self-report;
      it is the actor's own operative text, which is the closest thing to "behavior" that
      exists before a live run.

KNOWN BOUNDS (read before trusting a PASS — an overclaiming gate is worse than none):
  - Proves internal CONSISTENCY, not RUNTIME COMPLIANCE. A PASS means "this file's own
    instructed commands do not contradict its own promise." It does NOT mean a live
    session obeyed the promise on a real turn — that is Law 2 link 2 (FILE -> FIRED),
    which needs a real run graded by a voted judge (S4.4's job). This tool never replaces
    that; it catches the cheaper, earlier defect (link 1) before a run is ever spent on it.
  - Only recognizes the CLAIM_TABLE vocabulary below (curated from real skill text found
    in this repo, not invented). A promise phrased outside that vocabulary is invisible
    to this tool and returns CANNOT_EVALUATE, never a silent PASS.
  - Only reads forbidden actions INSIDE FENCED CODE BLOCKS, never free prose. Deliberate:
    prose commonly explains what ANOTHER pipeline does ("the Sheet is written by
    true_submeter_ingest.py, not here") — scanning prose for keywords would false-positive
    on exactly that legitimate, common pattern (the benign near-miss, SOP Law 4.3).
  - A code block used purely as a documented example, or to describe another system's
    behavior, will be misread as THIS skill's own instruction. Known false-positive risk,
    not fixed here — keep illustrative-only blocks out of SKILL.md bodies, or expect a
    flag that needs a human read.
  - Claims are matched against the WHOLE file, not scoped per-section — a claim is
    treated as a GLOBAL promise about the skill regardless of which heading it sits
    under. `>`-blockquoted lines are excluded on purpose (see mask_blockquotes()): a
    live sweep of every real skill in this repo during the build of this tool caught one
    skill's "read-only — no writes," scoped to one instruction inside one quoted
    sub-agent prompt, being read as a file-wide promise and flagged against an unrelated
    write elsewhere in the same file. Any OTHER narrowly-scoped claim outside a
    blockquote (e.g. inside a numbered list item that only applies to one step) is still
    read as global — a real, unfixed false-positive risk.

USAGE
  skill_promise_check.py --skill PATH/TO/SKILL.md [--json]
  skill_promise_check.py --selftest

EXIT CODES (the part contract — SOP / system/parts/README.md)
  0  PASS            — every promise this tool recognizes is upheld by the file's own
                        instructed commands.
  1  REFUSED          — at least one promise is directly contradicted by an instructed
                        command in the same file. A real, quoted finding.
  2  CANNOT_EVALUATE  — missing/unreadable/empty file, or the file makes none of the
                        promises this tool's vocabulary recognizes. Fail-closed: never a
                        silent PASS on a file with nothing to check.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

# ── the claim vocabulary — curated from real skill text, not invented ──────────────────
# Each entry: a NEGATIVE/BOUNDARY promise a skill states about itself, and the forbidden
# action(s) that would contradict it if found inside the same file's own fenced commands.
CLAIM_TABLE = [
    {
        "id": "no_sheet_writes",
        "label": "never writes / touches a Google Sheet",
        "claim_re": re.compile(
            r"no\s+google\s+sheet\s+writes|never\s+writes?\s+(the\s+)?sheet|"
            r"local\s+files\s+only[^\n]{0,80}\bsheet\b|writes?\s+local\s+files\s+only",
            re.I,
        ),
        "forbidden_re": re.compile(
            r"sheets?\s+spreadsheets\s+values\s+(update|append|batchupdate|clear)|"
            r"spreadsheets\(\)\.values\(\)\.(update|append|clear|batchupdate)",
            re.I,
        ),
    },
    {
        "id": "never_delete_trash",
        "label": "never deletes / trashes",
        "claim_re": re.compile(r"\bnever\s+delete\b|\bnever\s+trash\b", re.I),
        "forbidden_re": re.compile(
            r"gws\s+gmail\s+users\s+(messages|threads)\s+trash|"
            r"\bos\.remove\(|\brm\s+-rf?\s",
            re.I,
        ),
    },
    {
        "id": "propose_only",
        "label": "read-only / propose-only / report-only / never executes fixes",
        "claim_re": re.compile(
            r"\bread-only\b|\bread\s+only\b|\bpropose-only\b|\bpropose\s+only\b|"
            r"\breport-only\b|\breport\s+only\b|never\s+executes?\s+fixes",
            re.I,
        ),
        "forbidden_re": re.compile(
            r"gws\s+(?:\S+\s+){0,3}(messages|threads)\s+modify|"
            r"gws\s+(?:\S+\s+){0,3}(messages|threads)\s+delete|"
            r"\bos\.remove\(|\brm\s+-rf?\s",
            re.I,
        ),
    },
]

CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)

EXIT_FOR_VERDICT = {"PASS": 0, "REFUSED": 1, "CANNOT_EVALUATE": 2}


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def extract_code_blocks(text):
    """Return [(block_text, block_start_line), ...] for every fenced block in text."""
    blocks = []
    for m in CODE_BLOCK_RE.finditer(text):
        blocks.append((m.group(1), line_of(text, m.start(1))))
    return blocks


def mask_blockquotes(text):
    """Blank out `>`-prefixed lines, character-for-character (so positions/line numbers
    stay identical), before claim-matching. A blockquote line in a SKILL.md is quoted
    material — most commonly a prompt template BEING HANDED to a sub-agent, not the
    skill's own top-level statement about itself. Without this, a narrowly-scoped clause
    inside a quoted sub-agent prompt (e.g. "read-only -- no writes", scoped to one
    instruction inside one dispatched prompt) reads as a GLOBAL promise about the whole
    skill, and any unrelated write anywhere else in the file then looks like a
    contradiction. Found live on a real skill during this tool's own build sweep, not
    invented -- see the docstring's KNOWN BOUNDS."""
    out_lines = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(">"):
            newline = "\n" if line.endswith("\n") else ""
            body_len = len(line) - len(newline)
            out_lines.append(" " * body_len + newline)
        else:
            out_lines.append(line)
    return "".join(out_lines)


def check_text(text, source_label="<skill>"):
    checked = []
    contradictions = []
    blocks = extract_code_blocks(text)
    lines = text.splitlines()
    claim_text = mask_blockquotes(text)

    for entry in CLAIM_TABLE:
        claim_m = entry["claim_re"].search(claim_text)
        if not claim_m:
            continue
        claim_line = line_of(text, claim_m.start())
        claim_quote = lines[claim_line - 1].strip() if claim_line - 1 < len(lines) else ""
        checked.append(
            {"id": entry["id"], "label": entry["label"],
             "claim_line": claim_line, "claim_quote": claim_quote}
        )
        for block_text, block_start in blocks:
            fm = entry["forbidden_re"].search(block_text)
            if fm:
                block_lines = block_text.splitlines()
                offset = block_text.count("\n", 0, fm.start())
                offending_line = block_start + offset
                offending_quote = block_lines[offset].strip() if offset < len(block_lines) else ""
                contradictions.append({
                    "id": entry["id"], "label": entry["label"],
                    "claim_line": claim_line, "claim_quote": claim_quote,
                    "command_line": offending_line, "command_quote": offending_quote,
                })
                break  # one contradicting instance is enough to REFUSE this claim

    if contradictions:
        verdict = "REFUSED"
    elif checked:
        verdict = "PASS"
    else:
        verdict = "CANNOT_EVALUATE"

    return {
        "source": source_label,
        "verdict": verdict,
        "checked_claims": checked,
        "contradictions": contradictions,
    }


def check_file(path):
    if not path or not os.path.isfile(path):
        return {"source": path, "verdict": "CANNOT_EVALUATE",
                "checked_claims": [], "contradictions": [], "error": "file not found"}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except Exception as exc:  # unreadable — fail closed, never a silent pass
        return {"source": path, "verdict": "CANNOT_EVALUATE",
                "checked_claims": [], "contradictions": [], "error": str(exc)}
    if not text.strip():
        return {"source": path, "verdict": "CANNOT_EVALUATE",
                "checked_claims": [], "contradictions": [], "error": "empty file"}
    return check_text(text, source_label=path)


def render_report(report):
    lines = [f"skill_promise_check: {report['source']}", f"verdict: {report['verdict']}"]
    if report.get("error"):
        lines.append(f"  error: {report['error']}")
    for c in report["checked_claims"]:
        lines.append(f"  checked [{c['id']}] line {c['claim_line']}: \"{c['claim_quote']}\"")
    for x in report["contradictions"]:
        lines.append(
            f"  CONTRADICTION [{x['id']}]: promise at line {x['claim_line']} "
            f"(\"{x['claim_quote']}\") contradicted by instructed command at line "
            f"{x['command_line']} (\"{x['command_quote']}\")"
        )
    return "\n".join(lines)


# ── self-test ────────────────────────────────────────────────────────────────────────
# This repo's skills live under .claude/skills/ (per-item symlinks into the clone), not a
# top-level skills/ — see shared/paths.py's own note on the same layout.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SKILLS_DIR = os.path.join(REPO_ROOT, ".claude", "skills")
ARCHIVIST_AUDIT = os.path.join(SKILLS_DIR, "archivist-audit", "SKILL.md")

# Two of the regression fixtures below (tests 1/3/4/6b) are ported as SYNTHETIC in-memory
# text rather than pointing at a real skill file. The tool's original build-repo caught
# these exact defects live, on its own real skills — but this is a template repo that does
# not ship those specific skills, so the fixture is reproduced as a small synthetic body
# instead (the same technique the near-miss test, 6 below, already used). The synthetic
# body is built to trip the SAME claim regexes the real one did, so the assertions below
# are the same assertions, just against portable text instead of a file that would not
# exist on a fresh install.
SYNTHETIC_HONEST_SKILL = (
    "# example-ingest (synthetic fixture — see this file's --selftest)\n\n"
    "This skill writes local files only — no Google Sheet writes. It will NEVER delete "
    "anything it reads, and NEVER trash it either.\n\n"
    "## real step\n"
    "```bash\n"
    "echo 'processed' >> /tmp/example-ingest.log\n"
    "```\n"
)


def _run_cli(args):
    """Run this tool's own CLI in a subprocess (SOP §parts-README: prove the exit-code
    contract end-to-end, not just the internal functions)."""
    cmd = [sys.executable, os.path.abspath(__file__)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _mutate(base_path, injected_block, results):
    """Copy a REAL skill file and append one extra fenced command block. Returns the
    tmp path, or None (recorded as a skipped check) if the base file is unavailable —
    this tool's self-test is grounded in real, evolving skill content on purpose
    (SOP hard rail: never validate on a fixture authored for the test alone), so a
    missing base file is reported, not papered over with an invented stand-in."""
    if not os.path.isfile(base_path):
        results.append(("[SKIP]", f"base skill missing: {base_path}"))
        return None
    with open(base_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    text += "\n\n## injected for skill_promise_check --selftest\n" + injected_block + "\n"
    fd, tmp_path = tempfile.mkstemp(suffix="-SKILL.md")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return tmp_path


def run_selftest():
    results = []  # list of (tag, message)

    def check(label, cond, detail=""):
        tag = "[PASS]" if cond else "[FAIL]"
        results.append((tag, f"{label}" + (f" -- {detail}" if detail else "")))
        return cond

    # 1 — a synthetic, honest skill passes cleanly (two real claims, no contradiction in
    #     its own command blocks).
    report = check_text(SYNTHETIC_HONEST_SKILL, source_label="<synthetic honest fixture>")
    ids = {c["id"] for c in report["checked_claims"]}
    check(
        "passes a synthetic honest skill (two real claims, no contradiction)",
        report["verdict"] == "PASS" and {"no_sheet_writes", "never_delete_trash"} <= ids,
        f"verdict={report['verdict']} checked_ids={sorted(ids)}",
    )

    # 2 — a REAL, honest skill (archivist-audit: propose-only) passes cleanly.
    if os.path.isfile(ARCHIVIST_AUDIT):
        rc, out, err = _run_cli(["--skill", ARCHIVIST_AUDIT, "--json"])
        try:
            report = json.loads(out)
        except Exception:
            report = {}
        ids = {c["id"] for c in report.get("checked_claims", [])}
        check(
            "passes a known-good real skill (archivist-audit: propose-only, no contradiction)",
            rc == 0 and report.get("verdict") == "PASS" and "propose_only" in ids,
            f"exit={rc} verdict={report.get('verdict')} checked_ids={sorted(ids)}",
        )
    else:
        results.append(("[SKIP]", f"archivist-audit SKILL.md not found at {ARCHIVIST_AUDIT}"))

    # 3 — CAUGHT: a deliberately over-promising mutation of the synthetic honest fixture
    #     (real "no Google Sheet writes" promise intact, one Sheet-write instruction
    #     injected).
    mutated = SYNTHETIC_HONEST_SKILL + (
        "\n## injected for skill_promise_check --selftest\n"
        "```bash\n"
        "gws sheets spreadsheets values update --params "
        "'{\"spreadsheetId\":\"X\",\"range\":\"A1\"}' --json '{\"values\":[[\"x\"]]}' 2>/dev/null\n"
        "```\n"
    )
    report = check_text(mutated, source_label="<synthetic mutated fixture>")
    cids = {c["id"] for c in report["contradictions"]}
    check(
        "catches an over-promising mutation (Sheet-write injected against \"no Sheet writes\")",
        report["verdict"] == "REFUSED" and "no_sheet_writes" in cids,
        f"verdict={report['verdict']} contradiction_ids={sorted(cids)}",
    )

    # 4 — CAUGHT: a deliberately over-promising mutation (real "NEVER trash" promise
    #     intact, one gmail-trash instruction injected).
    mutated = SYNTHETIC_HONEST_SKILL + (
        "\n## injected for skill_promise_check --selftest\n"
        "```bash\n"
        "gws gmail users messages trash --params '{\"userId\":\"me\",\"id\":\"X\"}' 2>/dev/null\n"
        "```\n"
    )
    report = check_text(mutated, source_label="<synthetic mutated fixture>")
    cids = {c["id"] for c in report["contradictions"]}
    check(
        "catches an over-promising mutation (trash instruction injected against \"NEVER trash\")",
        report["verdict"] == "REFUSED" and "never_delete_trash" in cids,
        f"verdict={report['verdict']} contradiction_ids={sorted(cids)}",
    )

    # 5 — CAUGHT: a deliberately over-promising mutation of archivist-audit (real
    #     "Propose-only" promise intact, one Gmail-modify instruction injected).
    tmp = _mutate(
        ARCHIVIST_AUDIT,
        "```bash\n"
        "gws gmail users threads modify --params '{\"id\":\"X\"}' "
        "--json '{\"removeLabelIds\":[\"A\"]}' 2>/dev/null\n"
        "```",
        results,
    )
    if tmp:
        try:
            rc, out, err = _run_cli(["--skill", tmp, "--json"])
            try:
                report = json.loads(out)
            except Exception:
                report = {}
            cids = {c["id"] for c in report.get("contradictions", [])}
            check(
                "catches an over-promising mutation (Gmail-modify injected against \"Propose-only\")",
                rc == 1 and report.get("verdict") == "REFUSED" and "propose_only" in cids,
                f"exit={rc} verdict={report.get('verdict')} contradiction_ids={sorted(cids)}",
            )
        finally:
            os.unlink(tmp)

    # 6 — the benign near-miss: a code block that MENTIONS the forbidden word but does
    #     not perform the forbidden action (a path/variable name, not a gws trash call).
    #     A part that fires on this is noise (SOP: "a part that fires on the near-miss
    #     is noise, and noisy gates get switched off").
    near_miss_text = (
        "## claim\nThis skill NEVER deletes. NEVER trash.\n\n"
        "## real step\n```bash\n"
        "# clear the /tmp/example_trash_scratch staging dir before starting\n"
        "echo 'no gmail action here'\n"
        "```\n"
    )
    report = check_text(near_miss_text, source_label="<near-miss fixture>")
    check(
        "passes a benign near-miss (the word 'trash' in a path/comment, not a trash command)",
        report["verdict"] == "PASS" and not report["contradictions"],
        f"verdict={report['verdict']} contradictions={report['contradictions']}",
    )

    # 6b — REGRESSION, caught live on a real skill during this tool's own build sweep: a
    #      scoped claim ("read-only -- no writes") sitting inside one BLOCKQUOTED
    #      sub-agent prompt is not a file-wide promise. Before mask_blockquotes() this
    #      misread it as global and flagged the file's unrelated, legitimate write
    #      elsewhere as a contradiction. Reproduced synthetically here (the original real
    #      skill that surfaced it is not part of this template repo). Locks the fix in
    #      the same way the real regression did: the file's ONLY match to this tool's
    #      claim vocabulary lives inside the blockquoted prompt, so excluding it correctly
    #      leaves nothing left to check (CANNOT_EVALUATE), not a false PASS and not the
    #      false REFUSED this regression locks out.
    blockquote_text = (
        "# example-breakdown (synthetic fixture)\n\n"
        "## sub-agent prompt\n"
        "> Read-only — no writes. Summarize the record; do not modify it.\n\n"
        "## real step (unrelated to the quoted prompt above)\n"
        "```bash\n"
        "gws gmail users threads modify --params '{\"id\":\"X\"}' "
        "--json '{\"removeLabelIds\":[\"A\"]}' 2>/dev/null\n"
        "```\n"
    )
    report = check_text(blockquote_text, source_label="<synthetic blockquote fixture>")
    check(
        "does not read a blockquoted sub-agent prompt's scoped claim as a file-wide "
        "promise (a scoped 'read-only' clause inside a quote is not a global promise)",
        report["verdict"] == "CANNOT_EVALUATE" and not report["contradictions"],
        f"verdict={report['verdict']} contradictions={report['contradictions']}",
    )

    # 7 — fail-closed: missing file -> CANNOT_EVALUATE (exit 2), never a silent pass.
    rc, out, err = _run_cli(["--skill", "/tmp/definitely-does-not-exist-skill.md", "--json"])
    check(
        "fails closed on a missing file (exit 2, not exit 0)",
        rc == 2,
        f"exit={rc}",
    )

    # 8 — fail-closed: empty file -> CANNOT_EVALUATE (exit 2), never a vacuous pass.
    fd, empty_path = tempfile.mkstemp(suffix="-SKILL.md")
    os.close(fd)
    try:
        rc, out, err = _run_cli(["--skill", empty_path, "--json"])
        check(
            "fails closed on an empty file (exit 2, not exit 0)",
            rc == 2,
            f"exit={rc}",
        )
    finally:
        os.unlink(empty_path)

    # 9 — a file that makes none of the recognized promises -> CANNOT_EVALUATE, never a
    #     silent PASS (an empty/no-signal input must never report "all clear").
    fd, noclaim_path = tempfile.mkstemp(suffix="-SKILL.md")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("# a skill\n\nThis skill formats a report and emails it.\n")
    try:
        rc, out, err = _run_cli(["--skill", noclaim_path, "--json"])
        check(
            "reports CANNOT_EVALUATE, not PASS, when the file makes no recognized promise",
            rc == 2,
            f"exit={rc}",
        )
    finally:
        os.unlink(noclaim_path)

    print("skill_promise_check --selftest")
    fail = False
    for tag, msg in results:
        print(f"  {tag} {msg}")
        if tag == "[FAIL]":
            fail = True
    print(f"SELFTEST: {'FAIL' if fail else 'PASS'}")
    return 1 if fail else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--skill", help="path to the skill's SKILL.md")
    ap.add_argument("--json", action="store_true", help="emit the verdict as JSON")
    ap.add_argument("--selftest", action="store_true", help="run the embedded two-sided self-test")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(run_selftest())

    if not args.skill:
        print("skill_promise_check: --skill PATH required (or --selftest)", file=sys.stderr)
        sys.exit(2)

    report = check_file(args.skill)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_report(report))
    sys.exit(EXIT_FOR_VERDICT[report["verdict"]])


if __name__ == "__main__":
    main()
