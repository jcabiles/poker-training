"""Postflop heuristics + flop c-bet grader (Phase 2a).

A NEW grader (does NOT reuse the preflop range-chart `grade()`): it scores the
HU single-raised-pot flop c-bet decision from texture + a positional range-
advantage rule + the hero hand's made/draw category, and emits the existing
`EvaluationResult` shape (per-action freq + a documented PROXY EV).

Range advantage here is a POSITIONAL + texture rule, NOT equity-backed — the
equity engine is reserved for the equity-estimation drill (perf). Equity-backed
range advantage arrives in 2b.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.action import Decision
from app.domain.content.loader import load_pack_file
from app.domain.equity import combos_for_range, equity_vs_range, fold_equity_ev
from app.domain.evaluation import (
    ActionEval,
    ChosenEval,
    Correctness,
    Coverage,
    EvaluationResult,
    ProviderKind,
)
from app.domain.leaks import LeakCategory
from app.domain.spot import ActionType, NodeContext, PlayerStatus, Position, Spot
from app.domain.texture import Texture, classify

# --- N3: authored postflop rationale (content path) ---
# backend/app/domain/postflop.py -> parents[3] == repo root
_POSTFLOP_CONTENT_DIR = Path(__file__).resolve().parents[3] / "content" / "postflop"
_POSTFLOP_RATIONALE_INDEX: dict[tuple, str] | None = None


def _postflop_rationale_index() -> dict[tuple, str]:
    """Authored postflop rationale, keyed by (node_context, hero_position,
    counterpart_position). Additive teaching content (N3) — reuses the SAME
    Entry/ContentPack model as the preflop packs (only `.rationale` is read;
    `.actions` is unused here since postflop scoring stays texture/category-
    driven, not a content-pack range lookup). Lazily loaded once."""
    global _POSTFLOP_RATIONALE_INDEX
    if _POSTFLOP_RATIONALE_INDEX is None:
        idx: dict[tuple, str] = {}
        if _POSTFLOP_CONTENT_DIR.is_dir():
            for path in sorted(_POSTFLOP_CONTENT_DIR.glob("*.json")):
                pack = load_pack_file(path)
                for e in pack.entries:
                    if e.rationale:
                        idx[(e.node_context, e.position, e.facing)] = e.rationale
        _POSTFLOP_RATIONALE_INDEX = idx
    return _POSTFLOP_RATIONALE_INDEX


def _postflop_rationale(
    node_context: NodeContext, hero_pos: Position, counterpart_pos: Position
) -> str | None:
    return _postflop_rationale_index().get((node_context, hero_pos, counterpart_pos))

_RIDX = {r: i for i, r in enumerate("23456789TJQKA")}

# Postflop seat order — later acts last (in position). BTN is most IP.
_POSTFLOP_ORDER = {
    Position.SB: 0,
    Position.BB: 1,
    Position.UTG: 2,
    Position.UTG1: 3,
    Position.UTG2: 4,
    Position.LJ: 5,
    Position.HJ: 6,
    Position.CO: 7,
    Position.BTN: 8,
}

# Postflop correctness thresholds (proxy-EV units, ~bb). Tuned for the c-bet node.
POST_ACCEPTABLE_MAX = 0.6
POST_MISTAKE_MAX = 1.8
POST_MIX = 0.20

# NOTE (Phase 2d, deferred): equity-backed range advantage was investigated and
# reverted. Bounded Monte-Carlo over the wide-vs-condensed heuristic ranges does not
# recover a stable range-advantage signal (mean equity is flat ~0.5; strong-combo
# share is range-width-biased; top-of-range strength is noisy/counterintuitive). Real
# range advantage is an equity-distribution + EV property solvers compute over the full
# tree — so it waits for Phase 3 solver tables (swappable behind StrategyProvider). The
# positional+texture heuristic below is the sound, stable simplified prior for now.

# CW-2b (doc-06 §4 scope note): `_merits_vs_check_raise`'s raise_ merit deliberately
# does NOT get the same `texture.pairing` check-raise bump that CW-2 wired into
# `_merits_vs_cbet` — there is no solver data for hero's post-check-raise 4-bet on
# paired boards (doc-06 only tables the *defender's* first check-raise), and this
# function's fold-heavy live-exploit prior (see its own docstring) already
# discourages exactly the marginal-hand raises a mistaken bump would encourage.
# Revisit if/when solver data for this specific node lands (Phase 3).


def _in_position(hero: Position, villain: Position) -> bool:
    return _POSTFLOP_ORDER.get(hero, 0) > _POSTFLOP_ORDER.get(villain, 0)


def range_advantage(
    node_context: NodeContext, hero_pos: Position, villain_pos: Position, texture: Texture
) -> str:
    """Who holds the range advantage: 'hero' | 'villain' | 'neutral'.

    Positional + texture rule: the preflop aggressor (hero) starts with an edge,
    keeps/extends it on high & dry boards, loses it on low/connected/wet boards,
    and pays an out-of-position penalty.
    """
    score = 1.0  # preflop-aggressor baseline edge
    if texture.high_board:
        # doc 06 §2 (citing this project's own doc 02): ace-high is a documented
        # exception, not just "another high-card board" — live BB defenders
        # over-continue with any ace, so the aggressor's range/nut edge is
        # smaller on ace-high boards than on K/Q/J/T-high boards.
        score += 0.5 if texture.high_card == "A" else 1.0
    else:
        score -= 1.0
    if texture.wetness == "dry":
        score += 1.0
    elif texture.wetness == "wet":
        score -= 1.0
    if texture.connectedness == "connected":
        score -= 1.0
    if not _in_position(hero_pos, villain_pos):
        score -= 1.0
    if score >= 2.0:
        return "hero"
    if score <= -1.0:
        return "villain"
    return "neutral"


def _villain_pos(spot: Spot) -> Position:
    """The live opponent's position: prefer `spot.facing` (always set by the
    builders), else the first non-hero player still IN the hand — never a
    FOLDED seat, so enriched 9-seat player lists can't mis-pick the villain."""
    if spot.facing is not None:
        return spot.facing
    for p in spot.players:
        if not p.is_hero and p.status == PlayerStatus.IN:
            return p.position
    return Position.BB


