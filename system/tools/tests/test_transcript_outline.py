#!/usr/bin/env python3
"""test_transcript_outline.py — unit tests for transcript_outline.py.

All synthetic: no network, no real transcript files, nothing from the notes tree. Chunk-writing
tests use the real `scratch_dir`/`scratch_file` (they already resolve to the machine's own temp
folder, per `shared/paths.py`) so the `rdr`-segment assertion is checked against the real code path,
not a mock.
"""

import json
import os
import re
import sys
import tempfile
import unittest

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

import transcript_outline as to  # noqa: E402


def make_transcript(word_count, word="word"):
    return " ".join(f"{word}{i}" for i in range(word_count))


def write_seam_fixture(before_words, overlap_words, after_words):
    """Build two REAL chunk files on disk, laid out exactly the way `plan` lays out adjacent
    chunks: chunk 0 = before + overlap, chunk 1 = overlap + after, so the overlap text is
    byte-identical in both files (that identity is the whole positional signal). Uses
    tempfile.mkdtemp() with no dir= per the test brief. Returns the plan-shaped chunk list
    (index/path/word_start/word_end/word_count) merge_sections expects as `chunk_plan`."""
    tmp_dir = tempfile.mkdtemp()
    chunk0_words = before_words + overlap_words
    chunk1_words = overlap_words + after_words
    path0 = os.path.join(tmp_dir, "chunk-00.txt")
    path1 = os.path.join(tmp_dir, "chunk-01.txt")
    with open(path0, "w", encoding="utf-8") as fh:
        fh.write(" ".join(chunk0_words))
    with open(path1, "w", encoding="utf-8") as fh:
        fh.write(" ".join(chunk1_words))
    word_start1 = len(before_words)
    return [
        {"index": 0, "path": path0, "word_start": 0, "word_end": len(chunk0_words),
         "word_count": len(chunk0_words)},
        {"index": 1, "path": path1, "word_start": word_start1,
         "word_end": word_start1 + len(chunk1_words), "word_count": len(chunk1_words)},
    ]


class TestChunkArithmetic(unittest.TestCase):
    def test_zero_words(self):
        cw, ranges, enlarged = to.compute_chunk_plan(0)
        self.assertEqual(ranges, [])
        self.assertFalse(enlarged)

    def test_one_word(self):
        cw, ranges, enlarged = to.compute_chunk_plan(1)
        self.assertEqual(ranges, [(0, 1)])
        self.assertFalse(enlarged)

    def test_exactly_one_chunk_boundary(self):
        # exactly CHUNK_WORDS words -> single chunk, no overlap needed
        cw, ranges, enlarged = to.compute_chunk_plan(to.CHUNK_WORDS)
        self.assertEqual(ranges, [(0, to.CHUNK_WORDS)])
        self.assertFalse(enlarged)

    def test_one_word_over_boundary_makes_two_chunks(self):
        wc = to.CHUNK_WORDS + 1
        cw, ranges, enlarged = to.compute_chunk_plan(wc)
        self.assertEqual(len(ranges), 2)
        # full coverage: last range ends exactly at word_count
        self.assertEqual(ranges[-1][1], wc)
        self.assertEqual(ranges[0][0], 0)

    def test_overlap_is_present_between_adjacent_chunks(self):
        wc = to.CHUNK_WORDS + 1000
        cw, ranges, enlarged = to.compute_chunk_plan(wc, chunk_words=to.CHUNK_WORDS,
                                                       overlap_words=to.OVERLAP_WORDS)
        self.assertGreaterEqual(len(ranges), 2)
        for (s0, e0), (s1, e1) in zip(ranges, ranges[1:]):
            overlap = e0 - s1
            self.assertEqual(overlap, to.OVERLAP_WORDS)

    def test_full_coverage_no_gaps(self):
        wc = 25000
        cw, ranges, enlarged = to.compute_chunk_plan(wc)
        # every word index must be covered by at least one range
        covered = [False] * wc
        for s, e in ranges:
            for i in range(s, e):
                covered[i] = True
        self.assertTrue(all(covered))


