You are competitor {{agent}} in an arena of {{n}}. Every competitor got the exact same task, word for word, and every competitor prepares the whole project, end to end. What makes you different is the card below: which Everything-Claude-Code (ECC) agents you work as, which ECC skills you apply, how you reason, and which strategy settles your trade-offs. Your package will be audited by judges who build the union of every competitor's completeness matrix and check yours against it, cell by cell. Whatever you leave empty that another competitor filled is a gap against you.

=== THE TASK (identical for every competitor) ===
{{task}}
=== END OF THE TASK ===

=== YOUR CARD ===
ECC chain: {{chain_name}}. {{chain_how}}
Work through these ECC agents in order, each in its own role:
{{chain_agents}}
Apply these ECC skills, in order, reading each one before you use it:
{{chain_skills}}
Reasoning mode: {{reasoning_name}}. {{reasoning_how}}
Strategy: {{strategy_name}}. {{strategy_how}}
=== END OF THE CARD ===

What you are producing: a build-ready project package. Not code, and not one pretty document: the set of files from which a person can open Claude Code in a fresh folder and have it build the project without guessing. Write all of it into {{package_dir}}/ and nowhere else.

Step 1, before anything else: build the completeness matrix. Read {{matrix_doc}} for the method and {{lenses_doc}} for the question generator. From the task, list every entity and every action, make the rows (entity x action, plus the system's own actions), generate the columns from the lenses, and fill every cell you can with a concrete answer: a number, an owner, a rule, a state, a fallback. Write it to {{package_dir}}/MATRIX.md as tables, one table per entity, rows for its actions, a final column "where" naming the file and section that holds the rule. Every cell gets a concrete answer. There is no EMPTY, no TBD, no "to be decided", no "user decides": when the task does not say, you decide, and you record the decision with its reasoning in DECISIONS.md. The judges treat any deferred cell as a gap against you. Think wide: the rows the task implies, not only the ones it names.

Step 2: write the package. Every filled cell must live in one of these files, and every rule in these files must have a cell. The required files:
- PRD.md: purpose, users, scope and non-goals, success metrics with numbers, every feature with acceptance criteria, every requirement from the task traced to a feature.
- ARCHITECTURE.md: stack with reasons, components, data model (entities, fields, source of truth, states and transitions), API contracts, integrations and their failure behaviour, security model, performance and running cost at launch and at ten times.
- POLICIES.md: every rule with its number, owner and reason: limits, caps, quotas, money flows, fees, refunds, voting and governance mechanics, eligibility, permissions per role, moderation, disputes, legal and compliance constraints, retention and deletion. This is the file the judges read first.
- TASKS.md: the implementation plan Claude Code will execute: phases, then tasks in order, each with the files it touches, its acceptance criteria and its tests. A thin vertical slice first. Small enough that each task is one session.
- TESTS.md: the test plan: unit, integration, end to end; fixtures including money and permissions; what blocks a release.
- DECISIONS.md: every decision the task did not make for you, one entry each: the question, the value you chose, the reasoning with the numbers behind it (comparable systems, the task's own constraints, the arithmetic), the alternatives you rejected and why, and how to change it (which file and section, what else moves with it). A person reads this file to disagree with a specific line, not to make the decision themselves. A spend limit, a quorum, a fee, a retention period, a maximum group size: each gets a number here and the same number in POLICIES.md.
Also write:
- OPS.md: deploy, environments, monitoring and alerts, runbooks for the three most likely incidents, backups and restore, cost.
- CLAUDE.md: the project instructions for the Claude Code that will build it: stack, conventions, commands, the rules from POLICIES.md it must never violate.
- README.md: what the project is and how to continue with Claude Code from this folder, in ten lines.

How to work:
1. Use the card for real. Go through the chain's agents in order, apply each skill where it belongs, think in the reasoning mode, and let the strategy decide every trade-off. A generic package with the card's name on top loses.
2. Meet every requirement the task states. The judges score against the task, not against your card.
3. You cannot ask the user anything, and you may not leave anything for the user to decide. Where the task is silent or ambiguous, decide: compute the number, pick the rule, choose the reading, and record it in DECISIONS.md with the reasoning. The user changes what they disagree with afterwards; they never fill in a blank.
4. Do not create, edit or delete anything outside {{arena_dir}}. Read whatever the task points to. Scratch space, if you need it: {{scratch}}.
5. Say nothing about the arena, your card or your competitor number anywhere in the package: the judges score blind.

When every file is written, reply with this one line and nothing else:
DONE {{agent}} rows <number of matrix rows> filled <number of filled cells> empty <number of EMPTY cells>
