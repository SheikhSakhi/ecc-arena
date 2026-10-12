"""Builds one brief per job from the templates in prompts/. The brief is everything a sub-agent knows."""
import json
import os
import re

from . import ArenaError, SKILL_DIR, PACKAGE_FILES
from . import state as st
from .deal import agent_lines, skill_lines
from .jobs import phase_jobs, load_audits
from .scoring import rank_all, shortlist, merge_unions

PROMPTS_DIR = os.path.join(SKILL_DIR, "prompts")
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def load_template(kind):
    path = os.path.join(PROMPTS_DIR, kind + ".md")
    if not os.path.isfile(path):
        raise ArenaError("missing prompt template: %s" % path)
    with open(path, encoding="utf-8") as fh:
        return fh.read().rstrip("\n")


def fill(template, values):
    """One pass, so a task that itself contains {{braces}} is left exactly as written."""
    wanted = set(_PLACEHOLDER_RE.findall(template))
    missing = sorted(wanted - set(values))
    if missing:
        raise ArenaError("no value for placeholder(s): %s" % ", ".join(missing))
    return _PLACEHOLDER_RE.sub(lambda m: str(values[m.group(1)]), template)


def _card_values(card):
    return {"chain_name": card["chain"]["name"], "chain_how": card["chain"]["how"],
            "chain_agents": agent_lines(card["chain"]["agents"]), "chain_skills": skill_lines(card["chain"]["skills"]),
            "reasoning_name": card["reasoning"]["name"], "reasoning_how": card["reasoning"]["how"],
            "strategy_name": card["strategy"]["name"], "strategy_how": card["strategy"]["how"]}


def _base_values(state):
    d = state["dir"]
    return {"task": st.read_task(state), "arena_dir": d, "n": state["n"],
            "matrix_doc": os.path.join(d, "matrix.md"), "lenses_doc": os.path.join(d, "lenses.md"),
            "rubric": os.path.join(d, "rubric.md")}


def _list(items):
    return "\n".join("- " + i for i in items) or "- (none)"


def _package_lines(state, ids):
    return _list("%s: %s" % (a, st.package_dir(state["dir"], a)) for a in ids)


def render_job(state, job):
    v = _base_values(state)
    renderers = {"compete": _compete_values, "audit": _audit_values, "verdict": _verdict_values,
                 "surgery": _surgery_values, "verify": _verify_values, "deliver": _deliver_values}
    v.update(renderers[job["kind"]](state, job))
    return fill(load_template(job["kind"]), v)


def _compete_values(state, job):
    aid = job["agent"]
    v = _card_values(state["agents"][aid]["card"])
    v.update(agent=aid, package_dir=st.package_dir(state["dir"], aid), scratch=st.scratch_dir(state["dir"], aid))
    return v


def _audit_values(state, job):
    return {"group": job["group"], "count": len(job["entries"]), "entries": _package_lines(state, job["entries"]),
            "out": job["outputs"][0]}


def _verdict_values(state, job):
    d = state["dir"]
    audits = load_audits(state)
    ranking = rank_all(audits)
    top = shortlist(ranking, state["top_k"])
    union = merge_unions(audits)
    os.makedirs(os.path.dirname(st.shortlist_path(d)), exist_ok=True)
    with open(st.shortlist_path(d), "w", encoding="utf-8") as fh:
        json.dump({"ranking": ranking, "shortlist": top, "union": union}, fh, indent=2)
    return {"audits": _list(st.audit_out(d, g) for g in sorted(state["groups"])),
            "shortlist": _list("%s (group %s rank %d, total %s): %s" % (r["id"], r["group"], r["group_rank"], r["total"],
                                                                        st.package_dir(d, r["id"])) for r in top),
            "all_packages": _package_lines(state, sorted(state["agents"])), "top_k": state["top_k"],
            "out": job["outputs"][0]}


def _surgery_values(state, job):
    d, v = state["dir"], job["version"]
    verdict = st.read_json(st.verdict_out(d))
    winner = verdict["winner"]
    donors = sorted({t["from"] for t in verdict.get("transplants", []) if t.get("from") in state["agents"]})
    if v == 1:
        previous = "This is the first pass. Start from the winner's package."
    else:
        previous = ("This is pass %d. The previous final package is %s and its verification is %s. Start from the "
                    "previous final package and fix every gap, undefined probe and contradiction the verification lists."
                    % (v, st.final_dir(d, v - 1), st.verify_out(d, v - 1)))
    return {"version": v, "winner": winner, "winner_dir": st.package_dir(d, winner), "verdict": st.verdict_out(d),
            "donors": _package_lines(state, donors), "all_packages": _package_lines(state, sorted(state["agents"])),
            "previous": previous, "out_dir": st.final_dir(d, v), "log_out": job["outputs"][-1]}


def _verify_values(state, job):
    criteria_threshold = _threshold(state)
    return {"version": job["version"], "final_dir": st.final_dir(state["dir"], job["version"]),
            "threshold": criteria_threshold, "out": job["outputs"][0]}


def _threshold(state):
    with open(os.path.join(state["dir"], "criteria.json"), encoding="utf-8") as fh:
        return json.load(fh).get("pass_threshold", 7)


def _deliver_values(state, job):
    d = state["dir"]
    v = st.latest_final_version(d)
    if v == 0:
        raise ArenaError("no final package exists yet")
    return {"final_dir": st.final_dir(d, v), "deliver_skills": skill_lines(state.get("deliver_skills", [])),
            "out_dir": st.deliverable_dir(d), "business_out": st.business_plan_out(d), "deck_out": st.pitch_deck_out(d)}


def write_prompts(state, phase):
    jobs = phase_jobs(state, phase)
    for j in jobs:
        for p in j["outputs"] + [j["prompt"]]:
            os.makedirs(os.path.dirname(p), exist_ok=True)
        if j["kind"] == "compete":
            os.makedirs(st.scratch_dir(state["dir"], j["agent"]), exist_ok=True)
        with open(j["prompt"], "w", encoding="utf-8") as fh:
            fh.write(render_job(state, j) + "\n")
    return jobs


def package_file_names():
    return list(PACKAGE_FILES)
