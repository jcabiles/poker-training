"""Persona postflop engine (S4) — analytic strength ladder + lever-shaped
mixed decisions.

Pure domain, no Monte-Carlo in the hot loop: `strength_bucket` classifies a
hand analytically (best-5 rank tuples + rank/suit counting), and
`sample_postflop_decision` maps (bucket, draw, facing state) through a shared
merit table shaped multiplicatively by the pack's postflop levers. Mechanics
(the merit numbers) live here; every persona-differentiating number lives in
`content/personas/*.json` (PersonaPack.postflop). The rng is the HAND's
injected `random.Random` — same convention as `personas.py`.

Frozen interface + behavior rules: docs/ai-dlc/specs/simulate-s4.md.
"""

from __future__ import annotations

import itertools
import random
from enum import StrEnum
from typing import TYPE_CHECKING

from app.domain.action import Decision
from app.domain.content.models import PersonaPack, PersonaPostflop
from app.domain.equity import _RIDX, _eval5
from app.domain.spot import ActionType, Card, LegalAction, Street
from app.domain.table.sizing import postflop_node_key, pot_fraction_to_bb

if TYPE_CHECKING:
    from app.domain.table.postflop_context import PostflopContext

_ACE = 12  # rank index of the ace in equity.RANKS
_KING = 11


class StrengthBucket(StrEnum):
    """7-rung made-hand ladder — disjoint by construction (spec-pinned):
    sets are ALWAYS monster, never two_pair_plus; straights on paired boards
    stay monster; a pocket pair below the top board card is always
    middle_pair (never overpair_tptk/top_pair)."""

    MONSTER = "monster"
    TWO_PAIR_PLUS = "two_pair_plus"
    OVERPAIR_TPTK = "overpair_tptk"
    TOP_PAIR = "top_pair"
    MIDDLE_PAIR = "middle_pair"
    ACE_HIGH = "ace_high"
    AIR = "air"


class DrawCategory(StrEnum):
    NONE = "none"
    WEAK = "weak"  # gutshot / backdoor-flush+overcard class
    STRONG = "strong"  # flush draw / OESD / combo


class SizeBucket(StrEnum):
    """RES-E size taxonomy on live pot-fraction (faced_bb / pot-before-the-bet).
    Shared vocabulary for F1 (faced defense) and F2 (chosen-size bluffing)."""

    SMALL = "small"  # <= 0.40 pot
    MEDIUM = "medium"  # 0.41 - 0.70
    LARGE = "large"  # 0.71 - 1.10
    OVERBET = "overbet"  # > 1.10


def size_bucket(pot_fraction: float) -> SizeBucket:
    """RES-E §2 cutoffs, locked: computed on the LIVE pot-fraction at decision
    time, never on the discrete authored sizing keys."""
    if pot_fraction <= 0.40:
        return SizeBucket.SMALL
    if pot_fraction <= 0.70:
        return SizeBucket.MEDIUM
    if pot_fraction <= 1.10:
        return SizeBucket.LARGE
    return SizeBucket.OVERBET


_RUNG = {
    StrengthBucket.AIR: 0,
    StrengthBucket.ACE_HIGH: 1,
    StrengthBucket.MIDDLE_PAIR: 2,
    StrengthBucket.TOP_PAIR: 3,
    StrengthBucket.OVERPAIR_TPTK: 4,
    StrengthBucket.TWO_PAIR_PLUS: 5,
    StrengthBucket.MONSTER: 6,
}


def _best5(cards: list[Card]) -> tuple:
    """Best 5-card rank tuple over 5/6/7 cards (analytic, no MC)."""
    rs = [_RIDX[c[0]] for c in cards]
    ss = [c[1] for c in cards]
    best: tuple | None = None
    for idx in itertools.combinations(range(len(cards)), 5):
        v = _eval5([rs[i] for i in idx], [ss[i] for i in idx])
        if best is None or v > best:
            best = v
    return best  # type: ignore[return-value]  # len(cards) >= 5 always


def _high_card_bucket(hole_hi: int) -> StrengthBucket:
    return StrengthBucket.ACE_HIGH if hole_hi >= _KING else StrengthBucket.AIR


def _pair_bucket(pair_rank: int, kicker: int, board_top: int) -> StrengthBucket:
    if pair_rank != board_top:
        return StrengthBucket.MIDDLE_PAIR
    # Top pair: top kicker = ace, or king when top pair IS aces.
    top_kicker = _ACE if pair_rank != _ACE else _KING
    return StrengthBucket.OVERPAIR_TPTK if kicker >= top_kicker else StrengthBucket.TOP_PAIR


