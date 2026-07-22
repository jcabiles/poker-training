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
from app.domain.spot import (
    ActionType,
    NodeContext,
    PlayerStatus,
    Position,
    Spot,
    Street,
    is_multiway,
)
from app.domain.texture import Texture, classify, river_card_class, turn_card_class

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


_TURN_CTX = (NodeContext.TURN_BARREL, NodeContext.VS_TURN_BET)
_RIVER_CTX = (NodeContext.RIVER_BARREL, NodeContext.VS_RIVER_BET)


def range_advantage(
    node_context: NodeContext,
    hero_pos: Position,
    villain_pos: Position,
    texture: Texture,
    river_class: str | None = None,
) -> str:
    """Who holds the range advantage: 'hero' | 'villain' | 'neutral'.

    Dispatches on `node_context` (S6/S7): flop contexts keep the original
    positional + texture rule bit-for-bit; turn contexts use a turn-aware
    variant — the flop bet got CALLED, so the aggressor's baseline edge has
    decayed and low/wet boards tilt further toward the caller (research §5.1:
    "the board texture has become too good for their range" is a give-up
    trigger). River contexts (S7) decay the aggressor's baseline further —
    TWO bets got called — and the river-card class (`river_class`, passed only
    by the river graders) shifts the read: scare rivers re-credit the
    barreler's story, draw-completing rivers favor the two-time caller. Same
    (positions, texture) can therefore label differently street to street.
    `texture` is the FLOP texture in all branches.

    HU-SHAPED (N5 annotation): a range-vs-range read against ONE villain. On a
    multiway spot the true opposition is the UNION of ranges — someone-has-it
    probability is higher — so this read is HU-optimistic 3-way;
    `_apply_multiway`'s value-lean/catch-tighten is the deliberate downstream
    correction, not a substitute for a real multiway range model.
    """
    if node_context in _RIVER_CTX:
        score = 0.0  # two called bets: the aggressor's edge has decayed past the turn's 0.5
        if texture.high_board:
            score += 0.5 if texture.high_card == "A" else 1.0
        else:
            score -= 1.5
        if texture.wetness == "dry":
            score += 1.0
        elif texture.wetness == "wet":
            score -= 1.5
        if texture.connectedness == "connected":
            score -= 1.0
        if river_class in ("over", "pairing"):
            score += 0.5  # scare rivers weaken the caller's pair-heavy range
        elif river_class in ("flush", "straight"):
            score -= 1.0  # draw-completing rivers land in the caller's range
        if not _in_position(hero_pos, villain_pos):
            score -= 1.0
        if score >= 2.0:
            return "hero"
        if score <= -1.0:
            return "villain"
        return "neutral"

    if node_context in _TURN_CTX:
        score = 0.5  # aggressor's preflop edge decays once the flop bet is called
        if texture.high_board:
            score += 0.5 if texture.high_card == "A" else 1.0
        else:
            # a called low flop favors the caller even more by the turn — the
            # calling range connected while the aggressor's broadways bricked
            score -= 1.5
        if texture.wetness == "dry":
            score += 1.0
        elif texture.wetness == "wet":
            score -= 1.5
        if texture.connectedness == "connected":
            score -= 1.0
        if not _in_position(hero_pos, villain_pos):
            score -= 1.0
        if score >= 2.0:
            return "hero"
        if score <= -1.0:
            return "villain"
        return "neutral"

    # Flop contexts (CBET / VS_CHECK_RAISE / …): the original preflop-aggressor
    # rule, unchanged — flop grader outputs must stay byte-identical.
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
    FOLDED seat, so enriched 9-seat player lists can't mis-pick the villain.

    HU-SHAPED (N5 annotation): collapses the opposition to ONE seat. On a
    multiway spot this is the AGGRESSOR only — the extra callers' ranges are
    invisible here by design, and `_apply_multiway`'s dampens are the
    deliberate downstream correction. Don't mistake this for multiway-aware."""
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
            if branks.count(matches[0]) >= 2:
                # F7 bug 2: one-hole-card trips on a paired board (A8 on 883,
                # ~0.94 equity). Was falling to the top-pair/weak-pair rule →
                # "weak_made", so the F5 catcher clamp pinned its fold share at
                # α and FOLD graded ACCEPTABLE while the lower-equity 33 boat
                # graded FOLD a mistake. Trips slot with two-pair/sets/boats:
                made = 3  # trips (hole card + board pair)
            else:
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

    HU-SHAPED (N5 annotation): single villain range, single fold%. Multiway,
    total fold equity COMPOUNDS multiplicatively across defenders (P1×P2×…) —
    strictly lower — so this OVERESTIMATES bluff EV 3-way. `_apply_multiway`'s
    bluff dampen is the deliberate downstream correction; keep both in sync.
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


# --- S8: multiway merit adjustment (binary bucket — heads-up vs 3+) ---
# Applied by EVERY grader after its base merits are computed and BEFORE
# _frequencies(), and ONLY when is_multiway(spot) — heads-up output stays
# byte-identical. Directions (spec-frozen): fewer acceptable bluffs, slight
# value-lean, tighter bluff-catching. Values are tuning knobs.
_MW_BLUFF_DAMPEN = 0.6  # in (0,1): scales DOWN aggressive merit for bluff candidates
_MW_VALUE_LEAN = 1.15  # >= 1.0: scales UP value-category aggressive merit
_MW_CATCH_TIGHTEN = 1.3  # >= 1.0: scales UP fold merit for the air bluff-catch
# N5: thin-value dampen — "thin value disappears multiway" is the most-cited
# published multiway result (equity dilution: one-pair value bets that print
# HU become checks 3-way). Sits between the bluff dampen (0.6) and neutral:
# weak_made keeps SOME betting merit but stops betting thin by default.
_MW_THIN_VALUE_DAMPEN = 0.7


