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

from ecca import state as st  # noqa: E402
from ecca.jobs import next_action, phase_jobs  # noqa: E402
from ecca.prompts import write_prompts  # noqa: E402
from ecca.scoring import load_lenses  # noqa: E402

LENSES = load_lenses()


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
    return {l: v for l in LENSES["ids"]}


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix="ecca-")
        write(os.path.join(self.cwd, "task.md"), "Build a community bucket-list app with a shared wallet and voting.\n")
        code, out = engine(self.cwd, "init", "--task-file", "task.md", "--agents", "4", "--group-size", "2",
                           "--seed", "11", "--build", "--builders", "2")
        self.assertEqual(code, 0, out)
        self.state = st.load_state(st.latest_run_dir(self.cwd))
        self.d = self.state["dir"]

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)

    def finish_blueprints(self):
        for aid in self.state["agents"]:
            write(st.blueprint_out(self.d, aid), "# Blueprint %s\n\n## 3. Money\nCap 50 per day.\n" % aid)

    def finish_audits(self, totals):
        for gid, ids in self.state["groups"].items():
            doc = {"group": gid, "entries": {a: {"scores": scores(totals[a]), "fatal": False, "gaps": []} for a in ids},
                   "best_parts": {"C": {"entry": ids[0], "section": "Money", "why": "caps"}}}
            write_json(st.audit_out(self.d, gid), doc)

    def test_plan_prints_cheaper_than_bracket(self):
        code, out = engine(self.cwd, "plan", "--agents", "36")
        self.assertEqual(code, 0, out)
        self.assertIn("bracket arena costs 211", out)

    def test_run_walks_every_phase_in_order(self):
        phase, left, _, _ = next_action(self.state)
        self.assertEqual((phase, len(left)), ("blueprint", 4))
        self.finish_blueprints()
        phase, left, _, _ = next_action(self.state)
        self.assertEqual((phase, len(left)), ("audit", 2))
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        phase, jobs, _, _ = next_action(self.state)
        self.assertEqual(phase, "verdict")
        write_prompts(self.state, "verdict")
        short = st.read_json(st.shortlist_path(self.d))
        self.assertEqual(short["shortlist"][0]["id"], "A002")
        with open(jobs[0]["prompt"], encoding="utf-8") as fh:
            brief = fh.read()
        self.assertIn("A002 (group G02 rank 1", brief)
        self.assertNotIn("{{", brief)
        write_json(st.verdict_out(self.d), {"winner": "A002", "reason": "best", "transplants": [
            {"from": "A001", "lens": "C", "section": "Money", "into": "3. Money", "why": "caps"}], "open_gaps": []})
        phase, jobs, _, note = next_action(self.state)
        self.assertEqual((phase, jobs[0]["version"]), ("surgery", 1))
        write_prompts(self.state, "surgery")
        write(st.merged_out(self.d, 1), "# Merged v1\n")
        write(st.surgery_log_out(self.d, 1), "TRANSPLANT 1: ...\n")
        phase, jobs, _, _ = next_action(self.state)
        self.assertEqual((phase, jobs[0]["version"]), ("verify", 1))
        write_prompts(self.state, "verify")
        write_json(st.verify_out(self.d, 1), {"scores": dict(scores(8), D=4), "gaps": [
            {"lens": "D", "severity": "MAJOR", "what": "no tie-break", "fix": "add one"}]})
        phase, jobs, _, note = next_action(self.state)
        self.assertEqual((phase, jobs[0]["version"]), ("surgery", 2))
        self.assertIn("low lenses D", note)
        write_prompts(self.state, "surgery")
        with open(jobs[0]["prompt"], encoding="utf-8") as fh:
            self.assertIn("pass 2", fh.read())
        write(st.merged_out(self.d, 2), "# Merged v2\n")
        write(st.surgery_log_out(self.d, 2), "GAP 1 ...\n")
        write_json(st.verify_out(self.d, 2), {"scores": scores(8), "gaps": []})
        phase, left, _, note = next_action(self.state)
        self.assertEqual((phase, len(left)), ("build", 2))
        self.assertIn("v2 passed", note)
        write_prompts(self.state, "build")
        for bid in self.state["builders"]:
            write(st.build_report_out(self.d, bid), "# Build report\n")
        phase, _, _, _ = next_action(self.state)
        self.assertEqual(phase, "build_judge")
        write_prompts(self.state, "build_judge")
        write_json(st.build_verdict_out(self.d), {"winner": "B1", "reason": "tests pass", "hard_checks": {
            "B1": {"installs": True, "tests_pass": True}, "B2": {"installs": True, "tests_pass": False}},
            "transplants": [{"from": "B2", "path": "src/votes.py", "why": "has quorum"}]})
        phase, _, _, _ = next_action(self.state)
        self.assertEqual(phase, "build_surgery")
        write_prompts(self.state, "build_surgery")
        write(st.build_report_merged_out(self.d), "# Merged build report\n")
        phase, _, _, _ = next_action(self.state)
        self.assertEqual(phase, "done")
        code, out = engine(self.cwd, "winner")
        self.assertEqual(code, 0, out)
        self.assertIn("winner: A002", out)
        self.assertIn("build winner: B1", out)
        self.assertIn("src/votes.py", out)

    def test_last_allowed_pass_falls_through_with_open_gaps(self):
        self.finish_blueprints()
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        write_json(st.verdict_out(self.d), {"winner": "A002", "reason": "", "transplants": [], "open_gaps": []})
        for v in (1, 2):
            write(st.merged_out(self.d, v), "# v%d\n" % v)
            write(st.surgery_log_out(self.d, v), "-\n")
            write_json(st.verify_out(self.d, v), {"scores": scores(5), "gaps": []})
        phase, _, _, note = next_action(self.state)
        self.assertEqual(phase, "build")
        self.assertIn("did NOT pass", note)

    def test_broken_audit_json_is_reported_not_swallowed(self):
        self.finish_blueprints()
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        write(st.audit_out(self.d, "G01"), "not json at all")
        code, out = engine(self.cwd, "next")
        self.assertEqual(code, 1)
        self.assertIn("G01.json is not JSON", out)

    def test_every_phase_renders_without_unfilled_placeholders(self):
        self.finish_blueprints()
        self.finish_audits({"A001": 6, "A002": 9, "A003": 7, "A004": 5})
        write_json(st.verdict_out(self.d), {"winner": "A002", "reason": "", "transplants": [
            {"from": "A003", "lens": "D", "section": "Voting", "into": "4", "why": "quorum"}], "open_gaps": []})
        write(st.merged_out(self.d, 1), "# v1\n")
        write(st.surgery_log_out(self.d, 1), "-\n")
        write_json(st.build_verdict_out(self.d), {"winner": "B1", "hard_checks": {"B1": {"installs": True, "tests_pass": True}, "B2": {}}})
        for phase in ("blueprint", "audit", "verdict", "surgery", "verify", "build", "build_judge", "build_surgery"):
            for job in write_prompts(self.state, phase):
                with open(job["prompt"], encoding="utf-8") as fh:
                    text = fh.read()
                self.assertNotIn("{{", text, "%s left a placeholder" % job["id"])
                self.assertIn("community bucket-list", text)

    def test_models_come_from_deck_unless_overridden(self):
        self.assertEqual(phase_jobs(self.state, "blueprint")[0]["model"], "sonnet")
        self.assertEqual(phase_jobs(self.state, "verdict")[0]["model"], "opus")
        self.state["model_override"] = "haiku"
        self.assertEqual(phase_jobs(self.state, "verdict")[0]["model"], "haiku")


if __name__ == "__main__":
    unittest.main()