def _hand_category(hole: tuple[str, str], board: list[str]) -> str:
    """'strong' | 'weak_made' | 'draw' | 'air' — coarse made/draw tier."""
    hranks = [c[0] for c in hole]
    branks = [c[0] for c in board]
    hsuits = [c[1] for c in hole]
    bsuits = [c[1] for c in board]
    board_top = max(_RIDX[b] for b in branks)

    allr = {_RIDX[r] for r in hranks + branks}
    all_suits = hsuits + bsuits

    # Made straight (5 consecutive distinct ranks present across hole+board) and
    # made flush (>=5 cards of one suit present) are evaluated BEFORE the
    # pair-based tiers below — a made hand must never fall through to the
    # flush_draw/oesd draw-flag logic just because it didn't pair the board.
    made_straight = any(
        all((lo + i) in allr for i in range(5)) for lo in range(len(_RIDX) - 4)
    )
    made_flush = any(all_suits.count(s) >= 5 for s in set(all_suits))
    if made_straight or made_flush:
        return "strong"

    made = 0
    if hranks[0] == hranks[1]:  # pocket pair
        if hranks[0] in branks:
            made = 3  # set
        elif _RIDX[hranks[0]] > board_top:
            made = 3  # overpair
        else:
            made = 1  # under/middle pocket pair
    else:
        matches = [r for r in hranks if r in branks]
        if len(matches) >= 2:
            made = 3  # two pair
        elif len(matches) == 1:
            made = 2 if _RIDX[matches[0]] == board_top else 1  # top pair vs weak pair

    # flush_draw/oesd only need to distinguish "not yet made" from "made" for the
    # exactly-4-of-a-suit / exactly-4-consecutive-ranks case: any 5-of-a-suit or
    # 5-consecutive-ranks hand already returned "strong" above, so by the time we
    # get here neither flag can be hiding an already-made hand.
    flush_draw = any(hsuits.count(s) + bsuits.count(s) == 4 for s in set(hsuits))
    oesd = any(sum(1 for x in (lo, lo + 1, lo + 2, lo + 3) if x in allr) >= 4 for lo in range(10))

    if made >= 3:
        return "strong"
    if made in (1, 2):
        # made == 2 is plain top pair (any kicker) — deliberately demoted from
        # "strong" to join made == 1. Was a live bug: `made >= 2` conflated top
        # pair with two-pair/set, so grade_vs_cbet recommended "never fold" with
        # a marginal top pair vs. a big c-bet. Phase 2e-0 T2.
        return "weak_made"
    if flush_draw or oesd:
        return "draw"
    return "air"


