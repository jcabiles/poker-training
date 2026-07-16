# Tickets — R2: Realistic persona-flavored fixed bet sizes

Spec: `docs/ai-dlc/specs/r2-persona-bet-sizes.md` · Contracts: `docs/ai-dlc/contracts/r2-bet-sizing.md`
· Research: `docs/ai-dlc/research/RES-B-bet-sizing.md`. 6 tickets. One implementer end-to-end is
fine; the parallelizable pairs are noted for orchestration.

## Dependency DAG
```
T1 (sizing.py) ─────┬──────────────► T4 (bot wiring) ──┐
                    └──────────────► T5 (hero seam) ────┼──► T6 (accept tests)
T2 (schema) ──► T3 (content) ───────► T4 ───────────────┘
```
- **Parallel wave A:** T1 ‖ T2 (disjoint files).
- **Then:** T3 (needs T2). **Then:** T4 ‖ T5 (disjoint files; both need T1; T4 also needs T3).
- **Last:** T6 (needs T3,T4,T5).

---

### T1 — Pure sizing helper `sizing.py`
Create `backend/app/domain/table/sizing.py` (domain-pure) with `postflop_node_key(board, legal, *,
is_aggressor)`, `HERO_NODE_SIZE`, `preflop_raise_to(...)` (two-sided `[min_bb,max_bb]` clamp + `iso`
node), and a shared `pot_fraction_to_bb` extracted from the existing postflop conversion.
- **Owns:** `backend/app/domain/table/sizing.py`, `backend/tests/test_sizing.py`.
- **Accept:** node taxonomy maps per §3a incl. `"flat"` for non-aggressor leads and `iso`; clamp is
  two-sided and collapses on `min_bb==max_bb`; anti-tell (node from `board` not `hole`).
- **Done-condition:** `./scripts/verify.sh` green incl. new `test_sizing.py`; `ruff check .` clean;
  `test_domain_purity.py` passes (no web/DB import).
- **Deps:** none.

### T2 — Schema: `sizing_by_node` lever + validator refactor
Add `sizing_by_node: dict[str, dict[str, float]] | None = None` to `PersonaPostflop`; refactor
`_sizing_valid` body into module-level `_validate_bucket_dist` and add a `sizing_by_node`
field-validator that validates each INNER dist (never parses node-key strings as floats).
- **Owns:** `backend/app/domain/content/models.py`, its model test.
- **Accept:** existing `sizing` still validates; `sizing_by_node` with keys like `"cbet_dry"` +
  valid inner dists loads; an inner dist that doesn't sum to ~1 is rejected; `None` is allowed.
- **Done-condition:** `./scripts/verify.sh` green; loading all 6 packs still succeeds (maniac `1.5`
  unaffected). **No Alembic migration** (content JSON, not DB).
- **Deps:** none.

### T3 — Author `sizing_by_node` content (4 aggressor personas)
Add `sizing_by_node` blocks to `content/personas/{tag,lag,nit,maniac}.json`, derived from RES-B §5.1
node baselines shifted by each persona's §3/§5.2 personality; document the derivation. Station/fish
get NONE (flat fallback). Existing `sizing`/preflop/lever blocks stay byte-unchanged.
- **Owns:** `content/personas/tag.json`, `lag.json`, `nit.json`, `maniac.json`.
- **Accept:** each authored `sizing_by_node` has the node keys `postflop_node_key` emits; TAG dry
  mean ≤0.45 & wet mean ≥0.6; maniac keeps its `1.5` overbet on wet/river; all validate under T2.
- **Done-condition:** `./scripts/verify.sh` green (content-load + schema tests); packs diff shows
  ONLY additive `sizing_by_node`.
- **Deps:** T2.