class TestCapBehaviour(unittest.TestCase):
    def test_cap_not_exceeded_and_size_enlarged(self):
        # Force a word count that would need more than max_chunks at the default chunk size.
        max_chunks = 3
        wc = to.CHUNK_WORDS * 10  # would need far more than 3 chunks at default size
        cw, ranges, enlarged = to.compute_chunk_plan(wc, max_chunks=max_chunks)
        self.assertLessEqual(len(ranges), max_chunks)
        self.assertTrue(enlarged)
        self.assertGreater(cw, to.CHUNK_WORDS)
        # still full coverage despite the enlargement
        self.assertEqual(ranges[-1][1], wc)
        self.assertEqual(ranges[0][0], 0)

    def test_cap_not_triggered_when_unnecessary(self):
        wc = 500
        cw, ranges, enlarged = to.compute_chunk_plan(wc, max_chunks=12)
        self.assertFalse(enlarged)
        self.assertEqual(cw, to.CHUNK_WORDS)

    def test_plan_cli_warns_loudly_on_enlargement(self):
        import io
        import contextlib

        text = make_transcript(to.CHUNK_WORDS * 10)
        text_path = os.path.join(to.scratch_dir("test-outline-src"), "big.txt")
        with open(text_path, "w", encoding="utf-8") as fh:
            fh.write(text)

        class Args:
            text = text_path
            title = "Cap Test Transcript"
            max_agents = 3
            json = True

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            to.cmd_plan(Args())

        self.assertIn("WARNING", stderr.getvalue())
        self.assertIn("enlarged", stderr.getvalue().lower())
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["cap_enlarged_chunk_size"])
        self.assertLessEqual(result["chunk_count"], 3)


class TestChunkFilesUnderRdr(unittest.TestCase):
    def test_emitted_chunk_paths_land_under_rdr(self):
        import io
        import contextlib

        text = make_transcript(9000)
        text_path = os.path.join(to.scratch_dir("test-outline-src"), "mid.txt")
        with open(text_path, "w", encoding="utf-8") as fh:
            fh.write(text)

        class Args:
            text = text_path
            title = "Rdr Path Test"
            max_agents = 12
            json = True

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            to.cmd_plan(Args())

        result = json.loads(stdout.getvalue())
        self.assertGreater(len(result["chunks"]), 0)
        for chunk in result["chunks"]:
            parts = chunk["path"].split(os.sep)
            self.assertIn("rdr", parts, f"chunk path missing rdr segment: {chunk['path']}")
            self.assertTrue(os.path.isfile(chunk["path"]))


