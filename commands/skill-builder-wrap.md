---
description: turn the notes and the reviewer's findings from an observed skill into fixes
disable-model-invocation: true
---
A hook ran before you saw this. Its tagged line above ("OBSERVE WRAP") names the skill, the notes file and the findings file. If there is no such line, tell the person the hook did not run, and stop.

1. Read the notes file and the findings file in full. Either may be missing; say so plainly if one is.
2. Play them back plainly: the person's notes first, in their own words, then the findings, grouped by kind (DIDN'T HAPPEN, SPEC GAP, LIKELY CAUSE, BETTER WAY).
3. Check each finding against its source: the skill's SKILL.md, its step prompts, or the turn it quotes. Mark each finding "holds", "does not hold" or "cannot tell", with the line you checked. The reviewer is a model and can be wrong.
4. Sort what holds, together with the person's notes, into fixes: what to change, in which file, and why. One line each.
5. Propose the spec edits as exact before and after text. Write nothing until the person says yes; then write only what they approved.
6. When done, tell the person that watching is still on, and that /skill-builder-observe off stops it.
