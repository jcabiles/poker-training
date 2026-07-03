"""HeuristicProvider — grades preflop spots from the content packs.

Looks up the node-aware entry and delegates to the frequency-tolerant grading
engine. The async interface + freq+EV+coverage results are unchanged, so a
SolverTableProvider drops in later with no downstream changes.
"""

from __future__ import annotations

from app.domain.action import Decision
from app.domain.content.models import Entry
from app.domain.content.registry import lookup
from app.domain.evaluation import Coverage, EvaluationResult
from app.domain.grading import grade
from app.domain.spot import Spot, Street


class HeuristicProvider:
    name = "heuristic"

    def __init__(self, index: dict[tuple, Entry]):
        self._index = index

    def _entry(self, spot: Spot) -> Entry | None:
        return lookup(self._index, spot)

    def _baseline_entry(self, spot: Spot) -> Entry | None:
        """The same node with villain_type=None — for the GTO-vs-exploit contrast."""
        return lookup(self._index, spot, villain_type=None)

    async def supports(self, spot: Spot) -> bool:
        return spot.street == Street.PREFLOP and self._entry(spot) is not None

    async def optimal(self, spot: Spot) -> EvaluationResult:
        return self._grade(spot, None)

    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult:
        return self._grade(spot, action)

    def _grade(self, spot: Spot, decision: Decision | None) -> EvaluationResult:
        entry = self._entry(spot)
        result = grade(spot, entry, decision)
        if entry is None:
            result.coverage = Coverage.NOT_FOUND  # no content; heuristic fold-default applied
        elif spot.villain_type is not None:
            self._enrich_exploit(spot, entry, result)
        return result

    def _enrich_exploit(self, spot: Spot, entry: Entry, result: EvaluationResult) -> None:
        """Add the GTO-vs-exploit contrast + rationale. Degrades gracefully if no baseline."""
        result.rationale_tags = [*result.rationale_tags, "exploit"]
        parts = [result.explanation]
        baseline = self._baseline_entry(spot)
        if baseline is not None:
            base_top = grade(spot, baseline, None).best_action.action.value
            if base_top != result.best_action.action.value:
                parts.append(f"(baseline: {base_top})")
        if entry.rationale:
            parts.append(entry.rationale)
            # Raw material for the tier composer (compose_tiers reads this field
            # instead of re-parsing the flat explanation — no double-append).
            result.authored_rationale = entry.rationale
        result.explanation = " ".join(parts)
