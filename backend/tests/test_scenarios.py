import asyncio
import random

from app.domain.content.models import ActionRange, Entry
from app.domain.grading import range_grid
from app.domain.providers import get_provider
from app.domain.scenarios import (
    RFI_POSITIONS,
    _entries,
    _find_entry,
    build_spot,
    sample_rfi_spot,
    sample_spot,
)
from app.domain.spot import ActionType, NodeContext, PlayerStatus, Position, Street


def test_sample_rfi_is_valid():
    spot = sample_rfi_spot(random.Random(42))
    assert spot.hero.position in RFI_POSITIONS
    assert NodeContext.RFI in spot.node_context
    assert spot.hero.hole_cards[0] != spot.hero.hole_cards[1]
    assert any(a.action == ActionType.RAISE for a in spot.legal_actions)


def _rfi_raise_hands(position: Position) -> set[str]:
    entry = _find_entry(NodeContext.RFI, position, None)
    grid = range_grid(entry)
    return {hand for hand, mix in grid.items() if mix.get(ActionType.RAISE.value) == 1.0}


def test_rfi_nesting_utg_through_lj_is_monotonic():
    """R4 golden: UTG ⊆ UTG1 ⊆ UTG2 ⊆ LJ RFI-raise ranges (RES-A §4.2)."""
    utg = _rfi_raise_hands(Position.UTG)
    utg1 = _rfi_raise_hands(Position.UTG1)
    utg2 = _rfi_raise_hands(Position.UTG2)
    lj = _rfi_raise_hands(Position.LJ)
    assert utg <= utg1 <= utg2 <= lj
    # strictly widening at each step (no seat collapses to an equal-or-tighter set)
    assert len(utg) < len(utg1) < len(utg2) < len(lj)


def test_utg1_utg2_non_spots_stay_unmapped():
    """RES-A §7: vs_4bet / blind_defense are non-spots for UTG1/UTG2 -- no
    content entry exists so `_find_entry` returns None. vs_limpers is a
    SUPERSESSION as of M2 (RES-G Slice A): UTG2 now has a vs_limpers x1 entry
    (RES-G §1d measured the EP faces-1-limper shape at UTG2, not UTG -- UTG
    itself has no seats before it and can never face a limper, so the entry
    was authored at UTG2 to stay both organically reachable and coherent in
    `build_spot`). UTG1 remains a genuine vs_limpers non-spot."""
    for pos in (Position.UTG1, Position.UTG2):
        assert _find_entry(NodeContext.VS_4BET, pos, Position.BTN) is None
        assert _find_entry(NodeContext.BLIND_DEFENSE, pos, Position.BTN) is None
    assert _find_entry(NodeContext.VS_LIMPERS, Position.UTG1, None) is None
    assert _find_entry(NodeContext.VS_LIMPERS, Position.UTG2, None) is not None


def test_sample_is_deterministic_with_seed():
    a = sample_spot(random.Random(7))
    b = sample_spot(random.Random(7))
    assert a.hero.position == b.hero.position
    assert a.hero.hole_cards == b.hero.hole_cards
    assert a.node_context == b.node_context


def test_sample_varies_across_draws():
    rng = random.Random(123)
    hands = {sample_spot(rng).hero.hole_cards for _ in range(20)}
    assert len(hands) > 1


def test_every_entry_samples_to_full_coverage():
    """Content-driven sampling => every spot has a matching grading node."""
    provider = get_provider()
    rng = random.Random(0)
    for entry in _entries():
        spot = build_spot(entry, rng)
        assert asyncio.run(provider.supports(spot)) is True
        assert asyncio.run(provider.optimal(spot)).coverage.value == "full"


