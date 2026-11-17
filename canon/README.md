# canon/

**Everything in this folder is approved by the maintainer.** Being here is the proof of approval.

- **Approval = landing here.** Nothing enters `canon/` without the maintainer's approval, and each move in is its own commit.
- **Each document's approval date is in its history**, the `<name>.history.md` file that sits beside it. History
  files hold dated, verbatim text that left the document, and the shipped source of each ruling. They are a record and are never read in normal use.
- **Changing a document here:** make targeted edits with the Edit tool, on the maintainer's approval. Text that leaves goes
  to the history beside the document first (`system/tools/save/pad_archive.py cutlog`). Replacing a whole file asks
  first, and shell writes into this folder are refused (`system/hooks/guard_canon_write.sh`, repo-canon branch).
- Every other SOP and doc stays where it is until it is approved in.

## What is in it

| Document | Altitude | What it is |
|---|---|---|
| `canonical-principles-sop.md` | high | the merged principles behind the system |
| `skill-building-sop.md` | working | building, fixing or testing a skill |
| `build-conformance-sop.md` | working | how conformance works: guards, checks, tests |
| `hook-sop.md` | working | when and which kind of hook to build |
| `hook-contract.md` | working | hook mechanics: exit codes, deny format, registration |
| `cron-jobs-sop.md` | working | adding, changing, switching on or debugging a scheduled job |
| `desk-building-sop.md` | working | the one canonical statement of a desk's shape |
| `security-canon.md` | high | the security rules |
| `knowledge-altitude.md` | working | what goes in canon, records and the layers between |
| `data-layout.md` | working | where data lives in the notes |
| `context-injection-sop.md` | working | what text a session receives without asking, and how to keep it true |
| `circulatory-system-sop.md` | working | how a project's knowledge crosses the session handoff |
| `helpers-and-model-routing-sop.md` | working | which helper runs on which model tier |
| `connecting-an-outside-service-sop.md` | working | adding a key, token or connector without exposing it |
| `coordinating-windows-sop.md` | working | working beside and handing over between live windows |
| `status-emission-sop.md` | working | the status tile contract and the one writer |
| `status-health-proof-sop.md` | working | proof, receipts and labels for a part that works |
| `sop-template.md` | working | the shape every SOP starts from |

Each has its `.history.md` beside it.

**Altitude** says how hard a change of meaning is (canon as gravity, `canonical-principles-sop.md` §0.5).
