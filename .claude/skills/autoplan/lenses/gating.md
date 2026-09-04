model: sonnet

Angle: ordering and dependency. The gate rule: one task gates another ONLY if
it writes a file the other reads or writes, or the other consumes its output.
Every gate must name the file.

Hunt for:
- gates that name no file
- false gates (claimed dependency that doesn't actually exist)
- missing gates (two "independent" tasks that actually share a file)
- the true critical path
- max safe parallelism per phase
- any task depending on a LATER phase

Before findings, return:
critical_path: <the sequence>
max_parallel_per_phase: <one line per phase>

Find where this fails. Never improve it, never praise it.