def test_golden_vs_rfi_spot():
    entry = Entry(
        node_context=NodeContext.VS_RFI,
        position=Position.CO,
        facing=Position.UTG,
        actions=[ActionRange(action=ActionType.RAISE, combos="QQ+", frequency=1.0)],
        sizing_bb=10.0,
    )
    spot = build_spot(entry, random.Random(1))
    assert spot.facing == Position.UTG
    assert spot.node_context == [NodeContext.VS_RFI]
    assert any(
        h.action == ActionType.RAISE and h.position == Position.UTG for h in spot.action_history
    )
    assert {la.action for la in spot.legal_actions} == {
        ActionType.FOLD,
        ActionType.CALL,
        ActionType.RAISE,
    }
    assert spot.pot_bb == 1.5 + 3.0  # UTG open = 3.0bb


def test_golden_vs_limpers_spot():
    entry = Entry(
        node_context=NodeContext.VS_LIMPERS,
        position=Position.BTN,
        limper_count=2,
        actions=[ActionRange(action=ActionType.RAISE, combos="77+", frequency=1.0)],
        sizing_bb=6.0,
    )
    spot = build_spot(entry, random.Random(1))
    assert spot.limper_count == 2
    limps = [h for h in spot.action_history if h.action == ActionType.CALL and h.amount_bb == 1.0]
    assert len(limps) == 2
    assert spot.pot_bb == 1.5 + 2.0
    assert {la.action for la in spot.legal_actions} == {
        ActionType.FOLD,
        ActionType.CALL,
        ActionType.RAISE,
    }


# --- Phase 1b: facing-aggression sampler ---
def test_golden_vs_3bet_spot():
    entry = Entry(
        node_context=NodeContext.VS_3BET,
        position=Position.CO,
        facing=Position.BTN,
        actions=[ActionRange(action=ActionType.RAISE, combos="QQ+", frequency=1.0)],
        sizing_bb=22.0,
    )
    spot = build_spot(entry, random.Random(1))
    assert spot.pot_bb == 11.5  # 1.5 + 2.5 open + 7.5 3bet
    call = next(la for la in spot.legal_actions if la.action == ActionType.CALL)
    assert call.min_bb == 5.0  # 7.5 - 2.5 (incremental)
    raise_ = next(la for la in spot.legal_actions if la.action == ActionType.RAISE)
    assert raise_.min_bb == 22.0
    assert sum(1 for p in spot.players if p.position == Position.BTN) == 1  # facing once


def test_golden_vs_4bet_spot():
    entry = Entry(
        node_context=NodeContext.VS_4BET,
        position=Position.BTN,
        facing=Position.CO,
        actions=[ActionRange(action=ActionType.RAISE, combos="AA", frequency=1.0)],
        sizing_bb=100.0,
    )
    spot = build_spot(entry, random.Random(1), eff_bb=100.0)
    assert spot.pot_bb == 28.75  # 1.5 + 2.5 + 7.5 + 17.25
    call = next(la for la in spot.legal_actions if la.action == ActionType.CALL)
    assert call.min_bb == 9.75  # 17.25 - 7.5
    jam = next(la for la in spot.legal_actions if la.action == ActionType.RAISE)
    assert jam.min_bb == 100.0 and jam.max_bb == 100.0  # jam = eff stack
    assert sum(1 for p in spot.players if p.position == Position.CO) == 1  # facing once


def test_bb_call_open_is_incremental():
    entry = Entry(
        node_context=NodeContext.BLIND_DEFENSE,
        position=Position.BB,
        facing=Position.BTN,
        actions=[ActionRange(action=ActionType.CALL, combos="22+", frequency=1.0)],
        sizing_bb=11.0,
    )
    spot = build_spot(entry, random.Random(1))
    call = next(la for la in spot.legal_actions if la.action == ActionType.CALL)
    assert call.min_bb == 1.5  # 2.5 open - 1.0 BB already posted


def test_depth_variety_yields_multiple_buckets():
    rng = random.Random(5)
    depths = {sample_spot(rng).effective_stack_bb for _ in range(30)}
    assert len(depths) >= 2


