#!/usr/bin/env python3
"""test_pad_archive.py — the merged suite for the one section archiver.

It is the union of two suites that used to live apart (`test_pad_archive.py`, adversarial,
scratchpad-only; `test_section_archive.py`, unittest, named-sections-only) PLUS the coverage
neither of them had: `state` and `clear`. Those two verbs carry the frozen verdict contract —
PAD-EMPTY 0 · PAD-DIRTY 2 · PAD-ARCHIVED-UNCLEARED 3 · CANNOT-READ 4 — and until this merge
nothing tested them at all. A receipt gate that nothing exercises is a promise, not a control.

Run: python3 system/tools/save/test_pad_archive.py
"""

import concurrent.futures
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "pad_archive.py")
sys.path.insert(0, HERE)
import pad_archive as pa  # noqa: E402

PAD_HEADING = "## 7. SCRATCHPAD"
FOOTER = "\n## + CHRONICLE POINTER\nfooter\n"


def run(*args):
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def brief_with_pad(body, footer=FOOTER, heading=PAD_HEADING):
    d = tempfile.mkdtemp()
    b = os.path.join(d, "brief.md")
    with open(b, "w", encoding="utf-8") as f:
        f.write(f"# Brief\n## 1. FRAME\nframe\n{heading}\n{body}{footer}")
    return d, b


def brief_with_sections(current="state line A\nstate line B\n"):
    d = tempfile.mkdtemp()
    b = os.path.join(d, "brief.md")
    with open(b, "w", encoding="utf-8") as f:
        f.write("# Brief\n"
                "## 1. FRAME\nframe body\n"
                "## 2. CURRENT STATE (2026-08-06)\n" + current +
                "## 4. STORY LOG\nlog body\n")
    return d, b


def pad_archive_file(brief):
    return brief + pa.PAD_ARCHIVE_SUFFIX


def rewrite(path, old, new):
    t = open(path, encoding="utf-8").read()
    open(path, "w", encoding="utf-8").write(t.replace(old, new))


def last_block_body(archive_file):
    """Body of the final block. Splits on the block HEADER LINE, never on the first `-->`
    in the file — archived content legitimately contains HTML comments, and splitting on
    `-->` made this helper lie about what had been archived."""
    txt = open(archive_file, encoding="utf-8").read()
    lines = txt.splitlines(keepends=True)
    idx = max(i for i, l in enumerate(lines) if l.startswith("<!-- section-archive ::"))
    return "".join(lines[idx + 1:])


class Base(unittest.TestCase):
    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def pad(self, body, **kw):
        d, b = brief_with_pad(body, **kw)
        self._dirs.append(d)
        return b

    def sections(self, **kw):
        d, b = brief_with_sections(**kw)
        self._dirs.append(d)
        return b


# --------------------------------------------------------------- the scratchpad path

