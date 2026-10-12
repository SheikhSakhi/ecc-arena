"""Run folder layout and the state file. Every path the engine ever uses is defined here."""
import glob
import json
import os
import re
import shutil
import time

from . import (ArenaError, LATEST_FILE, RUN_ROOT, STATE_FILE, VERSION, DEFAULT_GROUP_SIZE, DEFAULT_TOP_K,
               DEFAULT_MAX_SURGERY, DEFAULT_WAVE, PACKAGE_REQUIRED)

SKILL_DOCS = ("matrix.md", "lenses.md", "rubric.md", "criteria.json")


def package_dir(d, aid):
    return os.path.join(d, "packages", aid)


def package_required(d, aid):
    return [os.path.join(package_dir(d, aid), name) for name in PACKAGE_REQUIRED]


def audit_out(d, gid):
    return os.path.join(d, "audits", gid + ".json")


def shortlist_path(d):
    return os.path.join(d, "verdict", "shortlist.json")


def verdict_out(d):
    return os.path.join(d, "verdict", "verdict.json")


def final_dir(d, version):
    return os.path.join(d, "final", "v%d" % version)


def final_required(d, version):
    return [os.path.join(final_dir(d, version), name) for name in PACKAGE_REQUIRED]


def surgery_log_out(d, version):
    return os.path.join(d, "final", "surgery.v%d.md" % version)


def verify_out(d, version):
    return os.path.join(d, "final", "verify.v%d.json" % version)


def deliverable_dir(d):
    return os.path.join(d, "deliverable")


def business_plan_out(d):
    return os.path.join(deliverable_dir(d), "BUSINESS-PLAN.md")


def pitch_deck_out(d):
    return os.path.join(deliverable_dir(d), "PITCH-DECK.md")


def delivered_readme(d):
    return os.path.join(deliverable_dir(d), "project", "README.md")


def prompt_path(d, phase, job_id):
    return os.path.join(d, "prompts", phase, job_id + ".md")


def scratch_dir(d, name):
    return os.path.join(d, "scratch", name)


def task_path(d):
    return os.path.join(d, "task.md")


def has_output(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0


def latest_final_version(d):
    versions = []
    for p in glob.glob(os.path.join(d, "final", "v*", "MATRIX.md")):
        m = re.search(r"[/\\]v(\d+)[/\\]MATRIX\.md$", p)
        if m and has_output(p):
            versions.append(int(m.group(1)))
    return max(versions) if versions else 0


def new_run_dir(cwd):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(cwd, RUN_ROOT, stamp)
    if os.path.exists(run_dir):
        run_dir += "-%d" % int(time.time() * 1000 % 1000)
    os.makedirs(run_dir)
    with open(os.path.join(cwd, RUN_ROOT, LATEST_FILE), "w", encoding="utf-8") as fh:
        fh.write(run_dir + "\n")
    return run_dir


def latest_run_dir(cwd):
    latest = os.path.join(cwd, RUN_ROOT, LATEST_FILE)
    if not os.path.isfile(latest):
        raise ArenaError("no run found: %s does not exist. Run `init` first, from the same directory." % latest)
    with open(latest, encoding="utf-8") as fh:
        run_dir = fh.read().strip()
    if not os.path.isdir(run_dir):
        raise ArenaError("LATEST points at %s, which is gone." % run_dir)
    return run_dir


def new_state(run_dir, n, seed, agents, groups, options):
    return {
        "version": VERSION,
        "seed": seed,
        "dir": run_dir,
        "n": n,
        "group_size": options.get("group_size", DEFAULT_GROUP_SIZE),
        "top_k": options.get("top_k", DEFAULT_TOP_K),
        "max_surgery": options.get("max_surgery", DEFAULT_MAX_SURGERY),
        "wave": options.get("wave", DEFAULT_WAVE),
        "model_override": options.get("model_override"),
        "models": dict(options.get("models", {})),
        "deliver_skills": list(options.get("deliver_skills", [])),
        "agents": agents,
        "groups": groups,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def copy_task(src, run_dir):
    if not os.path.isfile(src):
        raise ArenaError("task file not found: %s" % src)
    with open(src, encoding="utf-8") as fh:
        text = fh.read().rstrip("\n")
    if not text.strip():
        raise ArenaError("task file is empty: %s" % src)
    dst = task_path(run_dir)
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return dst


def copy_skill_docs(skill_dir, run_dir):
    """Judges read the method docs from the run folder, so a run is self-contained."""
    for name in SKILL_DOCS:
        shutil.copy(os.path.join(skill_dir, name), os.path.join(run_dir, name))


def load_state(run_dir):
    path = os.path.join(run_dir, STATE_FILE)
    if not os.path.isfile(path):
        raise ArenaError("no %s in %s" % (STATE_FILE, run_dir))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(state):
    path = os.path.join(state["dir"], STATE_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def read_task(state):
    with open(task_path(state["dir"]), encoding="utf-8") as fh:
        return fh.read().rstrip("\n")


def read_json(path):
    """Parsed JSON, or None when the file is missing or empty. ArenaError when present but broken."""
    if not has_output(path):
        return None
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ArenaError("%s is not JSON" % path)
        try:
            return json.loads(text[start:end + 1])
        except ValueError:
            raise ArenaError("%s is not JSON" % path)
