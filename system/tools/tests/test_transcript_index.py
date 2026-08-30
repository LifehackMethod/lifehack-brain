#!/usr/bin/env python3
"""test_transcript_index.py — unit tests for transcript_index.py.

Phase 6 (2026-08-27): transcript_index.py no longer parses markdown headings out of a record's
body. It reads the outline sidecar (`<record-slug>.outline.json`, schema_version 1, written by
`transcript_outline.py merge --outline-json` / `youtube_transcript_save.py --outline-json`) via
`transcript_outline.load_outline_document`. These tests build that sidecar directly rather than
running the outline pipeline end to end -- this file's job is transcript_index.py's own behavior,
not the outline generator's.

All synthetic. A fake records folder is built under a fresh `tempfile.mkdtemp()` for every test
(never `dir=`, never a wildcard `rm`) and torn down with `shutil.rmtree` on that exact path. The
real notes tree is never at risk: `brain_root.resolve_brain_root` is monkeypatched directly to
point at the fake folder, rather than relying on `$LIFEHACK_ROOT` -- clearing that env var alone
has previously fallen through to a repo pointer and reached live data.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_HERE)


def _repo_root():
    d = _TOOLS_DIR
    while True:
        if os.path.exists(os.path.join(d, "shared", "paths.py")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise RuntimeError("cannot locate the repo root (no shared/paths.py above this file)")
        d = parent


_ROOT = _repo_root()
sys.path.insert(0, _TOOLS_DIR)
sys.path.insert(0, os.path.join(_ROOT, "shared"))

import transcript_index as ti  # noqa: E402
import transcript_outline as to  # noqa: E402
import brain_root  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────────────────────────────────────
# Frontmatter blocks shared by several records. The markdown BODY is deliberately full of prose
# that must never appear in a rendered index -- intro prose above the outline, bullet text, and
# transcript body text below '## Transcript' -- since headings/themes now come only from the
# sidecar, none of it should ever be read for structure, and none of it should ever leak.

RECORD_WITH_SIDECAR = """---
title: "Weekly Wrap — Aug 20"
created_at: 2026-08-20
content_class: transcript
confidence: HIGH
themes_active: [fed-liquidity, credit-shadow]
source_refs: [zoom-2026-08-20]
word_count: 4200
reader_verdict: thorough
---

# Weekly Wrap — Aug 20

Some intro prose that must never appear in the index.

## Outline — Weekly Wrap

1. **Opening Remarks**
   - point about the Fed, must never leak
   - _themes: fed-liquidity_

2. **Credit Spreads Widen**
   - spreads gapped out Tuesday, must never leak
   - _themes: credit-shadow_

## Transcript

Body text that must never leak either.
"""

RECORD_WITH_SIDECAR_SECTIONS = [
    {"title": "Opening Remarks", "bullets": ["point about the Fed, must never leak"],
     "themes": ["fed-liquidity"]},
    {"title": "Credit Spreads Widen", "bullets": ["spreads gapped out Tuesday, must never leak"],
     "themes": ["credit-shadow"]},
]

RECORD_NOTHING_TO_SHOW = """---
title: "Ad-Hoc Note — Aug 18"
created_at: 2026-08-18
content_class: note
confidence: LOW
themes_active: [geopolitics]
source_refs: [email-thread-9]
word_count: 300
reader_verdict: thin
---

# Ad-Hoc Note

No outline section here at all — just prose that must not leak into the index.
"""

RECORD_LEGACY_NO_SIDECAR = """---
title: "Legacy Outline — Aug 17"
created_at: 2026-08-17
content_class: transcript
confidence: MEDIUM
themes_active: [fed-liquidity]
source_refs: [zoom-2026-08-17]
word_count: 1200
reader_verdict: thin
---

# Legacy Outline

## Outline

1. **Old Style Heading, must not leak**
   - a bullet, must not leak
   - _themes: fed-liquidity_

## Transcript

