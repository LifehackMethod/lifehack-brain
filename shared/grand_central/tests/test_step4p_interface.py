"""Phase 4P.1 finish check: the planning-interface page is TRUE.

1. Every `gc` command named on the page exists in the gc parser.
2. Every JSON shape block on the page (`gc X ... --json` followed by a ```json fence) matches the real
   `--json` output of that command on a scratch copy: documented keys == actual keys, recursively
   (objects compared key-wise; a list is compared against its first element when it has one).
3. A wrong field name planted on a copy of the page is CAUGHT by the checker (planted case, shown failing
   first).

Temp DB only; never the live rig.db.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, importlib.util, io, json, os, re, sqlite3, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHARED = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, SHARED)
import migrate, store, store_items  # noqa: E402

spec = importlib.util.spec_from_file_location("rig_gc_iface", os.path.join(ROOT, "gc.py"))
rig_gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig_gc)

PAGE = os.path.join(ROOT, "docs", "planning-interface.md")
DAY = "2026-11-17"

CMD_BLOCK_RE = re.compile(r"`gc ([a-z-]+)([^`]*?)--json`[^`]*?```json\s*\n(.*?)```", re.S)


def page_text(path=PAGE):
    with open(path, encoding="utf-8") as f:
        return f.read()


def documented_shapes(text):
    """[(command, args-suffix, {documented keys})] from every `gc X ... --json` + ```json block."""
    out = []
    for m in CMD_BLOCK_RE.finditer(text):
        try:
            shape = json.loads(m.group(3))
        except ValueError as e:
            raise AssertionError("page shape block for `gc %s` is not valid JSON: %s" % (m.group(1), e))
        out.append((m.group(1), m.group(2), shape))
    return out


def diff_keys(doc, real, path=""):
    """Documented keys vs actual keys. -> [mismatch strings]. Objects: key sets equal. Lists: first element."""
    errs = []
    if isinstance(doc, dict):
        if not isinstance(real, dict):
            return ["%s: page says an object, code returns %s" % (path, type(real).__name__)]
        if not doc:
            return []  # `{}` on the page means a dynamic mapping: keys vary, shape says nothing
        dk, rk = set(doc), set(real)
        for k in sorted(dk - rk):
            errs.append("%s: field %r on the page, absent from the real output" % (path, k))
        for k in sorted(rk - dk):
            errs.append("%s: field %r in the real output, not on the page" % (path, k))
        for k in sorted(dk & rk):
            errs += diff_keys(doc[k], real[k], path + "." + k if path else k)
    elif isinstance(doc, list):
        if not isinstance(real, list):
            return ["%s: page says a list, code returns %s" % (path, type(real).__name__)]
        if doc and isinstance(doc[0], (dict, list)) and real:
            errs += diff_keys(doc[0], real[0], path + "[]")
    return errs


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
        c.close()
        store.set_path(self.p)
        self._old_now = os.environ.get("AGE_NOW")
        os.environ["AGE_NOW"] = DAY + "T09:00:00+00:00"
        import clock as _clock
        _st = _clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        for _src in ("gmail", "calendar", "tasks"):
            store.set_source_state(_src, _st, 0)  # a connected feed: the reads return data shapes, not the no-feed gate
        store_items.upsert_item("gmail", "m1", "email", title="Example note", occurred_at=DAY + "T08:00:00Z",
                                due_at="2026-11-20", status="inbox")
        self.q = self.x("INSERT INTO queue(kind,subject_ref,question,proposed_answer,created_at) "
                        "VALUES('apply-label','item:1','Label it?','Example-Label','x') RETURNING id")[0][0]
        self.seed_decide()

    def tearDown(self):
        store.set_path(None)
        if self._old_now is None:
            os.environ.pop("AGE_NOW", None)
        else:
            os.environ["AGE_NOW"] = self._old_now
        self.tmp.cleanup()

    def x(self, sql, a=()):
        c = sqlite3.connect(self.p)
        try:
            r = c.execute(sql, a).fetchall(); c.commit(); return r
        finally:
            c.close()

    def seed_decide(self):
        """Stage one validated picture so `gc decide --show` has a receipt to print."""
        import decide
        self.notes = os.path.join(self.tmp.name, "notes")
        reg = os.path.join(self.tmp.name, "desk-registry.yaml")
        with open(reg, "w", encoding="utf-8") as f:
            f.write("schema_version: 2\ndesks:\n  - desk_id: desk-a\n    purpose_path: desks/desk-a/canon/purpose.md\n"
                    "    open_loops_path: desks/desk-a/state/open-loops.md\n")
        self._old_desk_list = os.environ.get("LIFEHACK_DESK_LIST")
        self._old_notes = os.environ.get("AGE_NOTES_ROOT")
        os.environ["LIFEHACK_DESK_LIST"] = reg
        os.environ["AGE_NOTES_ROOT"] = self.notes
        self._decide_env = (reg, self._old_desk_list, self._old_notes)
        dp = os.path.join(self.tmp.name, "draft.json"); dp2 = os.path.join(self.tmp.name, "decisions.json")
        with open(dp, "w", encoding="utf-8") as f:
            json.dump({"draft_id": "week-1", "made_on": "2026-11-16", "suggestions": [
                {"id": "s1", "kind": "fact", "question": "Is the Example note important?",
                 "subject_kind": "item", "subject_name": "m1", "fact_key": "note", "value": "keep this week"}]}, f)
        with open(dp2, "w", encoding="utf-8") as f:
            json.dump({"s1": {"decision": "yes", "words": "keep it this week"}}, f)
        rc, out, err = self.gc("decide", "--draft", dp, "--decisions", dp2, "--day", DAY, "--json")
        assert rc == 0, err

    def gc(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rig_gc.main(["--db", self.p] + list(argv))
        return rc, out.getvalue(), err.getvalue()

    def real_output(self, cmd, extra):
        rc, out, err = self.gc(cmd, *(extra.split() if extra else ()), "--json")
        self.assertEqual(rc, 0, "gc %s --json failed on the scratch copy: %s" % (cmd, err))
        return json.loads(out)


class InterfaceIsTrue(Base):
    def test_every_command_on_the_page_exists(self):
        text = page_text()
        named = set(re.findall(r"`gc ([a-z]+[a-z-]*)", text))
        parser_cmds = set()
        import argparse
        ap = argparse.ArgumentParser()
        # collect the subcommand names from gc.py's own parser setup
        src = open(os.path.join(ROOT, "gc.py"), encoding="utf-8").read()
        parser_cmds = set(re.findall(r'sub\.add_parser\("([a-z-]+)"', src))
        parser_cmds |= set(re.findall(r'\("([a-z-]+)", cmd_', src))
        missing = sorted(n for n in named if n not in parser_cmds)
        self.assertEqual(missing, [], "commands on the page that gc does not have: %s" % missing)

    def test_documented_json_shapes_match_the_code(self):
        text = page_text()
        shapes = documented_shapes(text)
        self.assertTrue(shapes, "the page documents no JSON shapes")
        for cmd, extra, shape in shapes:
            if cmd == "decide" and "show" in extra:
                real = self.real_output("decide", "--show")
            elif cmd == "decide":  # the record form: stage a second day so the first receipt is not refused
                dp = os.path.join(self.tmp.name, "draft2.json"); dp2 = os.path.join(self.tmp.name, "dec2.json")
                with open(dp, "w", encoding="utf-8") as f:
                    json.dump({"draft_id": "week-2", "made_on": "2026-11-17", "suggestions": [
                        {"id": "s1", "kind": "fact", "question": "Keep the note?",
                         "subject_kind": "item", "subject_name": "m1", "fact_key": "note", "value": "still wanted"}]}, f)
                with open(dp2, "w", encoding="utf-8") as f:
                    json.dump({"s1": {"decision": "yes", "words": "keep it"}}, f)
                rc, out, err = self.gc("decide", "--draft", dp, "--decisions", dp2, "--day", "2026-11-18", "--json")
                self.assertEqual(rc, 0, err)
                real = json.loads(out)
            elif cmd == "answer" and "subject-kind" in extra:
                rc, out, err = self.gc("answer", "--subject-kind", "item", "--subject", "m1", "--fact", "note",
                                       "--value", "ok", "--words", "his words", "--question", "Keep this?", "--json")
                self.assertEqual(rc, 0, err)
                real = json.loads(out)
            elif cmd == "answer":
                rc, out, err = self.gc("answer", str(self.q), "yes", "--json")
                self.assertEqual(rc, 0, err)
                real = json.loads(out)
            else:
                real = self.real_output(cmd, extra)
            errs = diff_keys(shape, real)
            self.assertEqual(errs, [], "`gc %s%s` shape differs from the page" % (cmd, extra))

    def test_a_wrong_field_planted_on_the_page_is_caught(self):
        text = page_text()
        planted = text.replace('"arrived_total"', '"arrived_totals"')  # one field name quietly renamed
        self.assertNotEqual(planted, text, "planted case did not change the page copy")
        for cmd, extra, shape in documented_shapes(planted):
            if cmd == "week":
                real = self.real_output("week", "")
                errs = diff_keys(shape, real)
                self.assertTrue(any("arrived_totals" in e for e in errs),
                                "the planted wrong field name was NOT caught")


if __name__ == "__main__":
    unittest.main()