def _apply_multiway(merits: dict, *, cat_effective: str, facing_side: bool) -> dict:
    """Multiway (3+) merit adjustment — reads NOTHING but the merit dict, the
    already-computed hand category (post busted-draw demotion on the river) and
    which side hero is on. Never persona data (graders-never-read-persona).

    Aggressor side (keys check/small/big): dampen aggressive merit for
    bluff-candidate categories — "air", and "draw" (semibluffs; river draws
    arrive already demoted to "air" upstream) — and lean the "strong" value
    bets up. Facing side (keys fold/call/raise): tighten the marginal
    bluff-catch ("air" AND "weak_made" — air call merits are structurally
    non-positive in every facing merit function, so weak_made is where the
    tighten actually moves frequencies) — raise the fold merit, dampen the
    call/raise-bluff merits. Scaling only applies to POSITIVE merits (scaling
    a negative merit toward zero would perversely INCREASE it).
    """
    out = dict(merits)
    if facing_side:
        if cat_effective in ("air", "weak_made"):
            out["fold"] = out["fold"] * _MW_CATCH_TIGHTEN
            for k in ("call", "raise"):
                if out[k] > 0:
                    out[k] = out[k] * _MW_BLUFF_DAMPEN
        return out
    if cat_effective in ("air", "draw"):
        for k in ("small", "big"):
            if out[k] > 0:
                out[k] = out[k] * _MW_BLUFF_DAMPEN
    elif cat_effective == "weak_made":
        # N5: thin value stops betting multiway (research: value thresholds
        # rise as equity dilutes — marginal made hands check, they don't bet).
        for k in ("small", "big"):
            if out[k] > 0:
                out[k] = out[k] * _MW_THIN_VALUE_DAMPEN
    elif cat_effective == "strong":
        for k in ("small", "big"):
            if out[k] > 0:
                out[k] = out[k] * _MW_VALUE_LEAN
    return out


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
    if spot.street != Street.FLOP:
        raise ValueError("grade_cbet is flop-only")
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
    if is_multiway(spot):
        mw = _apply_multiway(
            {"check": m_check, "small": m_small, "big": m_big},
            cat_effective=cat,
            facing_side=False,
        )
        m_check, m_small, m_big = mw["check"], mw["small"], mw["big"]
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

    bet_evals = [e for e in evals if e.action == ActionType.BET]
    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen_freq, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        sizing_correctness=_bet_sizing_verdict(bet_evals, chosen),
        rationale_tags=["cbet", adv, cat, tex.wetness],
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


def _bet_sizing_verdict(
    bet_evals: list[ActionEval], chosen_eval: ActionEval
) -> Correctness | None:
    """N4a additive size verdict for a postflop BET (independent of the action
    correctness). OPTIMAL when `chosen_eval` is the higher-merit (frequency) of
    the two BET sizes, ACCEPTABLE for the lower.

    None when there's nothing to grade or betting itself wasn't reasonable:
      - hero didn't bet (chosen isn't a BET eval),
      - fewer than two BET sizes were offered,
      - BOTH BET frequencies clamp to 0 (air/weak — betting is the mistake; no
        "size: Best" sub-note beside a bet-blunder).
    A tie between two POSITIVE-frequency sizes resolves to OPTIMAL.
    """
    if chosen_eval.action != ActionType.BET or len(bet_evals) < 2:
        return None
    top_freq = max(e.frequency for e in bet_evals)
    if top_freq <= 0.0:
        return None  # both sizes zero-frequency — betting isn't the play
    return (
        Correctness.OPTIMAL
        if chosen_eval.frequency >= top_freq
        else Correctness.ACCEPTABLE
    )


def _raise_sizing_verdict(
    spot: Spot, decision: Decision, wetness: str, chosen_eval: ActionEval
) -> Correctness | None:
    """N4b additive size verdict for a facing-node RAISE (independent of the
    action correctness). INTENTIONALLY diverges from `_bet_sizing_verdict`'s
    merit-comparison shape: the facing merits (`_merits_vs_*`) compute ONE
    scalar raise merit — there are no per-size raise merits to compare — so
    this is a texture-rule overlay applying RES-B §5.1 directly: on dry flops
    the small (pot-controlled) raise is the teach, on wet flops the big
    (equity-denying) raise; a medium flop has no forced optimal (both
    acceptable). `wetness` is the FLOP texture on every street, matching the
    graders' own convention.

    None when there's nothing to grade or raising itself wasn't reasonable:
      - hero didn't raise (or sent no size to attribute),
      - fewer than two distinct RAISE legs were offered (short-stack collapse
        and all pre-N4b single-leg flows),
      - the raise frequency clamps to 0 (raising is the mistake; no
        "size: Best" sub-note beside a raise-blunder).
    """
    if decision is None or decision.action != ActionType.RAISE or decision.size_bb is None:
        return None
    legs = sorted(
        la.min_bb
        for la in spot.legal_actions
        if la.action == ActionType.RAISE and la.min_bb
    )
    if len(legs) < 2 or legs[-1] <= legs[0]:
        return None
    if chosen_eval.frequency <= 0.0:
        return None  # zero-frequency raise — raising isn't the play
    small, big = legs[0], legs[-1]
    hero_leg = small if abs(decision.size_bb - small) <= abs(decision.size_bb - big) else big
    if wetness == "medium":
        return Correctness.ACCEPTABLE  # no forced optimal on a neutral board
    optimal_leg = small if wetness == "dry" else big
    return Correctness.OPTIMAL if hero_leg == optimal_leg else Correctness.ACCEPTABLE


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


