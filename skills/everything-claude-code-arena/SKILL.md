---
name: everything-claude-code-arena
description: >-
  Make N versions of a whole project compete, then assemble the best body from all of them. Every
  competitor is an Everything-Claude-Code agent chain with its own reasoning mode, strategy and an
  emphasis it obsesses over (legal, money and spend limits, voting and governance, security,
  logistics, operations, and so on). Each writes a complete project blueprint. Group judges audit
  every blueprint on sixteen lenses A to Z, a chief judge picks the winner and orders transplants of
  the best parts from the other blueprints, a surgeon assembles one body, and a verifier hunts the
  remaining gaps until it passes. Optionally builds the project with a few builders and merges the
  best build the same way. Use when the user says "ecc arena", "everything claude code arena",
  "make the projects compete", wants a project designed from every angle, or complains that an
  arena or a plan left gaps.
argument-hint: "[--agents N | --quick | --full] [--build [--builders B]] [--seed S] <task>"
---

# everything-claude-code-arena

The bracket arena makes a hundred answers fight pairwise and leaves the loser's good ideas on the
floor. This one is built for projects. Every competitor designs the whole project through a different
Everything-Claude-Code (ECC) chain and obsesses over a different part of it, a judge audits every
design from A to Z, and the winner gets the best parts of every other design grafted in. You are the
orchestrator. You never compete, judge, merge or build.

What the user typed after the command: `$ARGUMENTS`

If that is blank, or reads like a placeholder, take the task from the conversation.

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

Read the flags out of the request. Everything that is not a flag is the task.

| flag | meaning |
| --- | --- |
| `--agents N` | N competitors. Default 36 (three per emphasis). |
| `--quick` | 12 competitors, one per emphasis. The cheap setting. |
| `--full` | 100 competitors. |
| `--build` | After the blueprint passes, build it with `--builders B` builders (default 3) and merge the best build. |
| `--seed S` | Fixes the cards and the groups. Default: random, and recorded. |
| `--model M` | One model for every role. Default: per-role models from `deck.json` (sonnet for competitors, auditors and builders; opus for the chief judge, surgeon and verifier). |

Run `ENGINE plan` with the same flags. It prints the calls per phase and, for comparison, what the
bracket arena would have cost for the same N. Tell the user in one line, for example "36 competitors,
4 audit groups, 45 to 47 sub-agent calls", and start. If this skill fired without the user asking for
an arena, ask once, offering `--quick`, the default, and an ordinary plan, and wait.

Sub-agents write into `.ecc-arena/` in the current directory. Before the blueprint phase, suggest
accept-edits mode (Shift+Tab) for the run. Do not change the user's settings yourself.

## Step 2: write the task file

This step decides the result. **Sub-agents cannot see this conversation.** Every competitor, judge and
surgeon knows only what is in the task file. Write `.ecc-arena/task.md` to stand on its own:

- The project, in the user's own words where you can: what it is, for whom, what it must do.
- Every requirement and constraint the user stated anywhere in the conversation: jurisdiction,
  stack, budget, deadline, platforms, what must not change, who the users are.
- The context a stranger would need: absolute paths of files that matter, pasted data, existing
  conventions, links.
- What "done" looks like, if the user said.
- If a previous attempt (an arena, a plan, a build) had gaps the user noticed: list those gaps in the
  user's words. They become requirements the judges check.

Do not add requirements the user never gave. Do not write your own view of the right design into it:
that pushes every competitor the same way, which is the opposite of the point.

## Step 3: init

```bash
ENGINE init --task-file .ecc-arena/task.md [--agents N | --quick | --full] [--build --builders B] [--seed S] [--model M]
```

`init` copies the task, the lenses and the rubric into the run folder, deals every competitor a
distinct card (ECC chain, reasoning mode, strategy, emphasis), splits them into audit groups of ten,
and writes `arena.json`.

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
   twice, write the single line `NO OUTPUT` into its blueprint file (`ENGINE check blueprint` lists
   the paths) and move on: the auditors score it as empty. A judge, surgeon or verifier that fails
   twice gets a third, fresh run. Never judge, merge or verify anything yourself.

The order `next` takes you through:

- **blueprint**: every competitor writes a complete project blueprint through its ECC chain.
- **audit**: one judge per group of ten scores every blueprint on all sixteen lenses and names the
  best part in its group for each lens.
- **verdict**: the chief judge reads the shortlist and the best-parts inventory, picks the winner,
  orders transplants, lists open gaps.
- **surgery**: the surgeon assembles the merged blueprint and a log of every transplant and every
  gap filled.
- **verify**: the verifier audits the merged blueprint A to Z. If it fails and passes remain, `next`
  sends the surgeon back in with the verifier's list. Default: two passes at most.
- with `--build`: **build** (each builder builds the merged blueprint in its own folder, tests first),
  **build_judge** (runs every build's install and tests, picks the winner, orders file transplants),
  **build_surgery** (assembles the merged project and makes its tests pass).
- `next` prints DONE: go to step 5.

After each phase, give the user one line, such as "Audit done: 4 groups scored 36 blueprints." Never
paste blueprints, audits, verdicts or logs into the chat.

Why waves: Claude Code runs at most 10 tool calls at once by default
(`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`). A 36-competitor run is 4 blueprint waves, 1 audit wave, and
then single calls.

## Step 5: the result

Run `ENGINE winner`. It prints the winner, its card, the merged blueprint path, the transplants, the
verification result and every open gap. Read the merged blueprint and the surgery log; those are the
only blueprint files you read in the whole run. Give the user:

1. **The merged blueprint**: where it is, and its table of contents. Paste the full document only if
   the user asks or it is short.
2. **How it was assembled**: the winner's card in one line, then each transplant as "from X, lens C:
   spend limits" in a short list, from the surgery log.
3. **What was filled**: the gaps the surgeon closed, in a short list, and every `DECISION NEEDED`
   item, which the user must answer.
4. **What is still open**: the verifier's remaining gaps, honestly, if it did not pass.
5. With `--build`: the merged project path, the test result, and the build surgeon's hand-over notes.
6. Where the full record lives: the run folder.

If the result changes files in the user's project, do not apply it. Ask: apply it, or change it?

## Rules for the orchestrator

- You run the arena. You do not compete, audit, judge, merge, verify or build, and you never pick a
  winner. The engine records what the judges wrote.
- Every sub-agent gets the task through its brief, which the engine builds from the one task file,
  byte for byte the same for everyone. Never paraphrase the task for one agent or add a hint to one
  agent's call.
- Do not read blueprints, audits or verdicts during the run. The state is on disk, and `next`,
  `status` and `check` are all you need.
- If your context gets compacted mid-run, nothing is lost. Run `ENGINE status`, then `ENGINE next`,
  and carry on.
- Sub-agents only write inside `.ecc-arena/`. If one wrote anywhere else, tell the user.
- If the user says stop, stop. `ENGINE status` shows where it got to, and `ENGINE next` resumes it
  later.

## The briefs

The engine fills the templates in `prompts/` (the `{{placeholders}}`) and writes one brief per job.
Every sub-agent is told exactly what its template says and nothing else. Never edit a brief for a
single agent. The lenses are in `lenses.md`, the scoring in `rubric.md`, the cards in `deck.json`.
