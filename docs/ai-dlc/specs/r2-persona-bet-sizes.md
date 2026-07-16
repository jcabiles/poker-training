# Spec — R2: Realistic persona-flavored fixed bet sizes

**Slice:** Epic-2 R2 (`docs/ai-dlc/roadmap/simulate-table.md` line ~414), consumes
`docs/ai-dlc/research/RES-B-bet-sizing.md`. **Contract map:** `docs/ai-dlc/contracts/r2-bet-sizing.md`.
**Interview decisions (2026-07-15):** postflop = **Option B** (`sizing_by_node`); hero = **fix the
single predetermined size now** (sourced from the content baseline hero is graded against).
**Reviewed:** Claude `refuter` (2026-07-15) → `fail`, 5 findings, all folded below (§7 changelog).
Codex Sol review skipped (sandbox blocked its runtime twice; user opted to proceed on the Claude
refuter alone).

---

## 1. Goal (one line)
Replace the min-raise default that drives every bot AND hero bet/raise size with realistic
live-$2/$3 sizes — bots persona-flavored and node-aware, hero on a single realistic predetermined
size — wiring the (already-correct) persona levers through and adding a node-aware postflop lever.

---

## 2. Problem recap (from the contract scan)
- **Preflop:** `play.py:103` sizes every bot BET/RAISE at `la.min_bb` (min-raise). The persona
  `open_bb`/`threebet_mult`/`fourbet_mult` levers exist in `content/models.py` + all 6 packs but are
  **read nowhere** (dead code). Hero's predetermined size is the same engine `min_bb`.
- **Postflop:** bot sizes already read `pf.sizing` (`personas_postflop.py:329`), but the single
  distribution is **node-agnostic** — it can't be small on a dry flop and big on a wet turn.

---

## 3. Files / interfaces to touch

### 3a. New pure domain helper — node classification + fixed sizes
**`backend/app/domain/table/sizing.py`** (NEW, domain-pure — no web/DB import).
- `postflop_node_key(board, legal, *, is_aggressor: bool) -> str` — the single source of the node
  taxonomy, computed from EXISTING classifiers (`app.domain.texture.classify`,
  `turn_card_class`/`river_card_class`) so bots, hero, and (later) graders agree.
  **`is_aggressor` is a REQUIRED input, not derivable from `board`+`legal`** — a checked-around flop
  where a non-aggressor donk-leads has the identical `{CHECK,BET}` legal shape as a true c-bet
  (refuter H2). The caller supplies it (§3d/§3e/§3f compute it from `state.action_history`: hero/bot
  is the aggressor iff they made the last aggressive action on the prior street / are the preflop
  raiser with no intervening lead). Mapping:
  - flop (len board 3) + aggressor → `cbet_mono` if `suitedness == "monotone"`, else `cbet_wet`
    if `wetness == "wet"`, else `cbet_dry`
  - turn (4) + aggressor → `turn_barrel`
  - river (5) + aggressor → `river_value`
  - facing a bet (CALL in `legal`) + choosing RAISE → `raise` (check-raise + facing-bet raise)
  - anything else (incl. non-aggressor betting = donk/lead) → `"flat"` (⇒ flat `sizing` fallback)
- `HERO_NODE_SIZE: dict[str, float]` — hero's single predetermined postflop pot-fraction per node,
  from RES-B §5.1 baselines: `cbet_dry 0.33, cbet_wet 0.75, cbet_mono 0.33, turn_barrel 0.67,
  river_value 0.75, raise 1.0`. (The *node baseline* — the same size R3 offers as one of two options.)
