"""Villain range estimator (villain-range V1) — pure domain, NO card peeking.

Estimates a villain's hand range from PUBLIC information only: the persona
pack + the public action sequence + the revealed board + known dead cards
(the hero's own hole cards). The input type `PublicActionHistory` carries
street/position/seat/action/amount per action plus board, starting stacks and
button seat — structurally it CANNOT hold hole cards, so the estimator can
never peek (spec refuter high-3).

Reconstruction is a REPLAY, not a list scan (spec refuter high-1/high-2): a
lightweight chip walk over the projection regenerates each historical
decision's context — preflop `facing` exactly as `play._preflop_facing`
derives it from the interleaved history, and postflop pot/stack/opponents/
current-bet-to/legal-action-kinds exactly as `engine.legal_actions` +
`play.bot_decision` would have seen them (the SPR-commit branch in
`personas_postflop` makes snapshot errors catastrophic). Equivalence against
real `HandState` playouts is fixture-tested in tests/test_range_estimate.py.

Posterior math:
- Preflop is EXACT: weight(class) ×= P(observed wire action | class, node)
  from the pack mixes, including `play._preflop_decision`'s legality fallback
  (persona action not offered → call, else check, else fold).
- Postflop is APPROXIMATE (`exact=False`): per candidate combo, the action
  distribution the persona WOULD have mixed from at the reconstructed
  decision (merit ladder + levers, via `sample_postflop_decision` with a
  weight-capturing rng), reweighted by the observed action TYPE (bet/raise
  size is ignored — category-level approximation, spec-allowed).
- Class↔combo granularity (spec med-2): classes expand to suit combos so
  dead-card removal (hero cards + revealed board ONLY) zeroes just the
  blocked combos; combo mass re-aggregates to 169-class weights.

Spec: docs/ai-dlc/specs/simulate-villain-range.md.
"""

from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel, ConfigDict

from app.domain.content.models import PersonaPack
from app.domain.content.notation import all_hands, hole_cards_to_class
from app.domain.personas import _WIRE, _combos
from app.domain.personas_postflop import sample_postflop_decision, strength_bucket
from app.domain.spot import RANKS, SUITS, ActionType, Card, LegalAction, Position, Street

_SEATS = 9
_EPS = 1e-9
_BB = 1.0
# Revealed-board card count by street (engine._REVEAL + preflop).
_REVEAL = {Street.PREFLOP: 0, Street.FLOP: 3, Street.TURN: 4, Street.RIVER: 5}

_DECK: tuple[Card, ...] = tuple(r + s for r in RANKS for s in SUITS)
# All 1326 hole-card combos, deck order, c1 index < c2 index.
_ALL_COMBOS: tuple[tuple[Card, Card], ...] = tuple(
    (_DECK[i], _DECK[j]) for i in range(52) for j in range(i + 1, 52)
)


class PublicAction(BaseModel):
    """One public action — HistoryAction semantics: `amount_bb` is the chip
    INCREMENT the actor put in (0.0 for fold/check), never a raise-TO."""

    model_config = ConfigDict(frozen=True)

    seat: int
    position: Position
    street: Street
    action: ActionType  # POST entries for blinds included
    amount_bb: float


class PublicActionHistory(BaseModel):
    """Card-free projection of a hand's public record. NO SeatState, NO
    hole-card field exists anywhere in this type — the no-peek invariant is
    structural, not behavioral."""

    model_config = ConfigDict(frozen=True)

    button_seat: int
    starting_stacks_bb: tuple[float, ...]  # len 9, pre-blind stacks by seat
    board: tuple[Card, ...]  # revealed board cards so far (0/3/4/5)
    actions: tuple[PublicAction, ...]


class _Ctx(NamedTuple):
    """Reconstructed context of one historical decision by the target seat."""

    street: Street
    board: tuple[Card, ...]
    position: Position
    facing: str | None  # preflop node facing; None postflop
    kinds: frozenset[ActionType]  # legal action KINDS at the decision
    pot_bb: float
    stack_bb: float
    opponents: int
    current_bet_to: float
    observed: ActionType


class RangeEstimate(NamedTuple):
    class_weights: dict[str, float]  # all 169 classes; sums to 1.0 (or all 0)
    combo_weights: dict[tuple[Card, Card], float]  # deck-ordered combo keys
    exact: bool  # False iff any postflop (approximate) conditioning applied


