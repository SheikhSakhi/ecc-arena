import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecca import ArenaError  # noqa: E402
from ecca.deal import load_deck, deal, deal_builders, make_groups, agent_ids, combo_count  # noqa: E402


class DealTests(unittest.TestCase):
    def setUp(self):
        self.deck = load_deck()

    def test_deck_has_enough_cards_for_a_full_arena(self):
        self.assertGreaterEqual(combo_count(self.deck), 100)

    def test_every_emphasis_covers_real_lenses(self):
        lens_ids = set("ABCDEFGHIJKLMNOP")
        covered = set()
        for e in self.deck["emphasis"]:
            self.assertTrue(set(e["lenses"]) <= lens_ids, e["id"])
            covered |= set(e["lenses"])
        self.assertEqual(covered, lens_ids, "every lens needs an obsessive owner")

    def test_deal_is_deterministic_for_a_seed(self):
        a = deal(24, 7, self.deck)
        b = deal(24, 7, self.deck)
        self.assertEqual(a, b)

    def test_deal_gives_distinct_cards(self):
        cards = deal(100, 1, self.deck)
        keys = {(c["card"]["chain"]["id"], c["card"]["reasoning"]["id"], c["card"]["strategy"]["id"],
                 c["card"]["emphasis"]["id"]) for c in cards.values()}
        self.assertEqual(len(keys), 100)

    def test_quick_deal_covers_every_emphasis_once(self):
        cards = deal(12, 3, self.deck)
        emphases = [c["card"]["emphasis"]["id"] for c in cards.values()]
        self.assertEqual(sorted(emphases), sorted(e["id"] for e in self.deck["emphasis"]))

    def test_deal_rejects_too_few_or_too_many(self):
        with self.assertRaises(ArenaError):
            deal(1, 0, self.deck)
        with self.assertRaises(ArenaError):
            deal(combo_count(self.deck) + 1, 0, self.deck)

    def test_agent_ids_are_zero_padded(self):
        self.assertEqual(agent_ids(3), ["A001", "A002", "A003"])
        self.assertEqual(agent_ids(1000)[-1], "A1000")

    def test_groups_are_balanced_and_cover_everyone(self):
        ids = agent_ids(36)
        groups = make_groups(ids, 10)
        self.assertEqual(len(groups), 4)
        self.assertEqual(sorted(sum(groups.values(), [])), ids)
        self.assertTrue(all(len(g) == 9 for g in groups.values()))

    def test_small_run_makes_one_group(self):
        self.assertEqual(list(make_groups(agent_ids(5), 10)), ["G01"])

    def test_builders_get_distinct_chains(self):
        builders = deal_builders(3, 5, self.deck)
        self.assertEqual(len({b["card"]["chain"]["id"] for b in builders.values()}), 3)
        with self.assertRaises(ArenaError):
            deal_builders(len(self.deck["chains"]) + 1, 5, self.deck)


if __name__ == "__main__":
    unittest.main()