Body text that must never leak.
"""

RECORD_OUTLINE_PENDING = """---
title: "Pending Session — Aug 27"
created_at: 2026-08-27
content_class: transcript
confidence: MEDIUM
source_refs: [zoom-2026-08-27-b]
word_count: 1500
reader_verdict: thorough
outline_pending: true
---

# Pending Session

Full transcript body already saved by the tool-less reader; the outline has not been generated
yet.
"""

RECORD_OFF_LIST_THEME = """---
title: "Odd Session — Aug 22"
created_at: 2026-08-22
content_class: transcript
confidence: MEDIUM
themes_active: [crypto-speculation]
source_refs: [zoom-2026-08-22]
word_count: 900
reader_verdict: mixed
---

# Odd Session

No sidecar for this one; only frontmatter matters for this test.
"""

RECORD_MALFORMED = """---
title: "Broken Record"
created_at: 2026-08-19
content_class: transcript
confidence: HIGH
themes_active: [fed-liquidity]
source_refs: [zoom-2026-08-19]
reader_verdict: thorough

# frontmatter block is never closed with a second '---' line -- deliberately malformed
"""

RECORD_BAD_CREATED_AT = """---
title: "Bad Date Record"
created_at: not-a-date
content_class: transcript
confidence: HIGH
themes_active: [fed-liquidity]
source_refs: [zoom-2026-08-01]
word_count: 400
reader_verdict: thin
---

# Bad Date Record

No outline section here.
"""

# Task 6.2.1's explicit regression fixture: a transcript BODY (below '## Transcript') containing a
# literal '## Outline' line followed by numbered-bold text mimicking a real generated section. No
# real outline exists above '## Transcript', and no sidecar exists either. Nothing here may ever
# reach the rendered index -- headings must be empty and there must be no note, since the decoy
# lives below the boundary this module refuses to look past even for the legacy-note check.
RECORD_TRANSCRIPT_BODY_LOOKALIKE = """---
title: "Outline Lookalike In Body — Aug 26"
created_at: 2026-08-26
content_class: transcript
confidence: MEDIUM
themes_active: [fed-liquidity]
source_refs: [zoom-2026-08-26]
word_count: 800
reader_verdict: thin
---

# Outline Lookalike In Body

## Transcript

The host said, "let me give you an outline of my week."

## Outline

1. **This must never become a heading**
   - this bullet must never leak into the index either
   - _themes: fed-liquidity_
