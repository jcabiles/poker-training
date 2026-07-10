# Delta spec — Simulate S6: turn graders (barrel + facing turn bets)

> Slice S6 of `docs/ai-dlc/roadmap/simulate-table.md` (Track C, W2, after S5). Contract map:
> `docs/ai-dlc/contracts/simulate-s6.md` (supplements `simulate-s5.md`). Gate-1 decisions
> 2026-07-10: NOT_FOUND gate skips BOTH writes · SRS turn-texture dim appended NOW ·
> thresholds as code constants + prose packs (flop precedent) · no turn drill modes.

**Goal (one line):** heads-up turn grading — 2nd-barrel and facing-turn-bet — behind the
existing provider seam, with `range_advantage()` actually consuming `node_context`
(flop output byte-identical), the NOT_FOUND persistence gate closed, SRS turn-texture
dimension appended per the S5 append rule, and SRS review able to rebuild due turn spots.

## Frozen interface

```python
# domain/spot.py — NodeContext gains EXACTLY two members (StrEnum values persist in SRS):
TURN_BARREL = "turn_barrel"       # flop aggressor deciding whether to bet the turn
VS_TURN_BET = "vs_turn_bet"       # facing a turn bet after calling flop

# domain/texture.py — new function (classify() untouched, stays flop-only):
def turn_card_class(board: list[Card]) -> str
# board len >= 4; classifies board[3] against board[:3] into EXACTLY one of:
# "pairing" | "flush" | "straight" | "over" | "blank"
# precedence in that order (pairing beats flush-completing beats straight-completing
# beats overcard-to-the-flop beats blank)

# domain/postflop.py — same signature, body now branches on node_context:
def range_advantage(node_context, hero_pos, villain_pos, texture) -> str
# CBET / VS_CHECK_RAISE (and any other flop ctx) → CURRENT arithmetic, bit-for-bit
# TURN_BARREL / VS_TURN_BET → turn-aware scoring; returns ONLY 'hero'|'villain'|'neutral'

# New graders (flop-grader anatomy, contract map §2):
def grade_turn_barrel(spot, hero_range, villain_range, decision) -> EvaluationResult
def grade_vs_turn_bet(spot, hero_range, villain_range, decision) -> EvaluationResult

# domain/providers/turn.py — new provider, duck-typed protocol:
class TurnHeuristicProvider:
    async def supports(spot) -> bool   # street==TURN AND node ∈ {TURN_BARREL, VS_TURN_BET}
                                       # AND len(board) >= 4  — NEVER accepts flop contexts
    async def optimal(spot) -> EvaluationResult
    async def evaluate(spot, action) -> EvaluationResult

# domain/srs.py — _postflop_signature gains ONE CONDITIONALLY-APPENDED field (after
# faced_bet_bucket): the element is appended ONLY when street in (TURN, RIVER) and
# len(board) >= 4; for flop spots the parts list stays 9 elements, byte-identical.
# ⚠️ Refuter-proven (2026-07-10): the signature is "|".join(parts) → sha256 (srs.py:134-135),
# so appending ANY element — even a constant "-" — changes flop hashes
# (6832a54693ba5f6c → eb5624bf01b7635a). Constant-append is WRONG; conditional append is
# the only design that keeps both pins green. No collision risk: street sits at tuple
# index 2, so turn/river can never alias flop. Rewrite the S5 append-rule docstring
# (srs.py:113-117) — it embeds the false "constant value preserves hashes" premise; the
# correct rule: new dims must be OMITTED (not constant-valued) for existing flop spots.
# Side effect (accepted): junk turn/river SRS rows persisted via the pre-gate live gap
# get orphaned — fine, the coverage gate retires that path.

# domain/scenarios.py — two new builders (rebuild + future S9 use):
def build_turn_barrel_spot(rng, *, pairing=..., eff_bb=...) -> Spot   # street=TURN, board len 4,
def build_vs_turn_bet_spot(rng, *, pairing=..., eff_bb=..., bet_frac=...) -> Spot
# action_history spans preflop+flop(+turn bet for vs_turn_bet) so faced_bet_bucket's
# street filter works; CALL min_bb incremental; pot/spr arithmetically consistent.
```

