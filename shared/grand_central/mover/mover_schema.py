# origin: 92a9739:mover/mover_schema.py
"""mover_schema.py - the strict request schema + refusal rules, in Python.

Code.gs (validate_) enforces the SAME rules inside Apps Script. Keep the two in step
(tests/test_gs.py runs shared vectors through both, and checks the constants appear in Code.gs).

A request is plain JSON:
  {"request_id": "...", "created_at": "2026-11-12T10:00:00Z",
   "actions": [ {"op": "addLabel"|"removeLabel"|"archive"|"trash"|"untrash", "label": "<existing user label>", "ids": ["<gmail message id>", ...]} ]}
Unknown op / unknown field / anything off-schema refuses the WHOLE request.
"""
import re

ALLOWED_OPS = ["addLabel", "removeLabel", "archive", "trash", "untrash"]
LABELLESS_OPS = ["archive", "trash", "untrash"]   # take no label field
REQUEST_KEYS = ["request_id", "created_at", "actions"]
ACTION_KEYS = ["op", "label", "ids"]

# Per-request SAFETY cap (separate from Google's quotas; a typo guard, not a quota rule).
MAX_IDS_PER_REQUEST = 5000
MAX_ACTIONS_PER_REQUEST = 20
# "trash" is for approved always-junk only. Its own tighter cap: one request can trash at most this many ids in total
# (untrash, the undo, is not capped beyond the general cap). Trash is recoverable (Gmail keeps it ~30 days); nothing is deleted.
MAX_TRASH_IDS_PER_REQUEST = 1000
BATCH_SIZE = 1000            # Gmail batchModify maximum ids per call

# Gmail built-in labels. Never usable as a label name. ONE exception: addLabel "INBOX" is allowed,
# because it is the inverse of archive (the undo log needs it). removeLabel "INBOX" is refused: use archive.
SYSTEM_LABELS = ["INBOX", "SENT", "DRAFT", "SPAM", "TRASH", "UNREAD", "STARRED", "IMPORTANT", "CHAT",
                 "CATEGORY_PERSONAL", "CATEGORY_SOCIAL", "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES",
                 "CATEGORY_FORUMS", "YELLOW_STAR"]

REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
CREATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
MSG_ID_RE = re.compile(r"^[0-9a-f]{8,24}$")
LABEL_MAX_LEN = 225


def inverse(action):
    """The undo action for one applied action (same shape as a request action)."""
    op = action["op"]
    if op == "addLabel":
        return {"op": "removeLabel", "label": action["label"], "ids": list(action["ids"])}
    if op == "removeLabel":
        return {"op": "addLabel", "label": action["label"], "ids": list(action["ids"])}
    if op == "trash":
        return {"op": "untrash", "ids": list(action["ids"])}
    if op == "untrash":
        return {"op": "trash", "ids": list(action["ids"])}
    return {"op": "addLabel", "label": "INBOX", "ids": list(action["ids"])}   # archive


def validate(req):
    """Return a list of error strings; empty means the request is acceptable."""
    errs = []
    if not isinstance(req, dict):
        return ["request must be a JSON object"]
    for k in req:
        if k not in REQUEST_KEYS:
            errs.append("unknown request field: %s" % k)
    for k in REQUEST_KEYS:
        if k not in req:
            errs.append("missing request field: %s" % k)
    rid = req.get("request_id")
    if "request_id" in req and not (isinstance(rid, str) and REQUEST_ID_RE.match(rid)):
        errs.append("bad request_id")
    ca = req.get("created_at")
    if "created_at" in req and not (isinstance(ca, str) and CREATED_AT_RE.match(ca)):
        errs.append("bad created_at")
    acts = req.get("actions")
    if "actions" not in req:
        return errs
    if not isinstance(acts, list) or not acts:
        return errs + ["actions must be a non-empty list"]
    if len(acts) > MAX_ACTIONS_PER_REQUEST:
        errs.append("too many actions")
    total = 0
    trash_total = 0
    for i, a in enumerate(acts):
        p = "actions[%d]" % i
        if not isinstance(a, dict):
            errs.append(p + " must be an object")
            continue
        for k in a:
            if k not in ACTION_KEYS:
                errs.append("%s unknown field: %s" % (p, k))
        op = a.get("op")
        if not (isinstance(op, str) and op in ALLOWED_OPS):
            errs.append(p + " unknown op")
            continue
        if op in LABELLESS_OPS:
            if "label" in a:
                errs.append(p + " %s takes no label" % op)
        else:
            lab = a.get("label")
            if not isinstance(lab, str) or not lab or len(lab) > LABEL_MAX_LEN or lab != lab.strip() \
                    or re.search(r"[\x00-\x1f]", lab):
                errs.append(p + " bad label")
            elif lab.upper() in SYSTEM_LABELS and not (op == "addLabel" and lab == "INBOX"):
                errs.append(p + " system label not allowed")
        ids = a.get("ids")
        if not isinstance(ids, list) or not ids:
            errs.append(p + " ids must be a non-empty list")
            continue
        bad = [x for x in ids if not (isinstance(x, str) and MSG_ID_RE.match(x))]
        if bad:
            errs.append(p + " bad message id")
        if len(set(x for x in ids if isinstance(x, str))) != len(ids):
            errs.append(p + " duplicate ids")
        total += len(ids)
        if op == "trash":
            trash_total += len(ids)
    if trash_total > MAX_TRASH_IDS_PER_REQUEST:
        errs.append("too many trash ids in request (cap %d)" % MAX_TRASH_IDS_PER_REQUEST)
    if total > MAX_IDS_PER_REQUEST:
        errs.append("too many ids in request (cap %d)" % MAX_IDS_PER_REQUEST)
    return errs
