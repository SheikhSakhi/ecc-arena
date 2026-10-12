# The rubric

Every blueprint and every build in this arena is scored the same way. Judges write per-lens scores;
the engine computes the totals. Nothing is scored on style, length or confidence.

## Blueprint score

Sixteen lenses from `lenses.md`, each 0 to 10, each with the weight in `lenses.json`.

    total = sum(score_lens x weight_lens) / 10        (0 to 100)

Plus a `fatal` flag. Set it only for a verified flaw that makes the blueprint unusable or dangerous
for the task: it answers a different question, it breaks a hard constraint the user stated, it would
break the law in the stated jurisdiction, money could be lost with no recovery, or a core flow cannot
work as written. A fatal blueprint cannot rank above a non-fatal one, whatever the totals say.

## Ranking across groups

Group judges see ten blueprints each, so scores drift between groups. The engine normalises: each
blueprint's rank inside its group counts first, then its raw total. The chief judge gets the top K
by that order and may read any blueprint beyond the top K when a group audit says it holds the best
part for some lens.

## Best parts

For every lens, each group judge names the blueprint in its group that handles that lens best, with
the section and one line on why. These inventories are how the chief judge finds parts to transplant
into the winner. A best part must be concrete enough to lift: a rule with numbers, a state machine, a
flow, a table, a policy. "Good coverage of security" is not a part.

## Transplants

A transplant is justified only when the donor's part scores higher on that lens than the winner's and
fits the winner's design without contradiction. The surgeon rewrites the part into the winner's
vocabulary and structure; it does not paste. Every transplant is logged with donor, lens, section and
what changed.

## Verification pass

The merged blueprint passes when every lens scores at least the `pass_threshold` in `lenses.json`
(7), no gap is FATAL or MAJOR, and nothing in it contradicts the task. Otherwise the surgeon gets the
gap list and one more pass. After the last allowed pass, the open gaps go to the user in the report,
not silently.

## Build score, when the arena builds

A build is judged on the same lenses as applied to running code, plus three hard checks: it installs
with the documented command, its tests run and pass, and every feature in the merged blueprint is
present or explicitly listed as not built. A build that fails a hard check is fatal. File-level
transplants from other builds follow the same rule as blueprint transplants, and the merged build must
pass its tests after surgery.

## What the judge does not reward

- Length, confidence, or writing about quality instead of showing it.
- Agreement with the judge's own taste where the task does not ask for it.
- The approach: judges never see the cards and do not guess them.
- Anything that is "configurable later".
