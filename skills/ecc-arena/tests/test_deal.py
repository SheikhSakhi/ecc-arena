import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecca import ArenaError  # noqa: E402
from ecca.deal import load_deck, deal, make_groups, agent_ids, combo_count, find_skill, find_agent, skill_lines  # noqa: E402


class DealTests(unittest.TestCase):
    def setUp(self):
        self.deck = load_deck()

    def test_deck_has_enough_cards_for_a_full_arena(self):
        self.assertGreaterEqual(combo_count(self.deck), 100)

    def test_every_chain_names_agents_and_skills(self):
        for chain in self.deck["chains"]:
            self.assertTrue(chain["agents"], chain["id"])
            self.assertTrue(chain["skills"], chain["id"])

    def test_deal_is_deterministic_for_a_seed(self):
        self.assertEqual(deal(24, 7, self.deck), deal(24, 7, self.deck))

    def test_deal_gives_distinct_cards(self):
        cards = deal(100, 1, self.deck)
        keys = {(c["card"]["chain"]["id"], c["card"]["reasoning"]["id"], c["card"]["strategy"]["id"]) for c in cards.values()}
        self.assertEqual(len(keys), 100)

    def test_quick_deal_covers_ten_different_chains(self):
        cards = deal(10, 3, self.deck)
        self.assertEqual(len({c["card"]["chain"]["id"] for c in cards.values()}), 10)

    def test_deal_rejects_too_few_or_too_many(self):
        with self.assertRaises(ArenaError):
            deal(1, 0, self.deck)
        with self.assertRaises(ArenaError):
            deal(combo_count(self.deck) + 1, 0, self.deck)

    def test_agent_ids_are_zero_padded(self):
        self.assertEqual(agent_ids(3), ["A001", "A002", "A003"])

    def test_groups_are_balanced_and_cover_everyone(self):
        ids = agent_ids(100)
        groups = make_groups(ids, 10)
        self.assertEqual(len(groups), 10)
        self.assertEqual(sorted(sum(groups.values(), [])), ids)
        self.assertTrue(all(len(g) == 10 for g in groups.values()))

    def test_ten_competitors_make_one_group(self):
        self.assertEqual(list(make_groups(agent_ids(10), 10)), ["G01"])

    def test_vendored_ecc_skills_and_agents_resolve(self):
        for chain in self.deck["chains"]:
            for name in chain["skills"]:
                self.assertIsNotNone(find_skill(name), "skill %s is not vendored or installed" % name)
            for name in chain["agents"]:
                self.assertIsNotNone(find_agent(name), "agent %s is not vendored or installed" % name)
        for name in self.deck["deliver_skills"]:
            self.assertIsNotNone(find_skill(name), name)

    def test_missing_skill_degrades_to_a_note(self):
        self.assertIn("not installed", skill_lines(["no-such-skill-xyz"]))


if __name__ == "__main__":
    unittest.main()
