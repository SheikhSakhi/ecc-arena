"""Builds one brief per job from the templates in prompts/. The brief is everything a sub-agent knows."""
import json
import os
import re

from . import ArenaError, SKILL_DIR
from . import state as st
from .deal import chain_agent_lines
from .jobs import phase_jobs, latest_merged_version
from .scoring import load_lenses, validate_audit, rank_all, shortlist, best_parts_index, validate_verify

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
    v = {"chain_name": card["chain"]["name"], "chain_how": card["chain"]["how"],
         "chain_agents": chain_agent_lines(card["chain"]),
         "strategy_name": card["strategy"]["name"], "strategy_how": card["strategy"]["how"]}
    if "reasoning" in card:
        v.update(reasoning_name=card["reasoning"]["name"], reasoning_how=card["reasoning"]["how"])
    if "emphasis" in card:
        v.update(emphasis_name=card["emphasis"]["name"], emphasis_how=card["emphasis"]["how"],
                 emphasis_lenses=", ".join(card["emphasis"]["lenses"]))
    return v


def _base_values(state):
    d = state["dir"]
    return {"task": st.read_task(state), "arena_dir": d, "n": state["n"],
            "lenses_doc": os.path.join(d, "lenses.md"), "rubric": os.path.join(d, "rubric.md")}


def _list(items):
    return "\n".join("- " + i for i in items)


def _blueprint_lines(state, ids):
    return _list("%s: %s" % (a, st.blueprint_out(state["dir"], a)) for a in ids)


def render_job(state, job):
    v = _base_values(state)
    kind = job["kind"]
    renderers = {"blueprint": _blueprint_values, "audit": _audit_values, "verdict": _verdict_values,
                 "surgery": _surgery_values, "verify": _verify_values, "build": _build_values,
                 "build_judge": _build_judge_values, "build_surgery": _build_surgery_values}
    v.update(renderers[kind](state, job))
    return fill(load_template(kind), v)


def _blueprint_values(state, job):
    aid = job["agent"]
    v = _card_values(state["agents"][aid]["card"])
    v.update(agent=aid, out=job["outputs"][0], scratch=st.scratch_dir(state["dir"], aid))
    return v


def _audit_values(state, job):
    return {"group": job["group"], "count": len(job["entries"]),
            "entries": _blueprint_lines(state, job["entries"]), "out": job["outputs"][0]}


def _verdict_values(state, job):
    lenses = load_lenses(os.path.join(state["dir"], "lenses.json"))
    audits = [validate_audit(st.read_json(st.audit_out(state["dir"], g)), g, ids, lenses)
              for g, ids in sorted(state["groups"].items())]
    ranking = rank_all(audits)
    top = shortlist(ranking, state["top_k"])
    parts = best_parts_index(audits)
    short = {"ranking": ranking, "shortlist": top, "best_parts": parts}
    os.makedirs(os.path.dirname(st.shortlist_path(state["dir"])), exist_ok=True)
    with open(st.shortlist_path(state["dir"]), "w", encoding="utf-8") as fh:
        json.dump(short, fh, indent=2)
    return {"audits": _list(st.audit_out(state["dir"], g) for g in sorted(state["groups"])),
            "shortlist": _list("%s (group %s rank %d, total %s): %s" % (
                r["id"], r["group"], r["group_rank"], r["total"], st.blueprint_out(state["dir"], r["id"])) for r in top),
            "best_parts": _best_parts_lines(parts, lenses),
            "all_blueprints": _blueprint_lines(state, sorted(state["agents"])),
            "top_k": state["top_k"], "out": job["outputs"][0]}


def _best_parts_lines(parts, lenses):
    lines = []
    for lens in lenses["ids"]:
        for p in parts.get(lens, []):
            lines.append("- %s (%s): %s, section '%s': %s" % (lens, lenses["names"][lens], p["entry"], p["section"], p["why"]))
    return "\n".join(lines) or "- (no best parts were named)"


def _surgery_values(state, job):
    d, v = state["dir"], job["version"]
    verdict = st.read_json(st.verdict_out(d))
    winner = verdict["winner"]
    donors = sorted({t["from"] for t in verdict.get("transplants", []) if t.get("from") in state["agents"]})
    if v == 1:
        previous = "This is the first pass. Start from the winner's blueprint."
    else:
        previous = ("This is pass %d. The previous merged blueprint is %s and its verification is %s. Start from "
                    "the previous merged blueprint and fix every gap the verification lists." % (
                        v, st.merged_out(d, v - 1), st.verify_out(d, v - 1)))
    return {"version": v, "winner": winner, "winner_blueprint": st.blueprint_out(d, winner),
            "verdict": st.verdict_out(d), "donors": _blueprint_lines(state, donors) or "- (none)",
            "all_blueprints": _blueprint_lines(state, sorted(state["agents"])), "previous": previous,
            "out": job["outputs"][0], "log_out": job["outputs"][1]}


def _verify_values(state, job):
    lenses = load_lenses(os.path.join(state["dir"], "lenses.json"))
    return {"version": job["version"], "merged": st.merged_out(state["dir"], job["version"]),
            "threshold": lenses["threshold"], "out": job["outputs"][0]}


def _final_blueprint(state):
    v = latest_merged_version(state["dir"])
    if v == 0:
        raise ArenaError("no merged blueprint exists yet")
    return st.merged_out(state["dir"], v)


def _build_values(state, job):
    bid = job["builder"]
    v = _card_values(state["builders"][bid]["card"])
    v.update(builder=bid, blueprint=_final_blueprint(state), build_dir=st.build_dir(state["dir"], bid),
             out=job["outputs"][0])
    return v


def _build_lines(state):
    d = state["dir"]
    return _list("%s: project in %s, report at %s" % (b, st.build_dir(d, b), st.build_report_out(d, b))
                 for b in sorted(state["builders"]))


def _build_judge_values(state, job):
    return {"blueprint": _final_blueprint(state), "builds": _build_lines(state),
            "scratch": st.scratch_dir(state["dir"], "build-judge"), "out": job["outputs"][0]}


def _build_surgery_values(state, job):
    verdict = st.read_json(st.build_verdict_out(state["dir"]))
    return {"blueprint": _final_blueprint(state), "builds": _build_lines(state),
            "verdict": st.build_verdict_out(state["dir"]), "winner": verdict["winner"],
            "winner_dir": st.build_dir(state["dir"], verdict["winner"]),
            "out_dir": st.merged_project_dir(state["dir"]), "out": job["outputs"][0]}


def write_prompts(state, phase):
    jobs = phase_jobs(state, phase)
    for j in jobs:
        for p in j["outputs"] + [j["prompt"]]:
            os.makedirs(os.path.dirname(p), exist_ok=True)
        if j["kind"] == "blueprint":
            os.makedirs(st.scratch_dir(state["dir"], j["agent"]), exist_ok=True)
        with open(j["prompt"], "w", encoding="utf-8") as fh:
            fh.write(render_job(state, j) + "\n")
    return jobs


def verify_summary(state):
    """The latest verification result, or None."""
    v = latest_merged_version(state["dir"])
    doc = st.read_json(st.verify_out(state["dir"], v)) if v else None
    if doc is None:
        return None
    return dict(validate_verify(doc, load_lenses(os.path.join(state["dir"], "lenses.json"))), version=v)
