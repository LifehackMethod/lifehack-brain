# Routing eval: skill-builder

Run every case at least 3 times, each in a cold window (a fresh session, nothing loaded). Re-run all cases whenever the description or triggers change, and on the final commit.

**Scoring rule (set in advance).** 3/3 holds. 0/3 fails. 1 or 2 of 3 is unscored: re-run it. Record each result as k/3 with the commit SHA it was run on. Expect auto-trigger well under 100% even with a good description; 0 of 3 is the defect.

"Front door" below means `/build`. The plugin's current `build` skill is the old plan-executor ("execute the plan"); where a case says `/build`, it names the front door unless it says "old /build".

## Should start /skill-builder
| id | prompt | why |
|---|---|---|
| S1 | `/skill-builder` | the literal command |
| S2 | "build me a skill that turns my Friday review into a repeatable routine" | a concrete skill request |
| S3 | "make this skill better" (a skill open or pointed at) | improve an existing skill |
| S4 | "I want to design a new skill for handling my invoices, can you help me spec it out?" | design plus spec |
| S5 | "I have a skill I wrote months ago and it's messy; help me bring it up to standard" | improve an existing skill |
| S6 | "help me write the spec for a skill I haven't built yet" | spec only |
| S7 | "act out my skill idea so I can see how it would work before anyone builds it" | role-play |
| S8 | "I want to improve my planning skill, here's what it does now" | points at an existing skill |

## Must NOT start /skill-builder
| id | prompt | belongs to |
|---|---|---|
| N1 | `/build` (the front door, new /build, not the old plan-executor) | the front door decides size and hands over |
| N2 | "I want to build a whole inbox system with a database and scheduled jobs, where do I start?" | too big: the front door (`/build`) |
| N3 | "plan my week" | planning-weekly |
| N4 | "make a plan for this" | autoplan |
| N5 | "execute the plan" or "just do it" (old /build, the plan-executor) | the current `build` skill |
| N6 | "how do I make my own skill?" | `/build`, the front door (a vague "how do I" question) |
| N7 (REQUIRED) | "build me a skill that does X" (a bare request, `/skill-builder` not named, no concrete purpose) | `/build`, the front door; must NOT fire |

Note: S2 gives a concrete purpose and should fire; N7 gives none and must not. If a window cannot tell the two apart, record the clash and send it to the owner; do not tune the description to pass.

## Results
| id | run 1 | run 2 | run 3 | k/3 | commit SHA | date |
|---|---|---|---|---|---|---|
| S1 | 1/1 (typed command loads the skill directly) | | | | | |
| S2 | 3/3 (re-run 2026-11-25) | | | | | |
| S3 | 3/3 | | | | | |
| S4 | 3/3 | | | | | |
| S5 | 3/3 | | | | | |
| S6 | 3/3 | | | | | |
| S7 | 3/3 | | | | | |
| S8 | 3/3 | | | | | |
| N1 | 0/1 (went to build) | | | | | |
| N2 | 0/3 | | | | | |
| N3 | 0/3 (went to planning-weekly) | | | | | |
| N4 | 0/3 (autoplan or none) | | | | | |
| N5 | 0/3 (went to build) | | | | | |
| N6 | 0/3 | | | | | |
| N7 | 0/3 | | | | | |


Run 2026-11-24, headless cold sessions on the medium Claude model, plugin from the V2 working tree with the final
description. First round stopped each session after one turn; the plugin's build-mode hook makes a session read the
skills rules first, so the should-fire cases that looked missed were re-run with four turns (fair both ways: the
hardest must-not-fire cases were re-run with four turns too). Commit SHA: see the BUILD-NOTES G3 line.
