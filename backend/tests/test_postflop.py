from app.domain.action import Decision
from app.domain.evaluation import ActionEval, Correctness
from app.domain.leaks import LeakCategory
from app.domain.postflop import (
    _CAT_VALUE,
    _bet_sizing_verdict,
    _cbet_fold_equity_value,
    _hand_category,
    _merits,
    _merits_vs_cbet,
    _villain_pos,
    cbet_fold_pct,
    grade_cbet,
    grade_river_barrel,
    grade_turn_barrel,
    grade_vs_cbet,
    grade_vs_check_raise,
    range_advantage,
    range_advantage_defender,
)
from app.domain.spot import (
    ActionType,
    GameConfig,
    Hero,
    HistoryAction,
    LegalAction,
    NodeContext,
    PlayerState,
    PlayerStatus,
    Position,
    Spot,
    Stakes,
    Street,
)
from app.domain.texture import classify

SMALL, BIG = 2.0, 4.5


def _cbet_spot(hole, board, hero_pos=Position.BTN, villain_pos=Position.BB):
    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=6.0,
        hero=Hero(position=hero_pos, hole_cards=hole, stack_bb=100),
        players=[
            PlayerState(position=hero_pos, stack_bb=100, is_hero=True),
            PlayerState(position=villain_pos, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=15.0,
        to_act=hero_pos,
        node_context=[NodeContext.CBET],
        facing=villain_pos,
        legal_actions=[
            LegalAction(action=ActionType.CHECK),
            LegalAction(action=ActionType.BET, min_bb=SMALL),
            LegalAction(action=ActionType.BET, min_bb=BIG),
        ],
        hero_range="22+, A2s+, KTs+, ATo+, KQo",
        villain_range="22-99, A2s+, KTs+, QJs, ATo+, KJo+",
    )


def test_range_advantage_high_dry_favors_hero():
    tex = classify(["As", "Kd", "2c"])
    assert range_advantage(NodeContext.CBET, Position.BTN, Position.BB, tex) == "hero"


def test_range_advantage_low_connected_favors_villain():
    tex = classify(["7h", "6h", "5c"])
    adv = range_advantage(NodeContext.CBET, Position.BTN, Position.BB, tex)
    assert adv in ("villain", "neutral")


def test_dry_range_adv_small_bet_is_optimal():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])  # top pair, dry, hero adv
    res = grade_cbet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.BET, size_bb=SMALL)
    )
    assert res.correctness == Correctness.OPTIMAL
    assert res.best_action.action == ActionType.BET
    assert res.best_action.size_bb == SMALL
    assert res.leak_category == int(LeakCategory.FLOP_CBET)


def test_big_bet_oop_air_wet_is_worse():
    # CO opens, BTN calls -> hero (CO) is OOP; wet low board; pure air; barrel big.
    spot = _cbet_spot(
        ("As", "Kd"), ["9h", "8h", "6c"], hero_pos=Position.CO, villain_pos=Position.BTN
    )
    res = grade_cbet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.BET, size_bb=BIG)
    )
    assert res.best_action.action == ActionType.CHECK
    assert res.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)
    assert res.ev_loss_bb > POST_LOSS_FLOOR


def test_optimal_call_without_decision_has_no_chosen():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    res = grade_cbet(spot, spot.hero_range, spot.villain_range, None)
    assert res.chosen_eval is None
    assert res.best_action is not None
    assert {e.action for e in res.per_action} == {ActionType.CHECK, ActionType.BET}


def test_frequencies_normalized():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    res = grade_cbet(spot, spot.hero_range, spot.villain_range, None)
    total = sum(e.frequency for e in res.per_action)
    assert abs(total - 1.0) < 1e-6


# --- Phase 2e-0 T2: _hand_category made-hand fixes ---
# `_hand_category` is exercised directly here (not just through grade_cbet/
# grade_vs_cbet) so each fixed bug has its own explicit category-string anchor,
# per the ticket's "Verify-by" list, not just "the grader still runs".


def test_made_flush_on_monotone_board_is_strong():
    # Ah-Kh-2h is a monotone flop; Qh-Jh completes a 5-card flush. Previously this
    # fell through to the flush_draw flag (>=4 of a suit) and misclassified a MADE
    # flush as a "draw". Bug #2 from Phase 2e-0 T2.
    assert _hand_category(("Qh", "Jh"), ["Ah", "Kh", "2h"]) == "strong"


def test_made_straight_is_strong():
    # 5-6-7-8-9 across hole+board is a completed straight. Previously this fell
    # through to the OESD flag (4 consecutive ranks present) and misclassified a
    # MADE straight as a "draw". Bug #2 from Phase 2e-0 T2.
    assert _hand_category(("6s", "5h"), ["9h", "8d", "7c"]) == "strong"


