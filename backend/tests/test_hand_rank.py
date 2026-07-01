"""HAND_RANK must be deterministic regardless of PYTHONHASHSEED.

`all_hands()` (app/domain/content/notation.py) returns a `set[str]`, whose
iteration order is randomized per-process by PYTHONHASHSEED. `_strength()`
has 24 genuine ties (e.g. 88/KQo, 86s/T6o both share a strength score), so
without a deterministic tie-break, `sorted(all_hands(), key=_strength)`
(a stable sort) would resolve those ties by set-iteration order and the
resulting HAND_RANK values would swap between runs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.domain.hand_rank import HAND_RANK, _strength

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Known tied pairs (same _strength(), verified by inspection of all 169 hands).
TIED_PAIRS = [
    ("88", "KQo"),  # strength 0.73
    ("86s", "T6o"),  # strength 0.512
]


def test_known_pairs_are_actually_tied_in_strength() -> None:
    """Sanity check that the fixture pairs still exercise the tie-break path."""
    for low, high in TIED_PAIRS:
        assert _strength(low) == _strength(high)


def test_tied_pairs_break_ties_by_hand_string() -> None:
    """Tie-break must be the hand string itself: lower string sorts first."""
    for low, high in TIED_PAIRS:
        assert low < high  # confirms the fixture's naming matches the assertion
        assert HAND_RANK[low] < HAND_RANK[high]


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
    """The real regression test: two fresh interpreters, two hash seeds,
    identical HAND_RANK table (order and values) -- including the 24 tied
    hands.
    """
    ranks_seed1 = _hand_rank_snapshot("1")
    ranks_seed42 = _hand_rank_snapshot("42")
    assert ranks_seed1 == ranks_seed42
    # And specifically the pairs called out in the ticket:
    for low, high in TIED_PAIRS:
        assert ranks_seed1[low] < ranks_seed1[high]
        assert ranks_seed42[low] < ranks_seed42[high]