def _replay_contexts(history: PublicActionHistory, seat: int, n: int) -> list[_Ctx]:
    """Chip-walk the first `n` public actions; return the target seat's
    decision contexts. Mirrors engine.apply/_acted_seats/legal_actions and
    play._preflop_facing bookkeeping exactly (fixture-proven equivalent)."""
    stacks = list(history.starting_stacks_bb)
    inv_street = [0.0] * _SEATS
    inv_total = [0.0] * _SEATS
    folded: set[int] = set()
    street = Street.PREFLOP
    cur = 0.0  # current bet-TO this street
    last_full = _BB  # last full raise increment (min-raise/reopen rule)
    acted: set[int] = set()  # seats acted since last reopen this street
    pf_raises = 0
    pf_limped = False
    out: list[_Ctx] = []

    def pay(s: int, amt: float) -> None:
        stacks[s] -= amt
        if stacks[s] <= _EPS:
            stacks[s] = 0.0  # engine._pay clamps to exactly 0.0
        inv_street[s] += amt
        inv_total[s] += amt

    for a in history.actions[:n]:
        if a.street is not street:  # street closed: engine._close_street resets
            street = a.street
            inv_street = [0.0] * _SEATS
            cur = 0.0
            last_full = _BB
            acted = set()
        s = a.seat
        if a.action is ActionType.POST:
            pay(s, a.amount_bb)
            cur = max(cur, inv_street[s])
            continue

        if s == seat:
            all_in_to = inv_street[s] + stacks[s]
            to_call = cur - inv_street[s]
            if cur <= _EPS:  # unopened street
                kinds = frozenset({ActionType.CHECK, ActionType.BET})
            elif to_call <= _EPS:  # matched with option (e.g. BB preflop)
                kinds = frozenset({ActionType.CHECK, ActionType.RAISE})
            else:
                base = {ActionType.FOLD, ActionType.CALL}
                if all_in_to > cur + _EPS and s not in acted:
                    base.add(ActionType.RAISE)
                kinds = frozenset(base)
            if street is Street.PREFLOP:
                if pf_raises == 0:
                    facing = "vs_limpers" if pf_limped else "unopened"
                elif pf_raises == 1:
                    facing = "vs_rfi"
                elif pf_raises == 2:
                    facing = "vs_3bet"
                else:
                    facing = "vs_4bet"
            else:
                facing = None
            out.append(
                _Ctx(
                    street=street,
                    board=history.board[: _REVEAL[street]],
                    position=a.position,
                    facing=facing,
                    kinds=kinds,
                    pot_bb=sum(inv_total),
                    stack_bb=stacks[s],
                    opponents=sum(1 for j in range(_SEATS) if j != s and j not in folded),
                    current_bet_to=cur,
                    observed=a.action,
                )
            )

        if a.action is ActionType.FOLD:
            folded.add(s)
            acted.add(s)
        elif a.action is ActionType.CHECK:
            acted.add(s)
        elif a.action is ActionType.CALL:
            pay(s, a.amount_bb)
            acted.add(s)
            if street is Street.PREFLOP:
                pf_limped = True
        else:  # BET / RAISE — amount is the increment; new bet-TO = invested
            prev = cur
            pay(s, a.amount_bb)
            new_bet = inv_street[s]
            all_in = stacks[s] <= _EPS
            if all_in and new_bet - prev < last_full - _EPS:
                acted.add(s)  # incomplete all-in raise: no reopen
            else:
                last_full = new_bet - prev
                acted = {s}  # complete bet/raise reopens action
            cur = new_bet
            if street is Street.PREFLOP:
                pf_raises += 1
    return out


# ------------------------------------------------------ preflop (exact)


def _preflop_mix(pack: PersonaPack, position: Position, facing: str, hand: str) -> dict[str, float]:
    """Content-action distribution — mirrors personas.sample_preflop_action's
    node/mix lookup exactly (first match in list order, implicit fold)."""
    for node in pack.preflop:
        if node.facing != facing:
            continue
        if node.positions is not None and position not in node.positions:
            continue
        for mix in node.mixes:
            if hand not in _combos(mix.combos):
                continue
            weights = dict(mix.weights)
            remainder = 1.0 - sum(weights.values())
            if remainder > 1e-9:
                weights["fold"] = weights.get("fold", 0.0) + remainder
            return weights
        break  # node matched, no mix covers the class => fold 1.0
    return {"fold": 1.0}


def _preflop_observed_prob(
    mix: dict[str, float], kinds: frozenset[ActionType], observed: ActionType
) -> float:
    """P(observed wire action) incl. play._preflop_decision's legality
    fallback: illegal persona action -> call if legal, else check, else fold."""
    p = 0.0
    for name, w in mix.items():
        wire = _WIRE[name]
        if wire not in kinds:
            if ActionType.CALL in kinds:
                wire = ActionType.CALL
            elif ActionType.CHECK in kinds:
                wire = ActionType.CHECK
            else:
                wire = ActionType.FOLD
        if wire is observed:
            p += w
    return p


