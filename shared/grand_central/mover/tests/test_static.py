# origin: 92a9739:mover/tests/test_static.py
"""Static wall: exact scopes, no forbidden API (no read/send/delete), only two Gmail calls, TRASH only via the one trash/untrash pair, only five public functions.
Run: python3 -m unittest discover -s tests   (from the mover folder)"""
import json, re, unittest
from pathlib import Path

MOVER = Path(__file__).resolve().parent.parent
SRC = (MOVER / "Code.gs").read_text()
ALLOWED_SCOPES = ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/drive.file",
                  "https://www.googleapis.com/auth/script.scriptapp"]
FORBIDDEN = [r"\bGmailApp\b", r"\bMailApp\b", r"\bUrlFetchApp\b", r"\bSpreadsheetApp\b", r"\bDocumentApp\b",
             r"\bCalendarApp\b", r"\bContactsApp\b", r"\bDriveApp\b", r"\bSession\.get(Active|Effective)User\b",
             r"Messages\.(get|list|send|trash|untrash|delete|batchDelete|insert|import|modify|attachments)\b",
             r"\bbatchDelete\b", r"\bemptyTrash\b", r"Users\.Labels\.(create|delete|update|patch)\b",
             r"Gmail\.Users\.(Threads|Drafts|History|Settings|getProfile)",
             r"Gmail\s*\[", r"\beval\s*\(", r"\bnew\s+Function\b", r"\bfetch\s*\(", r"\bdoGet\b", r"\bdoPost\b",
             r"\bimport\s*\(", r"\brequire\s*\("]


class StaticWall(unittest.TestCase):
    def test_scopes_exact(self):
        m = json.loads((MOVER / "appsscript.json").read_text())
        self.assertEqual(m["oauthScopes"], ALLOWED_SCOPES)
        for bad in ("webapp", "urlFetchWhitelist", "executionApi"):   # no remote entry points at all: the lock
            self.assertNotIn(bad, m)
        self.assertEqual(m["dependencies"]["enabledAdvancedServices"], [{"userSymbol": "Gmail", "serviceId": "gmail", "version": "v1"},
                          {"userSymbol": "Drive", "serviceId": "drive", "version": "v3"}])
        self.assertFalse(m["dependencies"].get("libraries"))

    def test_no_forbidden_api(self):
        for pat in FORBIDDEN:
            self.assertIsNone(re.search(pat, SRC), "Code.gs matches forbidden %s" % pat)

    def test_only_two_gmail_calls(self):
        found = set(re.findall(r"Gmail\.[A-Za-z_.]+", SRC))
        self.assertEqual(found, {"Gmail.Users.Labels.list", "Gmail.Users.Messages.batchModify"})

    def test_no_trash_spam_in_bodies(self):
        # SPAM and UNREAD are never touched. TRASH appears in EXACTLY two modify bodies: the trash op (adds it) and its
        # undo, untrash (removes it). Nothing else may name TRASH, and neither op may combine it with any other label.
        self.assertIsNone(re.search(r"(addLabelIds|removeLabelIds)\s*:\s*\[[^\]]*(SPAM|UNREAD)", SRC))
        bodies = [(m.group(1), m.group(2).strip()) for m in re.finditer(r"(addLabelIds|removeLabelIds)\s*:\s*\[([^\]]*)\]", SRC)]
        self.assertEqual(sorted(b for b in bodies if "TRASH" in b[1]),
                         [("addLabelIds", "'TRASH'"), ("removeLabelIds", "'TRASH'")])
        for kind, lit in bodies:
            self.assertIn(lit, ("'INBOX'", "labelId", "'TRASH'"))
        # no delete anywhere: not the call, and not an op, in the allowed list
        self.assertEqual(re.search(r"ALLOWED_OPS\s*=\s*\[([^\]]*)\]", SRC).group(1).replace("'", "").replace(" ", "").split(","),
                         ["addLabel", "removeLabel", "archive", "trash", "untrash"])
        self.assertIsNone(re.search(r"\b(delete|batchDelete|emptyTrash)\b['\"]?\s*[:(]", SRC.replace("deleteProperty", "").replace("deleteTrigger", "")))

    def test_only_five_public_functions(self):
        names = re.findall(r"^function\s+([A-Za-z0-9_]+)\s*\(", SRC, re.M)
        public = sorted(n for n in names if not n.endswith("_"))
        self.assertEqual(public, ["pause", "resume", "run", "setup", "teardownTriggers"])

    def test_scriptapp_only_triggers(self):
        for m in re.finditer(r"ScriptApp\.([A-Za-z]+)", SRC):
            self.assertIn(m.group(1), ("getProjectTriggers", "newTrigger", "deleteTrigger"))

    def test_no_driveapp(self):
        # DriveApp needs the full drive scope; we hold only drive.file, so only the Advanced Drive service is allowed
        self.assertNotIn("DriveApp", SRC)

    def test_drive_advanced_calls_only(self):
        for m in re.finditer(r"Drive\.([A-Za-z]+)\.([A-Za-z]+)", SRC):
            self.assertEqual(m.group(1), "Files")
            self.assertIn(m.group(2), ("list", "create", "get", "update"))   # no delete/emptyTrash/permissions

    def test_no_delete_in_drive(self):
        self.assertNotRegex(SRC, r"setTrashed|\.remove\(|Access\.|addEditor|addViewer|setSharing|Permissions|Files\.(remove|delete|emptyTrash)")


if __name__ == "__main__":
    unittest.main()