# --- F5: theory-calibrated price band for the marginal bluff-catcher ---
#
# The facing graders compute `price` = faced_bet / pot where the pot ALREADY
# includes the faced bet, so price = B/(P+B) — which is exactly α, the
# bettor's bluff-indifference point and the defender's fold-CEILING for that
# exact size (RES-D §1a; RES-E §2 boundary ruling: use the size-exact α, not
# a bucket midpoint, when the live pot-fraction is known).
#
# RES-D §5 (the A1 guardrail, Sol+Opus #1 finding) as a grading rule:
#   * CEILING — a defender systematically folding MORE than α of the
#     marginal continue-decision region vs a balanced bet is over-folding,
#     so the graded FOLD share of a marginal bluff-catcher is capped at α
#     for the faced size (folding gets MORE credit as the bet grows, since
#     α rises with size — RES-D §1a's monotone column).
#   * NEVER A FLOOR ON THE PLAYER — α/MDF must NOT be used to mark a
#     below-MDF fold as wrong on the flop/turn (RES-D §1c: solver defense
#     routinely sits below raw MDF pre-river vs range-bets/capped bettors).
#     For any MEANINGFUL bet — α ≥ _A1_FOLD_CREDIT, i.e. at least the
#     ⅓-pot shape of the RES-E SMALL bucket (RES-D §1a row 1) — the grader
#     guarantees the marginal catcher's FOLD action a minimum graded share
#     (_A1_FOLD_CREDIT > POST_MIX, so a hero fold can never grade worse
#     than ACCEPTABLE there); it never asserts the hero MUST fold.
#   * TINY BETS (α < _A1_FOLD_CREDIT, sub-⅓-pot: min-bets/probes) — the
#     ACCEPTABLE-floor guarantee deliberately does NOT apply. The two
#     bounds are jointly unsatisfiable there (an unconditional 0.25 floor
#     would push fold share ABOVE α for α < ~0.23, breaking the α-ceiling
#     — the hard A1/RES-D contract, which wins), so the floor tracks α by
#     design (floor_q = min(_A1_FOLD_CREDIT, α)). That is also the right
#     verdict: theory never endorsed folding a bluff-catcher to a tiny bet
#     (at α ≈ 0.08 hero gets ~12:1) — A1 protects below-MDF folds vs
#     meaningful sizes where naive MDF over-demands defense, not min-bet
#     folds, which correctly fall through to the EV-loss ladder
#     (MISTAKE/BLUNDER).
#
# Scope (deliberate): flop `grade_vs_cbet` + turn `grade_vs_turn_bet` only.
# NOT the check-raise node — α is the flat-call form and "doesn't work with
# a raise" (RES-D §1c, GTO Wizard); its fold-heavy live-exploit prior stays.
# NOT the river — RES-D §5.2 scopes the don't-flag-below-MDF rule to
# flop/turn; river bluff-catching stays with its existing pot-odds terms.
# Applied BEFORE `_apply_multiway`: multiway defense correctly folds beyond
# the HU α ceiling (RES-D §6 — direction only, no per-opponent constant).
_A1_FOLD_CREDIT = 0.25  # α at the SMALL bucket (⅓-pot, RES-D §1a row 1):
# vs any bet of at least the smallest canonical shape, up to a quarter of
# the marginal region may correctly fold — the minimum graded credit a
# catcher's fold receives THERE. For sub-⅓-pot bets (α < 0.25) the floor
# tracks α instead (see TINY BETS above): the ACCEPTABLE guarantee is
# scoped to α ≥ _A1_FOLD_CREDIT, never unconditional.
_PRICE_CATCHER_CATS = ("weak_made",)  # the bluff-catch tier where fold-vs-
# call is the graded decision; strong ~never folds, air folds freely, and
# draws are priced by their equity terms, not by α (RES-D §5.2).


def _calibrate_catcher_fold(
    m_fold: float, m_call: float, m_raise: float, *, alpha: float, cat: str
) -> float:
    """F5: clamp the FOLD merit of the marginal bluff-catcher so its graded
    share lands in the theory band [min(_A1_FOLD_CREDIT, α), α] for the faced
    size (see the block comment above for the RES-D §1a/§1c/§5 derivation —
    including the TINY BETS scoping: for α < _A1_FOLD_CREDIT both bounds
    collapse to α, the A1 ACCEPTABLE-floor guarantee does not apply, and a
    catcher's fold to a sub-⅓-pot bet correctly grades by the EV ladder).
    Merit-space clamp: with continue mass S = call⁺ + raise⁺, fold share q
    means fold = q/(1−q)·S — so frequencies, per-action EVs and the
    correctness ladder all stay consistent (freq + approximate EV, never a
    boolean verdict). Call/raise merits are untouched: pot-odds keeps
    driving the call threshold via their existing price terms."""
    if cat not in _PRICE_CATCHER_CATS or alpha <= 0.0:
        return m_fold
    cont = max(m_call, 0.0) + max(m_raise, 0.0)
    if cont <= 0.0:
        return m_fold  # nothing continues — folding outright is fine
    ceil_q = min(alpha, 0.95)
    floor_q = min(_A1_FOLD_CREDIT, ceil_q)
    lo = floor_q / (1.0 - floor_q) * cont
    hi = ceil_q / (1.0 - ceil_q) * cont
    return min(max(m_fold, lo), hi)


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
    if spot.street != Street.FLOP:
        raise ValueError("grade_vs_cbet is flop-only")
    board = spot.board[:3]
    tex = classify(board)
    aggressor = spot.facing or _villain_pos(spot)
    adv = range_advantage_defender(aggressor, spot.hero.position, tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    value = _HAND_VALUE[cat]
    faced, pot = _faced_call_and_pot(spot)
    price = faced / pot if pot > 0 else 0.5
    rationale = _postflop_rationale(NodeContext.VS_CBET, spot.hero.position, aggressor)

    # N4b: the spot may offer two RAISE legs (small/big). The single action-level
    # RAISE eval keys on the BIG leg — max(), not first-leg next(), so a two-leg
    # spot can't ordering-dependently grab the small leg. On single-leg spots
    # (all pre-N4b flows) max == the one leg: byte-identical.
    raise_size = max(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.RAISE and la.min_bb),
        default=None,
    )
    m_fold, m_call, m_raise = _merits_vs_cbet(value, adv, price, tex, cat)
    # F5: price-calibrate the marginal catcher's fold share (α ceiling + A1
    # fold-credit floor, RES-D §5) — `price` here IS the size-exact α.
    m_fold = _calibrate_catcher_fold(m_fold, m_call, m_raise, alpha=price, cat=cat)
    if is_multiway(spot):
        mw = _apply_multiway(
            {"fold": m_fold, "call": m_call, "raise": m_raise},
            cat_effective=cat,
            facing_side=True,
        )
        m_fold, m_call, m_raise = mw["fold"], mw["call"], mw["raise"]
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
        sizing_correctness=_raise_sizing_verdict(spot, decision, tex.wetness, chosen),
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
    if spot.street != Street.FLOP:
        raise ValueError("grade_vs_check_raise is flop-only")
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

    # N4b: the spot may offer two RAISE legs (small/big). The single action-level
    # RAISE eval keys on the BIG leg — max(), not first-leg next(), so a two-leg
    # spot can't ordering-dependently grab the small leg. On single-leg spots
    # (all pre-N4b flows) max == the one leg: byte-identical.
    raise_size = max(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.RAISE and la.min_bb),
        default=None,
    )
    m_fold, m_call, m_raise = _merits_vs_check_raise(value, adv, price, tex, cat)
    if is_multiway(spot):
        mw = _apply_multiway(
            {"fold": m_fold, "call": m_call, "raise": m_raise},
            cat_effective=cat,
            facing_side=True,
        )
        m_fold, m_call, m_raise = mw["fold"], mw["call"], mw["raise"]
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
        sizing_correctness=_raise_sizing_verdict(spot, decision, tex.wetness, chosen),
        rationale_tags=["vs_check_raise", adv, cat, tex.wetness],
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


