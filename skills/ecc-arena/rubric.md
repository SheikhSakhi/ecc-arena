# The rubric

Every package is scored the same way. Judges write per-criterion scores, gaps and probes; the engine
computes totals and ranks. Nothing is scored on style, length, confidence or the judge's taste.

## The five criteria (weights in `criteria.json`)

| criterion | weight | scored against |
| --- | --- | --- |
| Completeness | 35 | the union completeness matrix: filled cells over applicable cells |
| Correctness | 25 | the scenario probes: survived over run |
| Task fit | 15 | the task text: nothing missing, nothing invented |
| Coherence | 15 | contradictions, dead-end states, rules without numbers or owners, buildability from TASKS.md |
| Simplicity | 10 | the less complicated design at the same completeness |

    total = sum(score x weight) / 10        (0 to 100)

Anchors, for every criterion: 10 means nothing you can fault after checking yourself; 7 means
covered with one or two thin spots; 4 means a real hole a builder would hit; 0 to 2 means absent or
wrong. Use the whole scale. A 7 is not a polite default.

## The fatal rule

`fatal` is set only for a verified flaw that makes the package unusable for the task: it answers a
different question, breaks a hard constraint the user stated, would break the law in the stated
jurisdiction, loses money with no recovery, a core flow cannot work as written, or a required file is
missing. A fatal package cannot rank above a non-fatal one, whatever the totals say.

## Ranking across groups

Group judges see up to ten packages each, so scores drift between groups. The engine ranks by rank
inside the group first, then raw total. The chief judge gets the top K by that order and may read
any package beyond the top K that the global union names as the only holder of a cell.

## Transplants: only for gaps

A transplant is allowed only when a union cell is empty in the winner and filled in a donor. If more
than one donor fills it, the donor whose cell passed its probe and whose design is closest to the
winner's is chosen. The surgeon rewrites the part into the winner's vocabulary, files and data model.
A transplant is never ordered because the donor's version is "better" than a filled cell in the
winner. Every transplant is logged with the union cell, the donor, the file and what changed.

## Open gaps

A union cell empty in every package, or a probe nobody defines, is an open gap. The surgeon completes
it: a concrete value or rule in the project files, with the reasoning, the alternatives and the
place to change it recorded in `notes/COMPLETIONS.md`. Nothing is handed to the user as a question.
Completed gaps are listed in the report so the user can change what they disagree with.

## Verification

The final package passes when every criterion scores at least the threshold (7), no gap is FATAL or
MAJOR, there is no contradiction between files, no probe is undefined, and the engine's own scan
finds no deferral marker (`DECISION NEEDED`, `TBD`, `EMPTY`, `TODO`, "to be decided", "open
question", "user decides") in any package file. Each marker the engine finds is a MAJOR gap added to
the verifier's list. Otherwise the surgeon gets the list and one more pass. After the last allowed
pass, what remains goes to the user in the report.

## What the judge does not reward

- Length, confidence, or writing about quality instead of showing it.
- The approach: judges never see the cards and do not guess them.
- Agreement with the judge's own taste where the task does not ask for it.
- Anything that is "configurable later".