def test_plain_top_pair_is_weak_made_not_strong():
    # Regression anchor for the live 2b bug: `if made >= 2: return "strong"` used
    # to conflate plain top pair (made == 2, no kicker concept) with two-pair/set
    # (made == 3) -- both graded "strong". Top pair of aces (marginal-kicker-
    # agnostic) must now grade "weak_made" so grade_vs_cbet stops recommending
    # "never fold" with plain top pair vs. a big c-bet. Bug #1 from Phase 2e-0 T2.
    assert _hand_category(("As", "Th"), ["Ah", "Kd", "2c"]) == "weak_made"


def test_two_pair_or_set_is_still_strong():
    # made == 3 (two-pair/set) is unaffected by the top-pair demotion.
    assert _hand_category(("Ac", "Kh"), ["Ah", "Kd", "2c"]) == "strong"


def test_unmade_flush_draw_is_still_draw():
    # Exactly 4 of a suit (2 hole + 2 board), no 5th card, and no rank adjacency
    # (Q-7 vs. board A-K-2 can't also trip the OESD flag) so this anchor isolates
    # the flush_draw path specifically rather than passing by coincidence via
    # OESD. Confirms flush_draw still fires for the genuinely-unmade case now that
    # the made-flush check runs first (bug #3 from Phase 2e-0 T2).
    assert _hand_category(("Qh", "7h"), ["Ah", "Kh", "2c"]) == "draw"


def test_unmade_oesd_is_still_draw():
    # 4 consecutive ranks present (J-Q-K-A), T missing -- no pair, no 5-of-a-suit.
    # Confirms the OESD flag still fires for a genuinely-unmade straight draw now
    # that the made-straight check runs first.
    assert _hand_category(("Qc", "Jd"), ["Ah", "Kd", "2c"]) == "draw"


# --- S7: 5-card-board _hand_category fixtures (roadmap regression guard) ---
# `_hand_category`'s arithmetic is length-agnostic but was never exercised at
# board len 5 before S7 (flop tests are 3-card, turn tests 4-card). These
# fixtures spot-check the 4-flush/4-straight-completing-river cases the river
# graders rely on for the busted-draw demotion (contract §4).


def test_made_flush_on_5card_board_is_strong():
    # Board carries 4 hearts (4-flush board); hero's Qh completes the 5th heart
    # for a made flush on the river.
    board = ["Ah", "Kh", "2h", "9h", "3c"]
    assert _hand_category(("Qh", "Jh"), board) == "strong"


def test_busted_flush_draw_on_5card_board_is_draw():
    # Hero has 2 hearts, board has 2 hearts (4 total) and the river bricks with
    # a non-heart -- the flush never completes. Documents WHY the river graders
    # must demote this to "air" for merits/tags: raw _hand_category still
    # returns "draw" (carrying _CAT_VALUE["draw"]=1.2, 2nd-highest value tier)
    # even though zero outs remain once the river is dealt.
    board = ["Ah", "Kh", "2c", "9d", "3c"]
    assert _hand_category(("Qh", "7h"), board) == "draw"


def test_made_straight_on_5card_board_is_strong():
    # 5-6-7-8-9 across hole+board is a completed straight on a 5-card board.
    board = ["9h", "8d", "7c", "2s", "4d"]
    assert _hand_category(("6s", "5h"), board) == "strong"


def test_busted_oesd_on_5card_board_is_draw():
    # 4 consecutive ranks (J-Q-K-A) present, T missing, and the river bricks --
    # the straight never completes. Documents the same overvaluation hazard as
    # the busted flush draw above: raw _hand_category still returns "draw" with
    # zero outs remaining.
    board = ["Ah", "Kd", "2c", "9s", "3h"]
    assert _hand_category(("Qc", "Jd"), board) == "draw"


POST_LOSS_FLOOR = 0.6


# --- game-table T1: _villain_pos hardening (folded seats must never be picked) ---


def _with_folded_seats(spot, hero_pos, villain_pos):
    """Enriched player list: FOLDED seats BEFORE the real (IN) villain, plus
    facing cleared, so the villain can only be found via the status filter."""
    players = [
        PlayerState(position=Position.LJ, stack_bb=100, status=PlayerStatus.FOLDED),
        PlayerState(position=Position.HJ, stack_bb=100, status=PlayerStatus.FOLDED),
        PlayerState(position=hero_pos, stack_bb=100, is_hero=True),
        PlayerState(position=Position.UTG, stack_bb=100, status=PlayerStatus.FOLDED),
        PlayerState(position=villain_pos, stack_bb=100),
    ]
    return spot.model_copy(update={"players": players, "facing": None})


def test_villain_pos_prefers_facing():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    # a non-hero IN seat precedes the facing villain — facing must still win
    players = [
        PlayerState(position=Position.CO, stack_bb=100),
        PlayerState(position=Position.BTN, stack_bb=100, is_hero=True),
        PlayerState(position=Position.BB, stack_bb=100),
    ]
    assert _villain_pos(spot.model_copy(update={"players": players})) == Position.BB