def _made_bucket(hole: tuple[Card, Card], board: list[Card]) -> StrengthBucket:
    r1, r2 = _RIDX[hole[0][0]], _RIDX[hole[1][0]]
    hole_hi = max(r1, r2)
    pocket = r1 == r2
    board_ranks = {_RIDX[c[0]] for c in board}
    board_top = max(board_ranks)
    rank = _best5(list(hole) + list(board))
    cat = rank[0]

    if cat >= 4:  # straight/flush/boat/quads — monster even on paired boards
        return StrengthBucket.MONSTER
    if cat == 3:  # trips: set or trips (hole card plays) = monster; board trips: high card
        return StrengthBucket.MONSTER if rank[1] in (r1, r2) else _high_card_bucket(hole_hi)
    if cat == 2:  # two pair
        if pocket:  # pocket pair + board pair (below set strength)
            # F7 bug 1: only a real strong two pair when the POCKET is the top
            # pair of the best five (pocket above the board's paired rank —
            # TT on 883). An under-pocket-pair also reads "two pair" to _eval5
            # (22 on 883 = "eights and deuces"), but the board pair plays for
            # everyone; its true showdown class is the same pocket-underpair
            # the unpaired-board cat==1 rule maps to MIDDLE_PAIR (22 on 883
            # == 22 on K72). Pre-fix it classed TWO_PAIR_PLUS and raised a
            # 3bb-into-6bb bet at .734 with 0.375 equity while AK-high
            # (0.499 equity, same board) folded .406.
            if rank[1] == r1:
                return StrengthBucket.TWO_PAIR_PLUS
            return StrengthBucket.MIDDLE_PAIR
        if r1 in board_ranks and r2 in board_ranks:  # both hole cards playing
            return StrengthBucket.TWO_PAIR_PLUS
        if r1 in board_ranks or r2 in board_ranks:  # one pair + board pair
            pair_rank = r1 if r1 in board_ranks else r2
            kicker = r2 if pair_rank == r1 else r1
            return _pair_bucket(pair_rank, kicker, board_top)
        return _high_card_bucket(hole_hi)  # plays the board's two pair
    if cat == 1:  # one pair
        if pocket:  # can't equal board_top (that would be a set)
            return (
                StrengthBucket.OVERPAIR_TPTK if r1 > board_top else StrengthBucket.MIDDLE_PAIR
            )
        if rank[1] in (r1, r2):  # a hole card pairs the board
            pair_rank = rank[1]
            kicker = r2 if pair_rank == r1 else r1
            return _pair_bucket(pair_rank, kicker, board_top)
        return _high_card_bucket(hole_hi)  # board-paired, hero unpaired
    return _high_card_bucket(hole_hi)


def _straight_out_ranks(hole_ranks: set[int], all_ranks: set[int]) -> int:
    """Count distinct ranks that would complete a 5-high-run straight using at
    least one hole card. >=2 => OESD/double-gutter class, ==1 => gutshot."""
    outs = 0
    for out in range(13):
        if out in all_ranks:
            continue
        new = all_ranks | {out}
        for lo in range(-1, 9):  # lo == -1 is the wheel (A-2-3-4-5)
            window = {r if r >= 0 else _ACE for r in range(lo, lo + 5)}
            if window <= new and out in window and window & hole_ranks:
                outs += 1
                break
    return outs


def _draw_category(hole: tuple[Card, Card], board: list[Card]) -> DrawCategory:
    cards = list(hole) + list(board)
    suit_counts: dict[str, int] = {}
    for c in cards:
        suit_counts[c[1]] = suit_counts.get(c[1], 0) + 1
    hole_suits = {c[1] for c in hole}
    flush_draw = any(n == 4 and s in hole_suits for s, n in suit_counts.items())

    hole_ranks = {_RIDX[c[0]] for c in hole}
    all_ranks = {_RIDX[c[0]] for c in cards}
    straight_outs = _straight_out_ranks(hole_ranks, all_ranks)

    if flush_draw or straight_outs >= 2:
        return DrawCategory.STRONG
    backdoor_flush = len(board) == 3 and any(
        n == 3 and s in hole_suits for s, n in suit_counts.items()
    )
    overcard = max(hole_ranks) > max(_RIDX[c[0]] for c in board)
    if straight_outs == 1 or (backdoor_flush and overcard):
        return DrawCategory.WEAK
    return DrawCategory.NONE


def strength_bucket(
    hole: tuple[Card, Card], board: list[Card]
) -> tuple[StrengthBucket, DrawCategory]:
    """Analytic (bucket, draw) classification for hole cards on a 3/4/5-card
    board. On the RIVER (board len 5) DrawCategory is always NONE — busted
    draws land in AIR/ACE_HIGH by made strength."""
    made = _made_bucket(hole, board)
    draw = DrawCategory.NONE if len(board) >= 5 else _draw_category(hole, board)
    return made, draw


# --------------------------------------------------------------------------
# Merit tables — SHARED game mechanics (behavior rule 4). Levers from the
# pack shape these multiplicatively; no persona-specific number lives here.
# Base masses are pre-normalization merits (components > 1 are fine).
# --------------------------------------------------------------------------