class TestSeamDeduplication(unittest.TestCase):
    def test_near_duplicate_adjacent_titles_collapse(self):
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {
                "chunk_index": 0,
                "sections": [
                    {"title": "The Fed's Balance Sheet", "start_marker": "today we discuss",
                     "bullets": ["QT continues"], "themes": ["fed-liquidity"]},
                ],
            },
            {
                "chunk_index": 1,
                "sections": [
                    {"title": "Fed Balance Sheet", "start_marker": "continuing on the fed",
                     "bullets": ["rate cuts priced in"], "themes": ["fed-liquidity"]},
                    {"title": "Geopolitics Update", "start_marker": "moving to the middle east",
                     "bullets": ["oil supply risk"], "themes": ["geopolitics"]},
                ],
            },
        ]
        merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(len(merged), 2)
        self.assertIn("QT continues", merged[0]["bullets"])
        self.assertIn("rate cuts priced in", merged[0]["bullets"])
        self.assertEqual(merged[1]["title"], "Geopolitics Update")
        self.assertEqual(dropped, 0)

    def test_distinct_adjacent_titles_do_not_collapse(self):
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Opening Remarks", "start_marker": "welcome",
                 "bullets": ["intro"], "themes": []},
            ]},
            {"chunk_index": 1, "sections": [
                {"title": "Credit Markets", "start_marker": "turning to credit",
                 "bullets": ["spreads widen"], "themes": ["credit-shadow"]},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(len(merged), 2)


class TestSeamPositionalDedup(unittest.TestCase):
    """Real-data regression: on an 8,635-word/3-chunk transcript, title similarity collapsed
    NOTHING (20 sections in, 20 out) even though two seams were plainly the same exchange split
    across a cut. These fixtures mirror the titles/bullets of the two real pairs, with genuinely
    different bullet text on each side, so a merge here can only be explained by the positional
    signal — not by the bullets happening to overlap."""

    def test_real_pair_1_mission_creep_collapses(self):
        valid = set(to._FALLBACK_THEMES)
        overlap = ("mission creep critique isn't going away and the framework review needs to "
                   "happen before we can honestly answer that").split()
        chunk_plan = write_seam_fixture(
            before_words=["earlier"] * 60,
            overlap_words=overlap,
            after_words=["moving", "on"] * 60,
        )
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Mission creep critique and the framework review",
                 "start_marker": "mission creep critique isn't going away",
                 "bullets": ["question left hanging as chunk cuts off"],
                 "themes": ["fiscal-currency"]},
            ]},
            {"chunk_index": 1, "sections": [
                {"title": "Mission creep critique and QE in hindsight",
                 "start_marker": "the framework review needs to happen",
                 "bullets": ["hindsight take on QE effectiveness"],
                 "themes": ["fed-liquidity"]},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid, chunk_plan)
        self.assertEqual(len(merged), 1)
        self.assertIn("question left hanging as chunk cuts off", merged[0]["bullets"])
        self.assertIn("hindsight take on QE effectiveness", merged[0]["bullets"])
        self.assertIn("fiscal-currency", merged[0]["themes"])
        self.assertIn("fed-liquidity", merged[0]["themes"])

    def test_real_pair_2_hard_data_collapses(self):
        valid = set(to._FALLBACK_THEMES)
        overlap = ("why wait for hard data when soft data already tells the story patience is "
                   "the whole game here").split()
        chunk_plan = write_seam_fixture(
            before_words=["context"] * 60,
            overlap_words=overlap,
            after_words=["next", "topic"] * 60,
        )
        chunk_results = [
            {"chunk_index": 1, "sections": [
                {"title": "Why wait for hard data",
                 "start_marker": "why wait for hard data",
                 "bullets": ["soft data leads the cycle"], "themes": []},
            ]},
            {"chunk_index": 2, "sections": [
                {"title": "Patience on soft versus hard data",
                 "start_marker": "patience is the whole game",
                 "bullets": ["patience framed as the discipline"], "themes": []},
            ]},
        ]
        # chunk_plan indices must match the chunk_index values used above (1 and 2, not 0 and 1).
        chunk_plan[0]["index"] = 1
        chunk_plan[1]["index"] = 2
        merged, dropped = to.merge_sections(chunk_results, valid, chunk_plan)
        self.assertEqual(len(merged), 1)
        self.assertIn("soft data leads the cycle", merged[0]["bullets"])
        self.assertIn("patience framed as the discipline", merged[0]["bullets"])

    def test_genuinely_different_seam_sections_do_not_collapse(self):
        # Same seam shape (overlap really exists between the two chunks), but the second chunk's
        # first section's start_marker sits in the genuinely-new "after" text, not the overlap —
        # exactly what a real topic change right at a seam looks like. Titles/bullets are also
        # unrelated so the text fallback cannot fire either.
        valid = set(to._FALLBACK_THEMES)
        overlap = ("and that wraps up the balance sheet discussion for today's session").split()
        after = ("turning now to an entirely unrelated subject the labor market printed a "
                 "surprise this week").split()
        chunk_plan = write_seam_fixture(
            before_words=["earlier"] * 60, overlap_words=overlap, after_words=after,
        )
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Balance Sheet Wrap-up", "start_marker": "and that wraps up",
                 "bullets": ["QT pace unchanged"], "themes": ["fed-liquidity"]},
            ]},
            {"chunk_index": 1, "sections": [
                {"title": "Labor Market Surprise", "start_marker": "turning now to an entirely",
                 "bullets": ["payrolls beat expectations"], "themes": ["secular-growth"]},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid, chunk_plan)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["title"], "Balance Sheet Wrap-up")
        self.assertEqual(merged[1]["title"], "Labor Market Surprise")

    def test_nonadjacent_similar_title_never_collapses(self):
        # chunk 0 and chunk 2 share a near-identical title, but chunk 1 sits between them, so
        # chunk 2's first section is never compared to chunk 0's — only strictly adjacent
        # chunk-index pairs are ever seam candidates.
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Recap of Fed Policy", "start_marker": "to recap fed policy",
                 "bullets": ["balance sheet unchanged"], "themes": ["fed-liquidity"]},
            ]},
            {"chunk_index": 1, "sections": [
                {"title": "Unrelated Middle Topic", "start_marker": "moving along",
                 "bullets": ["something else entirely"], "themes": []},
            ]},
            {"chunk_index": 2, "sections": [
                {"title": "Recap of Fed Policy", "start_marker": "to recap fed policy again",
                 "bullets": ["a second, later recap"], "themes": ["fed-liquidity"]},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0]["title"], "Recap of Fed Policy")
        self.assertEqual(merged[2]["title"], "Recap of Fed Policy")
        self.assertIn("a second, later recap", merged[2]["bullets"])
        self.assertNotIn("a second, later recap", merged[0]["bullets"])

    def test_merge_unions_bullets_and_themes_from_both_sides(self):
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "The Fed's Balance Sheet", "start_marker": "today we discuss",
                 "bullets": ["QT continues", "shared bullet"],
                 "themes": ["fed-liquidity", "market-structure"]},
            ]},
            {"chunk_index": 1, "sections": [
                {"title": "Fed Balance Sheet", "start_marker": "continuing on the fed",
                 "bullets": ["shared bullet", "rate cuts priced in"],
                 "themes": ["market-structure", "valuation-risk"]},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(len(merged), 1)
        # union, not replacement: nothing from either side is dropped, and the shared bullet is
        # not duplicated.
        self.assertEqual(merged[0]["bullets"].count("shared bullet"), 1)
        self.assertIn("QT continues", merged[0]["bullets"])
        self.assertIn("rate cuts priced in", merged[0]["bullets"])
        self.assertEqual(set(merged[0]["themes"]),
                          {"fed-liquidity", "market-structure", "valuation-risk"})

    def test_single_chunk_transcript_has_no_seams(self):
        # One chunk, two sections with near-identical titles: with only one chunk_index in play,
        # there is no "next chunk's first section" for either of them to be, so neither is ever a
        # seam candidate (si == 0 also requires a PRECEDING chunk) and both survive untouched.
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Opening Discussion", "start_marker": "welcome everyone",
                 "bullets": ["housekeeping"], "themes": []},
                {"title": "Opening Discussion Continued", "start_marker": "as I was saying",
                 "bullets": ["more housekeeping"], "themes": []},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(len(merged), 2)

    def test_empty_sections_list_handled(self):
        valid = set(to._FALLBACK_THEMES)
        merged, dropped = to.merge_sections([{"chunk_index": 0, "sections": []}], valid)
        self.assertEqual(merged, [])
        self.assertEqual(dropped, 0)

        # An empty chunk between two real ones must not crash the seam bookkeeping, and must not
        # be mistaken for a real seam (chunk 1 is empty, so chunk 2's first section is not
        # adjacent to any previously seen last section).
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "First", "start_marker": "first", "bullets": [], "themes": []},
            ]},
            {"chunk_index": 1, "sections": []},
            {"chunk_index": 2, "sections": [
                {"title": "First", "start_marker": "first", "bullets": [], "themes": []},
            ]},
        ]
        merged2, dropped2 = to.merge_sections(chunk_results, valid)
        self.assertEqual(len(merged2), 2)