_CAT_VALUE = {"strong": 2.0, "weak_made": 1.0, "draw": 1.2, "air": 0.0}

# Interim fold-equity anchoring (N2/doc-08 §3.2): defender fold-% vs the
# original c-bet, keyed off the three board textures doc-06 §2/§4 actually
# tabulates; anything else falls back to doc-06 §6's cited "~40% MDF-
# equilibrium" reference point. Deliberately coarse (no solver tables) — the
# point is grounding `value` in a real fold%+equity formula instead of a flat
# per-category guess, not a full frequency model.
_CBET_FOLD_PCT_PAIRED_DRY = 0.37  # doc-06 §2/§4: Q♥Q♣6♦, 33% pot
_CBET_FOLD_PCT_MONOTONE = 0.37  # doc-06 §2: Q♦J♦T♦, 33% pot
_CBET_FOLD_PCT_WET = 0.62  # doc-06 §2: K♥J♥7♦, 75-125% pot
_CBET_FOLD_PCT_DEFAULT = 0.40  # doc-06 §6: bettor fold-frequency MDF-equilibrium anchor
_FOLD_EQUITY_SCALE = 2.5  # maps per-pot fold-equity EV onto the existing merit-unit range
_FOLD_EQUITY_ITERS = 400  # bounded MC budget -- runs inline on every grade_cbet call


def cbet_fold_pct(texture: Texture) -> float:
    """Defender fold-% vs hero's c-bet, from the doc-06-cited board textures."""
    if texture.pairing == "paired" and texture.wetness == "dry":
        return _CBET_FOLD_PCT_PAIRED_DRY
    if texture.suitedness == "monotone":
        return _CBET_FOLD_PCT_MONOTONE
    if texture.wetness == "wet":
        return _CBET_FOLD_PCT_WET
    return _CBET_FOLD_PCT_DEFAULT


def _cbet_fold_equity_value(
    spot: Spot, board: list[str], texture: Texture, villain_range: str | None
) -> float | None:
    """Hero's `value` term (doc-08 §3.2's one-street fold-equity EV), normalized
    to the merit-unit scale so it composes with the wetness/position bumps in
    `_merits()` below. Returns None (falls back to `_CAT_VALUE`) if the pot or
    villain range makes the formula undefined.
    """
    pot = spot.pot_bb
    if not pot or pot <= 0:
        return None
    dead = frozenset(spot.hero.hole_cards)
    combos = sorted(combos_for_range(villain_range or "*", dead=dead))
    if not combos:
        return None
    equity = equity_vs_range(spot.hero.hole_cards, board, combos, iters=_FOLD_EQUITY_ITERS)
    fold_pct = cbet_fold_pct(texture)
    reference_bet = 0.5 * pot  # a canonical bet size -- small/big sizing stays
    # governed by the existing wetness-based adjustments further down.
    ev = fold_equity_ev(fold_pct, equity, pot, reference_bet)
    return (ev / pot) * _FOLD_EQUITY_SCALE