# Unopened / matched-with-option: aggressive (bet or raise) vs check merit.
_AGG_BASE = {
    StrengthBucket.MONSTER: 0.85,
    StrengthBucket.TWO_PAIR_PLUS: 0.75,
    StrengthBucket.OVERPAIR_TPTK: 0.70,
    StrengthBucket.TOP_PAIR: 0.55,
    StrengthBucket.MIDDLE_PAIR: 0.30,
    StrengthBucket.ACE_HIGH: 0.05,
    StrengthBucket.AIR: 0.05,
}
_CHECK_BASE = {
    StrengthBucket.MONSTER: 0.15,
    StrengthBucket.TWO_PAIR_PLUS: 0.25,
    StrengthBucket.OVERPAIR_TPTK: 0.30,
    StrengthBucket.TOP_PAIR: 0.45,
    StrengthBucket.MIDDLE_PAIR: 0.70,
    StrengthBucket.ACE_HIGH: 0.95,
    StrengthBucket.AIR: 0.95,
}
# Facing chips: fold / call / raise merit. Calibration (refuter round 2):
# tuned so a stickiness ~1.0 persona folds to a flop c-bet ~0.45-0.55 and
# stickiness 1.8 lands ~0.25-0.35; call floors keep low-stickiness personas
# (nit, 0.6) calling with real pairs so AF isn't call-starved. AIR call base
# dropped 0.25->0.08 (A1) so no-draw air stops floating; drawing air is
# unaffected since _DRAW_CALL_BONUS (WEAK 0.20 / STRONG 0.55) still adds on
# top. Street-aware river "air-call ~0" gate is deferred to a later slice
# (P2a) — this change is street-neutral, no street/river logic added here.
_FOLD_BASE = {
    StrengthBucket.MONSTER: 0.0,
    StrengthBucket.TWO_PAIR_PLUS: 0.05,
    StrengthBucket.OVERPAIR_TPTK: 0.05,
    StrengthBucket.TOP_PAIR: 0.12,
    StrengthBucket.MIDDLE_PAIR: 0.35,
    StrengthBucket.ACE_HIGH: 0.60,
    StrengthBucket.AIR: 0.75,
}
_CALL_BASE = {
    StrengthBucket.MONSTER: 0.35,
    StrengthBucket.TWO_PAIR_PLUS: 0.55,
    StrengthBucket.OVERPAIR_TPTK: 0.70,
    StrengthBucket.TOP_PAIR: 0.78,
    StrengthBucket.MIDDLE_PAIR: 0.60,
    StrengthBucket.ACE_HIGH: 0.40,
    StrengthBucket.AIR: 0.08,
}
_RAISE_BASE = {
    StrengthBucket.MONSTER: 0.65,
    StrengthBucket.TWO_PAIR_PLUS: 0.40,
    StrengthBucket.OVERPAIR_TPTK: 0.25,
    StrengthBucket.TOP_PAIR: 0.10,
    StrengthBucket.MIDDLE_PAIR: 0.05,
    StrengthBucket.ACE_HIGH: 0.02,
    StrengthBucket.AIR: 0.02,
}
# Draw bonuses (semi-bluff aggression + drawing calls), added pre-lever.
_DRAW_AGG_BONUS = {DrawCategory.NONE: 0.0, DrawCategory.WEAK: 0.15, DrawCategory.STRONG: 0.35}
_DRAW_RAISE_BONUS = {DrawCategory.NONE: 0.0, DrawCategory.WEAK: 0.05, DrawCategory.STRONG: 0.15}
_DRAW_CALL_BONUS = {DrawCategory.NONE: 0.0, DrawCategory.WEAK: 0.20, DrawCategory.STRONG: 0.55}
# Structural constants (shared mechanics).
# River polarization (P2a Q1): on the river (opt-in via the `street` kwarg)
# raising is polar — value raises come from TWO_PAIR_PLUS+, bluff raises from
# the bluff cell; the one-pair middle (bluff-catchers) never raises, and air
# never calls. These buckets get their non-bluff raise merit floored to 0.0.
# OVERPAIR_TPTK is a coarse compromise: the merged bucket spans thin-value
# hands that a finer split would let raise; splitting it is a later slice.
_RIVER_RAISE_FLOOR = (
    StrengthBucket.MIDDLE_PAIR,
    StrengthBucket.TOP_PAIR,
    StrengthBucket.OVERPAIR_TPTK,
)
# W1-a (F6): the unopened river BET floor — strictly NARROWER than the raise
# floor. A middle pair on the river is a bluff-catcher, never a value bet, under
# a conservative HU/balanced-villain DEFAULT (it CAN value-bet vs capped/station
# ranges — a rank approximation, not a theorem). TOP_PAIR/OVERPAIR keep the thin
# river value bet (they are floored on the RAISE only). P2a floored the river
# raise + air-call; this closes the residual unopened-BET leak for MIDDLE_PAIR.
_RIVER_BET_FLOOR = (StrengthBucket.MIDDLE_PAIR,)
_BLUFF_RAISE_FACTOR = 0.3  # bluff-raising is structurally rarer than bluff-betting
_COMMIT_AGG_BOOST = 3.0  # SPR-commit shift toward call/jam
# W2-b (B5b, F7): the max fraction of a draw's CALL/RAISE bonus removed at full
# commitment when the draw is NOT value-committed (below T1) — a naked draw stops
# stacking off. Scaled by the commitment fraction c in [0,1]. FIT SEED.
_B5B_DRAW_DAMP = 0.7
# F3 bounded aggression (RES-D §0 saturation fix): the `aggression` lever is
# capped before it scales any merit. An uncapped maniac lever (15.0) multiplies
# one side of the un-normalized merit ratio so hard that rng.choices degenerates
# to near-argmax (top-pair unopened P(bet)=0.948, entropy 0.29 bits; with the
# SPR-commit boost the effective multiplier hit 15×3=45, monster-commit
# P(bet)=0.991, entropy 0.08 bits). The cap is a MECHANIC (shared compression
# law, lives in code per the S4 split); persona identity stays in the pack's
# lever. 5.6 = 1.75 × the highest non-maniac lever (lag 3.2), fitted by sweep
# (4.8/5.6/6.4 against the closed-loop harness): the cap is the identity map
# for every other authored persona (all ≤ 3.2 — their sampled decisions are
# byte-unchanged, F3-verified) while the maniac stays strictly the most
# aggressive persona everywhere the lever applies — per-node (exact-weight
# ordering test) AND in population AF (~3.2-3.3 vs lag ~2.1-2.5; the tighter
# 4.8 cap dropped maniac AF into lag's range). The commit interaction is
# bounded as a consequence (5.6 × 3 = 16.8, was 45). Mixing restored:
# top-pair unopened P(bet) 0.948 → 0.873 (entropy 0.29 → 0.55 bits) — see
# the F3 tests.
_AGGRESSION_CAP = 5.6