def test_villain_pos_skips_folded_seats_without_facing():
    spot = _with_folded_seats(
        _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"]), Position.BTN, Position.BB
    )
    assert spot.facing is None
    assert _villain_pos(spot) == Position.BB  # not LJ/HJ/UTG (all FOLDED)


def test_grade_cbet_unaffected_by_folded_seats():
    base = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    enriched = _with_folded_seats(base, Position.BTN, Position.BB)
    decision = Decision(action=ActionType.BET, size_bb=SMALL)
    a = grade_cbet(base, base.hero_range, base.villain_range, decision)
    b = grade_cbet(enriched, enriched.hero_range, enriched.villain_range, decision)
    assert b.best_action == a.best_action
    assert b.correctness == a.correctness
    assert b.per_action == a.per_action


def test_grade_vs_check_raise_unaffected_by_folded_seats():
    base = _vscr_spot(("Ad", "Th"), ["As", "Kd", "2c"], faced=SMALL)
    enriched = _with_folded_seats(base, Position.BTN, Position.BB)
    a = grade_vs_check_raise(base, base.hero_range, base.villain_range, None)
    b = grade_vs_check_raise(enriched, enriched.hero_range, enriched.villain_range, None)
    assert b.best_action == a.best_action
    assert b.per_action == a.per_action


# --- Phase 2b: facing a c-bet (defense) ---
FLOP_POT = 6.0


def _vscbet_spot(hole, board, faced, hero=Position.BB, villain=Position.BTN):
    pot = FLOP_POT + faced
    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=pot,
        hero=Hero(position=hero, hole_cards=hole, stack_bb=100),
        players=[
            PlayerState(position=hero, stack_bb=100, is_hero=True),
            PlayerState(position=villain, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=round((100 - faced) / pot, 1),
        to_act=hero,
        node_context=[NodeContext.VS_CBET],
        facing=villain,
        action_history=[
            HistoryAction(
                street=Street.FLOP, position=villain, action=ActionType.BET, amount_bb=faced
            ),
        ],
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=faced),
            LegalAction(action=ActionType.RAISE, min_bb=round(3 * faced, 1), max_bb=100),
        ],
        hero_range="22-99, ATs+, KJs+, QJs, AJo+, KQo",
        villain_range="22+, A2s+, K9s+, Q9s+, J9s+, T8s+, AJo+, KQo",
    )


def test_defender_range_advantage_anchors():
    low_wet = classify(["8h", "7h", "6c"])
    assert range_advantage_defender(Position.BTN, Position.BB, low_wet) == "defender"
    high_dry = classify(["As", "Kd", "2c"])
    assert range_advantage_defender(Position.BTN, Position.BB, high_dry) == "aggressor"
    # high & wet (the case the 2a reuse-trick could not reach) -> not aggressor
    high_wet = classify(["Kh", "Qh", "Jh"])
    assert range_advantage_defender(Position.BTN, Position.BB, high_wet) != "aggressor"


def test_strong_never_folds_vs_cbet():
    spot = _vscbet_spot(("As", "Ac"), ["Ah", "Kd", "2c"], faced=SMALL)  # top set
    res = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action in (ActionType.CALL, ActionType.RAISE)
    assert res.leak_category == int(LeakCategory.VS_CBET)
    fold = grade_vs_cbet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.FOLD)
    )
    assert fold.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)


def test_air_high_dry_big_bet_folds():
    spot = _vscbet_spot(("7d", "2h"), ["As", "Kd", "9c"], faced=BIG)  # pure air, aggressor board
    res = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action == ActionType.FOLD


def test_draw_wet_defender_favored_continues():
    # flush draw on a low connected wet board where the defender has the edge
    spot = _vscbet_spot(("9h", "8h"), ["7h", "6h", "2c"], faced=SMALL)
    res = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action in (ActionType.CALL, ActionType.RAISE)
    assert res.best_action.action != ActionType.FOLD
    raise_eval = next(e for e in res.per_action if e.action == ActionType.RAISE)
    assert raise_eval.frequency > 0  # semibluff raise is a defensible mix


def test_bet_size_monotonic_defense():
    hole, board = ("Qd", "Jc"), ["Qh", "8d", "3s"]  # top pair (weak-ish made hand)
    small = grade_vs_cbet(_vscbet_spot(hole, board, SMALL), None, None, None)
    big = grade_vs_cbet(_vscbet_spot(hole, board, BIG), None, None, None)

    def freq(res, action):
        return next(e.frequency for e in res.per_action if e.action == action)

    assert freq(small, ActionType.CALL) >= freq(big, ActionType.CALL)
    assert freq(small, ActionType.FOLD) <= freq(big, ActionType.FOLD)


