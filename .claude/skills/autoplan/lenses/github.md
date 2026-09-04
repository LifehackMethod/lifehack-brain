model: sonnet

Angle: pass/fail on every card touching git or GitHub.

Check each card for:
- Repo: present and consistent with Where: (public · V2 for ~/lifehack-brain;
  private · main for ~/.claude/skills/ClaudeOps; none for anything else)
- Commit: subject starts with the task id
- no push, merge, or close anywhere in the card
- no issue/PR numbers enumerated in a card — a Query: line points at gh instead,
  with a Proof: that the query is well-formed; a zero result is UNKNOWN until proven
- nothing non-Harness routed to the public repo

Verdict is exactly PASS or FAIL — <one line>.

Find where this fails. Never improve it, never praise it.