# F1 price-aware defense (RES-D §1a/§2 + RES-E buckets). α = B/(P+B) is the
# fold-CEILING for the bucket's representative size — an anchor the fold merit
# scales AGAINST, never a floor the engine clamps folds up to (A1 guardrail:
# no code path may assert fold >= anything derived from α/MDF).
_BUCKET_ALPHA = {
    SizeBucket.SMALL: 0.25,  # ~⅓ pot
    SizeBucket.MEDIUM: 0.375,  # ½–⅔ pot
    SizeBucket.LARGE: 0.47,  # ¾–pot
    SizeBucket.OVERBET: 0.60,  # 1.5× pot (the engine's only overbet size)
}
# Reference size for the price ratio (MEDIUM ≈ the ½–⅔-pot c-bet the merit
# tables were originally calibrated against).
_ALPHA_REF = _BUCKET_ALPHA[SizeBucket.MEDIUM]
# The three shared price constants, fitted numerically (F1 tuning harness:
# uniform-random hole + flop range, analytic fold-rate per candidate) against
# min(RES-D §2 band top, α − 0.01) per persona × bucket:
# - LEVEL: global fold-merit level at the MEDIUM reference. The pre-F1 tables
#   over-folded the α ceiling at every size (a tag folded ~0.39 to a ⅓-pot bet
#   vs α 0.25); 0.35 re-levels the whole curve under the ceiling.
# - SENSITIVITY: exponent on the α ratio — how fast fold merit grows with size.
# - STICKINESS_DAMP: the LEGACY `stickiness` price wiring, used ONLY when a pack
#   has not opted into W2-a (`size_elasticity is None`) — the effective exponent
#   is SENSITIVITY * stickiness**(-DAMP), so stickier personas (station 1.8,
#   fish 1.4) respond LESS to price than the disciplined low-stickiness ones
#   (nit/tag 0.6). W2-a splits this: an explicit `size_elasticity` bypasses this
#   branch for a DIRECT exponent (see `_price_exponent`), and the flat call-merit
#   scaling moves to the separate `call_looseness` lever.
_PRICE_LEVEL = 0.35
_PRICE_SENSITIVITY = 2.2
_PRICE_STICKINESS_DAMP = 0.15

# F2 size-linked bluffing (RES-D §1b/§3 + RES-E §2-§3). Polar bluff SHARE of
# the betting range at each bucket's representative chosen size, f/(1+2f)
# with value:bluff = (1+f):f — the share RISES with size (bigger bets carry
# proportionally more bluffs; value:bluff tightens toward 1:1):
#   SMALL  ⅓-pot        → 0.20
#   MEDIUM ½–⅔          → 0.25–0.286, rep 0.27
#   LARGE  ¾–pot        → 0.30–0.333, rep 0.32
#   OVERBET 1.5× (α .60) → 0.375
# Consumed as a RATIO vs the MEDIUM reference (the ½–⅔-pot class the flat
# bluff_freq levers were calibrated against, mirroring _ALPHA_REF): theory
# sets the SHAPE across sizes, the persona's bluff_freq keeps setting the
# LEVEL — so the RES-D §3 ordering station < nit < fish < tag < lag < maniac
# is preserved at every size.
_BUCKET_BLUFF_SHARE = {
    SizeBucket.SMALL: 0.20,
    SizeBucket.MEDIUM: 0.27,
    SizeBucket.LARGE: 0.32,
    SizeBucket.OVERBET: 0.375,
}
_BLUFF_SHARE_REF = _BUCKET_BLUFF_SHARE[SizeBucket.MEDIUM]


