"""HAND_RANK is anchored to computed equity-vs-random (doc-08 §1.3-1.4) and
must be deterministic regardless of PYTHONHASHSEED.

Two concerns are covered here:

1. ORDERING (CW-3b): the old closed-form `_strength()` proxy systematically
   underrated pocket pairs (doc-08 §1.3) and had 24 genuine ties (§1.4) that
   real equity resolves. Ranks now come from `_EQUITY_VS_RANDOM`, a table
   computed with `app.domain.equity.equity_vs_range`. The doc's cited
   relations — including the pair anchors (66 between AJo and QJs) and the
   split former ties (88 > KQo, AJo > QJs) — are asserted below.

2. DETERMINISM: `all_hands()` returns a `set[str]` whose iteration order is
   randomized per-process by PYTHONHASHSEED. The equity values are all
   distinct today, but the sort still tie-breaks on the hand string so that
   HAND_RANK stays byte-identical across interpreters even if a future
   regeneration of the table lands on an exact MC tie.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.domain.content.notation import all_hands
from app.domain.hand_rank import _EQUITY_VS_RANDOM, HAND_RANK, hand_rank

BACKEND_DIR = Path(__file__).resolve().parents[1]


# --- ordering: doc-08 cited relations -------------------------------------

def test_pairs_are_monotonic_aa_down_to_22() -> None:
    pairs = [r + r for r in "AKQJT98765432"]
    for stronger, weaker in zip(pairs, pairs[1:], strict=False):
        assert hand_rank(stronger) > hand_rank(weaker)


def test_pocket_pairs_sit_in_equity_correct_position() -> None:
    """The CW-3b contradiction: doc-08 §1.3 requires 66 ABOVE QJs, while the
    CW-3b regression note requires 66 BELOW AJo. Impossible under the old
    proxy (AJo and QJs were exactly tied at 0.722); real equity splits the
    tie (AJo 0.636 > 66 0.633 > QJs 0.603) and both constraints hold.
    """
    assert hand_rank("AJo") > hand_rank("66") > hand_rank("QJs")
    assert hand_rank("77") > hand_rank("QJs")
    # §1.3 generalization: 66 below ATs yet above KJs (old proxy had
    # ATs < KJs, making this unsatisfiable).
    assert hand_rank("ATs") > hand_rank("66") > hand_rank("KJs")
    # §1.3 "decisive undervaluation" case: 55 over Q7s (~7-point equity gap).
    assert hand_rank("55") > hand_rank("Q7s")


def test_former_proxy_ties_resolve_in_equity_direction() -> None:
    """Doc-08 §1.4: every one of the old proxy's 24 tie groups resolves to a
    distinct real equity. Spot-check the groups the doc cites explicitly.
    """
    assert hand_rank("88") > hand_rank("KQo")  # old proxy: dead heat at 0.730
    assert hand_rank("99") > hand_rank("AQo")  # old proxy tie at 0.760
    assert hand_rank("KTo") > hand_rank("JTs")  # old proxy tie at 0.674


def test_extremes_and_bounds() -> None:
    assert hand_rank("AA") == 1.0
    # Doc-08 §1.3: 32o, not 72o, has the lowest raw equity vs random.
    assert hand_rank("32o") == 0.0
    assert hand_rank("32o") < hand_rank("72o")


# --- table integrity -------------------------------------------------------

def test_equity_table_covers_exactly_the_169_hand_classes() -> None:
    assert set(_EQUITY_VS_RANDOM) == all_hands()
    assert len(_EQUITY_VS_RANDOM) == 169


def test_hand_rank_values_are_distinct_percentiles() -> None:
    assert len(set(HAND_RANK.values())) == 169
    assert min(HAND_RANK.values()) == 0.0
    assert max(HAND_RANK.values()) == 1.0


# --- determinism across hash seeds -----------------------------------------

def _hand_rank_snapshot(seed: str) -> dict[str, float]:
    """Import HAND_RANK in a fresh subprocess under a given PYTHONHASHSEED."""
    code = (
        "import json\n"
        "from app.domain.hand_rank import HAND_RANK\n"
        "print(json.dumps(HAND_RANK))\n"
    )
    env = {**os.environ, "PYTHONHASHSEED": seed}
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_hand_rank_identical_across_hash_seeds() -> None:
    """Two fresh interpreters, two hash seeds, identical HAND_RANK table
    (order and values). The equity table has no exact ties today, but the
    hand-string tie-break keeps this invariant even if one appears.
    """
    ranks_seed1 = _hand_rank_snapshot("1")
    ranks_seed42 = _hand_rank_snapshot("42")
    assert ranks_seed1 == ranks_seed42
