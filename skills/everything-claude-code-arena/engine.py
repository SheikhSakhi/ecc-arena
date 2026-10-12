#!/usr/bin/env python3
"""everything-claude-code-arena engine. The orchestrator drives a run with these commands:

    python3 engine.py plan [--agents N | --quick | --full] [--build] [--builders B]
    python3 engine.py init --task-file T [--agents N | --quick | --full] [--seed S] [--build] [--builders B]
    python3 engine.py next                 # what to do now: the phase, the jobs left, the exact calls
    python3 engine.py prompts <phase>      # write the briefs, list the jobs still to run, in waves
    python3 engine.py check <phase>        # which outputs are missing or broken
    python3 engine.py status               # where the run is
    python3 engine.py winner               # the final report: merged blueprint, transplants, open gaps
    python3 engine.py card <agent>         # one competitor's card

State lives in .ecc-arena/<run>/arena.json under the directory you ran init in; later commands find it
through .ecc-arena/LATEST. Run every command from that same directory.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecca import (ArenaError, SKILL_DIR, PHASES, DEFAULT_AGENTS, QUICK_AGENTS, FULL_AGENTS, DEFAULT_GROUP_SIZE,
                  DEFAULT_TOP_K, DEFAULT_BUILDERS, DEFAULT_MAX_SURGERY, DEFAULT_WAVE)  # noqa: E402
from ecca import state as st  # noqa: E402
from ecca.deal import load_deck, deal, deal_builders, make_groups, combo_count  # noqa: E402
from ecca.jobs import next_action, phase_jobs, missing_jobs, latest_merged_version  # noqa: E402
from ecca.plan import plan_totals, compare_with_bracket  # noqa: E402
from ecca.prompts import write_prompts, verify_summary  # noqa: E402
from ecca.scoring import validate_verdict, validate_build_verdict  # noqa: E402


def _agents_arg(args):
    if getattr(args, "quick", False):
        return QUICK_AGENTS
    if getattr(args, "full", False):
        return FULL_AGENTS
    return args.agents or DEFAULT_AGENTS


def cmd_plan(args):
    n = _agents_arg(args)
    t = plan_totals(n, group_size=args.group_size, max_surgery=args.max_surgery, build=args.build,
                    builders=args.builders, wave=args.wave)
    print("%d competitors, waves of %d%s" % (n, args.wave, ", then %d builders" % args.builders if args.build else ""))
    print("  %-28s %6s %6s" % ("phase", "calls", "waves"))
    for r in t["rows"]:
        print("  %-28s %6d %6d" % (r["phase"], r["calls"], r["waves"]))
    print("  %-28s %3d..%-3d %6d" % ("total", t["calls_min"], t["calls_max"], t["waves_max"]))
    print("For comparison, the bracket arena costs %d sub-agent calls for %d agents." % (compare_with_bracket(n), n))


def cmd_init(args):
    n = _agents_arg(args)
    deck = load_deck()
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(4), "big")
    agents = deal(n, seed, deck)
    groups = make_groups(sorted(agents), args.group_size)
    builders = deal_builders(args.builders, seed, deck) if args.build else {}
    run_dir = st.new_run_dir(os.getcwd())
    st.copy_task(args.task_file, run_dir)
    st.copy_skill_docs(SKILL_DIR, run_dir)
    options = {"group_size": args.group_size, "top_k": args.top_k, "max_surgery": args.max_surgery,
               "wave": args.wave, "build": args.build, "builders": args.builders, "models": deck["models"],
               "model_override": args.model}
    state = st.new_state(run_dir, n, seed, agents, groups, builders, options)
    st.save_state(state)
    print("run: %s" % run_dir)
    print("seed %d, %d competitors dealt from %d distinct cards, %d audit groups%s" % (
        seed, n, combo_count(deck), len(groups), ", %d builders" % len(builders) if builders else ""))
    print("Next: python3 engine.py next")


def _load(args):
    return st.load_state(st.latest_run_dir(os.getcwd()))


def _print_wave_plan(state, phase, jobs, left):
    w = state["wave"]
    waves = [left[i:i + w] for i in range(0, len(left), w)]
    print("phase %s: %d jobs, %d still to run, %d wave(s) of up to %d" % (phase, len(jobs), len(left), len(waves), w))
    for k, wave in enumerate(waves, start=1):
        print("  wave %d:" % k)
        for j in wave:
            print("    Agent(subagent_type=general-purpose, model=%s, description=\"ecc-arena %s\", "
                  "prompt=\"Read %s and follow it exactly. It is your whole brief.\")" % (j["model"], j["id"], j["prompt"]))
    if waves:
        print("A wave is one message with all of its Agent calls. Let it finish before the next wave.")


def cmd_next(args):
    state = _load(args)
    phase, left, jobs, note = next_action(state)
    if note:
        print("note: " + note)
    if phase == "done":
        print("DONE. Run: python3 engine.py winner")
        return
    write_prompts(state, phase)
    _print_wave_plan(state, phase, jobs, left)


def cmd_prompts(args):
    state = _load(args)
    jobs = write_prompts(state, args.phase)
    _print_wave_plan(state, args.phase, jobs, missing_jobs(jobs))


def cmd_check(args):
    state = _load(args)
    jobs = phase_jobs(state, args.phase)
    left = missing_jobs(jobs)
    if not left:
        print("phase %s: every output is present" % args.phase)
        return
    print("phase %s: %d job(s) missing output" % (args.phase, len(left)))
    for j in left:
        for p in j["outputs"]:
            if not st.has_output(p):
                print("  %s -> %s" % (j["id"], p))


def cmd_status(args):
    state = _load(args)
    d = state["dir"]
    print("run %s" % d)
    print("seed %s, %d competitors, %d groups, build=%s" % (state["seed"], state["n"], len(state["groups"]), state["build"]))
    for phase in ("blueprint", "audit"):
        jobs = phase_jobs(state, phase)
        print("  %-10s %d of %d written" % (phase, len(jobs) - len(missing_jobs(jobs)), len(jobs)))
    print("  %-10s %s" % ("verdict", "written" if st.has_output(st.verdict_out(d)) else "-"))
    v = latest_merged_version(d)
    print("  %-10s v%d" % ("merged", v) if v else "  merged     -")
    summary = verify_summary(state)
    if summary:
        print("  %-10s v%d total %s, %s" % ("verify", summary["version"], summary["total"], "PASS" if summary["pass"] else "FAIL"))
    if state["build"]:
        jobs = phase_jobs(state, "build")
        print("  %-10s %d of %d reported" % ("builds", len(jobs) - len(missing_jobs(jobs)), len(jobs)))
    try:
        phase, left, _, _ = next_action(state)
        print("next: %s (%d job(s))" % (phase, len(left)))
    except ArenaError as e:
        print("next: blocked: %s" % e)


def cmd_winner(args):
    state = _load(args)
    d = state["dir"]
    verdict_doc = st.read_json(st.verdict_out(d))
    if verdict_doc is None:
        raise ArenaError("no verdict yet")
    verdict = validate_verdict(verdict_doc, list(state["agents"]))
    v = latest_merged_version(d)
    card = state["agents"][verdict["winner"]]["card"]
    print("winner: %s  (%s / %s / %s / emphasis %s)" % (verdict["winner"], card["chain"]["name"], card["reasoning"]["name"],
                                                       card["strategy"]["name"], card["emphasis"]["name"]))
    print("reason: %s" % verdict["reason"])
    print("merged blueprint: %s" % (st.merged_out(d, v) if v else "(none yet)"))
    print("surgery log: %s" % (st.surgery_log_out(d, v) if v else "(none yet)"))
    print("transplants: %d" % len(verdict["transplants"]))
    for t in verdict["transplants"]:
        print("  from %s, lens %s: %s -> %s" % (t["from"], t["lens"], t["section"], t["into"]))
    summary = verify_summary(state)
    if summary:
        print("verification v%d: total %s, %s" % (summary["version"], summary["total"], "PASS" if summary["pass"] else "FAIL"))
        for g in summary["gaps"]:
            print("  open gap [%s] lens %s: %s" % (g["severity"], g["lens"], g["what"]))
    _print_build(state)
    print("full record: %s" % d)


def _print_build(state):
    if not state["build"]:
        return
    doc = st.read_json(st.build_verdict_out(state["dir"]))
    if doc is None:
        print("build: no build verdict yet")
        return
    bv = validate_build_verdict(doc, list(state["builders"]))
    print("build winner: %s. %s" % (bv["winner"], bv["reason"]))
    for t in bv["transplants"]:
        print("  file from %s: %s (%s)" % (t["from"], t["path"], t["why"]))
    if st.has_output(st.build_report_merged_out(state["dir"])):
        print("merged project: %s (report %s)" % (st.merged_project_dir(state["dir"]), st.build_report_merged_out(state["dir"])))


def cmd_card(args):
    state = _load(args)
    agent = state["agents"].get(args.agent) or state["builders"].get(args.agent)
    if not agent:
        raise ArenaError("unknown agent %s" % args.agent)
    for key, part in agent["card"].items():
        print("%-10s %s: %s" % (key, part["name"], part["how"]))


def _size_flags(p):
    g = p.add_mutually_exclusive_group()
    g.add_argument("--agents", type=int, help="number of competitors (default %d)" % DEFAULT_AGENTS)
    g.add_argument("--quick", action="store_true", help="%d competitors, one per emphasis" % QUICK_AGENTS)
    g.add_argument("--full", action="store_true", help="%d competitors" % FULL_AGENTS)
    p.add_argument("--build", action="store_true", help="after the blueprint, build the project with B builders")
    p.add_argument("--builders", type=int, default=DEFAULT_BUILDERS)
    p.add_argument("--group-size", type=int, default=DEFAULT_GROUP_SIZE)
    p.add_argument("--max-surgery", type=int, default=DEFAULT_MAX_SURGERY)
    p.add_argument("--wave", type=int, default=DEFAULT_WAVE)


def build_parser():
    p = argparse.ArgumentParser(prog="engine.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    sub.required = True
    s = sub.add_parser("plan", help="calls and waves for a run. Writes nothing.")
    _size_flags(s)
    s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("init", help="deal the cards and start a run")
    _size_flags(s)
    s.add_argument("--task-file", required=True)
    s.add_argument("--seed", type=int)
    s.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    s.add_argument("--model", help="use this model for every role instead of the per-role defaults in deck.json")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("next", help="what to do now")
    s.set_defaults(fn=cmd_next)
    for name, fn in (("prompts", cmd_prompts), ("check", cmd_check)):
        s = sub.add_parser(name)
        s.add_argument("phase", choices=PHASES)
        s.set_defaults(fn=fn)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("winner").set_defaults(fn=cmd_winner)
    s = sub.add_parser("card")
    s.add_argument("agent")
    s.set_defaults(fn=cmd_card)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except ArenaError as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
