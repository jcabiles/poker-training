# Tickets — Simulate wave 3: S4 (persona postflop) + S7 (river graders)

> Specs: `docs/ai-dlc/specs/simulate-s4.md` (lever engine, refuter-hardened: measured
> budget N=600/persona, AF occurrence floor, 3-bet <12% w/ pinned formula) and
> `docs/ai-dlc/specs/simulate-s7.md` (refuter PASS: verified conditional-append hashes,
> feedback surfaces both cards, own `_RIVER_CTX` branch). Contracts:
> `contracts/simulate-s4.md`, `contracts/simulate-s7.md`.
> Branch: single shared `feat/simulate-wave3` **off main AFTER PR #29 merges**.
> Per-ticket commits; disjoint ownership. DAG: **T1 ‖ T2 ‖ T3 ‖ T4 ‖ T5 parallel**
> (T2 authors packs/tests to T1's frozen schema; T5 cross-references T3's frozen names —
> wave-2 pattern). T6 = lead close-out.

## S4 — persona postflop engine

- [x] **T1 — Strength ladder + lever engine (heavy-worker).**
  `domain/personas_postflop.py` (new): StrengthBucket (7 disjoint rungs per the spec's
  disjointness rule), DrawCategory, public `strength_bucket()` (analytic only, river ⇒
  DrawCategory.NONE), `sample_postflop_decision()` (frozen signature; merit mapping w/
  lever semantics, monotonicity contract, SPR commit, pinned sizing formulas incl. the
  pot-after-call raise formula, clamp/jam, pinned normalize step, noise). Plus
  `content/models.py` `PersonaPostflop` + optional `postflop` field (own validator;
  preflop validation untouched) + purity allowlist += `'app.domain.personas_postflop'`.
  **Owns:** `backend/app/domain/personas_postflop.py` (new) ·
  `backend/app/domain/content/models.py` · `backend/tests/test_domain_purity.py`.
  **No-gos:** no engine/grader/provider/srs changes · no MC equity in the hot loop ·
  no persona-aware grading · preflop sampling path byte-identical.

- [x] **T2 — Packs + closed-loop suite (implementer).**
  Author `postflop` blocks in all 6 `content/personas/*.json` (doc-grounded per spec
  Content section). `backend/tests/test_personas_postflop.py` (new): unit tests (rung
  fixtures incl. disjointness edges, monotonicity, sizing-spread proof, clamp/jam,
  dampener, same-seed determinism, sum-0 fallback) + closed-loop harness (S2 engine
  playouts, seed 20260710, N=600/persona re-measured to fit ≤12s added, AF/fold-to-cbet
  with ≥30 occurrence floors, WTSD, PRD §8 bands widened per documented 3σ math) +
  table-texture test (9-max lineup, 1,500 hands, players-to-flop [2.8,4.5], limper >50%,
  3-bet-pot rate <12% with the pinned formula).
  **Owns:** `content/personas/*.json` (6 files) · `backend/tests/test_personas_postflop.py` (new).
  **No-gos:** no source edits — spec-conformance issues in T1's engine get REPORTED, not
  patched; band tuning of pack numbers is yours (wave-1b T3 precedent), engine math is not.

## S7 — river graders

- [x] **T3 — River grading core (heavy-worker).**
  NodeContext += `RIVER_BARREL("river_barrel")`/`VS_RIVER_BET("vs_river_bet")`;
  `texture.py::river_card_class` (board[4] vs board[:4], same 5 classes/precedence);
  `range_advantage` river branch (flop/turn paths byte-identical); `grade_river_barrel`/
  `grade_vs_river_bet` (flat constants + pot odds, busted-draw demotion
  `cat_effective = "air" if cat == "draw"`, 6-wide tags, villain-pos convention
  `spot.facing or _villain_pos(spot)` commented, leak ints via frozen names 205/206 —
  T5 defines); `providers/river.py` (street==RIVER + river nodes only + board≥5) +
  composite 4-param + factory; `content/postflop/river.json`; schema enum hand-edit.
  **Owns:** `domain/spot.py` · `domain/texture.py` · `domain/postflop.py` ·
  `domain/providers/river.py` (new) · `providers/composite.py` · `providers/factory.py` ·
  `content/postflop/river.json` (new) · `content/schema/contentpack.schema.json`.
  **No-gos:** no `_hand_category` body changes · no srs/drill/scenarios/review/db edits
  (T4's) · no leaks/grading/feedback edits (T5's) · flop+turn grader outputs byte-identical.

