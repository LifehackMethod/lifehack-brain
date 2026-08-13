# ASCII Layout Preview — the cheap render

A **terminal box-diagram** of where the cards/tiles sit, shown IN the chat before any
real HTML render. The preferred way to iterate layout fast: agree placement in
seconds, back-and-forth cheaply, THEN build pixels. Use it whenever proposing or
revising a desk-view layout.

It shows **placement + relative size only** — not final card shape, not content.

## ⚠️⚠️ THE #1 RULE — PASTE IT INTO YOUR REPLY (not just tool output)

**Generating the ASCII is only step 1. Pasting it verbatim into your reply message is the actual deliverable.**

Claude Code collapses long Bash/tool output behind a "+N lines (ctrl+o to expand)" fold — the user will never
see a mock that lives only in tool output. The rendered ASCII MUST appear in the assistant's reply message body
inside a fenced ` ``` ` code block. This applies to ANY visual the user must SEE (ASCII mocks, tables, diagrams).

**The rule:** after running the generator script, copy its printed output and paste it into your reply inside a
fenced code block. Every time, no exceptions. Never treat the tool-output print as sufficient.

## ⚠️ THE PAGINATION GOTCHA (this is the toe-stub — do not repeat it)

The preview "renders weird / wraps / pagination is off" for exactly two reasons:

1. **Non-ASCII glyphs break monospace.** Box-drawing (`│ ┌ ┐ ├ ▎ ▟`), emoji (`✈ 🔥`),
   and even "typographic" punctuation (em-dash `—`, middot `·`, arrows `→ ↗`) are NOT
   single-width in a terminal. One of them in a row and every border below it shifts.
2. **Too wide → it wraps.** Two boxes side-by-side + a gap can exceed the chat panel
   width; the right box wraps to the next line and the whole thing looks shattered.

## THE FIX (always do all four)

1. **Pure ASCII only:** `+ - |` for boxes, plain `A-Z 0-9 . ( ) > [ ]` for text.
   NO emoji, NO box-drawing, NO em-dash/middot/arrows. (`>` not arrow, `.` not middot, `-` not em-dash.)
2. **Keep total width small — target ~45 columns, hard ceiling ~60.** If two columns
   don't fit, **stack the bands vertically** instead of side-by-side.
3. **Don't hand-count padding - generate it.** Use Python `str.center(w)` / `str.ljust(w)`
   to pad every cell to an exact width, so borders always line up.
4. **Present inside a fenced code block IN the chat message** (not only as tool output -
   paste the generated text into the reply so it renders for the user). **See the #1 Rule at the top of this file — Claude Code folds tool output; the user will not see it unless you paste it into the reply.**

## Reusable generator (run via Bash, paste the output into the reply)

```python
LW,RW=26,16   # inner widths; shrink if it wraps
def hr(w): return '+'+'-'*w+'+'
def ln(w,txt=''): return '|'+txt.center(w)+'|'
def band(left,right):
    L=[ln(LW,t) for t in left]; R=[ln(RW,t) for t in right]
    h=max(len(L),len(R))
    L=[hr(LW)]+L+[ln(LW)]*(h-len(L))+[hr(LW)]
    R=[hr(RW)]+R+[ln(RW)]*(h-len(R))+[hr(RW)]
    for a,b in zip(L,R): print(a+' '+b)   # one space gap
```

Call `band([...left card lines...],[...right card lines...])` per band; print a full-width
`+--+` header strip above. Widen/narrow `LW,RW` to convey relative card size
(hero wider than companion). Stack bands by printing them in sequence.

## When to use

Every layout proposal or revision in a desk-view design pass - it's the standard
"show me a rough draft" artifact before committing to an HTML render. Cheap enough to
redo on every change.
