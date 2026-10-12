"""Reads what the judges wrote, checks it, and does the arithmetic. Judges never compute totals."""
import json
import os

from . import ArenaError, SKILL_DIR

LENSES_PATH = os.path.join(SKILL_DIR, "lenses.json")
SEVERITIES = ("FATAL", "MAJOR", "MINOR")
BLOCKING = ("FATAL", "MAJOR")


def load_lenses(path=LENSES_PATH):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    lenses = doc.get("lenses") or []
    if not lenses:
        raise ArenaError("lenses.json has no lenses")
    if sum(l["weight"] for l in lenses) != 100:
        raise ArenaError("lens weights must sum to 100")
    return {"ids": [l["id"] for l in lenses], "names": {l["id"]: l["name"] for l in lenses},
            "weights": {l["id"]: l["weight"] for l in lenses}, "threshold": doc.get("pass_threshold", 7)}


def _score(value, where):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ArenaError("%s: score %r is not a number" % (where, value))
    if not 0 <= v <= 10:
        raise ArenaError("%s: score %s is outside 0..10" % (where, v))
    return v


def lens_total(scores, lenses, where):
    """Weighted 0..100 total. Every lens must be present."""
    missing = [l for l in lenses["ids"] if l not in scores]
    if missing:
        raise ArenaError("%s: missing lens scores %s" % (where, ", ".join(missing)))
    return round(sum(_score(scores[l], where + " lens " + l) * lenses["weights"][l] for l in lenses["ids"]) / 10, 1)


def _truthy(v):
    return v is True or str(v).strip().lower() in ("true", "yes", "1")


def _gaps(raw, where):
    gaps = []
    for g in raw or []:
        sev = str(g.get("severity", "MINOR")).upper()
        if sev not in SEVERITIES:
            raise ArenaError("%s: gap severity %r must be one of %s" % (where, sev, "/".join(SEVERITIES)))
        gaps.append({"lens": g.get("lens", "?"), "severity": sev, "what": g.get("what", ""), "fix": g.get("fix", "")})
    return gaps


def validate_audit(doc, gid, expected, lenses):
    """Normalised group audit: entries with computed totals, and the best-part inventory."""
    where = "audit " + gid
    entries = doc.get("entries")
    if not isinstance(entries, dict):
        raise ArenaError("%s: 'entries' must be an object keyed by competitor id" % where)
    missing = [a for a in expected if a not in entries]
    if missing:
        raise ArenaError("%s: no scores for %s" % (where, ", ".join(missing)))
    out = {}
    for aid in expected:
        e = entries[aid]
        scores = e.get("scores") or {}
        out[aid] = {"scores": {l: _score(scores.get(l), "%s %s" % (where, aid)) for l in lenses["ids"]},
                    "total": lens_total(scores, lenses, "%s %s" % (where, aid)),
                    "fatal": _truthy(e.get("fatal", False)), "fatal_reason": e.get("fatal_reason", ""),
                    "gaps": _gaps(e.get("gaps"), "%s %s" % (where, aid)), "notes": e.get("notes", "")}
    best = {}
    for lens, part in (doc.get("best_parts") or {}).items():
        if isinstance(part, dict) and part.get("entry") in expected:
            best[lens] = {"entry": part["entry"], "section": part.get("section", ""), "why": part.get("why", "")}
    return {"group": gid, "entries": out, "best_parts": best}


def rank_group(audit):
    """Entries of one group, best first: non-fatal before fatal, then total."""
    items = [(aid, e) for aid, e in audit["entries"].items()]
    items.sort(key=lambda kv: (kv[1]["fatal"], -kv[1]["total"], kv[0]))
    return [{"id": aid, "group": audit["group"], "group_rank": i + 1, "total": e["total"], "fatal": e["fatal"]}
            for i, (aid, e) in enumerate(items)]


def rank_all(audits):
    """Global order: group rank first (judges drift between groups), then raw total."""
    rows = []
    for audit in audits:
        rows.extend(rank_group(audit))
    rows.sort(key=lambda r: (r["fatal"], r["group_rank"], -r["total"], r["id"]))
    return rows


def shortlist(ranking, k):
    return [r for r in ranking if not r["fatal"]][:k] or ranking[:k]


def best_parts_index(audits):
    """lens -> list of {entry, section, why, group}, one per group that named one."""
    index = {}
    for audit in audits:
        for lens, part in audit["best_parts"].items():
            index.setdefault(lens, []).append(dict(part, group=audit["group"]))
    return index


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
        transplants.append({"from": t["from"], "lens": t.get("lens", "?"), "section": t.get("section", ""),
                            "into": t.get("into", ""), "why": t.get("why", "")})
    return {"winner": winner, "reason": doc.get("reason", ""), "ranking": doc.get("ranking") or [],
            "transplants": transplants, "open_gaps": _gaps(doc.get("open_gaps"), "verdict")}


def validate_verify(doc, lenses):
    """The engine decides pass/fail from the scores and gaps; the judge's own 'pass' is ignored."""
    scores = doc.get("scores") or {}
    total = lens_total(scores, lenses, "verify")
    gaps = _gaps(doc.get("gaps"), "verify")
    fatal = _truthy(doc.get("fatal", False))
    low = [l for l in lenses["ids"] if _score(scores[l], "verify") < lenses["threshold"]]
    blocking = [g for g in gaps if g["severity"] in BLOCKING]
    contradictions = list(doc.get("contradictions") or [])
    passed = not fatal and not low and not blocking and not contradictions
    return {"total": total, "scores": {l: _score(scores[l], "verify") for l in lenses["ids"]}, "fatal": fatal,
            "gaps": gaps, "low_lenses": low, "contradictions": contradictions, "pass": passed}


def validate_build_verdict(doc, builder_ids):
    winner = doc.get("winner")
    if winner not in builder_ids:
        raise ArenaError("build verdict: winner %r is not a builder id" % winner)
    checks = doc.get("hard_checks") or {}
    missing = [b for b in builder_ids if b not in checks]
    if missing:
        raise ArenaError("build verdict: no hard_checks for %s" % ", ".join(missing))
    w = checks[winner]
    if not all(_truthy(w.get(k, False)) for k in ("installs", "tests_pass")):
        raise ArenaError("build verdict: the winner must install and pass its tests; %s does not" % winner)
    transplants = []
    for t in doc.get("transplants") or []:
        if t.get("from") not in builder_ids or t["from"] == winner:
            raise ArenaError("build verdict: bad transplant source %r" % t.get("from"))
        transplants.append({"from": t["from"], "path": t.get("path", ""), "why": t.get("why", "")})
    return {"winner": winner, "reason": doc.get("reason", ""), "hard_checks": checks,
            "transplants": transplants, "open_gaps": _gaps(doc.get("open_gaps"), "build verdict")}
