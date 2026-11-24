#!/usr/bin/env python3
"""Tests for prompt_sections.py (stdlib unittest).

Run:  python3 -m unittest discover -s .claude/skills/skill-builder/scripts/tests
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
SCRIPT = os.path.join(SCRIPTS_DIR, "prompt_sections.py")
HEADING = re.compile(r"^## (\d+[ab]?)\..*$", re.MULTILINE)


def repo_root():
    env = os.environ.get("LIFEHACK_REPO_ROOT")
    if env:
        return env
    d = os.path.dirname(SCRIPTS_DIR)
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "shared", "paths.py")):
            return d
        d = os.path.dirname(d)
    return None


def run_script(script_path, argv):
    env = dict(os.environ)
    r = repo_root()
    if r:
        env["PYTHONPATH"] = os.path.join(r, "shared") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, script_path] + argv,
                          capture_output=True, text=True, env=env, timeout=60)


def template_path():
    return os.path.join(repo_root(), "system", "templates", "skill-spec-form",
                        "step-prompt-template.md")


def template_heading_lines():
    """The template's numbered ## heading lines, in file order — FIRST occurrence
    per slot only (the template ends with a filled example that repeats them)."""
    with open(template_path(), encoding="utf-8") as fh:
        lines, seen = [], set()
        for m in HEADING.finditer(fh.read()):
            slot = m.group(1)  # raw slot label — 3a and 3b are BOTH kept
            if slot in seen:
                continue
            seen.add(slot)
            lines.append(m.group(0))
    return lines


def build_prompt(headings, body="filled content\n"):
    """A prompt skeleton carrying exactly the given heading lines."""
    return "\n".join(h + "\n" + body for h in headings) + "\n"


class PromptSectionsGood(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.headings = template_heading_lines()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def test_all_sections_in_order_passes(self):
        keep = [h for h in self.headings if not h.startswith("## 3b.")]
        p = self.write("good.md", build_prompt(keep))
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RECEIPT prompt_sections.py PASS", r.stdout)

    def test_3b_kept_instead_of_3a_passes(self):
        keep = [h for h in self.headings if not h.startswith("## 3a.")]
        p = self.write("good3b.md", build_prompt(keep))
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_real_generated_step_prompts_pass(self):
        prompts = os.path.join(repo_root(), ".claude", "skills", "skill-builder", "prompts")
        for name in sorted(os.listdir(prompts)):
            if not (name.startswith("step-") and name.endswith(".md")):
                continue
            r = run_script(SCRIPT, ["--prompt", os.path.join(prompts, name),
                                    "--template", template_path()])
            self.assertEqual(r.returncode, 0, f"{name}:\n{r.stdout}{r.stderr}")


class PromptSectionsEdge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.headings = template_heading_lines()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def test_missing_section_fails_with_count(self):
        keep = [h for h in self.headings
                if not h.startswith("## 3b.") and not h.startswith("## 7.")]
        p = self.write("missing7.md", build_prompt(keep))
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("missing (1): ## 7.", r.stdout)

    def test_out_of_order_fails(self):
        keep = [h for h in self.headings if not h.startswith("## 3b.")]
        swapped = list(keep)
        i4, i5 = swapped.index("## 4. Your job in this step"), swapped.index(
            "## 5. What you read and write (scratchpad sections, spec §5; read and write only these)")
        swapped[i4], swapped[i5] = swapped[i5], swapped[i4]
        p = self.write("swapped.md", build_prompt(swapped))
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("out-of-order headings: 1", r.stdout)

    def test_both_3a_and_3b_fails(self):
        p = self.write("both3.md", build_prompt(self.headings))
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("duplicated (1): ## 3.", r.stdout)

    def test_leftover_placeholder_and_r_number_fail(self):
        keep = [h for h in self.headings if not h.startswith("## 3b.")]
        text = build_prompt(keep) + "\nsay {spec_blank} here and cite R119 and R42.\n"
        p = self.write("leaks.md", text)
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("leftover template placeholder(s) (1): {spec_blank}", r.stdout)
        self.assertIn("R-number pattern(s) found (2)", r.stdout)

    def test_missing_file_is_could_not_check(self):
        r = run_script(SCRIPT, ["--prompt", os.path.join(self.tmp, "nope.md"),
                                "--template", template_path()])
        self.assertEqual(r.returncode, 2)
        self.assertIn("COULD-NOT-CHECK", r.stdout)

    def test_runner_double_brace_placeholders_are_not_leftovers(self):
        keep = [h for h in self.headings if not h.startswith("## 3b.")]
        p = self.write("runner.md", build_prompt(keep) + "\nfill `{{OUT}}` and `{{CODE}}`.\n")
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class PromptSectionsPadded(unittest.TestCase):
    """Right words buried in filler must NOT pass."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.headings = template_heading_lines()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def test_extra_numbered_section_fails(self):
        keep = [h for h in self.headings if not h.startswith("## 3b.")]
        text = build_prompt(keep) + "\n## 11. Extra section\nstuff\n"
        p = self.write("extra.md", text)
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("extra (1): ## 11.", r.stdout)

    def test_unknown_lettered_slot_fails(self):
        keep = [h for h in self.headings if not h.startswith("## 3b.")]
        text = build_prompt(keep) + "\n## 3c. How you whisper\nstuff\n"
        p = self.write("extra3c.md", text)
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("extra (1): ## 3c.", r.stdout)

    def test_r_number_buried_in_prose_fails(self):
        keep = [h for h in self.headings if not h.startswith("## 3b.")]
        filler = ("The design leans on house style (as approved) and on what the person said "
                  "earlier, quietly, without ceremony (R119) and more besides.")
        text = build_prompt(keep) + "\n" + filler + "\n"
        p = self.write("buried.md", text)
        r = run_script(SCRIPT, ["--prompt", p, "--template", template_path()])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("R119", r.stdout)


class PromptSectionsBrokenCopy(unittest.TestCase):
    def test_broken_copy_passes_where_it_must_fail(self):
        with open(SCRIPT, encoding="utf-8") as fh:
            src = fh.read()
        needle = 'PLACEHOLDER = re.compile(r"(?<!\\{)\\{[^{}\\n]+\\}(?!\\})")'
        self.assertIn(needle, src, "placeholder regex line changed; fix the broken-copy test")
        broken_src = src.replace(needle, 'PLACEHOLDER = re.compile(r"\\{\\b\\}")')
        with tempfile.TemporaryDirectory() as tmp:
            broken = os.path.join(tmp, "prompt_sections.py")
            with open(broken, "w", encoding="utf-8") as fh:
                fh.write(broken_src)
            keep = [h for h in template_heading_lines() if not h.startswith("## 3b.")]
            text = build_prompt(keep) + "\nleftover {spec_blank} here\n"
            f = os.path.join(tmp, "leaky.md")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(text)
            good = run_script(SCRIPT, ["--prompt", f, "--template", template_path()])
            bad = run_script(broken, ["--prompt", f, "--template", template_path()])
        self.assertEqual(good.returncode, 1, good.stdout)
        self.assertEqual(bad.returncode, 0, bad.stdout)  # the break is visible


if __name__ == "__main__":
    unittest.main()
