# Tickets — Simulate wave 1b: S3 (personas) + S5 (turn/river seams)

> Specs: `docs/ai-dlc/specs/simulate-s3.md` (frozen pack schema + engine interface) and
> `docs/ai-dlc/specs/simulate-s5.md`. Contracts: `contracts/simulate-s3-personas.md`,
> `contracts/simulate-s5.md`.
> Branch: single shared `feat/simulate-wave1b` (one working tree ⇒ one branch); per-slice
> commits; disjoint file ownership across all four tickets.
> DAG: **T1 ‖ T2 ‖ T3 ‖ T4 all parallel** (T2/T3 author content to the frozen schema; T1's
> loader validates them at fan-in). T5 = lead close-out.

- [x] **T1 — S3 engine + enum widening (heavy-worker).**
  Persona Pydantic models + loader (duplicate-coverage raises), `sample_preflop_action`
  (first-match-wins, rng-injected `choices`, limp→CALL translation), VillainType += TAG/MANIAC
  + `EXPLOIT_ARCHETYPES`, leak categories 304/305 + `_EXPLOIT_LEAK` entries, test decoupling,
  closed-loop stat test per the frozen protocol.
  **Owns:** `backend/app/domain/content/models.py` · `backend/app/domain/personas.py` (new) ·
  `domain/archetypes.py` · `domain/leaks.py` · `domain/grading.py` ·
  `content/schema/persona.schema.json` (generated) · `backend/tests/test_personas.py` (new) ·
  `tests/test_domain_purity.py` · `tests/test_exploits.py` · `tests/test_api.py`.
  **Done-check:** `cd backend && pytest tests/test_personas.py tests/test_exploits.py tests/test_api.py tests/test_domain_purity.py -q`
  green; stat bands hit for all 6 packs; full `pytest -q` no regressions; runtime of
  test_personas.py measured + reported.
  **No-gos:** no postflop logic; no ActionType changes; no exploit content authoring; no FE/DB.

- [x] **T2 — S3 packs A (implementer).** Author `content/personas/{passive_fish,calling_station,nit}.json`
  to the frozen schema — doc-grounded, position-aware, genuinely mixed weights.
  **Done-check:** files parse as JSON and (at fan-in) validate via T1's loader with stat
  bands hit. **No-gos:** only these 3 files.

- [x] **T3 — S3 packs B (implementer).** Same for `content/personas/{tag,lag,maniac}.json`.
  **No-gos:** only these 3 files.

- [x] **T4 — S5 seams + golden tests (heavy-worker).**
  Pinned-hash signature tests (flop + preflop literals), turn/river signature fixtures
  (turn ≠ flop), street guards on the 3 flop graders, street-keyed dispatch map in
  `CompositeProvider`, append-rule docstring. ZERO behavior change — the 3 provider
  NOT_FOUND tests pass unmodified.
  **Owns:** `domain/providers/composite.py` · `domain/postflop.py` (guards only) ·
  `domain/srs.py` (docstring) · `backend/tests/test_signature.py`.
  **Done-check:** full `pytest -q` green with only `test_signature.py` modified among tests;
  deliberate-reorder tripwire verified locally (not committed) and noted in report.
  **No-gos:** no signature-tuple changes; no grader logic; no `range_advantage`/
  `_rebuild_postflop` work (S6/S7).

- [x] **T5 — Lead close-out.** Fan-in: run T1's loader over T2/T3 packs; full Verify-by both
  specs; refuter on the combined diff; PR `feat/simulate-wave1b`; mark S3 + S5 `[x]` in the
  roadmap only after checks actually pass.