def _merits(
    adv: str, texture: Texture, cat: str, value_override: float | None = None
) -> tuple[float, float, float]:
    """Return (check, bet_small, bet_big) merit scores (proxy EV, ~bb).

    `value_override` (optional): a fold-equity-EV-derived `value`
    (`_cbet_fold_equity_value`) supplied by `grade_cbet`, which has the real
    hole/board/villain-range context needed to compute it. Falls back to the
    flat `_CAT_VALUE` category lookup when not supplied (e.g. direct unit-test
    calls), so existing callers are unaffected.
    """
    value = _CAT_VALUE[cat] if value_override is None else value_override
    adv_bonus = {"hero": 1.0, "neutral": 0.0, "villain": -1.0}[adv]

    check = 1.0
    if cat == "air":
        check += 1.0
    elif cat == "weak_made":
        check += 0.4
    if adv != "hero":
        check += 0.6
    if texture.wetness == "wet":
        check += 0.4
    if texture.suitedness == "monotone":
        # doc 06 §2: monotone boards get c-bet at roughly half the frequency of
        # two-tone/wet boards (checks most of the range) — `classify()`'s
        # wetness score folds monotone into "wet" via the suitedness term, so
        # without this a monotone board graded identically to a two-tone one.
        check += 0.6

    bet = value + adv_bonus
    if texture.wetness == "dry":
        bet += 0.4  # range-bet dry boards

    small = bet
    big = bet
    if texture.wetness == "dry":
        small += 0.5  # small range bet preferred on dry boards
        big -= 0.5
    else:  # wet/medium: polarize — big with strong/draws, not with marginal/air
        small += 0.1
        if cat in ("strong", "draw"):
            big += 0.4
        else:
            big -= 0.6
    if texture.suitedness == "monotone":
        # doc 06 §2: even when a monotone board IS bet, sizing stays small
        # (~33% pot) for real value/nut draws — the big/polarized-overbet
        # sizing menu is a two-tone-wet-board play, not a monotone one.
        small += 0.3
        big -= 0.6
        if cat not in ("strong", "draw"):
            big -= 0.4  # discourage big bluffs/thin bets on monotone further
    if cat == "air":
        big -= 1.0  # never barrel big with pure air
    return check, small, big


def _frequencies(merits: list[float]) -> list[float]:
    pos = [max(0.0, m) for m in merits]
    total = sum(pos)
    if total <= 0:
        # degenerate — default to a pure check
        return [1.0 if i == 0 else 0.0 for i in range(len(merits))]
    return [p / total for p in pos]


def _bet_sizes(spot: Spot) -> tuple[float | None, float | None]:
    bets = sorted((la.min_bb or 0.0) for la in spot.legal_actions if la.action == ActionType.BET)
    small = bets[0] if bets else None
    big = bets[-1] if len(bets) > 1 else small
    return small, big