# --- game-table T2: 9-seat enrichment + explicit preflop FOLD history ---

_ALL_SEATS = [
    Position.UTG,
    Position.UTG1,
    Position.UTG2,
    Position.LJ,
    Position.HJ,
    Position.CO,
    Position.BTN,
    Position.SB,
    Position.BB,
]


def _entry(ctx, pos, facing=None, limper_count=None):
    action = ActionType.CALL if ctx == NodeContext.BLIND_DEFENSE else ActionType.RAISE
    return Entry(
        node_context=ctx,
        position=pos,
        facing=facing,
        limper_count=limper_count,
        actions=[ActionRange(action=action, combos="22+", frequency=1.0)],
    )


_T2_ENTRIES = [
    _entry(NodeContext.RFI, Position.CO),
    _entry(NodeContext.VS_RFI, Position.CO, facing=Position.UTG),
    _entry(NodeContext.BLIND_DEFENSE, Position.BB, facing=Position.BTN),
    _entry(NodeContext.VS_3BET, Position.CO, facing=Position.BTN),
    _entry(NodeContext.VS_4BET, Position.BTN, facing=Position.CO),
    _entry(NodeContext.VS_LIMPERS, Position.BTN, limper_count=2),
]


def _statuses(spot):
    return {p.position: p.status for p in spot.players}


def _fold_positions(spot):
    return [h.position for h in spot.action_history if h.action == ActionType.FOLD]


def test_build_spot_emits_all_nine_seats_once_each():
    for entry in _T2_ENTRIES:
        spot = build_spot(entry, random.Random(42))
        assert len(spot.players) == 9
        assert [p.position for p in spot.players] == _ALL_SEATS  # one seat per position
        assert sum(1 for p in spot.players if p.is_hero) == 1
        # every FOLDED seat has exactly one FOLD history entry, and vice versa
        folded = [p.position for p in spot.players if p.status == PlayerStatus.FOLDED]
        assert sorted(_fold_positions(spot)) == sorted(folded)
        # hero and the aggressor faced are always still in the hand
        assert _statuses(spot)[entry.position] == PlayerStatus.IN
        if entry.facing:
            assert _statuses(spot)[entry.facing] == PlayerStatus.IN


def test_vs_rfi_statuses_match_authored_action():
    # vs_RFI CO vs UTG: UTG opened (IN), UTG1/UTG2/LJ/HJ folded to hero, seats
    # behind hero (BTN + blinds) have not acted yet -> IN.
    entry = _entry(NodeContext.VS_RFI, Position.CO, facing=Position.UTG)
    spot = build_spot(entry, random.Random(1))
    st = _statuses(spot)
    assert st[Position.UTG] == PlayerStatus.IN
    for pos in (Position.UTG1, Position.UTG2, Position.LJ, Position.HJ):
        assert st[pos] == PlayerStatus.FOLDED
    for pos in (Position.CO, Position.BTN, Position.SB, Position.BB):
        assert st[pos] == PlayerStatus.IN
    # canonical order, chronologically after the open
    assert _fold_positions(spot) == [Position.UTG1, Position.UTG2, Position.LJ, Position.HJ]
    open_idx = next(i for i, h in enumerate(spot.action_history) if h.action == ActionType.RAISE)
    fold_idxs = [i for i, h in enumerate(spot.action_history) if h.action == ActionType.FOLD]
    assert all(i > open_idx for i in fold_idxs)


def test_rfi_blinds_never_fold():
    spot = build_spot(_entry(NodeContext.RFI, Position.CO), random.Random(1))
    st = _statuses(spot)
    assert st[Position.SB] == PlayerStatus.IN and st[Position.BB] == PlayerStatus.IN
    assert _fold_positions(spot) == [
        Position.UTG,
        Position.UTG1,
        Position.UTG2,
        Position.LJ,
        Position.HJ,
    ]