- `preflop_raise_to(sizing, node, *, last_raise_to, limpers, min_bb, max_bb) -> float` — converts a
  persona preflop lever to a legal raise-TO bb, **two-sided clamped to `[min_bb, max_bb]`** (refuter
  L5 — a one-sided up-to-min clamp can leave a size above `max_bb`/outside the jam bracket and the
  engine rejects it, `engine.py:284-287`):
  - `open → sizing.open_bb`
  - `iso` (raise over limper(s), the `vs_limpers` node — refuter M3) → `sizing.open_bb + 1.0*limpers`
    (standard live iso: open size + 1bb per limper), clamped
  - `3bet → sizing.threebet_mult * last_raise_to` (base = **last raise-TO**, i.e.
    `state.current_bet_bb`, per RES-B §4)
  - `4bet → sizing.fourbet_mult * last_raise_to`
  - `5bet → max_bb` (jam)
  - final: `return min(max(computed, min_bb), max_bb)`. When the engine encodes a forced jam
    (`min_bb == max_bb`, `engine.py:170-176`), the clamp collapses to that single legal value.
- `pot_fraction_to_bb(frac, pot_bb, ...)` — reuse the existing conversion the postflop sampler
  already uses (extract/share the one formula; do NOT fork a second).

### 3b. Schema — add the node-aware postflop lever (Option B)
**`backend/app/domain/content/models.py`** — `PersonaPostflop`:
- Add `sizing_by_node: dict[str, dict[str, float]] | None = None`. Each VALUE is a pot-fraction
  bucket distribution (float keys > 0, weights > 0, sum ~1.0); each KEY is a node-taxonomy string
  from §3a (e.g. `"cbet_dry"`) — a plain string, **NOT** a float fraction.
- **Validator (refuter L4):** `_sizing_valid` is a `@field_validator("sizing")` bound to the flat
  field and cannot be attached to `sizing_by_node` directly. Refactor its body into a module-level
  `_validate_bucket_dist(dist: dict[str, float])` and (a) call it from the existing `sizing`
  validator, (b) add a `@field_validator("sizing_by_node")` that, when non-None, iterates the OUTER
  dict and calls `_validate_bucket_dist` on each INNER dict — never parsing the outer node-key
  strings as floats. Unknown node keys are allowed (forward-compat) but each inner dist must be valid.
- **No migration** — persona packs are content JSON, not DB rows. `sizing` (flat) stays as the
  fallback and is unchanged.

### 3c. Content — author `sizing_by_node` (the derivation step)
**`content/personas/{tag,lag,nit,maniac}.json`** — add `sizing_by_node` for the four aggressor
personas. Derive each node's distribution from RES-B §5.1 node baseline shifted by the persona's
§3/§5.2 personality (e.g. TAG `cbet_dry` centered 0.33, `cbet_wet` centered 0.75; maniac shifts
every node up a tier and keeps its `1.5` overbet bucket on wet/river). Document the derivation rule
in a `_rationale`-style comment or the ticket, citing RES-B §5.1/§5.2.
**`content/personas/{calling_station,passive_fish}.json`** — **no `sizing_by_node`** (they rarely
bet/raise; the flat `sizing` fallback is documented as sufficient — RES-B §3 note).
Existing `sizing`, preflop, and lever blocks in ALL six packs stay byte-unchanged.

### 3d. Bot preflop wiring
**`backend/app/domain/table/play.py`** (the `size = la.min_bb …` at line 103).
- **Signature thread (refuter M3):** `_preflop_decision(pack, position, facing, hole, legal, rng)`
  lacks the betting state needed to size. Thread `current_bet_to` (= `state.current_bet_bb`) and the
  limper count into it (the caller `bot_decision` holds `state`). Do NOT recompute facing — reuse
  the existing `_preflop_facing` result (it already returns `"vs_limpers"` as a distinct value).
- Map facing/raise-count → node: unopened raise = `open`; `vs_limpers` = `iso`; a raise over an
  existing raise = `3bet`; over a 3bet = `4bet`; over a 4bet = `5bet`. Then
  `size = sizing.preflop_raise_to(pack.sizing, node, last_raise_to=current_bet_to, limpers=…,
  min_bb=la.min_bb, max_bb=la.max_bb)` instead of `min_bb`. Postflop path (`_postflop_decision`)
  unchanged except via 3e.