# --- S6: turn graders (2nd barrel + facing a turn bet), HU SRP ---
#
# Research grounding (docs/research/02-postflop-strategy.md §5.1-5.2): fire the
# turn on scare cards that weaken the caller's flop-continue range (overcards,
# board-pairing cards that strengthen the aggressor's story); check back bricks
# with air/medium showdown value; flush/straight-completing turns favor the
# CALLER's range (hero's blockers are unmodeled here), so barreling them without
# a hand is discouraged. Facing a turn barrel, discipline is pot-odds-first: a
# second barrel is stronger news than a lone c-bet but weaker than a check-raise.

# Per-turn-class barrel merit shift (§5.2 fire-frequency table).
_TURN_BARREL_SCARE = {
    "over": 0.6,  # overcard weakens the caller's pair-heavy continue range
    "pairing": 0.4,  # pairing card strengthens the barreler's story
    "straight": -0.2,  # context-dependent; slight give-up lean without blockers
    "flush": -0.4,  # caller's range improved; hero is unprotected sans blockers
    "blank": -0.5,  # bricks are give-up cards for the bluffing part of the range
}
_TURN_FOLD_BASE = 0.8  # vs a 2nd barrel: above _merits_vs_cbet's 0.6, below vs_check_raise's 1.6
_TURN_SCARE_FOLD_BONUS = 0.3  # scare turns make the barrel story credible -> fold a bit more
_TURN_SCARE_CLASSES = ("over", "flush", "straight")


def _merits_turn_barrel(
    adv: str, texture: Texture, cat: str, turn_class: str, in_position: bool
) -> tuple[float, float, float]:
    """Return (check, bet_small, bet_big) merit scores (proxy EV, ~bb) for hero —
    the flop c-bettor deciding whether to fire the turn.

    `texture` is the FLOP texture (classify(board[:3])); `turn_class` is the
    turn card's class vs the flop (turn_card_class). §5.1: barrel scare cards
    and strong hands/draws; give up bricks with air, pot-control medium
    showdown value, and give up more OOP.
    """
    value = _CAT_VALUE[cat]
    adv_bonus = {"hero": 1.0, "neutral": 0.0, "villain": -1.0}[adv]
    scare = _TURN_BARREL_SCARE[turn_class]

    check = 1.0
    if cat == "air":
        check += 1.2  # give up more air on the turn than the flop (§5.1)
    elif cat == "weak_made":
        check += 0.6  # medium showdown value realizes best by pot-controlling
    if adv != "hero":
        check += 0.6
    if turn_class in ("flush", "straight"):
        check += 0.4  # the board improved the caller's range
    if turn_class == "blank" and cat in ("air", "weak_made"):
        check += 0.4  # bricks are give-ups without a real hand or scare card
    if not in_position:
        check += 0.3  # OOP barrels need more; checking ranges are wider OOP

    bet = value + adv_bonus + scare
    small = bet
    big = bet
    if texture.wetness == "dry":
        small += 0.3  # static boards keep the small-sizing lean from the flop
    if turn_class in ("over", "pairing"):
        big += 0.3  # scare cards support the bigger, polarizing 2nd barrel
    if cat in ("strong", "draw"):
        big += 0.3  # value + semibluff combo draws size up (§5.1 best barrels)
    else:
        big -= 0.8  # never pile big money in with air/marginal on the turn
    return check, small, big


def _merits_vs_turn_bet(
    value: float, price: float, cat: str, turn_class: str
) -> tuple[float, float, float]:
    """Return (fold, call, raise) merit scores (proxy EV, ~bb) for hero — the
    flop caller now facing a turn barrel.

    Pot-odds-first (§5.4 equity realization + pot-odds discipline): `price` =
    faced bet / pot (incl. the bet). A 2nd barrel is a stronger strength signal
    than a lone c-bet (fold baseline 0.8 > vs_cbet's 0.6) but far weaker than a
    check-raise; scare turns (§5.2) make the barreler's story credible, so
    folding gains merit on them.
    """
    fold = _TURN_FOLD_BASE
    if cat == "air":
        fold += 1.2
    elif cat == "weak_made":
        fold += 0.4
    fold += price * 1.5  # worse price (bigger barrel) -> folding better
    if turn_class in _TURN_SCARE_CLASSES:
        fold += _TURN_SCARE_FOLD_BONUS
    fold -= value * 0.6  # strong made hands / draws rarely fold

    call = value
    call += (0.5 - price) * 2.0  # pot-odds discipline: cheap -> call, dear -> fold
    if cat == "air":
        call -= 1.2  # bluff-catching pure air vs two barrels is bad
    elif cat == "weak_made" and turn_class == "blank":
        call += 0.4  # a brick changes nothing — keep bluff-catching marginal pairs

    if cat == "strong":
        raise_ = value + 0.4  # value raise; worse hands continue vs the barrel
    elif cat == "draw":
        raise_ = value - 0.6  # one card to come: semibluff raise is thin, call is fine
    elif cat == "weak_made":
        raise_ = -1.0  # never raise-bluff-catch a marginal made hand
    else:  # air
        raise_ = -1.4
    return fold, call, raise_


