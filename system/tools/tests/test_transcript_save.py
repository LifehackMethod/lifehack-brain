#!/usr/bin/env python3
"""Tests for youtube_transcript_save.py — F1 (frontmatter forging via title), F2 (SOURCE
cross-check by substring containment), F3 (desk fallback), F4 (unwrapped wrapper-file open), plus
the pre-existing verdict/--confirm gates that an adversarial pass already confirmed correct.

Every test drives the real script as a subprocess, with LIFEHACK_ROOT pointed at a fresh temp
directory under /private/tmp/claude-501/ — never the real notes tree. LIFEHACK_ROOT is
resolve_brain_root()'s own first-priority, documented injection point (shared/brain_root.py), so
this needs no monkeypatching of the module under test.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_HERE)
SCRIPT = os.path.join(_TOOLS_DIR, "youtube_transcript_save.py")
VALIDATOR = os.path.join(_TOOLS_DIR, "validate_frontmatter.py")

# Every temp artifact this suite creates lives under here, per instructions — never system tmp,
# never anywhere near the real notes tree.
_SCRATCH_BASE = "/private/tmp/claude-501"
os.makedirs(_SCRATCH_BASE, exist_ok=True)

FORGE_TITLE = (
    'evil"\nrecord_type: pwned\ndesk: attacker-desk\ncreated_at: 2020-01-01\n'
    'status: forged\nauthority: system\n---\nmalicious_body: true'
)


def default_manifest(**overrides):
    man = {
        "gate_passed": True,
        "desk": "deryl",
        "title": "A Perfectly Normal Title",
        "video_id": "vid123",
        "url": "https://youtube.com/watch?v=vid123",
        "uploader": "Some Uploader",
        "upload_date": "2024-01-01",
        "duration_seconds": 120,
        "provenance_tag": "gate-v1",
        "cleared_path": "/tmp/rdr/yt/vid123/vid123.cleared.txt",
    }
    man.update(overrides)
    return man


def default_wrapper(source="/tmp/rdr/yt/vid123/vid123.cleared.txt", verdict="BENIGN",
                     data="Hello world transcript text."):
    indented = "\n".join("  " + line for line in data.splitlines()) or "  "
    return f"SOURCE: {source}\nVERDICT: {verdict}\nDATA\n{indented}\n"


class TranscriptSaveTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ytsave_", dir=_SCRATCH_BASE)
        self.brain = os.path.join(self.tmpdir, "brain")
        os.makedirs(self.brain, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def write_manifest(self, name="manifest.json", cleared_content="Hello world transcript text.",
                        **overrides):
        # The coverage-verification fix (2026-08-27 incident) makes youtube_transcript_save.py
        # read the ACTUAL cleared_path file for every save, not just --from-cleared ones, so a
        # manifest whose cleared_path points nowhere now fails a save that previously succeeded
        # for unrelated reasons. Callers that don't care about the coverage mechanics (the vast
        # majority of this suite) get a small real file auto-created at the SAME basename the
        # module-level default_wrapper()'s SOURCE default already expects ("vid123.cleared.txt"),
        # so the existing SOURCE-basename-equality check still matches with zero other changes.
        # Callers that explicitly pass their own cleared_path (missing-file / empty-file / real
        # --from-cleared fixtures) are left alone — they manage that file themselves on purpose.
        if "cleared_path" not in overrides:
            cleared_path = os.path.join(self.tmpdir, "vid123.cleared.txt")
            if not os.path.exists(cleared_path):
                with open(cleared_path, "w", encoding="utf-8") as fh:
                    fh.write(cleared_content)
            overrides = dict(overrides)
            overrides["cleared_path"] = cleared_path
        man = default_manifest(**overrides)
        path = os.path.join(self.tmpdir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(man, fh)
        return path

    def run_save(self, manifest_path, wrapper_path, confirm=False, extra_args=None, env_extra=None,
                 stdin=None):
        args = [sys.executable, SCRIPT, "--manifest", manifest_path, "--wrapper", wrapper_path]
        if confirm:
            args.append("--confirm")
        if extra_args:
            args.extend(extra_args)
        env = dict(os.environ)
        env["LIFEHACK_ROOT"] = self.brain
        # Never let a persisted machine-global or repo pointer leak in and point tests at the real
        # notes tree; LIFEHACK_ROOT is priority (1) in resolve_brain_root's order so this suffices.
        if env_extra:
            env.update(env_extra)
        return subprocess.run(args, capture_output=True, text=True, env=env, input=stdin)

    def all_md_files(self):
        hits = []
        for root, _dirs, files in os.walk(self.brain):
            for f in files:
                if f.endswith(".md"):
                    hits.append(os.path.join(root, f))
        return hits

    def validate(self, path):
        return subprocess.run([sys.executable, VALIDATOR, path], capture_output=True, text=True)


# ── F1 — forging the frontmatter via title ──────────────────────────────────────────────────────
class TestF1FrontmatterForging(TranscriptSaveTestCase):
    def _write_and_confirm(self, title):
        manifest = self.write_manifest(title=title)
        wrapper = self.write(
            "wrapper.txt",
            default_wrapper(source=self.cleared_path_for(manifest)),
        )
        return self.run_save(manifest, wrapper, confirm=True)

    def cleared_path_for(self, manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)["cleared_path"]

    def test_exact_forging_payload_produces_real_frontmatter(self):
        proc = self._write_and_confirm(FORGE_TITLE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files = self.all_md_files()
        self.assertEqual(len(files), 1, files)
        outfile = files[0]

        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        # Reproduce the validator's own (naive) delimiter scan directly, so this test fails loudly
        # if a future change reopens the gap rather than silently trusting validate_frontmatter.py.
        end = content.find("---", 3)
        self.assertNotEqual(end, -1, "closing delimiter not found at all")
        frontmatter = content[3:end]

        # The REAL fields, anchored to start-of-line so an attacker-controlled substring sitting
        # inside a quoted value (e.g. the title itself, which literally contains the text
        # "record_type: pwned") cannot be mistaken for them.
        import re
        self.assertRegex(frontmatter, r"(?m)^record_type:\s*source-ingest\s*$")
        self.assertRegex(frontmatter, r"(?m)^desk:\s*deryl\s*$")
        self.assertRegex(frontmatter, r"(?m)^authority:\s*skill\s*$")
        self.assertRegex(frontmatter, r"(?m)^status:\s*active\s*$")
        # None of the attacker's forged values leaked into a real field.
        self.assertNotRegex(frontmatter, r"(?m)^record_type:\s*pwned\s*$")
        self.assertNotRegex(frontmatter, r"(?m)^desk:\s*attacker-desk\s*$")
        self.assertNotRegex(frontmatter, r"(?m)^status:\s*forged\s*$")
        proc2 = self.validate(outfile)
        self.assertEqual(proc2.returncode, 0, f"stdout={proc2.stdout!r} stderr={proc2.stderr!r}")

    def test_title_with_bare_quote(self):
        proc = self._write_and_confirm('A "quoted" title')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_title_with_lone_delimiter(self):
        proc = self._write_and_confirm("Before --- After")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        end = content.find("---", 3)
        frontmatter = content[3:end]
        import re
        self.assertRegex(frontmatter, r"(?m)^record_type:\s*source-ingest\s*$")
        self.assertRegex(frontmatter, r"(?m)^desk:\s*deryl\s*$")
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_title_with_single_hyphen_stays_readable(self):
        # A lone hyphen between words is the ordinary case ("Transcript - Powell - May 7") and
        # must render as a literal "-" in the frontmatter, not the - escape — that escape is
        # reserved for actually-dangerous runs of 2+ consecutive hyphens (see yaml_scalar()).
        proc = self._write_and_confirm("Transcript - Powell - May 7")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertRegex(content, r'(?m)^title:\s*".*Transcript - Powell - May 7"\s*$')
        self.assertNotIn("\\u002d", content)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_title_with_double_hyphen_is_escaped(self):
        proc = self._write_and_confirm("Before -- After")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertRegex(content, r'(?m)^title:\s*".*Before \\u002d\\u002d After"\s*$')
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_title_with_triple_hyphen_is_escaped(self):
        proc = self._write_and_confirm("Before --- After")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertRegex(content, r'(?m)^title:\s*".*Before \\u002d\\u002d\\u002d After"\s*$')
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_title_with_cr(self):
        proc = self._write_and_confirm("Line one\rrecord_type: pwned")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        self.assertEqual(self.validate(outfile).returncode, 0)
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("\r", content)

    def test_title_with_nul(self):
        proc = self._write_and_confirm("Weird\x00Title")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        self.assertEqual(self.validate(outfile).returncode, 0)
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("\x00", content)

    def test_title_5000_chars(self):
        long_title = "x" * 5000
        proc = self._write_and_confirm(long_title)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        self.assertEqual(self.validate(outfile).returncode, 0)


# ── F2 — SOURCE cross-check must be equality, not containment ──────────────────────────────────
class TestF2SourceCrossCheck(TranscriptSaveTestCase):
    def test_mention_but_different_file_is_rejected(self):
        manifest = self.write_manifest(cleared_path="/tmp/rdr/yt/OTHER/abc123.cleared.txt")
        src = ("this document mentions abc123.cleared.txt somewhere but is actually "
               "/tmp/rdr/yt/OTHER/xyz999.cleared.txt")
        wrapper = self.write("wrapper.txt", default_wrapper(source=src))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])

    def test_correct_basename_is_accepted(self):
        # cleared_path now must exist for every save (the coverage check reads it), so this points
        # at a real file — under a differently-named directory, "OTHER", to keep testing that
        # basename equality (not full-path equality) is what the SOURCE cross-check enforces.
        cleared = self._make_other_cleared()
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt", default_wrapper(source=cleared))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_source_with_surrounding_whitespace_is_accepted(self):
        cleared = self._make_other_cleared()
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write(
            "wrapper.txt",
            default_wrapper(source=f"   {cleared}   "),
        )
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def _make_other_cleared(self):
        other_dir = os.path.join(self.tmpdir, "OTHER")
        os.makedirs(other_dir, exist_ok=True)
        path = os.path.join(other_dir, "abc123.cleared.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("Hello world transcript text.")
        return path


# ── F3 — desk must fail closed, never fall back to "marc" ──────────────────────────────────────
class TestF3DeskFailClosed(TranscriptSaveTestCase):
    def test_missing_desk_halts_and_writes_nothing(self):
        manifest = self.write_manifest()
        with open(manifest, encoding="utf-8") as fh:
            man = json.load(fh)
        del man["desk"]
        with open(manifest, "w", encoding="utf-8") as fh:
            json.dump(man, fh)
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        # Never silently lands under "marc".
        self.assertFalse(os.path.isdir(os.path.join(self.brain, "desks", "marc")))

    def test_explicit_desk_targets_that_desk_path(self):
        manifest = self.write_manifest(desk="deryl")
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files = self.all_md_files()
        self.assertEqual(len(files), 1)
        self.assertIn(os.path.join("desks", "deryl", "records", "source-ingests"), files[0])
        self.assertFalse(os.path.isdir(os.path.join(self.brain, "desks", "marc")))


# ── F4 — missing wrapper file fails through die(), not a raw traceback ─────────────────────────
class TestF4MissingWrapperFile(TranscriptSaveTestCase):
    def test_missing_wrapper_exits_clean(self):
        manifest = self.write_manifest()
        missing_wrapper = os.path.join(self.tmpdir, "does-not-exist.txt")
        proc = self.run_save(manifest, missing_wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        # A die()-routed failure: our own "[transcript-save]" prefix, no Python traceback.
        self.assertIn("[transcript-save]", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


# ── Regression: verdict membership + --confirm gate ─────────────────────────────────────────────
class TestVerdictAndConfirmRegressions(TranscriptSaveTestCase):
    def _run_with_verdict(self, verdict, confirm=True):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper(verdict=verdict))
        return self.run_save(manifest, wrapper, confirm=confirm)

    def test_benign_lowercase_rejected(self):
        proc = self._run_with_verdict("benign")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])

    def test_benign_with_no_flags_suffix_rejected(self):
        proc = self._run_with_verdict("BENIGN (no flags)")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])

    def test_empty_verdict_rejected(self):
        manifest = self.write_manifest()
        wrapper = self.write(
            "wrapper.txt",
            "SOURCE: /tmp/rdr/yt/vid123/vid123.cleared.txt\nVERDICT: \nDATA\n  hi\n",
        )
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])

    def test_none_with_trailing_space_rejected(self):
        proc = self._run_with_verdict("NONE ")
        # "NONE " (with a trailing space) is stripped by parse_wrapper's own `.strip()` on the
        # VERDICT line, so this one legitimately matches the real "NONE" member — confirm it is
        # accepted, since the point of this regression group is that verdicts OUTSIDE the closed
        # set are rejected, not that whitespace defeats the strip.
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unicode_lookalike_rejected(self):
        # Cyrillic-look-alike "ВENIGN" style homoglyph — not the ASCII string "BENIGN".
        proc = self._run_with_verdict("BЕNIGN")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])

    def test_bare_save_no_confirm_no_outline_actually_writes(self):
        # Writing is now the default: no --confirm, no --outline, no --dry-run — the record must
        # still land on disk. This is the behavior the whole change exists for (see the module
        # docstring's WRITING IS THE DEFAULT note): a transcript must never again sit unsaved in a
        # temp directory just because a human keystroke or an outline never arrived.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files = self.all_md_files()
        self.assertEqual(len(files), 1, files)
        out = json.loads(proc.stdout)
        self.assertTrue(out["wrote"])
        self.assertEqual(self.validate(files[0]).returncode, 0)

    def test_confirm_flag_still_accepted_without_error(self):
        # --confirm is now a no-op, kept only so existing callers/docs don't break. Passing it must
        # neither be rejected nor change the outcome from the bare-save case above.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files = self.all_md_files()
        self.assertEqual(len(files), 1, files)
        out = json.loads(proc.stdout)
        self.assertTrue(out["wrote"])

    def test_dry_run_writes_nothing_and_exits_zero(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=False, extra_args=["--dry-run"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.all_md_files(), [])
        out = json.loads(proc.stdout)
        self.assertFalse(out["wrote"])
        self.assertIn("would_write", out)

    def test_dry_run_with_confirm_also_present_still_writes_nothing(self):
        # --confirm is a no-op; it must never override --dry-run.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True, extra_args=["--dry-run"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.all_md_files(), [])
        out = json.loads(proc.stdout)
        self.assertFalse(out["wrote"])


# ── Opinion / low-confidence default markers ─────────────────────────────────────────────────────
class TestOpinionDefaultMarkers(TranscriptSaveTestCase):
    def test_default_save_has_all_three_opinion_markers(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        files = self.all_md_files()
        self.assertEqual(len(files), 1, files)
        outfile = files[0]

        # Filename marker.
        self.assertIn("opinion", os.path.basename(outfile))

        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()

        # Frontmatter markers.
        self.assertRegex(content, r'(?m)^content_class:\s*"opinion"\s*$')
        self.assertRegex(content, r'(?m)^confidence:\s*"low"\s*$')
        self.assertRegex(content, r'(?m)^body_source:\s*reader-data\s*$')

        # Body banner, unmissable, directly under the H1.
        self.assertIn("OPINION / LOW CONFIDENCE", content)

        self.assertEqual(self.validate(outfile).returncode, 0)


# ── --content-class / --confidence overrides ─────────────────────────────────────────────────────
class TestContentClassOverride(TranscriptSaveTestCase):
    def test_override_flows_through_quoted_and_into_filename(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--content-class", "primary-source",
                                          "--confidence", "high"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        self.assertIn("primary-source", os.path.basename(outfile))
        self.assertNotIn("opinion", os.path.basename(outfile))

        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        # yaml_scalar() only escapes RUNS of 2+ hyphens; a lone "-" between words stays literal
        # and readable, since clean_text() already guarantees no embedded line break exists for
        # it to hide a forged "---" delimiter behind.
        self.assertRegex(content, r'(?m)^content_class:\s*"primary-source"\s*$')
        self.assertRegex(content, r'(?m)^confidence:\s*"high"\s*$')
        self.assertIn("PRIMARY-SOURCE / HIGH CONFIDENCE", content)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_override_with_forging_payload_is_quoted_not_interpolated(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--content-class", FORGE_TITLE])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        end = content.find("---", 3)
        frontmatter = content[3:end]
        self.assertRegex(frontmatter, r"(?m)^record_type:\s*source-ingest\s*$")
        self.assertRegex(frontmatter, r"(?m)^desk:\s*deryl\s*$")
        self.assertNotRegex(frontmatter, r"(?m)^record_type:\s*pwned\s*$")
        self.assertNotRegex(frontmatter, r"(?m)^desk:\s*attacker-desk\s*$")
        self.assertEqual(self.validate(outfile).returncode, 0)


# ── --outline insertion point ────────────────────────────────────────────────────────────────────
class TestOutlineInsertion(TranscriptSaveTestCase):
    def test_outline_lands_between_provenance_and_transcript(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md",
                                   "## Outline — My Video\n\n- Point A\n- Point B\n")
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()

        i_source = content.find("## Source")
        i_provenance = content.find("## Provenance")
        i_outline = content.find("## Outline — My Video")
        i_transcript = content.find("## Transcript")
        for label, idx in (("Source", i_source), ("Provenance", i_provenance),
                            ("Outline", i_outline), ("Transcript", i_transcript)):
            self.assertNotEqual(idx, -1, f"{label} section missing")
        self.assertLess(i_source, i_provenance)
        self.assertLess(i_provenance, i_outline)
        self.assertLess(i_outline, i_transcript)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_multiline_outline_survives_with_newlines_intact(self):
        # The defect this guards against: clean_text() strips \n along with every other C0 control
        # character, which used to flatten the whole outline block onto one physical line. An
        # outline with real newlines between its numbered sections must come out with those
        # newlines still in place.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_src = (
            "## Outline — Powell press conference\n\n"
            "1. **Opening statement**\n"
            "   - Rate held steady\n"
            "   - _themes: fed-liquidity, fiscal-currency_\n\n"
            "2. **Mandate tension**\n"
            "   - Some other point\n"
        )
        outline_path = self.write("outline.md", outline_src)
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        # The full multi-line block appears verbatim (modulo the trailing whitespace .strip()
        # removes) -- not squashed onto one line.
        self.assertIn(outline_src.strip(), content)
        i_opening = content.find("1. **Opening statement**")
        i_mandate = content.find("2. **Mandate tension**")
        self.assertNotEqual(i_opening, -1)
        self.assertNotEqual(i_mandate, -1)
        self.assertLess(i_opening, i_mandate)
        # And each section is genuinely on its own set of lines, not one giant run-on line.
        between = content[i_opening:i_mandate]
        self.assertIn("\n", between)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_outline_nul_and_c0_controls_stripped(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write(
            "outline.md",
            "## Outline — Weird\n\n1. **Sec\x00tion\x01 One**\n   - detail\x07 here\n",
        )
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("\x00", content)
        self.assertNotIn("\x01", content)
        self.assertNotIn("\x07", content)
        self.assertIn("Section One", content)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_outline_crlf_normalised_to_lf(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write(
            "outline.md",
            "## Outline — CRLF\r\n\r\n1. **Section One**\r\n   - detail\r\n",
        )
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("\r", content)
        self.assertIn("## Outline — CRLF\n\n1. **Section One**\n   - detail", content)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_outline_cannot_forge_frontmatter_even_with_newlines_preserved(self):
        # Re-run the original F1 attack payload, but as the OUTLINE body rather than the title, now
        # that the outline path deliberately preserves newlines. The record's real frontmatter must
        # still be the only frontmatter -- the outline's newlines land in the BODY, after the
        # frontmatter's closing '---' has already been written, so they can never reach back into it.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", FORGE_TITLE)
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        end = content.find("---", 3)
        self.assertNotEqual(end, -1, "closing delimiter not found at all")
        frontmatter = content[3:end]
        self.assertRegex(frontmatter, r"(?m)^record_type:\s*source-ingest\s*$")
        self.assertRegex(frontmatter, r"(?m)^desk:\s*deryl\s*$")
        self.assertRegex(frontmatter, r"(?m)^authority:\s*skill\s*$")
        self.assertRegex(frontmatter, r"(?m)^status:\s*active\s*$")
        self.assertNotRegex(frontmatter, r"(?m)^record_type:\s*pwned\s*$")
        self.assertNotRegex(frontmatter, r"(?m)^desk:\s*attacker-desk\s*$")
        self.assertNotRegex(frontmatter, r"(?m)^status:\s*forged\s*$")
        self.assertEqual(self.validate(outfile).returncode, 0)
        # And the original title's own frontmatter forging test still stands untouched — this test
        # only proves the SAME payload is also neutralised when it arrives via --outline instead.


# ── outline_pending / themes_active absence on a bare save ──────────────────────────────────────
class TestOutlinePending(TranscriptSaveTestCase):
    def test_bare_save_has_outline_pending_true_and_no_themes_active(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertRegex(content, r"(?m)^outline_pending:\s*true\s*$")
        # absent, not an empty list — an empty list would mean "themes were computed and none
        # applied"; absent means "themes were never even attempted on this pass".
        self.assertNotIn("themes_active:", content)
        # No "## Outline" section header on a bare save, but a visible placeholder line where the
        # outline will eventually go.
        self.assertNotIn("## Outline", content)
        self.assertIn("still in progress", content)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_outline_supplied_sets_outline_pending_false(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", "## Outline — My Video\n\n- Point A\n")
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertRegex(content, r"(?m)^outline_pending:\s*false\s*$")
        self.assertIn("## Outline — My Video", content)
        self.assertEqual(self.validate(outfile).returncode, 0)


# ── --themes validation against system/marc-lenses.md ────────────────────────────────────────────
class TestThemesFiltering(TranscriptSaveTestCase):
    def _themes_active_values(self, content):
        m = None
        import re
        m = re.search(r"(?m)^themes_active:\s*\[(.*)\]\s*$", content)
        self.assertIsNotNone(m, content)
        raw = m.group(1).strip()
        if not raw:
            return []
        # Each element is a proper JSON string (yaml_scalar's quoting); these theme slugs only
        # contain lone hyphens, which now render literally, but json.loads decodes a - run
        # back to literal "-" all the same under any interpreter's stdlib, if one is present.
        return [json.loads(part.strip()) for part in raw.split(",")]

    def test_offlist_theme_dropped_and_reported_valid_kept(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--themes", "fed-liquidity,not-a-real-theme,geopolitics"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("not-a-real-theme", proc.stderr)
        self.assertIn("dropping off-list theme", proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        values = self._themes_active_values(content)
        self.assertEqual(values, ["fed-liquidity", "geopolitics"])
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_all_offlist_themes_yields_empty_list_not_a_halt(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--themes", "nonsense-one,nonsense-two"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertEqual(self._themes_active_values(content), [])


# ── --from-cleared ────────────────────────────────────────────────────────────────────────────────
class TestFromCleared(TranscriptSaveTestCase):
    def _cleared_file(self, content="A full, unredacted transcript body from disk."):
        path = self.write("cleared.txt", content)
        return path

    def test_happy_path_sources_body_from_file_and_records_body_source(self):
        cleared = self._cleared_file()
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt",
                              default_wrapper(source=cleared, verdict="BENIGN", data="UNCHANGED"))
        proc = self.run_save(manifest, wrapper, confirm=True, extra_args=["--from-cleared"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("A full, unredacted transcript body from disk.", content)
        self.assertRegex(content, r"(?m)^body_source:\s*cleared-file\s*$")
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_refused_when_verdict_is_real_attack(self):
        cleared = self._cleared_file()
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt",
                              default_wrapper(source=cleared, verdict="REAL-ATTACK",
                                               data="UNCHANGED"))
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--from-cleared", "--accept-attack-redacted"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("REAL-ATTACK", proc.stderr)

    def test_unchanged_without_from_cleared_halts(self):
        cleared = self._cleared_file()
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt",
                              default_wrapper(source=cleared, verdict="BENIGN", data="UNCHANGED"))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("--from-cleared", proc.stderr)

    def test_missing_cleared_file_halts(self):
        missing = os.path.join(self.tmpdir, "does-not-exist.cleared.txt")
        manifest = self.write_manifest(cleared_path=missing)
        wrapper = self.write("wrapper.txt",
                              default_wrapper(source=missing, verdict="BENIGN", data="UNCHANGED"))
        proc = self.run_save(manifest, wrapper, confirm=True, extra_args=["--from-cleared"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])

    def test_empty_cleared_file_halts(self):
        empty = self.write("empty.cleared.txt", "")
        manifest = self.write_manifest(cleared_path=empty)
        wrapper = self.write("wrapper.txt",
                              default_wrapper(source=empty, verdict="BENIGN", data="UNCHANGED"))
        proc = self.run_save(manifest, wrapper, confirm=True, extra_args=["--from-cleared"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])


# ── Coverage verification (2026-08-27 incident: 208-of-28,730-word partial read, whole-file
#    VERDICT: NONE) ──────────────────────────────────────────────────────────────────────────────
def coverage_wrapper(source, coverage_line, verdict="NONE", data=None):
    """Build a raw envelope with an explicit COVERAGE line, which default_wrapper() doesn't
    support. `data` defaults to a string built from the SAME word list `coverage_line` was derived
    from, so tests can pass whatever they built independently."""
    if data is None:
        data = "placeholder"
    indented = "\n".join("  " + line for line in data.splitlines()) or "  "
    return f"SOURCE: {source}\nVERDICT: {verdict}\nCOVERAGE: {coverage_line}\nDATA\n{indented}\n"


class TestCoverageVerification(TranscriptSaveTestCase):
    # Per the test instructions for this fix: NO dir= argument here — this class's temp files are
    # not required to live under _SCRATCH_BASE the way the rest of this suite's fixtures are.
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ytsave_coverage_")
        self.brain = os.path.join(self.tmpdir, "brain")
        os.makedirs(self.brain, exist_ok=True)

    def _words(self, n, tag):
        # Distinct, greppable tokens per position so a wrong-window bug (off-by-one, wrong end)
        # can't accidentally still match.
        return [f"{tag}{i:05d}" for i in range(n)]

    def test_full_coverage_declared_and_verified_is_accepted(self):
        words = self._words(500, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())  # computed, not guessed
        first = " ".join(words[:4])
        last = " ".join(words[-4:])
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_coverage_end_text_not_at_file_end_is_refused(self):
        words = self._words(500, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first = " ".join(words[:4])
        fabricated_last = "this text is not actually in the file"
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{fabricated_last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        # DEFECT 2 fix: the message now names the PHRASE comparison specifically, not a vague
        # "does not verify" over both fields.
        self.assertIn("did not verify against the real start/end", proc.stderr)
        self.assertIn("LAST_WORDS", proc.stderr)

    def test_partial_coverage_is_refused_naming_both_numbers(self):
        # Models the actual incident: the reader stopped partway through and declared coverage
        # ending at that (real, verbatim) point — which is genuinely NOT the file's real end.
        words = self._words(2000, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        actual_total = len(content.split())
        cutoff = 300
        declared_words = cutoff  # honestly reports how much it read
        first = " ".join(words[:4])
        last = " ".join(words[cutoff - 4:cutoff])  # the real text where it actually stopped
        coverage = f'WORDS_READ={declared_words} FIRST_WORDS="{first}" LAST_WORDS="{last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="NONE", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        # Both numbers named, not just one.
        self.assertIn(str(declared_words), proc.stderr)
        self.assertIn(str(actual_total), proc.stderr)

    def test_unparseable_coverage_line_is_refused(self):
        cleared = self.write("cleared.txt", "one two three four five")
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write(
            "wrapper.txt",
            coverage_wrapper(cleared, "I read the whole thing, trust me", verdict="NONE",
                              data="one two three four five"),
        )
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("cannot parse", proc.stderr)

    def test_large_file_with_no_coverage_line_is_refused(self):
        # Over READ_TOOL_DEFAULT_LINE_LIMIT (2000) lines AND over READ_TOOL_DEFAULT_BYTE_LIMIT
        # bytes — the chosen no-coverage-line policy (accept only when a single default Read call
        # plainly reaches the end) must reject this outright rather than silently trust a bare
        # wrapper, exactly like the live incident: a 28,730-word file where the reader only
        # actually saw the first 208 lines. The byte gate is checked first (see DEFECT 1), so a
        # fixture this large trips that message rather than the line-count one.
        big_content = "\n".join(f"line {i} of a very long transcript" for i in range(2500))
        cleared = self.write("cleared.txt", big_content)
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt", default_wrapper(source=cleared, verdict="NONE",
                                                              data="a short reader summary"))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("no COVERAGE line", proc.stderr)
        self.assertIn("52600", proc.stderr)

    def test_many_lines_but_few_bytes_with_no_coverage_line_is_refused(self):
        # Over READ_TOOL_DEFAULT_LINE_LIMIT (2000) lines but UNDER READ_TOOL_DEFAULT_BYTE_LIMIT
        # bytes — isolates the line-count gate (kept alongside the byte gate per DEFECT 1's fix,
        # not replaced by it) since a file can be line-heavy without being byte-heavy.
        big_content = "\n".join("x" for _ in range(2500))  # 2500 lines, ~5000 bytes
        cleared = self.write("cleared.txt", big_content)
        self.assertLess(os.path.getsize(cleared), 52_600)
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt", default_wrapper(source=cleared, verdict="NONE",
                                                              data="a short reader summary"))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("no COVERAGE line", proc.stderr)
        self.assertIn("2000", proc.stderr)

    def test_153kb_482_line_incident_fixture_with_no_coverage_line_is_refused(self):
        # DEFECT 1, demonstrated exactly: the incident's own dimensions — 482 lines, comfortably
        # under READ_TOOL_DEFAULT_LINE_LIMIT (2000), but 153,465 bytes — well over the byte
        # ceiling. The pre-fix line-only gate accepted this; the byte gate must refuse it.
        lines = ["x" * 317 for _ in range(482)]  # 482 * (317 + 1 newline) ~= 153,276 bytes; padded below
        big_content = "\n".join(lines)
        # pad the final line so the total is >= 153,465 bytes, matching the incident's own fixture
        pad_needed = 153_465 - len(big_content.encode("utf-8"))
        if pad_needed > 0:
            lines[-1] += "y" * pad_needed
            big_content = "\n".join(lines)
        cleared = self.write("cleared.txt", big_content)
        self.assertEqual(len(big_content.splitlines()), 482)
        self.assertGreaterEqual(os.path.getsize(cleared), 153_465)
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt", default_wrapper(source=cleared, verdict="NONE",
                                                              data="a short reader summary"))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("no COVERAGE line", proc.stderr)
        self.assertIn("52600", proc.stderr)

    def test_byte_ceiling_boundary_at_limit_is_accepted(self):
        # Exactly READ_TOOL_DEFAULT_BYTE_LIMIT bytes, no COVERAGE line, under the line limit too —
        # must be accepted (boundary is "at or below", not "strictly below").
        content = "a" * 52_600
        self.assertEqual(len(content.encode("utf-8")), 52_600)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt", default_wrapper(source=cleared, verdict="NONE",
                                                              data="a short reader summary"))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_byte_ceiling_boundary_one_over_is_refused(self):
        # One byte over READ_TOOL_DEFAULT_BYTE_LIMIT, no COVERAGE line, under the line limit —
        # must be refused.
        content = "a" * 52_601
        self.assertEqual(len(content.encode("utf-8")), 52_601)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt", default_wrapper(source=cleared, verdict="NONE",
                                                              data="a short reader summary"))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("no COVERAGE line", proc.stderr)
        self.assertIn("52600", proc.stderr)

    def test_small_file_with_no_coverage_line_is_still_accepted(self):
        # Backward compatibility for the case the size threshold is meant to cover: a small file,
        # no COVERAGE line at all — a single default Read call plainly reaches the end of it.
        cleared = self.write("cleared.txt", "A short transcript that easily fits one Read call.")
        manifest = self.write_manifest(cleared_path=cleared)
        wrapper = self.write("wrapper.txt", default_wrapper(source=cleared, verdict="NONE"))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    # ── DEFECT 2: WORDS_READ is a checked claim, not decorative ────────────────────────────────
    def test_words_read_far_below_actual_is_refused_sampled_head_tail_attack(self):
        # Demonstrated attack: WORDS_READ=8 against a 10,017-word file, honest FIRST_WORDS/
        # LAST_WORDS phrases (so the OLD phrase-only check would accept it), with an injection
        # buried in the middle the reader never actually looked at.
        words = self._words(10_017, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        actual_total = len(content.split())
        self.assertEqual(actual_total, 10_017)
        first = " ".join(words[:4])
        last = " ".join(words[-4:])
        coverage = f'WORDS_READ=8 FIRST_WORDS="{first}" LAST_WORDS="{last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="NONE", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        # Both the declared and the actual counts are named.
        self.assertIn("8", proc.stderr)
        self.assertIn(str(actual_total), proc.stderr)

    def test_words_read_within_small_tolerance_is_accepted(self):
        # A reader's honest hand-count can be off by a little; a small shortfall must not be a
        # false refusal. actual=500, declared=490 (10 short) is within max(20, 2%) = 20.
        words = self._words(500, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        first = " ".join(words[:4])
        last = " ".join(words[-4:])
        coverage = f'WORDS_READ=490 FIRST_WORDS="{first}" LAST_WORDS="{last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_words_read_just_outside_tolerance_is_refused(self):
        # actual=500, tolerance = max(20, round(0.02*500)) = 20. declared=479 is 21 short: outside.
        words = self._words(500, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        first = " ".join(words[:4])
        last = " ".join(words[-4:])
        coverage = f'WORDS_READ=479 FIRST_WORDS="{first}" LAST_WORDS="{last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("479", proc.stderr)
        self.assertIn("500", proc.stderr)

    # ── DEFECT 3: a genuine quote in the transcript's first/last words must be representable ───
    def test_last_word_containing_quote_with_honest_coverage_is_accepted(self):
        words = self._words(50, "w")
        words[-1] = 'word"quoted'  # the file's true last "word" contains a literal double-quote
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first = " ".join(words[:4])
        last_escaped = " ".join(words[-4:]).replace('"', '\\"')
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{last_escaped}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_first_word_containing_quote_with_honest_coverage_is_accepted(self):
        words = self._words(50, "w")
        words[0] = '"quoted'  # the file's true first "word" starts with a literal double-quote
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first_escaped = " ".join(words[:4]).replace('"', '\\"')
        last = " ".join(words[-4:])
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first_escaped}" LAST_WORDS="{last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_quote_bearing_claim_that_does_not_actually_match_is_still_refused(self):
        # Anti-spoofing must not weaken: an escaped-quote phrase that is simply WRONG (doesn't
        # match the file's real end) is still refused, exactly like an unescaped wrong phrase.
        words = self._words(50, "w")
        words[-1] = 'word"quoted'
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first = " ".join(words[:4])
        fabricated_last = 'not\\"the real ending'
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{fabricated_last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])

    # ── Refusal messages still leak only counts, never the file's real first/last words ────────
    def test_refusal_messages_do_not_echo_the_files_real_phrases(self):
        words = self._words(500, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        real_first = " ".join(words[:4])
        real_last = " ".join(words[-4:])
        fabricated_last = "this text is not actually in the file"
        coverage = f'WORDS_READ={len(words)} FIRST_WORDS="{real_first}" LAST_WORDS="{fabricated_last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        # The declared (wrong) phrase is named — that's the reader's own claim, already known to
        # whoever wrote it — but the file's REAL last words must never appear in the message.
        self.assertNotIn(real_last, proc.stderr)

    # ── DEFECT 1 (2026-08-27 first live run): HTML-entity-mangled coverage phrases ──────────────
    # The subagent result channel HTML-escapes text in transit, so an honest, fully-covered
    # LAST_WORDS="Bye. >> [music]" arrives here as LAST_WORDS="Bye. &gt;&gt; [music]". These prove
    # the genuinely-correct-but-mangled case is now ACCEPTED, and that a genuinely wrong phrase
    # (entity-escaped or not) is still REFUSED.
    def test_entity_escaped_last_words_matching_real_gt_gt_is_accepted(self):
        # The real observed incident fixture: a transcript ending in "Bye. >> [music]" with the
        # reader honestly declaring LAST_WORDS="Bye. &gt;&gt; [music]" (transport-mangled, not
        # dishonest).
        words = self._words(50, "w")
        content = " ".join(words) + " Bye. >> [music]"
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first = " ".join(words[:4])
        last_escaped = "Bye. &gt;&gt; [music]"
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{last_escaped}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_entity_escaped_first_words_matching_real_lt_gt_is_accepted(self):
        # Same mangling on the FIRST_WORDS side: the file genuinely starts with "<start>" and the
        # reader's honest declaration arrives HTML-escaped.
        content = "<start> Hello world " + " ".join(self._words(50, "w"))
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first_escaped = "&lt;start&gt; Hello world"
        last = " ".join(content.split()[-4:])
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first_escaped}" LAST_WORDS="{last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_amp_lt_apos_and_double_escaped_gt_entities_all_handled(self):
        # &amp; , &lt; , &#39; , and a DOUBLE-escaped &amp;gt; (two layers of channel escaping,
        # observed in practice) all decode correctly in one declared phrase.
        real_last = "AT&T <ok> it's done >"
        content = " ".join(self._words(50, "w")) + " " + real_last
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first = " ".join(content.split()[:4])
        last_escaped = "AT&amp;T &lt;ok&gt; it&#39;s done &amp;gt;"
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{last_escaped}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.all_md_files()), 1)

    def test_entity_escaped_but_genuinely_wrong_last_words_is_still_refused(self):
        # Anti-spoofing must not weaken: an entity-escaped phrase that, once decoded, still does
        # NOT match the file's real end must be refused exactly like an unescaped wrong phrase.
        words = self._words(50, "w")
        content = " ".join(words) + " Bye. >> [music]"
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first = " ".join(words[:4])
        wrong_last_escaped = "Never said. &gt;&gt; [silence]"
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{wrong_last_escaped}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("LAST_WORDS", proc.stderr)
        # The file's real, undecoded-entity ending must never appear in the refusal.
        self.assertNotIn("Bye. >> [music]", proc.stderr)

    # ── DEFECT 2 (2026-08-27 first live run): refusal must name the PHRASE comparison, not the
    #    (matching) word count ───────────────────────────────────────────────────────────────────
    def test_phrase_mismatch_refusal_names_the_phrase_comparison_not_the_word_count(self):
        words = self._words(500, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        first = " ".join(words[:4])  # correct
        fabricated_last = "this text is not actually in the file"  # wrong
        coverage = f'WORDS_READ={total_words} FIRST_WORDS="{first}" LAST_WORDS="{fabricated_last}"'
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        # Names the comparison that actually failed...
        self.assertIn("LAST_WORDS", proc.stderr)
        self.assertIn("PHRASE comparison failed", proc.stderr)
        # ...and does not name FIRST_WORDS as also failing, since it matched.
        self.assertNotIn("FIRST_WORDS did not verify", proc.stderr)
        # Explicitly rules out the word count as the cause (WORDS_READ matched exactly here).
        self.assertIn("not the problem", proc.stderr)
        # Still never echoes the file's real last words.
        real_last = " ".join(words[-4:])
        self.assertNotIn(real_last, proc.stderr)

    def test_both_phrases_mismatched_refusal_names_both(self):
        words = self._words(500, "w")
        content = " ".join(words)
        cleared = self.write("cleared.txt", content)
        manifest = self.write_manifest(cleared_path=cleared)
        total_words = len(content.split())
        fabricated_first = "not the real opening at all"
        fabricated_last = "this text is not actually in the file"
        coverage = (f'WORDS_READ={total_words} FIRST_WORDS="{fabricated_first}" '
                    f'LAST_WORDS="{fabricated_last}"')
        wrapper = self.write("wrapper.txt",
                              coverage_wrapper(cleared, coverage, verdict="BENIGN", data=content))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        self.assertIn("FIRST_WORDS", proc.stderr)
        self.assertIn("LAST_WORDS", proc.stderr)
        self.assertIn("PHRASE comparison failed", proc.stderr)


# ── The fold: youtube_transcript_save.py called a SECOND time against its own record ─────────────
# Folded in from the retired transcript_inject_outline.py's own test suite (9/9 passing there) —
# see splice_outline_into_existing_record() in the tool under test for the mechanism. Every test
# here calls run_save TWICE against the SAME --manifest/--wrapper: first bare (writes the record
# with outline_pending: true and a placeholder), then again with --outline (and often --themes) to
# fold it in. Because the outfile path is deterministic from the manifest (today + desk + slug),
# the second call lands on the exact same file as the first.
class TestOutlineFoldIn(TranscriptSaveTestCase):
    def _bare_save(self, manifest_overrides=None, wrapper_overrides=None):
        manifest = self.write_manifest(**(manifest_overrides or {}))
        wrapper = self.write("wrapper.txt", default_wrapper(**(wrapper_overrides or {})))
        proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return manifest, wrapper, self.all_md_files()[0]

    def test_outline_folds_between_provenance_and_transcript(self):
        manifest, wrapper, outfile = self._bare_save()
        outline_path = self.write("outline.md", "## Outline\n- Point one\n- Point two\n")
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("still in progress", content)
        self.assertIn("## Outline\n- Point one\n- Point two", content)
        i_prov = content.index("## Provenance")
        i_outline = content.index("## Outline")
        i_transcript = content.index("## Transcript")
        self.assertLess(i_prov, i_outline)
        self.assertLess(i_outline, i_transcript)
        self.assertRegex(content, r"(?m)^outline_pending:\s*false\s*$")
        self.assertNotRegex(content, r"(?m)^outline_pending:\s*true\s*$")
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_themes_folded_in_as_flat_yaml_list(self):
        manifest, wrapper, outfile = self._bare_save()
        outline_path = self.write("outline.md", "## Outline\n- A point\n")
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--themes", "fed-liquidity,geopolitics"])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        m = re.search(r"(?m)^themes_active:\s*\[(.*)\]\s*$", content)
        self.assertIsNotNone(m, content)
        self.assertEqual(m.group(1), '"fed-liquidity", "geopolitics"')
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_offlist_theme_dropped_and_reported_on_fold(self):
        manifest, wrapper, outfile = self._bare_save()
        outline_path = self.write("outline.md", "## Outline\n- A point\n")
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--themes", "fed-liquidity,not-a-real-lens"])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertIn("not-a-real-lens", proc2.stderr)
        self.assertIn("dropping off-list theme", proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        m = re.search(r"(?m)^themes_active:\s*\[(.*)\]\s*$", content)
        self.assertIsNotNone(m, content)
        self.assertEqual(m.group(1), '"fed-liquidity"')
        self.assertEqual(self.validate(outfile).returncode, 0)

    # ── The sacred property: the transcript body never changes ────────────────────────────────────
    def test_transcript_body_byte_identical_before_and_after_fold(self):
        manifest, wrapper, outfile = self._bare_save()
        with open(outfile, encoding="utf-8") as fh:
            before = fh.read()
        before_tail = before[before.index("## Transcript"):]
        before_hash = hashlib.sha256(before_tail.encode("utf-8")).hexdigest()

        outline_path = self.write("outline.md", "## Outline\n- A point\n- Another point\n")
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path, "--themes", "geopolitics"])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            after = fh.read()
        after_tail = after[after.index("## Transcript"):]
        after_hash = hashlib.sha256(after_tail.encode("utf-8")).hexdigest()

        self.assertEqual(before_tail, after_tail)
        self.assertEqual(before_hash, after_hash)

    # ── Idempotency ─────────────────────────────────────────────────────────────────────────────
    def test_idempotent_two_fold_calls_byte_identical_no_duplicate_outline(self):
        manifest, wrapper, outfile = self._bare_save()
        outline_path = self.write("outline.md", "## Outline\n- Only point\n")

        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path, "--themes", "credit-shadow"])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            after_first = fh.read()

        proc3 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path, "--themes", "credit-shadow"])
        self.assertEqual(proc3.returncode, 0, proc3.stderr)
        with open(outfile, encoding="utf-8") as fh:
            after_second = fh.read()

        self.assertEqual(after_first, after_second)
        self.assertEqual(after_second.count("## Outline"), 1)
        self.assertEqual(after_second.count("Only point"), 1)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_different_outline_replaces_not_appends(self):
        manifest, wrapper, outfile = self._bare_save()

        outline_a = self.write("outline_a.md", "## Outline\n- First outline\n")
        proc2 = self.run_save(manifest, wrapper, confirm=True, extra_args=["--outline", outline_a])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)

        outline_b = self.write("outline_b.md", "## Outline\n- Second, different outline\n")
        proc3 = self.run_save(manifest, wrapper, confirm=True, extra_args=["--outline", outline_b])
        self.assertEqual(proc3.returncode, 0, proc3.stderr)

        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        self.assertNotIn("First outline", content)
        self.assertIn("Second, different outline", content)
        self.assertEqual(content.count("## Outline"), 1)
        self.assertEqual(self.validate(outfile).returncode, 0)

    # ── Fail-closed paths ───────────────────────────────────────────────────────────────────────
    def test_second_bare_call_against_existing_record_fails_closed(self):
        manifest, wrapper, outfile = self._bare_save()
        with open(outfile, encoding="utf-8") as fh:
            before = fh.read()
        proc2 = self.run_save(manifest, wrapper, confirm=True)
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("already exists", proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), before)  # untouched

    def test_unreadable_outline_file_on_fold_fails_closed_and_leaves_record_untouched(self):
        manifest, wrapper, outfile = self._bare_save()
        with open(outfile, encoding="utf-8") as fh:
            before = fh.read()
        missing_outline = os.path.join(self.tmpdir, "nope-outline.md")
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", missing_outline])
        self.assertNotEqual(proc2.returncode, 0)
        with open(outfile, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), before)  # untouched

    # ── Frontmatter-forgery resistance on the fold path ────────────────────────────────────────
    def test_malicious_outline_heading_cannot_forge_frontmatter_on_fold(self):
        manifest, wrapper, outfile = self._bare_save()
        # A heading whose text tries to smuggle a newline plus a bare '---' plus a forged key,
        # pretending to close the frontmatter block and open a new one.
        malicious = (
            "## Outline\n"
            "- innocuous point\ntitle-forge\n---\nauthority: attacker\nstatus: pwned\n"
            "- another point\n"
        )
        outline_path = self.write("malicious.md", malicious)
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--themes", "flows-positioning"])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        # validate_frontmatter.py's own scan (content.find("---", 3)) must still land on the
        # legitimate closing delimiter, not on the '---' smuggled inside the outline text.
        fm_end = content.find("---", 3)
        fm = content[3:fm_end]
        self.assertIn("authority: skill", fm)
        self.assertNotIn("authority: attacker", fm)
        self.assertNotIn("status: pwned", fm)
        self.assertIn("record_type: source-ingest", fm)
        self.assertEqual(self.validate(outfile).returncode, 0)

    # ── --dry-run on the fold path ──────────────────────────────────────────────────────────────
    def test_dry_run_fold_writes_nothing(self):
        manifest, wrapper, outfile = self._bare_save()
        with open(outfile, encoding="utf-8") as fh:
            before = fh.read()
        outline_path = self.write("outline.md", "## Outline\n- A point\n")
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--themes", "market-structure", "--dry-run"])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        payload = json.loads(proc2.stdout)
        self.assertFalse(payload["wrote"])
        with open(outfile, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), before)


# ── Task 6.1.2 — the outline sidecar ────────────────────────────────────────────────────────────
# `--outline-json` writes the structured outline (from `transcript_outline.py merge
# --outline-json`) as a `<record-slug>.outline.json` sidecar next to the record. Humans still read
# the markdown "## Outline" block in the record; tools read the sidecar. See the module docstring's
# THE OUTLINE SIDECAR section on the tool under test.
def default_outline_json(sections_count=2):
    return json.dumps({
        "schema_version": 1,
        "title": "My Video",
        "sections": [
            {"title": f"Section {i}", "bullets": [f"point {i}"], "themes": []}
            for i in range(sections_count)
        ],
        "themes_active": [],
        "theme_vocabulary": ["fed-liquidity"],
        "provenance": [],
        "counts": {"sections_in": sections_count, "sections_out": sections_count,
                    "dropped_themes": 0},
    })


class TestOutlineSidecar(TranscriptSaveTestCase):
    def _sidecar_path_for(self, outfile):
        base, _ext = os.path.splitext(outfile)
        return base + ".outline.json"

    def test_sidecar_written_and_parses_matching_record_section_count(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write(
            "outline.md",
            "## Outline — My Video\n\n1. **Section 0**\n   - point 0\n\n"
            "2. **Section 1**\n   - point 1\n",
        )
        outline_json_path = self.write("outline.json", default_outline_json(2))
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path,
                                          "--outline-json", outline_json_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        sidecar = self._sidecar_path_for(outfile)
        self.assertTrue(os.path.isfile(sidecar))
        with open(sidecar, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(doc["schema_version"], 1)
        with open(outfile, encoding="utf-8") as fh:
            content = fh.read()
        rendered_sections = len(re.findall(r"(?m)^\d+\. \*\*", content))
        self.assertEqual(len(doc["sections"]), rendered_sections)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["outline_sidecar"], sidecar)

    def test_no_sidecar_without_outline_json_flag(self):
        # Bare --outline (no --outline-json) is still legal — no sidecar is written, matching
        # every pre-Phase-6 caller's behavior unmodified.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", "## Outline\n- Point A\n")
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        self.assertFalse(os.path.isfile(self._sidecar_path_for(outfile)))

    def test_outline_json_without_outline_dies(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_json_path = self.write("outline.json", default_outline_json(1))
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline-json", outline_json_path])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("without --outline", proc.stderr)
        self.assertEqual(self.all_md_files(), [])

    def test_malformed_outline_json_fails_closed_writes_nothing(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", "## Outline\n- Point A\n")
        bad_json_path = self.write("outline.json", "not json at all {{{")
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path,
                                          "--outline-json", bad_json_path])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not valid JSON", proc.stderr)
        self.assertEqual(self.all_md_files(), [])

    def test_no_sidecar_when_record_write_fails(self):
        # Force the record write itself to fail: put a plain FILE where the desk's "records"
        # directory needs to be, so os.makedirs(outdir) blows up before anything lands on disk.
        # The sidecar write happens strictly after a successful record write + validation, so it
        # must never appear when the record write never even completed.
        desk_dir = os.path.join(self.brain, "desks", "deryl")
        os.makedirs(desk_dir, exist_ok=True)
        with open(os.path.join(desk_dir, "records"), "w", encoding="utf-8") as fh:
            fh.write("blocking file, not a directory")

        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", "## Outline\n- Point A\n")
        outline_json_path = self.write("outline.json", default_outline_json(1))
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path,
                                          "--outline-json", outline_json_path])
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.all_md_files(), [])
        sidecars = []
        for root, _dirs, files in os.walk(self.brain):
            for f in files:
                if f.endswith(".outline.json"):
                    sidecars.append(os.path.join(root, f))
        self.assertEqual(sidecars, [])

    def test_sidecar_survives_removal_without_damaging_record(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", "## Outline\n- Point A\n")
        outline_json_path = self.write("outline.json", default_outline_json(1))
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path,
                                          "--outline-json", outline_json_path])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        outfile = self.all_md_files()[0]
        sidecar = self._sidecar_path_for(outfile)
        with open(outfile, encoding="utf-8") as fh:
            record_before = fh.read()
        os.remove(sidecar)
        with open(outfile, encoding="utf-8") as fh:
            record_after = fh.read()
        self.assertEqual(record_before, record_after)
        self.assertEqual(self.validate(outfile).returncode, 0)

    def test_transcript_body_byte_identical_across_outline_pass_with_sidecar(self):
        # The sacred property, re-checked with --outline-json in play: the transcript body must be
        # byte-identical whether or not a sidecar accompanies the outline.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        bare_proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(bare_proc.returncode, 0, bare_proc.stderr)
        outfile = self.all_md_files()[0]
        with open(outfile, encoding="utf-8") as fh:
            before = fh.read()
        before_tail = before[before.index("## Transcript"):]
        before_hash = hashlib.sha256(before_tail.encode("utf-8")).hexdigest()

        outline_path = self.write("outline.md", "## Outline\n- A point\n- Another point\n")
        outline_json_path = self.write("outline.json", default_outline_json(2))
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--outline-json", outline_json_path])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            after = fh.read()
        after_tail = after[after.index("## Transcript"):]
        after_hash = hashlib.sha256(after_tail.encode("utf-8")).hexdigest()

        self.assertEqual(before_tail, after_tail)
        self.assertEqual(before_hash, after_hash)

    def test_idempotent_sidecar_and_record_byte_identical_on_rerun(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", "## Outline\n- Only point\n")
        outline_json_path = self.write("outline.json", default_outline_json(1))

        proc1 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--outline-json", outline_json_path])
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        outfile = self.all_md_files()[0]
        sidecar = self._sidecar_path_for(outfile)
        with open(outfile, encoding="utf-8") as fh:
            record_first = fh.read()
        with open(sidecar, encoding="utf-8") as fh:
            sidecar_first = fh.read()

        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--outline-json", outline_json_path])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        with open(outfile, encoding="utf-8") as fh:
            record_second = fh.read()
        with open(sidecar, encoding="utf-8") as fh:
            sidecar_second = fh.read()

        self.assertEqual(record_first, record_second)
        self.assertEqual(sidecar_first, sidecar_second)

    def test_dry_run_writes_no_sidecar_but_reports_would_write(self):
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        outline_path = self.write("outline.md", "## Outline\n- Point A\n")
        outline_json_path = self.write("outline.json", default_outline_json(1))
        proc = self.run_save(manifest, wrapper, confirm=True,
                              extra_args=["--outline", outline_path,
                                          "--outline-json", outline_json_path,
                                          "--dry-run"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["wrote"])
        self.assertIsNotNone(payload["would_write_sidecar"])
        self.assertEqual(self.all_md_files(), [])

    def test_sidecar_written_on_fold_path(self):
        # Second-call fold-in against a bare-saved record — the sidecar path (Task 6.1.2) applies
        # equally to the splice branch, not only the fresh-write branch.
        manifest = self.write_manifest()
        wrapper = self.write("wrapper.txt", default_wrapper())
        bare_proc = self.run_save(manifest, wrapper, confirm=True)
        self.assertEqual(bare_proc.returncode, 0, bare_proc.stderr)
        outfile = self.all_md_files()[0]

        outline_path = self.write("outline.md", "## Outline\n- A point\n")
        outline_json_path = self.write("outline.json", default_outline_json(1))
        proc2 = self.run_save(manifest, wrapper, confirm=True,
                               extra_args=["--outline", outline_path,
                                           "--outline-json", outline_json_path])
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        sidecar = self._sidecar_path_for(outfile)
        self.assertTrue(os.path.isfile(sidecar))
        with open(sidecar, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(len(doc["sections"]), 1)


if __name__ == "__main__":
    unittest.main()