def grade_cbet(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    board = spot.board[:3]
    tex = classify(board)
    ctx = spot.node_context[0] if spot.node_context else NodeContext.CBET
    adv = range_advantage(ctx, spot.hero.position, _villain_pos(spot), tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    small, big = _bet_sizes(spot)
    rationale = _postflop_rationale(NodeContext.CBET, spot.hero.position, _villain_pos(spot))

    # N2/doc-08 §3.2: ground `value` in a real fold-equity EV (equity.py's
    # `equity_vs_range` + doc-06's fold-continuation numbers) instead of the
    # flat per-category guess, wherever it's computable for this spot.
    fold_equity_value = _cbet_fold_equity_value(spot, board, tex, villain_range)
    m_check, m_small, m_big = _merits(adv, tex, cat, value_override=fold_equity_value)
    merits = [m_check, m_small, m_big]
    freqs = _frequencies(merits)

    specs = [
        (ActionType.CHECK, None, m_check, freqs[0]),
        (ActionType.BET, small, m_small, freqs[1]),
        (ActionType.BET, big, m_big, freqs[2]),
    ]
    evals = [
        ActionEval(action=a, size_bb=size, frequency=round(f, 3), ev_bb=round(m, 2))
        for a, size, m, f in specs
    ]
    best = max(evals, key=lambda e: e.ev_bb)
    is_mixed = sum(1 for f in freqs if f > POST_MIX) >= 2
    leak = int(LeakCategory.FLOP_CBET)

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": leak,
        "is_mixed": is_mixed,
    }

    def _size_label(size: float | None) -> str:
        if size is None:
            return "check"
        if big and small and big != small:
            return "big bet" if size >= big else "small bet"
        return "bet"

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=["cbet", adv, cat, tex.wetness],
            explanation=(
                f"{tex.texture_class.split('|')[0]} board, {adv} range advantage; "
                f"hero has {cat}: {_size_label(best.size_bb)} is the play."
            ),
        )
        if rationale:
            result.authored_rationale = rationale
        return result

    chosen = _match(evals, decision, small, big)
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))
    chosen_freq = chosen.frequency

    if chosen.action == best.action and chosen.size_bb == best.size_bb:
        correctness = Correctness.OPTIMAL
    elif chosen_freq > POST_MIX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_ACCEPTABLE_MAX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_MISTAKE_MAX:
        correctness = Correctness.MISTAKE
    else:
        correctness = Correctness.BLUNDER

    if correctness == Correctness.OPTIMAL:
        why = (
            f"{cat} on a {tex.wetness} board with {adv} range advantage: "
            f"{_size_label(best.size_bb)} is the play."
        )
    else:
        why = (
            f"{cat} on a {tex.wetness} board ({adv} range advantage): best is "
            f"{_size_label(best.size_bb)}; you chose {_size_label(chosen.size_bb)} "
            f"(-{ev_loss}bb)."
        )

    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen_freq, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        rationale_tags=["cbet", adv, cat, tex.wetness],
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


def _match(evals: list[ActionEval], decision: Decision, small, big) -> ActionEval:
    """Resolve the chosen ActionEval, disambiguating small vs big bets by size."""
    if decision.action == ActionType.CHECK:
        return next(e for e in evals if e.action == ActionType.CHECK)
    # a bet: pick the bet eval whose size is nearest the chosen size
    target = decision.size_bb
    bet_evals = [e for e in evals if e.action == ActionType.BET]
    if target is None:
        return bet_evals[0]
    return min(bet_evals, key=lambda e: abs((e.size_bb or 0.0) - target))


# --- Phase 2b: facing a flop c-bet (defense) ---

_HAND_VALUE = {"strong": 2.0, "draw": 1.2, "weak_made": 0.8, "air": 0.0}


def range_advantage_defender(
    aggressor_pos: Position, defender_pos: Position, texture: Texture
) -> str:
    """Who holds the range advantage from the DEFENDER's view: 'defender' |
    'aggressor' | 'neutral'.

    Distinct from `range_advantage()` (the aggressor's view): the defender gets
    NO preflop-aggressor baseline; gains an edge on low / connected / wet boards
    (their calling range connects); loses it on high / dry boards; and pays an
    out-of-position penalty (the defender is OOP in a HU SRP).
    """
    score = 0.0  # no preflop-aggressor baseline for the caller
    score += -1.0 if texture.high_board else 1.0  # low boards favor the caller
    if texture.wetness == "wet":
        score += 1.0
    elif texture.wetness == "dry":
        score -= 1.0
    if texture.connectedness == "connected":
        score += 1.0
    if not _in_position(defender_pos, aggressor_pos):
        score -= 1.0  # defender OOP penalty
    if score >= 1.0:
        return "defender"
    if score <= -1.0:
        return "aggressor"
    return "neutral"


