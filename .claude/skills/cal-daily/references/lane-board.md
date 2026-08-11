# The 10-Lane Board (the visibility gate)

A **rendered scoreboard** of all 10 life-lanes, laid on the table ONCE at the Pass 0→1 boundary —
**before** any interrogation. Its whole job: make every lane's data **visible**, so a starved or a
live lane can never hide behind a silent filter. (The June-24 failure: a lane was truncated upstream
and the run never showed all 10, so the hole stayed invisible until they noticed it themselves.)

## What it is NOT
- **NOT a demand for a move per lane.** Anchors always get a daily move; a quiet 🟡 triggered lane
  still gets nothing (canon: the generative deep-mine is the weekly skill's job). The board shows
  data; **ranking (Pass 4) still respects anchor/triggered.**
- **NOT a preview of the dominoes.** It's the *input* picture, not the output plan.

## The lanes (yours, at `<notes>/desks/cal/skill-refs/user-canon.md`)

A lane is one standing area of your life that the day can move. Write them there once, each marked
as one of two kinds — that distinction is what the board runs on:

🟢 **ANCHOR** — always gets a daily move, whether or not anything happened. The things that decay
   silently if a week goes by: health, a relationship, a programme you are in.
🟡 **TRIGGERED** — surfaces only when something live appeared in it. Work, money, property, admin.

Most people land somewhere between six and twelve. Fewer than that and the board stops being your
whole life; many more and it stops being glanceable, which is the only thing it is for.

## How to build it (from the vault — NO live re-pull)
Read the already-pulled vault (`tasks.json`, `calendar.json`, the inbox slices, `dominoes-draft.md`).
For each lane, by judgment, fold in the data that belongs to it. Reference map (a guide, not a rule —
lists get renamed):
⛔ **THE LANES ARE NOT IN THIS FILE, AND THAT IS DELIBERATE.** A board is a picture of ONE person's
life — their work, their family, the property they own, the recovery programme they are in. Ten of
somebody else's would be worse than none, because a lane you did not choose still gets asked about
every morning. **Your lanes and the lists that feed each one live in
`<notes>/desks/cal/skill-refs/user-canon.md`** — write them there once, in your own words, and this
file is the shape they are rendered in. With no lanes on file, say so and ask for them; do not invent
a set.

## The render (one glance — concrete shape)
One line per lane. **Bold the lane name.** Show: mode badge · a live-item count · a one-clause "what's live" · the ⚠ flag if truncated.

```
THE BOARD — your whole life, on the table (every lane; nothing hidden)
🟢 1 <lane>             — [n live]  <one clause: what is live in it today>
🟢 2 <lane>             — [n live]  …
🟡 3 <lane>             — [n live]  …
   …one line per lane you wrote down, in your order, none omitted…
🟡 n <lane>             — [n live]  (quiet → shows [0 live] — quiet, which is correct, not a gap)
```
Counts come from the vault. A 🟡 lane with nothing live shows `[0 live] — quiet` (correct, not a gap).

## The truncation ALARM (binary, loud)
`tasks.json` now carries `truncated:(total>kept)` per list. **If ANY list feeding a lane is
`truncated:true`, render that lane with a loud `⚠ TRUNCATED — pulled N of M; data is incomplete`**
and say it out loud at the top of the board — data integrity beats a tidy board. A truncated lane is
NEVER silently treated as "covered." (With the cap at 50 this should be rare; the alarm is the
backstop for the exact starvation that caused the June-24 miss.)