def test_blind_defense_sb_folds_only_because_it_faced_the_raise():
    # BB defends vs BTN open: everyone folds to BTN, BTN opens, SB (facing the
    # raise) folds -> hero BB decides. SB's FOLD entry sits AFTER the open.
    spot = build_spot(
        _entry(NodeContext.BLIND_DEFENSE, Position.BB, facing=Position.BTN), random.Random(1)
    )
    st = _statuses(spot)
    assert st[Position.SB] == PlayerStatus.FOLDED
    assert st[Position.BB] == PlayerStatus.IN and st[Position.BTN] == PlayerStatus.IN
    hist = spot.action_history
    open_idx = next(i for i, h in enumerate(hist) if h.action == ActionType.RAISE)
    sb_fold_idx = next(
        i for i, h in enumerate(hist) if h.action == ActionType.FOLD and h.position == Position.SB
    )
    assert sb_fold_idx > open_idx


def test_vs_3bet_exactly_two_in_and_blinds_fold_facing_3bet():
    # CO opens, BTN 3-bets, blinds fold facing the 3-bet, back on CO.
    entry = _entry(NodeContext.VS_3BET, Position.CO, facing=Position.BTN)
    spot = build_spot(entry, random.Random(1))
    st = _statuses(spot)
    assert [p for p in _ALL_SEATS if st[p] == PlayerStatus.IN] == [Position.CO, Position.BTN]
    hist = spot.action_history
    tbet_idx = next(
        i for i, h in enumerate(hist) if h.action == ActionType.RAISE and h.position == Position.BTN
    )
    for blind in (Position.SB, Position.BB):
        fold_idx = next(
            i for i, h in enumerate(hist) if h.action == ActionType.FOLD and h.position == blind
        )
        assert fold_idx > tbet_idx  # blinds folded only once they faced the 3-bet


def test_vs_limpers_history_interleaves_limps_and_folds_in_seat_order():
    # BTN vs 2 limpers (UTG, LJ): UTG limps, UTG1/UTG2 fold, LJ limps, HJ/CO fold.
    entry = _entry(NodeContext.VS_LIMPERS, Position.BTN, limper_count=2)
    spot = build_spot(entry, random.Random(1))
    seq = [
        (h.position, h.action)
        for h in spot.action_history
        if h.action in (ActionType.CALL, ActionType.FOLD)
    ]
    assert seq == [
        (Position.UTG, ActionType.CALL),
        (Position.UTG1, ActionType.FOLD),
        (Position.UTG2, ActionType.FOLD),
        (Position.LJ, ActionType.CALL),
        (Position.HJ, ActionType.FOLD),
        (Position.CO, ActionType.FOLD),
    ]
    st = _statuses(spot)
    assert st[Position.SB] == PlayerStatus.IN and st[Position.BB] == PlayerStatus.IN


def test_spot_signature_unchanged_by_seat_enrichment():
    """Fixed-rng regression: spot_signature must be byte-identical to the values
    computed BEFORE the 9-seat/FOLD-history enrichment (signatures are frozen —
    a change here orphans persisted SRS history)."""
    from app.domain.srs import spot_signature

    pinned = [
        "0cdf437e044b0bc5",  # RFI CO
        "8a793dd99f77ebf7",  # vs_RFI CO vs UTG
        "fa40bf9b0275ec4e",  # blind_defense BB vs BTN
        "315c1e5575bb68e9",  # vs_3bet CO vs BTN
        "3e607efbc81f026c",  # vs_4bet BTN vs CO
        "70295f999f86ee76",  # vs_limpers BTN, 2 limpers
    ]
    sigs = [
        spot_signature(build_spot(entry, random.Random(42), eff_bb=100.0))
        for entry in _T2_ENTRIES
    ]
    assert sigs == pinned


# --- Phase 1c: pool isolation ---
def test_baseline_pool_excludes_exploit_entries():
    from app.domain.scenarios import _entries

    assert _entries()
    assert all(e.villain_type is None for e in _entries())


