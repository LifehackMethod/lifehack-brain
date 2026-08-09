# .claude/

This folder is how Claude finds the skill and the specialist readers in this repo. `skills/ingest` is
what makes `/ingest` work the moment you open this folder — no install step, no configuration.

**You don't need to touch anything in here.**

---

*A note for anyone reading the history: these used to be symbolic links pointing into `system/`. They are
now the real files. Links break silently on Windows and break when the repo is downloaded as a ZIP rather
than cloned — and when they break, `/ingest` simply does not exist and nothing reports an error. Real
files work on every machine and every download method.*
