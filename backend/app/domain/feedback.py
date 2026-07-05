"""Tiered teaching feedback — verdict / reasoning / deep-dive (N1).

`compose_tiers` is a pure post-processing pass over ANY StrategyProvider's
EvaluationResult (mounted by providers/tiered.py::TieredFeedbackProvider), so a
future solver provider inherits the teaching layer for free.

It composes ONLY from data already on the result (correctness, chosen_eval,
per_action, rationale_tags, authored_rationale, coverage, is_mixed) plus the
spot. It authors NO new content-pack prose (that is slice N3) — where authored
rationale is missing it builds the best non-tautological reasoning it can from
the rationale tags. EVs are formatted with the "≈" approximate convention.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.evaluation import (
    ActionEval,
    Correctness,
    Coverage,
    EvaluationResult,
    FeedbackTiers,
)
from app.domain.spot import Spot

# --- Preflop mistake-shape tags (grading.py::_tags) -> mechanism phrases ---
_PRE_SHAPE = {
    "correct": "This matches the chart's line for this hand at this node.",
    "chart": "The chart drives this node — the recommended mix is range-based, not read-based.",
    "over_fold": (
        "Folding surrenders a hand the chart plays here — it sits above the "
        "range's edge, so the fold gives up EV outright."
    ),
    "over_aggressive": (
        "Raising puts money in with a hand outside the raising range at this "
        "node — the aggression isn't backed by enough value or fold equity."
    ),
    "under_aggressive": (
        "Playing passively misses value: the chart prefers raising this hand, "
        "and the passive line lets the opponent realize equity cheaply."
    ),
    "loose_call": (
        "Calling with a hand below the edge of the continuing range loses "
        "money against this opening range."
    ),
    "off_chart": "This action isn't part of the chart's mix at this node.",
}

# --- Postflop 4-wide tags [node, adv, cat, wetness] (postflop.py) -> clauses ---
_NODE = {
    "cbet": "You're the preflop aggressor deciding whether to c-bet",
    "vs_cbet": "You're defending against a c-bet",
    "vs_check_raise": "Your c-bet just got check-raised — fresh strength information",
}
_ADV = {
    "hero": "the range advantage is yours, so betting pressure is credible",
    "villain": "this board favors your opponent's range, so tread carefully",
    "neutral": "neither range has a clear edge on this board",
    "defender": "your calling range connects with this board better than the bettor's",
    "aggressor": "the bettor's range hits this board harder than yours",
}
_CAT = {
    "strong": "A strong hand wants to build the pot while worse hands can pay",
    "weak_made": (
        "A marginal made hand plays best by controlling the pot and bluff-catching selectively"
    ),
    "draw": "A draw has real equity to realize and can double as a semi-bluff",
    "air": "With no pair and no draw, avoid bloating the pot without fold equity",
}
_WET = {
    "dry": "Dry boards change little on later streets, favoring small, frequent bets",
    "medium": "This medium texture leaves both ranges live, so balance matters",
    "wet": "Wet boards shift fast — sizing polarizes and raises demand respect",
}


def _pct(freq: float) -> str:
    return f"{round(freq * 100)}%"


def _ev(ev_bb: float) -> str:
    return f"≈{ev_bb}bb"  # matches the FE's approximate-EV convention


def _fmt(e: ActionEval) -> str:
    return f"{e.action.value} {e.size_bb}bb" if e.size_bb else e.action.value


def _verdict(result: EvaluationResult, decision: Decision | None) -> str:
    """One short plain-language lede. Numeric freq/EV detail lives in the FE's
    EV-comparison block and the deep-dive tier, not here (F2.6)."""
    if result.coverage == Coverage.NOT_FOUND:
        return "No strategy content covers this spot yet, so it was graded by a fallback."
    best = result.best_action
    if decision is None or result.chosen_eval is None:
        return f"Best play: {_fmt(best)}."
    if result.correctness == Correctness.OPTIMAL:
        return f"Optimal — {decision.action.value} is the best line here."
    label = (result.correctness or Correctness.ACCEPTABLE).value.capitalize()
    return f"{label} — you chose {decision.action.value}; {_fmt(best)} earns more here."


def _reasoning(spot: Spot, result: EvaluationResult) -> str:
    """Authored, hand-specific rationale is always sentence 1 (the lede) — in
    the postflop tag-branch, the preflop shape-branch, AND the exploit-villain
    branch — with the tag-derived mechanism template following (F2.7/R3)."""
    if result.coverage == Coverage.NOT_FOUND:
        return "No reasoning is available — this spot is outside the current strategy content."
    tags = result.rationale_tags
    parts: list[str] = []
    exploit = "exploit" in tags and spot.villain_type is not None
    if exploit:
        # exploit lede first: the villain-specific sentence IS the hand-specific
        # rationale here (authored_rationale is consumed by this lede, so the
        # branches below must not repeat it).
        villain = spot.villain_type.value.replace("_", " ")
        if result.authored_rationale:
            parts.append(f"Versus a {villain}: {result.authored_rationale}")
        else:
            parts.append(
                f"This is an exploit adjustment versus a {villain}, "
                f"shifted from the baseline chart."
            )
    elif result.authored_rationale:
        # N3 authored content (preflop baseline or postflop node) leads.
        parts.append(result.authored_rationale)
    if tags and tags[0] in _NODE and len(tags) >= 4:
        node, adv, cat, wet = tags[0], tags[1], tags[2], tags[3]
        parts.append(
            f"{_NODE[node]} on a {wet} board: "
            f"{_ADV.get(adv, 'range advantage unclear')}. "
            f"{_CAT.get(cat, 'Hand category unclear')}. "
            f"{_WET.get(wet, '')}".rstrip()
            + "."
        )
    else:
        shape = next((t for t in tags if t in _PRE_SHAPE), None)
        if shape is not None:
            parts.append(_PRE_SHAPE[shape])
        if result.is_mixed:
            parts.append(
                "This is a genuinely mixed node — the chart plays more than one "
                "action at meaningful frequency, so the overall mix matters more "
                "than any single rep."
            )
        else:
            best = result.best_action
            parts.append(
                f"The chart's line here is essentially pure: "
                f"{_fmt(best)} at {_pct(best.frequency)}."
            )
    return " ".join(parts)


def _deep_dive(result: EvaluationResult, decision: Decision | None) -> str:
    if result.coverage == Coverage.NOT_FOUND:
        return "No per-action data for this spot — fallback grading only."
    mix = " · ".join(
        f"{_fmt(e)} {_pct(e.frequency)} (EV {_ev(e.ev_bb)})" for e in result.per_action
    )
    parts = [f"Full mix: {mix}."]
    if result.is_mixed:
        parts.append("Mixed node: two or more actions are played at meaningful frequency.")
    if decision is not None and result.chosen_eval is not None:
        parts.append(f"Your action gave up {_ev(result.ev_loss_bb)} against the best line.")
    parts.append(
        f"Coverage: {result.coverage.value} · graded by the {result.provider.value} provider."
    )
    return " ".join(parts)


def compose_tiers(
    spot: Spot, result: EvaluationResult, decision: Decision | None = None
) -> FeedbackTiers:
    """Compose the verdict/reasoning/deep-dive tiers for a graded result."""
    return FeedbackTiers(
        verdict=_verdict(result, decision),
        reasoning=_reasoning(spot, result),
        deep_dive=_deep_dive(result, decision),
    )