def test_exploit_sampler_sets_villain_type():
    from app.domain.scenarios import sample_exploit_spot

    s = sample_exploit_spot(random.Random(3))
    assert s.villain_type is not None


# --- Phase 2a: flop c-bet spot ---
def test_cbet_spot_is_valid_flop_with_ranges():
    from app.domain.scenarios import build_cbet_spot
    from app.domain.spot import Street

    s = build_cbet_spot(random.Random(7), eff_bb=100.0)
    assert s.street == Street.FLOP
    assert len(s.board) == 3
    assert s.node_context == [NodeContext.CBET]
    assert s.hero_range and s.villain_range
    # hole cards and board are disjoint, all 5 distinct
    cards = list(s.hero.hole_cards) + s.board
    assert len(set(cards)) == 5
    # legal = check + two bet sizes
    actions = [la.action for la in s.legal_actions]
    assert actions.count(ActionType.BET) == 2
    assert ActionType.CHECK in actions
    assert s.spr is not None and s.spr > 0


def test_cbet_spot_signature_stable_across_seeds():
    from app.domain.scenarios import build_cbet_spot
    from app.domain.srs import spot_signature

    # Same pairing + same depth -> texture/SPR-bucketed signature should land in a
    # small stable set (not unique per board).
    sigs = {
        spot_signature(
            build_cbet_spot(random.Random(i), pairing=(Position.BTN, Position.BB), eff_bb=100.0)
        )
        for i in range(40)
    }
    assert len(sigs) < 40  # boards collapse into texture/SPR buckets


def test_cbet_spot_grades_via_provider():
    from app.domain.action import Decision
    from app.domain.providers import get_provider
    from app.domain.scenarios import build_cbet_spot

    s = build_cbet_spot(random.Random(11), eff_bb=100.0)
    p = get_provider()
    res = asyncio.run(p.evaluate(s, Decision(action=ActionType.CHECK)))
    assert res.leak_category == 200  # FLOP_CBET
    assert res.correctness is not None


# --- Phase 2b: facing-a-c-bet spot ---
def test_vs_cbet_spot_is_valid_defense_spot():
    from app.domain.scenarios import build_vs_cbet_spot
    from app.domain.spot import Street

    s = build_vs_cbet_spot(random.Random(7), eff_bb=100.0)
    assert s.street == Street.FLOP and len(s.board) == 3
    assert s.node_context == [NodeContext.VS_CBET]
    assert s.hero.position == Position.BB  # hero is the BB defender (OOP)
    assert s.facing is not None and s.facing != s.hero.position  # villain = opener
    assert any(h.action == ActionType.BET for h in s.action_history)  # villain c-bet
    acts = {la.action for la in s.legal_actions}
    assert acts == {ActionType.FOLD, ActionType.CALL, ActionType.RAISE}
    raise_la = next(la for la in s.legal_actions if la.action == ActionType.RAISE)
    assert raise_la.min_bb and raise_la.min_bb > 0  # raise carries a size
    faced = next(la.min_bb for la in s.legal_actions if la.action == ActionType.CALL)
    assert s.pot_bb > faced  # pot includes the faced c-bet
    cards = list(s.hero.hole_cards) + s.board
    assert len(set(cards)) == 5


def test_vs_cbet_spot_grades_via_provider():
    from app.domain.action import Decision
    from app.domain.providers import get_provider
    from app.domain.scenarios import build_vs_cbet_spot

    s = build_vs_cbet_spot(random.Random(13), eff_bb=100.0)
    p = get_provider()
    res = asyncio.run(p.evaluate(s, Decision(action=ActionType.CALL)))
    assert res.leak_category == 201  # VS_CBET
    assert res.correctness is not None


