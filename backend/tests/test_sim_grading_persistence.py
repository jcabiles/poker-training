"""S10 persistence battery: migration 0010 up/down, source-tagging, and the
Practice-stats source filter (contracts/simulate-s10-s11.md hazard #2:
`stats.py` corruption if tagged sim rows land without a filter on all five
reads). Spec: docs/ai-dlc/specs/simulate-s10.md.

Some tests below exercise T1's grade wire (`sim_session.apply_hero_action`
writing `SimDecision`/tagged `DrillAttempt` rows) indirectly by inserting rows
that mimic what that wire will produce, since T1 lands concurrently with this
file. The zero-SRS-rows test drives the real service entry point and must
hold both before and after T1 lands.

NULL-source semantics: on SQLite, migration 0010's `ADD COLUMN ... server_default
'practice'` backfills pre-existing `drill_attempt` rows with the literal
'practice' string (verified below), not SQL NULL. The `source` column is still
nullable at the schema level, so the Practice-stats filter in `stats.py`
treats an explicit NULL the same as 'practice' defensively (belt and
suspenders) — exercised via `_seed_practice_and_sim_rows` below.
"""

from __future__ import annotations

import asyncio
import random
from datetime import date

import pytest
from sqlalchemy import text
from sqlmodel import Session, create_engine, select

from alembic import command
from app.db.migrate import make_alembic_config, run_migrations
from app.db.models import DrillAttempt, SimDecision, SimHand, SimSeat, SimSession, SRSItemRow
from app.domain.action import Decision
from app.domain.spot import ActionType
from app.domain.table.deck import deal_hand
from app.domain.table.engine import start_hand
from app.services.sim_session import apply_hero_action, create_session, deal_next_hand
from app.services.stats import calendar, hand_error_weights, leak_stats, recap, summary

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture
def engine(tmp_path):
    url = f"sqlite:///{tmp_path / 's.db'}"
    run_migrations(url)
    return create_engine(url, connect_args={"check_same_thread": False})


def _attempt(source, cat=100, correctness="blunder", loss=3.0, hand_class=None):
    return DrillAttempt(
        spot_signature="sig",
        leak_category=cat,
        chosen_action="raise",
        correctness=correctness,
        ev_loss_bb=loss,
        provider="heuristic",
        hand_class=hand_class,
        source=source,
    )


# --------------------------------------------------------- migration 0010


def test_migration_0010_up_down_clean_and_existing_rows_read_back_unchanged(tmp_path):
    url = f"sqlite:///{tmp_path / 'mig.db'}"
    cfg = make_alembic_config(url)

    # Land on 0009 (pre-S10), insert a practice row the old schema's way (no
    # `source` column exists yet at this revision).
    command.upgrade(cfg, "0009")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO drill_attempt "
                "(owner_id, spot_signature, chosen_action, ev_loss_bb, provider, created_at) "
                "VALUES ('', 'presig', 'raise', 1.0, 'heuristic', '2026-01-01 00:00:00')"
            )
        )
    engine.dispose()

    # Up to head (0010): additive migration must not disturb the pre-existing row.
    # On SQLite, ADD COLUMN ... DEFAULT backfills existing rows with the
    # literal default ('practice') rather than leaving them NULL — verified
    # directly against the raw column value below (not the ORM's Python
    # default, which would mask a backfill gap).
    command.upgrade(cfg, "head")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT source, chosen_action, ev_loss_bb FROM drill_attempt "
                 "WHERE spot_signature='presig'")
        ).fetchone()
        assert row == ("practice", "raise", 1.0)
    engine.dispose()

    # Down to 0009: drops sim_decision + source column, must not error.
    command.downgrade(cfg, "0009")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(drill_attempt)")).fetchall()
        }
        assert "source" not in cols
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        assert "sim_decision" not in tables
    engine.dispose()

    # Back up to head: must re-apply clean.
    command.upgrade(cfg, "head")
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT source FROM drill_attempt WHERE spot_signature='presig'")
        ).fetchone()
        assert row == ("practice",)
    engine.dispose()


# --------------------------------------------------------- zero SRS rows


def _fold_or_check_decision(view) -> Decision:
    kinds = {la.action for la in view.hand.legal_actions}
    if ActionType.CHECK in kinds:
        return Decision(action=ActionType.CHECK)
    if ActionType.CALL in kinds:
        return Decision(action=ActionType.CALL)
    return Decision(action=ActionType.FOLD)


def test_simulate_session_creates_zero_srs_rows(engine):
    with Session(engine) as s:
        view = create_session(s)
        guard = 0
        while guard < 300:
            guard += 1
            if view.hand.hand_over:
                view = deal_next_hand(s, view.session_id)
                continue
            assert view.hand.is_hero_turn
            # apply_hero_action went async in S10 T1 (awaits the grading provider).
            view = asyncio.run(
                apply_hero_action(s, view.session_id, _fold_or_check_decision(view))
            )
        srs_rows = list(s.exec(select(SRSItemRow)))
        assert srs_rows == []


# --------------------------------------------------------- source tagging