# F4 multiway calibration correction (RES-D §6, direction only): "bluff less
# + value-lean" per added opponent. The unopened/aggressor-side half of this
# is already live via `multiway_bluff_damp ** max(opponents-1, 0)` on
# `bluff_mass` (S4-era) — confirmed measurably lower 3-way vs HU in the F4
# audit. This constant closes the facing-side gap: bluff-catching (folding a
# weak made hand to a bet) was flat across `opponents` on the bot path (S8's
# `_MW_CATCH_TIGHTEN` only ever touched the GRADER). Mirrors the S8 pattern —
# a flat multiplicative tighten on the fold merit for bluff-catch-class
# buckets (AIR/ACE_HIGH/MIDDLE_PAIR facing a bet), exponentiated the same way
# as `multiway_bluff_damp` (per-added-opponent decay, NOT an n-th-root
# MDF/defense constant — no per-opponent MDF number is asserted anywhere).
# 1.15 = the grader's `_MW_VALUE_LEAN` value, reused here as "value-lean"
# framed as tightening the fold-ceiling side; kept deliberately modest (a
# direction, not a target level).
_MW_CATCH_TIGHTEN = 1.15
_MW_CATCH_BUCKETS = (StrengthBucket.AIR, StrengthBucket.ACE_HIGH, StrengthBucket.MIDDLE_PAIR)

# W1-c (F13, RES-D §6 direction-only): the VALUE-BET side of the multiway
# correction. `multiway_bluff_damp` already tightens bluffs and `_MW_CATCH_TIGHTEN`
# the bluff-catch folds per added opponent; made-value BETTING was flat across
# `opponents`. Damp the unopened made-value BET merit geometrically as the field
# grows — HU (opponents==1) is byte-identical (exponent 0). Scoped to the
# THIN-value buckets (top pair / middle pair — the opponent-count-sensitive ones);
# NOT monsters/two-pair+/overpairs (strong value you bet multiway regardless).
# `0.8` is an UNFIT directional SEED (no multiway made-value metric is live — a
# merit multiplier under softmax, so the observed bet-rate change is far smaller
# than 0.8**k); capped at a labeled 4-way tier (`_MW_VALUE_CAP` added opponents —
# 5+way magnitudes are unresearched → Later).
_MW_VALUE_DAMP = 0.8
_MW_VALUE_CAP = 3
_MW_VALUE_BUCKETS = (StrengthBucket.TOP_PAIR, StrengthBucket.MIDDLE_PAIR)


def _bluff_size_factor(frac: float) -> float:
    """Multiplier on the bluff mass for a chosen pot-fraction: the bucket's
    polar bluff share relative to the MEDIUM reference. Bucketed on the
    authored pot-fraction key (RES-E §3's chosen-size mapping)."""
    return _BUCKET_BLUFF_SHARE[size_bucket(frac)] / _BLUFF_SHARE_REF


def _sizing_dist(pf, board: list[Card], legal: list[LegalAction], is_aggressor: bool):
    """The sizing distribution this decision draws from (R2 node-aware
    override when authored + aggressor context supplied; else flat)."""
    if pf.sizing_by_node and is_aggressor:
        node = postflop_node_key(board, legal, is_aggressor=is_aggressor)
        return pf.sizing_by_node.get(node, pf.sizing)
    return pf.sizing


def _price_factor(faced_fraction: float, exponent: float) -> float:
    """Multiplier on the fold merit for a faced bet at `faced_fraction` of the
    pot: LEVEL * (α_bucket/α_ref) ** exponent. Monotone non-decreasing across
    SMALL→OVERBET because _BUCKET_ALPHA is (for any exponent >= 0). The exponent
    is resolved by `_price_exponent` (W2-a)."""
    alpha = _BUCKET_ALPHA[size_bucket(faced_fraction)]
    return _PRICE_LEVEL * (alpha / _ALPHA_REF) ** exponent


def _price_exponent(pf: PersonaPostflop) -> float:
    """W2-a: the price-response exponent, driven by `size_elasticity`.

    Two branches to preserve default-off byte-identity WHILE fixing the crash +
    direction reversal a naive rename would cause:
    - `size_elasticity is None` (un-opted-in) → the LEGACY inverse formula
      `SENSITIVITY * stickiness**(-DAMP)`: stickier personas (station 1.8, fish
      1.4) respond LESS to price than the disciplined low-stickiness ones
      (nit/tag 0.6). Byte-identical to pre-W2.
    - `size_elasticity` set → a DIRECT exponent `SENSITIVITY * size_elasticity`.
      This is a DIFFERENT scale from stickiness, chosen so 0.0 is size-blind
      (exponent 0 → flat factor, no `0**-DAMP` ZeroDivisionError) and larger
      values are STEEPER (scared) — the intuitive direction. ~1.0 reproduces a
      normal price response (exponent ≈ 2.2).
    """
    if pf.size_elasticity is None:
        return _PRICE_SENSITIVITY * pf.stickiness ** (-_PRICE_STICKINESS_DAMP)
    return _PRICE_SENSITIVITY * pf.size_elasticity


