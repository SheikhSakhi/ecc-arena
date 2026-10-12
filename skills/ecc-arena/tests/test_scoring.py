import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecca import ArenaError  # noqa: E402
from ecca.scoring import (load_lenses, lens_total, validate_audit, rank_all, shortlist, best_parts_index,  # noqa: E402
                          validate_verdict, validate_verify, validate_build_verdict)

LENSES = load_lenses()


def scores(value):
    return {l: value for l in LENSES["ids"]}


def audit_doc(gid, ids, totals, fatal=()):
    return {"group": gid, "entries": {a: {"scores": scores(t), "fatal": a in fatal, "gaps": []} for a, t in zip(ids, totals)},
            "best_parts": {"C": {"entry": ids[0], "section": "Spend limits", "why": "numbers for every cap"}}}


class LensTests(unittest.TestCase):
    def test_weights_sum_to_one_hundred_and_total_scales(self):
        self.assertEqual(lens_total(scores(10), LENSES, "t"), 100.0)
        self.assertEqual(lens_total(scores(0), LENSES, "t"), 0.0)
        self.assertEqual(lens_total(scores(7), LENSES, "t"), 70.0)

    def test_missing_lens_is_an_error(self):
        s = scores(8)
        del s["C"]
        with self.assertRaises(ArenaError):
            lens_total(s, LENSES, "t")

    def test_out_of_range_score_is_an_error(self):
        s = scores(8)
        s["A"] = 11
        with self.assertRaises(ArenaError):
            lens_total(s, LENSES, "t")


class AuditTests(unittest.TestCase):
    def test_audit_is_normalised_with_totals(self):
        out = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 6]), "G01", ["A001", "A002"], LENSES)
        self.assertEqual(out["entries"]["A001"]["total"], 90.0)
        self.assertEqual(out["best_parts"]["C"]["entry"], "A001")

    def test_audit_must_score_every_expected_entry(self):
        with self.assertRaises(ArenaError):
            validate_audit(audit_doc("G01", ["A001"], [9]), "G01", ["A001", "A002"], LENSES)

    def test_bad_gap_severity_is_rejected(self):
        doc = audit_doc("G01", ["A001", "A002"], [9, 6])
        doc["entries"]["A001"]["gaps"] = [{"lens": "C", "severity": "HUGE", "what": "x"}]
        with self.assertRaises(ArenaError):
            validate_audit(doc, "G01", ["A001", "A002"], LENSES)

    def test_ranking_uses_group_rank_before_raw_total(self):
        g1 = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 8]), "G01", ["A001", "A002"], LENSES)
        g2 = validate_audit(audit_doc("G02", ["A003", "A004"], [6, 5]), "G02", ["A003", "A004"], LENSES)
        order = [r["id"] for r in rank_all([g1, g2])]
        self.assertEqual(order, ["A001", "A003", "A002", "A004"])

    def test_fatal_entries_rank_last_and_are_kept_off_the_shortlist(self):
        g1 = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 8], fatal=("A001",)), "G01", ["A001", "A002"], LENSES)
        ranking = rank_all([g1])
        self.assertEqual(ranking[-1]["id"], "A001")
        self.assertEqual([r["id"] for r in shortlist(ranking, 5)], ["A002"])

    def test_best_parts_index_collects_across_groups(self):
        g1 = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 8]), "G01", ["A001", "A002"], LENSES)
        g2 = validate_audit(audit_doc("G02", ["A003", "A004"], [6, 5]), "G02", ["A003", "A004"], LENSES)
        self.assertEqual([p["entry"] for p in best_parts_index([g1, g2])["C"]], ["A001", "A003"])


class VerdictTests(unittest.TestCase):
    def test_verdict_requires_known_winner_and_donor(self):
        with self.assertRaises(ArenaError):
            validate_verdict({"winner": "A999"}, ["A001"])
        with self.assertRaises(ArenaError):
            validate_verdict({"winner": "A001", "transplants": [{"from": "A001"}]}, ["A001", "A002"])
        out = validate_verdict({"winner": "A001", "transplants": [{"from": "A002", "lens": "C"}]}, ["A001", "A002"])
        self.assertEqual(out["transplants"][0]["from"], "A002")

    def test_verify_passes_only_when_clean(self):
        clean = validate_verify({"scores": scores(8), "gaps": []}, LENSES)
        self.assertTrue(clean["pass"])
        low = validate_verify({"scores": dict(scores(8), C=5), "gaps": []}, LENSES)
        self.assertFalse(low["pass"])
        self.assertEqual(low["low_lenses"], ["C"])
        blocked = validate_verify({"scores": scores(8), "gaps": [{"lens": "D", "severity": "MAJOR", "what": "no tie-break"}]}, LENSES)
        self.assertFalse(blocked["pass"])
        minor = validate_verify({"scores": scores(8), "gaps": [{"lens": "D", "severity": "MINOR", "what": "typo"}]}, LENSES)
        self.assertTrue(minor["pass"])

    def test_verify_ignores_the_judges_own_pass_flag(self):
        out = validate_verify({"scores": scores(3), "gaps": [], "pass": True}, LENSES)
        self.assertFalse(out["pass"])

    def test_build_verdict_winner_must_install_and_pass_tests(self):
        with self.assertRaises(ArenaError):
            validate_build_verdict({"winner": "B1", "hard_checks": {"B1": {"installs": True, "tests_pass": False}, "B2": {}}}, ["B1", "B2"])
        out = validate_build_verdict({"winner": "B1", "hard_checks": {"B1": {"installs": True, "tests_pass": True}, "B2": {}},
                                      "transplants": [{"from": "B2", "path": "src/limits.py"}]}, ["B1", "B2"])
        self.assertEqual(out["transplants"][0]["path"], "src/limits.py")


if __name__ == "__main__":
    unittest.main()