def grade_turn_barrel(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    if spot.street != Street.TURN:
        raise ValueError("grade_turn_barrel is turn-only")
    board = spot.board
    tex = classify(board[:3])  # flop texture — deliberate flop slice
    tclass = turn_card_class(board)
    ctx = spot.node_context[0] if spot.node_context else NodeContext.TURN_BARREL
    villain = _villain_pos(spot)
    adv = range_advantage(ctx, spot.hero.position, villain, tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    small, big = _bet_sizes(spot)
    rationale = _postflop_rationale(NodeContext.TURN_BARREL, spot.hero.position, villain)

    m_check, m_small, m_big = _merits_turn_barrel(
        adv, tex, cat, tclass, _in_position(spot.hero.position, villain)
    )
    if is_multiway(spot):
        mw = _apply_multiway(
            {"check": m_check, "small": m_small, "big": m_big},
            cat_effective=cat,
            facing_side=False,
        )
        m_check, m_small, m_big = mw["check"], mw["small"], mw["big"]
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
    leak = int(LeakCategory.TURN_BARREL)

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": leak,
        "is_mixed": is_mixed,
    }
    tags = ["turn_barrel", adv, cat, tex.wetness, tclass]

    def _size_label(size: float | None) -> str:
        if size is None:
            return "check"
        if big and small and big != small:
            return "big bet" if size >= big else "small bet"
        return "bet"

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=tags,
            explanation=(
                f"{tclass} turn on a {tex.wetness} flop ({adv} range advantage); "
                f"hero has {cat}: {_size_label(best.size_bb)} is the play."
            ),
        )
        if rationale:
            result.authored_rationale = rationale
        return result

    chosen = _match(evals, decision, small, big)
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))

    if chosen.action == best.action and chosen.size_bb == best.size_bb:
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
            f"{cat} on a {tclass} turn ({adv} range advantage): "
            f"{_size_label(best.size_bb)} is the play."
        )
    else:
        why = (
            f"{cat} on a {tclass} turn ({adv} range advantage): best is "
            f"{_size_label(best.size_bb)}; you chose {_size_label(chosen.size_bb)} "
            f"(-{ev_loss}bb)."
        )

    bet_evals = [e for e in evals if e.action == ActionType.BET]
    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        sizing_correctness=_bet_sizing_verdict(bet_evals, chosen),
        rationale_tags=tags,
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