## Changes (exact)

1. **Graders** (`domain/postflop.py`, turn section): mirror flop anatomy — merit-vector →
   freq (round 3dp) → EV (round 2dp) → correctness ladder using the SAME band constants
   (`POST_ACCEPTABLE_MAX/MISTAKE_MAX/MIX`); **5-wide** `rationale_tags`
   `["turn_barrel"|"vs_turn_bet", adv, cat, wetness, turn_class]` — the 5th tag is
   backward-compatible (composer dispatch is `len(tags) >= 4` and flop nodes read only
   0–3) and lets turn phrasing name the turn card (roadmap demands non-tautological
   reasoning; a barrel verdict that never names the scare card fails that bar);
   `leak_category` set (see 6); never boolean. Barrel merits incorporate research
   §5.1–5.2 factors: `turn_card_class` (scare cards favor barreling for the aggressor),
   range advantage (via the rewritten `range_advantage`), hand category, position.
   Facing-bet merits: pot odds from `_faced_call_and_pot`, hand category, turn-card class.
   `wetness` tag comes from `classify(board[:3])` — legal, texture.py documents flop-slice
   use. Numeric thresholds = module constants; authored prose from packs (see 5).
2. **`range_advantage` rewrite:** dispatch on node_context; flop-context path is the
   current code moved verbatim (golden proof: 3 flop graders' outputs unchanged — existing
   grader tests + pinned hashes stay green untouched). Turn path adds turn-specific scoring;
   test asserts same (positions, texture) yields a DIFFERENT label for at least one
   flop-vs-turn context pair (roadmap pass/fail line).
3. **Provider wiring:** `providers/turn.py` (new) + `composite.py` `__init__(preflop,
   postflop, turn)` + `_by_street[Street.TURN] = turn` + `factory.py` constructs it
   (refuter-verified: `factory.py:33` is the ONLY construction site; no default param
   needed). NOT_FOUND trio (`test_provider.py:141-184`) assertions pass UNCHANGED — turn
   provider rejects flop contexts on turn boards by design. One comment-only amendment
   permitted: `test_postflop_provider_rejects_turn_street` goes through `get_provider()`,
   so post-S6 it exercises the TURN provider's rejection — update its comment/docstring
   (assertions untouched). Purity: refuter-resolved — `'app.domain.providers'` allowlist
   entry covers `turn.py` transitively (package `__init__` → factory → turn import);
   **no `test_domain_purity.py` change.**
4. **Coverage gate** (`api/v1/drill.py` `grade_drill`): wrap the `DrillAttempt` add/commit
   AND `record_attempt` call in `if result.coverage != Coverage.NOT_FOUND:`. Response bytes
   unchanged (no SRS fields in `EvaluationResult`). New tripwire test: POST a NOT_FOUND spot
   → 200 + zero new `DrillAttempt`/`SRSItemRow` rows.
5. **Content:** `content/personas` untouched; new `content/postflop/turn.json` pack
   (`id: "postflop-turn", version: 1`) — entries `{node_context, position, facing,
   actions: [], rationale}` for both turn contexts, keyed like `cbet.json`;
   `_postflop_rationale_index()` globs `content/postflop/*.json` (refuter-verified,
   `postflop.py:48`) — turn.json auto-loads. Schema: **hand-edit**
   `$defs/NodeContext.enum` at `content/schema/contentpack.schema.json:123` to append the
   two values (no generator script exists — refuter-verified; do not hunt for one).
6. **Leaks:** `leaks.py` += `TURN_BARREL = 203`, `VS_TURN_BET = 204`; `TAXONOMY_VERSION = 4`.
   Map in BOTH places: grader-local `leak =` lines AND `grading.py::leak_category_for()`
   branches (contract §7 — miss one and leak_focus breaks). No Home.tsx tiles, no concept
   cards (turn drill modes are a no-go; tiles are mode entry points).
7. **Composer:** `feedback.py` `_NODE` += entries for `"turn_barrel"` / `"vs_turn_bet"`
   (turn-appropriate phrasing); `_ADV` unchanged (labels canonical). Without this, turn tags
   fall through to preflop chart-language (contract §2).