class Scratchpad(Base):

    def test_fresh_append_emits_receipt_and_writes_the_archive(self):
        b = self.pad("> note A\n> note B\n")
        rc, out, err = run("archive", b)
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith("RECEIPT "), out)
        self.assertTrue(os.path.exists(pad_archive_file(b)))

    def test_idempotent_rerun_appends_no_second_block(self):
        b = self.pad("> same\n")
        run("archive", b)
        rc, out, _ = run("archive", b)
        blocks = pa.block_count(pad_archive_file(b))
        self.assertEqual(rc, 0)
        self.assertEqual(blocks, 1, f"blocks={blocks}")
        self.assertIn("idempotent", out)

    def test_changed_pad_chains_to_the_previous_hash(self):
        b = self.pad("> first\n")
        run("archive", b)
        h1 = pa.last_block_hash(pad_archive_file(b))
        rewrite(b, "> first", "> second")
        run("archive", b)
        arch = open(pad_archive_file(b), encoding="utf-8").read()
        self.assertEqual(pa.block_count(pad_archive_file(b)), 2)
        self.assertIn(f"prev={h1}", arch)

    def test_no_scratchpad_section_fails_closed(self):
        d = tempfile.mkdtemp(); self._dirs.append(d)
        b = os.path.join(d, "brief.md")
        open(b, "w").write("# Brief\n## 1. FRAME\nx\n")
        rc, out, _ = run("archive", b)
        self.assertEqual(rc, 2)
        self.assertFalse(out.startswith("RECEIPT"))

    def test_missing_file_is_cannot_read_not_a_receipt(self):
        rc, out, _ = run("archive", "/tmp/nonexistent-brief-xyz.md")
        self.assertEqual(rc, 4)
        self.assertIn("CANNOT-READ", out)
        self.assertFalse(out.startswith("RECEIPT"))

    def test_empty_pad_does_not_crash(self):
        b = self.pad("")
        rc, _out, err = run("archive", b)
        self.assertIn(rc, (0, 2))
        self.assertNotIn("Traceback", err)

    def test_hostile_content_survives_byte_for_byte(self):
        hostile = ("> émojis 🎉 and ünïcode\n> `backticks` and ```code fence```\n"
                   "> <!-- an html comment --> and $HOME and \"quotes\"\n> tabs\there\n")
        b = self.pad(hostile)
        run("archive", b)
        self.assertIn(hostile.strip(), last_block_body(pad_archive_file(b)))

    def test_a_markdown_heading_inside_the_pad_does_not_truncate_it(self):
        tricky = ("> before the fake header\n"
                  "## This Looks Like A Section But Is Pad Content\n"
                  "> AFTER the fake header — this MUST be archived\n")
        b = self.pad(tricky)
        run("archive", b)
        self.assertIn("AFTER the fake header", last_block_body(pad_archive_file(b)),
                      "pad content after an internal '## ' was LOST")

    def test_unwritable_archive_emits_no_false_receipt(self):
        b = self.pad("> important\n")
        ap = pad_archive_file(b)
        open(ap, "w").write('<!-- section-archive :: section="## 7. SCRATCHPAD" :: archive #1 '
                            ':: t :: host=x :: prev=GENESIS :: hash=' + "0" * 64 + ' -->\nold\n')
        os.chmod(ap, 0o444)
        try:
            rc, out, _ = run("archive", b)
        finally:
            os.chmod(ap, 0o644)
        self.assertEqual(rc, 2)
        self.assertFalse(out.startswith("RECEIPT"), "a false RECEIPT here means data loss")

    def test_the_archived_block_reconstructs_the_original_pad(self):
        original = "> keeper 1\n> keeper 2 with detail\n> keeper 3\n"
        b = self.pad(original)
        run("archive", b)
        self.assertIn(original.strip(), last_block_body(pad_archive_file(b)))

    def test_chain_integrity_across_five_appends(self):
        b = self.pad("> v0\n")
        run("archive", b)
        for i in range(1, 5):
            rewrite(b, f"> v{i-1}", f"> v{i}")
            run("archive", b)
        blocks = pa._blocks(pad_archive_file(b))
        self.assertEqual(len(blocks), 5)
        self.assertEqual(blocks[0][2], "GENESIS")
        for i in range(1, 5):
            self.assertEqual(blocks[i][2], blocks[i - 1][3])

    def test_a_large_pad_still_archives(self):
        big = "".join(f"> line {i} with some filler content to add bytes\n" for i in range(2500))
        b = self.pad(big)
        rc, out, _ = run("archive", b)
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("RECEIPT"))

    def test_concurrent_appends_to_one_archive_both_land(self):
        b1 = self.pad("> base\n")
        run("archive", b1)
        b2 = self.pad("> concurrent X\n")
        os.replace(pad_archive_file(b1), pad_archive_file(b2))
        rewrite(b1, "> base", "> proc-A unique")
        shutil.copy(pad_archive_file(b2), pad_archive_file(b1))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(run, "archive", b1), ex.submit(run, "archive", b2)]
            [f.result() for f in futs]
        total = pa.block_count(pad_archive_file(b1)) + pa.block_count(pad_archive_file(b2))
        self.assertGreaterEqual(total, 3)

    def test_pad_content_quoting_the_block_marker_does_not_inflate_the_counter(self):
        # ⭐ THE REGRESSION THIS FILE EXISTS FOR. A note that merely QUOTES the marker used to
        # make `verify` report a malformed header on a provably perfect chain — permanently,
        # because the archive is append-only.
        b = self.pad('> quoting the marker: <!-- section-archive :: fake -->\n')
        run("archive", b)
        rewrite(b, "fake", "fake2")
        rc, out, _ = run("archive", b)
        self.assertEqual(rc, 0)
        self.assertTrue(out.strip().endswith("archive=2"), out)
        rc_v, out_v, err_v = run("verify", b)
        self.assertEqual(rc_v, 0, f"verify false-alarmed on quoted marker: {err_v}")

    def test_a_path_with_spaces_and_unicode_works(self):
        d = tempfile.mkdtemp(); self._dirs.append(d)
        sub = os.path.join(d, "My Drive ünï")
        os.makedirs(sub)
        b = os.path.join(sub, "brief.md")
        open(b, "w", encoding="utf-8").write(
            "# B\n## 7. SCRATCHPAD\n> spaced path note\n\n## + CHRONICLE POINTER\nf\n")
        rc, out, err = run("archive", b)
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith("RECEIPT"))

    def test_verify_passes_clean_and_detects_a_tampered_block(self):
        b = self.pad("> a\n")
        run("archive", b)
        rewrite(b, "> a", "> b"); run("archive", b)
        rewrite(b, "> b", "> c"); run("archive", b)
        self.assertEqual(run("verify", b)[0], 0)
        ap = pad_archive_file(b)
        lines = open(ap, encoding="utf-8").read().splitlines()
        idxs = [i for i, l in enumerate(lines) if l.startswith("<!-- section-archive ::")]
        lines[idxs[1]] = lines[idxs[1]].replace("hash=", "hash=deadbeef", 1)
        open(ap, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        self.assertNotEqual(run("verify", b)[0], 0)


# --------------------------------------------------------------- state + clear (the frozen contract)

class StateAndClear(Base):

    def test_state_on_a_fresh_pad_is_dirty_rc2(self):
        b = self.pad("> something real\n")
        rc, out, _ = run("state", b)
        self.assertEqual(rc, 2)
        self.assertTrue(out.startswith("PAD-DIRTY "), out)

    def test_state_after_archiving_is_archived_uncleared_rc3(self):
        b = self.pad("> something real\n")
        run("archive", b)
        rc, out, _ = run("state", b)
        self.assertEqual(rc, 3)
        self.assertTrue(out.startswith("PAD-ARCHIVED-UNCLEARED"), out)

    def test_state_after_clearing_is_empty_rc0(self):
        b = self.pad("> something real\n")
        run("archive", b)
        run("clear", b)
        rc, out, _ = run("state", b)
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("PAD-EMPTY"), out)

    def test_state_on_a_whitespace_only_pad_is_empty_rc0(self):
        b = self.pad("   \n\n")
        rc, out, _ = run("state", b)
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("PAD-EMPTY"), out)

    def test_state_on_one_bolded_line_is_dirty_not_empty(self):
        # The old emptiness test matched by LINE SHAPE and called any all-bold line
        # boilerplate — reporting a genuinely full pad as empty.
        b = self.pad("**call the bank about the transfer**\n")
        rc, out, _ = run("state", b)
        self.assertEqual(rc, 2, out)

    def test_state_on_a_missing_brief_is_cannot_read_rc4(self):
        rc, out, _ = run("state", "/tmp/nonexistent-brief-xyz.md")
        self.assertEqual(rc, 4)
        self.assertIn("CANNOT-READ", out)

    def test_state_on_an_unreadable_brief_is_cannot_read_rc4(self):
        b = self.pad("> x\n")
        os.chmod(b, 0o000)
        try:
            rc, out, _ = run("state", b)
        finally:
            os.chmod(b, 0o644)
        self.assertEqual(rc, 4)
        self.assertIn("CANNOT-READ", out)

    def test_state_on_a_brief_with_no_scratchpad_is_cannot_read_rc4(self):
        d = tempfile.mkdtemp(); self._dirs.append(d)
        b = os.path.join(d, "brief.md")
        open(b, "w").write("# Brief\n## 1. FRAME\nx\n")
        rc, out, _ = run("state", b)
        self.assertEqual(rc, 4)
        self.assertIn("CANNOT-READ", out)

    def test_state_never_writes_anything(self):
        b = self.pad("> untouched\n")
        before = open(b, encoding="utf-8").read()
        run("state", b)
        self.assertEqual(open(b, encoding="utf-8").read(), before)
        self.assertFalse(os.path.exists(pad_archive_file(b)))

    def test_clear_refuses_without_an_archive(self):
        b = self.pad("> never archived\n")
        before = open(b, encoding="utf-8").read()
        rc, out, _ = run("clear", b)
        self.assertEqual(rc, 2)
        self.assertTrue(out.startswith("REFUSED"), out)
        self.assertEqual(open(b, encoding="utf-8").read(), before, "brief was modified on a REFUSED")

    def test_clear_refuses_when_the_pad_changed_after_archiving(self):
        b = self.pad("> archived version\n")
        run("archive", b)
        rewrite(b, "archived version", "edited after the archive")
        before = open(b, encoding="utf-8").read()
        rc, out, _ = run("clear", b)
        self.assertEqual(rc, 2)
        self.assertTrue(out.startswith("REFUSED"), out)
        self.assertEqual(open(b, encoding="utf-8").read(), before)

    def test_the_full_cycle_archive_verify_clear(self):
        b = self.pad("> line one\n> line two\n")
        rc_a, out_a, _ = run("archive", b)
        self.assertEqual(rc_a, 0)
        self.assertTrue(out_a.startswith("RECEIPT "))
        self.assertEqual(run("verify", b)[0], 0)
        rc_c, out_c, _ = run("clear", b)
        self.assertEqual(rc_c, 0)
        self.assertTrue(out_c.startswith("CLEARED "), out_c)
        after = open(b, encoding="utf-8").read()
        self.assertIn(pa._CLEAR_SENTINEL, after)
        self.assertNotIn("> line one", after)
        # and the content is still recoverable from the archive
        self.assertIn("> line one", open(pad_archive_file(b), encoding="utf-8").read())

    def test_clear_removes_the_FIRST_line_when_the_heading_has_no_annotation(self):
        # ⭐ THE 2026-08-11 REGRESSION. `clear` used to hop unconditionally to the line after
        # span_start. With a bare `## 7. SCRATCHPAD` heading, span_start was ALREADY the first
        # body line, so the hop skipped it and the pad's opening line survived every clear —
        # while `clear` still printed CLEARED and exit 0.
        b = self.pad("> FIRST line\n> second line\n")
        run("archive", b)
        rc, _out, _ = run("clear", b)
        self.assertEqual(rc, 0)
        after = open(b, encoding="utf-8").read()
        self.assertNotIn("> FIRST line", after, "clear left the pad's opening line behind")
        self.assertNotIn("> second line", after)
        self.assertIn("## 7. SCRATCHPAD", after)

    def test_clear_keeps_the_heading_annotation_when_there_is_one(self):
        # The other shape, which the buggy version happened to get right. Both must work.
        b = self.pad("> pad body\n",
                     heading="## 7. SCRATCHPAD  *(dumb capture surface — dump freely)*")
        run("archive", b)
        rc, _out, _ = run("clear", b)
        self.assertEqual(rc, 0)
        after = open(b, encoding="utf-8").read()
        self.assertIn("*(dumb capture surface — dump freely)*", after,
                      "the heading's own annotation was deleted")
        self.assertNotIn("> pad body", after)

    def test_clear_preserves_the_heading_and_everything_after_the_section(self):
        b = self.pad("> pad content\n")
        run("archive", b)
        run("clear", b)
        after = open(b, encoding="utf-8").read()
        self.assertIn("## 7. SCRATCHPAD", after)
        self.assertIn("## + CHRONICLE POINTER", after)
        self.assertIn("## 1. FRAME", after)

    def test_clear_leaves_no_temp_file_behind(self):
        b = self.pad("> pad content\n")
        run("archive", b); run("clear", b)
        leftovers = [f for f in os.listdir(os.path.dirname(b)) if f.startswith(".pad-clear-")]
        self.assertEqual(leftovers, [])


