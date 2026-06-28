"""Range-correctness sanity (maker != checker for the authored content packs)."""

from app.domain.content.notation import parse_range
from app.domain.content.registry import build_index, load_preflop_packs
from app.domain.spot import ActionType, NodeContext, Position

IDX = build_index(load_preflop_packs())
_RFI_POS = [Position.UTG, Position.LJ, Position.HJ, Position.CO, Position.BTN]


def _raise_combos(entry):
    out = set()
    for a in entry.actions:
        if a.action == ActionType.RAISE:
            out |= parse_range(a.combos)
    return out


def _rfi(pos):
    return IDX[(NodeContext.RFI, pos, None, 0, None)]


def test_aa_in_every_rfi_range():
    for pos in [*_RFI_POS, Position.SB]:
        assert "AA" in _raise_combos(_rfi(pos))


def test_trash_absent_from_early_position():
    early = _raise_combos(_rfi(Position.UTG))
    for junk in ["72o", "32o", "T2o", "94o", "85o", "J2o"]:
        assert junk not in early


def test_rfi_widens_by_position():
    sizes = {pos: len(_raise_combos(_rfi(pos))) for pos in _RFI_POS}
    assert (
        sizes[Position.UTG]
        < sizes[Position.LJ]
        < sizes[Position.HJ]
        < sizes[Position.CO]
        < sizes[Position.BTN]
    )


def test_3bet_and_defense_ranges_are_value_heavy():
    for (ctx, *_), entry in IDX.items():
        if ctx in (NodeContext.VS_RFI, NodeContext.BLIND_DEFENSE):
            rc = _raise_combos(entry)
            assert "AA" in rc and "KK" in rc, f"{ctx} {entry.position} missing premiums"


# --- Phase 1b: facing-aggression packs ---
def test_vs_3bet_and_4bet_raise_ranges_value_heavy():
    for (ctx, *_), entry in IDX.items():
        if ctx in (NodeContext.VS_3BET, NodeContext.VS_4BET):
            rc = _raise_combos(entry)
            assert "AA" in rc and "KK" in rc, f"{ctx} {entry.position} vs {entry.facing}"


def test_no_entry_faces_itself():
    for ctx, pos, facing, _limp, _vt in IDX.keys():
        assert pos != facing, f"{ctx} {pos} faces itself"


def test_vs_4bet_continue_range_is_tight():
    for (ctx, *_), entry in IDX.items():
        if ctx == NodeContext.VS_4BET:
            cont = set()
            for a in entry.actions:
                cont |= parse_range(a.combos)
            for junk in ["72o", "32o", "J2o", "T5o", "96o"]:
                assert junk not in cont
