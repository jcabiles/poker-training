"""Pure-Python equity engine (Phase 2a).

A dependency-free 7-card best-5 evaluator plus a Monte-Carlo
`equity_vs_range`. Originally used ONLY by the equity-estimation drill
(single hero hand vs a range); N2 (accuracy-debt paydown, doc-08 §3.2) also
wires `equity_vs_range` into `postflop.py`'s interim fold-equity EV for the
c-bet grader — bounded MC, its OWN seeded RNG, still never shared with spot
construction. Range-vs-range equity remains out of scope (perf); range
advantage in the c-bet grader is still a positional+texture rule.

Dead-card order (the classic bug to avoid): dead = hero ∪ board; filter the
villain combos to those disjoint from dead BEFORE the loop; each iteration
draws the runout from deck − dead − villain_combo. Win = +1, tie = +0.5.
"""

from __future__ import annotations

import itertools
import random

RANKS = "23456789TJQKA"
SUITS = "cdhs"
_RIDX = {r: i for i, r in enumerate(RANKS)}
_DECK = [r + s for r in RANKS for s in SUITS]

# Best-5-of-7 index combinations (21), precomputed once.
_C75 = list(itertools.combinations(range(7), 5))


def _eval5(rs: list[int], ss: list[str]) -> tuple:
    """Comparable rank tuple for a 5-card hand. Higher tuple = stronger."""
    is_flush = ss[0] == ss[1] == ss[2] == ss[3] == ss[4]
    srt = sorted(rs, reverse=True)

    cnt: dict[int, int] = {}
    for r in rs:
        cnt[r] = cnt.get(r, 0) + 1

    uniq = sorted(cnt, reverse=True)
    straight_high = None
    if len(uniq) == 5:
        if uniq[0] - uniq[4] == 4:
            straight_high = uniq[0]
        elif uniq == [12, 3, 2, 1, 0]:  # A-2-3-4-5 wheel; 5-high straight
            straight_high = 3

    # rank groups ordered by (count, rank) desc — e.g. trips first, then kickers
    items = sorted(cnt.items(), key=lambda x: (x[1], x[0]), reverse=True)
    pat = [c for _, c in items]
    ranks = [r for r, _ in items]

    if is_flush and straight_high is not None:
        return (8, straight_high)
    if pat[0] == 4:
        return (7, ranks[0], ranks[1])
    if pat[0] == 3 and pat[1] == 2:
        return (6, ranks[0], ranks[1])
    if is_flush:
        return (5, srt[0], srt[1], srt[2], srt[3], srt[4])
    if straight_high is not None:
        return (4, straight_high)
    if pat[0] == 3:
        return (3, ranks[0], ranks[1], ranks[2])
    if pat[0] == 2 and pat[1] == 2:
        return (2, ranks[0], ranks[1], ranks[2])
    if pat[0] == 2:
        return (1, ranks[0], ranks[1], ranks[2], ranks[3])
    return (0, srt[0], srt[1], srt[2], srt[3], srt[4])


def _best7(cards: list[str]) -> tuple:
    rs = [_RIDX[c[0]] for c in cards]
    ss = [c[1] for c in cards]
    best = None
    for a, b, c, d, e in _C75:
        v = _eval5([rs[a], rs[b], rs[c], rs[d], rs[e]], [ss[a], ss[b], ss[c], ss[d], ss[e]])
        if best is None or v > best:
            best = v
    return best


def class_to_combos(cls: str) -> list[tuple[str, str]]:
    """'AA' -> 6 combos, 'AKs' -> 4, 'AKo' -> 12."""
    if len(cls) == 2:  # pair
        cards = [cls[0] + s for s in SUITS]
        return list(itertools.combinations(cards, 2))
    hi, lo, kind = cls[0], cls[1], cls[2]
    if kind == "s":
        return [(hi + s, lo + s) for s in SUITS]
    return [(hi + s1, lo + s2) for s1 in SUITS for s2 in SUITS if s1 != s2]


def combos_for_range(spec: str, dead: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    """Concrete 2-card combos for a range spec, excluding any touching `dead`."""
    from app.domain.content.notation import parse_range

    out: list[tuple[str, str]] = []
    for cls in parse_range(spec):
        for combo in class_to_combos(cls):
            if not (set(combo) & dead):
                out.append(combo)
    return out


def equity_vs_range(
    hero: tuple[str, str],
    board: list[str],
    villain_combos: list[tuple[str, str]],
    iters: int = 2000,
    rng: random.Random | None = None,
) -> float:
    """Monte-Carlo equity of `hero` vs a villain range. Deterministic per seed.

    `board` length ∈ {0,3,4,5}. Returns a win-share in [0,1] (ties = 0.5).
    """
    rng = rng or random.Random(0)
    dead = set(hero) | set(board)
    combos = [c for c in villain_combos if not (set(c) & dead)]
    if not combos:
        return 0.0
    deck_base = [c for c in _DECK if c not in dead]
    need = 5 - len(board)

    total = 0.0
    n = 0
    for _ in range(iters):
        vc = combos[rng.randrange(len(combos))]
        v0, v1 = vc
        avail = [c for c in deck_base if c != v0 and c != v1]
        runout = rng.sample(avail, need) if need else []
        full_board = board + runout
        hr = _best7([hero[0], hero[1], *full_board])
        vr = _best7([v0, v1, *full_board])
        if hr > vr:
            total += 1.0
        elif hr == vr:
            total += 0.5
        n += 1
    return total / n if n else 0.0


def fold_equity_ev(fold_pct: float, equity_if_called: float, pot_bb: float, bet_bb: float) -> float:
    """Standard textbook one-street fold-equity / semi-bluff EV (doc-08 §3.2):

        EV(bet) = Fold% x Pot
                + (1 - Fold%) x (Equity_vs_continuing_range x (Pot + 2xBet) - Bet)

    Collapses the rest of the hand into two branches -- villain folds (hero
    wins the pot as-is) or villain calls and it runs out with a static
    continuing range -- so it is NOT solver-exact, but it is a real,
    dimensionally-correct chip-EV formula (bb in, bb out), unlike a hand-tuned
    unitless merit score. `pot_bb` is the pot BEFORE `bet_bb` is added.
    """
    return fold_pct * pot_bb + (1 - fold_pct) * (
        equity_if_called * (pot_bb + 2 * bet_bb) - bet_bb
    )
