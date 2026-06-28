from factories import make_rfi_spot

from app.domain.content.registry import build_index, load_preflop_packs, lookup
from app.domain.spot import NodeContext, Position


def test_packs_load_and_validate():
    packs = load_preflop_packs()
    assert len(packs) >= 4
    domains = {p.domain for p in packs}
    assert domains == {"preflop"}


def test_index_covers_all_rfi_positions():
    idx = build_index(load_preflop_packs())
    for pos in [Position.UTG, Position.LJ, Position.HJ, Position.CO, Position.BTN, Position.SB]:
        assert (NodeContext.RFI, pos, None, 0, None) in idx


def test_lookup_finds_rfi_entry():
    idx = build_index(load_preflop_packs())
    entry = lookup(idx, make_rfi_spot(position=Position.CO))
    assert entry is not None
    assert entry.node_context == NodeContext.RFI
    assert entry.position == Position.CO