### T4 — Bot sizing wiring (preflop levers + postflop node-aware)
`play.py`: thread `current_bet_to`/limpers into `_preflop_decision`, map facing→node
(open/iso/3bet/4bet/5bet), size via `preflop_raise_to` instead of `min_bb`; update the
`sample_postflop_decision` call to pass `is_aggressor`. `personas_postflop.py`: add `is_aggressor`
param, select `sizing_by_node.get(node, sizing)` before the sampling draw.
- **Owns:** `backend/app/domain/table/play.py`, `backend/app/domain/personas_postflop.py`,
  `backend/tests/test_personas.py`, `backend/tests/test_personas_postflop.py`.
- **Accept:** bot open == pack `open_bb` per persona (maniac 4.5 ≠ nit 3.0); 3bet/4bet ==
  mult×last-raise clamped legal; `vs_limpers` iso sized; postflop dry vs wet differ per §6.2; sizes
  still sampled (no strength→size tell); chip deltas sum 0.0.
- **Done-condition:** `./scripts/verify.sh` green; engine/side-pot/persona suites green.
- **Deps:** T1, T3.

### T5 — Hero single predetermined size (backend + FE seam)
Add optional `size_bb` to `LegalAction` (`spot.py`); in `sim_session._view` set it on hero's
BET/RAISE options (preflop from content `sizing_bb`, postflop from `HERO_NODE_SIZE[node]`, clamped;
unmapped ⇒ `None`). FE: add `size_bb?` to the `LegalAction` type; `decisions.ts` submits
`la.size_bb ?? la.min_bb`.
- **Owns:** `backend/app/domain/spot.py`, `backend/app/services/sim_session.py`,
  `frontend/src/api/types.ts`, `frontend/src/lib/decisions.ts`, the `sim_session` size test.
- **Accept:** hero open `size_bb` == content seat size (UTG 3.0), not `min_bb`; always ∈
  `[min_bb,max_bb]` and `engine.apply` accepts it; unmapped node ⇒ `size_bb=None` ⇒ FE uses
  `min_bb`; exactly one size offered (no R3 choice); `spot_signature` unchanged (field not hashed).
- **Done-condition:** `./scripts/verify.sh` green; `cd frontend && npm run typecheck && npm run
  build` green.
- **Deps:** T1.

### T6 — Acceptance battery + full verify
Integration tests covering §6 (bot preflop per-persona, postflop node-differentiation, hero size +
legality, chip conservation, purity) and the full green run.
- **Owns:** `backend/tests/test_bet_sizing.py` (new).
- **Accept:** all §6 automated checks pass; a deliberate deterministic-strength→size mutation makes
  the anti-tell test FAIL (non-tautological).
- **Done-condition:** `./scripts/verify.sh` + `ruff check .` + `cd frontend && npm run typecheck &&
  npm run build` all green; `TAXONOMY_VERSION` unchanged; no migration added.
- **Deps:** T3, T4, T5.

---

### T7 — grade_map band reconciliation (added at build, user-approved)
Widen the preflop grading bands so hero is graded at R2's realistic prices: open cap → universal
3.0, 3-bet → 3.5×, 4-bet → 2.4×; genuine oversizes still return None.
- **Owns:** `backend/app/domain/table/grade_map.py` (bands only — no taxonomy/signature change).
- **Accept:** `test_bot_driven_facing_raise_decision_grades` passes; all pinned oversize/min-raise
  band tests stay green (they assert 4.0/12/30bb, above the new caps); additive (grades ≥ before).
- **Done-condition:** `./scripts/verify.sh` green.
- **Deps:** T4 (realistic bot sizes exist).

## Global done (slice complete)
All 6 tickets green · verify.sh + ruff + FE typecheck/build green · no Alembic migration · no
`spot_signature`/`TAXONOMY_VERSION` change · manual smoke (maniac opens big, hero opens 3bb, TAG
c-bets small-dry/big-wet) · then design-review is NOT required (no visual change) — but a quick
Simulate smoke in both themes is prudent since hero's action bar now shows different numbers.
</content>