### 3e. Bot postflop node-aware sizing
**`backend/app/domain/personas_postflop.py`** — `sample_postflop_decision` (line ~237) currently has
NO aggressor signal (refuter H2), and `board`+`legal` alone cannot separate a c-bet from a
donk-lead. **Add an `is_aggressor: bool` parameter** to `sample_postflop_decision`; the bot caller
(`_postflop_decision` in `play.py`, which has `state`) computes it from `state.action_history` (this
bot is the aggressor iff it made the last aggressive action / is the unchallenged preflop raiser).
Then where it reads `pf.sizing` (line ~329): `node = postflop_node_key(board, legal,
is_aggressor=is_aggressor)`; use `pf.sizing_by_node.get(node, pf.sizing)` when `sizing_by_node` is
present (and the node is not `"flat"`), else `pf.sizing`. The pot-fraction is still **sampled** from
the chosen distribution independently of the made-hand bucket — node selection depends on `board`,
never `hole`, so no strength→size tell is reintroduced (anti-sizing-tell rule 3 preserved; refuter
confirmed).

### 3f. Hero single predetermined size
**Refuter H1 correction:** `LegalAction` has NO `size_bb` field — it is `{action, min_bb, max_bb}`
(`backend/app/domain/spot.py:117`), and the FE derives the size it submits from `la.min_bb`
(`frontend/src/lib/decisions.ts:42-46` sets `size_bb: la.min_bb`). So "override `size_bb` on the
option" is not implementable as originally written. Fix = add a real, explicit suggested-size field
end to end (also the right seam for R3's two-option extension):
- **`backend/app/domain/spot.py`** — add `size_bb: float | None = None` to `LegalAction` (optional;
  `None` = no suggestion, engine behavior unchanged; not hashed by `spot_signature`).
- **`backend/app/services/sim_session.py`** — where hero's legal actions are built for the wire
  (`legal_actions(state)` at ~line 337, inside `_view`), set `size_bb` on the BET/RAISE option(s) to
  hero's realistic single size (compute `is_aggressor` from `state` as in §3e for the postflop node):
  - preflop → content `sizing_bb` for hero's position/node (`rfi.json`/`vs_3bet.json`/`vs_4bet.json`
    via the content registry — the SAME baseline grading uses), then
    `min(max(size, min_bb), max_bb)` (two-sided clamp; the clamped value is what the FE shows and
    submits, so it is always a legal raise).
  - postflop → `HERO_NODE_SIZE[node]` (§3a) pot-fraction → bb via `pot_fraction_to_bb`, clamped.
  - unmapped node / absent content baseline → leave `size_bb = None` ⇒ FE falls back to `min_bb`
    (graceful; no crash).
- **`frontend/src/api/types.ts`** — add `size_bb?: number | null` to the `LegalAction` type
  (hand-maintained per invariant).
- **`frontend/src/lib/decisions.ts`** — for BET/RAISE, submit `la.size_bb ?? la.min_bb` (one-line:
  prefer the suggested size when present). This is the ONLY FE logic change; `SimActionBar` is
  untouched. Hero still submits exactly ONE size — the choice UI is R3.

### 3g. Tests
- `backend/tests/test_personas.py` / `test_personas_postflop.py` — extend.
- New `backend/tests/test_bet_sizing.py` (or similar): the assertions in §6.
- `sim_session` test for hero size override.

---

## 4. Out of scope (hard)
- **Hero size CHOICE / two options** — that is R3. R2 gives hero exactly ONE predetermined size.
- **No bet-size sliders**, no free-form sizing, no rake/ante math.
- **No grader change** — `grade_map` baselines (flop cbet 33%/75%) and the postflop grader merit
  constants are untouched; graders keep reading live `spot.legal_actions`.
