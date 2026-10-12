# ecc-arena

A [Claude Code](https://claude.com/claude-code) skill that makes many versions of a whole **project** compete, finds what the winner is missing, and fills it from the others.

The bracket arena (`/arena`) makes answers fight pairwise and throws away the loser's good ideas. It is expensive and it is built for answers. ECC Arena is built for projects, and it runs on [Everything-Claude-Code](https://github.com/affaan-m/everything-claude-code): every competitor and every judge works with the ECC agents and skills, which are vendored in this repo under `ecc/`.

## How it works

1. **Compete.** Every competitor is dealt a card: an ECC chain (which ECC agents it works as and which ECC skills it applies, in order), a reasoning mode and a strategy. Each one prepares the **whole project** as a build-ready package: a completeness matrix, PRD, architecture, policies, tasks, tests, ops, CLAUDE.md and README, plus a margin note of what the task did not say and the competitor completed. Not code: the set of files from which Claude Code can build the project in a fresh folder without guessing.
2. **Audit.** One judge per group of ten builds the **union completeness matrix**: every entity x action row and every question any competitor thought of, plus the rows the task implies. For every package it lists the empty cells as gaps, with evidence ("7 of 10 packages define this"), probes it with scenarios traced through its own rules ("a non-member votes": blocked, allowed or undefined), and scores five criteria.
3. **Verdict.** The chief judge merges the unions, picks the winner, and walks the union cell by cell against it. Every empty cell in the winner becomes either a **transplant** from a package that filled it or an **open gap** nobody filled. Nothing is transplanted because it is "better". Something is transplanted because it is missing.
4. **Surgery.** A surgeon assembles the final package: the winner, with every transplant rewritten to fit and every open gap **completed**. The value goes into the project files like any other rule; `notes/COMPLETIONS.md` records what the winner lacked, what came from which package, what was written at assembly, with the reasoning, the arithmetic, the alternatives rejected and the place to change it. It is a margin note, not a project document. Nothing is left for you to decide: a person cannot compute a per-member spend limit better than a model with the whole package in front of it, but a person can disagree with a specific line and change it.
5. **Verify.** A verifier rebuilds the matrix from the task without looking at the package's, checks every claimed cell at the place the package names, probes, and scores. The engine itself scans the package for deferral markers (`DECISION NEEDED`, `TBD`, `EMPTY`, `TODO`, "to be decided") and adds a MAJOR gap per hit, so a package cannot pass with an unmade decision. On failure the surgeon gets the list and one more pass.
6. **Deliver.** The deliverer writes the project folder to continue in Claude Code (with the exact first message to give it), a business plan and a pitch deck, all from the verified package.

Claude orchestrates. It never competes, judges, merges, verifies or delivers.

## How the judge finds what is missing

The method is in [`matrix.md`](skills/ecc-arena/matrix.md). Rows come from the task's nouns and verbs (member, shared wallet, proposal, vote; join, spend, propose, vote, leave). Columns come from the sixteen lenses in [`lenses.md`](skills/ecc-arena/lenses.md) applied to each row (who, when, limit, at-limit, twice, undo, fail, abuse, money, law, see). "Shared wallet x spend" has a "limit" cell whether or not anyone wrote one. "Proposal x vote" has a "who" cell. An empty cell is a gap, and a cell filled by most competitors and empty in one is a gap with evidence.

## Cost

| run | competitors | audit groups | sub-agent calls | bracket arena, same N |
|---|---|---|---|---|
| `--quick` (default) | 10 | 1 | 15 to 17 | 55 |
| `--full` | 100 | 10 | 114 to 116 | 595 |

Each competitor call prepares a whole package, so it is many times the size of a judge call. Competitors, auditors and the deliverer run on Sonnet; the chief judge, surgeon and verifier run on Opus. `--model` overrides all of them. `python3 engine.py plan` prints the numbers before anything is spent.

## Install

**Easiest:** paste this into Claude Code:

> Install this: https://github.com/SheikhSakhi/ecc-arena — clone it and run install.sh

**Manual:**

```bash
git clone https://github.com/SheikhSakhi/ecc-arena.git
cd ecc-arena && sh install.sh
```

Requirements: python3 (3.9 or newer), git. The installer puts the skill in `~/.claude/skills/ecc-arena` with the vendored ECC agents and skills beside it. ECC agents and skills already installed in `~/.claude` take precedence; the vendored copy is the fallback, so nothing of yours is overwritten.

Restart Claude Code after installing.

## Use

```
/ecc-arena ClawBucket: a community bucket-list app with a shared wallet, per-member spend limits and voting on what to do next
/ecc-arena --full <project>
/ecc-arena --agents 30 --seed 7 <project>
```

Everything a run writes lives in `.ecc-arena/<run>/` in the directory you ran it from: every package, every audit, the verdict with the global union, the final package and surgery log per pass, the verification per pass, and `deliverable/` with the project folder, `BUSINESS-PLAN.md` and `PITCH-DECK.md`. Add `.ecc-arena/` to your `.gitignore`.

## Layout

```
skills/ecc-arena/
  SKILL.md         what Claude does as the orchestrator
  engine.py        the command line: plan, init, next, prompts, check, status, winner, card
  ecca/            state, dealing, jobs, prompts, scoring, plan
  deck.json        the cards: ECC chains (agents + skills), reasoning modes, strategies, per-role models
  matrix.md        how the completeness matrix is built and used
  lenses.md        the sixteen lenses, the question generator
  rubric.md        scoring, ranking, transplants, verification
  criteria.json    the five criteria and their weights
  prompts/         one brief template per role
  tests/           python3 -m unittest discover -s skills/ecc-arena/tests
ecc/               vendored Everything-Claude-Code agents, skills, rules and commands (MIT)
```

## License

MIT. The vendored `ecc/` folder is from [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code), also MIT; see `ecc/LICENSE` and `ecc/VENDORED.md`.
