# origin: 92a9739:mover/tests/test_schema.py
"""Schema refusals: Python validator, and the SAME vectors through validate_ in Code.gs (parity)."""
import copy, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mover_schema as S  # noqa: E402
import gsrun  # noqa: E402

I = gsrun.ids(3)
GOOD = gsrun.req([{"op": "addLabel", "label": "Projects/Alpha", "ids": I}, {"op": "removeLabel", "label": "Projects/Alpha", "ids": I},
                  {"op": "archive", "ids": I}, {"op": "addLabel", "label": "INBOX", "ids": I},
                  {"op": "trash", "ids": I}, {"op": "untrash", "ids": I}])


def mut(f):
    r = copy.deepcopy(GOOD); f(r); return r


BAD = {
    "unknown op": mut(lambda r: r["actions"][0].update(op="spam")),
    "trash with label": mut(lambda r: r["actions"].append({"op": "trash", "label": "x", "ids": I})),
    "untrash with label": mut(lambda r: r["actions"].append({"op": "untrash", "label": "TRASH", "ids": I})),
    "trash over its cap": mut(lambda r: r["actions"].append({"op": "trash", "ids": gsrun.ids(S.MAX_TRASH_IDS_PER_REQUEST + 1)})),
    "trash cap is per request": mut(lambda r: r["actions"].extend([{"op": "trash", "ids": gsrun.ids(S.MAX_TRASH_IDS_PER_REQUEST, 0)},
                                                                  {"op": "trash", "ids": gsrun.ids(1, 5000)}])),
    "batchDelete op": mut(lambda r: r["actions"][0].update(op="batchDelete")),
    "removeLabel TRASH": mut(lambda r: r["actions"][1].update(label="TRASH")),
    "trash op bad id": mut(lambda r: r["actions"].append({"op": "trash", "ids": ["zz"]})),
    "delete op": mut(lambda r: r["actions"][0].update(op="delete")),
    "unknown action field": mut(lambda r: r["actions"][0].update(cc="x")),
    "unknown request field": mut(lambda r: r.update(extra=1)),
    "missing request_id": mut(lambda r: r.pop("request_id")),
    "bad request_id": mut(lambda r: r.update(request_id="a b")),
    "bad created_at": mut(lambda r: r.update(created_at="yesterday")),
    "empty actions": mut(lambda r: r.update(actions=[])),
    "archive with label": mut(lambda r: r["actions"][2].update(label="Projects/Alpha")),
    "add without label": mut(lambda r: r["actions"][0].pop("label")),
    "system label TRASH": mut(lambda r: r["actions"][0].update(label="TRASH")),
    "system label spam lower": mut(lambda r: r["actions"][0].update(label="spam")),
    "addLabel UNREAD": mut(lambda r: r["actions"][0].update(label="UNREAD")),
    "removeLabel INBOX": mut(lambda r: r["actions"][1].update(label="INBOX")),
    "bad id": mut(lambda r: r["actions"][0]["ids"].append("not-an-id")),
    "numeric id": mut(lambda r: r["actions"][0]["ids"].append(12345678)),
    "dup ids": mut(lambda r: r["actions"][0]["ids"].append(I[0])),
    "empty ids": mut(lambda r: r["actions"][0].update(ids=[])),
    "over cap": mut(lambda r: r["actions"][0].update(ids=gsrun.ids(S.MAX_IDS_PER_REQUEST + 1))),
    "label padded": mut(lambda r: r["actions"][0].update(label=" Projects/Alpha")),
    "action not object": mut(lambda r: r["actions"].append("archive")),
}


class Schema(unittest.TestCase):
    def test_good_accepted(self):
        self.assertEqual(S.validate(GOOD), [])

    def test_refusals(self):
        for name, r in BAD.items():
            self.assertTrue(S.validate(r), name)

    def test_trash_at_its_cap_ok(self):
        r = gsrun.req([{"op": "trash", "ids": gsrun.ids(S.MAX_TRASH_IDS_PER_REQUEST)}])
        self.assertEqual(S.validate(r), [])

    def test_trash_inverse_is_untrash_and_round_trips(self):
        a = {"op": "trash", "ids": I}
        self.assertEqual(S.inverse(a), {"op": "untrash", "ids": I})
        self.assertEqual(S.inverse(S.inverse(a)), a)

    def test_non_object(self):
        for x in (None, [], "x", 5):
            self.assertTrue(S.validate(x))

    def test_at_cap_ok(self):
        r = gsrun.req([{"op": "archive", "ids": gsrun.ids(S.MAX_IDS_PER_REQUEST)}])
        self.assertEqual(S.validate(r), [])

    def test_python_and_gs_agree(self):
        vecs = [("good", GOOD)] + list(BAD.items()) + [("none", None), ("list", []), ("cap", gsrun.req([{"op": "archive", "ids": gsrun.ids(S.MAX_IDS_PER_REQUEST)}]))]
        out = gsrun.gs([{"call": "validate_", "args": [v]} for _, v in vecs])
        for (name, v), gs_errs in zip(vecs, out["results"]):
            self.assertEqual(bool(S.validate(v)), bool(gs_errs), "%s py=%s gs=%s" % (name, S.validate(v), gs_errs))

    def test_constants_mirrored(self):
        src = (Path(__file__).resolve().parent.parent / "Code.gs").read_text()
        for line in ("var MAX_IDS_PER_REQUEST = %d;" % S.MAX_IDS_PER_REQUEST, "var BATCH_SIZE = %d;" % S.BATCH_SIZE,
                     "var MAX_ACTIONS_PER_REQUEST = %d;" % S.MAX_ACTIONS_PER_REQUEST,
                     "var MAX_TRASH_IDS_PER_REQUEST = %d;" % S.MAX_TRASH_IDS_PER_REQUEST):
            self.assertIn(line, src)
        for s in S.SYSTEM_LABELS + S.ALLOWED_OPS + S.REQUEST_KEYS + S.ACTION_KEYS:
            self.assertIn("'%s'" % s, src)


if __name__ == "__main__":
    unittest.main()