def _faced_call_and_pot(spot: Spot) -> tuple[float, float]:
    """The amount hero must call (the faced c-bet) and the current pot (incl. it)."""
    call = next(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.CALL and la.min_bb),
        0.0,
    )
    return float(call or 0.0), float(spot.pot_bb)


def _merits_vs_cbet(value: float, adv: str, price: float, texture: Texture, cat: str):
    """Return (fold, call, raise) merit scores (proxy EV, ~bb). `price` = pot odds
    to call (faced bet / pot, already includes the bet)."""
    adv_bonus = {"defender": 0.5, "neutral": 0.0, "aggressor": -0.5}[adv]

    fold = 0.6
    if cat == "air":
        fold += 1.0
    elif cat == "weak_made":
        fold += 0.2
    fold += price * 1.5  # worse price (bigger faced bet) -> folding better
    if adv == "aggressor":
        fold += 0.3
    fold -= value * 0.6  # strong made hands / draws rarely fold

    call = value + adv_bonus
    call += (0.5 - price) * 2.0  # cheap price -> call better; expensive -> worse
    if cat == "air":
        call -= 1.0  # bluff-catching pure air is bad

    if cat == "strong":
        raise_ = value + 0.5 + adv_bonus
    elif cat == "draw":
        raise_ = value - 0.2 + adv_bonus
        if texture.wetness == "wet" and adv == "defender":
            raise_ += 0.8  # semibluff check-raise spot
    elif cat == "weak_made":
        raise_ = -0.8  # don't check-raise weak made hands
    else:  # air
        raise_ = -1.0
        if adv == "defender" and texture.connectedness == "connected" and texture.wetness == "wet":
            raise_ += 0.6  # occasional check-raise bluff on low connected boards

    if texture.pairing == "paired" and adv == "defender":
        # doc 06 §4: paired boards get check-raised ~2.5-5x more often than other
        # textures (GTOWizard, "Defending vs BB Check-Raise on Paired Flops") —
        # cheap to represent trips/a boat for both ranges. `texture.pairing` was
        # computed but never read anywhere in this module before this fix.
        raise_ += 0.5

    return fold, call, raise_


def grade_vs_cbet(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    board = spot.board[:3]
    tex = classify(board)
    aggressor = spot.facing or _villain_pos(spot)
    adv = range_advantage_defender(aggressor, spot.hero.position, tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    value = _HAND_VALUE[cat]
    faced, pot = _faced_call_and_pot(spot)
    price = faced / pot if pot > 0 else 0.5
    rationale = _postflop_rationale(NodeContext.VS_CBET, spot.hero.position, aggressor)

    raise_size = next(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.RAISE and la.min_bb),
        None,
    )
    m_fold, m_call, m_raise = _merits_vs_cbet(value, adv, price, tex, cat)
    specs = [
        (ActionType.FOLD, None, m_fold),
        (ActionType.CALL, faced or None, m_call),
        (ActionType.RAISE, raise_size, m_raise),
    ]
    freqs = _frequencies([m for _, _, m in specs])
    evals = [
        ActionEval(action=a, size_bb=size, frequency=round(f, 3), ev_bb=round(m, 2))
        for (a, size, m), f in zip(specs, freqs, strict=False)
    ]
    best = max(evals, key=lambda e: e.ev_bb)
    is_mixed = sum(1 for f in freqs if f > POST_MIX) >= 2
    leak = int(LeakCategory.VS_CBET)

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": leak,
        "is_mixed": is_mixed,
    }

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=["vs_cbet", adv, cat, tex.wetness],
            explanation=(
                f"{cat} facing a c-bet on a {tex.wetness} board ({adv} range advantage): "
                f"{best.action.value} is the play."
            ),
        )
        if rationale:
            result.authored_rationale = rationale
        return result

    chosen = next((e for e in evals if e.action == decision.action), None)
    if chosen is None:
        chosen = ActionEval(
            action=decision.action, frequency=0.0, ev_bb=min(e.ev_bb for e in evals) - 1.0
        )
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))

    if chosen.action == best.action:
        correctness = Correctness.OPTIMAL
    elif chosen.frequency > POST_MIX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_ACCEPTABLE_MAX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_MISTAKE_MAX:
        correctness = Correctness.MISTAKE
    else:
        correctness = Correctness.BLUNDER

    if correctness == Correctness.OPTIMAL:
        why = f"{cat} on a {tex.wetness} board ({adv} edge): {best.action.value} is the play."
    else:
        why = (
            f"{cat} on a {tex.wetness} board ({adv} edge): best is {best.action.value}; "
            f"you chose {decision.action.value} (-{ev_loss}bb)."
        )

    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        rationale_tags=["vs_cbet", adv, cat, tex.wetness],
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