def _draw_equity(draw: DrawCategory, board: list[Card]) -> float:
    """W2-b heuristic draw equity — rule-of-4-and-2, NO solve (interim EV; label
    approximate). Street is derived from `len(board)` so this never depends on the
    optional `street` kwarg being passed: flop (3 cards, 2 to come) uses ×4, turn
    (4 cards, 1 to come) uses ×2. STRONG ≈ 9 outs (flush/OESD), WEAK ≈ 4 outs
    (gutshot/backdoor). River (5 cards) or NONE → 0.0 (no draw equity; the made-
    hand path governs the river). Calibration is a Later item (H7)."""
    outs = {DrawCategory.STRONG: 9.0, DrawCategory.WEAK: 4.0}.get(draw, 0.0)
    if outs == 0.0:
        return 0.0
    cards_to_come = 5 - len(board)
    if cards_to_come >= 2:
        return outs * 4.0 / 100.0  # STRONG 0.36 / WEAK 0.16
    if cards_to_come == 1:
        return outs * 2.0 / 100.0  # STRONG 0.18 / WEAK 0.08
    return 0.0


def _value_commit_threshold(faced_fraction: float) -> float:
    """W2-b value-commit (T1) threshold: the equity at which calling/jamming all-in
    is +EV, e ≥ B/(P+2B). Expressed via the faced pot-fraction f = B/P (the already
    pre-aggression-corrected `faced_frac`): B/(P+2B) = f/(1+2f). f=1 (pot) → 1/3;
    f=3 (3×-pot overbet) → 3/7 = 0.429. A heuristic CALL-commit price proxy for the
    stack-off, NOT a full jam-EV solve (reviewer #3)."""
    return faced_fraction / (1.0 + 2.0 * faced_fraction)


def _commit_transform(
    entries: list[tuple[ActionType, float]],
) -> list[tuple[ActionType, float]]:
    """The SPR value-commit shift: zero FOLD mass, boost BET/RAISE by
    _COMMIT_AGG_BOOST, leave CALL/CHECK. Extracted so W2-b's gate can reuse it."""
    return [
        (
            a,
            0.0
            if a is ActionType.FOLD
            else m * (_COMMIT_AGG_BOOST if a in (ActionType.BET, ActionType.RAISE) else 1.0),
        )
        for a, m in entries
    ]