# --------------------------------------------------------------- named sections

class NamedSection(Base):
    HEAD = "## 2. CURRENT STATE (2026-08-06)"

    def test_heading_gives_a_receipt_and_a_byte_identical_backup(self):
        b = self.sections()
        orig = open(b, "rb").read()
        rc, out, err = run("archive", b, "--heading", self.HEAD)
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith("RECEIPT "))
        bak = pa.backup_path(b)
        self.assertTrue(os.path.exists(bak))
        self.assertEqual(open(bak, "rb").read(), orig)

    def test_start_end_gives_a_receipt(self):
        b = self.sections()
        lines = open(b, encoding="utf-8").read().split("\n")
        s = lines.index(self.HEAD) + 1
        e = lines.index("## 4. STORY LOG") + 1
        rc, out, err = run("archive", b, "--start", str(s), "--end", str(e))
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith("RECEIPT "))

    def test_heading_and_line_numbers_select_the_same_span(self):
        b1 = self.sections()
        b2 = self.sections()
        lines = open(b2, encoding="utf-8").read().split("\n")
        s = lines.index(self.HEAD) + 1
        e = lines.index("## 4. STORY LOG") + 1
        h1 = run("archive", b1, "--heading", self.HEAD)[1].split()[1]
        h2 = run("archive", b2, "--start", str(s), "--end", str(e))[1].split()[1]
        self.assertEqual(h1, h2)

    def test_a_near_miss_heading_is_refused_never_fuzzy_matched(self):
        b = self.sections()
        rc, out, _ = run("archive", b, "--heading", "## 2. CURRENT STATE")
        self.assertEqual(rc, 2)
        self.assertFalse(out.startswith("RECEIPT"))

    def test_a_duplicated_heading_is_refused_as_ambiguous(self):
        d = tempfile.mkdtemp(); self._dirs.append(d)
        b = os.path.join(d, "brief.md")
        open(b, "w").write("# B\n## DUP\na\n## DUP\nb\n## OTHER\nc\n")
        rc, out, err = run("archive", b, "--heading", "## DUP")
        self.assertEqual(rc, 2)
        self.assertIn("ambiguous", (out + err).lower())

    def test_neither_selector_on_a_brief_without_a_pad_exits_2(self):
        d = tempfile.mkdtemp(); self._dirs.append(d)
        b = os.path.join(d, "brief.md")
        open(b, "w").write("# B\n## 1. FRAME\nx\n")
        self.assertEqual(run("archive", b)[0], 2)

    def test_start_without_end_exits_2(self):
        b = self.sections()
        self.assertEqual(run("archive", b, "--start", "3")[0], 2)
        self.assertEqual(run("archive", b, "--end", "9")[0], 2)

    def test_out_of_bounds_line_numbers_exit_2(self):
        b = self.sections()
        self.assertEqual(run("archive", b, "--start", "1", "--end", "9999")[0], 2)

    def test_a_heading_that_is_not_present_exits_2(self):
        b = self.sections()
        rc, out, _ = run("archive", b, "--heading", "## NOT A SECTION HERE")
        self.assertEqual(rc, 2)
        self.assertFalse(out.startswith("RECEIPT"))

    def test_idempotent_rerun_on_a_named_section(self):
        b = self.sections()
        run("archive", b, "--heading", self.HEAD)
        rc, out, _ = run("archive", b, "--heading", self.HEAD)
        self.assertEqual(rc, 0)
        self.assertIn("idempotent", out)
        self.assertEqual(pa.block_count(pa.archive_path(b, self.HEAD)), 1)

    def test_two_sequential_archives_chain_and_verify(self):
        b = self.sections()
        run("archive", b, "--heading", self.HEAD)
        rewrite(b, "state line A", "state line A CHANGED")
        run("archive", b, "--heading", self.HEAD)
        self.assertEqual(pa.block_count(pa.archive_path(b, self.HEAD)), 2)
        self.assertEqual(run("verify", b, "--heading", self.HEAD)[0], 0)

    def test_a_tampered_named_archive_makes_verify_exit_3(self):
        b = self.sections()
        run("archive", b, "--heading", self.HEAD)
        rewrite(b, "state line A", "state line A CHANGED")
        run("archive", b, "--heading", self.HEAD)
        ap = pa.archive_path(b, self.HEAD)
        lines = open(ap, encoding="utf-8").read().splitlines()
        idxs = [i for i, l in enumerate(lines) if l.startswith("<!-- section-archive ::")]
        lines[idxs[1]] = lines[idxs[1]].replace("prev=", "prev=deadbeef", 1)
        open(ap, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        self.assertEqual(run("verify", b, "--heading", self.HEAD)[0], 3)

    def test_a_named_section_gets_its_own_archive_file_not_the_pads(self):
        b = self.sections()
        run("archive", b, "--heading", self.HEAD)
        self.assertTrue(os.path.exists(pa.archive_path(b, self.HEAD)))
        self.assertFalse(os.path.exists(pad_archive_file(b)))

    def test_the_pad_keeps_its_well_known_archive_filename(self):
        self.assertTrue(pa.archive_path("/x/brief.md", "## 7. SCRATCHPAD").endswith(".pad-archive.md"))
        self.assertTrue(pa.archive_path("/x/brief.md", "## 2. CURRENT STATE")
                        .endswith(".2-current-state-archive.md"))


# --------------------------------------------------------------- the public API pm_flag.sh depends on

class PublicApi(Base):

    def test_extract_scratchpad_and_sha_are_importable_and_agree(self):
        b = self.pad("> fingerprint me\n")
        text = open(b, encoding="utf-8").read()
        pad = pa.extract_scratchpad(text)
        self.assertIsNotNone(pad)
        self.assertIn("fingerprint me", pad)
        # the hash pm_flag.sh stamps must equal the one `archive` receipts
        run("archive", b)
        self.assertEqual(pa.sha(pad), pa.last_block_hash(pad_archive_file(b)))

    def test_extract_scratchpad_returns_none_without_a_section(self):
        self.assertIsNone(pa.extract_scratchpad("# B\n## 1. FRAME\nx\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
