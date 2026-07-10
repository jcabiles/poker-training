# Tickets — Simulate S1: table walking skeleton

> Spec: `docs/ai-dlc/specs/simulate-s1.md` (API + domain interfaces frozen there — build to
> them, don't renegotiate). Contracts: `docs/ai-dlc/contracts/simulate-s1.md`.
> Branch: one shared `feat/simulate-s1` (workers share the main tree — no worktrees, .venv/node_modules).
> DAG: **T1 ‖ T3** first (disjoint files), **T2 after T1** (imports it), **T4 last** (lead).

- [ ] **T1 — Domain deck + rotation (Track A · agent: implementer).**
  Pure-domain dealing: `deal_hand(rng)` → `DealtHand` (9×2 hole + 5 board, `rng.shuffle` on
  the `equity.py:24`-style 52-card list) and `positions_for_button(button_seat)` per the
  spec's worked example.
  **Owns:** `backend/app/domain/table/{__init__.py,deck.py}` (new; `__init__` re-exports
  deck's public names) · `backend/tests/test_table.py` (new) · `backend/tests/test_domain_purity.py`
  (allowlist += `app.domain.table.deck` — precise module, contract C4).
  **Done-check (runnable):** `cd backend && pytest tests/test_table.py tests/test_domain_purity.py -q`
  green, including: fixed seed ⇒ exact expected deal; 52 distinct cards, 23 consumed, no
  repeats; `positions_for_button(0)` equals the spec's worked example and `(2)[2] == BTN`;
  no fastapi/starlette/sqlmodel/sqlalchemy in `sys.modules` after import.
  **No-gos:** no web/DB imports; no session state (T2's); no changes outside owned files.

- [ ] **T2 — Simulate API (Track E backend · agent: implementer · AFTER T1 merges).**
  `POST /simulate/session` + `POST /simulate/session/{id}/hand` per the frozen contract:
  module-level `dict[str, SimSession]` (`button_seat`, `hand_no` minimum), per-hand
  `random.Random(secrets.randbits(256))`, seed logged server-side never on the wire, button
  advances one seat per hand, 404 `HTTPException` on unknown session, hero cards only in the
  response (no villain cards, no board fields).
  **Owns:** `backend/app/schemas/simulate.py` (new) · `backend/app/api/v1/simulate.py` (new) ·
  `backend/app/api/v1/__init__.py` (include_router, mirror drill wiring) ·
  `backend/tests/test_simulate_api.py` (new; reuse `test_api.py`'s `temp_engine`/`client`
  fixture pattern).
  **Done-check:** `cd backend && pytest tests/test_simulate_api.py -q` green: session create
  returns 9 players (exactly one BTN, one is_hero, all stacks 100) + hero with 2 valid cards;
  next-hand moves BTN exactly one seat; response JSON contains no board/villain-card fields;
  unknown session → 404; `./scripts/verify.sh` → `BACKEND VERIFY OK`.
  **No-gos:** no DB models/migrations (touching `alembic/versions/` = scope violation); no
  reuse of drill's `_RNG`; no grader/provider imports.

- [ ] **T3 — Simulate tab UI (Track E frontend · agent: ux-ui-designer · parallel with T1).**
  View registration at all 4 points (`View` union + `VIEW_IDS` in `hashRoute.ts`; `VIEWS` +
  explicit render branch in `App.tsx` — must not fall into the `QuizPanel` else);
  `SimulateView.tsx` with the **synthetic-Spot adapter exactly as pinned in the spec**
  (PokerTable.tsx untouched); lazy session create; hand counter + "Next hand" button;
  `postSimulateSession`/`postSimulateHand` client fns mirroring `client.ts` idiom;
  hand-authored `types.ts` interfaces field-for-field with `schemas/simulate.py`.
  **Owns:** `frontend/src/lib/hashRoute.ts` · `frontend/src/App.tsx` ·
  `frontend/src/components/SimulateView.tsx` (new) · `frontend/src/api/client.ts` ·
  `frontend/src/api/types.ts`.
  **Done-check:** `cd frontend && npm run typecheck && npm run build` clean (compiles before
  T2 lands — types are hand-written); existing drill/home/quiz views still render (no
  QuizPanel fallthrough); CSS via design tokens only, AA contrast + visible focus both themes.
  **No-gos:** don't touch `PokerTable.tsx`, `Card.tsx`, keyboard-shortcut effect, StatsStrip;
  no new deps; no board rendering.

- [ ] **T4 — Integration verify + slice close-out (lead — not delegated).**
  Merge order T1 → T2 → T3 on `feat/simulate-s1`; run full Verify-by (spec §Verify-by):
  `verify.sh` + FE typecheck/build + manual probe on `#/simulate` (hand renders, villains
  face-down, one dealer chip, Next hand rotates button, reload restores view). Then:
  refuter pass on the combined diff + design-reviewer on the live tab (maker ≠ checker);
  open PR `feat/simulate-s1`; mark S1 `[x]` in `docs/ai-dlc/roadmap/simulate-table.md` only
  after every check actually passes.
  **Done-check:** all of the above observed by the lead, not reported by makers.