def test_vs_cbet_frequencies_normalized_and_raise_sized():
    spot = _vscbet_spot(("As", "Ac"), ["Ah", "7d", "2c"], faced=SMALL)
    res = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, None)
    assert abs(sum(e.frequency for e in res.per_action) - 1.0) < 1e-6
    # a sized raise decision grades without a Decision validation error
    sized = grade_vs_cbet(spot, None, None, Decision(action=ActionType.RAISE, size_bb=3 * SMALL))
    assert sized.correctness is not None


# --- Phase 2e-1: facing a flop check-raise (hero = original c-bettor) ---


def _vscr_spot(hole, board, faced, pot=None, hero=Position.BTN, villain=Position.BB):
    """A flop check-raise spot: hero c-bet, defender check-raised, hero (still the
    original aggressor) now faces fold/call/raise. Built inline like _vscbet_spot —
    T4 owns the real builder (build_check_raise_spot), which does not exist yet."""
    if pot is None:
        pot = FLOP_POT + faced
    cbet = 2.0
    raise_to = round(cbet + faced, 2)  # CALL.min_bb (faced) is the incremental delta
    return Spot(
        game=GameConfig(stakes=Stakes(sb=0.5, bb=1.0), table_size=9),
        street=Street.FLOP,
        board=board,
        pot_bb=pot,
        hero=Hero(position=hero, hole_cards=hole, stack_bb=100),
        players=[
            PlayerState(position=hero, stack_bb=100, is_hero=True),
            PlayerState(position=villain, stack_bb=100),
        ],
        effective_stack_bb=100,
        spr=round((100 - faced) / pot, 1),
        to_act=hero,
        node_context=[NodeContext.VS_CHECK_RAISE],
        facing=villain,
        action_history=[
            HistoryAction(street=Street.FLOP, position=hero, action=ActionType.BET, amount_bb=cbet),
            HistoryAction(
                street=Street.FLOP, position=villain, action=ActionType.RAISE, amount_bb=raise_to
            ),
        ],
        legal_actions=[
            LegalAction(action=ActionType.FOLD),
            LegalAction(action=ActionType.CALL, min_bb=faced),
            LegalAction(action=ActionType.RAISE, min_bb=round(3 * raise_to, 1), max_bb=100),
        ],
        hero_range="22+, A2s+, KTs+, ATo+, KQo",
        villain_range="22-99, A2s+, KTs+, QJs, ATo+, KJo+",
    )


def _fold_freq(res):
    return next(e.frequency for e in res.per_action if e.action == ActionType.FOLD)


def test_strong_never_folds_vs_check_raise():
    # (a) top set vs a check-raise -> raise or call, never fold.
    spot = _vscr_spot(("As", "Ac"), ["Ah", "Kd", "2c"], faced=SMALL)
    res = grade_vs_check_raise(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action in (ActionType.CALL, ActionType.RAISE)
    assert res.best_action.action != ActionType.FOLD
    assert _fold_freq(res) < min(
        e.frequency for e in res.per_action if e.action in (ActionType.CALL, ActionType.RAISE)
    )
    fold = grade_vs_check_raise(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.FOLD)
    )
    assert fold.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)