def _make_session_hand(s: Session) -> tuple[str, int]:
    """Minimal SimSession + SimHand rows to satisfy SimDecision FKs."""
    dealt = deal_hand(random.Random(1))
    state = start_hand(dealt, button_seat=0, stacks_bb=[100.0] * 9)
    session = SimSession(id="sess1", button_seat=0, hand_no=1)
    s.add(session)
    for i in range(9):
        s.add(
            SimSeat(
                session_id="sess1",
                seat_index=i,
                is_hero=i == 0,
                persona_type=None if i == 0 else "tag",
                stack_bb=100.0,
                buyins_bb=100.0,
            )
        )
    hand = SimHand(
        session_id="sess1",
        hand_no=1,
        button_seat=0,
        rng_seed="1",
        state_json=state.model_dump_json(),
    )
    s.add(hand)
    s.commit()
    s.refresh(hand)
    return session.id, hand.id


def test_graded_sim_decision_produces_tagged_drill_attempt_queryable_by_source(engine):
    with Session(engine) as s:
        session_id, hand_id = _make_session_hand(s)
        s.add(
            SimDecision(
                session_id=session_id,
                sim_hand_id=hand_id,
                street="preflop",
                ordinal=0,
                chosen_action="raise",
                correctness="blunder",
                ev_loss_bb=4.0,
                leak_category=100,
                coverage="full",
            )
        )
        s.add(
            DrillAttempt(
                spot_signature="sim-sig",
                leak_category=100,
                chosen_action="raise",
                correctness="blunder",
                ev_loss_bb=4.0,
                provider="heuristic",
                source="simulate",
            )
        )
        s.commit()

        sim_rows = list(s.exec(select(DrillAttempt).where(DrillAttempt.source == "simulate")))
        assert len(sim_rows) == 1
        assert sim_rows[0].spot_signature == "sim-sig"

        sim_decisions = list(
            s.exec(select(SimDecision).where(SimDecision.session_id == session_id))
        )
        assert len(sim_decisions) == 1
        assert sim_decisions[0].coverage == "full"


# --------------------------------------------------- stats source filter


_SIM_LEAK_CAT = 101  # RFI_MP — distinctive category used only by the sim-tagged row


def _seed_practice_and_sim_rows(s: Session):
    """One practice row, one explicit-NULL-source row, one sim row — all
    sharing the distinctive _SIM_LEAK_CAT so a leaked sim row is obvious in
    any of the five reads' output.

    The NULL row models any row that ends up with a SQL NULL `source` (belt
    and suspenders: on SQLite the 0010 backfill actually writes 'practice'
    into pre-existing rows — see test_migration_0010_* — but the `source`
    column is nullable at the schema level, so a NULL value must still be
    treated as 'practice' rather than silently excluded).
    """
    s.add_all(
        [
            _attempt("practice", cat=_SIM_LEAK_CAT, hand_class="AJo"),
            _attempt(None, cat=_SIM_LEAK_CAT, hand_class="AJo"),
            _attempt("simulate", cat=_SIM_LEAK_CAT, hand_class="AJo"),
        ]
    )
    s.commit()


def test_leak_stats_excludes_simulate_source(engine):
    with Session(engine) as s:
        _seed_practice_and_sim_rows(s)
        out = leak_stats(s)
    row = next(r for r in out if r["category"] == _SIM_LEAK_CAT)
    assert row["attempts"] == 2  # practice + NULL-source, not the simulate row


def test_summary_excludes_simulate_source(engine):
    with Session(engine) as s:
        _seed_practice_and_sim_rows(s)
        out = summary(s)
    assert out["total_attempts"] == 2


def test_calendar_excludes_simulate_source(engine):
    with Session(engine) as s:
        _seed_practice_and_sim_rows(s)
        days = calendar(s, weeks=1)
    today_entry = next(d for d in days if d["date"] == date.today().isoformat())
    assert today_entry["attempts"] == 2


def test_recap_excludes_simulate_source(engine):
    with Session(engine) as s:
        _seed_practice_and_sim_rows(s)
        out = recap(s)
    assert out["hands"] == 2


def test_hand_error_weights_excludes_simulate_source(engine):
    # hand_error_weights requires MIN_N=5 attempts per hand_class to surface a
    # signal; seed 5 practice/NULL rows for "AJo" plus 5 simulate rows for a
    # *different* hand_class so a leak would show up as an extra qualifying
    # class rather than silently folding into "AJo"'s mean.
    with Session(engine) as s:
        for _ in range(3):
            s.add(_attempt("practice", cat=100, loss=1.0, hand_class="AJo"))
        for _ in range(2):
            s.add(_attempt(None, cat=100, loss=1.0, hand_class="AJo"))
        for _ in range(5):
            s.add(_attempt("simulate", cat=100, loss=9.0, hand_class="72o"))
        s.commit()
        out = hand_error_weights(s)
    assert "AJo" in out
    assert "72o" not in out


def test_practice_and_null_source_rows_still_appear_in_all_five_reads(engine):
    with Session(engine) as s:
        _seed_practice_and_sim_rows(s)
        assert any(r["category"] == _SIM_LEAK_CAT and r["attempts"] == 2 for r in leak_stats(s))
        assert summary(s)["total_attempts"] == 2
        days = calendar(s, weeks=1)
        today_entry = next(d for d in days if d["date"] == date.today().isoformat())
        assert today_entry["attempts"] == 2
        assert recap(s)["hands"] == 2
