# canon/

**Everything in this folder is approved by the maintainer.** Being here is the proof of approval.

- **Approval = landing here.** Nothing enters `canon/` without the maintainer's approval, and each move in is its own commit.
- **Each document's approval date is in its history**, the `<name>.history.md` file that sits beside it. History
  files hold dated, verbatim text that left the document. They are a record and are never read in normal use.
- **Changing a document here:** make targeted edits with the Edit tool, on the maintainer's approval. Text that leaves goes
  to the history beside the document first (`system/tools/save/pad_archive.py cutlog`). Replacing a whole file asks
  first, and shell writes into this folder are refused (`system/hooks/guard_canon_write.sh`, repo-canon branch).
- Every other SOP and doc stays where it is until it is approved in.

## What is in it

| Document | What it is |
|---|---|
| `canonical-principles-sop.md` | the merged principles behind the system |
| `skill-building-sop.md` | building, fixing or testing a skill |
| `build-conformance-sop.md` | how conformance works: guards, checks, tests |
| `hook-sop.md` | when and which kind of hook to build |
| `hook-contract.md` | hook mechanics: exit codes, deny format, registration |
| `cron-jobs-sop.md` | adding, changing, switching on or debugging a scheduled job |
| `desk-building-sop.md` | the one canonical statement of a desk's shape |
| `security-canon.md` | the security rules |
| `knowledge-altitude.md` | what goes in canon, records and the layers between |
| `data-layout.md` | where data lives in the notes |

Each has its `.history.md` beside it.
