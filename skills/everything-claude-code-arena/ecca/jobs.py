"""Which sub-agent jobs exist in each phase, which are still missing, and what comes next."""
import glob
import os
import re

from . import ArenaError, PHASES
from . import state as st
from .scoring import load_lenses, validate_audit, validate_verify, validate_verdict, validate_build_verdict


def _job(jid, kind, outputs, **extra):
    j = {"id": jid, "kind": kind, "outputs": outputs}
    j.update(extra)
    return j


def latest_merged_version(d):
    versions = [int(m.group(1)) for p in glob.glob(st.merged_out(d, 0).replace("v0", "v*"))
                for m in [re.search(r"blueprint\.v(\d+)\.md$", p)] if m]
    return max(versions) if versions else 0


def phase_jobs(state, phase):
    if phase not in PHASES:
        raise ArenaError("unknown phase '%s' (one of: %s)" % (phase, ", ".join(PHASES)))
    d = state["dir"]
    if phase == "blueprint":
        jobs = [_job(a + ".blueprint", "blueprint", [st.blueprint_out(d, a)], agent=a) for a in sorted(state["agents"])]
    elif phase == "audit":
        jobs = [_job(g + ".audit", "audit", [st.audit_out(d, g)], group=g, entries=ids)
                for g, ids in sorted(state["groups"].items())]
    elif phase == "verdict":
        jobs = [_job("chief.verdict", "verdict", [st.verdict_out(d)])]
    elif phase == "surgery":
        v = _surgery_version(state)
        jobs = [_job("surgeon.v%d" % v, "surgery", [st.merged_out(d, v), st.surgery_log_out(d, v)], version=v)]
    elif phase == "verify":
        v = latest_merged_version(d)
        jobs = [_job("verifier.v%d" % v, "verify", [st.verify_out(d, v)], version=v)] if v else []
    elif phase == "build":
        jobs = [_job(b + ".build", "build", [st.build_report_out(d, b)], builder=b) for b in sorted(state["builders"])]
    elif phase == "build_judge":
        jobs = [_job("build.judge", "build_judge", [st.build_verdict_out(d)])]
    else:
        jobs = [_job("build.surgeon", "build_surgery", [st.build_report_merged_out(d)])]
    for j in jobs:
        j["prompt"] = st.prompt_path(d, phase, j["id"])
        j["model"] = state.get("model_override") or state["models"].get(j["kind"], "sonnet")
    return jobs


def _surgery_version(state):
    """The version the next surgery pass writes: 1 when none exists, else latest + 1."""
    v = latest_merged_version(state["dir"])
    return 1 if v == 0 else v + 1


def missing_jobs(jobs):
    return [j for j in jobs if not all(st.has_output(p) for p in j["outputs"])]


def _audits(state, lenses):
    """Every group's validated audit. ArenaError names the broken file."""
    out = []
    for gid, ids in sorted(state["groups"].items()):
        doc = st.read_json(st.audit_out(state["dir"], gid))
        if doc is None:
            return None
        out.append(validate_audit(doc, gid, ids, lenses))
    return out


def next_action(state):
    """(phase, jobs_left, jobs_all, note). phase is a PHASES entry or 'done'."""
    lenses = load_lenses(os.path.join(state["dir"], "lenses.json"))
    for phase in ("blueprint", "audit"):
        jobs = phase_jobs(state, phase)
        left = missing_jobs(jobs)
        if left:
            return phase, left, jobs, ""
    if _audits(state, lenses) is None:
        raise ArenaError("an audit file exists but is empty")
    verdict_doc = st.read_json(st.verdict_out(state["dir"]))
    if verdict_doc is None:
        jobs = phase_jobs(state, "verdict")
        return "verdict", jobs, jobs, ""
    validate_verdict(verdict_doc, list(state["agents"]))
    return _after_verdict(state, lenses)


def _after_verdict(state, lenses):
    d = state["dir"]
    v = latest_merged_version(d)
    if v == 0:
        jobs = phase_jobs(state, "surgery")
        return "surgery", jobs, jobs, "first surgery pass"
    verify_doc = st.read_json(st.verify_out(d, v))
    if verify_doc is None:
        jobs = phase_jobs(state, "verify")
        return "verify", jobs, jobs, "verifying merged blueprint v%d" % v
    result = validate_verify(verify_doc, lenses)
    if not result["pass"] and v < state["max_surgery"]:
        jobs = phase_jobs(state, "surgery")
        return "surgery", jobs, jobs, "v%d failed verification (%s); pass %d of %d" % (
            v, _fail_reason(result), v + 1, state["max_surgery"])
    note = "merged blueprint v%d %s" % (v, "passed" if result["pass"] else "did NOT pass after the last allowed pass; open gaps go to the user")
    if not state["build"]:
        return "done", [], [], note
    return _build_phases(state, note)


def _fail_reason(result):
    parts = []
    if result["fatal"]:
        parts.append("fatal")
    if result["low_lenses"]:
        parts.append("low lenses " + ",".join(result["low_lenses"]))
    blocking = [g for g in result["gaps"] if g["severity"] in ("FATAL", "MAJOR")]
    if blocking:
        parts.append("%d blocking gaps" % len(blocking))
    if result["contradictions"]:
        parts.append("%d contradictions" % len(result["contradictions"]))
    return "; ".join(parts) or "did not pass"


def _build_phases(state, note):
    jobs = phase_jobs(state, "build")
    left = missing_jobs(jobs)
    if left:
        return "build", left, jobs, note
    doc = st.read_json(st.build_verdict_out(state["dir"]))
    if doc is None:
        jobs = phase_jobs(state, "build_judge")
        return "build_judge", jobs, jobs, "all builds reported"
    validate_build_verdict(doc, list(state["builders"]))
    jobs = phase_jobs(state, "build_surgery")
    if missing_jobs(jobs):
        return "build_surgery", jobs, jobs, "build winner: " + doc["winner"]
    return "done", [], [], note + "; merged build ready"
