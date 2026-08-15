# The size / confidence readout (Phase 0 → Phase 2 round-count signal)

After assembling the Map, emit a short readout the session uses to set Phase 2's depth. Compute it mechanically
(counts, not vibes):

```
## Size / confidence readout
- items in window: <N>   (emails <e> · tasks <t> · events <v>)
- already-annotated (had a HITL note, read via note): <a>    ← until Phase D ships the store, this is 0
- fresh deep-reads this run: <N - a>
- un-annotated ratio: <pct>
- SUGGESTED PHASE-2 PASS: LIGHT (mostly annotated / small) | MEDIUM | HEAVY (large + little annotated)
```

The suggestion is a HINT for the adaptive round count, never a hard rule. Do NOT infer the numbers — count them
from the actual window.

## FAN-OUT COST — report it every run (added 2026-08-03)

Also emit, per map-agent:

```
## Fan-out cost
- <angle>: <turns> turns · <output_tokens> out · <wall_seconds>s
- TOTAL: <turns> turns · <output_tokens> out · slowest agent <s>s  ← the slowest agent is the phase's real cost
```

**Why this line exists — the multiplier was invisible and it was the whole bill.** Measured 2026-08-03 from
the independent wire record: **80 turns across 4 agents (20 each)** · **40 `Read` calls where 3 each were
instructed** · **6,222,673 cache-read tokens** against a 48,912-token bundle — **the bundle re-entered
context ~32× per agent.** Nobody had looked, because turn count appears in no design document and shows up
only on the bill.

⚠ **THIS IS MEASUREMENT, NOT A GATE — say so, and do not pretend otherwise.** Nothing lets a skill CAP a
sub-agent's turns. The point is that a high count becomes a **finding a human can act on** instead of an
invisible cost. **Baseline to compare against: 20 turns / ~47.5k output tokens per agent.** A run materially
above that is worth surfacing in the readout, not swallowing.