# ------------------------------------------------- postflop (approximate)


class _CaptureRng:
    """Duck-typed rng that records the first `choices` call's distribution.

    Passed to sample_postflop_decision so the estimator reuses the EXACT merit
    ladder + lever + SPR-commit math without duplicating its tables. The
    sampler's action draw is its first choices() call; returning population[0]
    (always FOLD or CHECK, the first entry) guarantees the sizing draw — a
    second choices() call — is never reached."""

    def __init__(self) -> None:
        self.population: list[ActionType] | None = None
        self.weights: list[float] | None = None

    def choices(self, population, weights, k=1):  # noqa: ANN001 — rng protocol
        if self.population is None:
            self.population = list(population)
            self.weights = list(weights)
        return [population[0]]


def _postflop_action_dist(
    pack: PersonaPack, hole: tuple[Card, Card], ctx: _Ctx
) -> dict[ActionType, float]:
    legal = [LegalAction(action=k) for k in sorted(ctx.kinds)]
    cap = _CaptureRng()
    decision = sample_postflop_decision(
        pack,
        hole,
        list(ctx.board),
        legal,
        ctx.pot_bb,
        ctx.stack_bb,
        ctx.opponents,
        cap,  # type: ignore[arg-type] — duck-typed capture rng
        current_bet_to=ctx.current_bet_to,
    )
    if cap.population is None:  # zero-total-merit fallback path: deterministic
        return {decision.action: 1.0}
    assert cap.weights is not None
    return dict(zip(cap.population, cap.weights, strict=True))


# ---------------------------------------------------------- public API


def estimate_range(
    pack: PersonaPack,
    history: PublicActionHistory,
    seat: int,
    dead_cards: tuple[Card, ...] = (),
    through_action: int | None = None,
) -> RangeEstimate:
    """Posterior over the target seat's hole-card combos given its public line.

    `dead_cards` is the hero's own hole cards (plus nothing else — other
    villains' unseen cards are NOT excluded; the revealed board is taken from
    the projection). `through_action` conditions on only the first N entries
    of `history.actions` (POST entries count toward N); the board is truncated
    to the street of the last considered action.
    """
    total_actions = len(history.actions)
    n = total_actions if through_action is None else min(through_action, total_actions)
    ctxs = _replay_contexts(history, seat, n)
    if n >= len(history.actions):
        board_seen = history.board
    else:
        street = history.actions[n - 1].street if n > 0 else Street.PREFLOP
        board_seen = history.board[: _REVEAL[street]]

    dead = set(dead_cards) | set(board_seen)
    weights = {
        combo: (0.0 if combo[0] in dead or combo[1] in dead else 1.0) for combo in _ALL_COMBOS
    }
    exact = True
    bucket_cache: dict[tuple[Card, Card, int], tuple] = {}

    for ctx in ctxs:
        live = [c for c in _ALL_COMBOS if weights[c] > 0.0]
        if ctx.street is Street.PREFLOP:
            assert ctx.facing is not None
            factor_by_class: dict[str, float] = {}
            for combo in live:
                cls = hole_cards_to_class(*combo)
                if cls not in factor_by_class:
                    mix = _preflop_mix(pack, ctx.position, ctx.facing, cls)
                    factor_by_class[cls] = _preflop_observed_prob(mix, ctx.kinds, ctx.observed)
                weights[combo] *= factor_by_class[cls]
        else:
            exact = False
            # Group live combos by (bucket, draw): the action distribution
            # depends only on the group + context, so one sampler call per
            # group covers every member combo.
            groups: dict[tuple, list[tuple[Card, Card]]] = {}
            for combo in live:
                key = bucket_cache.get((combo[0], combo[1], len(ctx.board)))
                if key is None:
                    key = strength_bucket(combo, list(ctx.board))
                    bucket_cache[combo[0], combo[1], len(ctx.board)] = key
                groups.setdefault(key, []).append(combo)
            for members in groups.values():
                dist = _postflop_action_dist(pack, members[0], ctx)
                factor = dist.get(ctx.observed, 0.0)
                for combo in members:
                    weights[combo] *= factor

    total = sum(weights.values())
    if total > 0.0:
        weights = {c: w / total for c, w in weights.items()}
    class_weights = dict.fromkeys(all_hands(), 0.0)
    for combo, w in weights.items():
        class_weights[hole_cards_to_class(*combo)] += w
    return RangeEstimate(class_weights=class_weights, combo_weights=weights, exact=exact)
