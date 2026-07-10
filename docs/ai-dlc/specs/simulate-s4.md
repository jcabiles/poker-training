# Delta spec — Simulate S4: persona postflop engine + live-texture calibration

> Slice S4 of `docs/ai-dlc/roadmap/simulate-table.md` (Track B, W3 — after S2+S3). Contract
> map: `docs/ai-dlc/contracts/simulate-s4.md`. Gate-1 decisions 2026-07-10: **lever block**
> (not node trees) · **budget-capped unmarked tests** · analytic strength ladder (no MC in
> the hot loop) · new module `personas_postflop.py` · `persona.schema.json` stays decorative.

**Goal (one line):** every persona can play flop/turn/river — a shared engine maps a 7-rung
analytic strength ladder × per-persona levers → mixed action frequencies + sampled sizings,
closed-loop-tested against PRD §8 postflop bands and a 9-max live-table-texture test.

## Frozen interface

```python
# domain/content/models.py — PersonaPack gains ONE optional field (None-safe: existing
# inline constructions and the preflop path stay byte-identical):
class PersonaPostflop(BaseModel):
    aggression: float            # > 0; scales bet/raise merit (1.0 = neutral)
    stickiness: float            # > 0; scales call merit / resistance to folding
    bluff_freq: float            # 0..1; baseline bet/raise rate with air & busted draws
    sizing: dict[str, float]     # pot-fraction str -> weight, e.g. {"0.33": .5, "0.75": .4, "1.25": .1}
                                 # weights sum to ~1; keys parseable as float pot fractions
    spr_commit: float            # SPR at/below which strong+ hands jam/commit
    multiway_bluff_damp: float   # 0..1; bluff_freq multiplier per opponent beyond one

class PersonaPack(...):          # existing fields untouched
    postflop: PersonaPostflop | None = None   # required in all 6 shipped packs

# domain/personas_postflop.py (new module; purity-allowlist entry REQUIRED)
class StrengthBucket(StrEnum):   # the 7-rung ladder — DISJOINT by construction
    MONSTER = "monster"          # any set/straight/flush/boat/quads, regardless of board
                                 # texture (coarse on paired/wet boards — accepted heuristic)
    TWO_PAIR_PLUS = "two_pair_plus"   # exactly two pair (both hole cards playing or
                                 # pocket pair + board pair combos below set strength)
    OVERPAIR_TPTK = "overpair_tptk"   # pocket pair above ALL board cards, or top pair
                                 # with top kicker
    TOP_PAIR = "top_pair"        # top pair, lesser kicker
    MIDDLE_PAIR = "middle_pair"  # any other pair: middle/bottom pair, pocket pair below
                                 # the board's top card
    ACE_HIGH = "ace_high"        # ace- or king-high, no pair
    AIR = "air"
# Disjointness rule (refuter-fixed): sets are ALWAYS monster, never two_pair_plus;
# straights on paired boards stay monster; a pocket pair below the top board card is
# always middle_pair (never overpair_tptk/top_pair).

class DrawCategory(StrEnum):
    NONE = "none"
    WEAK = "weak"                # gutshot / backdoor-flush+overcard class
    STRONG = "strong"            # flush draw / OESD / combo

def strength_bucket(hole: tuple[Card, Card], board: list[Card]) -> tuple[StrengthBucket, DrawCategory]
# PUBLIC from day one. Analytic only: best7/_eval5 rank tuples + rank/suit counting —
# NO Monte-Carlo, NO equity_vs_range. On the RIVER, DrawCategory is always NONE
# (no cards to come — busted draws are AIR/ACE_HIGH by made strength).

def sample_postflop_decision(
    pack: PersonaPack,
    hole: tuple[Card, Card],
    board: list[Card],           # revealed board (3/4/5 cards)
    legal: list[LegalAction],    # the engine's live bracket for this seat
    pot_bb: float,
    stack_bb: float,             # acting seat's stack behind
    opponents: int,              # live (IN or ALLIN) opponents remaining
    rng: random.Random,          # the HAND's injected rng — never a fresh Random
    noise: float = 1.0,          # per-session multiplier (S9 supplies; 1.0 = none)
    current_bet_to: float = 0.0, # the street's current bet-TO amount (HandState.
                                 # current_bet_bb) — combined-refuter amendment: the
                                 # to_call approximation deviates from the pinned raise
                                 # formula by the seat's street investment in multi-raise
                                 # sequences; callers pass the true value (0.0 = unopened)
) -> Decision
# Returns an engine-ready Decision: action ∈ legal shapes; BET/RAISE always carry
# absolute size_bb (raise-TO) sampled from pack.postflop.sizing then CLAMPED into the
# legal [min_bb, max_bb] bracket (jam collapse min==max handled). Frequencies are
# ALWAYS mixed (rng.choices over a frequency vector), never argmax.
```

