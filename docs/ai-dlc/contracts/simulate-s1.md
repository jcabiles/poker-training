# Contract scan — Simulate S1 (table walking skeleton)

> Read-only scan by contract-mapper, 2026-07-10, ahead of the S1 spec.
> Scope: card model, API wiring, domain purity, FE shell, state patterns, test conventions.

## A. Behavioral contracts that must not break

1. **Card = frozen 2-char string `rank+suit`** (`domain/spot.py:16-26`: `RANKS="23456789TJQKA"`,
   `SUITS="cdhs"`, `Card = str` + `validate_card()`). Deck module must emit exactly this;
   `equity.py:24` `_DECK = [r + s for r in RANKS for s in SUITS]` is the canonical 52-card
   construction to mirror.
2. **FE `Card.tsx` parses positionally** (`card[0]`/`card[1]`, `Card.tsx:13-15`); `faceDown`
   prop is a discriminated union (`Card.tsx:6`) — card XOR faceDown, strict-TS enforced.
3. **Seat order lives in FE `RING` array** (`PokerTable.tsx:11` — UTG…BB), independent of the
   backend `Position` StrEnum (`spot.py:29-38`, 9 values, `.value` = wire format). Button
   rotation must keep backend Position values ∈ RING or seats silently vanish
   (`PokerTable.tsx:59` filters RING by presence).
4. **Dealer = `position === "BTN"`**, no is_dealer flag (`PokerTable.tsx:103-106`, `:129-133`).
5. **`PlayerState`/`Hero` are the wire shapes for seats** (`spot.py:99-104`, `:119-127`); FE
   indexes players by unique Position (`PokerTable.tsx:56` Map, last-wins on dupes).
6. **`spot_signature()` frozen** (`srs.py:48-63`) — S1 has no persistence; hazard deferred to S9/S10.
7. **Purity test = hardcoded module allowlist** (`test_domain_purity.py:12-15`, imports exact
   module strings). Must add the real module (see C4).

## B. Integration points — pattern to mirror

1. **Router:** `api/v1/simulate.py` with `APIRouter(prefix="/simulate", tags=["simulate"])`,
   wired in `api/v1/__init__.py` (mirror `drill.py:54` + `__init__.py:5-21`).
2. **Schemas:** domain Pydantic models ARE the wire contract — thin wrappers only, no parallel
   DTOs (`schemas/drill.py:1-22` idiom).
3. **In-memory state:** no precedent; closest analog = module-level singletons in
   `drill.py:56-60` (`_provider`, `_INDEX`, `_RNG`). A module-level `dict[str, ...]` keyed by
   session id inherits the same no-locking caveats.
4. **API tests:** reuse `temp_engine` + `client` fixture pair (`test_api.py:13-28`); app
   lifespan runs migrations on boot (`main.py:19`) so TestClient still needs the migration path.
5. **Factories:** add `make_*` helpers to `tests/factories.py` if fixtures needed, don't inline.
6. **FE view registration — 4-point checklist:** `View` union + `VIEW_IDS`
   (`hashRoute.ts:9,11`) · `VIEWS` array (`App.tsx:26-31`) · explicit render branch
   (`App.tsx:345-389` — the bare `else` falls into `QuizPanel` with invalid `kind` otherwise).
7. **Keyboard guard** gated `view === "drill"` (`App.tsx:244-269`) — correct to leave alone in
   S1; S2+ needs its own `view === "simulate"` effect.
8. **StatsStrip renders above every view** (`App.tsx:343`) — informational, no S1 action.
9. **API client:** flat async fns in `api/client.ts`, `json<T>()` wrapper, `BASE="/api/v1"`
   (`client.ts:19-38`).
10. **`types.ts` hand-maintained** — new interfaces authored manually, field-for-field.

## C. Hazards

1. **No error-response precedent anywhere** — zero `HTTPException` in `api/v1/*`. S1's
   `/simulate/session/{id}/hand` is the first fallible lookup; it establishes the pattern
   (decision recorded in spec).
2. **Existing RNG pattern is a shared unseeded module singleton** (`drill.py:60`) — S1
   deliberately diverges (per-hand `random.Random(secrets.randbits(256))`, seed logged);
   never reuse `_RNG`.
3. **In-memory sessions die on backend restart** — accepted by no-gos; note `serve.sh restart`
   + lifespan auto-migrate make restarts common during dev.
4. **Purity allowlist precision:** adding bare `app.domain.table` only imports `__init__.py`.
   Either add `app.domain.table.deck` explicitly or make `table/__init__.py` re-export deck —
   verify the entry actually exercises the module with logic.
5. **PokerTable RING filter** silently drops seats whose Position isn't in RING.
6. **Card.tsx discriminated union** — reveal logic must pass card XOR faceDown.
7. **No Alembic migration expected in S1** — any touch of `alembic/versions/` is a scope
   violation per the slice no-gos.
