"""Range-notation parser.

Expands compact poker range strings into the 169 starting-hand-class space
(e.g. "AA", "AKs", "AKo"). Solver-grade 1326-combo expansion can come later;
169 classes are enough for preflop grading.

Supported tokens (comma-separated):
  *              all 169 hands
  77             a single pair
  77+            that pair and every higher pair (77..AA)
  QQ-99          an inclusive pair range
  AKs / AKo      a single suited / offsuit hand
  AK             both AKs and AKo
  ATs+ / ATo+    fix the high card, kicker up to one below it (ATs,AJs,AQs,AKs)
"""

from __future__ import annotations

RANKS = "23456789TJQKA"
_IDX = {r: i for i, r in enumerate(RANKS)}


def all_hands() -> set[str]:
    hands: set[str] = set()
    for i, hi in enumerate(RANKS):
        for j, lo in enumerate(RANKS):
            if i == j:
                hands.add(hi + lo)  # pair
            elif i > j:
                hands.add(hi + lo + "s")
                hands.add(hi + lo + "o")
    return hands


def _expand_pair(rank: str, plus: bool) -> set[str]:
    idx = _IDX[rank]
    if plus:
        return {RANKS[k] + RANKS[k] for k in range(idx, len(RANKS))}
    return {rank + rank}


def _expand_two(r1: str, r2: str, suit: str | None, plus: bool) -> set[str]:
    if _IDX[r1] < _IDX[r2]:
        r1, r2 = r2, r1
    suits = [suit] if suit in ("s", "o") else ["s", "o"]
    if plus:
        kickers = [RANKS[k] for k in range(_IDX[r2], _IDX[r1])]
    else:
        kickers = [r2]
    return {r1 + k + s for k in kickers for s in suits}


def _expand_range(a: str, b: str) -> set[str]:
    if len(a) == 2 and a[0] == a[1] and len(b) == 2 and b[0] == b[1]:
        lo, hi = sorted((_IDX[a[0]], _IDX[b[0]]))
        return {RANKS[k] + RANKS[k] for k in range(lo, hi + 1)}
    raise ValueError(f"unsupported range token: {a}-{b} (only pair ranges supported)")


def _expand_token(tok: str) -> set[str]:
    tok = tok.strip()
    if not tok:
        return set()
    if tok == "*":
        return all_hands()
    plus = tok.endswith("+")
    core = tok[:-1] if plus else tok
    if "-" in core and not plus:
        a, b = core.split("-", 1)
        return _expand_range(a.strip(), b.strip())
    if len(core) == 2 and core[0] == core[1]:
        return _expand_pair(core[0], plus)
    if len(core) in (2, 3):
        r1, r2 = core[0], core[1]
        if r1 not in _IDX or r2 not in _IDX:
            raise ValueError(f"unparseable range token: {tok!r}")
        suit = core[2] if len(core) == 3 else None
        if suit is not None and suit not in ("s", "o"):
            raise ValueError(f"bad suit in token: {tok!r}")
        return _expand_two(r1, r2, suit, plus)
    raise ValueError(f"unparseable range token: {tok!r}")


def parse_range(spec: str) -> set[str]:
    out: set[str] = set()
    for tok in spec.split(","):
        out |= _expand_token(tok)
    return out


def hole_cards_to_class(c1: str, c2: str) -> str:
    """('Ah','Ks') -> 'AKo'; ('Ah','Kh') -> 'AKs'; ('7c','7d') -> '77'."""
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    if r1 == r2:
        return r1 + r2
    if _IDX[r1] < _IDX[r2]:
        r1, r2, s1, s2 = r2, r1, s2, s1
    return r1 + r2 + ("s" if s1 == s2 else "o")
