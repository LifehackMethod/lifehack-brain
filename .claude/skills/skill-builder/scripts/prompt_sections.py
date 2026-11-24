#!/usr/bin/env python3
"""prompt_sections.py — the prompt-section check.

CALLER: run by skill-builder 2.1's checker (checker-step-prompts) after the
step-prompt-drafter helper writes one draft per agreed step, and again whenever
a step prompt under prompts/ is edited. Usage:

    prompt_sections.py --prompt <a step prompt .md> \
        --template system/templates/skill-spec-form/step-prompt-template.md [--timeout 20]

    (--template may be omitted when the script sits in the repo; the default
    template resolves through shared/paths.tool_dir(), never a hard-coded path.)

WHY NO SHARED TOOL COVERS IT: the shared tools diff files generically; none of
them knows that a step prompt must carry the step-prompt template's numbered
`##` sections in the template's order, with no leftover `{…}` placeholder and no
leaked spec R-number. Skill-local knowledge, so it lives in the skill. The
script writes NOTHING anywhere — stdout only.

WHAT IT CHECKS (deny by default — anything not recognised is a fail):
1. The template's numbered `##` sections (## 1. … ## 10.; slots 3a and 3b are a
   CHOICE — the prompt must keep exactly one of them) are each present in the
   prompt, in the same order. Reports missing / duplicate / extra / out-of-order
   with counts taken from the sources. The template's unnumbered sections (e.g.
   "## How to fill it") and the prompt's own unnumbered sections are ignored.
2. No `{…}` template placeholder is left in the prompt.
3. No R-number pattern (R1–R9999, word-bounded) appears in the prompt — a spec
   reference leaked into a person-facing prompt.

Exit codes: 0 PASS · 1 FAIL (any of the above) · 2 COULD-NOT-CHECK (bad args,
unreadable file, unknown template shape, timeout).
"""

import argparse
import os
import re
import signal
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _d in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE)),
           os.path.dirname(os.path.dirname(os.path.dirname(_HERE))),
           os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))):
    if os.path.isfile(os.path.join(_d, "shared", "paths.py")):
        sys.path.insert(0, os.path.join(_d, "shared"))
        break
try:
    import paths  # shared/paths.py — resolves the default template; no hard-coded path here
except Exception:
    paths = None

DEFAULT_TIMEOUT = 20
# Numbered headings: ## 1. … ## 10., including lettered variants (3a/3b are the
# template's choice pair; any OTHER lettered/numbered slot, e.g. 3c or 12, is EXTRA).
HEADING = re.compile(r"^## (\d+[a-z]?)\.(?:\s|$)", re.MULTILINE)
# A SINGLE-brace {…} is a leftover template blank. The runner's own placeholders are
# DOUBLE-braced ({{OUT}}, {{CODE}}) and are legitimate in a draft — the lookbehind/lookahead
# keeps them out.
PLACEHOLDER = re.compile(r"(?<!\{)\{[^{}\n]+\}(?!\})")
R_NUMBER = re.compile(r"\bR\d{1,4}\b")
TEMPLATE_DEFAULT_REL = ("system", "templates", "skill-spec-form", "step-prompt-template.md")


class TimeUp(Exception):
    pass


def arm_timeout(seconds):
    def handler(signum, frame):
        raise TimeUp()
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(max(1, int(seconds)))


def refuse(why, what_to_do, rule):
    print(f"REFUSED: {why}")
    print(f"WHAT TO DO: {what_to_do}")
    print(f"RULE: {rule}")


