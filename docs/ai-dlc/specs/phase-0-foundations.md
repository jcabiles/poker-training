# Spec — Phase 0: Foundations & Architecture

> Delta spec for Phase 0 ONLY. See `docs/ai-dlc/roadmap.md` for the full plan. No preflop content/features here — those are Phase 1.

## Goal (one line)
Stand up the project skeleton + the core contracts (schemas, `StrategyProvider` interface, versioned API, persistence, test harness, a thin end-to-end "walking skeleton") so Phase 1+ features plug in with **no rebuild** and the heuristic→solver grading swap stays a drop-in.

## Why now
Everything downstream consumes a small set of schemas and one grading interface. Getting these right first is the whole future-proofing bet (roadmap principles 1–10). A walking skeleton proves the React ↔ FastAPI ↔ SQLite ↔ domain ↔ provider wiring before we pour features in.

## Repo structure
```
poker-training/
  backend/
    app/
      main.py                # FastAPI app, mounts /api/v1
      api/v1/                # routes: health, drill (next/grade)
      domain/                # PURE core — NO web/DB imports
        spot.py  action.py  evaluation.py  leaks.py  srs.py
        content/             # content-pack loader + range-notation parser
        providers/           # StrategyProvider interface + HeuristicProvider stub
      schemas/               # Pydantic request/response models (mirror domain)
      db/                    # SQLModel models, session, alembic migrations
    tests/                   # pytest + golden fixtures
    pyproject.toml
  frontend/
    src/
      components/            # RangeGrid, PokerTable, DecisionBar, FeedbackPanel (skeleton)
      api/                   # typed client generated from OpenAPI
      styles/tokens.css      # design tokens (colors, spacing, type) — both themes
      App.tsx main.tsx
    package.json vite.config.ts tsconfig.json
  content/
    preflop/                 # (empty in Phase 0; Phase 1 fills)
    schema/contentpack.schema.json
  docs/ research/ ai-dlc/
```

## Core schemas to define (the contracts)
All as Pydantic models in `domain/` + mirrored JSON Schema where they cross the API or content boundary. **Designed solver-ready and freq+EV from day 1.**

1. **Card / Board** — card = `"Ah"`,`"Td"` (rank+suit). Board = 0–5 cards.
2. **Spot** (normalized, solver-ready game state):
   - `game`: { variant `"NLHE"`, format `"cash"`, table_size, stakes {sb,bb,ante,straddle?}, max_buyin }
   - `street`: preflop|flop|turn|river · `board`: [card] · `pot_bb`
   - `hero`: { position, hole_cards:[card,card], stack_bb }
   - `players`: [{ position, stack_bb, status, is_hero }]
   - `effective_stack_bb`, `spr?`
   - `action_history`: [{ street, position, action, amount_bb }]
   - `to_act`, `legal_actions`: [{ action, min_bb, max_bb }]
   - `node_context`: tag(s) e.g. `RFI | vs_3bet | blind_defense | squeeze | vs_limpers` (drives provider + leak mapping)
   - Full granularity stored even if heuristics ignore some — so a solver can key off it later.