def test_air_high_dry_folds_vs_check_raise():
    # (b) pure air on a high/dry board vs a check-raise -> fold is the clear best.
    spot = _vscr_spot(("7d", "4h"), ["As", "Kd", "2c"], faced=BIG)
    res = grade_vs_check_raise(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action == ActionType.FOLD


def test_combo_draw_low_wet_calls_raise_is_mix_vs_check_raise():
    # (c) flush draw + OESD on a low-connected-wet board -> call best; raise (semibluff)
    # a defensible non-zero mix.
    spot = _vscr_spot(("Ah", "9h"), ["8h", "7h", "6c"], faced=SMALL)
    res = grade_vs_check_raise(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action == ActionType.CALL
    raise_eval = next(e for e in res.per_action if e.action == ActionType.RAISE)
    assert raise_eval.frequency > 0


def test_fold_baseline_higher_than_vs_cbet():
    # (d) THE KEY TEST: a fixed weak_made hand (top pair) on a DRY board must fold
    # MORE OFTEN facing a check-raise than facing a plain c-bet — the check-raise-
    # strength prior (§10.3) is doing real work, not a cosmetic baseline bump.
    hole, board = ("Ad", "Th"), ["As", "Kd", "2c"]  # top pair aces -> weak_made
    assert _hand_category(hole, board) == "weak_made"
    cr = grade_vs_check_raise(_vscr_spot(hole, board, SMALL), None, None, None)
    vc = grade_vs_cbet(_vscbet_spot(hole, board, SMALL), None, None, None)
    cr_fold, vc_fold = _fold_freq(cr), _fold_freq(vc)
    print(f"\n[fold-baseline] vs_check_raise fold={cr_fold} vs_cbet fold={vc_fold}")
    assert cr_fold > vc_fold


def test_vs_check_raise_leak_category_is_202():
    # (e) leak = VS_CHECK_RAISE (202) on a graded result.
    spot = _vscr_spot(("Ad", "Th"), ["As", "Kd", "2c"], faced=SMALL)
    res = grade_vs_check_raise(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.CALL, size_bb=SMALL)
    )
    assert res.leak_category == int(LeakCategory.VS_CHECK_RAISE)
    assert int(LeakCategory.VS_CHECK_RAISE) == 202


def test_made_flush_reads_strong_from_check_raise_grader():
    # (f) regression guard: a made flush (monotone board, hero holds 2 more of the
    # suit) grades as effectively "strong" here — never fold — honoring the 2e-0
    # _hand_category fix from this grader's call site.
    hole, board = ("Qh", "Jh"), ["Ah", "Kh", "2h"]
    assert _hand_category(hole, board) == "strong"
    spot = _vscr_spot(hole, board, faced=SMALL)
    res = grade_vs_check_raise(spot, spot.hero_range, spot.villain_range, None)
    assert res.best_action.action in (ActionType.CALL, ActionType.RAISE)
    assert res.best_action.action != ActionType.FOLD


def test_vs_check_raise_frequencies_normalized_and_raise_sized():
    spot = _vscr_spot(("As", "Ac"), ["Ah", "Kd", "2c"], faced=SMALL)
    res = grade_vs_check_raise(spot, spot.hero_range, spot.villain_range, None)
    assert abs(sum(e.frequency for e in res.per_action) - 1.0) < 1e-6
    sized = grade_vs_check_raise(
        spot, None, None, Decision(action=ActionType.RAISE, size_bb=3 * (2.0 + SMALL))
    )
    assert sized.correctness is not None


# --- CW-2 (doc 06 errata): suitedness + pairing wired into the merit functions ---


def test_monotone_checks_more_and_bets_smaller_than_two_tone():
    # Same ranks/connectedness (K-J-7, semi-connected, high) -- suits differ only
    # in suitedness: two-tone (Kh Jh 7d) vs monotone (Kh Jh 7h). Both classify as
    # "wet" under `classify()` (suitedness folds monotone into the wetness score),
    # which is exactly why `_merits()` used to treat them identically -- it only
    # branched on `texture.wetness`, never `texture.suitedness`. Doc 06 §2: a
    # monotone board should check more and, when bet, size down vs. a two-tone
    # wet board (small-only, not the big/polarized menu).
    two_tone = classify(["Kh", "Jh", "7d"])
    monotone = classify(["Kh", "Jh", "7h"])
    assert two_tone.suitedness == "two-tone"
    assert monotone.suitedness == "monotone"
    assert two_tone.wetness == monotone.wetness == "wet"  # same bucket pre-fix

    check_tt, small_tt, big_tt = _merits("neutral", two_tone, "weak_made")
    check_mono, small_mono, big_mono = _merits("neutral", monotone, "weak_made")

    assert check_mono > check_tt  # bets (checks) less often on monotone
    assert big_mono < big_tt  # doesn't polarize big on monotone
    # small is preferred over big by a wider margin on monotone than two-tone
    assert (small_mono - big_mono) > (small_tt - big_tt)


def test_paired_board_raises_defender_check_raise():
    # Doc 06 §4: paired boards (Q♥Q♣6♦ example) get check-raised ~24% vs 5-9% on
    # other textures -- `_merits_vs_cbet`'s raise_ never read `texture.pairing`
    # before this fix (confirmed by grep: the string didn't appear in the file).
    paired = classify(["Qh", "Qc", "6d"])
    unpaired = classify(["Kh", "Qc", "6d"])  # same high-card tier, unpaired
    assert paired.pairing == "paired"
    assert unpaired.pairing == "unpaired"

    _, _, raise_paired = _merits_vs_cbet(
        value=0.8, adv="defender", price=0.33, texture=paired, cat="weak_made"
    )
    _, _, raise_unpaired = _merits_vs_cbet(
        value=0.8, adv="defender", price=0.33, texture=unpaired, cat="weak_made"
    )
    assert raise_paired > raise_unpaired

    # the bump is specific to the DEFENDER's check-raise -- it must not leak
    # into the aggressor's/neutral's raise merit on the very same paired board.
    _, _, raise_aggressor = _merits_vs_cbet(
        value=0.8, adv="aggressor", price=0.33, texture=paired, cat="weak_made"
    )
    assert raise_aggressor < raise_paired


def test_ace_high_board_scored_below_other_high_boards():
    # Doc 06 §2 (citing this project's own doc 02): ace-high boards are a
    # documented exception -- the aggressor's range/nut edge is smaller than on
    # other high-card (K/Q/J/T) boards, because live BB defenders over-continue
    # with any ace. Same shape (rainbow, semi-connected, unpaired, span=6) on
    # both boards -- only the top card differs (K vs A) -- isolating the
    # ace-high discount from any wetness/connectedness difference.
    king_high = classify(["Kh", "8d", "7c"])
    ace_high = classify(["Ah", "9d", "8c"])
    assert king_high.high_card == "K" and king_high.wetness == "medium"
    assert ace_high.high_card == "A" and ace_high.wetness == "medium"

    king_adv = range_advantage(NodeContext.CBET, Position.BTN, Position.BB, king_high)
    ace_adv = range_advantage(NodeContext.CBET, Position.BTN, Position.BB, ace_high)
    assert king_adv == "hero"
    assert ace_adv != "hero"  # ace-high doesn't clear the "hero" bar the K-high board does


# --- N2: interim fold-equity EV (doc-08 §3.2) grounds grade_cbet's `value` term ---


def test_cbet_fold_pct_matches_doc06_cited_textures():
    paired_dry = classify(["Qh", "Qc", "6d"])  # doc-06 §2/§4: 37% fold
    monotone = classify(["Qd", "Jd", "Td"])  # doc-06 §2: 37% fold
    wet_two_tone = classify(["Kh", "Jh", "7d"])  # doc-06 §2: 62% fold
    assert cbet_fold_pct(paired_dry) == 0.37
    assert cbet_fold_pct(monotone) == 0.37
    assert cbet_fold_pct(wet_two_tone) == 0.62


def test_grade_cbet_value_is_grounded_in_real_equity_not_flat_category_guess():
    # Pure air (two live overcards, no pair/draw) on a low wet board actually
    # retains real equity vs a wide continuing range -- doc-08 §1.3's headline
    # finding that flat category buckets misprice hands. The old flat
    # `_CAT_VALUE["air"] == 0.0` floor must no longer be what feeds `_merits`
    # once a real villain_range/board is available to compute equity from.
    spot = _cbet_spot(
        ("As", "Kd"), ["9h", "8h", "6c"], hero_pos=Position.CO, villain_pos=Position.BTN
    )
    tex = classify(spot.board)
    value = _cbet_fold_equity_value(spot, spot.board, tex, spot.villain_range)
    assert value is not None
    assert value != _CAT_VALUE["air"]


def test_grade_cbet_falls_back_to_category_value_without_a_villain_range():
    # No villain_range/pot context (e.g. a bare unit-test spot) -> `_merits`
    # keeps using the flat category lookup, so existing direct-call tests of
    # `_merits`/`_merits_vs_cbet` (which never pass `value_override`) stay valid.
    spot = _cbet_spot(("As", "Kd"), ["9h", "8h", "6c"])
    tex = classify(spot.board)
    assert _cbet_fold_equity_value(spot, spot.board, tex, None) is not None  # "*" fallback range
    spot_no_pot = spot.model_copy(update={"pot_bb": 0.0})
    assert _cbet_fold_equity_value(spot_no_pot, spot_no_pot.board, tex, None) is None


# --- N4a: additive bet-sizing verdict (`_bet_sizing_verdict`) ---------------


def _bet(size, freq, ev=0.0):
    return ActionEval(action=ActionType.BET, size_bb=size, frequency=freq, ev_bb=ev)


def _check_eval(freq=0.0):
    return ActionEval(action=ActionType.CHECK, size_bb=None, frequency=freq, ev_bb=0.0)


def test_bet_sizing_verdict_higher_freq_size_is_optimal():
    small, big = _bet(2.0, 0.7), _bet(4.5, 0.3)
    assert _bet_sizing_verdict([small, big], small) == Correctness.OPTIMAL
    assert _bet_sizing_verdict([small, big], big) == Correctness.ACCEPTABLE


def test_bet_sizing_verdict_positive_tie_resolves_optimal():
    small, big = _bet(2.0, 0.4, ev=1.0), _bet(4.5, 0.4, ev=1.0)
    # Two POSITIVE-frequency sizes tied -> either chosen is OPTIMAL.
    assert _bet_sizing_verdict([small, big], small) == Correctness.OPTIMAL
    assert _bet_sizing_verdict([small, big], big) == Correctness.OPTIMAL


def test_bet_sizing_verdict_none_when_hero_checked():
    small, big = _bet(2.0, 0.7), _bet(4.5, 0.3)
    assert _bet_sizing_verdict([small, big], _check_eval(0.5)) is None


def test_bet_sizing_verdict_none_when_single_size():
    only = _bet(2.0, 0.6)
    assert _bet_sizing_verdict([only], only) is None


def test_bet_sizing_verdict_none_when_both_merits_zero():
    # Air/weak hand: BOTH bet sizes clamp to 0 frequency -> betting itself is the
    # mistake; no "size: Best" sub-note beside a bet-blunder (refuter LOW).
    small, big = _bet(2.0, 0.0), _bet(4.5, 0.0)
    assert _bet_sizing_verdict([small, big], small) is None
    assert _bet_sizing_verdict([small, big], big) is None


# --- N4a: graders populate sizing_correctness (additive; action unchanged) ---


def test_grade_cbet_populates_sizing_correctness_optimal():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])  # top pair, dry, hero adv
    res = grade_cbet(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.BET, size_bb=SMALL),
    )
    # Small is the higher-frequency c-bet size on a dry hero-adv board.
    assert res.sizing_correctness == Correctness.OPTIMAL
    other = grade_cbet(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.BET, size_bb=BIG),
    )
    assert other.sizing_correctness == Correctness.ACCEPTABLE