"""


def _write_sidecar(folder, record_filename, sections, schema_version=1, title=""):
    """Write a Phase 6 outline sidecar next to `record_filename`, using the exact naming
    convention `transcript_index.outline_sidecar_path` (and `youtube_transcript_save.py`) use:
    the record's own filename with '.md' replaced by '.outline.json'."""
    base, _ext = os.path.splitext(record_filename)
    sidecar_name = base + ".outline.json"
    doc = {
        "schema_version": schema_version,
        "title": title,
        "sections": sections,
        "themes_active": sorted({t for s in sections for t in s.get("themes", [])}),
        "theme_vocabulary": [],
        "provenance": [],
        "counts": {
            "sections_in": len(sections),
            "sections_out": len(sections),
            "dropped_themes": 0,
        },
    }
    with open(os.path.join(folder, sidecar_name), "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return sidecar_name


class TranscriptIndexTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix="ti-")
        self.brain_root = os.path.join(self.tmp_root, "brain")
        self.folder = os.path.join(self.brain_root, "desks", "marc", "records", "source-ingests")
        os.makedirs(self.folder, exist_ok=True)
        # Monkeypatch the resolver directly -- never rely on $LIFEHACK_ROOT alone. Clearing that
        # env var without also patching the resolver has previously fallen through to this repo's
        # own .brain-root pointer (or the persisted machine-global config) and reached live data.
        self._patcher = mock.patch.object(
            brain_root, "resolve_brain_root", return_value=("test", self.brain_root)
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def write_record(self, name, content):
        with open(os.path.join(self.folder, name), "w", encoding="utf-8") as fh:
            fh.write(content)


class TestFindRepoRoot(TranscriptIndexTestBase):
    def test_finds_real_repo_root(self):
        found = ti.find_repo_root(_TOOLS_DIR)
        self.assertEqual(found, _ROOT)

    def test_returns_none_when_nothing_above(self):
        # A directory guaranteed to have no shared/paths.py above it in isolation is hard to fake
        # portably; instead confirm the walk terminates (doesn't loop forever) starting from root.
        found = ti.find_repo_root("/")
        self.assertIn(found, (None,))


class TestSidecarOutline(TranscriptIndexTestBase):
    def test_ordering_newest_first(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        self.write_record("b-note.md", RECORD_NOTHING_TO_SHOW)
        records = ti.load_records(self.folder)
        rendered = ti.render_index(records)
        pos_20 = rendered.index("Weekly Wrap — Aug 20")
        pos_18 = rendered.index("Ad-Hoc Note — Aug 18")
        self.assertLess(pos_20, pos_18, "2026-08-20 record must render before the 08-18 record")

    def test_sidecar_headings_and_themes_extracted_bullets_excluded(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        records = ti.load_records(self.folder)
        rec = records[0]
        self.assertEqual(rec["_headings"], ["Opening Remarks", "Credit Spreads Widen"])
        self.assertEqual(rec["_heading_themes"]["Opening Remarks"], ["fed-liquidity"])
        self.assertEqual(rec["_heading_themes"]["Credit Spreads Widen"], ["credit-shadow"])
        rendered = ti.render_index(records)
        self.assertIn("Opening Remarks", rendered)
        self.assertIn("Credit Spreads Widen", rendered)
        # bullets are never read from the sidecar's structure into a heading, and never rendered
        self.assertNotIn("point about the Fed", rendered)
        self.assertNotIn("spreads gapped out Tuesday", rendered)

    def test_no_body_or_bullet_text_leaks_into_rendered_index(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        self.write_record("b-note.md", RECORD_NOTHING_TO_SHOW)
        records = ti.load_records(self.folder)
        rendered = ti.render_index(records)
        self.assertNotIn("must never appear in the index", rendered)
        self.assertNotIn("must never leak", rendered)
        self.assertNotIn("must not leak into the index", rendered)

    def test_off_list_theme_is_carried_through_from_frontmatter(self):
        self.write_record("c-odd.md", RECORD_OFF_LIST_THEME)
        records = ti.load_records(self.folder)
        rendered = ti.render_index(records)
        self.assertIn("crypto-speculation", rendered)

    def test_case1_outline_pending_no_sidecar_renders_marker_no_note(self):
        self.write_record("f-pending.md", RECORD_OUTLINE_PENDING)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            records = ti.load_records(self.folder)
        self.assertEqual(stderr.getvalue(), "", "a pending record must never trigger a note")
        self.assertEqual(records[0]["_headings"], [])
        self.assertTrue(records[0]["_outline_pending"])
        rendered = ti.render_index(records)
        self.assertIn("- outline: (pending — outline not yet generated)", rendered)
        self.assertNotIn("- outline: (none)", rendered)

    def test_case2_legacy_no_sidecar_emits_one_line_note(self):
        self.write_record("g-legacy.md", RECORD_LEGACY_NO_SIDECAR)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            records = ti.load_records(self.folder)
        err = stderr.getvalue()
        self.assertIn("NOTE", err)
        self.assertIn("g-legacy.md", err)
        self.assertIn("predates the outline sidecar", err)
        self.assertEqual(err.count("\n"), 1, "exactly one line on stderr")
        self.assertEqual(records[0]["_headings"], [])
        rendered = ti.render_index(records)
        self.assertIn("outline: (none)", rendered)
        # the legacy markdown outline's own content must never leak, only the note (and the note
        # never contains the outline's own heading text)
        self.assertNotIn("Old Style Heading", rendered)
        self.assertNotIn("Old Style Heading", err)

    def test_case3_nothing_to_show_no_sidecar_no_pending_no_legacy_block_no_note(self):
        self.write_record("b-note.md", RECORD_NOTHING_TO_SHOW)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            records = ti.load_records(self.folder)
        self.assertEqual(stderr.getvalue(), "")
        self.assertFalse(records[0]["_outline_pending"])
        self.assertEqual(records[0]["_headings"], [])
        rendered = ti.render_index(records)
        self.assertIn("outline: (none)", rendered)

    def test_transcript_body_lookalike_outline_is_not_legacy_and_does_not_leak(self):
        # Task 6.2.1's regression fixture: the decoy '## Outline' + numbered-bold text lives BELOW
        # '## Transcript', so it must not even trigger the legacy note (that check itself is
        # bounded to stop at the transcript boundary), and none of its text may reach the index.
        self.write_record("i-lookalike.md", RECORD_TRANSCRIPT_BODY_LOOKALIKE)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            records = ti.load_records(self.folder)
        self.assertEqual(stderr.getvalue(), "", "a decoy below '## Transcript' must never warn or note")
        rec = records[0]
        self.assertEqual(rec["_headings"], [])
        rendered = ti.render_index(records)
        self.assertNotIn("This must never become a heading", rendered)
        self.assertNotIn("this bullet must never leak into the index either", rendered)
        self.assertNotIn("let me give you an outline of my week", rendered)
        self.assertIn("outline: (none)", rendered)

    def test_unknown_schema_version_fails_loudly_naming_file_and_both_versions(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS, schema_version=99)
        with self.assertRaises(ti.FrontmatterError) as ctx:
            ti.load_records(self.folder)
        msg = str(ctx.exception)
        self.assertIn("a-wrap.outline.json", msg)
        self.assertIn("99", msg)
        self.assertIn(str(to.OUTLINE_JSON_SCHEMA_VERSION), msg)

    def test_malformed_sidecar_json_fails_closed_not_traceback(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        with open(os.path.join(self.folder, "a-wrap.outline.json"), "w", encoding="utf-8") as fh:
            fh.write("{not valid json")
        with self.assertRaises(ti.FrontmatterError) as ctx:
            ti.load_records(self.folder)
        self.assertIn("a-wrap.md", str(ctx.exception))

    def test_malformed_frontmatter_fails_closed(self):
        self.write_record("z-broken.md", RECORD_MALFORMED)
        with self.assertRaises(ti.FrontmatterError) as ctx:
            ti.load_records(self.folder)
        self.assertIn("z-broken.md", str(ctx.exception))

    def test_malformed_created_at_fails_closed(self):
        self.write_record("k-baddate.md", RECORD_BAD_CREATED_AT)
        with self.assertRaises(ti.FrontmatterError) as ctx:
            ti.load_records(self.folder)
        self.assertIn("k-baddate.md", str(ctx.exception))
        self.assertIn("created_at", str(ctx.exception))

    def test_no_rendered_line_originates_below_transcript_heading(self):
        # Structural regression: across a mix of sidecar-backed, legacy, pending, and decoy
        # records, nothing living below any record's '## Transcript' heading may ever appear in
        # the rendered index.
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        self.write_record("g-legacy.md", RECORD_LEGACY_NO_SIDECAR)
        self.write_record("i-lookalike.md", RECORD_TRANSCRIPT_BODY_LOOKALIKE)
        self.write_record("f-pending.md", RECORD_OUTLINE_PENDING)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            records = ti.load_records(self.folder)
        rendered = ti.render_index(records)
        below_transcript_snippets = [
            "Body text that must never leak either",
            "Body text that must never leak",
            "The host said",
            "This must never become a heading",
            "this bullet must never leak into the index either",
            "Old Style Heading",
        ]
        for snippet in below_transcript_snippets:
            self.assertNotIn(snippet, rendered)

    def test_write_is_idempotent_with_pending_and_sidecar_mixed(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        self.write_record("f-pending.md", RECORD_OUTLINE_PENDING)
        out_path = os.path.join(self.folder, "_index.md")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ti.main(["--desk", "marc", "--write"])
        with open(out_path, "rb") as fh:
            first = fh.read()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ti.main(["--desk", "marc", "--write"])
        with open(out_path, "rb") as fh:
            second = fh.read()
        self.assertEqual(first, second, "two --write runs must produce a byte-identical file")


class TestCliDryRunAndWrite(TranscriptIndexTestBase):
    def test_dry_run_default_writes_nothing(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        out_path = os.path.join(self.folder, "_index.md")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = ti.main(["--desk", "marc"])
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(out_path), "dry run must not write _index.md")
        self.assertIn("DRY RUN", stdout.getvalue())

    def test_write_creates_index_file(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        out_path = os.path.join(self.folder, "_index.md")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = ti.main(["--desk", "marc", "--write"])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile(out_path))

    def test_write_is_idempotent(self):
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        self.write_record("b-note.md", RECORD_NOTHING_TO_SHOW)
        out_path = os.path.join(self.folder, "_index.md")
        with contextlib.redirect_stdout(io.StringIO()):
            ti.main(["--desk", "marc", "--write"])
        with open(out_path, "rb") as fh:
            first = fh.read()
        with contextlib.redirect_stdout(io.StringIO()):
            ti.main(["--desk", "marc", "--write"])
        with open(out_path, "rb") as fh:
            second = fh.read()
        self.assertEqual(first, second, "two --write runs must produce a byte-identical file")

    def test_malformed_record_fails_closed_via_cli(self):
        self.write_record("z-broken.md", RECORD_MALFORMED)
        out_path = os.path.join(self.folder, "_index.md")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = ti.main(["--desk", "marc", "--write"])
        self.assertNotEqual(code, 0)
        self.assertFalse(os.path.exists(out_path), "a malformed record must abort the whole write")
        self.assertIn("FAIL", stderr.getvalue())

    def test_missing_folder_fails_closed(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = ti.main(["--desk", "nonexistent-desk"])
        self.assertNotEqual(code, 0)
        self.assertIn("FAIL", stderr.getvalue())

    def test_brain_root_not_set_fails_closed(self):
        stderr = io.StringIO()
        with mock.patch.object(brain_root, "resolve_brain_root", return_value=(None, None)):
            with contextlib.redirect_stderr(stderr):
                code = ti.main(["--desk", "marc"])
        self.assertNotEqual(code, 0)
        self.assertIn("NOT-SET", stderr.getvalue())


class TestBomAndInvalidEncoding(TranscriptIndexTestBase):
    def test_non_utf8_bytes_raise_named_error_not_traceback(self):
        path = os.path.join(self.folder, "l-badbytes.md")
        with open(path, "wb") as fh:
            fh.write(b"---\ntitle: \xff\xfe garbage bytes here\n---\nbody\n")
        with self.assertRaises(ti.FrontmatterError) as ctx:
            ti.load_records(self.folder)
        self.assertIn("l-badbytes.md", str(ctx.exception))

    def test_bom_record_does_not_abort_the_other_records_index(self):
        bom_content = "﻿" + RECORD_OFF_LIST_THEME
        self.write_record("m-bom.md", bom_content)
        self.write_record("a-wrap.md", RECORD_WITH_SIDECAR)
        _write_sidecar(self.folder, "a-wrap.md", RECORD_WITH_SIDECAR_SECTIONS)
        records = ti.load_records(self.folder)
        self.assertEqual(len(records), 2)
        rendered = ti.render_index(records)
        self.assertIn("Odd Session — Aug 22", rendered)
        self.assertIn("Weekly Wrap — Aug 20", rendered)


if __name__ == "__main__":
    unittest.main()