# --- Phase 2e-1: facing a flop check-raise (hero = the original c-bettor) ---


def _merits_vs_check_raise(
    value: float, adv: str, price: float, texture: Texture, cat: str
) -> tuple[float, float, float]:
    """Return (fold, call, raise) merit scores (proxy EV, ~bb) for hero — the
    ORIGINAL flop c-bettor — facing a defender's check-raise.

    `adv` is the AGGRESSOR-view `range_advantage()` result ('hero'|'neutral'|
    'villain'), since hero is still the preflop+flop aggressor. `price` = pot odds
    to call (faced check-raise / pot).

    Live $1/$2 check-raises are rarely bluffs (research §10.3) — a raise-after-my-
    bet is fresh strength news, a STRONGER prior than the static board range read.
    So the fold baseline here (1.6) is meaningfully higher than `_merits_vs_cbet`'s
    (0.6), and a nominal range advantage does NOT rescue a marginal/air hand (the
    check-raise overrides the static read for hands that only bluff-catch). Texture
    modulates it (§4.4): bluffs are more plausible on low/connected/wet boards, rare
    on dry rainbow boards — texture shifts fold/call balance but never overrides a
    clear air-hand fold on a dry board (bluffy is negative there, so it can't).
    """
    adv_bonus = {"hero": 0.5, "neutral": 0.0, "villain": -0.5}[adv]

    # texture-conditioned bluff plausibility (§4.4)
    bluffy = 0.0
    if not texture.high_board:
        bluffy += 0.3
    if texture.connectedness == "connected":
        bluffy += 0.3
    if texture.wetness == "wet":
        bluffy += 0.4
    elif texture.wetness == "dry":
        bluffy -= 0.4
    low_connected_wet = (
        not texture.high_board
        and texture.connectedness == "connected"
        and texture.wetness == "wet"
    )

    # FOLD — baseline well above _merits_vs_cbet's 0.6 (the check-raise-strength prior)
    fold = 1.6
    if cat == "air":
        fold += 1.2
    elif cat == "weak_made":
        fold += 0.6
    fold += price * 1.5  # worse price (bigger check-raise) -> folding better
    if adv == "villain":
        fold += 0.3  # villain's range even stronger -> fold more
    fold -= value * 0.8  # strong made hands / draws fold far less
    fold -= max(0.0, bluffy)  # bluffier boards -> fold a bit less (never on dry: bluffy<=0)

    # CALL — range advantage only rewards genuinely-continuing hands (strong/draw);
    # a check-raise strips a marginal/air hand of the static-edge call boost.
    call = value
    if cat in ("strong", "draw"):
        call += adv_bonus
    call += (0.4 - price) * 1.5  # cheap check-raise -> call better
    if cat == "draw" and texture.wetness == "wet":
        call += 0.6  # draws want to continue on wet boards (equity to realize)
    if cat == "air":
        call -= 1.4  # bluff-catching pure air vs a check-raise is bad
    elif cat == "weak_made":
        call += bluffy * 0.5  # a marginal bluff-catch only where a bluff is plausible

    # RAISE (4-bet)
    if cat == "strong":
        raise_ = value + 0.6 + adv_bonus  # value 4-bet
    elif cat == "draw":
        raise_ = value - 0.4  # kept below call so call stays best on wet boards
        if low_connected_wet:
            raise_ += 0.5  # semibluff 4-bet only where check-raise bluffs are plausible
    elif cat == "weak_made":
        raise_ = -1.0  # don't 4-bet a marginal made hand into a check-raise
    else:  # air
        raise_ = -1.4
        if low_connected_wet:
            raise_ += 0.8  # rare semibluff 4-bet with backdoors on very wet boards
    return fold, call, raise_