- **No preflop RANGE edits** (that is R4) — R2 only touches *sizes*, not which combos open.
- **No `spot_signature()` / `srs.py` change**, no `TAXONOMY_VERSION` bump, no Alembic migration.
- **Station/fish `sizing_by_node`** — deliberately omitted (flat fallback).
- Postflop grader/chart reconciliation (RES-C / R5) — not here.

---

## 5. Constraints (from profile invariants + interview)
- Domain core `backend/app/domain/` stays web/DB-import-free (`sizing.py` is pure;
  `test_domain_purity.py` must pass — `play.py`/`personas_postflop.py` are allowlisted).
- Results stay frequency + EV; EVs labeled **approximate**.
- Grading stays behind the async `StrategyProvider` (untouched).
- Strategy/sizes live in versioned `content/` data — the new lever is DATA; no size is hard-coded
  in code except the hero node-baseline table (`HERO_NODE_SIZE`), which is a documented
  heuristic-baseline constant, acceptable analogously to `grade_map`'s 33/75 baselines.
- **Anti-sizing-tell:** every postflop size stays a frequency-weighted distribution sampled
  independently of hand strength; preflop sizes are fixed per persona/node (a persona opens the same
  size with AA and 72s). No deterministic strength→size leak for bots.
- **Chip conservation:** every produced size is a legal raise (`≥ min_bb`, `≤ max_bb`); engine
  side-pot / no-reopen / incomplete-raise math unaffected; deltas still sum to 0.0.
- CSS/tokens/AA — N/A (no visual change; hero just sees a different default number).
- No auth/accounts (local single-user).

## 5a. Behavioral consequence to accept (flagged, not a bug)
Realistic bot preflop sizes change the pot geometry hero faces, so a bet that used to fall in the
`faced_bet_bucket` "small" band (`srs.py:71`) may now be "big" (or vice-versa). This produces a
*different but still-valid* SRS item for Practice-persisted spots — arguably more correct. R2 does
not touch `srs.py`; Simulate/MW live-sim spots don't persist to Practice SRS, so live grading is
unaffected. Documented so review doesn't read it as a regression.

---

## 6. Verify-by (what `/verify-change` + the new tests check)
**Automated (`./scripts/verify.sh` + `cd frontend && npm run typecheck && npm run build` green):**
1. **Bot preflop per-persona:** maniac opens ~4.5bb, TAG/nit/LAG ~3.0bb, station ~3.5bb, fish
   ~4.0bb — i.e. bot open size == pack `open_bb`, NOT `min_bb`; and persona A ≠ persona B where the
   packs differ. 3-bet/4-bet == `threebet_mult`/`fourbet_mult` × last-raise, clamped legal.
2. **Bot postflop node-aware:** for a persona with `sizing_by_node`, assert the c-bet distribution
   on a DRY flop vs a WET flop differs by a **concrete bound** (refuter L4 — a mere direction check
   is too weak to catch bad authoring): e.g. dry-flop mean pot-fraction ≤ 0.45 AND wet-flop mean
   ≥ 0.6 for TAG, and the two distributions are not equal. A persona WITHOUT `sizing_by_node` falls
   back to flat `sizing` (behavior byte-identical to today). Sizes remain sampled — a direction test
   that FAILS if size is made a deterministic function of the made-hand bucket. Also assert
   `postflop_node_key` returns `"flat"` for a non-aggressor lead (donk) so it never mis-sizes a
   donk as a c-bet.
3. **Hero single size:** the wire `LegalAction.size_bb` for hero's open == content `sizing_bb` for
   the seat (e.g. UTG 3.0bb), not `min_bb`; postflop == the node baseline; and the value is always
   within `[min_bb, max_bb]` (clamped ⇒ `engine.apply` accepts it — a test submits it and asserts no
   `size outside [lo,hi]` reject). An unmapped node leaves `size_bb=None`. Still exactly ONE size per
   action. FE: `decisions.ts` submits `la.size_bb ?? la.min_bb`; `types.ts` carries the new field
   (typecheck green).
