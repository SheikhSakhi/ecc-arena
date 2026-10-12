"""How many sub-agent calls a run costs, before anything is spent."""
import math

from . import DEFAULT_GROUP_SIZE, DEFAULT_MAX_SURGERY, DEFAULT_WAVE


def plan_rows(n, group_size=DEFAULT_GROUP_SIZE, max_surgery=DEFAULT_MAX_SURGERY, wave=DEFAULT_WAVE):
    """One row per phase: calls and waves. Surgery and verify are shown at their maximum."""
    groups = max(1, math.ceil(n / group_size))
    rows = [("compete", n, math.ceil(n / wave)),
            ("audit", groups, math.ceil(groups / wave)),
            ("verdict", 1, 1),
            ("surgery (up to %d passes)" % max_surgery, max_surgery, max_surgery),
            ("verify (up to %d passes)" % max_surgery, max_surgery, max_surgery),
            ("deliver", 1, 1)]
    return [{"phase": p, "calls": c, "waves": w} for p, c, w in rows]


def plan_totals(n, **kw):
    rows = plan_rows(n, **kw)
    max_surgery = kw.get("max_surgery", DEFAULT_MAX_SURGERY)
    calls_max = sum(r["calls"] for r in rows)
    return {"agents": n, "rows": rows, "calls_max": calls_max, "calls_min": calls_max - 2 * (max_surgery - 1),
            "waves_max": sum(r["waves"] for r in rows)}


def compare_with_bracket(n):
    """What the single-elimination arena costs for the same n: n spawns + 5 calls per match."""
    return n + 5 * (n - 1)
