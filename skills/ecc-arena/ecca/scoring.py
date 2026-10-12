"""Reads what the judges wrote, checks it, and does the arithmetic. Judges never compute totals."""
import json
import os
import re

from . import ArenaError, SKILL_DIR, FORBIDDEN_MARKERS, PACKAGE_FILES

CRITERIA_PATH = os.path.join(SKILL_DIR, "criteria.json")
SEVERITIES = ("FATAL", "MAJOR", "MINOR")
BLOCKING = ("FATAL", "MAJOR")
PROBE_RESULTS = ("BLOCKED", "ALLOWED", "UNDEFINED")


def load_criteria(path=CRITERIA_PATH):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    items = doc.get("criteria") or []
    if not items:
        raise ArenaError("criteria.json has no criteria")
    if sum(c["weight"] for c in items) != 100:
        raise ArenaError("criteria weights must sum to 100")
    return {"ids": [c["id"] for c in items], "names": {c["id"]: c["name"] for c in items},
            "weights": {c["id"]: c["weight"] for c in items}, "threshold": doc.get("pass_threshold", 7)}


def _score(value, where):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ArenaError("%s: score %r is not a number" % (where, value))
    if not 0 <= v <= 10:
        raise ArenaError("%s: score %s is outside 0..10" % (where, v))
    return v


def total(scores, criteria, where):
    """Weighted 0..100 total. Every criterion must be present."""
    missing = [c for c in criteria["ids"] if c not in (scores or {})]
    if missing:
        raise ArenaError("%s: missing scores for %s" % (where, ", ".join(missing)))
    return round(sum(_score(scores[c], where + " " + c) * criteria["weights"][c] for c in criteria["ids"]) / 10, 1)


def _truthy(v):
    return v is True or str(v).strip().lower() in ("true", "yes", "1")


def _gaps(raw, where):
    gaps = []
    for g in raw or []:
        sev = str(g.get("severity", "MINOR")).upper()
        if sev not in SEVERITIES:
            raise ArenaError("%s: gap severity %r must be one of %s" % (where, sev, "/".join(SEVERITIES)))
        gaps.append({"union_id": g.get("union_id"), "row": g.get("row", ""), "question": g.get("question", ""),
                     "severity": sev, "what": g.get("what", ""), "fix": g.get("fix", "")})
    return gaps


def _probes(raw, where):
    probes = []
    for p in raw or []:
        result = str(p.get("result", "UNDEFINED")).upper()
        if result not in PROBE_RESULTS:
            raise ArenaError("%s: probe result %r must be one of %s" % (where, result, "/".join(PROBE_RESULTS)))
        probes.append({"scenario": p.get("scenario", ""), "result": result, "where": p.get("where", "")})
    return probes


def _union(raw, allowed):
    cells = []
    for c in raw or []:
        if not isinstance(c, dict) or not c.get("id"):
            continue
        filled = [a for a in (c.get("filled_by") or []) if a in allowed]
        cells.append({"id": c["id"], "row": c.get("row", ""), "question": c.get("question", ""), "filled_by": filled})
    return cells


def validate_audit(doc, gid, expected, criteria):
    """Normalised group audit: union cells, entries with computed totals, gaps and probes."""
    where = "audit " + gid
    entries = doc.get("entries")
    if not isinstance(entries, dict):
        raise ArenaError("%s: 'entries' must be an object keyed by competitor id" % where)
    missing = [a for a in expected if a not in entries]
    if missing:
        raise ArenaError("%s: no scores for %s" % (where, ", ".join(missing)))
    out = {}
    for aid in expected:
        e, w = entries[aid], "%s %s" % (where, aid)
        out[aid] = {"scores": {c: _score((e.get("scores") or {}).get(c), w + " " + c) for c in criteria["ids"]},
                    "total": total(e.get("scores"), criteria, w), "fatal": _truthy(e.get("fatal", False)),
                    "fatal_reason": e.get("fatal_reason", ""), "gaps": _gaps(e.get("gaps"), w),
                    "probes": _probes(e.get("probes"), w), "notes": e.get("notes", "")}
    union = _union(doc.get("union"), set(expected))
    if not union:
        raise ArenaError("%s: 'union' must list at least one matrix cell" % where)
    return {"group": gid, "entries": out, "union": union}


def rank_group(audit):
    items = sorted(audit["entries"].items(), key=lambda kv: (kv[1]["fatal"], -kv[1]["total"], kv[0]))
    return [{"id": aid, "group": audit["group"], "group_rank": i + 1, "total": e["total"], "fatal": e["fatal"]}
            for i, (aid, e) in enumerate(items)]


def rank_all(audits):
    """Global order: group rank first (judges drift between groups), then raw total."""
    rows = [r for audit in audits for r in rank_group(audit)]
    rows.sort(key=lambda r: (r["fatal"], r["group_rank"], -r["total"], r["id"]))
    return rows