4. **Chip conservation / engine:** existing engine + side-pot + persona behavior suites stay green;
   deltas sum to 0.0.
5. **Domain purity + FE build** green; **no migration** added; `TAXONOMY_VERSION` unchanged; pins
   unchanged.

**Manual (boot `./scripts/serve.sh start`, play a Simulate hand):** deal a hand — a maniac in the
pot opens a visibly larger raise than a nit; hero's "raise" button shows a realistic 3bb open, not a
min-raise; a TAG bot c-bets small on a dry board and bigger on a wet one across several hands.

---

## 7. Review changelog — Claude refuter findings folded (2026-07-15)
Refuter verdict `fail`; all 5 findings addressed in-spec (premises it CONFIRMED: dead preflop
levers, `1.5` key legal, texture fields exist, anti-tell preserved, SRS/no-migration correct).

- **H1 — `LegalAction` has no `size_bb`** (hero fix was unimplementable/cosmetic). → §3f rewritten:
  add optional `size_bb` to `LegalAction` (backend `spot.py` + FE `types.ts`), `decisions.ts`
  submits `la.size_bb ?? la.min_bb`. Honest one-line FE touch, not "no FE change"; also the R3 seam.
- **H2 — `sample_postflop_decision` can't tell c-bet from donk-lead** (no aggressor signal;
  board+legal insufficient). → §3a/§3e: `is_aggressor` is a REQUIRED param, computed by the caller
  from `state.action_history`; non-aggressor bet ⇒ `"flat"` node (never mis-sized as a c-bet).
- **M3 — `_preflop_decision` lacks state + `vs_limpers`/iso node unmapped.** → §3d: thread
  `current_bet_to`/limpers in, reuse `_preflop_facing`; §3a adds the `iso` node (open + 1bb/limper).
- **L4 — `_sizing_valid` can't attach to `sizing_by_node`; dry<wet test too weak.** → §3b: refactor
  to a module-level `_validate_bucket_dist` + a dedicated `sizing_by_node` field-validator (never
  parse node-key strings as floats); §6.2 strengthened to concrete mean-pot-fraction bounds.
- **L5 — one-sided preflop clamp** (can exceed `max_bb`/jam bracket → engine reject). → §3a:
  `preflop_raise_to` two-sided clamps `[min_bb, max_bb]`; `min_bb==max_bb` jam collapses correctly.

## 8. Implementation addition — grade_map band reconciliation (user-approved, 2026-07-15)
Surfaced at build: the `grade_map` preflop bands (open `[2.0..canonical]`, 3-bet `≤3×`, 4-bet
`≤2.3×`) were tuned for the min-raise era, so R2's realistic bot sizes (open 3bb, 3-bet 3.5×) fell
OUTSIDE them → hero-facing-an-open became ungradeable (`test_bot_driven_facing_raise_decision_grades`
regressed). Per the interview follow-up decision (widen bands to fit realistic sizes), `grade_map.py`
bands widened: open cap → universal `3.0` (`_STD_OPEN_CAP`), 3-bet → `3.5×` (`_THREEBET_MULT_CAP`),
4-bet → `2.4×` (`_FOURBET_MULT_CAP`). Genuine oversizes (station 3.5 / fish 4.0 / maniac 4.5 opens,
maniac 5.5× 3-bets) still return None — defense ranges shift materially. All pinned oversize tests
stay green (they assert 4.0/12/30bb, far above the new caps). Grading a 3bb open against the
canonical entry stays within the ≈-approximate EV labels (same W1 rationale as the original 2.0
relaxation). This is an additive relaxation (grades ≥ before); no `spot_signature`/`TAXONOMY_VERSION`
change. **New owned file for the slice: `backend/app/domain/table/grade_map.py` (bands only).**
</content>
