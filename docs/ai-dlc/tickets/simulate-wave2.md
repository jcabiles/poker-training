# Tickets — Simulate wave 2: S2 (hand engine) + S6 (turn graders)

> Specs: `docs/ai-dlc/specs/simulate-s2.md` (frozen engine interface + betting semantics)
> and `docs/ai-dlc/specs/simulate-s6.md` (frozen enum/signature/provider contracts, both
> refuter-hardened 2026-07-10). Contracts: `contracts/simulate-s2.md`, `contracts/simulate-s6.md`.
> Branch: single shared `feat/simulate-wave2` **off main AFTER PR #28 merges** (S6 builds on
> S5's dispatch seam + S3's enum widening). Per-ticket commits; disjoint file ownership.
> DAG: **T1 ‖ T2 ‖ T3 ‖ T4 ‖ T5 all parallel** (T2 authors tests to T1's frozen interface;
> T3/T5 cross-reference frozen leak names — fan-in compiles, wave-1b pattern). T6 = lead
> close-out.

## S2 — hand engine

- [ ] **T1 — Engine implementation (heavy-worker).**
  `domain/table/engine.py` per the frozen interface: SeatState/Pot/HandState/Settlement,
  `start_hand` (POST blinds, initial betting state 1.0/1.0/2.0), `legal_actions` (4 shapes:
  unopened / facing / matched-with-option / no-reopen [FOLD,CALL]), `apply` (raise-TO
  semantics, size_fraction → ValueError, incomplete-raise increment rule, street advance +
  auto-runout), `settle` (side pots w/ dead money, best7 showdown, round-down +
  residual-to-first-clockwise ⇒ deltas sum EXACTLY 0.0). Plus `equity.py` `best7 = _best7`
  alias, `table/__init__.py` re-exports, purity allowlist += `'app.domain.table.engine'`.
  **Owns:** `backend/app/domain/table/engine.py` (new) · `domain/table/__init__.py` ·
  `domain/equity.py` (alias line) · `tests/test_domain_purity.py` (one string).
  **Done-check:** module imports clean; `pytest tests/test_domain_purity.py -q` green;
  T2's battery green at fan-in.
  **No-gos:** no deck.py changes (pinned-seed test) · no wire/FE/DB · no persona logic ·
  no rng params on the engine (deterministic given inputs).

- [ ] **T2 — Engine test battery + RNG suite (implementer).**
  Author to the FROZEN spec interface (parallel with T1): `tests/test_engine.py` — scripted
  side-pot scenarios (3-way double all-in, split main + sole side winner, incomplete-raise
  case asserting legal-action SHAPES, fold-out, BB walk, **limped-pot BB option: [CHECK,
  RAISE] never CALL(0)**), ≥2k random-policy conservation property (seeded rng, deltas sum
  == 0.0 exactly, no negative stacks, all-in delta bounds), illegal-action ValueErrors
  (incl. size_bb=None). `tests/test_rng_suite.py` — 200k raw shuffles seeded
  `random.Random(20260710)`: summed per-slot GOF chi-square over 52×18, d.f. 918,
  hardcoded critical value 1057 (χ²₉₁₈ @ p=0.001, cite in comment — NO scipy/numpy);
  pair 5.88% / suited 23.53% ±0.3pp; 5k full `deal_hand` wrapper check ±1.5pp + no-dup
  cards. Runtime < 10s (refuter measured 2.4s), report measured.
  **Owns:** `backend/tests/test_engine.py` (new) · `backend/tests/test_rng_suite.py` (new).
  **No-gos:** no new dependencies · no source edits — interface mismatches get reported to
  lead, not patched around.

## S6 — turn graders