def grade_vs_turn_bet(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    if spot.street != Street.TURN:
        raise ValueError("grade_vs_turn_bet is turn-only")
    board = spot.board
    tex = classify(board[:3])  # flop texture — deliberate flop slice
    tclass = turn_card_class(board)
    aggressor = spot.facing or _villain_pos(spot)
    # Defender-frame advantage label for the tags/prose (same frame as
    # grade_vs_cbet — hero is the caller here); merits stay pot-odds-first.
    adv = range_advantage_defender(aggressor, spot.hero.position, tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    value = _HAND_VALUE[cat]
    faced, pot = _faced_call_and_pot(spot)
    price = faced / pot if pot > 0 else 0.5
    rationale = _postflop_rationale(NodeContext.VS_TURN_BET, spot.hero.position, aggressor)

    # N4b: the spot may offer two RAISE legs (small/big). The single action-level
    # RAISE eval keys on the BIG leg — max(), not first-leg next(), so a two-leg
    # spot can't ordering-dependently grab the small leg. On single-leg spots
    # (all pre-N4b flows) max == the one leg: byte-identical.
    raise_size = max(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.RAISE and la.min_bb),
        default=None,
    )
    m_fold, m_call, m_raise = _merits_vs_turn_bet(value, price, cat, tclass)
    # F5: price-calibrate the marginal catcher's fold share (α ceiling + A1
    # fold-credit floor, RES-D §5) — `price` here IS the size-exact α.
    m_fold = _calibrate_catcher_fold(m_fold, m_call, m_raise, alpha=price, cat=cat)
    if is_multiway(spot):
        mw = _apply_multiway(
            {"fold": m_fold, "call": m_call, "raise": m_raise},
            cat_effective=cat,
            facing_side=True,
        )
        m_fold, m_call, m_raise = mw["fold"], mw["call"], mw["raise"]
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
    leak = int(LeakCategory.VS_TURN_BET)

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": leak,
        "is_mixed": is_mixed,
    }
    tags = ["vs_turn_bet", adv, cat, tex.wetness, tclass]

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=tags,
            explanation=(
                f"{cat} facing a turn barrel on a {tclass} turn "
                f"({adv} range advantage): {best.action.value} is the play."
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
        why = f"{cat} on a {tclass} turn ({adv} edge): {best.action.value} is the play."
    else:
        why = (
            f"{cat} on a {tclass} turn ({adv} edge): best is {best.action.value}; "
            f"you chose {decision.action.value} (-{ev_loss}bb)."
        )

    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        sizing_correctness=_raise_sizing_verdict(spot, decision, tex.wetness, chosen),
        rationale_tags=tags,
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


# --- S7: river graders (value-bet/bluff + facing a river bet), HU SRP ---
#
# Clone of the S6 turn anatomy: same band constants, merit -> freq(3dp) ->
# EV(2dp) -> correctness ladder. Merits stay flat constants + pot odds
# (_faced_call_and_pot); NO equity_vs_range (Gate-1). The one river-specific
# rule is BUSTED-DRAW DEMOTION: with no cards to come, `_hand_category`'s
# "draw" tier (flush_draw/oesd flags still fire on 5-card boards) has ZERO
# outs — both graders demote it to "air" (bluff-candidate) for merits AND
# tags. `_hand_category` itself is untouched (flop/turn callers unaffected).

# Per-river-class barrel merit shift: scare rivers keep the three-street story
# credible; draw-completing rivers land in the two-time caller's range.
_RIVER_BARREL_SCARE = {
    "over": 0.4,  # overcard still weakens the caller's pair range, less so than the turn
    "pairing": 0.4,  # pairing card keeps favoring the barreler's story
    "straight": -0.4,  # the caller's flop+turn calls hold the straights
    "flush": -0.6,  # completed flush: the caller's suited calls got there
    "blank": -0.3,  # bricks: value still bets, bluffs have run out of story
}
_RIVER_FOLD_BASE = 1.0  # a THIRD barrel: above the turn's 0.8, below vs_check_raise's 1.6
_RIVER_SCARE_FOLD_BONUS = 0.4
_RIVER_SCARE_CLASSES = ("over", "flush", "straight")


def _river_cat_effective(cat: str) -> str:
    """Busted-draw demotion (S7): on the river a 'draw' has zero outs — it is a
    bluff-candidate, never the 1.2 value tier. Used for BOTH merits and tags."""
    return "air" if cat == "draw" else cat


def _merits_river_barrel(
    adv: str, texture: Texture, cat: str, river_class: str, in_position: bool
) -> tuple[float, float, float]:
    """Return (check, bet_small, bet_big) merit scores (proxy EV, ~bb) for hero —
    the flop+turn aggressor deciding whether to fire the river.

    Value-bet discipline: the river is the last bet — strong hands size up and
    polarize; marginal made hands realize their showdown value for free by
    checking (a third bet folds out worse, gets called by better); busted draws
    arrive here already demoted to "air" and only barrel where a scare river
    keeps the story credible. `cat` is the DEMOTED category.
    """
    value = _CAT_VALUE[cat]
    adv_bonus = {"hero": 1.0, "neutral": 0.0, "villain": -1.0}[adv]
    scare = _RIVER_BARREL_SCARE[river_class]

    check = 1.2  # checking the river is final — showdown value realizes for free
    if cat == "air":
        check += 1.2  # most bluffs have given up by the river
    elif cat == "weak_made":
        check += 1.0  # thin value after two calls mostly gets called by better
    if adv != "hero":
        check += 0.6
    if river_class in ("flush", "straight"):
        check += 0.5  # the board completed the caller's draws
    if not in_position:
        check += 0.3

    bet = value + adv_bonus + scare
    small = bet
    big = bet
    if texture.wetness == "dry":
        small += 0.3  # static boards keep the small-sizing lean
    if cat == "strong":
        big += 0.5  # river bets are polar: strong value sizes up
    else:
        big -= 1.0  # never pile the big river bet in thin or with air
    return check, small, big


def _merits_vs_river_bet(
    value: float, price: float, cat: str, river_class: str
) -> tuple[float, float, float]:
    """Return (fold, call, raise) merit scores (proxy EV, ~bb) for hero — the
    flop+turn caller now facing a river bet.

    Pot-odds + bluff-frequency discipline: the price sets the bluff-catch bar,
    a third barrel is the strongest bet-signal short of a check-raise (fold
    baseline 1.0 > turn's 0.8), and scare rivers make the story credible so
    folding gains merit on them. `cat` is the DEMOTED category (busted draws
    are "air" — with zero outs they are the clearest folds of all).
    """
    fold = _RIVER_FOLD_BASE
    if cat == "air":
        fold += 1.2
    elif cat == "weak_made":
        fold += 0.4
    fold += price * 1.5  # worse price (bigger river bet) -> folding better
    if river_class in _RIVER_SCARE_CLASSES:
        fold += _RIVER_SCARE_FOLD_BONUS
    fold -= value * 0.6  # strong made hands rarely fold

    call = value
    call += (0.5 - price) * 2.0  # pot-odds discipline: cheap -> call, dear -> fold
    if cat == "air":
        call -= 1.4  # no equity, no future streets: bluff-catching air is the worst call
    elif cat == "weak_made" and river_class == "blank":
        call += 0.4  # a brick river changes nothing — keep the disciplined bluff-catches

    if cat == "strong":
        raise_ = value + 0.4  # value raise; worse hands bet-called the river
    elif cat == "weak_made":
        raise_ = -1.0  # never raise a marginal bluff-catcher
    else:  # air (incl. demoted busted draws)
        raise_ = -1.4
    return fold, call, raise_


def grade_river_barrel(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    if spot.street != Street.RIVER:
        raise ValueError("grade_river_barrel is river-only")
    board = spot.board
    tex = classify(board[:3])  # flop texture — deliberate flop slice
    tclass = turn_card_class(board)
    rclass = river_card_class(board)
    ctx = spot.node_context[0] if spot.node_context else NodeContext.RIVER_BARREL
    # Villain-position convention (the S6 check-raiser lesson): pass
    # `spot.facing or _villain_pos(spot)` — the flop-caller-turned-defender's
    # seat, NEVER hero's own, or the in-position read corrupts.
    villain = spot.facing or _villain_pos(spot)
    adv = range_advantage(ctx, spot.hero.position, villain, tex, river_class=rclass)
    cat = _hand_category(spot.hero.hole_cards, board)
    cat_effective = _river_cat_effective(cat)  # busted draws demote to air
    small, big = _bet_sizes(spot)
    rationale = _postflop_rationale(NodeContext.RIVER_BARREL, spot.hero.position, villain)

    m_check, m_small, m_big = _merits_river_barrel(
        adv, tex, cat_effective, rclass, _in_position(spot.hero.position, villain)
    )
    if is_multiway(spot):
        mw = _apply_multiway(
            {"check": m_check, "small": m_small, "big": m_big},
            cat_effective=cat_effective,
            facing_side=False,
        )
        m_check, m_small, m_big = mw["check"], mw["small"], mw["big"]
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
    leak = int(LeakCategory.RIVER_BARREL)

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": leak,
        "is_mixed": is_mixed,
    }
    tags = ["river_barrel", adv, cat_effective, tex.wetness, tclass, rclass]

    def _size_label(size: float | None) -> str:
        if size is None:
            return "check"
        if big and small and big != small:
            return "big bet" if size >= big else "small bet"
        return "bet"

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=tags,
            explanation=(
                f"{rclass} river on a {tex.wetness} flop ({adv} range advantage); "
                f"hero has {cat_effective}: {_size_label(best.size_bb)} is the play."
            ),
        )
        if rationale:
            result.authored_rationale = rationale
        return result

    chosen = _match(evals, decision, small, big)
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))

    if chosen.action == best.action and chosen.size_bb == best.size_bb:
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
            f"{cat_effective} on a {rclass} river ({adv} range advantage): "
            f"{_size_label(best.size_bb)} is the play."
        )
    else:
        why = (
            f"{cat_effective} on a {rclass} river ({adv} range advantage): best is "
            f"{_size_label(best.size_bb)}; you chose {_size_label(chosen.size_bb)} "
            f"(-{ev_loss}bb)."
        )

    bet_evals = [e for e in evals if e.action == ActionType.BET]
    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        sizing_correctness=_bet_sizing_verdict(bet_evals, chosen),
        rationale_tags=tags,
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