def script_name():
    return os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "prompt_sections.py"


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def numbered_slots(text):
    """The template/prompt's numbered ## slots, in file order. 3a/3b merge to '3'."""
    out = []
    for m in HEADING.finditer(text):
        slot = m.group(1)
        if slot in ("3a", "3b"):
            slot = "3"
        out.append(slot)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check a step prompt against the step-prompt template (skill-builder).")
    parser.add_argument("--prompt", required=True, help="a step prompt .md file")
    parser.add_argument("--template", default=None,
                        help="step-prompt-template.md (default: the repo's own)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)

    template = args.template
    if template is None:
        if paths is None:
            refuse("no --template given and the repo's shared helpers are not reachable from "
                   "this script's location",
                   "pass --template system/templates/skill-spec-form/step-prompt-template.md",
                   "paths are never guessed; a missing template is COULD-NOT-CHECK")
            print(f"RECEIPT {script_name()} COULD-NOT-CHECK no template | untested: nothing "
                  f"was checked")
            return 2
        template = paths.tool_dir(*TEMPLATE_DEFAULT_REL)
    if not os.path.isfile(template):
        refuse(f"template '{template}' is not a readable file",
               "pass --template system/templates/skill-spec-form/step-prompt-template.md",
               "a missing template is COULD-NOT-CHECK, never a pass")
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK unreadable template | "
              f"untested: nothing was checked")
        return 2
    if not os.path.isfile(args.prompt):
        refuse(f"prompt '{args.prompt}' is not a readable file",
               "pass the step prompt to check: --prompt <step prompt .md>",
               "a missing prompt is COULD-NOT-CHECK, never a pass")
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK unreadable prompt | "
              f"untested: nothing was checked")
        return 2

    arm_timeout(args.timeout)
    try:
        template_text = read_text(template)
        prompt_text = read_text(args.prompt)
        template_slots = numbered_slots(template_text)
        prompt_slots = numbered_slots(prompt_text)
    except TimeUp:
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK timed out after {args.timeout}s | "
              f"untested: the prompt's sections")
        return 2
    finally:
        signal.alarm(0)

    if not template_slots:
        refuse(f"the template '{template}' carries no numbered ## sections",
               "check that this is really the step-prompt template",
               "an unrecognised template shape is COULD-NOT-CHECK, never a pass")
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK template has no numbered sections | "
              f"untested: nothing was checked")
        return 2

    # Required set = the template's slots, one of each. 3a/3b merged to '3'.
    required = []
    for s in template_slots:
        if s not in required:
            required.append(s)

    counts = {}
    for s in prompt_slots:
        counts[s] = counts.get(s, 0) + 1
    missing = [s for s in required if counts.get(s, 0) == 0]
    duplicated = [s for s in required if counts.get(s, 0) > 1]
    extra = [s for s in prompt_slots if s not in required]  # deny by default

    # Order: the prompt's slots, in order of first appearance, must be a
    # non-decreasing walk of the template order.
    template_order = {s: i for i, s in enumerate(required)}
    seen_positions, out_of_order = [], 0
    last = -1
    for s in prompt_slots:
        if s in template_order:
            if template_order[s] < last:
                out_of_order += 1
            last = max(last, template_order[s])

    placeholders = PLACEHOLDER.findall(prompt_text)
    r_numbers = R_NUMBER.findall(prompt_text)

    failed = bool(missing or duplicated or extra or out_of_order or placeholders or r_numbers)

    if failed:
        print(f"template requires {len(required)} sections in order: "
              f"{', '.join('## ' + s + '.' for s in required)}")
        if missing:
            print(f"missing ({len(missing)}): " + ", ".join("## " + s + "." for s in missing))
        if duplicated:
            print(f"duplicated ({len(duplicated)}): "
                  + ", ".join(f"## {s}. x{counts[s]}" for s in duplicated))
        if extra:
            print(f"extra ({len(extra)}): " + ", ".join("## " + s + "." for s in extra))
        if out_of_order:
            print(f"out-of-order headings: {out_of_order}")
        if placeholders:
            print(f"leftover template placeholder(s) ({len(placeholders)}): "
                  + "; ".join(placeholders[:5]))
        if r_numbers:
            print(f"R-number pattern(s) found ({len(r_numbers)}): "
                  + ", ".join(sorted(set(r_numbers))[:10]))
        print("WHAT TO DO: fix the prompt to carry every required section once, in the "
              "template's order, with every placeholder filled and no spec R-number left in.")
        print("RULE: a step prompt is a filled copy of the step-prompt template; deny by "
              "default — anything not recognised is a fail.")
        print(f"RECEIPT {script_name()} FAIL "
              f"missing={len(missing)} duplicated={len(duplicated)} extra={len(extra)} "
              f"out-of-order={out_of_order} placeholders={len(placeholders)} "
              f"r-numbers={len(r_numbers)} | untested: section CONTENTS beyond presence, "
              f"order and placeholders")
        return 1

    print(f"prompt carries all {len(required)} required sections, in the template's order, "
          f"no leftover placeholder, no R-number")
    print(f"RECEIPT {script_name()} PASS {len(required)} sections in order | "
          f"untested: section CONTENTS (whether the prose under each heading is right)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