- [ ] **T3 — Turn grading core (heavy-worker).**
  NodeContext += `TURN_BARREL("turn_barrel")`/`VS_TURN_BET("vs_turn_bet")`;
  `texture.py::turn_card_class` (pairing|flush|straight|over|blank, precedence order);
  `range_advantage` rewrite — flop path VERBATIM (outputs byte-identical), turn path
  consumes ctx, only 3 canonical labels; `grade_turn_barrel`/`grade_vs_turn_bet` (flop
  anatomy, SAME band constants, **5-wide tags** [node, adv, cat, wetness, turn_class],
  leak ints via frozen names LeakCategory.TURN_BARREL/VS_TURN_BET — T5 defines them);
  `providers/turn.py` (supports: street==TURN + turn nodes only + board≥4) + composite
  3-param `__init__` + `_by_street[TURN]` + factory wiring; `content/postflop/turn.json`
  (both contexts, position/facing-keyed rationale); hand-edit schema NodeContext enum
  (`contentpack.schema.json:123`).
  **Owns:** `domain/spot.py` · `domain/texture.py` · `domain/postflop.py` ·
  `domain/providers/turn.py` (new) · `providers/composite.py` · `providers/factory.py` ·
  `content/postflop/turn.json` (new) · `content/schema/contentpack.schema.json`.
  **Done-check:** existing flop grader tests + NOT_FOUND trio assertions pass UNMODIFIED;
  T5's grader tests green at fan-in.
  **No-gos:** no srs.py/drill.py/scenarios.py edits (T4's) · no leaks.py/grading.py/
  feedback.py edits (T5's) · no river · no multiway · no test_domain_purity.py change.

- [ ] **T4 — SRS turn dim + persistence + coverage gate + rebuild (heavy-worker).**
  `srs.py`: CONDITIONAL append of turn_class (element OMITTED for flop — refuter-proven;
  constant-append breaks the pin) + rewrite the false append-rule docstring. DB: nullable
  `turn_class` column on SRSItemRow + additive Alembic migration; `review.py::
  _postflop_archetype` persists turn_card_class for turn/river, None flop. `drill.py`:
  coverage gate (`if result.coverage != Coverage.NOT_FOUND:` around BOTH writes),
  `_POSTFLOP_CTX` += turn members, two rebuild branches matching (texture, spr, faced,
  turn_class). `scenarios.py`: `build_turn_barrel_spot`/`build_vs_turn_bet_spot` (board
  len 4, multi-street history for faced_bet_bucket, incremental CALL min_bb).
  Tests: `test_signature.py` additions (pins UNTOUCHED as literals; turn-class divergence;
  flop byte-unchanged), `test_api.py` additions (NOT_FOUND-persists-nothing tripwire;
  non-tautological turn rebuild test: node_context+street+texture+turn_class match).
  **Owns:** `domain/srs.py` · `app/db/models.py` · `backend/alembic/versions/` (new
  migration) · `app/services/review.py` · `api/v1/drill.py` · `domain/scenarios.py` ·
  `tests/test_signature.py` · `tests/test_api.py`.
  **No-gos:** NEVER update a pinned hash literal · no postflop.py/spot.py edits (T3's —
  import the new enum members; they exist once T3 commits, author to frozen names) · no
  drop/alter columns, additive migration only.

- [ ] **T5 — Leaks + feedback wiring + grader tests (implementer).**
  `leaks.py`: TURN_BARREL=203, VS_TURN_BET=204, TAXONOMY_VERSION→4; `grading.py::
  leak_category_for` turn branches (BOTH mapping sites — miss one and leak_focus breaks);
  `feedback.py`: `_NODE` entries for turn_barrel/vs_turn_bet with turn phrasing consuming
  tags[4] (turn_class), `_ADV` unchanged. `tests/test_turn_graders.py` (new): freq+EV never
  boolean, correctness ladder, range_advantage differs-by-context test, rationale names the
  turn-card class, both leak ints mapped. `test_provider.py`: additions for the turn
  provider + the ONE permitted comment-only amendment on
  `test_postflop_provider_rejects_turn_street` (assertions untouched).
  **Owns:** `domain/leaks.py` · `domain/grading.py` · `domain/feedback.py` ·
  `tests/test_turn_graders.py` (new) · `tests/test_provider.py`.
  **No-gos:** no grader/provider source edits (T3's) · no Home.tsx/concept cards/drill
  modes · `test_feedback_tiers.py` must pass UNMODIFIED.

## Close-out

- [ ] **T6 — Lead fan-in.** Full `pytest -q` + ruff + `./scripts/verify.sh`; verify pinned
  hashes are literals and unchanged; migration applies on an existing dev DB; refuter on
  the combined diff; PR `feat/simulate-wave2`; mark S2 + S6 `[x]` in the roadmap only
  after checks pass.
