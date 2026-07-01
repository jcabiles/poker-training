import pytest
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt
from app.services.stats import M_MAX, M_MIN, hand_error_weights


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 's.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


def _attempt(hand_class, loss, cat=100):
    return DrillAttempt(
        spot_signature="sig",
        leak_category=cat,
        chosen_action="raise",
        correctness="optimal",
        ev_loss_bb=loss,
        provider="heuristic",
        hand_class=hand_class,
    )


def test_empty_db_returns_empty_dict(engine):
    with Session(engine) as s:
        weights = hand_error_weights(s)
    assert weights == {}


def test_heavy_errors_on_one_class_get_the_highest_weight(engine):
    with Session(engine) as s:
        # KJo: 6 attempts, consistently large EV-loss (a real leak).
        s.add_all([_attempt("KJo", 3.0) for _ in range(6)])
        # Two other classes: 6 attempts each, small/no EV-loss.
        s.add_all([_attempt("AKo", 0.1) for _ in range(6)])
        s.add_all([_attempt("77", 0.2) for _ in range(6)])
        s.commit()
        weights = hand_error_weights(s)

    assert set(weights) == {"KJo", "AKo", "77"}
    assert weights["KJo"] == max(weights.values())
    assert weights["KJo"] > 1.0
    for w in weights.values():
        assert M_MIN <= w <= M_MAX


def test_class_below_min_n_is_omitted(engine):
    with Session(engine) as s:
        # KJo: only 4 attempts — below MIN_N (5), must be omitted.
        s.add_all([_attempt("KJo", 5.0) for _ in range(4)])
        # AKo: 5 attempts — meets MIN_N, included.
        s.add_all([_attempt("AKo", 0.1) for _ in range(5)])
        s.commit()
        weights = hand_error_weights(s)

    assert "KJo" not in weights
    assert "AKo" in weights


def test_non_rfi_attempts_are_excluded(engine):
    with Session(engine) as s:
        # Non-RFI leak category (VS_3BET_IP = 120) — must not contribute.
        s.add_all([_attempt("KJo", 5.0, cat=120) for _ in range(6)])
        s.commit()
        weights = hand_error_weights(s)

    assert weights == {}


def test_all_equal_ev_loss_is_neutral(engine):
    with Session(engine) as s:
        s.add_all([_attempt("AKo", 1.0) for _ in range(5)])
        s.add_all([_attempt("77", 1.0) for _ in range(5)])
        s.commit()
        weights = hand_error_weights(s)

    assert weights == {"AKo": 1.0, "77": 1.0}


def test_single_qualifying_class_is_neutral(engine):
    with Session(engine) as s:
        s.add_all([_attempt("KJo", 9.0) for _ in range(6)])
        s.commit()
        weights = hand_error_weights(s)

    assert weights == {"KJo": 1.0}
