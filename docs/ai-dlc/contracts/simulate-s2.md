# Contract map — S2 betting engine (`domain/table/engine.py`), scanned at HEAD 2026-07-10

> Read-only scan by contract-mapper (post-wave-1b checkout, `feat/simulate-wave1b`).
> Slice: `docs/ai-dlc/roadmap/simulate-table.md` S2.

## Contracts

1. **`table` package surface = exactly 3 names.** `backend/app/domain/table/__init__.py:1-3`
   exports `DealtHand`, `deal_hand`, `positions_for_button` only. S2 adds `engine.py` alongside
   and re-exports; never rewrites `deck.py`.

2. **`DealtHand` shape + deal order pinned byte-exact.** `deck.py:32-44`:
   `hole_cards: list[tuple[Card, Card]]` (len 9, index = seat), `board: list[Card]` (len 5,
   upfront). Deal order `deck.py:53-56`: shuffle once → 18 hole cards (2 consecutive per seat,
   seats 0–8) → 5 board, no burns. `tests/test_table.py:7-21` pins seed 42 to exact cards.
   ⚠️ Engine must consume the pre-dealt board and reveal street-by-street — any `deal_hand`
   internal change breaks the pinned-seed test.

3. **Seat/position convention.** Element `i` of `positions_for_button()` = seat `i`'s position;
   clockwise = ascending seat mod 9; `_ROTATION` starts BTN (`deck.py:19-29,60-66`; tested
   `test_table.py:52-79`). ⚠️ Preflop ACTION order is a different list —
   `scenarios.py:35-45` `_SEAT_ORDER` (UTG first, blinds last). Engine derives "first to act
   preflop = seat `(button_seat+3) % 9`" from rotation; do not conflate the two orderings.

4. **`LegalAction` = 3-field predetermined-sizing shape; CALL amounts INCREMENTAL.**
   `spot.py:113-116`: `LegalAction(action: ActionType, min_bb: float | None, max_bb: float | None)`.
   Units doc `scenarios.py:7-9`: call `min_bb` = chips hero must ADD, net of posted/invested
   (`_posted()` `scenarios.py:107-112`: SB 0.5, BB 1.0). Precedents: RFI =
   `[FOLD, RAISE(min_bb=sizing, max_bb=eff_bb)]` (`scenarios.py:187-188`); vs-RFI call =
   `round(osize - _posted(pos), 2)` (`:200`); jam = `RAISE(min_bb=eff_bb, max_bb=eff_bb)`
   (`:248`); two discrete sizes = two `BET` entries differing in `min_bb` (`:409-411`).
   ⚠️ Consumers scan by `(action, min_bb)`: `postflop.py:323,480,545,726`; `srs.py:71-80`
   `faced_bet_bucket` derives the SRS signature bucket from CALL `min_bb` — wrong call
   semantics silently shifts frozen signatures.

5. **`Decision` requires a size for BET/RAISE.** `action.py:10-20`:
   `Decision(action, size_bb: float | None, size_fraction: float | None)` + validator. FE
   mirror `types.ts:77-79` has only `{action, size_bb?}`. `HistoryAction.amount_bb`
   (`spot.py:106-110`) records absolute per-action amounts. **Spec must freeze raise-to vs
   increment semantics** for engine action-apply.

6. **`ActionType` vocabulary CLOSED:** `fold/check/call/bet/raise/post` (`spot.py:48-54`;
   `POST` exists for blind posting in history). `PlayerStatus IN/FOLDED/ALLIN`
   (`spot.py:57-60`). All-in = CALL/RAISE capped at stack + `PlayerStatus.ALLIN`, never a new
   enum value (would ripple to hand-maintained `types.ts`).

7. **Showdown evaluator is `equity.py:_best7` — PRIVATE; `hand_rank.py` is NOT it.**
   `equity.py:71-79`: `_best7(cards: list[str]) -> tuple`, 7-card input of 2-char strings,
   max over 21 five-card combos (`_C75` `:27`), `_eval5` (`:30-68`) returns comparable tuple
   higher = stronger, categories 8→0, wheel handled (`straight_high = 3`, `:44`); ties =
   exact tuple equality (`equity.py:135-137` uses `hr == vr → 0.5`). `hand_rank.py:83-84` is
   the preflop 169-class percentile table — irrelevant to showdown. **Spec decision: promote
   a public alias** (e.g. `best7 = _best7`) rather than import a private name. No split-pot
   helper exists — S2 writes it (equal tuples split).

8. **Domain-purity allowlist is hardcoded strings, module-precise.**
   `tests/test_domain_purity.py:10-15` currently ends `...,'app.domain.table.deck',
   'app.domain.personas'`. S2 must append `'app.domain.table.engine'` (+ any siblings) —
   package prefix not enough; missing entry = silently unchecked. Banned in-process:
   `fastapi, starlette, sqlmodel, sqlalchemy` (`:18`).

