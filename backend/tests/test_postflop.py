from app.domain.action import Decision
from app.domain.evaluation import Correctness
from app.domain.leaks import LeakCategory
from app.domain.postflop import (
    _CAT_VALUE,
    _cbet_fold_equity_value,
    _hand_category,
    _merits,
    _merits_vs_cbet,
    cbet_fold_pct,
    grade_cbet,
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


POST_LOSS_FLOOR = 0.6


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