- [x] **T4 — SRS river dim + rebuild + migration (heavy-worker).**
  `srs.py`: SECOND conditional append (river-only, after turn_class — refuter-verified
  design; flop AND turn hashes byte-unchanged, pins stay literal) + docstring update.
  `db/models.py`: nullable `river_class` + fix the stale turn_class comment; additive
  migration `0008` (clone 0007). `review.py`: populate river_class for RIVER spots.
  `drill.py`: `_POSTFLOP_CTX` += river members; **own `_RIVER_CTX` branch with 5-wide
  target — NEVER fold into `_TURN_CTX` (turn rows carry river_class=None; shared branch
  silently degrades turn rebuild)**. `scenarios.py`: `build_river_barrel_spot`/
  `build_vs_river_bet_spot` (pinned prior lines; street=RIVER history entries; CALL
  min_bb incremental). Tests: `test_signature.py` additions (river-class divergence;
  turn hashes unchanged; pins untouched), `test_api.py` additions (river rebuild test
  matching all 5 archetype fields) + the ONE permitted comment amendment at the tripwire
  (`test_api.py:272`).
  **Owns:** `domain/srs.py` · `app/db/models.py` · `backend/alembic/versions/` (new) ·
  `app/services/review.py` · `api/v1/drill.py` · `domain/scenarios.py` ·
  `tests/test_signature.py` · `tests/test_api.py`.
  **No-gos:** NEVER update a pinned hash literal · additive migration only · no
  postflop/spot/texture edits (T3's — author to frozen names).

- [x] **T5 — Leaks + feedback + river tests (implementer).**
  `leaks.py`: RIVER_BARREL=205, VS_RIVER_BET=206, TAXONOMY_VERSION→5; `grading.py`
  river branches (second mapping site); `feedback.py`: `_NODE` river entries,
  `_RIVER_CLASS` dict, **widen the turn_class gate's node tuple to include river nodes
  (both card sentences surface) + add the tags[5] river gate; turn-node output
  byte-unchanged**. `tests/test_river_graders.py` (new): freq+EV never boolean, ladder,
  busted-draw-demotion grading test, range_advantage river-vs-flop divergence, tiers
  naming BOTH turn and river cards, leaks 205/206 both sites. `test_provider.py`: river
  provider gating additions (scaffold pattern). `test_postflop.py`: new 5-card-board
  `_hand_category` fixtures (made vs busted 4-flush/4-straight — roadmap regression guard).
  **Owns:** `domain/leaks.py` · `domain/grading.py` · `domain/feedback.py` ·
  `tests/test_river_graders.py` (new) · `tests/test_provider.py` · `tests/test_postflop.py`.
  **No-gos:** no grader/provider source edits (T3's) · `test_feedback_tiers.py` +
  `test_turn_graders.py` pass UNMODIFIED · no tiles/cards/drill modes.

## Close-out

- [x] **T6 — Lead fan-in.** Full `pytest -q` + ruff + `./scripts/verify.sh`; pins literal +
  unchanged; migration 0008 applies; S3 preflop band test + S6 turn tests byte-identical;
  closed-loop runtime ≤ budget (report); refuter on the combined diff; PR
  `feat/simulate-wave3`; mark S4 + S7 `[x]` in roadmap + add the 3-bet-target roadmap note.