def grade_vs_river_bet(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    if spot.street != Street.RIVER:
        raise ValueError("grade_vs_river_bet is river-only")
    board = spot.board
    tex = classify(board[:3])  # flop texture — deliberate flop slice
    tclass = turn_card_class(board)
    rclass = river_card_class(board)
    # Villain-position convention (the S6 check-raiser lesson): pass
    # `spot.facing or _villain_pos(spot)` — the river BETTOR's seat, NEVER
    # hero's own, or the defender's positional read corrupts.
    aggressor = spot.facing or _villain_pos(spot)
    # Defender-frame advantage label (grade_vs_turn_bet precedent — hero is the
    # caller); range_advantage_defender is street-agnostic, reused VERBATIM.
    adv = range_advantage_defender(aggressor, spot.hero.position, tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    cat_effective = _river_cat_effective(cat)  # busted draws demote to air
    value = _HAND_VALUE[cat_effective]
    faced, pot = _faced_call_and_pot(spot)
    price = faced / pot if pot > 0 else 0.5
    rationale = _postflop_rationale(NodeContext.VS_RIVER_BET, spot.hero.position, aggressor)

    # N4b: the spot may offer two RAISE legs (small/big). The single action-level
    # RAISE eval keys on the BIG leg — max(), not first-leg next(), so a two-leg
    # spot can't ordering-dependently grab the small leg. On single-leg spots
    # (all pre-N4b flows) max == the one leg: byte-identical.
    raise_size = max(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.RAISE and la.min_bb),
        default=None,
    )
    m_fold, m_call, m_raise = _merits_vs_river_bet(value, price, cat_effective, rclass)
    if is_multiway(spot):
        mw = _apply_multiway(
            {"fold": m_fold, "call": m_call, "raise": m_raise},
            cat_effective=cat_effective,
            facing_side=True,
        )
        m_fold, m_call, m_raise = mw["fold"], mw["call"], mw["raise"]
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
    leak = int(LeakCategory.VS_RIVER_BET)

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": leak,
        "is_mixed": is_mixed,
    }
    tags = ["vs_river_bet", adv, cat_effective, tex.wetness, tclass, rclass]

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=tags,
            explanation=(
                f"{cat_effective} facing a river bet on a {rclass} river "
                f"({adv} range advantage): {best.action.value} is the play."
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
        why = f"{cat_effective} on a {rclass} river ({adv} edge): {best.action.value} is the play."
    else:
        why = (
            f"{cat_effective} on a {rclass} river ({adv} edge): best is {best.action.value}; "
            f"you chose {decision.action.value} (-{ev_loss}bb)."
        )

    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        sizing_correctness=_raise_sizing_verdict(spot, decision, tex.wetness, chosen),
        rationale_tags=tags,
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


# --- M5 (Epic 5, RES-G Slice C): HU limped-pot flop graders ------------------
#
# The app's FIRST limped-pot postflop node family, HU only. Directions per
# RES-G §4b (all direction-only, no MDF / no solver, EVs approximate):
#   1. No preflop aggressor → no range-advantage baseline: the edge read
#      reuses `range_advantage_defender`'s score=0 no-baseline start and lets
#      board texture decide (both limped-pot ranges are calling-type ranges,
#      so the defender-view texture terms — low/connected/wet connects, high/
#      dry misses — apply to hero's own range; position breaks the tie).
#   2. Capped ranges both sides: big bets are over-repped by value — reward
#      small stabs, penalize bloating with medium strength, tighten the
#      marginal bluff-catch vs a big lead.
#   3. Whoever bets first should bet SMALL + polar (strong + some air, check
#      the middle).
#   4. The OOP player mostly checks.
#   5. Multiway dampening seam (`_apply_multiway`) is wired but dormant —
#      these graders only ever see HU spots (the mappers gate 2 preflop
#      entrants), so `is_multiway` is structurally False today; the seam
#      exists so a future multiway limped grader (RES-G Slice D) inherits it.
#
# Every direction-shaping number lives in content/postflop/limped.json
# `sizing_rules` (strategy-as-data), not here.

_LIMPED_RULES: dict | None = None


def _limped_rules(node: str) -> dict:
    """The §4b direction knobs for `node` ('limped_lead' | 'limped_vs_lead'),
    from content/postflop/limped.json `sizing_rules`. Lazily loaded once; a
    missing pack/key fails loud — the strategy IS the content."""
    global _LIMPED_RULES
    if _LIMPED_RULES is None:
        pack = load_pack_file(_POSTFLOP_CONTENT_DIR / "limped.json")
        _LIMPED_RULES = pack.sizing_rules
    return _LIMPED_RULES[node]


def _limped_edge(hero_pos: Position, villain_pos: Position, texture: Texture) -> str:
    """Texture-decided edge in a limped pot: 'hero' | 'villain' | 'neutral'.

    Reuses `range_advantage_defender` (§4b-1: its score=0 start IS the
    no-preflop-aggressor read) with hero in the defender slot — a limped-pot
    range is a calling-type range, so the caller-view texture terms transfer —
    then relabels the verdict to hero/villain."""
    read = range_advantage_defender(villain_pos, hero_pos, texture)
    return {"defender": "hero", "aggressor": "villain", "neutral": "neutral"}[read]


def _merits_limped_lead(
    edge: str, texture: Texture, cat: str, in_position: bool
) -> tuple[float, float, float]:
    """(check, bet_small, bet_big) merits for hero deciding whether to lead a
    HU limped flop. Small polar lead + mostly-check-OOP + never-bloat-the-
    middle, all knob-driven from content (§4b-2/3/4)."""
    r = _limped_rules("limped_lead")
    edge_bonus = {"hero": 1.0, "neutral": 0.0, "villain": -1.0}[edge] * r["edge_weight"]

    check = r["check_base"]
    if cat == "air":
        check += r["check_air_bonus"]
    elif cat == "weak_made":
        check += r["check_middle_bonus"]  # §4b-4: check the medium made hands
    if not in_position:
        check += r["check_oop_bonus"]  # §4b-4: the OOP player mostly checks
    if texture.wetness == "wet":
        check += r["check_wet_bonus"]

    bet = r["value"][cat] + edge_bonus
    small = bet + r["small_bonus"]  # §4b-3: small size preferred
    big = bet - r["big_penalty"]  # §4b-2: big bets over-repped by value
    if cat == "weak_made":
        big -= r["big_middle_penalty"]  # never bloat medium strength
    elif cat == "air":
        big -= r["big_air_penalty"]
    return check, small, big


def _merits_limped_vs_lead(
    edge: str, price: float, texture: Texture, cat: str
) -> tuple[float, float, float]:
    """(fold, call, raise) merits for hero facing a lead in a HU limped flop.
    `price` = faced bet / pot (pot already includes the bet). Capped-range
    discipline: fold air, price the marginal catch, and tighten it further vs
    a BIG lead (§4b-2: limped-pot big bets are value-heavy)."""
    r = _limped_rules("limped_vs_lead")
    value = r["value"][cat]
    edge_bonus = {"hero": 1.0, "neutral": 0.0, "villain": -1.0}[edge] * r["edge_weight"]

    fold = r["fold_base"]
    if cat == "air":
        fold += r["fold_air_bonus"]
    elif cat == "weak_made":
        fold += r["fold_middle_bonus"]
        if price >= r["big_lead_price"]:
            fold += r["big_lead_middle_fold_bonus"]  # §4b-2: big lead → real strength
    fold += price * r["fold_price_weight"]
    if edge == "villain":
        fold += r["fold_edge_bonus"]
    fold -= value * r["fold_value_relief"]

    call = value + edge_bonus
    call += (r["call_price_anchor"] - price) * r["call_price_weight"]
    if cat == "air":
        call -= r["call_air_penalty"]

    if cat == "strong":
        raise_ = value + r["raise_strong_bonus"] + edge_bonus
    elif cat == "draw":
        raise_ = value - r["raise_draw_penalty"]
        if texture.wetness == "wet" and edge == "hero":
            raise_ += r["raise_semibluff_wet_bonus"]
    elif cat == "weak_made":
        raise_ = r["raise_middle"]
    else:  # air
        raise_ = r["raise_air"]
    return fold, call, raise_


def grade_limped_lead(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    """HU limped flop, hero can lead (check / bet small / bet big)."""
    if spot.street != Street.FLOP:
        raise ValueError("grade_limped_lead is flop-only")
    board = spot.board[:3]
    tex = classify(board)
    villain = _villain_pos(spot)
    edge = _limped_edge(spot.hero.position, villain, tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    small, big = _bet_sizes(spot)
    rationale = _postflop_rationale(NodeContext.LIMPED_LEAD, spot.hero.position, villain)

    m_check, m_small, m_big = _merits_limped_lead(
        edge, tex, cat, _in_position(spot.hero.position, villain)
    )
    if is_multiway(spot):  # dormant HU (mappers gate 2 entrants); Slice D seam
        mw = _apply_multiway(
            {"check": m_check, "small": m_small, "big": m_big},
            cat_effective=cat,
            facing_side=False,
        )
        m_check, m_small, m_big = mw["check"], mw["small"], mw["big"]
    freqs = _frequencies([m_check, m_small, m_big])

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
    tags = ["limped_lead", edge, cat, tex.wetness]

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": int(LeakCategory.LIMPED_LEAD),
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
            rationale_tags=tags,
            explanation=(
                f"limped pot ({edge} texture edge), hero has {cat}: "
                f"{_size_label(best.size_bb)} is the play."
            ),
        )
        if rationale:
            result.authored_rationale = rationale
        return result

    chosen = _match(evals, decision, small, big)
    ev_loss = max(0.0, round(best.ev_bb - chosen.ev_bb, 2))

    if chosen.action == best.action and chosen.size_bb == best.size_bb:
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
            f"{cat} in a limped pot on a {tex.wetness} board ({edge} texture edge): "
            f"{_size_label(best.size_bb)} is the play."
        )
    else:
        why = (
            f"{cat} in a limped pot on a {tex.wetness} board ({edge} texture edge): "
            f"best is {_size_label(best.size_bb)}; you chose "
            f"{_size_label(chosen.size_bb)} (-{ev_loss}bb)."
        )

    bet_evals = [e for e in evals if e.action == ActionType.BET]
    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        sizing_correctness=_bet_sizing_verdict(bet_evals, chosen),
        rationale_tags=tags,
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result


def grade_limped_vs_lead(
    spot: Spot, hero_range: str | None, villain_range: str | None, decision: Decision | None
) -> EvaluationResult:
    """HU limped flop, hero faces a lead (fold / call / raise)."""
    if spot.street != Street.FLOP:
        raise ValueError("grade_limped_vs_lead is flop-only")
    board = spot.board[:3]
    tex = classify(board)
    villain = spot.facing or _villain_pos(spot)
    edge = _limped_edge(spot.hero.position, villain, tex)
    cat = _hand_category(spot.hero.hole_cards, board)
    faced, pot = _faced_call_and_pot(spot)
    price = faced / pot if pot > 0 else 0.5
    rationale = _postflop_rationale(NodeContext.LIMPED_VS_LEAD, spot.hero.position, villain)

    raise_size = max(
        (la.min_bb for la in spot.legal_actions if la.action == ActionType.RAISE and la.min_bb),
        default=None,
    )
    m_fold, m_call, m_raise = _merits_limped_vs_lead(edge, price, tex, cat)
    if is_multiway(spot):  # dormant HU (mappers gate 2 entrants); Slice D seam
        mw = _apply_multiway(
            {"fold": m_fold, "call": m_call, "raise": m_raise},
            cat_effective=cat,
            facing_side=True,
        )
        m_fold, m_call, m_raise = mw["fold"], mw["call"], mw["raise"]
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
    tags = ["limped_vs_lead", edge, cat, tex.wetness]

    base_kwargs = {
        "per_action": evals,
        "best_action": best,
        "provider": ProviderKind.HEURISTIC,
        "coverage": Coverage.FULL,
        "leak_category": int(LeakCategory.LIMPED_VS_LEAD),
        "is_mixed": is_mixed,
    }

    if decision is None:
        result = EvaluationResult(
            **base_kwargs,
            rationale_tags=tags,
            explanation=(
                f"{cat} facing a lead in a limped pot on a {tex.wetness} board "
                f"({edge} texture edge): {best.action.value} is the play."
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
        why = (
            f"{cat} vs a limped-pot lead on a {tex.wetness} board ({edge} edge): "
            f"{best.action.value} is the play."
        )
    else:
        why = (
            f"{cat} vs a limped-pot lead on a {tex.wetness} board ({edge} edge): best is "
            f"{best.action.value}; you chose {decision.action.value} (-{ev_loss}bb)."
        )

    result = EvaluationResult(
        **base_kwargs,
        chosen_eval=ChosenEval(frequency=chosen.frequency, ev_bb=chosen.ev_bb),
        ev_loss_bb=ev_loss,
        correctness=correctness,
        sizing_correctness=_raise_sizing_verdict(spot, decision, tex.wetness, chosen),
        rationale_tags=tags,
        explanation=why,
    )
    if rationale:
        result.authored_rationale = rationale
    return result
