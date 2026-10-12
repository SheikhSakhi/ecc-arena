---
name: ecc-arena
description: >-
  Make N versions of a whole project compete, find what the winner is missing, and fill it from the
  others. Every competitor is an Everything-Claude-Code (ECC) agent chain with its own skills,
  reasoning mode and strategy; each builds a complete, build-ready project package (completeness
  matrix, PRD, architecture, policies, tasks, tests, ops, CLAUDE.md). Judges build the union of
  every competitor's completeness matrix, probe every package with scenarios, and score it. A chief
  judge picks the winner and, for every matrix cell the winner leaves empty, orders a transplant
  from a package that filled it or declares an open gap. A surgeon assembles one package, a
  verifier re-audits it, and a deliverer produces the project folder to continue in Claude Code
  plus a business plan and a pitch deck. Use when the user says "ecc arena", wants a project
  designed from every angle, or complains that a plan or an arena left gaps.
argument-hint: "[--agents N | --quick | --full] [--seed S] [--model M] <project>"
---

# ecc-arena

The bracket arena makes answers fight pairwise and throws away the loser's good ideas. This one is
for projects. Every competitor prepares the whole project through a different ECC chain, judges
find what each one is missing with a completeness matrix built from the task, and the winner gets
what it lacks from the packages that have it. You are the orchestrator. You never compete, judge,
merge, verify or deliver.

What the user typed after the command: `$ARGUMENTS`

If that is blank, or reads like a placeholder, take the project from the conversation.

## The engine

Every piece of bookkeeping goes through `engine.py` in this skill's folder:

```bash
python3 "${CLAUDE_SKILL_DIR}/engine.py" <command>
```

Below, `ENGINE` means exactly that command. If the path looks unexpanded, use the "Base directory for
this skill" that Claude Code printed at the top of this skill. State lives in
`.ecc-arena/<run>/arena.json` in the current directory, and every command after `init` finds it through
`.ecc-arena/LATEST`. Run every command from the directory you ran `init` in.

## Step 1: size it, and say what it costs

Read the flags out of the request. Everything that is not a flag is the project.

| flag | meaning |
| --- | --- |
| `--quick` | 10 competitors, one audit group. The default. |
| `--full` | 100 competitors, ten audit groups. |
| `--agents N` | Any other number. |
| `--seed S` | Fixes the cards and the groups. Default: random, and recorded. |
| `--model M` | One model for every role. Default: per-role models from `deck.json` (Sonnet for competitors, auditors and the deliverer; Opus for the chief judge, surgeon and verifier). |

Run `ENGINE plan` with the same flags. It prints the calls per phase. Tell the user in one line, for
example "10 competitors, 1 audit group, 16 to 18 sub-agent calls; each competitor call prepares a
whole project package", and start. If this skill fired without the user asking for an arena, ask
once, offering `--quick` or an ordinary plan, and wait.

Sub-agents write hundreds of files into `.ecc-arena/` in the current directory. Before the compete
phase, suggest accept-edits mode (Shift+Tab) for the run. Do not change the user's settings yourself.

## Step 2: write the task file

This step decides the result. **Sub-agents cannot see this conversation.** Every competitor, judge,
surgeon and deliverer knows only what is in the task file. Write `.ecc-arena/task.md` to stand on its
own:

- The project, in the user's own words where you can: what it is, for whom, what it must do.
- Every requirement and constraint the user stated anywhere in the conversation: jurisdiction,
  stack, budget, deadline, platforms, what must not change, who the users are.
- The context a stranger would need: absolute paths of files that matter, pasted data, existing
  conventions, links.
- What "done" looks like, if the user said.
- If a previous attempt had gaps the user noticed (no spend limit, no rule for who may vote), list
  them in the user's words. The judges' matrices will carry those rows.

Do not add requirements the user never gave. Do not write your own view of the right design into it:
that pushes every competitor the same way, which is the opposite of the point.

## Step 3: init

```bash
ENGINE init --task-file .ecc-arena/task.md [--quick | --full | --agents N] [--seed S] [--model M]
```

`init` copies the task and the method docs (`matrix.md`, `lenses.md`, `rubric.md`, `criteria.json`)
into the run folder, deals every competitor a distinct card (ECC chain with its agents and skills,
reasoning mode, strategy), splits them into audit groups of ten, and writes `arena.json`.

## Step 4: the loop

Always drive it with `ENGINE next`. It reads the state on disk, writes the briefs for the current
phase, and prints the exact Agent calls still to run, in waves.

Every phase works the same way:

1. `ENGINE next` writes one brief per job and lists the jobs still to run, in waves, with the model
   for each.