8. **SRS turn dimension** (`domain/srs.py`): CONDITIONALLY append `turn_class` to
   `_postflop_signature` per the frozen interface above (element omitted for flop spots —
   parts list unchanged); REWRITE the S5 append-rule docstring (it states the false
   constant-value premise). Pinned-hash tests must pass with UNCHANGED literals
   (`6832a54693ba5f6c` / `0cdf437e044b0bc5`). New tests: two turn spots differing only in
   turn card class hash differently; a flop spot's hash byte-unchanged; turn/river pairwise
   fixtures (`test_signature.py:218-235`, no pinned turn literals) stay green.
9. **SRS rebuild** (`api/v1/drill.py` + `services/review.py` + DB): `_POSTFLOP_CTX` += the
   two turn members; two new `_rebuild_postflop` branches using the new builders.
   **Refuter finding folded in:** without persistence the turn dim is write-only — two due
   turn rows differing only by turn class would rebuild indistinguishable targets. So:
   additive nullable `turn_class: str | None` column on `SRSItemRow` + **Alembic
   migration** (additive only, per repo invariant); `_postflop_archetype`
   (`review.py:25-31`) persists `turn_card_class(board)` for turn/river spots, None for
   flop; turn rebuild branches match
   `(row.texture_class, row.spr_bucket, row.faced_bet_bucket, row.turn_class)` — candidate
   `_key` compares flop-3 texture PLUS the candidate's turn class. Rebuild test must be
   non-tautological: assert the rebuilt spot's node_context, street, flop texture AND
   turn_card_class match the row (not just the `srs_signature` override at `drill.py:147`).
10. **Flop rows unaffected:** `turn_class` column stays None for all existing/new flop
    rows; flop rebuild branches unchanged.

## Files

`backend/app/domain/spot.py` (enum) · `domain/texture.py` (new fn) · `domain/postflop.py`
(rewrite + 2 graders) · `domain/providers/turn.py` (new) · `domain/providers/composite.py` ·
`domain/providers/factory.py` · `domain/feedback.py` · `domain/leaks.py` ·
`domain/grading.py` · `domain/srs.py` (conditional append + docstring rewrite) ·
`domain/scenarios.py` (2 builders) · `api/v1/drill.py` (gate + rebuild) ·
`app/services/review.py` (persist turn_class) · `app/db/models.py` (nullable column) ·
`backend/alembic/versions/` (one additive migration) · `content/postflop/turn.json` (new) ·
`content/schema/contentpack.schema.json` (hand-edit enum) · tests: `test_turn_graders.py`
(new), `test_signature.py` (additions only — pins untouched), `test_provider.py` (additions
+ one comment-only amendment — assertions untouched), `test_api.py` (gate tripwire + turn
rebuild test). NO `test_domain_purity.py` change (providers entry covers turn.py transitively).

## Out of scope (S6 no-gos)

Multiway (S8) · river (S7) · NO new Practice drill modes / Mode union / MODE_IDS /
Home.tsx / concept cards · no `Entry`/`ContentPack` threshold fields (numbers stay code
constants — Gate-1 decision; roadmap's "thresholds in packs" deferred to a future
consistency slice) · no changes to flop graders' outputs (byte-identical) · no preflop
`spot_signature` branch changes · no FE changes at all (`node_context: string[]` already
accommodates new values) · EVs labeled approximate (inherited composer language).

## Verify-by

Full `pytest -q` green; pinned hashes `6832a54693ba5f6c` / `0cdf437e044b0bc5` UNCHANGED
(literal assertions, not recomputed); NOT_FOUND provider trio assertions +
`test_feedback_tiers.py` pass unmodified; turn spots return freq+EV verdicts with authored
rationale naming the turn-card class (never boolean, non-tautological); `range_advantage`
differs by node context (test); NOT_FOUND grade persists nothing (tripwire test); due turn
row rebuilds a spot matching node_context + street + flop texture + turn_class (test); two
turn spots with different turn-card classes hash differently; Alembic migration applies
cleanly on an existing DB (additive nullable column); ruff clean; `./scripts/verify.sh` →
BACKEND VERIFY OK.
