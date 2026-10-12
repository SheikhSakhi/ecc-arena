# ecc-arena

A [Claude Code](https://claude.com/claude-code) skill that makes many versions of a whole **project** compete, then assembles the best body from all of them.

The bracket arena (`/arena`) makes a hundred answers fight pairwise and throws away the loser's good ideas. It is expensive and it is built for answers, not projects. This skill is built for projects:

1. **Blueprint.** Every competitor is a different [Everything-Claude-Code](https://github.com/affaan-m/everything-claude-code) agent chain with its own reasoning mode, strategy and an *emphasis* it obsesses over: legal, money and spend limits, voting and governance, identity, data, edge cases, security, operations, logistics, user experience, quality, delivery. Each writes a complete project blueprint.
2. **Audit.** One judge per group of ten scores every blueprint on sixteen lenses, A to Z (`lenses.md`), and names the best part in its group for every lens.
3. **Verdict.** The chief judge picks the winner, then orders transplants: the parts of other blueprints that beat the winner's on a lens. It also lists every gap no blueprint closed.
4. **Surgery.** A surgeon assembles one body: the winner, with every transplant rewritten to fit and every gap filled or marked `DECISION NEEDED`.
5. **Verify.** A hostile verifier audits the merged blueprint lens by lens. If it fails, the surgeon goes back in with the list. Two passes by default.
6. **Build** (optional, `--build`). A few builders build the merged blueprint, a build judge runs every build's install and tests, picks the winner and orders file-level transplants, and a build surgeon assembles the merged project and makes its tests pass.

Claude orchestrates. It never competes, judges, merges or builds.

## Cost

| run | competitors | sub-agent calls | the bracket arena, same N |
|---|---|---|---|
| `--quick` | 12 | 17 to 19 | 67 |
| default | 36 | 43 to 45 | 211 |
| `--full` | 100 | 113 to 115 | 595 |

`--build` adds the builders (default 3) plus two calls. Competitors, auditors and builders run on Sonnet; the chief judge, surgeon and verifier run on Opus. `--model` overrides all of them. `python3 engine.py plan` prints the numbers before anything is spent.

## Install

**Easiest:** paste this into Claude Code:

> Install this: https://github.com/SheikhSakhi/ecc-arena — clone it and run install.sh

**Manual:**

```bash
git clone https://github.com/SheikhSakhi/ecc-arena.git
cd ecc-arena && sh install.sh
```

Requirements: python3 (3.9 or newer), git. The ECC agents are optional: with [everything-claude-code](https://github.com/affaan-m/everything-claude-code) installed in `~/.claude/agents`, each competitor reads its chain's agent definitions and works in those roles; without them it works from the chain's description.

Restart Claude Code after installing.

## Use

```
/ecc-arena a community bucket-list app with a shared wallet, spend limits and voting on what to do next
/ecc-arena --quick <task>
/ecc-arena --full --build --builders 3 <task>
```

| flag | meaning |
|---|---|
| `--agents N` | N competitors. Default 36, three per emphasis. |
| `--quick` | 12 competitors, one per emphasis. |
| `--full` | 100 competitors. |
| `--build` | Build the merged blueprint with `--builders B` builders (default 3) and merge the best build. |
| `--seed S` | Fixes the cards and the groups. |
| `--model M` | One model for every role. |

Everything a run writes lives in `.ecc-arena/<run>/` in the directory you ran it from: every blueprint, every audit, the verdict, the merged blueprint and surgery log per pass, the verification per pass, and the builds. Add `.ecc-arena/` to your `.gitignore`.

## What the judge checks

`lenses.md` is the A-to-Z list: purpose and scope, legal and compliance, money and limits and fraud, governance and voting and disputes, identity and permissions, data lifecycle, core logic and edge cases, security and abuse, reliability and operations, logistics and the real world, integrations, user experience and communication, performance and running cost, testing, delivery and risk, documentation and handover. Every lens has the probing questions and what a gap looks like: a rule without a number, a flow without an owner, a state with no way out.

## Layout

```
skills/ecc-arena/
  SKILL.md         what Claude does as the orchestrator
  engine.py        the command line: plan, init, next, prompts, check, status, winner, card
  ecca/            state, dealing, jobs, prompts, scoring, plan
  deck.json        the cards: ECC chains, reasoning modes, strategies, emphases, per-role models
  lenses.json      lens ids and weights
  lenses.md        the A-to-Z audit the judges read
  rubric.md        how scores, ranking, transplants and verification work
  prompts/         one brief template per role
  tests/           unittest suite: python3 -m unittest discover -s skills/ecc-arena/tests
```

## License

MIT.