def grade_vs_check_raise(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    board = spot.board[:3]
    tex = classify(board)
    ctx = spot.node_context[0] if spot.node_context else NodeContext.VS_CHECK_RAISE
    # CRITICAL: the third arg is the check-raiser's position (_villain_pos), NOT
    # hero's own. Hero is the aggressor here; passing hero's position twice would
    # corrupt range_advantage()'s in-position read (refuter-caught).
    adv = range_advantage(ctx, spot.hero.position, _villain_pos(spot), tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    value = _HAND_VALUE[cat]
    faced, pot = _faced_call_and_pot(spot)
    price = faced / pot if pot > 0 else 0.5
    rationale = _postflop_rationale(
        NodeContext.VS_CHECK_RAISE, spot.hero.position, _villain_pos(spot)
    )

    raise_size = next(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.RAISE and la.min_bb),
        None,
    )
    m_fold, m_call, m_raise = _merits_vs_check_raise(value, adv, price, tex, cat)
    specs = [
        (ActionType.FOLD, None, m_fold),
        (ActionType.CALL, faced or None, m_call),
        (ActionType.RAISE, raise_size, m_raise),
    ]
    freqs = _frequencies([m for _, _, m in specs])
    evals = [
        ActionEval(action=a, size_bb=size, frequency=round(f, 3), ev_bb=round(m, 2))
        for (a, size, m), f in zip(specs, freqs, strict=True)
    ]
    best = max(evals, key=lambda e: e.ev_bb)
    is_mixed = sum(1 for f in freqs if f > POST_MIX) >= 2
    leak = int(LeakCategory.VS_CHECK_RAISE)

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": leak,
        "is_mixed": is_mixed,
    }

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=["vs_check_raise", adv, cat, tex.wetness],
            explanation=(
                f"{cat} facing a check-raise on a {tex.wetness} board "
                f"({adv} range advantage): {best.action.value} is the play."
            ),
        )
        if rationale:
            result.authored_rationale = rationale
        return result

    # RAISE matches by ActionType alone (one raise option), like grade_vs_cbet.
    chosen = next((e for e in evals if e.action == decision.action), None)
    if chosen is None:
        chosen = ActionEval(
            action=decision.action, frequency=0.0, ev_bb=min(e.ev_bb for e in evals) - 1.0
        )
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))

    if chosen.action == best.action:
        correctness = Correctness.OPTIMAL
    elif chosen.frequency > POST_MIX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_ACCEPTABLE_MAX:
        correctness = Correctness.ACCEPTABLE
    elif ev_loss <= POST_MISTAKE_MAX:
        correctness = Correctness.MISTAKE
    else:
        correctness = Correctness.BLUNDER

    if correctness == Correctness.OPTIMAL:
        why = (
            f"{cat} vs a check-raise on a {tex.wetness} board ({adv} edge): "
            f"{best.action.value} is the play."
        )
    else:
        why = (
            f"{cat} vs a check-raise on a {tex.wetness} board ({adv} edge): best is "
            f"{best.action.value}; you chose {decision.action.value} (-{ev_loss}bb)."
        )

    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        rationale_tags=["vs_check_raise", adv, cat, tex.wetness],
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result
