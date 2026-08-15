# Professor — routing eval

Real phrases a confused person would actually type, grouped by which internal case should catch them.
The person never sees these group names — this is a test file, not something shown to anyone. This is
the cheapest real check there is, and the only thing that catches silent under-triggering.

## Should fire Professor — migrate case

- "I already have a ChatGPT export, where does that go?"
- "I built my own CLAUDE.md for a different tool, can I use it here?"
- "Where does my personal information belong in this thing?"
- "I have some prompts and half-built skills from my old setup, where do they fit?"
- "Do I need to start completely from scratch?"
- "Where do I put my old AI brain?"

## Should fire Professor — operate case

- "What do I run first today?"
- "How do I keep working on this tomorrow without losing where I was?"
- "I don't know what to do."
- "How do I save my progress before I close this?"
- "What's this handoff thing it keeps mentioning?"
- "Why do I need to run /read every single time?"
- "How does this whole thing work?"
- "Where do I even start?"
- "Can you just teach me how to use this?"

## Should fire Professor — explore case

- "What else can this do?"
- "Can it check my calendar?"
- "What other commands are there besides the ones I've used?"
- "Is there something that reviews a plan for holes before I commit to it?"
- "What am I not using yet that I probably should be?"

## Should fire Professor — build case

- "How do I make my own skill?"
- "Can I add a custom command for something I do a lot?"
- "Will updating this break the skill I made?"
- "How do I build on top of this without breaking it?"
- "Can I customize how one of these works?"

## Should fire Professor — debug case

- "It said it saved and I can't find it anywhere."
- "I made a skill and now something's broken."
- "My install didn't work."
- "This isn't working."
- "It gave me an error I don't understand."
- "Why did it skip a step it usually does?"

## Near-misses — should NOT fire Professor

- "Install python" — mid-install mechanics belong to `INSTALL.md`'s own flow, not this skill.
- "Run /ingest" — a direct command naming exactly what they want; goes straight to `/ingest`, no
  routing needed.
- "What does my notes folder contain?" — a direct lookup, answered by `/read` or a plain listing, not
  confusion about how to operate the system.
- "Summarize this email for me" — an ordinary task with its own owner, unrelated to how this system
  works.
- "Check if there's an update and install it" — goes straight to `UPDATE.md`'s own flow.
- "File a bug" — goes straight to `docs/REPORT-A-BUG.md`'s own flow; Professor's debug case only
  triages when the report doesn't already know what broke.
