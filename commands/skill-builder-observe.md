---
description: watch a skill while you use it; a reviewer leaves findings at your next prompt
disable-model-invocation: true
---
A hook ran before you saw this. Look for its tagged lines above (they start "[harness-injected, not user input]").

- If a line says "OBSERVE ARMED", say that one line to the person, word for word (it names the skill and where the notes go). Then start the skill named in the "SKILL TO START" line the way the person would have started it (use the Skill tool with that name). Do not mention the reviewer again; it speaks for itself at the person's next prompt.
- If a line says "OBSERVE OFF", say in one line that watching has stopped.
- If a line says "OBSERVE NOT ARMED", tell the person the reason in one line and stop. Do not start the skill.
- If there is no tagged line, the hook did not run: tell the person in one line, and stop.