def shortlist(ranking, k):
    return [r for r in ranking if not r["fatal"]][:k] or ranking[:k]


def merge_unions(audits):
    """Global union keyed by (row, question), with the full list of competitors that filled it."""
    merged = {}
    for audit in audits:
        for cell in audit["union"]:
            key = (cell["row"].strip().lower(), cell["question"].strip().lower())
            entry = merged.setdefault(key, {"row": cell["row"], "question": cell["question"], "filled_by": [],
                                            "group_ids": []})
            entry["filled_by"] = sorted(set(entry["filled_by"]) | set(cell["filled_by"]))
            entry["group_ids"].append("%s:%s" % (audit["group"], cell["id"]))
    cells = sorted(merged.values(), key=lambda c: (c["row"], c["question"]))
    return [dict(c, id="U%d" % (i + 1), prevalence=len(c["filled_by"])) for i, c in enumerate(cells)]


def validate_verdict(doc, agent_ids):
    winner = doc.get("winner")
    if winner not in agent_ids:
        raise ArenaError("verdict: winner %r is not a competitor id" % winner)
    transplants = []
    for t in doc.get("transplants") or []:
        if t.get("from") not in agent_ids:
            raise ArenaError("verdict: transplant from unknown competitor %r" % t.get("from"))
        if t["from"] == winner:
            raise ArenaError("verdict: a transplant cannot come from the winner itself")
        if not t.get("union_id"):
            raise ArenaError("verdict: every transplant must name the union cell it fills (union_id)")
        transplants.append({"union_id": t["union_id"], "from": t["from"], "file": t.get("file", ""),
                            "section": t.get("section", ""), "into": t.get("into", ""), "why": t.get("why", "")})
    return {"winner": winner, "reason": doc.get("reason", ""), "ranking": doc.get("ranking") or [],
            "union": doc.get("union") or [], "transplants": transplants, "open_gaps": _gaps(doc.get("open_gaps"), "verdict")}


def validate_verify(doc, criteria):
    """The engine decides pass/fail from scores, gaps, probes and contradictions. Any 'pass' the judge
    wrote is ignored."""
    scores = {c: _score((doc.get("scores") or {}).get(c), "verify " + c) for c in criteria["ids"]}
    gaps = _gaps(doc.get("gaps"), "verify")
    probes = _probes(doc.get("probes"), "verify")
    fatal = _truthy(doc.get("fatal", False))
    low = [c for c in criteria["ids"] if scores[c] < criteria["threshold"]]
    blocking = [g for g in gaps if g["severity"] in BLOCKING]
    undefined = [p for p in probes if p["result"] == "UNDEFINED"]
    contradictions = list(doc.get("contradictions") or [])
    passed = not (fatal or low or blocking or undefined or contradictions)
    return {"total": total(scores, criteria, "verify"), "scores": scores, "fatal": fatal, "gaps": gaps,
            "probes": probes, "low": low, "undefined": undefined, "contradictions": contradictions, "pass": passed,
            "summary": doc.get("summary", "")}


def scan_markers(package_dir, markers=FORBIDDEN_MARKERS, files=PACKAGE_FILES):
    """Every unmade decision left in a package: [{file, line, marker, text}]."""
    hits = []
    patterns = [(m, re.compile(m, re.I)) for m in markers]
    for name in files:
        path = os.path.join(package_dir, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, start=1):
                for raw, pat in patterns:
                    if pat.search(line):
                        hits.append({"file": name, "line": lineno, "marker": raw, "text": line.strip()[:160]})
                        break
    return hits


def marker_gaps(hits):
    """The synthetic MAJOR gaps the engine adds for unmade decisions. The surgeon must decide, not defer."""
    return [{"union_id": None, "row": "%s:%d" % (h["file"], h["line"]), "question": "unmade decision",
             "severity": "MAJOR", "what": "left for the user instead of decided: %s" % h["text"],
             "fix": "decide it: write the value, the reasoning and how to change it in DECISIONS.md, and put the value in place"}
            for h in hits]


def fail_reason(result):
    parts = []
    if result["fatal"]:
        parts.append("fatal")
    if result["low"]:
        parts.append("low " + ",".join(result["low"]))
    blocking = [g for g in result["gaps"] if g["severity"] in BLOCKING]
    if blocking:
        parts.append("%d blocking gaps" % len(blocking))
    if result["undefined"]:
        parts.append("%d undefined probes" % len(result["undefined"]))
    if result["contradictions"]:
        parts.append("%d contradictions" % len(result["contradictions"]))
    if result.get("markers"):
        parts.append("%d unmade decisions left in the package" % len(result["markers"]))
    return "; ".join(parts) or "did not pass"
