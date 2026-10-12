"""Deal the cards. Chains go round-robin so every ECC discipline is in the room; reasoning and strategy
are drawn at random with no repeated full card. Also resolves where ECC agents and skills live."""
import json
import os
import random

from . import ArenaError, SKILL_DIR

DECK_PATH = os.path.join(SKILL_DIR, "deck.json")
MAX_DRAWS = 10000


def load_deck(path=DECK_PATH):
    with open(path, encoding="utf-8") as fh:
        deck = json.load(fh)
    for key in ("chains", "reasoning", "strategies", "models", "deliver_skills"):
        if key not in deck:
            raise ArenaError("deck.json is missing '%s'" % key)
    return deck


def combo_count(deck):
    return len(deck["chains"]) * len(deck["reasoning"]) * len(deck["strategies"])


def agent_ids(n):
    width = max(3, len(str(n)))
    return ["A" + str(i).zfill(width) for i in range(1, n + 1)]


def _card_key(card):
    return (card["chain"]["id"], card["reasoning"]["id"], card["strategy"]["id"])


def deal(n, seed, deck):
    """n distinct cards keyed by agent id. Deterministic for a seed."""
    if n < 2:
        raise ArenaError("need at least 2 competitors")
    if n > combo_count(deck):
        raise ArenaError("only %d distinct cards exist, cannot deal %d" % (combo_count(deck), n))
    rng = random.Random(seed)
    chains = deck["chains"]
    order = list(range(len(chains)))
    rng.shuffle(order)
    seen, cards = set(), {}
    for i, aid in enumerate(agent_ids(n)):
        card = _draw(rng, deck, chains[order[i % len(chains)]], seen)
        seen.add(_card_key(card))
        cards[aid] = {"card": card}
    return cards


def _draw(rng, deck, chain, seen):
    for _ in range(MAX_DRAWS):
        card = {"chain": chain, "reasoning": rng.choice(deck["reasoning"]), "strategy": rng.choice(deck["strategies"])}
        if _card_key(card) not in seen:
            return card
    raise ArenaError("could not find an unused card after %d draws" % MAX_DRAWS)


def make_groups(ids, group_size):
    """Audit groups of about group_size, keyed G01, G02 ..."""
    if group_size < 2:
        raise ArenaError("group size must be at least 2")
    count = max(1, -(-len(ids) // group_size))
    return {"G" + str(k + 1).zfill(2): ids[k::count] for k in range(count)}


def claude_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))


def ecc_roots():
    """Where ECC agents and skills may live, in order: the user's Claude config, this skill's vendored
    copy, and the repository's vendored copy when running from a checkout."""
    return [claude_dir(), os.path.join(SKILL_DIR, "ecc"), os.path.join(os.path.dirname(os.path.dirname(SKILL_DIR)), "ecc")]


def find_agent(name):
    for root in ecc_roots():
        path = os.path.join(root, "agents", name + ".md")
        if os.path.isfile(path):
            return path
    return None


def find_skill(name):
    for root in ecc_roots():
        path = os.path.join(root, "skills", name, "SKILL.md")
        if os.path.isfile(path):
            return path
    return None


def agent_lines(names):
    lines = []
    for name in names:
        path = find_agent(name)
        if path:
            lines.append("- %s: read %s and work in that role." % (name, path))
        else:
            lines.append("- %s: that ECC agent is not installed here; work from its name and the chain's description." % name)
    return "\n".join(lines)


def skill_lines(names):
    lines = []
    for name in names:
        path = find_skill(name)
        if path:
            lines.append("- %s: read %s and apply it." % (name, path))
        else:
            lines.append("- %s: that ECC skill is not installed here; apply what its name implies." % name)
    return "\n".join(lines)
