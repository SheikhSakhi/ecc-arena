"""Deal the cards. Emphasis and chain go round-robin so every lens has an obsessive owner; reasoning and
strategy are drawn at random with no repeated full card."""
import json
import os
import random

from . import ArenaError, SKILL_DIR

DECK_PATH = os.path.join(SKILL_DIR, "deck.json")
MAX_DRAWS = 10000


def load_deck(path=DECK_PATH):
    with open(path, encoding="utf-8") as fh:
        deck = json.load(fh)
    for key in ("chains", "reasoning", "strategies", "emphasis", "models"):
        if key not in deck:
            raise ArenaError("deck.json is missing '%s'" % key)
    return deck


def combo_count(deck):
    return len(deck["chains"]) * len(deck["reasoning"]) * len(deck["strategies"]) * len(deck["emphasis"])


def agent_ids(n):
    width = max(3, len(str(n)))
    return ["A" + str(i).zfill(width) for i in range(1, n + 1)]


def builder_ids(n):
    return ["B" + str(i) for i in range(1, n + 1)]


def _card_key(card):
    return (card["chain"]["id"], card["reasoning"]["id"], card["strategy"]["id"], card["emphasis"]["id"])


def deal(n, seed, deck):
    """n distinct cards, keyed by agent id. Deterministic for a seed."""
    if n < 2:
        raise ArenaError("need at least 2 competitors")
    if n > combo_count(deck):
        raise ArenaError("only %d distinct cards exist, cannot deal %d" % (combo_count(deck), n))
    rng = random.Random(seed)
    chains, emphases = deck["chains"], deck["emphasis"]
    chain_order = list(range(len(chains)))
    emphasis_order = list(range(len(emphases)))
    rng.shuffle(chain_order)
    rng.shuffle(emphasis_order)
    seen, cards = set(), {}
    for i, aid in enumerate(agent_ids(n)):
        card = _draw(rng, deck, chains[chain_order[i % len(chains)]], emphases[emphasis_order[i % len(emphases)]], seen)
        seen.add(_card_key(card))
        cards[aid] = {"card": card}
    return cards


def _draw(rng, deck, chain, emphasis, seen):
    for _ in range(MAX_DRAWS):
        card = {"chain": chain, "reasoning": rng.choice(deck["reasoning"]),
                "strategy": rng.choice(deck["strategies"]), "emphasis": emphasis}
        if _card_key(card) not in seen:
            return card
    raise ArenaError("could not find an unused card after %d draws" % MAX_DRAWS)


def deal_builders(n, seed, deck):
    """Builders differ by chain and strategy only; they all build the same merged blueprint."""
    if n < 1:
        raise ArenaError("need at least 1 builder")
    if n > len(deck["chains"]):
        raise ArenaError("only %d chains exist, cannot deal %d builders" % (len(deck["chains"]), n))
    rng = random.Random(seed + 1)
    chains = rng.sample(deck["chains"], n)
    return {bid: {"card": {"chain": chains[i], "strategy": rng.choice(deck["strategies"])}}
            for i, bid in enumerate(builder_ids(n))}


def make_groups(ids, group_size):
    """Audit groups of about group_size, keyed G01, G02 ... Each group gets at least 2 entries."""
    if group_size < 2:
        raise ArenaError("group size must be at least 2")
    count = max(1, -(-len(ids) // group_size))
    groups = {}
    for k in range(count):
        gid = "G" + str(k + 1).zfill(2)
        groups[gid] = ids[k::count]
    return groups


def ecc_agents_dir():
    return os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")), "agents")


def chain_agent_lines(chain):
    """One line per ECC agent in the chain, with the path to its definition when it is installed."""
    lines = []
    for name in chain["agents"]:
        path = os.path.join(ecc_agents_dir(), name + ".md")
        if os.path.isfile(path):
            lines.append("- %s: read %s and work in that role." % (name, path))
        else:
            lines.append("- %s: that ECC agent is not installed here; work from its name and the chain's description." % name)
    return "\n".join(lines)
