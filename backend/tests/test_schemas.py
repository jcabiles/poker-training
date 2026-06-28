import pytest
from pydantic import ValidationError

from app.domain.action import Decision
from app.domain.evaluation import (
    ActionEval,
    Coverage,
    EvaluationResult,
    ProviderKind,
)
from app.domain.spot import ActionType, Hero, Position, Spot


def test_spot_roundtrips(rfi_spot):
    dumped = rfi_spot.model_dump()
    rebuilt = Spot.model_validate(dumped)
    assert rebuilt == rfi_spot


def test_invalid_card_rejected():
    with pytest.raises(ValidationError):
        Hero(position=Position.CO, hole_cards=("Zx", "Ks"), stack_bb=100.0)


def test_decision_requires_size_for_raise():
    with pytest.raises(ValidationError):
        Decision(action=ActionType.RAISE)  # no size
    Decision(action=ActionType.RAISE, size_bb=3.0)  # ok
    Decision(action=ActionType.FOLD)  # ok, no size needed


def test_frequency_bounds_enforced():
    with pytest.raises(ValidationError):
        ActionEval(action=ActionType.RAISE, frequency=1.5, ev_bb=0.0)


def test_evaluation_result_minimal():
    best = ActionEval(action=ActionType.RAISE, size_bb=2.5, frequency=1.0, ev_bb=1.2)
    result = EvaluationResult(
        per_action=[best],
        best_action=best,
        provider=ProviderKind.HEURISTIC,
    )
    assert result.coverage == Coverage.FULL
    assert result.chosen_eval is None  # optimal()-style result
    assert result.solver_node_key is None
    assert result.is_mixed is False


def test_new_spot_fields_default(rfi_spot):
    assert rfi_spot.facing is None
    assert rfi_spot.limper_count == 0
