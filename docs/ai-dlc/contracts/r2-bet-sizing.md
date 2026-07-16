# Contract map — R2: Realistic persona-flavored fixed bet sizes

**Scope of scan:** how bet/raise SIZES are produced + consumed for bots and hero in the
Simulate table, ahead of R2. Read-only. Spec input: `docs/ai-dlc/research/RES-B-bet-sizing.md`.
**Date:** 2026-07-15.

---

## 1. The size-production map (end to end)

### Preflop — bots
- `backend/app/domain/table/play.py:103` — `size = la.min_bb if la.min_bb is not None else la.max_bb`.
  **Bots BET/RAISE to the minimum legal raise.** The persona preflop levers are NOT consulted.
- `sample_preflop_action` (`personas.py:61`) returns only an ACTION (raise/call/fold) via the
  weighted mix in the pack `preflop` blocks — it does **not** return a size. `play.py` then
  slaps `min_bb` on it.

### Preflop — persona sizing levers (DEAD CODE)
- `PersonaSizing{open_bb, threebet_mult, fourbet_mult}` defined `content/models.py:114-118`.
- **Read NOWHERE in `backend/app/`** (grep: only the model definition matches). The docstring
  even admits it: *"Authored in S3, consumed in S4 (the S3 engine ignores it)"* — but S4 never
  wired them either. The six packs carry values RES-B confirmed correct, but nothing reads them.
- ⇒ **R2's core preflop task:** make the bot (and hero) preflop size read `open_bb` /
  `threebet_mult` / `fourbet_mult` from the persona pack instead of `min_bb`.

### Postflop — bots (ALREADY DATA-DRIVEN)
- `play.py:_postflop_decision` → `sample_postflop_decision` (`personas_postflop.py`).
- `personas_postflop.py:329` — `fracs = [(float(k), w) for k, w in pf.sizing.items()]`, samples a
  pot-fraction independent of hand strength (anti-sizing-tell rule 3). **Postflop sizes are
  already persona-flavored.** R2 does NOT need to rewire postflop sizing — RES-B §5.2 confirms
  the shipped distributions. (Open question = the node-agnostic flat distribution, RES-B §5.3.)

### Hero (both streets)
- `frontend/src/components/simulate/SimActionBar.tsx:9` — renders "fold/check/call/bet/raise
  options at **ENGINE-provided sizes**"; `onDecide(opt.action, opt.size_bb)`.
- `SimulateView.tsx:444-471` — `postHeroAction(id, {action, size_bb})`.
- `sim_session.apply_hero_action` (`sim_session.py:402`) receives `Decision(action, size_bb)`.
- Hero's "predetermined size" = the `size_bb` on each legal option produced by
  `legal_actions(state)` (imported `sim_session.py:46`) — which, like the bot path, defaults to
  the engine's `min_bb`. **R2 keeps hero on a SINGLE predetermined size** (realistic, not
  min-raise); the two-option choice is R3's extension of this same seam.

---

## 2. Hard-coded vs data-driven (R2's wiring targets)

| Path | Today | R2 target |
|---|---|---|
| Preflop bot open/3bet/4bet size | **hard-coded** `min_bb` (`play.py:103`) | read persona `open_bb`/`threebet_mult`/`fourbet_mult` |
| Preflop hero predetermined size | engine `min_bb` via `legal_actions` `size_bb` | realistic single size (research/pack-driven) |
| Postflop bot bet/raise size | **data-driven** `pf.sizing` (`personas_postflop.py:329`) | no change (RES-B confirms) |
| Postflop hero size | engine size via `legal_actions` | R2 keeps single; R3 adds 2nd option |
| 5-bet | jam to stack (`vs_4bet.json sizing_bb:100` override) | no change |

---

## 3. Schema — the maniac `1.5` question: RESOLVED, no change needed

`PersonaPostflop.sizing` (`content/models.py:120`) is `dict[str,float]`. Its validator
`_sizing_valid` (`models.py:134-150`) requires: keys parse as `float > 0`, weights `> 0`,
weights sum to ~1.0. **No fixed-enum key lock.** `maniac.json` already ships
`{"0.75":0.4,"1.0":0.35,"1.5":0.25}` and loads/validates today (532 tests green). ⇒ **The `1.5`
overbet key is already legal. R2 needs no schema/migration change for it.**

RES-B's optional Option B (`sizing_by_node` per-node override) WOULD be a new schema field — but
RES-B recommends deferring it (Option A). No Alembic migration either way: persona packs are
**content JSON**, not DB rows.

---

## 4. Frozen / pinned things a size change must NOT break

- **`spot_signature()` (`srs.py`) is frozen** — but it does NOT hash raw bet amounts (docstring
  `srs.py:5`: *"bet amounts / pot size (sizes vary), so the same conceptual spot"* collapses).
  R2 does not touch `srs.py`. **Behavioral consequence to flag:** `faced_bet_bucket` (`srs.py:71`)
  buckets the bet hero FACES into small/big and *keeps them as separate SRS items*. Making bot
  preflop sizes realistic (3bb vs a min-raise) changes the pot geometry hero faces, which can move
  a faced bet across the small/big boundary → a *different, still-valid* SRS item. This is
  arguably more correct, but the spec must call it out (Practice SRS persistence path). Simulate
  MW/sim spots don't persist to Practice SRS, so live-sim grading is unaffected.
- **`grade_map.py`** authors flop c-bet small=33%/big=75% (lines ~292-293) as the graded baseline;
  turn/river read `spot.legal_actions`. R2 changing *bot/hero action* sizes feeds these graders
  realistic prices — intended — but R2 must not change the grader's own baseline constants.
- **`TAXONOMY_VERSION`** — unchanged (no grader taxonomy change).
- **Chip conservation** — deltas must still sum to 0.0; side-pot / no-reopen / incomplete-raise
  rules in `engine.py` must stay green. A bigger open is still a legal raise ≥ `min_bb`, so the
  engine's raise-legality math is unaffected — but tests must confirm.

---

## 5. Domain purity
`play.py` is purity-allowlisted (`tests/test_domain_purity.py`). Reading persona levers stays
pure (packs are loaded via the domain content registry, no web/DB import). R2's wiring stays in
`app/domain/` — no purity risk.

---

## 6. Tests R2 must keep green
- `./scripts/verify.sh` (backend pytest + boot probe).
- Chip-conservation / engine: `backend/tests/` engine + side-pot + RNG suites.
- Persona sizing/behavior: `test_personas.py`, `test_personas_postflop.py`.
- Domain purity: `test_domain_purity.py`.
- FE: `cd frontend && npm run typecheck && npm run build`.
- **New tests R2 adds** (per roadmap pass/fail): bot open/3bet/cbet/barrel sizes match the
  researched table per persona; a test asserting persona A sizes ≠ persona B where research says
  so; sizes stay frequency-sampled where multiple authored (no deterministic strength→size tell).

---

## 7. Integration points (who else is affected)
- **`grade_map` / grading** — reads sizes to grade hero; realistic sizes = realistic graded prices
  (the whole point). No grader-code change; graders read live `spot.legal_actions`.
- **`SimEventLog` / FE narration** — renders `raises to {amount}bb`; realistic sizes just show
  bigger numbers, no FE logic change beyond what `size_bb` already carries.
- **Ledger / stacks** — carry-over stack + net-BB ledger (S9) sum from deltas; unaffected as long
  as chip conservation holds.
</content>
</invoke>