9. **Simulate wire (S1): domain models ARE the wire; hero-only cards; flat 100bb.**
   `schemas/simulate.py:16-24` `SimulateHandView(hand_no, players, hero)`;
   `api/v1/simulate.py:33-34` `_SEATS=9, _STACK_BB=100.0`; hero = seat 0; button random via
   `secrets.randbelow(9)` (`:79`), advances `+1 mod 9` (`:90`). No pot/board/action wire
   fields yet — S2 is domain-only (roadmap no-go: "no UI here"); engine state should compose
   from `PlayerState`/`Hero` so S9 reuses shapes without DTO drift. Do NOT add wire fields now.

10. **RNG convention: caller-owned injected `random.Random`; per-hand
    `random.Random(secrets.randbits(256))` at API edge; seed logged never on wire.**
    `deck.py:3-5` (docstring pins it), `simulate.py:48-56`, `personas.py:3-6,61-67`. Contrast:
    drill uses module singleton `_RNG` (`drill.py:60`) — simulate deliberately does NOT.
    Every S2 entry point that randomizes takes `rng: random.Random`, no default singleton.

11. **Units/rounding: bb floats everywhere; money 2dp, freq 3dp, SPR 1dp; no Decimal/cents.**
    `spot.py:99-141`, `evaluation.py:36-41`; `round(x,2)` at `scenarios.py:197-247,381-383`;
    EV `round(,2)` freq `round(,3)` (`postflop.py:356,393`). SB 0.5 / BB 1.0; `Stakes.ante=0.0`
    (`spot.py:82-87`). ⚠️ Chip-conservation test must tolerate float rounding (sum unrounded
    internals, round at edges) — introducing Decimal is out of scope.

12. **Personas interface pressure (S4, not S2):** `PersonaAction(name, ActionType)` +
    `PersonaSizing(open_bb, threebet_mult, fourbet_mult)` (`personas.py:35-37,61-91`;
    `content/models.py:116-118,127`). Engine action interface must accept plain
    (seat, ActionType, amount_bb)-style input so S4 translates persona actions without the
    engine knowing personas (S2 no-go: no persona logic).

13. **Test conventions: zero registered pytest markers; heavy stat tests run unmarked, tight
    budget, one pinned seed.** `pyproject.toml` has only `testpaths`; S3 precedent
    `test_personas.py:198-202`: `DEALS=1112`, `random.Random(20260710)`, 0.4s. Roadmap S2
    demands ≥200k seeded deals — ⚠️ 200k `deal_hand` calls run Pydantic validation on 23
    cards each → likely tens of seconds. **Spec decision:** raw-shuffle sampling (bypass
    `DealtHand` construction) vs reduced-N vs a new slow marker.

14. **Repo invariants brushed:** domain purity (contract 8) · results freq+EV never boolean —
    engine does settlement, not grading; no pass/fail shapes · grading stays behind async
    `StrategyProvider` (`providers/base.py:18-29`) · `spot_signature()` frozen — preserve
    incremental CALL `min_bb` semantics (feeds `faced_bet_bucket`) · FE `types.ts`
    hand-maintained — zero FE edits (domain-only) · engine betting-legality rules are game
    mechanics, fine in code; strategy stays in `content/`.

## Integration points

| Seam | Location | Direction |
|---|---|---|
| `deal_hand`/`positions_for_button` | `api/v1/simulate.py:26,57-58`; `tests/test_personas.py:18,207` | engine builds on |
| `Spot.legal_actions` consumers | `postflop.py:323,480,545,726`; `srs.py:71+`; FE `types.ts:29` | engine must emit compatible |
| `Decision` consumers | `providers/base.py:29`; `api/v1/drill.py` | align action-apply |
| `_best7` | `equity.py:71-79` (private) | needs public export decision |
| Future wire seam (S9) | `simulate.py:47-73` `_deal_and_build` | engine state → view later |
| Purity allowlist | `test_domain_purity.py:14-15` | append `app.domain.table.engine` |
| Persona bots (S4) | `personas.py:61` + sizing | persona-agnostic action interface |

## Decisions the S2 spec must freeze (ranked)

1. Public showdown-evaluator export (`_best7` private).
2. Raise-amount semantics (`Decision.size_bb` raise-to vs increment) vs incremental-CALL convention.
3. RNG-suite runtime strategy (raw-shuffle sampling vs reduced-N vs marker infra).
4. Chip-conservation assertion tolerance under float-bb + `round(,2)`.
5. Blind posting as `ActionType.POST` history entries (resolves S1 carry-forward "Pot 0bb").