2. Launch **one wave at a time**: a single message with one Agent tool call per job in that wave.
   Each call is:
   - `subagent_type`: `general-purpose`
   - `model`: the model `next` printed for that job
   - `description`: `ecc-arena <job id>`
   - `prompt`: `Read <prompt path> and follow it exactly. It is your whole brief.`
   - `run_in_background`: false, so the wave comes back together.

   Wait until every agent in the wave has replied before launching the next wave.
3. After the last wave, run `ENGINE next` again. If an output is missing or a judge's JSON is broken,
   it says which, and `next` lists only the missing jobs. Re-run those once. If a competitor fails
   twice, write the single line `NO OUTPUT` into each of its five required files (`ENGINE check
   compete` lists the paths) and move on: the auditors score it as empty and fatal. A judge, surgeon,
   verifier or deliverer that fails twice gets a third, fresh run. Never judge, merge, verify or
   deliver anything yourself.

The order `next` takes you through:

- **compete**: every competitor builds its completeness matrix from the task and writes a full
  project package: MATRIX.md, PRD.md, ARCHITECTURE.md, POLICIES.md, TASKS.md, TESTS.md, OPS.md,
  CLAUDE.md, README.md.
- **audit**: one judge per group of ten builds the union matrix of its group, lists every package's
  empty cells as gaps with evidence, probes every package with scenarios, and scores the five
  criteria.
- **verdict**: the chief judge merges the unions, reads the shortlist, picks the winner, and for
  every cell empty in the winner orders a transplant from a package that filled it or declares an
  open gap.
- **surgery**: the surgeon assembles the final package and a log of every transplant and every gap
  filled or marked `DECISION NEEDED`.
- **verify**: the verifier rebuilds the matrix from the task, checks every claimed cell at the place
  the package names, probes, and scores. If it fails and passes remain, `next` sends the surgeon
  back in with the verifier's list. Two passes by default.
- **deliver**: the deliverer writes the project folder to continue in Claude Code, the business plan
  and the pitch deck.
- `next` prints DONE: go to step 5.

After each phase, give the user one line, such as "Audit done: 1 group, 10 packages, 142 union
cells." Never paste packages, audits, verdicts or logs into the chat.

Why waves: Claude Code runs at most 10 tool calls at once by default
(`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`). A 10-competitor run is one compete wave and then single
calls; a 100-competitor run is ten compete waves and one audit wave.

## Step 5: the result

Run `ENGINE winner`. It prints the winner and its card, the union size, every transplant and every
open gap from the verdict, the verification result, and the deliverable paths. Read the surgery log
and the deliverable README; those are the only run files you read. Give the user:

1. **Where to continue**: the `deliverable/project/` path and the exact first message to give Claude
   Code there, from its README.
2. **The business plan and the pitch deck**: their paths.
3. **How it was assembled**: the winner's card in one line, then each transplant as "cell: wallet x
   spend / per-member limit, from A007" in a short list, from the surgery log.
4. **What was filled and what you must decide**: the gaps the surgeon closed, and every
   `DECISION NEEDED` item.
5. **What is still open**: the verifier's remaining gaps, undefined probes and contradictions,
   honestly, if it did not pass.
6. Where the full record lives: the run folder.

The deliverable is a folder outside the user's project. Do not copy it anywhere unless asked.

## Rules for the orchestrator

- You run the arena. You do not compete, audit, judge, merge, verify or deliver, and you never pick a
  winner. The engine records what the judges wrote.
- Every sub-agent gets the task through its brief, which the engine builds from the one task file,
  byte for byte the same for everyone. Never paraphrase the task for one agent or add a hint to one
  agent's call.
- Do not read packages, audits or verdicts during the run. The state is on disk, and `next`,
  `status` and `check` are all you need.
- If your context gets compacted mid-run, nothing is lost. Run `ENGINE status`, then `ENGINE next`,
  and carry on.
- Sub-agents only write inside `.ecc-arena/`. If one wrote anywhere else, tell the user.
- If the user says stop, stop. `ENGINE status` shows where it got to, and `ENGINE next` resumes it
  later.

## The briefs

The engine fills the templates in `prompts/` (the `{{placeholders}}`) and writes one brief per job.
Every sub-agent is told exactly what its template says and nothing else. Never edit a brief for a
single agent. The method is in `matrix.md`, the question generator in `lenses.md`, the scoring in
`rubric.md` and `criteria.json`, the cards in `deck.json`. ECC agents and skills are resolved from
the user's `~/.claude` first, then from the vendored copy in `ecc/`.