def test_grade_cbet_check_has_no_sizing_verdict():
    spot = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    res = grade_cbet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.CHECK)
    )
    assert res.sizing_correctness is None


def test_grade_cbet_action_verdict_unchanged_by_sizing_retrofit():
    # The additive sizing_correctness must not move the action correctness (R3
    # c-bet non-regression): re-assert the R3 anchor cases hold byte-for-byte.
    dry = _cbet_spot(("Ah", "Qc"), ["As", "Kd", "2c"])
    res = grade_cbet(
        dry, dry.hero_range, dry.villain_range,
        Decision(action=ActionType.BET, size_bb=SMALL),
    )
    assert res.correctness == Correctness.OPTIMAL
    assert res.best_action.action == ActionType.BET and res.best_action.size_bb == SMALL

    wet = _cbet_spot(
        ("As", "Kd"), ["9h", "8h", "6c"], hero_pos=Position.CO, villain_pos=Position.BTN
    )
    bad = grade_cbet(
        wet, wet.hero_range, wet.villain_range,
        Decision(action=ActionType.BET, size_bb=BIG),
    )
    assert bad.best_action.action == ActionType.CHECK
    assert bad.correctness in (Correctness.MISTAKE, Correctness.BLUNDER)


def _turn_barrel_spot(hole, board, hero_pos=Position.BTN, villain_pos=Position.BB):
    return _cbet_spot(hole, board, hero_pos, villain_pos).model_copy(
        update={"street": Street.TURN, "node_context": [NodeContext.TURN_BARREL]}
    )


