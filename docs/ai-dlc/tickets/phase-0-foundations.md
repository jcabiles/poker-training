# Tickets — Phase 0: Foundations & Architecture

Spec: `docs/ai-dlc/specs/phase-0-foundations.md`. 8 tickets, small, one-file-one-owner. Build code only after the plan gate is approved.

> **STATUS: COMPLETE (2026-06-27).** T0–T5 + T7 verified — 36 backend tests green, `scripts/verify.sh` boots app + round-trips a graded decision. T6 frontend builds clean and the live smoke drill was driven via Playwright (next → grade → feedback → persist). EV numbers are a documented heuristic placeholder; real grading lands in Phase 1.

## DAG / waves
```
T0  ─▶ T1 ─┬─▶ T2 ─▶ T3 ─┐
           └─▶ T4 ────────┴─▶ T5 ─▶ T6 ─▶ T7
```
- Wave 1: **T0**
- Wave 2: **T1**
- Wave 3: **T2 + T4** (parallel — disjoint files)
- Wave 4: **T3**
- Wave 5: **T5**
- Wave 6: **T6**
- Wave 7: **T7**

For a single-agent build, just go T0→T7 in order. Parallelize only T2+T4 if desired.

---

### T0 — Repo scaffold + tooling + health
Create the monorepo skeleton: backend FastAPI app (with CORS for localhost:5173, `/api/v1/health`, and a `main.py` that includes an `api.v1.router` package T5 will fill), frontend Vite+React+TS skeleton, dirs, dev scripts.
- **Owns:** top-level dirs, `backend/app/main.py`, `backend/pyproject.toml`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `scripts/`.
- **Depends on:** —
- **Done when:** `uvicorn app.main:app` boots; `GET /api/v1/health` → 200; `npm run dev` serves the Vite app; CORS middleware present.

### T1 — Domain schemas (pure core)
Define Card/Board, Spot (solver-ready), Decision, EvaluationResult (incl. `coverage` + `solver_node_key`), LeakCategory (namespaced enum + `taxonomy_version`), SRS item (incl. locked `spot_signature` canonical-subset hash).
- **Owns:** `backend/app/domain/{spot,action,evaluation,leaks,srs}.py`, `backend/tests/test_schemas.py`, `backend/tests/test_signature.py`, `backend/tests/test_domain_purity.py`.
- **Depends on:** T0.
- **Done when:** `pytest` green for schema round-trips, **spot_signature stability across a simulated content-pack version bump**, and "domain imports with zero web/DB deps".

### T2 — ContentPack schema + range parser + loader
Lock the content-pack JSON Schema (actions-list format with per-action combos + frequency), implement the range-notation parser (`"77+, ATs+"` → combos) and the pack loader/validator.
- **Owns:** `content/schema/contentpack.schema.json`, `backend/app/domain/content/`, `backend/tests/test_content.py`.
- **Depends on:** T1.
- **Done when:** parser unit tests pass (expansions + edge cases); a sample pack validates against the schema; invalid packs are rejected with a clear error.

### T3 — StrategyProvider interface + HeuristicProvider stub + factory
Define the **async** `StrategyProvider` Protocol and a `HeuristicProvider` stub that grades an RFI node and returns freq + **non-null/finite ev_bb** (documented placeholder) + coverage + rationale; add a provider factory.
- **Owns:** `backend/app/domain/providers/`, `backend/tests/test_provider.py`.
- **Depends on:** T1, T2.
- **Done when:** golden-fixture test asserts a known RFI spot → expected EvaluationResult shape (freq+EV+coverage+rationale); factory returns the heuristic provider by config.

### T4 — Persistence (SQLite + Alembic)
SQLModel models (a `drill_attempt`/progress row), DB session, Alembic setup, and auto-`upgrade head` on app startup.
- **Owns:** `backend/app/db/`, `backend/alembic/`, `backend/alembic.ini`.
- **Depends on:** T0, T1.
- **Done when:** `alembic upgrade head` succeeds from clean; app startup auto-migrates; a row can be inserted/read in a test.

### T5 — API layer (drill next/grade) + request/response schemas
Implement `/api/v1/drill/next` (returns a hardcoded RFI Spot) and `/api/v1/drill/grade` (calls the provider, persists a progress row), with Pydantic API schemas mirroring domain; verify OpenAPI generates.
- **Owns:** `backend/app/api/v1/` (router + drill routes), `backend/app/schemas/`, `backend/tests/test_api.py`.
- **Depends on:** T1, T3, T4.
- **Done when:** `/drill/next` returns a schema-valid Spot; `/drill/grade` returns a schema-valid EvaluationResult and writes a row; `/openapi.json` includes both routes.

### T6 — Frontend smoke drill + typed client + tokens
Generate the typed client (`openapi-typescript` + `openapi-fetch`), add `tokens.css` (both themes), skeleton components (RangeGrid, PokerTable, DecisionBar, FeedbackPanel), and wire next→decide→grade→feedback.
- **Owns:** `frontend/src/` (components, api client, styles, App).
- **Depends on:** T5. **⚠ Prereq:** npm-registry sandbox access (see gate note).
- **Done when:** `vite build` succeeds; dev app renders the RFI spot, a decision round-trips with no CORS error, and FeedbackPanel shows correctness + EV + why.

### T7 — Verify harness + run docs + sandbox note
Wire the spec's Verify-by into runnable checks (pytest config, a boot-and-probe script for the API routes, the CSS token/contrast check), write README run instructions, and document the npm-registry sandbox-widening step.
- **Owns:** `backend/tests/conftest.py` + pytest config, `scripts/verify.sh`, `README.md`.
- **Depends on:** T0–T6.
- **Done when:** the full Verify-by checklist runs green via one command and the README lets a cold reader boot both halves.

---

## Gate note — sandbox prerequisite for T6
Front-end `npm install` (React/Vite + `openapi-typescript`/`openapi-fetch`) needs `registry.npmjs.org`, which is **not** in the current `.claude/settings.json` network allowlist (pypi only). Before T6, the allowlist must be widened (likely `registry.npmjs.org`, possibly `registry.yarnpkg.com`) and Claude Code restarted. Backend tickets (T0–T5, T7-backend) are unblocked now since Python deps use pypi.