class TestOffListThemeRejection(unittest.TestCase):
    def test_off_list_theme_dropped_and_counted(self):
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Crypto Corner", "start_marker": "and now crypto",
                 "bullets": ["bitcoin update"], "themes": ["crypto-speculation", "fed-liquidity"]},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(dropped, 1)
        self.assertEqual(merged[0]["themes"], ["fed-liquidity"])

    def test_fallback_theme_list_matches_spec(self):
        expected = [
            "fed-liquidity", "fiscal-currency", "valuation-risk", "secular-growth",
            "geopolitics", "flows-positioning", "credit-shadow", "market-structure",
        ]
        self.assertEqual(to._FALLBACK_THEMES, expected)


class TestMergeCliMalformedInput(unittest.TestCase):
    def _run_merge(self, results_content):
        import io
        import contextlib

        results_path = os.path.join(to.scratch_dir("test-outline-results"), "results.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            fh.write(results_content)

        class Args:
            results = results_path
            title = "Malformed Test"
            json = True

        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                to.cmd_merge(Args())
        return ctx.exception.code, stderr.getvalue()

    def test_not_json_fails_closed(self):
        code, err = self._run_merge("not json at all {{{")
        self.assertNotEqual(code, 0)
        self.assertIn("not valid JSON", err)

    def test_not_an_array_fails_closed(self):
        code, err = self._run_merge(json.dumps({"chunk_index": 0, "sections": []}))
        self.assertNotEqual(code, 0)
        self.assertIn("array", err)

    def test_missing_sections_field_fails_closed(self):
        code, err = self._run_merge(json.dumps([{"chunk_index": 0}]))
        self.assertNotEqual(code, 0)
        self.assertIn("sections", err)

    def test_empty_array_fails_closed(self):
        code, err = self._run_merge(json.dumps([]))
        self.assertNotEqual(code, 0)


class TestMergeMarkdownOutput(unittest.TestCase):
    def test_markdown_contains_section_numbering_and_themes(self):
        import io
        import contextlib

        results = [
            {"chunk_index": 0, "sections": [
                {"title": "Opening", "start_marker": "hello",
                 "bullets": ["point one", "point two"], "themes": ["fed-liquidity"]},
            ]},
        ]
        results_path = os.path.join(to.scratch_dir("test-outline-md"), "results.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh)

        class Args:
            results = results_path
            title = "Sample Talk"
            json = False

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            to.cmd_merge(Args())
        out = stdout.getvalue()
        self.assertIn("## Outline", out)
        self.assertIn("1. **Opening**", out)
        self.assertIn("point one", out)
        self.assertIn("fed-liquidity", out)
        self.assertIn("Themes active: fed-liquidity", out)


class TestOutlineJsonArtifact(unittest.TestCase):
    """Task 6.1.1 — `merge` also emits the outline as a durable JSON document (schema_version 1),
    independent of markdown/stdout. `--outline-json` writes it to disk; `--json` only controls what
    prints to stdout. See the module docstring's THE OUTLINE JSON CONTRACT section for the schema."""

    def _results_with_two_sections(self):
        return [
            {"chunk_index": 0, "sections": [
                {"title": "Opening", "start_marker": "hello",
                 "bullets": ["point one", "point two"], "themes": ["fed-liquidity"]},
                {"title": "Closing", "start_marker": "goodbye",
                 "bullets": ["point three"], "themes": []},
            ]},
        ]

    def test_json_parses_and_section_count_matches_markdown_headings(self):
        results = self._results_with_two_sections()
        tmp_dir = tempfile.mkdtemp()
        results_path = os.path.join(tmp_dir, "results.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh)
        outline_json_path = os.path.join(tmp_dir, "out.outline.json")

        class ArgsJson:
            results = results_path
            title = "Sample Talk"
            json = True
            outline_json = outline_json_path

        class ArgsMd:
            results = results_path
            title = "Sample Talk"
            json = False
            outline_json = None

        import io
        import contextlib
        stdout_md = io.StringIO()
        with contextlib.redirect_stdout(stdout_md):
            to.cmd_merge(ArgsMd())
        md = stdout_md.getvalue()
        numbered_headings = re.findall(r"(?m)^\d+\. \*\*", md)

        stdout_json = io.StringIO()
        with contextlib.redirect_stdout(stdout_json):
            to.cmd_merge(ArgsJson())

        with open(outline_json_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(len(doc["sections"]), len(numbered_headings))
        self.assertEqual(doc["schema_version"], to.OUTLINE_JSON_SCHEMA_VERSION)
        self.assertEqual(doc["counts"]["sections_out"], len(doc["sections"]))
        self.assertEqual(doc["counts"]["sections_in"], 2)
        self.assertEqual(doc["counts"]["dropped_themes"], 0)
        self.assertIn("theme_vocabulary", doc)
        self.assertIn("fed-liquidity", doc["theme_vocabulary"])
        self.assertEqual(doc["themes_active"], ["fed-liquidity"])
        self.assertEqual(doc["provenance"], [])

    def test_outline_json_written_regardless_of_stdout_format(self):
        # --outline-json must write the artifact even when --json is NOT passed (markdown to
        # stdout) — the two are independent, per the module docstring.
        results = self._results_with_two_sections()
        tmp_dir = tempfile.mkdtemp()
        results_path = os.path.join(tmp_dir, "results.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh)
        outline_json_path = os.path.join(tmp_dir, "out.outline.json")

        class Args:
            results = results_path
            title = "Sample Talk"
            json = False
            outline_json = outline_json_path

        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            to.cmd_merge(Args())
        self.assertTrue(os.path.isfile(outline_json_path))
        with open(outline_json_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(len(doc["sections"]), 2)

    def test_provenance_records_seam_merge_with_evidence(self):
        chunk_plan = write_seam_fixture(
            before_words=["intro" + str(i) for i in range(60)],
            overlap_words=["overlap" + str(i) for i in range(20)],
            after_words=["outro" + str(i) for i in range(60)],
        )
        results = [
            {"chunk_index": 0, "sections": [
                {"title": "Shared Topic", "start_marker": "overlap0 overlap1",
                 "bullets": ["a"], "themes": []},
            ]},
            {"chunk_index": 1, "sections": [
                {"title": "Shared Topic", "start_marker": "overlap0 overlap1",
                 "bullets": ["b"], "themes": []},
            ]},
        ]
        tmp_dir = tempfile.mkdtemp()
        results_path = os.path.join(tmp_dir, "results.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh)
        plan_path = os.path.join(tmp_dir, "plan.json")
        with open(plan_path, "w", encoding="utf-8") as fh:
            json.dump({"title": "T", "chunks": chunk_plan}, fh)
        outline_json_path = os.path.join(tmp_dir, "out.outline.json")

        class Args:
            results = results_path
            plan = plan_path
            title = "Seam Talk"
            json = False
            outline_json = outline_json_path

        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            to.cmd_merge(Args())

        with open(outline_json_path, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(len(doc["sections"]), 1)  # the seam duplicate collapsed into one
        self.assertEqual(len(doc["provenance"]), 1)
        entry = doc["provenance"][0]
        self.assertEqual(entry["into_section_index"], 0)
        self.assertEqual(entry["from_chunk_index"], 1)
        self.assertEqual(entry["into_chunk_index"], 0)
        self.assertIn("positional", entry["evidence"])


class TestOutlineJsonSchemaVersion(unittest.TestCase):
    """A consumer of the outline JSON contract must fail loudly on an unrecognized schema_version,
    never guess at a shape that may have changed underneath it (module docstring)."""

    def test_current_version_loads_cleanly(self):
        tmp_dir = tempfile.mkdtemp()
        path = os.path.join(tmp_dir, "ok.outline.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"schema_version": to.OUTLINE_JSON_SCHEMA_VERSION, "sections": []}, fh)
        doc = to.load_outline_document(path)
        self.assertEqual(doc["schema_version"], to.OUTLINE_JSON_SCHEMA_VERSION)

    def test_unknown_schema_version_raises(self):
        tmp_dir = tempfile.mkdtemp()
        path = os.path.join(tmp_dir, "future.outline.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"schema_version": 999, "sections": []}, fh)
        with self.assertRaises(to.OutlineSchemaError):
            to.load_outline_document(path)

    def test_missing_schema_version_raises(self):
        tmp_dir = tempfile.mkdtemp()
        path = os.path.join(tmp_dir, "no-version.outline.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"sections": []}, fh)
        with self.assertRaises(to.OutlineSchemaError):
            to.load_outline_document(path)


class TestDefect1MissingChunkCoverage(unittest.TestCase):
    """DEFECT 1 (CRITICAL): a chunk_index present in --plan but absent from --results must die,
    naming exactly which index(es) are missing and the word span each covered — never silently
    shorten the outline."""

    def _write(self, dirpath, name, obj):
        path = os.path.join(dirpath, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return path

    def test_missing_chunk_index_dies_naming_index_and_span(self):
        import io
        import contextlib

        tmp_dir = tempfile.mkdtemp()
        plan = {
            "title": "Four Chunk Talk",
            "chunks": [
                {"index": 0, "path": "/x/chunk-00.txt", "word_start": 0, "word_end": 1000,
                 "word_count": 1000},
                {"index": 1, "path": "/x/chunk-01.txt", "word_start": 1000, "word_end": 2000,
                 "word_count": 1000},
                {"index": 2, "path": "/x/chunk-02.txt", "word_start": 2000, "word_end": 6000,
                 "word_count": 4000},
                {"index": 3, "path": "/x/chunk-03.txt", "word_start": 6000, "word_end": 7000,
                 "word_count": 1000},
            ],
        }
        # Results present for 0, 1, 3 — chunk 2 (a ~4000-word span) is missing, exactly the
        # scenario in the defect report (a chunk subagent that died on a server error).
        results = [
            {"chunk_index": 0, "sections": [{"title": "A", "start_marker": "a",
                                              "bullets": [], "themes": []}]},
            {"chunk_index": 1, "sections": [{"title": "B", "start_marker": "b",
                                              "bullets": [], "themes": []}]},
            {"chunk_index": 3, "sections": [{"title": "D", "start_marker": "d",
                                              "bullets": [], "themes": []}]},
        ]
        plan_path = self._write(tmp_dir, "plan.json", plan)
        results_path = self._write(tmp_dir, "results.json", results)

        class Args:
            pass
        args = Args()
        args.results = results_path
        args.plan = plan_path
        args.title = "Four Chunk Talk"
        args.json = True

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                to.cmd_merge(args)
        self.assertNotEqual(ctx.exception.code, 0)
        err = stderr.getvalue()
        self.assertIn("2", err)
        self.assertIn("2000-6000", err)


class TestDefect1DuplicateChunkIndex(unittest.TestCase):
    """A chunk_index repeated in --results is ambiguous — which copy is authoritative? This tool
    DIES on a duplicate rather than guessing (silently keeping one copy, or silently merging both,
    is a guess dressed up as an answer); the seam-dedup bookkeeping in merge_sections also assumes
    exactly one result per chunk_index, so a duplicate would otherwise corrupt that state too."""

    def test_duplicate_chunk_index_dies(self):
        import io
        import contextlib

        results = [
            {"chunk_index": 0, "sections": [{"title": "A", "start_marker": "a",
                                              "bullets": [], "themes": []}]},
            {"chunk_index": 0, "sections": [{"title": "A again", "start_marker": "a2",
                                              "bullets": [], "themes": []}]},
        ]
        results_path = os.path.join(to.scratch_dir("test-outline-dupe"), "results.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh)

        class Args:
            results = results_path
            title = "Dupe Test"
            json = True

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                to.cmd_merge(Args())
        self.assertNotEqual(ctx.exception.code, 0)
        self.assertIn("duplicate", stderr.getvalue().lower())


class TestDefect2PositionConflictRejectsMerge(unittest.TestCase):
    """DEFECT 2 (CRITICAL): two DIFFERENT sections that both happen to use an identical, generic
    start_marker ("now lets move on") must not merge just because each marker is independently
    found somewhere inside its own chunk's declared overlap window. This fixture gives each chunk
    its own real content with the marker phrase at a genuinely different point in each file, but
    declares (via plan word_start/word_end) an overlap window wide enough that BOTH bounded
    searches independently succeed — exactly what the old bounds-only check accepted. The new
    absolute-offset check must catch that the two hits are ~30 words apart (well past the 20-word
    tolerance) and refuse to merge, reporting the rejection on stderr."""

    def test_shared_generic_marker_at_different_positions_does_not_merge(self):
        tmp_dir = tempfile.mkdtemp()
        prev_words = ["x"] * 100 + ["now", "lets", "move", "on"] + ["y"] * 50
        next_words = ["z"] * 80 + ["now", "lets", "move", "on"] + ["w"] * 50
        prev_path = os.path.join(tmp_dir, "chunk-00.txt")
        next_path = os.path.join(tmp_dir, "chunk-01.txt")
        with open(prev_path, "w", encoding="utf-8") as fh:
            fh.write(" ".join(prev_words))
        with open(next_path, "w", encoding="utf-8") as fh:
            fh.write(" ".join(next_words))

        chunk_plan = [
            {"index": 0, "path": prev_path, "word_start": 0, "word_end": len(prev_words),
             "word_count": len(prev_words)},
            # Declares an overlap of 104 words (154 - 50) — wide enough that the marker's real
            # position in EACH file (local 100, local 80) falls inside the declared window on
            # both sides, satisfying the old bounds-only check.
            {"index": 1, "path": next_path, "word_start": 50, "word_end": 50 + len(next_words),
             "word_count": len(next_words)},
        ]
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Fed Liquidity Wrap-up", "start_marker": "now lets move on",
                 "bullets": ["QT unchanged"], "themes": ["fed-liquidity"]},
            ]},
            {"chunk_index": 1, "sections": [
                {"title": "Geopolitics Update", "start_marker": "now lets move on",
                 "bullets": ["oil supply risk"], "themes": ["geopolitics"]},
            ]},
        ]

        import io
        import contextlib
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            merged, dropped = to.merge_sections(chunk_results, valid, chunk_plan)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["title"], "Fed Liquidity Wrap-up")
        self.assertEqual(merged[1]["title"], "Geopolitics Update")
        err = stderr.getvalue()
        self.assertIn("REJECTED", err)
        self.assertIn("DIFFERENT absolute transcript positions", err)


class TestDefect3MarkdownStaysWellFormed(unittest.TestCase):
    """DEFECT 3: content containing markdown structure characters must not corrupt the emitted
    document. Re-parses the output the way a downstream index tool reasonably would: exactly one
    top-level '## ' heading, one numbered section line per section, and no bare thematic-break
    line anywhere in the body."""

    def test_hostile_title_and_bullet_stay_well_formed(self):
        import io
        import contextlib

        hostile_title = "## Injected Heading\n---\n**unmatched bold"
        hostile_bullet = "1. fake list item\n---\nmore `unmatched code"
        results = [
            {"chunk_index": 0, "sections": [
                {"title": hostile_title, "start_marker": "hi",
                 "bullets": [hostile_bullet, "a normal bullet"], "themes": []},
            ]},
        ]
        results_path = os.path.join(to.scratch_dir("test-outline-hostile"), "results.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh)

        class Args:
            results = results_path
            title = "Hostile ## Title\n---"
            json = False

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            to.cmd_merge(Args())
        out = stdout.getvalue()

        lines = out.splitlines()
        heading_lines = [ln for ln in lines if ln.startswith("## ")]
        self.assertEqual(len(heading_lines), 1, f"expected exactly one top-level heading:\n{out}")
        numbered_lines = [ln for ln in lines if re.match(r"^\d+\.\s", ln)]
        self.assertEqual(len(numbered_lines), 1, f"expected exactly one numbered section:\n{out}")
        thematic_breaks = [ln for ln in lines if re.match(r"^(?:-{3,}|\*{3,}|_{3,})\s*$", ln)]
        self.assertEqual(thematic_breaks, [], f"a bare thematic break leaked into the body:\n{out}")
        # No line should contain an odd, unmatched run of ** or ` — the surest sign emphasis/code
        # was left open, corrupting everything rendered after it. A backslash-escaped marker
        # (\** or \`) is intentionally neutralised content, not live markdown syntax, so it does
        # not count toward the live-marker parity check.
        def _live_marker_count(line, marker):
            return len(re.findall(r"(?<!\\)" + re.escape(marker), line))

        for ln in lines:
            self.assertEqual(_live_marker_count(ln, "**") % 2, 0, f"unmatched ** on line: {ln!r}")
            self.assertEqual(_live_marker_count(ln, "`") % 2, 0, f"unmatched ` on line: {ln!r}")


class TestDefect4MissingLensFileNotesLoudly(unittest.TestCase):
    """DEFECT 4: the fallback vocabulary is fine to use when `system/marc-lenses.md` is absent,
    but every OTHER malformed-file branch in load_themes() reports loudly — the missing-file
    branch must too, matching the module's own FAIL POSTURE: closed."""

    def test_missing_lens_file_uses_fallback_and_notes_on_stderr(self):
        import io
        import contextlib

        orig_root = to._ROOT
        try:
            to._ROOT = tempfile.mkdtemp()  # guaranteed to have no system/marc-lenses.md
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                themes = to.load_themes()
        finally:
            to._ROOT = orig_root

        self.assertEqual(themes, to._FALLBACK_THEMES)
        err = stderr.getvalue()
        self.assertIn("NOTE", err)
        self.assertIn("fallback", err.lower())


class TestDefect5NearMissThemesResolve(unittest.TestCase):
    """DEFECT 5: obvious typo/formatting variants of a valid theme (case, underscore-vs-hyphen,
    stray whitespace) must resolve to the canonical theme, not be dropped as off-list — and a
    genuinely off-list theme must still be named on stderr, not just counted."""

    def test_near_miss_variants_all_resolve_to_canonical_theme(self):
        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Fed Talk", "start_marker": "hello",
                 "bullets": ["QT continues"],
                 "themes": ["Fed-Liquidity", "fed_liquidity", "fed-liquidity "]},
            ]},
        ]
        merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(dropped, 0)
        self.assertEqual(merged[0]["themes"], ["fed-liquidity"])

    def test_genuinely_offlist_theme_still_named_on_stderr(self):
        import io
        import contextlib

        valid = set(to._FALLBACK_THEMES)
        chunk_results = [
            {"chunk_index": 0, "sections": [
                {"title": "Crypto Corner", "start_marker": "and now crypto",
                 "bullets": ["bitcoin update"], "themes": ["crypto-speculation"]},
            ]},
        ]
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            merged, dropped = to.merge_sections(chunk_results, valid)
        self.assertEqual(dropped, 1)
        self.assertIn("crypto-speculation", stderr.getvalue())


class TestDefect6MaxAgentsMustBePositive(unittest.TestCase):
    """DEFECT 6: a non-positive --max-agents must die, not be silently replaced with the default
    of 12 — a caller who typed 0 or a negative number made a mistake, and the tool should say so
    rather than quietly doing something else."""

    def _run(self, max_agents):
        import io
        import contextlib

        text = make_transcript(500)
        text_path = os.path.join(to.scratch_dir("test-outline-maxagents"), f"t{max_agents}.txt")
        with open(text_path, "w", encoding="utf-8") as fh:
            fh.write(text)

        class Args:
            pass
        args = Args()
        args.text = text_path
        args.title = "Max Agents Test"
        args.max_agents = max_agents
        args.json = True

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                to.cmd_plan(args)
        return ctx.exception.code, stderr.getvalue()

    def test_zero_dies(self):
        code, err = self._run(0)
        self.assertNotEqual(code, 0)
        self.assertIn("positive", err.lower())

    def test_negative_dies(self):
        code, err = self._run(-5)
        self.assertNotEqual(code, 0)
        self.assertIn("positive", err.lower())


if __name__ == "__main__":
    unittest.main()
