"""Drill endpoints.

GET  /drill/next?mode=<mode> -> a Spot to solve.
     modes: random|review|leak_focus|exploit|postflop|vs_cbet|vs_check_raise|challenge
            |rfi|vs_rfi|blind_defense|vs_limpers|vs_3bet (preflop-family path nodes)
POST /drill/grade -> grade via the StrategyProvider, persist the attempt, update SM-2.
GET  /drill/quiz/next?kind=texture|equity|random -> a foundational quiz item.
POST /drill/quiz/grade -> grade a quiz answer, persist it (provider="quiz").
"""

from __future__ import annotations

import random

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db.models import DrillAttempt
from app.db.session import get_session
from app.domain.archetypes import VillainType
from app.domain.challenge import sample_challenge_spot
from app.domain.content.notation import hole_cards_to_class
from app.domain.content.registry import build_index, load_preflop_packs, lookup
from app.domain.equity import combos_for_range, equity_vs_range
from app.domain.evaluation import EvaluationResult
from app.domain.grading import archetype_leak, leak_category_for, range_grid
from app.domain.leaks import LeakCategory
from app.domain.providers import get_provider
from app.domain.scenarios import (
    _DEPTHS,
    build_cbet_spot,
    build_check_raise_spot,
    build_spot,
    build_vs_cbet_spot,
    sample_cbet_spot,
    sample_check_raise_spot,
    sample_exploit_spot,
    sample_spot,
    sample_vs_cbet_spot,
)
from app.domain.spot import NodeContext, Position, Spot, Street
from app.domain.srs import faced_bet_bucket, spot_signature, spr_bucket
from app.domain.texture import classify
from app.schemas.drill import (
    GradeRequest,
    NextDrillResponse,
    QuizAnswer,
    QuizItem,
    QuizResult,
)
from app.services.review import due_items, record_attempt
from app.services.stats import hand_error_weights, leak_stats

router = APIRouter(prefix="/drill", tags=["drill"])

_provider = get_provider()
_INDEX = build_index(load_preflop_packs())
_BASELINE = [e for e in _INDEX.values() if e.villain_type is None]
_EXPLOIT = [e for e in _INDEX.values() if e.villain_type is not None]
_RNG = random.Random()


def _entry_category(e) -> int:
    if e.villain_type is not None:
        return archetype_leak(e.villain_type)
    return leak_category_for(e.node_context, e.position, e.facing)


def _next_random() -> Spot:
    return sample_spot(_RNG)


def _next_exploit() -> Spot:
    return sample_exploit_spot(_RNG)


def _next_postflop() -> Spot:
    return sample_cbet_spot(_RNG)


def _next_vs_cbet() -> Spot:
    return sample_vs_cbet_spot(_RNG)


def _next_vs_check_raise() -> Spot:
    return sample_check_raise_spot(_RNG)


_POSTFLOP_CTX = (NodeContext.CBET, NodeContext.VS_CBET, NodeContext.VS_CHECK_RAISE)


def _rebuild_postflop(row) -> Spot | None:
    """Reconstruct a postflop spot of the row's archetype (node + position +
    texture/SPR/faced-bet bucket) by rejection-sampling the 2a/2b builders.
    Tag it with the row's signature so re-grading graduates THIS row regardless
    of the reconstructed board's own (possibly-different) signature."""
    try:
        pos = Position(row.position)
    except ValueError:
        return None
    if row.node_context == NodeContext.CBET.value:

        def build() -> Spot:
            return build_cbet_spot(_RNG, pairing=(pos, Position.BB), eff_bb=_RNG.choice(_DEPTHS))
    elif row.node_context == NodeContext.VS_CBET.value and row.facing:
        try:
            opener = Position(row.facing)
        except ValueError:
            return None
        frac = 0.33 if row.faced_bet_bucket == "small" else 0.75

        def build() -> Spot:
            return build_vs_cbet_spot(
                _RNG, pairing=(opener, Position.BB), eff_bb=_RNG.choice(_DEPTHS), cbet_frac=frac
            )
    elif row.node_context == NodeContext.VS_CHECK_RAISE.value and row.facing:
        # Hero is the OPENER/aggressor here (`pos` == row.position), like the CBET
        # branch — NOT the caller as in vs_cbet; the check-raiser (villain) is the
        # BB (row.facing). Unlike vs_cbet (where cbet_frac maps 1:1 to the faced-bet
        # bucket), the check-raise faced-bet bucket depends on the INTERACTION of the
        # internally randomized c-bet size and the raise multiple, so no fixed
        # raise_mult deterministically hits `row.faced_bet_bucket`. Leave raise_mult
        # to randomize; the rejection-sampling loop below + the srs_signature
        # override still graduate THIS row regardless of the reconstructed board's
        # own bucket.
        def build() -> Spot:
            return build_check_raise_spot(
                _RNG, pairing=(pos, Position.BB), eff_bb=_RNG.choice(_DEPTHS), raise_mult=None
            )
    else:
        return None

    candidates = [build() for _ in range(150)]
    target = (row.texture_class, row.spr_bucket, row.faced_bet_bucket)

    def _key(s: Spot):
        return (classify(s.board[:3]).texture_class, spr_bucket(s.spr), faced_bet_bucket(s))

    chosen = (
        next((s for s in candidates if _key(s) == target), None)  # tier a: exact
        or next(  # tier b: same texture class
            (s for s in candidates if classify(s.board[:3]).texture_class == row.texture_class),
            None,
        )
        or candidates[0]  # tier c: same node + position
    )
    chosen.srs_signature = row.signature
    return chosen