def _river_barrel_spot(hole, board, hero_pos=Position.BTN, villain_pos=Position.BB):
    return _cbet_spot(hole, board, hero_pos, villain_pos).model_copy(
        update={"street": Street.RIVER, "node_context": [NodeContext.RIVER_BARREL]}
    )


def test_grade_turn_barrel_populates_sizing_correctness():
    spot = _turn_barrel_spot(("Ah", "Ks"), ["Ac", "Kd", "Qh", "2s"])
    ungraded = grade_turn_barrel(spot, spot.hero_range, spot.villain_range, None)
    bet_freqs = {
        e.size_bb: e.frequency for e in ungraded.per_action if e.action == ActionType.BET
    }
    top = max(bet_freqs, key=lambda s: bet_freqs[s])
    if bet_freqs[top] <= 0.0:  # degenerate spot — no size verdict at all
        res = grade_turn_barrel(
            spot, spot.hero_range, spot.villain_range,
            Decision(action=ActionType.BET, size_bb=top),
        )
        assert res.sizing_correctness is None
        return
    hi = grade_turn_barrel(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.BET, size_bb=top),
    )
    assert hi.sizing_correctness == Correctness.OPTIMAL
    check = grade_turn_barrel(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.CHECK)
    )
    assert check.sizing_correctness is None


def test_grade_river_barrel_check_has_no_sizing_verdict():
    spot = _river_barrel_spot(("Ah", "Ks"), ["Ac", "Kd", "Qh", "2s", "7d"])
    res = grade_river_barrel(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.CHECK)
    )
    assert res.sizing_correctness is None


def test_grade_river_barrel_no_size_verdict_beside_a_bet_blunder():
    # Refuter LOW, through a real grader: OOP air on a villain-advantage runout —
    # BOTH bet sizes clamp to 0 frequency, so betting is a BLUNDER and NO size
    # verdict prints beside it (no "· size: Best" next to "Blunder").
    spot = _river_barrel_spot(
        ("7c", "2d"), ["9h", "8h", "6c", "Ah", "Ks"],
        hero_pos=Position.CO, villain_pos=Position.BTN,
    )
    ungraded = grade_river_barrel(spot, spot.hero_range, spot.villain_range, None)
    bet_freqs = [e.frequency for e in ungraded.per_action if e.action == ActionType.BET]
    assert all(f == 0.0 for f in bet_freqs)  # air: both sizes zero-frequency
    res = grade_river_barrel(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.BET, size_bb=SMALL),
    )
    assert res.correctness == Correctness.BLUNDER
    assert res.sizing_correctness is None


