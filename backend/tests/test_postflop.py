from app.domain.action import Decision
from app.domain.evaluation import Correctness
from app.domain.leaks import LeakCategory
from app.domain.postflop import (
    _hand_category,
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
            HistoryAction(street=Street.FLOP, position=villain, action=ActionType.BET, amount_bb=faced),
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
    fold = grade_vs_cbet(spot, spot.hero_range, spot.villain_range, Decision(action=ActionType.FOLD))
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
    sized = grade_vs_cbet(
        spot, None, None, Decision(action=ActionType.RAISE, size_bb=3 * SMALL)
    )
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