def _next_review(session: Session) -> Spot:
    for row in due_items(session):
        try:
            ctx = NodeContext(row.node_context)
        except ValueError:
            continue
        if ctx in _POSTFLOP_CTX:
            spot = _rebuild_postflop(row)
            if spot is not None:
                return spot
            continue
        try:
            pos = Position(row.position)
            facing = Position(row.facing) if row.facing else None
            villain = VillainType(row.villain_type) if row.villain_type else None
        except ValueError:
            continue
        entry = _INDEX.get((ctx, pos, facing, row.limper_count or 0, villain))
        if entry is not None:
            return build_spot(entry, _RNG)
    return _next_random()  # nothing due / reconstructable -> fall back


# Preflop learning-path families: a drill mode per home-hub node so each node
# deals its own strategic situation instead of falling back to `random`.
_FAMILY_CTX: dict[str, NodeContext] = {
    "rfi": NodeContext.RFI,
    "vs_rfi": NodeContext.VS_RFI,
    "blind_defense": NodeContext.BLIND_DEFENSE,
    "vs_limpers": NodeContext.VS_LIMPERS,
    "vs_3bet": NodeContext.VS_3BET,
}


def _next_family(family: str) -> Spot:
    ctx = _FAMILY_CTX[family]
    pool = [e for e in _BASELINE if e.node_context == ctx]
    return build_spot(_RNG.choice(pool), _RNG) if pool else _next_random()


def _next_leak_focus(session: Session) -> Spot:
    stats = leak_stats(session)
    if not stats:
        return _next_random()
    worst = stats[0]["category"]
    pool = [e for e in (_BASELINE + _EXPLOIT) if _entry_category(e) == worst]
    return build_spot(_RNG.choice(pool), _RNG) if pool else _next_random()


def _next_challenge(session: Session) -> Spot:
    weights = hand_error_weights(session)
    return sample_challenge_spot(_RNG, personal_weights=weights)


@router.get("/next", response_model=NextDrillResponse)
async def next_drill(
    mode: str = Query("random"),
    session: Session = Depends(get_session),
) -> NextDrillResponse:
    if mode == "review":
        spot = _next_review(session)
    elif mode == "leak_focus":
        spot = _next_leak_focus(session)
    elif mode == "exploit":
        spot = _next_exploit()
    elif mode == "postflop":
        spot = _next_postflop()
    elif mode == "vs_cbet":
        spot = _next_vs_cbet()
    elif mode == "vs_check_raise":
        spot = _next_vs_check_raise()
    elif mode == "challenge":
        spot = _next_challenge(session)
    elif mode in _FAMILY_CTX:
        spot = _next_family(mode)
    else:
        spot = _next_random()
    # range_grid is preflop-only; the frontend hides the grid for postflop spots.
    grid = range_grid(lookup(_INDEX, spot)) if spot.street == Street.PREFLOP else {}
    return NextDrillResponse(spot=spot, grid=grid)