3. **Decision** (player's action): { action: fold|check|call|bet|raise, size_bb?, size_fraction? }
4. **EvaluationResult** (NEVER boolean):
   - `per_action`: [{ action, size_bb?, frequency 0..1, ev_bb }]
   - `best_action`, `chosen_eval`:{frequency,ev_bb}, `ev_loss_bb`
   - `correctness`: optimal|acceptable|mistake|blunder (ev_loss thresholds, configurable)
   - `rationale_tags`: [str], `explanation`: short text (the "why")
   - `provider`: heuristic|solver|hybrid (provenance), `leak_category`
   - **`coverage`: full | partial | not_found** + **`solver_node_key`: str | None** — *(refuter #1)* lets a solver report a missed node and a `HybridProvider` fall back to heuristics without any interface change. `not_found` ⇒ heuristic is authoritative.
5. **ContentPack**: { id, version, domain, entries, sizing rules, exploit overlays } + JSON Schema + range-notation parser (`"77+, ATs+, KQs"` → set of combos). **Entry format locked for mixed strategies from day 1** *(refuter #4)* — each entry's `actions` is a list, never a bare range:
   ```
   actions: [ { action: "raise", combos: "77+, ATs+", frequency: 1.0 },
              { action: "call",  combos: "77+, ATs+", frequency: 0.0 } ]
   ```
   HeuristicProvider sets `frequency: 1.0` on its dominant action; SolverProvider later fills true mixed frequencies with **no format change**. `exploit_overlays` may stay a freeform stub dict in Phase 0 (Phase 1 defines it).
6. **SRS item** (SM-2 fields): { id, spot_signature, leak_category, ease_factor=2.5, interval_days, repetitions, due_date, last_grade, history }. *(Schema only in Phase 0; algorithm runs in Phase 1.)*
   - **`spot_signature` definition locked now** *(refuter #3)* — deterministic, version-stable hash of a **canonical subset**: `(game.variant, game.format, street, sorted(node_context), hero.position, table_size, bucket(effective_stack_bb))`. **Excludes** hole_cards (same archetype) and action_history amounts (sizes vary). Documented in `domain/srs.py`; a golden test asserts signature stability so SRS history survives content-pack version bumps.
7. **LeakCategory** taxonomy (versioned enum) with **reserved numeric namespaces** *(refuter should-fix #1)* so later phases never renumber/break historical rows: **preflop 100–199**, **postflop 200–299**, **exploit 300–399**. Phase 0 seeds preflop: 100 rfi_ep … rfi_sb, bb_defense, vs_3bet_ip/oop, 4bet_response, squeeze, vs_limpers, sizing; 300 exploit_adjustment. A `taxonomy_version` constant ships alongside.

## StrategyProvider interface
```python
class StrategyProvider(Protocol):
    name: str
    async def supports(self, spot: Spot) -> bool: ...
    async def optimal(self, spot: Spot) -> EvaluationResult: ...           # action mix, no chosen action
    async def evaluate(self, spot: Spot, action: Decision) -> EvaluationResult: ...
```
**Async from day 1** *(refuter #2)* — solver lookups in Phase 3 are I/O-bound; defining the Protocol sync would force every provider + every golden fixture to be rewritten when the solver arrives. HeuristicProvider implements `async def` as trivial wrappers over sync logic; routes `await`. Phase 0 ships the interface + a **HeuristicProvider stub** that grades ONE node (RFI) well enough for the walking skeleton, returning **non-null, finite `ev_bb`** via a documented placeholder preflop-equity approximation *(refuter should-fix #5)* (clearly marked as a stub, replaced by real content in Phase 1). Full preflop content = Phase 1. Provider is selected via a factory so `SolverTableProvider`/`HybridProvider` drop in later untouched.

## Walking skeleton (the smoke slice)
One hardcoded RFI spot exercises the whole stack:
`GET /api/v1/drill/next` → Spot → React renders position + hole cards + DecisionBar → user picks action → `POST /api/v1/drill/grade` {spot, action} → HeuristicProvider stub → EvaluationResult → FeedbackPanel shows correctness + EV loss + the "why". One progress row persisted to SQLite.
No SRS / leak analytics / exploit logic yet (Phase 1) — just the wiring + every contract exercised once.

## Tech & tooling
- Backend: Python **3.14** (installed; 3.12+ works), FastAPI, Pydantic v2, SQLModel + SQLAlchemy, Alembic, pytest. venv at `backend/.venv`. Deps from pypi (allowed by sandbox). Watch for any dep lacking a 3.14 wheel at install time.
- Frontend: React 18 + TypeScript + Vite.
- **OpenAPI-typed client = `openapi-typescript` (types) + `openapi-fetch` (tiny typed client)** *(refuter should-fix #3)* — type-only generation, no heavy codegen toolchain to conflict with tsconfig. Both are npm deps (see sandbox note).
- API versioned under `/api/v1`; OpenAPI auto-generated.
- **CORS middleware** *(refuter should-fix #2)* allows `http://localhost:5173` (Vite dev) → `http://localhost:8000` (FastAPI) in dev, or the app is served same-origin in prod.
- **Migrations auto-run on app startup** in local/dev (`alembic upgrade head` on boot) *(refuter should-fix #4)* so a clean checkout never hits a schema-less SQLite file; a manual `alembic upgrade head` target also exists.
- Domain core importable with zero web/DB deps (enforced by a test that imports `domain` alone).

## Constraints
- **CSS = design tokens only** (no raw hex); AA contrast + visible `:focus-visible` in both themes.
- Domain core stays pure (no FastAPI/SQL imports) — keeps it unit-testable and reusable.
- EvaluationResult is freq+EV (never boolean); Spot is solver-ready. These two are load-bearing for the solver swap.
- Local single-user; no auth.
- **Sandbox note:** front-end `npm install` needs `registry.npmjs.org`, which is NOT in the current `.claude/settings.json` network allowlist. The allowlist must be widened (and Claude Code restarted) before front-end deps install. Python deps use pypi (already allowed). Flagged at the plan gate.

## Out of scope (Phase 0)
Real preflop ranges/content · SM-2 algorithm logic · leak analytics/dashboards · exploit/archetype drills · drill modes beyond the one smoke spot · ALL postflop · solver tables · live session logger · full UI/visual polish.

## Verify-by (what `/verify-change` will check)
1. `pytest` green: schema round-trip tests, range-notation parser test, golden fixture for the HeuristicProvider stub, the "domain imports with no web/DB" test, and a **spot_signature stability test** (same canonical spot → same signature across a simulated content-pack version bump).
2. `alembic upgrade head` succeeds from a clean state and the progress table exists.
3. Backend boots; `GET /api/v1/health` → 200; `/api/v1/drill/next` returns a schema-valid Spot; `/api/v1/drill/grade` returns a schema-valid EvaluationResult with **freq + non-null/finite ev_bb + coverage** populated; OpenAPI doc generated.
4. Frontend `vite build` succeeds; dev server reaches the backend **with no CORS error**; the smoke drill renders; one decision round-trips and renders feedback (correctness + EV + why).
5. CSS contrast/token check passes.
