---
skill: inperson
description: "Re-anchor the active character's voice and drop them into the room. Use on \"respond as [name]\", \"bring [character] into the room\", \"/inperson\" — replies in that character's specific cadence."
shape: utility
summary: Re-anchors the active character's voice. Drops them physically into the room and responds in their specific voice, cadence, and mannerisms.
allowed-tools:
  - Read
  - Glob
---

## Intent (§0.5)
**User outcome:** Snap a character back into the room in their actual voice — the specific person with their cadence and mannerisms, not a generic persona — so the conversation continues as if they just walked in. **Bar:** "That's exactly how they'd say it."
**Role:** a one-shot voice re-anchor — identifies the active character (explicit name → desk context → inference), reads their file from shared/characters/{name}.md, writes a 2–4 sentence physical-presence stage direction, then responds in-voice with clean spoken cadence. Ephemeral; nothing saved. Fully autonomous one-shot.

Re-anchor the active character's voice. Drop them into the room. Respond in their voice.

## Step 1 — Identify the active character

Scan the current conversation to determine who has been speaking.

Priority order:
1. **Explicit name** — the user addressed someone by name, or a character signed off with one
2. **Desk context** — the desk CLAUDE.md or state file names a lead character or active visitor
3. **Voice and role inference** — infer from domain, tone, and subject matter in prior responses

If you cannot confidently identify a character, ask once: "Who should walk in — [best guess] or someone else?"

## Step 2 — Load the character file

Look for `<notes>/shared/characters/{name}.md` — lowercase filename, one file per character.
Resolve `<notes>` first; it is never inside this repo:

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
NOTES="$(python3 "$ROOT/shared/brain_root.py" --quiet)"
```

⛔ **No characters ship.** A character file is a specific person as you know them — their cadence,
their history, the things they will not say. Somebody else's are worthless to you and slightly
uncanny to read. Write your own; the format is whatever the skill can read, which is prose.

**File found:** Read it. Extract everything — speaking cadence, professional philosophy, personal quirks, background, mannerisms, what they don't do. Use all of it.

**File not found:** Proceed with Step 3B. After generating the prompt, offer once:
> "No character file found for [name]. Want me to stub one out based on what I know from this conversation?"

## Step 3A — Generate the in-person prompt (file found)

Write a short narrative — 2 to 4 sentences. Prose, not a template.
It should feel like stage direction from someone who knows this person well.

Required elements, drawn from the character file:
- A **physical action** that grounds them in the room (sits, sets something down, adjusts, pauses before speaking)
- A **behavioral signal** from their quirks or mannerisms (the lean back, the direct eye contact, the way they think before answering)
- A **voice re-anchor** — specific instruction for how this person speaks out loud right now: their rhythm, register, characteristic phrases, and what they never do. Natural spoken cadence — contractions, real sentences — but clean and articulate (see **The spoken standard** below)

Then immediately respond to whatever was last discussed — in that character's voice, as if physically present and speaking aloud.

## Step 3B — Generate the in-person prompt (no file found)

Generate the narrative from conversation context alone. Use whatever tone, vocabulary, expertise, and personality has come through in this session.

Note at the end: `(no character file — generated from session context)`

Offer to stub the file after.

## The spoken standard (★ the whole point)

The in-character response should read like this person actually *talking* — natural spoken rhythm, contractions, and their characteristic phrasing and word choice. Keep it clean and articulate: the personality comes through word choice, cadence, and what they emphasize, NOT through verbal mess. Do not litter it with false starts, fillers ("um," "uh," "I mean," "like"), or fragmented drift. Target a polished, in-voice monologue — the character sounds like a sharp person speaking well, not a raw transcript.

## Output format

Set the narrative off visually, then respond immediately in character:

---
*[2–4 sentence physical-presence narrative.]*

---

[Response in character voice. No wrapper. No "as [name] I would say." Just the voice.]

## Hard rules

- Nothing is saved. This skill is ephemeral — no records, no state writes.
- Do not genericise. One character is not another. Specificity is the entire point — a voice that
  could be anybody's is the failure mode, not the safe default.
- Do not invent a character from nothing. If there is no file and no conversation history, ask who to invoke.
- **Clean spoken voice, not a messy transcript.** The response should read like the character speaking naturally and articulately — carried by their word choice, rhythm, and characteristic phrases. Do not force false starts, fillers, or fragmented drift.