def sample_postflop_decision(
    pack: PersonaPack,
    hole: tuple[Card, Card],
    board: list[Card],
    legal: list[LegalAction],
    pot_bb: float,
    stack_bb: float,
    opponents: int,
    rng: random.Random,
    noise: float = 1.0,
    current_bet_to: float = 0.0,
    is_aggressor: bool = False,
    street: Street | None = None,
    latest_aggressor_contribution_bb: float | None = None,
    context: PostflopContext | None = None,
) -> Decision:
    """Draw a frequency-mixed postflop decision from the pack's levers.

    R2 sizing: when `sizing_by_node` is authored on the pack AND the caller
    passes `is_aggressor`, the pot-fraction is drawn from the node-specific
    distribution (small on dry flops, big on wet turns). The default
    `is_aggressor=False` keeps every existing caller (the statistical harness,
    the range estimator) on the flat `sizing` distribution byte-for-byte — so
    action-frequency bands are unchanged; only the live bot loop opts in.

    W3-a: `context` (in_position / bet_prev_street / busted_draw) is threaded
    end-to-end as a walking skeleton but NOT yet read — the position/street/
    texture mechanics (W3-b/c/d) consume it. Default `None` and every current
    caller are byte-identical.

    Facing state is derived from the `legal` shapes (unopened: CHECK+BET;
    matched-with-option: CHECK+RAISE; facing chips: FOLD+CALL[+RAISE]).
    Merits: clamp >= 0, normalize by the sum (sum 0 => CHECK if legal else
    FOLD), then ALWAYS `rng.choices` — mixed, never argmax.

    Sizing (spec-pinned): pot-fraction `f` sampled from pack sizing weights,
    independent of bucket (F2: a pure-air bluff's frequency is linked to the
    chosen size via the joint two-stage sampling documented inline; the
    authored distribution itself never varies with strength). BET:
    `f * pot_bb`. RAISE:
    `raise_to = current_bet_to + f * (pot_bb + to_call)` where `to_call` is
    the CALL entry's min_bb and `current_bet_to` is the caller-supplied
    street current bet-TO amount (HandState.current_bet_bb; 0.0 = unopened —
    it is NOT derivable from the legal bracket, whose RAISE min_bb is
    min_raise_to, not the bet being raised). Legality is guaranteed by
    rounding 2dp then clamping into [min_bb, max_bb]; a jam bracket
    (min == max) resolves to it.
    """
    pf = pack.postflop
    if pf is None:
        raise ValueError(f"persona pack {pack.id!r} has no postflop block")
    # W2-a: the two split identity levers, each falling back to `stickiness` when
    # the pack hasn't opted in (default-off byte-identity). `looseness` scales the
    # flat CALL merit; the price-response exponent is resolved by `_price_exponent`.
    looseness = pf.call_looseness if pf.call_looseness is not None else pf.stickiness
    bucket, draw = strength_bucket(hole, board)
    by_kind = {la.action: la for la in legal}

    bluff_cell = bucket in (StrengthBucket.AIR, StrengthBucket.ACE_HIGH) and (
        draw is DrawCategory.NONE
    )
    bluff_mass = pf.bluff_freq * noise * pf.multiway_bluff_damp ** max(opponents - 1, 0)
    agg_scale = min(pf.aggression, _AGGRESSION_CAP) * noise  # F3: bounded, see _AGGRESSION_CAP

    # F2 size-linked bluffing: the joint (action, size) law for a pure-air
    # bluff candidate is  w(s) · bluff_mass · factor(s)  — sampled in two
    # stages so the ACTION draw stays the first rng.choices call (capture
    # rngs in range_estimate and the tests key on that): (1) here, scale
    # bluff_mass by E_s[factor] over the sizing distribution; (2) below, tilt
    # the size-draw weights by factor(s). Equivalent to pre-drawing the size
    # and conditioning the bluff decision on it. Strength never steers the
    # size draw (value hands keep the authored distribution byte-for-byte —
    # the anti-sizing-tell no-go); the resulting big-size lean WITHIN the
    # bluff-bet range is the Bayes face of "bigger bets carry proportionally
    # more bluffs" (RES-D §1b), not a strength→size map.
    sizing_dist = _sizing_dist(pf, board, legal, is_aggressor)
    if bluff_cell and (ActionType.BET in by_kind or ActionType.RAISE in by_kind):
        bluff_mass *= sum(
            w * _bluff_size_factor(float(k)) for k, w in sizing_dist.items()
        ) / sum(sizing_dist.values())

    entries: list[tuple[ActionType, float]] = []
    if ActionType.FOLD in by_kind:  # facing chips
        # F1 price-aware defense: faced pot-fraction = to_call over the pot
        # the aggressor's bet/raise was made INTO, mapped to the RES-E bucket;
        # the fold merit scales with the bucket's α relative to the MEDIUM
        # reference, damped by stickiness. Call/raise merits are untouched —
        # they absorb the complement through normalization.
        #
        # Pre-aggression pot = the pot the aggressor's bet/raise was made INTO
        # = live pot − the aggressor's own contribution (the chips their bet/raise
        # added). NUMERATOR is to_call (the facing seat's call increment — the
        # right pot-fraction numerator; only the denominator was ever wrong).
        #
        # W1-b (F9): when the live loop supplies `latest_aggressor_contribution_bb`
        # (the W0-a `pot_before_current_aggression` increment), use it — the EXACT
        # pre-aggression pot. Do NOT subtract `current_bet_to`: that is the
        # aggressor's full bet-TO, which OVER-subtracts (denominator too small →
        # faced_frac OVERSTATED → over-fold) whenever the aggressor already had
        # street chips before this action — a self-re-raise (bet→raise) OR a
        # back-raise after calling (call→raise). Fresh aggression (0 prior street
        # chips) has contribution == current_bet_to, so the two agree.
        #
        # The legacy `max(current_bet_to, to_call)` branch remains ONLY for
        # un-opted-in direct callers (harness, estimator, unit tests) that pass no
        # contribution — byte-identical to pre-W1-b. Its over-subtraction is the
        # documented approximation THERE; the estimator additionally never
        # reconstructs to_call (it builds CALL with min_bb=None → numerator 0), so
        # its faced_frac is 0 regardless — a separate, pre-existing approximation.
        to_call_bb = by_kind[ActionType.CALL].min_bb or 0.0
        if latest_aggressor_contribution_bb is None:
            faced_frac = to_call_bb / max(pot_bb - max(current_bet_to, to_call_bb), 0.01)
        else:
            faced_frac = to_call_bb / max(pot_bb - latest_aggressor_contribution_bb, 0.01)
        fold_merit = _FOLD_BASE[bucket] * _price_factor(faced_frac, _price_exponent(pf))
        # F4 (RES-D §6): bluff-catch-class buckets fold MORE per added
        # opponent — direction only, see _MW_CATCH_TIGHTEN above.
        if bucket in _MW_CATCH_BUCKETS:
            fold_merit *= _MW_CATCH_TIGHTEN ** max(opponents - 1, 0)
        entries.append((ActionType.FOLD, fold_merit))
        # River polarization (see _RIVER_RAISE_FLOOR): air never bluff-CALLS
        # the river — it folds or bluff-raises. Flooring happens BEFORE the
        # SPR-commit block so a floored 0 survives the commit boost.
        call_merit = (_CALL_BASE[bucket] + _DRAW_CALL_BONUS[draw]) * looseness
        if bluff_cell and street is Street.RIVER:
            call_merit = 0.0
        entries.append((ActionType.CALL, call_merit))
        if ActionType.RAISE in by_kind:
            if bluff_cell:
                raise_merit = _BLUFF_RAISE_FACTOR * bluff_mass  # polar bluff survives
            else:
                raise_merit = (_RAISE_BASE[bucket] + _DRAW_RAISE_BONUS[draw]) * agg_scale
                if street is Street.RIVER and bucket in _RIVER_RAISE_FLOOR:
                    raise_merit = 0.0  # bluff-catchers never value-raise the river
            entries.append((ActionType.RAISE, raise_merit))
    else:  # unopened (CHECK+BET) or matched-with-option (CHECK+RAISE)
        agg_action = ActionType.BET if ActionType.BET in by_kind else ActionType.RAISE
        if bluff_cell:  # bluff_freq SETS the air bet/raise mass (rule 1)
            agg_merit = bluff_mass
            check_merit = max(1.0 - bluff_mass, 0.0)
        else:
            agg_merit = (_AGG_BASE[bucket] + _DRAW_AGG_BONUS[draw]) * agg_scale
            check_merit = _CHECK_BASE[bucket]
            # W1-c (F13): tighten thin made-value BETTING as the field grows —
            # the value-side mirror of the multiway bluff damp. BET only (the
            # matched-with-option check-RAISE is out of scope); HU byte-identical.
            if agg_action is ActionType.BET and bucket in _MW_VALUE_BUCKETS:
                agg_merit *= _MW_VALUE_DAMP ** min(max(opponents - 1, 0), _MW_VALUE_CAP)
            # River polarization: the matched-with-option RAISE (check-raise
            # line) is floored for the whole one-pair class; the unopened BET is
            # floored for MIDDLE_PAIR ONLY (W1-a) — top-pair/overpair keep the
            # thin river value bet.
            if (
                agg_action is ActionType.RAISE
                and street is Street.RIVER
                and bucket in _RIVER_RAISE_FLOOR
            ):
                agg_merit = 0.0
            elif (
                agg_action is ActionType.BET
                and street is Street.RIVER
                and bucket in _RIVER_BET_FLOOR
            ):
                agg_merit = 0.0  # middle pair never value-bets the river
        entries.append((ActionType.CHECK, check_merit))
        entries.append((agg_action, agg_merit))

    # SPR commit (rule 2): shift to call/jam. Live SPR only — never srs.spr_bucket
    # (frozen SRS contract).
    #
    # W2-b (F5/F7): the commit shift is EV-gated on the DRAW side (directional own-
    # action policy — no forced-F*, owner decision).
    #  - A made hand (rung >= OVERPAIR) commits exactly as before (equity ≈ 1): the
    #    value-jam path is byte-identical and is NEVER draw-damped, even when it also
    #    holds a draw (reviewer #6).
    #  - A STRONG draw NOT facing a price (unopened/betting — no fold to zero)
    #    commits as before.
    #  - A draw FACING a bet commits (zero fold) ONLY when its heuristic equity
    #    clears the value-commit threshold for the faced price (T1 = f/(1+2f)). Below
    #    T1 the fold is NOT zeroed (the price-aware fold merit stands) and the draw's
    #    CALL/RAISE bonus is damped by commitment so a naked draw stops stacking off
    #    (B5b). A draw hand is never bluff_cell (draw != NONE), so the RAISE merit is
    #    always the non-bluff value+bonus form — the bonus subtraction is exact.
    if stack_bb / pot_bb <= pf.spr_commit:
        made = _RUNG[bucket] >= _RUNG[StrengthBucket.OVERPAIR_TPTK]
        facing = ActionType.FOLD in by_kind
        drawing = draw in (DrawCategory.STRONG, DrawCategory.WEAK)
        if made or (draw is DrawCategory.STRONG and not facing):
            value_commit = True
        elif facing and drawing:
            value_commit = _draw_equity(draw, board) >= _value_commit_threshold(faced_frac)
        else:
            value_commit = False
        if value_commit:
            entries = _commit_transform(entries)
        elif facing and drawing:  # below T1 — keep fold, damp the draw's stack-off pull
            c = min(max((pf.spr_commit - stack_bb / pot_bb) / pf.spr_commit, 0.0), 1.0)
            removed = _B5B_DRAW_DAMP * c
            damped: list[tuple[ActionType, float]] = []
            for a, m in entries:
                if a is ActionType.CALL:
                    m -= _DRAW_CALL_BONUS[draw] * looseness * removed
                elif a is ActionType.RAISE:
                    m -= _DRAW_RAISE_BONUS[draw] * agg_scale * removed
                damped.append((a, m))
            entries = damped

    # Normalize (rule 1, pinned): clamp >= 0, divide by sum; sum 0 fallback.
    weights = [max(m, 0.0) for _, m in entries]
    total = sum(weights)
    if total <= 0.0:
        fallback = ActionType.CHECK if ActionType.CHECK in by_kind else ActionType.FOLD
        return Decision(action=fallback)
    action = rng.choices([a for a, _ in entries], weights=[w / total for w in weights], k=1)[0]

    if action not in (ActionType.BET, ActionType.RAISE):
        return Decision(action=action)

    # Sizing draw — independent of bucket (rule 3): the distribution is the
    # persona-authored one for every strength class. F2 stage 2 (see the
    # bluff_mass comment above): a pure-air bluff bet tilts the weights by
    # the bucket factor, completing the joint law w(s)·bluff_mass·factor(s).
    fracs = [(float(k), w) for k, w in sizing_dist.items()]
    if bluff_cell:
        fracs = [(fr, w * _bluff_size_factor(fr)) for fr, w in fracs]
    f = rng.choices([fr for fr, _ in fracs], weights=[w for _, w in fracs], k=1)[0]
    to_call = by_kind[ActionType.CALL].min_bb or 0.0 if ActionType.CALL in by_kind else 0.0
    size = pot_fraction_to_bb(
        f, pot_bb, action=action, current_bet_to=current_bet_to, to_call=to_call
    )
    bracket = by_kind[action]
    size = min(max(round(size, 2), bracket.min_bb), bracket.max_bb)
    return Decision(action=action, size_bb=size)