## Behavior rules (frozen semantics)

1. **Frequency mapping:** base merit vector per (StrengthBucket, DrawCategory, facing
   state derived from `legal` shapes: unopened / facing-chips / matched-with-option) —
   shared table in code (game mechanics), shaped multiplicatively by levers:
   `aggression` scales bet/raise mass · `stickiness` scales call mass · `bluff_freq` sets
   AIR/busted bet-raise mass (dampened `× multiway_bluff_damp ** (opponents-1)`) ·
   `noise` multiplies aggression and bluff_freq only. **Normalize step (refuter-pinned):**
   clamp each merit component to ≥ 0, divide by the sum; components > 1 pre-normalize are
   fine; if the sum is 0, fall back to CHECK when legal else FOLD. → `rng.choices`.
   Monotonicity contract (tested): raising `aggression` never lowers bet+raise frequency;
   raising `stickiness` never lowers call frequency.
2. **SPR commit:** when `stack_bb / pot_bb <= spr_commit` and bucket ≥ OVERPAIR_TPTK (or
   STRONG draw), the vector shifts to call/jam (no fold mass) — persona-tuned via the
   lever value, mechanics shared.
3. **Sizing (exact formulas — refuter-fixed):** sample a pot-fraction `f` from `sizing`
   weights (rng). Unopened BET: `size_bb = f × pot_bb`. RAISE facing chips:
   `raise_to = current_bet_to + f × (pot_bb + to_call_incremental)` (fraction of the pot
   AFTER the call — textbook pot-raise; `current_bet_to` = the bet being raised, TO amount;
   `to_call_incremental` = CALL entry's min_bb). Round 2dp, clamp into `[min_bb, max_bb]`;
   when the bracket is a jam (min==max) the clamp resolves to it. **No deterministic
   strength→size mapping** — the sizing draw is independent of bucket (pass/fail
   requirement; test samples sizes across strength).
4. **Levers are content, mechanics are code:** the merit table + mapping algorithm live in
   `personas_postflop.py`; every number that differentiates personas lives in the packs.
5. **Preflop path untouched:** `sample_preflop_action`, `_WIRE`, pack preflop nodes,
   S3 band test — all byte-identical.
6. **Purity:** `personas_postflop.py` imports only stdlib/pydantic/domain; append
   `'app.domain.personas_postflop'` to the `test_domain_purity.py` allowlist (module-exact).
7. **Two SPRs:** the commit lever computes live `stack_bb / pot_bb` — never import or
   touch `srs.spr_bucket` / `spot_signature` (frozen SRS contract, contract C11).
8. **No persona-aware grading:** graders/providers never read persona data (invariant).

## Content

All 6 packs (`content/personas/*.json`) gain a `postflop` block, doc-grounded per persona
(PRD §8): fish = low aggression/high stickiness; station = stickiness extreme, near-zero
bluff; nit = low bluff, high commit threshold discipline; TAG = balanced-aggressive; LAG =
high aggression + bluff; maniac = extreme aggression/bluff, low multiway damp.
`persona.schema.json` NOT regenerated (decorative — decision recorded here).

## Closed-loop tests (budget-capped, unmarked) — `backend/tests/test_personas_postflop.py`

Harness: full-hand playouts via the S2 engine — each seat's persona sampled via
`sample_preflop_action` + `sample_postflop_decision`; seeded `random.Random(20260710)`.
**Budget (refuter-measured, single number):** the ENTIRE new test file adds ≤ 12s to the
suite. Measured engine throughput at HEAD ≈ 430 hands/s (sticky-policy floor; 91% of
`apply()` cost is pydantic deep-copy — a known perf ceiling, optimization deferred to a
Later roadmap note, NOT this slice). Derived allocation: **N = 600 hands/persona × 6 +
1,500 texture hands ≈ 5,100 hands ≈ 11.8s**. Maker re-measures with the real sampler and
scales N DOWN if needed (never up past budget); final N + ~3σ binomial tolerance
derivation documented in test comments.

Frozen stat formulas (computed from `HandState.action_history` + `Settlement`):
- **AF** = (BET + RAISE count) / CALL count, postflop streets only, per persona seat.
  **Occurrence floor (refuter-fixed):** AF is asserted ONLY for personas whose measured
  postflop CALL count ≥ 30 at the chosen N (expected: fish, station, tag, lag, maniac);
  for low-volume personas (nit) assert fold-to-cbet + WTSD only — never divide by a
  count < 30, never ZeroDivisionError.
- **Fold-to-cbet** = folds / opportunities (opportunity = seat faces the FIRST flop BET
  and is not the bettor); asserted only when opportunities ≥ 30.
- **WTSD** = seat in `Settlement.showdown_seats` / hands where the seat saw the flop.
Bands per persona: PRD §8 table (`docs/ai-dlc/prd/simulate-table.md:172-184`), widened
per the N-derivation above.

**Table-texture test:** 9-max lineup = the 8 product villains (2× passive_fish, 2× tag,
calling_station, nit, lag, maniac) + 1 extra passive_fish in seat 0; over 1,500 hands:
avg players-to-flop within [2.8, 4.5] · % hands with ≥1 preflop limper > 50% ·
**3-bet-pot rate < 12%** with the formula pinned: numerator = hands where any seat's
sampled preflop action ∈ {3bet, 4bet, 5bet_shove}; denominator = all hands.
(Refuter-measured lower bound with the real S3 packs + this lineup: 10.1% — the
roadmap's "low single-digit %" population anchor is unreachable with a deliberately
aggressive 3-of-9 lineup; per-persona fidelity wins. Roadmap note at close-out.)

**Unit tests:** strength_bucket fixtures per rung + draw class incl. river-no-draws;
monotonicity (aggression/stickiness); sizing samples span ≥2 fractions for one bucket at
fixed seed (non-deterministic mapping proof); clamp + jam edge; multiway dampener effect;
same seed ⇒ same decision.

## Files

`backend/app/domain/content/models.py` (PersonaPostflop + field) ·
`backend/app/domain/personas_postflop.py` (new) · `content/personas/*.json` (6 packs) ·
`backend/tests/test_personas_postflop.py` (new) · `backend/tests/test_domain_purity.py`
(one string). NOTHING else — no engine changes, no grader/provider changes, no API/FE/DB.

## Out of scope (S4 no-gos)

No solver lookups · no persona learning/tilt · no wiring into `api/v1/simulate.py` (S9) ·
no grader/provider/SRS changes · no engine changes (if the engine lacks something, report
to lead — don't patch) · no new dependencies · no slow markers.

## Verify-by

Full `pytest -q` green with the new suite's measured runtime reported (whole suite stays
under ~25s); S3 preflop band test byte-identical and green; all 6 packs load with postflop
blocks; per-persona AF/fold-to-cbet/WTSD inside documented bands; table-texture assertions
pass; same-seed determinism; ruff clean; `./scripts/verify.sh` → BACKEND VERIFY OK.