@router.post("/grade", response_model=EvaluationResult)
async def grade_drill(
    req: GradeRequest,
    session: Session = Depends(get_session),
) -> EvaluationResult:
    result = await _provider.evaluate(req.spot, req.action)
    correctness = result.correctness.value if result.correctness else None
    # Honor the SRS-key override (review spots) so the attempt + SRS update key the
    # same archetype row. record_attempt reads req.spot.srs_signature internally.
    sig = req.spot.srs_signature or spot_signature(req.spot)
    hand_class = hole_cards_to_class(*req.spot.hero.hole_cards)
    session.add(
        DrillAttempt(
            spot_signature=sig,
            leak_category=result.leak_category,
            chosen_action=req.action.action.value,
            correctness=correctness,
            ev_loss_bb=result.ev_loss_bb,
            provider=result.provider.value,
            hand_class=hand_class,
        )
    )
    session.commit()
    record_attempt(session, req.spot, correctness, result.leak_category)
    return result


# --- Foundational quizzes (Phase 2a) ---
_WET_ORDER = {"dry": 0, "medium": 1, "wet": 2}
_QUIZ_ITERS = 1500


def _grade_texture(choice: str, expected: str) -> tuple[str, bool]:
    if choice == expected:
        return "optimal", True
    if choice in _WET_ORDER and abs(_WET_ORDER[choice] - _WET_ORDER[expected]) == 1:
        return "acceptable", False  # adjacent (dry<->medium, medium<->wet)
    return "blunder", False


def _grade_equity(delta: float) -> tuple[str, bool]:
    if delta <= 5:
        return "optimal", True
    if delta <= 10:
        return "acceptable", False
    if delta <= 15:
        return "mistake", False
    return "blunder", False


@router.get("/quiz/next", response_model=QuizItem)
async def quiz_next(kind: str = Query("random")) -> QuizItem:
    if kind not in ("texture", "equity"):
        kind = _RNG.choice(["texture", "equity"])
    spot = sample_cbet_spot(_RNG)
    board = spot.board
    qid = f"{kind}:{''.join(board)}"
    if kind == "texture":
        return QuizItem(
            quiz_id=qid,
            kind="texture",
            board=board,
            prompt="How wet is this flop?",
            options=["dry", "medium", "wet"],
        )
    return QuizItem(
        quiz_id=qid,
        kind="equity",
        board=board,
        hero_cards=spot.hero.hole_cards,
        villain_range=spot.villain_range,
        prompt="Estimate hero's equity vs villain's calling range (%).",
    )


@router.post("/quiz/grade", response_model=QuizResult)
async def quiz_grade(ans: QuizAnswer, session: Session = Depends(get_session)) -> QuizResult:
    if ans.kind == "texture":
        tex = classify(ans.board[:3])
        choice = (ans.choice or "").strip().lower()
        correctness, correct = _grade_texture(choice, tex.wetness)
        leak = int(LeakCategory.BOARD_TEXTURE)
        result = QuizResult(
            kind="texture",
            correct=correct,
            correctness=correctness,
            expected=tex.wetness,
            your_answer=choice or "(none)",
            explanation=f"Texture: {tex.texture_class}.",
            leak_category=leak,
        )
        signature = f"quiz:texture:{tex.texture_class}"
        chosen = choice or "(none)"
    else:
        hero = ans.hero_cards or ("As", "Ks")
        dead = frozenset(hero) | set(ans.board)
        combos = combos_for_range(ans.villain_range or "*", dead)
        seed = sum(ord(c) for c in "".join(hero) + "".join(ans.board))
        true_eq = equity_vs_range(
            tuple(hero), ans.board, combos, iters=_QUIZ_ITERS, rng=random.Random(seed)
        )
        true_pct = round(true_eq * 100, 1)
        est = float(ans.estimate_pct or 0.0)
        delta = round(abs(est - true_pct), 1)
        correctness, correct = _grade_equity(delta)
        leak = int(LeakCategory.EQUITY_EST)
        result = QuizResult(
            kind="equity",
            correct=correct,
            correctness=correctness,
            expected=f"{true_pct}%",
            your_answer=f"{est}%",
            delta=delta,
            explanation=f"True equity ≈ {true_pct}% (Monte-Carlo, {_QUIZ_ITERS} iters).",
            leak_category=leak,
        )
        signature = "quiz:equity"
        chosen = f"{est}%"

    session.add(
        DrillAttempt(
            spot_signature=signature,
            leak_category=leak,
            chosen_action=str(chosen)[:40],
            correctness=correctness,
            ev_loss_bb=0.0,
            provider="quiz",
        )
    )
    session.commit()
    return result