# --- Phase 2e-1: facing a flop check-raise ---
def _flop_bet(spot):
    """Hero's (the aggressor's) flop c-bet amount from action_history."""
    return next(
        h.amount_bb
        for h in spot.action_history
        if h.action == ActionType.BET and h.position == spot.hero.position
    )


def _flop_raise(spot):
    """The defender's flop check-raise total from action_history."""
    return next(
        h.amount_bb
        for h in spot.action_history
        if h.action == ActionType.RAISE and h.position == spot.facing
    )


def test_check_raise_spot_is_valid_flop_with_ranges():
    from app.domain.scenarios import build_check_raise_spot
    from app.domain.spot import Street

    s = build_check_raise_spot(random.Random(7), eff_bb=100.0, raise_mult=2.5)
    assert s.street == Street.FLOP and len(s.board) == 3
    assert s.node_context == [NodeContext.VS_CHECK_RAISE]
    # hero is the ORIGINAL aggressor (opener / c-bettor), still to act
    hero_ps = next(p for p in s.players if p.is_hero)
    assert hero_ps.position == s.hero.position == s.to_act
    assert s.facing is not None and s.facing != s.hero.position  # villain = check-raiser
    # the defender's RAISE (check-raise) sits in the history at raise_to
    raise_h = next(
        h for h in s.action_history if h.action == ActionType.RAISE and h.position == s.facing
    )
    assert raise_h.amount_bb == _flop_raise(s)
    assert s.hero_range and s.villain_range
    acts = {la.action for la in s.legal_actions}
    assert acts == {ActionType.FOLD, ActionType.CALL, ActionType.RAISE}
    # cards disjoint: hole ∩ board == ∅
    cards = list(s.hero.hole_cards) + s.board
    assert len(set(cards)) == 5


def test_check_raise_call_size_is_incremental_not_total():
    """THE refuter-caught bug: hero already has `cbet` invested this street, so
    the CALL amount is the delta `raise_to - cbet`, NOT the raise's raw total."""
    from app.domain.scenarios import build_check_raise_spot

    s = build_check_raise_spot(
        random.Random(3), pairing=(Position.BTN, Position.BB), eff_bb=100.0, raise_mult=2.5
    )
    cbet = _flop_bet(s)
    raise_to = _flop_raise(s)
    call = next(la.min_bb for la in s.legal_actions if la.action == ActionType.CALL)
    assert call == round(raise_to - cbet, 2)  # incremental delta owed
    assert call != raise_to  # NOT the raise-to total (the double-count bug)
    assert call < raise_to  # hero's own c-bet already counts toward the call


def test_check_raise_pot_includes_both_bets():
    from app.domain.scenarios import build_check_raise_spot

    s = build_check_raise_spot(
        random.Random(9), pairing=(Position.CO, Position.BB), eff_bb=100.0, raise_mult=3.0
    )
    cbet = _flop_bet(s)
    raise_to = _flop_raise(s)
    osize = 2.5  # CO open
    flop_pot = round(2 * osize + 0.5, 2)
    assert s.pot_bb == round(flop_pot + cbet + raise_to, 2)


def test_check_raise_has_concrete_numeric_raise_size():
    from app.domain.scenarios import build_check_raise_spot

    s = build_check_raise_spot(random.Random(5), eff_bb=100.0, raise_mult=2.5)
    raise_la = next(la for la in s.legal_actions if la.action == ActionType.RAISE)
    assert raise_la.min_bb is not None and raise_la.min_bb > 0  # concrete 4-bet size


