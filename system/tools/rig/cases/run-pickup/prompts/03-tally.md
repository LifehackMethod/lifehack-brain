Step {{ID}} of {{TOTAL}} of the practice skill "run-pickup-practice" (mode: {{MODE}}). This step is done ALONE — the person does not need to be asked anything; when the file passes its check, the run moves on by itself.

Your task: in the file {{OUT}}, under the heading `## Tally`, write 3-4 sentences that count up what the previous steps produced (two habits listed, one rule of thumb chosen). Plain prose; nothing else is required.

End the file with the line `Code word: {{CODE}}` (this exact word — it is how the runner verifies the step).

Then run: python3 {{RUNNER}} advance --workdir .
(from the working folder you are in) so the runner verifies this alone step and moves the
run on itself. {{RUNNER}} is the full path to stage_runner.py in this repository's
system/parts/ folder.
