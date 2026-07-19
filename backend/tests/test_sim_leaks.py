"""N7 — leak-by-spot read-model + the Simulate-only metric lock.

leak_by_spot ranks the hero's worst Simulate spot families (node_context x
position) over GRADED sim_decision rows, maps each to a Practice drill mode (or
None), respects min_sample, and reads SimDecision ONLY — a Practice drill_attempt
(incl. a source='simulate' one) never moves these numbers or the street report.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.db.migrate import run_migrations
from app.db.models import DrillAttempt, SimDecision
from app.db.session import get_session
from app.main import app
from app.services.sim_session import leak_by_spot, street_report

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'leaks.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


def _dec(session_id, node, pos, street, correctness, ev=0.0, ordinal=0):
    return SimDecision(
        owner_id="",
        session_id=session_id,
        sim_hand_id=1,
        street=street,
        ordinal=ordinal,
        chosen_action="call",
        correctness=correctness,
        ev_loss_bb=ev,
        coverage="full" if correctness else "unmappable",
        position=pos,
        node_context=node,
    )


def _seed(engine, rows):
    with Session(engine) as s:
        for i, r in enumerate(rows):
            r.ordinal = i
            s.add(r)
        s.commit()


def test_leak_ranking_worst_first_and_min_sample(engine):
    # Family A (BB, vs_cbet): 5 graded, 1 good -> rate 0.20 (worst).
    # Family B (BTN, rfi): 6 graded, 4 good -> rate 0.67.
    # Family C (CO, cbet): 3 graded -> below min_sample=5, dropped.
    rows = []
    rows += [_dec("s", "vs_cbet", "BB", "flop", "blunder", ev=2.0) for _ in range(4)]
    rows += [_dec("s", "vs_cbet", "BB", "flop", "optimal")]
    rows += [_dec("s", "rfi", "BTN", "preflop", "optimal") for _ in range(4)]
    rows += [_dec("s", "rfi", "BTN", "preflop", "mistake", ev=1.0) for _ in range(2)]
    rows += [_dec("s", "cbet", "CO", "flop", "mistake") for _ in range(3)]
    _seed(engine, rows)

    with Session(engine) as s:
        report = leak_by_spot(s, owner_id="")

    assert report.min_sample == 5
    assert [(r.node_context, r.position) for r in report.rows] == [
        ("vs_cbet", "BB"),  # rate 0.20, worst
        ("rfi", "BTN"),  # rate 0.67
    ]
    worst = report.rows[0]
    assert worst.graded == 5 and worst.good == 1 and worst.good_rate == 0.2
    assert worst.drill_mode == "vs_cbet"  # node maps to a real Practice mode
    assert worst.node_label == "BB · facing a c-bet"


def test_turn_river_families_have_no_drill_mode(engine):
    rows = [_dec("s", "turn_barrel", "BTN", "turn", "mistake", ev=1.0) for _ in range(5)]
    _seed(engine, rows)
    with Session(engine) as s:
        report = leak_by_spot(s, owner_id="")
    assert len(report.rows) == 1
    assert report.rows[0].drill_mode is None  # "Simulate only" — no Practice drill


def test_unmappable_and_null_node_rows_excluded(engine):
    # Graded rows with node_context=None (defensive) + no-baseline rows must not
    # form groups. Only the mapped graded family survives.
    rows = [_dec("s", "vs_cbet", "BB", "flop", "optimal") for _ in range(5)]
    rows += [_dec("s", None, "BB", "flop", "optimal") for _ in range(5)]  # null node
    rows += [_dec("s", None, "BB", "flop", None) for _ in range(5)]  # no-baseline
    _seed(engine, rows)
    with Session(engine) as s:
        report = leak_by_spot(s, owner_id="")
    assert [(r.node_context, r.position) for r in report.rows] == [("vs_cbet", "BB")]


def test_metric_lock_practice_rows_dont_move_leaks_or_streets(engine):
    # The Simulate-only lock (N7 decision B): a Practice drill_attempt — even one
    # tagged source='simulate' — must not enter the leak report OR the street
    # report. Both read SimDecision only.
    sim_rows = [_dec("s", "vs_cbet", "BB", "flop", "blunder", ev=2.0) for _ in range(5)]
    _seed(engine, sim_rows)
    with Session(engine) as s:
        leaks_before = leak_by_spot(s, owner_id="")
        streets_before = street_report(s, owner_id="")
        s.add(
            DrillAttempt(
                spot_signature="x", chosen_action="fold", provider="h", source="practice"
            )
        )
        s.add(
            DrillAttempt(
                spot_signature="y", chosen_action="fold", provider="h", source="simulate"
            )
        )
        s.commit()
        leaks_after = leak_by_spot(s, owner_id="")
        streets_after = street_report(s, owner_id="")

    assert leaks_before.model_dump() == leaks_after.model_dump()
    assert streets_before.model_dump() == streets_after.model_dump()


@pytest.fixture
def client(engine):
    def _override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_leak_report_endpoint(client, engine):
    rows = [_dec("s", "vs_cbet", "BB", "flop", "mistake", ev=1.0) for _ in range(5)]
    _seed(engine, rows)
    r = client.get("/api/v1/simulate/report/leaks")
    assert r.status_code == 200
    body = r.json()
    assert body["min_sample"] == 5
    assert body["rows"][0]["node_context"] == "vs_cbet"
    assert body["rows"][0]["drill_mode"] == "vs_cbet"


def test_leak_report_empty_below_threshold(client, engine):
    rows = [_dec("s", "vs_cbet", "BB", "flop", "mistake") for _ in range(3)]
    _seed(engine, rows)
    r = client.get("/api/v1/simulate/report/leaks")
    assert r.status_code == 200
    assert r.json()["rows"] == []
