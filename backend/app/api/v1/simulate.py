"""Simulate endpoints.

POST /simulate/session               -> create a session + deal hand 1.
POST /simulate/session/{id}/hand     -> advance the button one seat, deal
                                         the next hand.

Table-walking skeleton only: no betting, chips, or persistence. Sessions
live in a module-level dict (mirrors `drill.py`'s singleton precedent) and
are lost on restart — accepted for S1. Per-hand seeding is independent of
`drill.py`'s shared `_RNG`: `random.Random(secrets.randbits(256))`, seed
logged server-side, never on the wire (see
`docs/ai-dlc/specs/simulate-s1.md`).
"""

from __future__ import annotations

import logging
import random
import secrets
import uuid
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException

from app.domain.spot import Hero, PlayerState
from app.domain.table import deal_hand, positions_for_button
from app.schemas.simulate import SimulateHandView, SimulateSessionResponse

router = APIRouter(prefix="/simulate", tags=["simulate"])

logger = logging.getLogger(__name__)

_SEATS = 9
_STACK_BB = 100.0


@dataclass
class SimSession:
    button_seat: int
    hand_no: int
    seed: int  # most recently dealt hand's seed, kept server-side only


_SESSIONS: dict[str, SimSession] = {}


def _deal_and_build(session_id: str, session: SimSession) -> SimulateHandView:
    seed = secrets.randbits(256)
    session.seed = seed
    logger.info(
        "simulate hand seed session=%s hand=%s seed=%s",
        session_id,
        session.hand_no,
        seed,
    )
    rng = random.Random(seed)
    dealt = deal_hand(rng)
    positions = positions_for_button(session.button_seat)

    players = [
        PlayerState(
            position=positions[seat],
            stack_bb=_STACK_BB,
            is_hero=(seat == 0),
        )
        for seat in range(_SEATS)
    ]
    hero = Hero(
        position=positions[0],
        hole_cards=dealt.hole_cards[0],
        stack_bb=_STACK_BB,
    )
    return SimulateHandView(hand_no=session.hand_no, players=players, hero=hero)


@router.post("/session", response_model=SimulateSessionResponse)
async def create_session() -> SimulateSessionResponse:
    session_id = uuid.uuid4().hex
    session = SimSession(button_seat=secrets.randbelow(_SEATS), hand_no=1, seed=0)
    _SESSIONS[session_id] = session
    hand = _deal_and_build(session_id, session)
    return SimulateSessionResponse(session_id=session_id, hand=hand)


@router.post("/session/{session_id}/hand", response_model=SimulateHandView)
async def next_hand(session_id: str) -> SimulateHandView:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    session.button_seat = (session.button_seat + 1) % _SEATS
    session.hand_no += 1
    return _deal_and_build(session_id, session)
