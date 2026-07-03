"""HAND_RANK — each of the 169 starting hands mapped to a strength percentile
in [0,1] (AA=1.0, weakest=0.0), ordered by computed equity vs a random hand.

CW-3b (doc-08 §1.3-1.4): the old closed-form `_strength()` proxy
systematically underrated pocket pairs (66 ranked below QJs despite a clear
equity gap) and carried 24 exact ties (e.g. AJo == QJs at 0.722) that made
equity-correct pair placement provably unsatisfiable without touching
non-pair values. Ranks are now anchored to `_EQUITY_VS_RANDOM`: preflop
equity vs a uniform random hand, computed with this repo's own
`app.domain.equity.equity_vs_range` (one representative combo per class —
exact by suit symmetry vs a uniform range — seed 0, 100k MC iterations;
66/AJo/KJs/87s/J6o refined at 1M iterations because their gaps to doc-08's
cited neighbors sit within 100k-iteration MC noise). Regeneration recipe
lives in the table's provenance above; doc-08 §1.5's caveat still applies —
raw equity is a strength ordering, not playability — and Phase 3's solver
provider can replace this without touching the grading interface.

Results still scale grading penalties (folding strong hands hurts more;
raising weak hands hurts more).
"""

from __future__ import annotations

from app.domain.content.notation import all_hands

# fmt: off
_EQUITY_VS_RANDOM: dict[str, float] = {
    "AA": 0.85233, "KK": 0.824165, "QQ": 0.800445, "JJ": 0.774955,
    "TT": 0.75085, "99": 0.72168, "88": 0.692825, "AKs": 0.671645,
    "77": 0.66257, "AQs": 0.662265, "AJs": 0.65561, "AKo": 0.65327,
    "ATs": 0.646015, "AQo": 0.643995, "AJo": 0.636012, "KQs": 0.63382,
    "66": 0.6324885, "A9s": 0.629335, "ATo": 0.626695, "KJs": 0.6264265,
    "A8s": 0.61993, "KTs": 0.617255, "KQo": 0.61395, "A7s": 0.610115,
    "A9o": 0.60797, "KJo": 0.605985, "55": 0.60515, "QJs": 0.602775,
    "K9s": 0.601165, "A8o": 0.599185, "A6s": 0.599005, "A5s": 0.598005,
    "KTo": 0.59655, "QTs": 0.59255, "A4s": 0.58955, "A7o": 0.58903,
    "K8s": 0.583715, "A3s": 0.5824, "QJo": 0.58081, "K9o": 0.57929,
    "A6o": 0.576785, "A5o": 0.57639, "Q9s": 0.57624, "K7s": 0.57607,
    "JTs": 0.57444, "A2s": 0.57301, "QTo": 0.570875, "44": 0.5694,
    "K6s": 0.566965, "A4o": 0.566725, "K8o": 0.561045, "Q8s": 0.558775,
    "J9s": 0.558745, "A3o": 0.558215, "K5s": 0.55718, "Q9o": 0.55316,
    "K7o": 0.55299, "JTo": 0.552985, "A2o": 0.548755, "K4s": 0.54864,
    "K6o": 0.54335, "Q7s": 0.54195, "T9s": 0.54168, "J8s": 0.540215,
    "K3s": 0.539845, "33": 0.537855, "Q6s": 0.535235, "J9o": 0.534925,
    "Q8o": 0.53426, "K5o": 0.53346, "K2s": 0.53109, "Q5s": 0.526615,
    "T8s": 0.524395, "K4o": 0.523755, "J7s": 0.523535, "Q4s": 0.51834,
    "Q7o": 0.517375, "T9o": 0.51642, "J8o": 0.515015, "K3o": 0.51361,
    "Q3s": 0.509875, "Q6o": 0.50955, "98s": 0.508555, "J6s": 0.507045,
    "T7s": 0.50566, "K2o": 0.50447, "22": 0.50274, "Q2s": 0.50186,
    "J5s": 0.501185, "Q5o": 0.49985, "J7o": 0.49785, "T8o": 0.49779,
    "J4s": 0.49178, "Q4o": 0.49129, "97s": 0.490695, "T6s": 0.490215,
    "J3s": 0.482495, "Q3o": 0.482165, "98o": 0.481365, "87s": 0.4790555,
    "T7o": 0.47866, "J6o": 0.4781255, "96s": 0.47535, "T5s": 0.47482,
    "J2s": 0.473545, "Q2o": 0.47309, "J5o": 0.47221, "T4s": 0.467485,
    "86s": 0.46382, "97o": 0.46301, "J4o": 0.462445, "T6o": 0.46178,
    "95s": 0.45932, "T3s": 0.4575, "76s": 0.453935, "J3o": 0.45309,
    "87o": 0.45042, "T2s": 0.44894, "85s": 0.448135, "96o": 0.446555,
    "T5o": 0.44511, "J2o": 0.444125, "94s": 0.442025, "75s": 0.438225,
    "T4o": 0.436985, "93s": 0.434025, "86o": 0.43338, "65s": 0.43231,
    "95o": 0.429035, "84s": 0.42799, "T3o": 0.427325, "92s": 0.42641,
    "76o": 0.422955, "74s": 0.417815, "T2o": 0.417775, "85o": 0.41677,
    "54s": 0.41486, "64s": 0.412055, "94o": 0.410095, "83s": 0.407515,
    "75o": 0.406855, "82s": 0.402565, "93o": 0.402025, "65o": 0.40009,
    "73s": 0.398725, "53s": 0.39754, "84o": 0.396405, "63s": 0.39537,
    "92o": 0.394015, "43s": 0.38633, "74o": 0.385855, "54o": 0.38272,
    "72s": 0.38139, "64o": 0.3793, "52s": 0.37878, "62s": 0.37622,
    "83o": 0.375615, "82o": 0.370115, "42s": 0.36917, "73o": 0.366025,
    "53o": 0.36455, "63o": 0.36139, "32s": 0.358705, "43o": 0.35231,
    "72o": 0.34724, "52o": 0.343585, "62o": 0.34129, "42o": 0.333165,
    "32o": 0.321795,}
# fmt: on

# `all_hands()` returns a `set[str]`; its iteration order depends on
# `PYTHONHASHSEED` (string hashing is seed-randomized). The equity values are
# all distinct today, but Python's `sorted()` is stable, so an exact MC tie in
# a future regeneration would otherwise resolve by set-iteration order and
# swap between process runs. Tie-break on the hand string itself (stable,
# seed-independent) so HAND_RANK is fully deterministic.
_SORTED = sorted(all_hands(), key=lambda h: (_EQUITY_VS_RANDOM[h], h))
HAND_RANK: dict[str, float] = {h: i / (len(_SORTED) - 1) for i, h in enumerate(_SORTED)}


def hand_rank(hand: str) -> float:
    return HAND_RANK.get(hand, 0.5)
