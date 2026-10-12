"""Which sub-agent jobs exist in each phase, which are still missing, and what comes next."""
import os

from . import ArenaError, PHASES
from . import state as st
from .scoring import load_criteria, validate_audit, validate_verdict, validate_verify, fail_reason


def _job(jid, kind, outputs, **extra):
    j = {"id": jid, "kind": kind, "outputs": outputs}
    j.update(extra)
    return j


def phase_jobs(state, phase):
    if phase not in PHASES:
        raise ArenaError("unknown phase '%s' (one of: %s)" % (phase, ", ".join(PHASES)))
    d = state["dir"]
    if phase == "compete":
        jobs = [_job(a + ".compete", "compete", st.package_required(d, a), agent=a) for a in sorted(state["agents"])]
    elif phase == "audit":
        jobs = [_job(g + ".audit", "audit", [st.audit_out(d, g)], group=g, entries=ids)
                for g, ids in sorted(state["groups"].items())]
    elif phase == "verdict":
        jobs = [_job("chief.verdict", "verdict", [st.verdict_out(d)])]
    elif phase == "surgery":
        v = st.latest_final_version(d) + 1
        jobs = [_job("surgeon.v%d" % v, "surgery", st.final_required(d, v) + [st.surgery_log_out(d, v)], version=v)]
    elif phase == "verify":
        v = st.latest_final_version(d)
        jobs = [_job("verifier.v%d" % v, "verify", [st.verify_out(d, v)], version=v)] if v else []
    else:
        jobs = [_job("deliver", "deliver", [st.business_plan_out(d), st.pitch_deck_out(d), st.delivered_readme(d)])]
    for j in jobs:
        j["prompt"] = st.prompt_path(d, phase, j["id"])
        j["model"] = state.get("model_override") or state["models"].get(j["kind"], "sonnet")
    return jobs


def missing_jobs(jobs):
    return [j for j in jobs if not all(st.has_output(p) for p in j["outputs"])]


def load_audits(state):
    """Every group's validated audit, or None if one is still missing. ArenaError names a broken file."""
    criteria = load_criteria(os.path.join(state["dir"], "criteria.json"))
    out = []
    for gid, ids in sorted(state["groups"].items()):
        doc = st.read_json(st.audit_out(state["dir"], gid))
        if doc is None:
            return None
        out.append(validate_audit(doc, gid, ids, criteria))
    return out


def next_action(state):
    """(phase, jobs_left, jobs_all, note). phase is a PHASES entry or 'done'."""
    for phase in ("compete", "audit"):
        jobs = phase_jobs(state, phase)
        left = missing_jobs(jobs)
        if left:
            return phase, left, jobs, ""
    load_audits(state)
    verdict_doc = st.read_json(st.verdict_out(state["dir"]))
    if verdict_doc is None:
        jobs = phase_jobs(state, "verdict")
        return "verdict", jobs, jobs, ""
    validate_verdict(verdict_doc, list(state["agents"]))
    return _after_verdict(state)


def _after_verdict(state):
    d = state["dir"]
    criteria = load_criteria(os.path.join(d, "criteria.json"))
    v = st.latest_final_version(d)
    if v == 0:
        jobs = phase_jobs(state, "surgery")
        return "surgery", jobs, jobs, "first surgery pass"
    verify_doc = st.read_json(st.verify_out(d, v))
    if verify_doc is None:
        jobs = phase_jobs(state, "verify")
        return "verify", jobs, jobs, "verifying final package v%d" % v
    result = validate_verify(verify_doc, criteria)
    if not result["pass"] and v < state["max_surgery"]:
        jobs = phase_jobs(state, "surgery")
        return "surgery", jobs, jobs, "v%d failed verification (%s); pass %d of %d" % (v, fail_reason(result), v + 1, state["max_surgery"])
    note = "final package v%d %s" % (v, "passed" if result["pass"] else "did NOT pass after the last allowed pass; open gaps go to the user")
    jobs = phase_jobs(state, "deliver")
    if missing_jobs(jobs):
        return "deliver", jobs, jobs, note
    return "done", [], [], note + "; deliverables written"


def verify_summary(state):
    """The latest verification result with its version, or None."""
    v = st.latest_final_version(state["dir"])
    doc = st.read_json(st.verify_out(state["dir"], v)) if v else None
    if doc is None:
        return None
    criteria = load_criteria(os.path.join(state["dir"], "criteria.json"))
    return dict(validate_verify(doc, criteria), version=v)
