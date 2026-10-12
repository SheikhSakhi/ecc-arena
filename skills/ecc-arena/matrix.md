# The completeness matrix

This is how the arena finds what is missing. A judge does not "notice" that a project has no spend
limit or no rule for who may vote. The matrix forces the question, and an empty cell is the answer.

## Rows come from the task

Read the task. Write down every **entity** (a noun the system must know about: member, group,
shared wallet, bucket item, proposal, vote, payout) and every **action** (a verb someone or the
system performs: join, leave, deposit, spend, propose, vote, close, refund, remove, report). Rows are
every meaningful pair **entity x action**, plus the system's own actions (expire, remind, reconcile).

If the task says "voting on what to do next", then "proposal x vote" is a row whether or not the
task says another word about it. Rows are implied by the nouns and verbs, not by what the task
spells out.

## Columns come from the lenses

For each row, apply every lens in `lenses.md` that could matter and write the questions it
generates. The lenses are angles, not a checklist. Typical columns for an action row:

| column | the question |
| --- | --- |
| who | who may perform it, and how that is checked |
| when | under what conditions, in which states, within what window |
| limit | the numeric limit per actor, per period, per object, overall |
| at-limit | what happens exactly at and over the limit |
| twice | what happens if it is done twice, or by two actors at once |
| undo | how it is reversed, by whom, until when |
| fail | what the user sees and what the system does when it fails |
| abuse | the most likely abuse of this action and the defense |
| money | every amount it moves, fee, refund, who is liable |
| law | any legal or policy constraint it triggers |
| see | who can see it happened, and what is logged |

An entity row gets columns like: fields and source of truth, states and transitions, who owns it,
retention and deletion, limits on count and size, what references it and what happens when it goes.

## A cell is filled only by a concrete answer

A filled cell has a number, a name, a rule or a state that someone could build and test. These are
empty cells: "reasonable limits apply", "handled by admins", "configurable later", "standard
practice", "TBD", a flow with no owner, a state with no exit.

## How competitors use it

Every competitor builds its own matrix from the task, fills every cell it can, and writes it to
`MATRIX.md` in its package. The rest of the package (PRD, architecture, policies, tasks, tests)
must agree with the matrix: every filled cell has a home in a file, and every rule in a file has a
cell.

## How judges use it

1. **Union.** The judge reads every competitor's matrix in its group and builds the union: every row
   and every column any competitor thought of, with the list of competitors whose cell is filled.
   Nobody's matrix is the reference. The union is the reference, and it gets wider as the arena
   gets bigger.
2. **Gaps.** For each competitor, every union cell it leaves empty is a gap. A cell filled by most of
   the group and empty in one package is a gap with evidence, not an opinion.
3. **Probes.** For every row the judge writes scenarios that should be blocked, allowed or defined,
   and traces each one through the package's own rules: "a non-member votes", "a member spends
   over the limit", "two members spend the last of the wallet at the same time", "a member leaves
   with money in the wallet". A probe whose outcome the package does not define is a gap, whatever
   the prose claims.
4. **Everything else** (correctness, task fit, coherence, simplicity) is scored against the same
   rows, so a design that is elegant but leaves rows empty does not win.

## How the chief judge uses it

The chief judge merges the group unions into one global union with a prevalence count per cell (how
many of N filled it). The winner's empty cells split into two lists:

- **filled by someone else**: a transplant from a donor whose cell passed its probe and fits the
  winner's design; and
- **empty everywhere**: an open gap the surgeon must decide, with the reasoning recorded in
  `DECISIONS.md`.

That is the only reason a part moves from one project to another. Nothing is transplanted because
it is "better". Something is transplanted because it is missing.

## Nothing is left to the user

A cell is never deferred. There is no `DECISION NEEDED`, no `TBD`, no `EMPTY`, no "the user will
decide". A person cannot compute a per-member spend limit, a quorum or a retention period better
than a model that has the whole package in front of it; what a person can do is disagree with a
specific decision and change it. So every decision the task did not make is made in the package,
with its value, its reasoning and arithmetic, the alternatives rejected and the place to change it,
all in `DECISIONS.md`. The engine scans the final package for deferral markers and fails
verification on every hit.
