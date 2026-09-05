# Scratch fixture — spacey.plan.md

Built for card 6.7's Verify: a JUDGE card whose `artifact:` value contains a directory
with a space in it, so `plan_retire.py get_evidence()` is exercised on the exact shape
that broke (`\S+` truncating a real notes path at its first space).

## Phase 9 — scratch

- [ ] **9.9 Scratch JUDGE card with a spaced artifact path.** `Owner: BUILD` · gear-2, one sonnet helper
  `Where: /private/tmp/claude-501/-Users-envergjokaj--claude-skills-ClaudeOps/2bd5bc3d-75a4-46fe-b716-4276ddfb4c30/scratchpad/`
  `Do:` scratch fixture only, not a real task.
  `Repo: none — scratch` · `artifact: /private/tmp/claude-501/-Users-envergjokaj--claude-skills-ClaudeOps/2bd5bc3d-75a4-46fe-b716-4276ddfb4c30/scratchpad/spaced dir/evidence.md`
  `Verify: JUDGE — artifact:` `test -s "/private/tmp/claude-501/-Users-envergjokaj--claude-skills-ClaudeOps/2bd5bc3d-75a4-46fe-b716-4276ddfb4c30/scratchpad/spaced dir/evidence.md"; echo $?` → `0`
  `model: sonnet`
  `Done: n/a — scratch fixture`
