#!/usr/bin/env python3
"""No-AI conformance check for the planning-weekly step prompts (slice A).

Checks, over the step prompts and subagent/reference files given as arguments
(default: this skill's prompts/ + references/question-style.md):
  1. Every "§ Section" named in a prompt is a scratchpad section from SKILL.md's
     one section table (the "§ Council-<advisor>" row matches any Council-<name>).
  2. No file holds "desks/cal", a person's name, or a model id (tier words are fine).

Exit 0 = clean, 1 = violations found. Prints each violation as file:line.
"""
import os
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent / "SKILL.md"

ALLOWED = set()          # exact section names from SKILL.md's table
COUNCIL_PREFIX = "Council-"   # the § Council-<advisor> row matches by prefix

def person_names():
    """Person names, loaded at run time from the same setup terms the engine's
    check_personal_values.py uses — never hardcoded here."""
    try:
        gc = Path(__file__).resolve().parents[4] / "shared" / "grand_central"
        if not gc.is_dir():
            gc = Path(os.environ.get("LIFEHACK_CODE_ROOT", "")) / "shared" / "grand_central"
        if not gc.is_dir():
            return set()
        sys.path.insert(0, str(gc))
        import check_personal_values as cpv
        pr = cpv.load_roots()
        setup = cpv.setup_dir(os.environ.get("GC_SETUP_DIR"), pr)
        terms = cpv.build_terms(setup, pr)
        return {t for t, cat in terms.items()
                if cat in ("db-person", "setup-name") and len(t) >= 4}
    except Exception:
        return set()

MODEL_IDS = ["sonnet", "opus", "haiku", "gpt", "claude", "glm", "gemini",
             "llama", "mistral", "deepseek", "kimi", "qwen"]
LITERAL_BANS = ["desks/cal"]

SEC_RE = re.compile(r"§\s*([A-Z][A-Za-z0-9<>_'’-]*(?:[ \t]+[A-Za-z0-9<>_'’-]+)*)")
MD_CH = re.compile(r"[*_`]")

def load_sections():
    rows = []
    in_table = False
    for line in SKILL.read_text().splitlines():
        s = line.strip()
        if s.startswith("| Section") or (in_table and not s.startswith("|")):
            in_table = s.startswith("| Section")
            continue
        if in_table and s.startswith("|"):
            name = s.split("|")[1].strip().lstrip("§").strip()
            if name:
                rows.append(name)
    return rows

def section_tokens(text):
    out = []
    for m in SEC_RE.finditer(text):
        name = MD_CH.sub("", m.group(1)).strip()
        if name:
            out.append(name)
    return out

def tok_ok(tok, allowed):
    """True if the token equals a table section (or a line-wrap truncated
    leading-word prefix of one, or vice versa)."""
    words = tok.split()
    for n in range(len(words), 0, -1):
        cand = " ".join(words[:n])
        if cand.startswith(COUNCIL_PREFIX) or cand in allowed:
            return True
    return any(a.startswith(tok + " ") or a == tok for a in allowed)

def check_file(path, allowed):
    problems = []
    text = path.read_text()
    for tok in section_tokens(text):
        if not tok_ok(tok, allowed):
            problems.append(f"{path}: section not in SKILL.md's table: § {tok}")
    low = text.lower()
    for ban in LITERAL_BANS:
        if ban in low:
            problems.append(f"{path}: literal '{ban}'")
    for name in sorted(person_names() | set(MODEL_IDS)):
        if re.search(r"\b" + re.escape(name) + r"\b", low):
            problems.append(f"{path}: personal name / model id: '{name}'")
    return problems

def main(argv):
    allowed = set(load_sections())
    if not allowed:
        print("check_prompt_sections: could not read SKILL.md's section table", file=sys.stderr)
        return 1
    rel = ["prompts/step-1-check-the-compass.md", "prompts/step-2-confirm-the-week.md",
           "prompts/step-3-mine-the-brain.md", "prompts/step-4-rank.md",
           "prompts/subagents/look-back-drafter.md", "prompts/subagents/email-reader.md",
           "prompts/subagents/world-model-sharpener.md", "prompts/subagents/draft-ranker.md",
           "references/question-style.md"]
    files = [Path(a) for a in argv[1:]] if len(argv) > 1 else \
        [SKILL.parent / r for r in rel]
    files = [f for f in files if f.exists()]
    problems = []
    for f in files:
        problems += check_file(f, allowed)
    for p in problems:
        print("FAIL:", p)
    print(f"checked {len(files)} files; {len(problems)} violation(s)")
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