# --- N4b: facing-raise sizing verdict (texture overlay) + big-leg build ---


def _two_raise_legs(spot, small, big):
    """Swap the spot's single RAISE leg for a small/big pair (the N4b mapper shape)."""
    legs = [la for la in spot.legal_actions if la.action != ActionType.RAISE]
    legs += [
        LegalAction(action=ActionType.RAISE, min_bb=small, max_bb=100),
        LegalAction(action=ActionType.RAISE, min_bb=big, max_bb=100),
    ]
    return spot.model_copy(update={"legal_actions": legs})


def test_two_leg_raise_eval_keys_on_big_leg():
    # Refuter HIGH-2 regression: with two RAISE legs the action-level RAISE eval
    # must key on the BIG leg (max), never ordering-dependently grab the first.
    spot = _two_raise_legs(
        _vscbet_spot(("As", "Ac"), ["Ah", "Kd", "2c"], faced=SMALL), 5.0, 6.0
    )
    res = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, None)
    raise_eval = next(e for e in res.per_action if e.action == ActionType.RAISE)
    assert raise_eval.size_bb == 6.0


def test_single_leg_facing_flow_has_no_sizing_verdict():
    # Strict superset: pre-N4b single-leg spots grade exactly as before —
    # same RAISE eval size, sizing_correctness stays unset.
    spot = _vscbet_spot(("As", "Ac"), ["Ah", "Kd", "2c"], faced=SMALL)
    res = grade_vs_cbet(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.RAISE, size_bb=3 * SMALL),
    )
    raise_eval = next(e for e in res.per_action if e.action == ActionType.RAISE)
    assert raise_eval.size_bb == round(3 * SMALL, 1)
    assert res.sizing_correctness is None


def test_raise_sizing_verdict_dry_small_optimal():
    spot = _two_raise_legs(
        _vscbet_spot(("As", "Ac"), ["Ah", "Kd", "2c"], faced=SMALL), 5.0, 6.0
    )  # Ah Kd 2c classifies dry
    assert classify(spot.board).wetness == "dry"
    small_res = grade_vs_cbet(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.RAISE, size_bb=5.0),
    )
    big_res = grade_vs_cbet(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.RAISE, size_bb=6.0),
    )
    assert small_res.sizing_correctness == Correctness.OPTIMAL
    assert big_res.sizing_correctness == Correctness.ACCEPTABLE
    # the size verdict never moves the action verdict
    assert small_res.correctness == big_res.correctness


def test_raise_sizing_verdict_wet_big_optimal():
    spot = _two_raise_legs(
        _vscbet_spot(("8s", "8d"), ["8h", "7h", "6c"], faced=SMALL), 5.0, 6.0
    )  # 8h 7h 6c classifies wet; top set keeps the raise frequency positive
    assert classify(spot.board).wetness == "wet"
    small_res = grade_vs_cbet(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.RAISE, size_bb=5.0),
    )
    big_res = grade_vs_cbet(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.RAISE, size_bb=6.0),
    )
    assert big_res.sizing_correctness == Correctness.OPTIMAL
    assert small_res.sizing_correctness == Correctness.ACCEPTABLE


def test_raise_sizing_verdict_medium_both_acceptable():
    spot = _two_raise_legs(
        _vscbet_spot(("As", "Ac"), ["Ah", "Kd", "9c"], faced=SMALL), 5.0, 6.0
    )  # Ah Kd 9c classifies medium — no forced optimal
    assert classify(spot.board).wetness == "medium"
    for size in (5.0, 6.0):
        res = grade_vs_cbet(
            spot, spot.hero_range, spot.villain_range,
            Decision(action=ActionType.RAISE, size_bb=size),
        )
        assert res.sizing_correctness == Correctness.ACCEPTABLE


def test_raise_sizing_verdict_none_beside_raise_blunder():
    # Air facing a check-raise on a dry board: raise frequency clamps to 0 —
    # raising is the mistake, so no size verdict prints beside it.
    spot = _two_raise_legs(
        _vscr_spot(("7d", "2h"), ["Ah", "Kd", "4c"], faced=SMALL), 12.0, 14.0
    )
    res = grade_vs_check_raise(
        spot, spot.hero_range, spot.villain_range,
        Decision(action=ActionType.RAISE, size_bb=12.0),
    )
    raise_eval = next(e for e in res.per_action if e.action == ActionType.RAISE)
    assert raise_eval.frequency == 0.0
    assert res.sizing_correctness is None


def test_raise_sizing_verdict_non_raise_decision_none():
    spot = _two_raise_legs(
        _vscbet_spot(("As", "Ac"), ["Ah", "Kd", "2c"], faced=SMALL), 5.0, 6.0
    )
    res = grade_vs_cbet(
        spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.CALL)
    )
    assert res.sizing_correctness is None