def test_check_raise_raise_mult_differentiates_faced_bet_bucket():
    """A wider check-raise must land in a different `faced_bet_bucket` than a
    modest 2.5x one at the SAME c-bet baseline (via the builder's raise_mult
    param). The 2.5x lands in "small" only when the internally-chosen c-bet is
    the 0.33-pot size, so scan seeds for one that does, then confirm a much
    wider raise on the SAME baseline flips it to "big"."""
    from app.domain.scenarios import build_check_raise_spot
    from app.domain.srs import faced_bet_bucket

    pairing = (Position.BTN, Position.BB)
    for seed in range(200):
        small = build_check_raise_spot(
            random.Random(seed), pairing=pairing, eff_bb=100.0, raise_mult=2.5
        )
        if faced_bet_bucket(small) != "small":
            continue
        big = build_check_raise_spot(
            random.Random(seed), pairing=pairing, eff_bb=100.0, raise_mult=6.0
        )
        # same seed + pairing => identical flop_pot and c-bet baseline
        assert _flop_bet(small) == _flop_bet(big)
        assert faced_bet_bucket(small) == "small"
        assert faced_bet_bucket(big) == "big"
        return
    raise AssertionError("no seed produced a small-bucket 2.5x check-raise")


def test_check_raise_faced_bet_bucket_valid_for_defaults():
    """faced_bet_bucket runs and returns a valid bucket for default-sampled
    check-raise spots (they always carry a CALL legal action)."""
    from app.domain.scenarios import sample_check_raise_spot
    from app.domain.srs import faced_bet_bucket

    rng = random.Random(21)
    for _ in range(20):
        s = sample_check_raise_spot(rng)
        assert faced_bet_bucket(s) in {"small", "big"}


# --- game-table T3: postflop builders emit 9 seats via the shared helper ---


def test_postflop_builders_emit_nine_seats_exactly_two_in():
    from app.domain.postflop import _villain_pos
    from app.domain.scenarios import build_cbet_spot, build_check_raise_spot, build_vs_cbet_spot
    from app.domain.srs import faced_bet_bucket

    pairing = (Position.CO, Position.BB)
    for build in (build_cbet_spot, build_vs_cbet_spot, build_check_raise_spot):
        s = build(random.Random(7), pairing=pairing, eff_bb=100.0)
        assert len(s.players) == 9
        assert [p.position for p in s.players] == _ALL_SEATS  # one seat per position
        in_seats = {p.position for p in s.players if p.status == PlayerStatus.IN}
        assert in_seats == set(pairing)  # exactly the opener/caller pairing
        # every folded seat has exactly one preflop FOLD history entry
        folded = sorted(p.position for p in s.players if p.status == PlayerStatus.FOLDED)
        assert sorted(_fold_positions(s)) == folded
        # _villain_pos resolves the pairing villain, never a folded seat
        villain = pairing[0] if s.hero.position == pairing[1] else pairing[1]
        assert _villain_pos(s) == villain
        # faced_bet_bucket still computes cleanly (FOLD entries filtered out)
        assert faced_bet_bucket(s) in {"none", "small", "big"}


def test_postflop_builders_sb_posts_then_folds_facing_the_open():
    from app.domain.scenarios import build_cbet_spot, build_check_raise_spot, build_vs_cbet_spot

    for build in (build_cbet_spot, build_vs_cbet_spot, build_check_raise_spot):
        s = build(random.Random(3), pairing=(Position.BTN, Position.BB), eff_bb=100.0)
        hist = s.action_history
        sb_post = next(
            i
            for i, h in enumerate(hist)
            if h.action == ActionType.POST and h.position == Position.SB
        )
        open_idx = next(
            i
            for i, h in enumerate(hist)
            if h.action == ActionType.RAISE and h.street == Street.PREFLOP
        )
        sb_fold = next(
            i
            for i, h in enumerate(hist)
            if h.action == ActionType.FOLD and h.position == Position.SB
        )
        assert sb_post < open_idx < sb_fold  # SB posted, then folded facing the open


def test_check_raise_sample_is_deterministic_with_seed():
    from app.domain.scenarios import sample_check_raise_spot

    a = sample_check_raise_spot(random.Random(4))
    b = sample_check_raise_spot(random.Random(4))
    assert a.hero.hole_cards == b.hero.hole_cards
    assert a.board == b.board
    assert a.pot_bb == b.pot_bb
