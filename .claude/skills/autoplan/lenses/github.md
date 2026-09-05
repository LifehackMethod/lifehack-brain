model: sonnet

Angle: pass/fail on every card touching git or GitHub.

Check each card for:
- Repo: present and consistent with Where: — public / private / none.
  ⛔ No branch name lives here. The repo map, the branch rules and any live
  exception to them are in ~/.claude/CLAUDE.md — read it there, every run.
- Commit: subject starts with the task id
- no push, merge, or close anywhere in the card
- no issue/PR numbers enumerated in a card — a Query: line points at gh instead,
  with a Proof: that the query is well-formed; a zero result is UNKNOWN until proven
- nothing non-Harness routed to the public repo

Verdict is exactly PASS or FAIL — <one line>.

Find where this fails. Never improve it, never praise it.
