"""Walks a fake run through every phase with the real engine, writing the outputs a sub-agent would."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)

from ecca import PACKAGE_REQUIRED  # noqa: E402
from ecca import state as st  # noqa: E402
from ecca.jobs import next_action, phase_jobs  # noqa: E402
from ecca.prompts import write_prompts  # noqa: E402
from ecca.scoring import load_criteria  # noqa: E402

CRITERIA = load_criteria()


def engine(cwd, *args):
    out = subprocess.run([sys.executable, os.path.join(SKILL, "engine.py")] + list(args), cwd=cwd,
                         capture_output=True, text=True)
    return out.returncode, out.stdout + out.stderr


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def write_json(path, doc):
    write(path, json.dumps(doc))


def scores(v):
    return {c: v for c in CRITERIA["ids"]}


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix="ecca-")
        write(os.path.join(self.cwd, "task.md"), "Build ClawBucket: a community bucket-list app with a shared wallet and voting.\n")
        code, out = engine(self.cwd, "init", "--task-file", "task.md", "--agents", "4", "--group-size", "2", "--seed", "11")
        self.assertEqual(code, 0, out)
        self.state = st.load_state(st.latest_run_dir(self.cwd))
        self.d = self.state["dir"]

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)

    def finish_packages(self):
        for aid in self.state["agents"]:
            for name in PACKAGE_REQUIRED:
                write(os.path.join(st.package_dir(self.d, aid), name), "# %s of %s\n" % (name, aid))

    def finish_audits(self, totals):
        for gid, ids in self.state["groups"].items():
            doc = {"group": gid,
                   "union": [{"id": "U1", "row": "wallet x spend", "question": "per-member limit", "filled_by": ids[:1]},
                             {"id": "U2", "row": "proposal x vote", "question": "eligibility", "filled_by": []}],
                   "entries": {a: {"scores": scores(totals[a]), "fatal": False, "gaps": [], "probes": []} for a in ids}}
            write_json(st.audit_out(self.d, gid), doc)

    def finish_final(self, v):
        for name in PACKAGE_REQUIRED:
            write(os.path.join(st.final_dir(self.d, v), name), "# final v%d %s\n" % (v, name))
        write(st.surgery_log_out(self.d, v), "TRANSPLANT 1: ...\n")

    def test_plan_is_cheaper_than_the_bracket(self):
        code, out = engine(self.cwd, "plan", "--full")
        self.assertEqual(code, 0, out)
        self.assertIn("bracket arena costs 595", out)
        self.assertIn("114..116", out)

    def test_partial_package_counts_as_missing(self):
        write(os.path.join(st.package_dir(self.d, "A001"), "MATRIX.md"), "# only the matrix\n")
        phase, left, _, _ = next_action(self.state)
        self.assertEqual(phase, "compete")
        self.assertIn("A001.compete", [j["id"] for j in left])

    def test_run_walks_every_phase_in_order(self):
        phase, left, _, _ = next_action(self.state)
        self.assertEqual((phase, len(left)), ("compete", 4))
        self.finish_packages()
        phase, left, _, _ = next_action(self.state)
        self.assertEqual((phase, len(left)), ("audit", 2))
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        phase, jobs, _, _ = next_action(self.state)
        self.assertEqual(phase, "verdict")
        write_prompts(self.state, "verdict")
        short = st.read_json(st.shortlist_path(self.d))
        self.assertEqual(short["shortlist"][0]["id"], "A002")
        self.assertEqual(len(short["union"]), 2)
        with open(jobs[0]["prompt"], encoding="utf-8") as fh:
            brief = fh.read()
        self.assertIn("A002 (group G02 rank 1", brief)
        self.assertNotIn("{{", brief)
        write_json(st.verdict_out(self.d), {"winner": "A002", "reason": "fills most cells", "union": short["union"],
                                            "transplants": [{"union_id": "U1", "from": "A001", "file": "POLICIES.md",
                                                             "section": "Spend limits", "into": "POLICIES.md", "why": "winner has no limit"}],
                                            "open_gaps": [{"union_id": "U2", "row": "proposal x vote", "question": "eligibility",
                                                           "severity": "MAJOR", "what": "nobody defines who may vote"}]})
        phase, jobs, _, _ = next_action(self.state)
        self.assertEqual((phase, jobs[0]["version"]), ("surgery", 1))
        write_prompts(self.state, "surgery")
        self.finish_final(1)
        phase, jobs, _, _ = next_action(self.state)
        self.assertEqual((phase, jobs[0]["version"]), ("verify", 1))
        write_prompts(self.state, "verify")
        write_json(st.verify_out(self.d, 1), {"scores": dict(scores(8), completeness=5),
                                              "probes": [{"scenario": "non-member votes", "result": "UNDEFINED"}]})
        phase, jobs, _, note = next_action(self.state)
        self.assertEqual((phase, jobs[0]["version"]), ("surgery", 2))
        self.assertIn("undefined probes", note)
        write_prompts(self.state, "surgery")
        with open(jobs[0]["prompt"], encoding="utf-8") as fh:
            self.assertIn("pass 2", fh.read())
        self.finish_final(2)
        write_json(st.verify_out(self.d, 2), {"scores": scores(8), "summary": "ready"})
        phase, jobs, _, note = next_action(self.state)
        self.assertEqual(phase, "deliver")
        self.assertIn("v2 passed", note)
        write_prompts(self.state, "deliver")
        with open(jobs[0]["prompt"], encoding="utf-8") as fh:
            self.assertIn("investor-materials", fh.read())
        write(st.business_plan_out(self.d), "# plan\n")
        write(st.pitch_deck_out(self.d), "# deck\n")
        write(st.delivered_readme(self.d), "# project\n")
        phase, _, _, _ = next_action(self.state)
        self.assertEqual(phase, "done")
        code, out = engine(self.cwd, "winner")
        self.assertEqual(code, 0, out)
        self.assertIn("winner: A002", out)
        self.assertIn("transplant U1 from A001", out)
        self.assertIn("notes/COMPLETIONS.md", out)
        self.assertIn("pitch deck", out)

    def test_a_deferred_decision_in_the_final_package_fails_verification(self):
        self.finish_packages()
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        write_json(st.verdict_out(self.d), {"winner": "A002", "reason": "", "transplants": [], "open_gaps": []})
        self.finish_final(1)
        write(os.path.join(st.final_dir(self.d, 1), "POLICIES.md"),
              "# Policies\n\nDaily spend limit per member: [DECISION NEEDED: how much?]\nQuorum: tbd\n")
        write_json(st.verify_out(self.d, 1), {"scores": scores(9), "summary": "the judge says fine"})
        phase, jobs, _, note = next_action(self.state)
        self.assertEqual((phase, jobs[0]["version"]), ("surgery", 2))
        self.assertIn("2 unmade decisions", note)
        write_prompts(self.state, "surgery")
        code, out = engine(self.cwd, "status")
        self.assertIn("FAIL", out)
        self.finish_final(2)
        write_json(st.verify_out(self.d, 2), {"scores": scores(9)})
        phase, _, _, note = next_action(self.state)
        self.assertEqual(phase, "deliver")
        self.assertIn("v2 passed", note)

    def test_last_allowed_pass_falls_through_to_deliver_with_open_gaps(self):
        self.finish_packages()
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        write_json(st.verdict_out(self.d), {"winner": "A002", "reason": "", "transplants": [], "open_gaps": []})
        for v in (1, 2):
            self.finish_final(v)
            write_json(st.verify_out(self.d, v), {"scores": scores(5)})
        phase, _, _, note = next_action(self.state)
        self.assertEqual(phase, "deliver")
        self.assertIn("did NOT pass", note)

    def test_broken_audit_json_is_reported_not_swallowed(self):
        self.finish_packages()
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        write(st.audit_out(self.d, "G01"), "not json at all")
        code, out = engine(self.cwd, "next")
        self.assertEqual(code, 1)
        self.assertIn("G01.json is not JSON", out)

    def test_every_phase_renders_without_unfilled_placeholders(self):
        self.finish_packages()
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        write_json(st.verdict_out(self.d), {"winner": "A002", "reason": "", "transplants": [
            {"union_id": "U1", "from": "A003", "file": "POLICIES.md", "section": "Voting", "into": "POLICIES.md", "why": "quorum"}],
            "open_gaps": []})
        self.finish_final(1)
        for phase in ("compete", "audit", "verdict", "surgery", "verify", "deliver"):
            for job in write_prompts(self.state, phase):
                with open(job["prompt"], encoding="utf-8") as fh:
                    text = fh.read()
                self.assertNotIn("{{", text, "%s left a placeholder" % job["id"])
                self.assertIn("ClawBucket", text)
        with open(st.prompt_path(self.d, "compete", "A001.compete"), encoding="utf-8") as fh:
            self.assertIn("SKILL.md and apply it", fh.read())

    def test_models_come_from_deck_unless_overridden(self):
        self.assertEqual(phase_jobs(self.state, "compete")[0]["model"], "sonnet")
        self.assertEqual(phase_jobs(self.state, "verdict")[0]["model"], "opus")
        self.state["model_override"] = "haiku"
        self.assertEqual(phase_jobs(self.state, "verdict")[0]["model"], "haiku")


if __name__ == "__main__":
    unittest.main()
