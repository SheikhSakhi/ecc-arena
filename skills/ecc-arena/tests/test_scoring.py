import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ecca import ArenaError  # noqa: E402
from ecca.scoring import (load_criteria, total, validate_audit, rank_all, shortlist, merge_unions,  # noqa: E402
                          validate_verdict, validate_verify)

CRITERIA = load_criteria()


def scores(value):
    return {c: value for c in CRITERIA["ids"]}


def audit_doc(gid, ids, totals, fatal=(), union=None):
    return {"group": gid,
            "union": union or [{"id": "U1", "row": "wallet x spend", "question": "per-member limit", "filled_by": ids[:1]}],
            "entries": {a: {"scores": scores(t), "fatal": a in fatal, "gaps": [], "probes": []} for a, t in zip(ids, totals)}}


class CriteriaTests(unittest.TestCase):
    def test_weights_sum_to_one_hundred_and_total_scales(self):
        self.assertEqual(total(scores(10), CRITERIA, "t"), 100.0)
        self.assertEqual(total(scores(0), CRITERIA, "t"), 0.0)
        self.assertEqual(total(scores(7), CRITERIA, "t"), 70.0)

    def test_missing_or_out_of_range_score_is_an_error(self):
        s = scores(8)
        del s["coherence"]
        with self.assertRaises(ArenaError):
            total(s, CRITERIA, "t")
        with self.assertRaises(ArenaError):
            total(dict(scores(8), completeness=11), CRITERIA, "t")


class AuditTests(unittest.TestCase):
    def test_audit_is_normalised_with_totals_and_union(self):
        out = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 6]), "G01", ["A001", "A002"], CRITERIA)
        self.assertEqual(out["entries"]["A001"]["total"], 90.0)
        self.assertEqual(out["union"][0]["filled_by"], ["A001"])

    def test_audit_must_score_every_expected_entry(self):
        with self.assertRaises(ArenaError):
            validate_audit(audit_doc("G01", ["A001"], [9]), "G01", ["A001", "A002"], CRITERIA)

    def test_audit_without_union_is_rejected(self):
        doc = audit_doc("G01", ["A001", "A002"], [9, 6])
        doc["union"] = []
        with self.assertRaises(ArenaError):
            validate_audit(doc, "G01", ["A001", "A002"], CRITERIA)

    def test_bad_probe_result_is_rejected(self):
        doc = audit_doc("G01", ["A001", "A002"], [9, 6])
        doc["entries"]["A001"]["probes"] = [{"scenario": "x", "result": "MAYBE"}]
        with self.assertRaises(ArenaError):
            validate_audit(doc, "G01", ["A001", "A002"], CRITERIA)

    def test_ranking_uses_group_rank_before_raw_total(self):
        g1 = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 8]), "G01", ["A001", "A002"], CRITERIA)
        g2 = validate_audit(audit_doc("G02", ["A003", "A004"], [6, 5]), "G02", ["A003", "A004"], CRITERIA)
        self.assertEqual([r["id"] for r in rank_all([g1, g2])], ["A001", "A003", "A002", "A004"])

    def test_fatal_entries_rank_last_and_leave_the_shortlist(self):
        g1 = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 8], fatal=("A001",)), "G01", ["A001", "A002"], CRITERIA)
        ranking = rank_all([g1])
        self.assertEqual(ranking[-1]["id"], "A001")
        self.assertEqual([r["id"] for r in shortlist(ranking, 5)], ["A002"])

    def test_unions_merge_on_row_and_question_with_prevalence(self):
        u1 = [{"id": "U1", "row": "Wallet x spend", "question": "per-member limit", "filled_by": ["A001"]}]
        u2 = [{"id": "U3", "row": "wallet x spend", "question": "Per-member limit", "filled_by": ["A003", "A004"]},
              {"id": "U4", "row": "proposal x vote", "question": "eligibility", "filled_by": []}]
        g1 = validate_audit(audit_doc("G01", ["A001", "A002"], [9, 8], union=u1), "G01", ["A001", "A002"], CRITERIA)
        g2 = validate_audit(audit_doc("G02", ["A003", "A004"], [6, 5], union=u2), "G02", ["A003", "A004"], CRITERIA)
        merged = merge_unions([g1, g2])
        self.assertEqual(len(merged), 2)
        spend = [c for c in merged if c["question"] == "per-member limit"][0]
        self.assertEqual(spend["prevalence"], 3)
        self.assertEqual(spend["group_ids"], ["G01:U1", "G02:U3"])


class VerdictTests(unittest.TestCase):
    def test_verdict_requires_known_winner_donor_and_cell(self):
        with self.assertRaises(ArenaError):
            validate_verdict({"winner": "A999"}, ["A001"])
        with self.assertRaises(ArenaError):
            validate_verdict({"winner": "A001", "transplants": [{"from": "A001", "union_id": "U1"}]}, ["A001", "A002"])
        with self.assertRaises(ArenaError):
            validate_verdict({"winner": "A001", "transplants": [{"from": "A002"}]}, ["A001", "A002"])
        out = validate_verdict({"winner": "A001", "transplants": [{"from": "A002", "union_id": "U1"}]}, ["A001", "A002"])
        self.assertEqual(out["transplants"][0]["union_id"], "U1")

    def test_verify_passes_only_when_clean(self):
        self.assertTrue(validate_verify({"scores": scores(8)}, CRITERIA)["pass"])
        low = validate_verify({"scores": dict(scores(8), completeness=5)}, CRITERIA)
        self.assertEqual((low["pass"], low["low"]), (False, ["completeness"]))
        self.assertFalse(validate_verify({"scores": scores(8), "gaps": [{"severity": "MAJOR"}]}, CRITERIA)["pass"])
        self.assertTrue(validate_verify({"scores": scores(8), "gaps": [{"severity": "MINOR"}]}, CRITERIA)["pass"])
        self.assertFalse(validate_verify({"scores": scores(8), "probes": [{"scenario": "x", "result": "UNDEFINED"}]}, CRITERIA)["pass"])
        self.assertFalse(validate_verify({"scores": scores(8), "contradictions": ["a vs b"]}, CRITERIA)["pass"])

    def test_verify_ignores_the_judges_own_pass_flag(self):
        self.assertFalse(validate_verify({"scores": scores(3), "pass": True}, CRITERIA)["pass"])


if __name__ == "__main__":
    unittest.main()
