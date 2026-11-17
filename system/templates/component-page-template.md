> This component-page template is adapted from the arc42 architecture documentation template (https://arc42.org) by
> Gernot Starke and Peter Hruschka, licensed under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).
> Changes: it reuses the section-5 building-block (blackbox) fields as a standalone per-component page, with added
> intent, generated as-built, and stamped status sections. This adapted template is itself licensed under CC BY-SA
> 4.0, provided as is without warranty. The arc42 authors do not endorse this adaptation.

# Component page template

This template is a highly recommended starting point, not a form: a page may add sections, depart from this layout, and run as long as it needs to — there is no length limit. What stays firm is the mechanism: intent as pointers to canon, the generated as-built block, the stamped status block, and the shared-ownership pointer pattern.

Fill in every section; the HTML comment on each says who writes it. The fenced blocks are written by the generator and the stamper — leave them empty and untouched; a hand edit inside a fence is overwritten and reported.

```markdown
---
component: <slug>            # the triage slug (§8 of the definition)
title: "<the approved name, exactly>"
source: origin/V2            # where as-built is read
scope:                       # human: what belongs here; the generator expands it
  - <repo path or glob>      # one entry per file the component is
shared:                      # §6 of the definition; only if a file is homed elsewhere
  - {paths: [<path>], home: false, role_here: friction|check|data, file_home: <other slug>}
checks:                      # what "working" means, per check id; the register carries the checks at run time
  - {id: <register id>, watches: "<the canon outcome, in one clause>"}
receipts:
  - <brain>/status/component-<slug>.json
health: []
---
# <Title>
<!-- roll-up, generated: <LABEL> · checked <date> · valid until <date> · <receipt> · Health · as-built sha · last reading -->

## Purpose/Responsibility <!-- human: one plain sentence (the approved purpose) + pointers up to canon; no restatement, no rule -->
## Interface(s) <!-- human: each seam to another component — what crosses, which way, the carrying file, the other page -->
## Quality-/Performance characteristics <!-- human: what "working" means per check id, each pointed at canon's desired outcome -->
## Directory/file location <!-- human: one line of scope meaning; the generator writes the block -->
<!-- AS-BUILT:BEGIN generator=<path> source=origin/<branch>@<sha> fetched=<time> sha256=<hash of body> -->
<!-- AS-BUILT:END -->
## Fulfilled requirements <!-- human: canon lines this component fulfils, including the SOP's "not built yet" slots -->
## Open issues/problems/risks <!-- DELTA -->
### Known <!-- human: pointers only — debt-ledger lines, canon Open Tensions, the appeals; no restatement -->
### Delta reading (AI, dated) <!-- an AI reader with judgment; names its inputs; never edits the blocks or canon -->
## Inside (whitebox) <!-- human -->
<!-- overview diagram (text or Mermaid) · motivation for the decomposition · each part as a mini-blackbox: responsibility + scope -->
## Status <!-- checker → stamper; the suffix line is human-owned, outside the fence -->
Suffix (human-owned): ·gap
<!-- STATUS:BEGIN stamper=<path> stamped=<time> sha256=<hash> -->
<!-- STATUS:END -->
## Shared ownership <!-- human, in words; the generator verifies the files -->
## Pointed at by <!-- generator: SOPs whose References name this page -->
---
Structure adapted from arc42 (CC BY-SA 4.0); see `system/templates/component-page-template.md`.
```
