# W2 — persona identity + EV correctness (delta spec)

**Roadmap slice:** `docs/ai-dlc/roadmap/persona-realism.md` → W2 (two slices, one PR).
**Depends-on (shipped):** W0-a (`pot_before_current_aggression`), W0-b (D4 size-bucket FtC curve metric), W1 (#94).
**Goal:** give personas a real identity axis (decouple *how loose they call* from *how much size scares them*), and make the interim-EV commit/draw math correct (stop forced air-jams and weak-draw over-chasing).

## Out of scope
- No population WTSD/AF band re-anchor (frozen to the single W4-b re-anchor). W2 re-anchors only **lever-identity** unit pins (monotonicity + α-ceiling), never the population bands.
- No equity SOLVE — heuristic rule-of-4-and-2 proxy only; its calibration is a Later item (H7).
- No position/street/texture context (that's W3). No commitment-brake stack-depth work (W4).
- The estimator's faced-price reconstruction stays on Later (spun out in W1).

## Files to touch
- `backend/app/domain/content/models.py` — `PersonaPostflop`: add two OPTIONAL levers (`call_looseness`, `size_elasticity`), both `None` default.
- `backend/app/domain/personas_postflop.py` — the hotspot. W2-a: resolve the two levers (fallback to `stickiness`), split their two uses. W2-b: refine the SPR-commit block + draw-bonus damp.
- `content/personas/*.json` — set `call_looseness` / `size_elasticity` for the personas whose identity the split unlocks (station, fish; others may stay unset = byte-identical).
- `backend/tests/test_personas_postflop.py` — rewrite monotonicity pins onto the new levers; add W2-a identity tests + W2-b commit/draw-gate tests.
- Seeded fixtures (golden AF/WTSD, `coverage_baseline.json`, limper belt) — re-record per-slice under the established protocol (bands stay frozen). See "Fixtures".

---

## Slice W2-a — elasticity split (`stickiness` → `call_looseness` + `size_elasticity`)

**Problem.** `stickiness` is welded: it scales BOTH the flat CALL merit (line 531, `pf.stickiness`) AND the price-response exponent (line 522/414, `stickiness**(-DAMP)`). So you cannot build a **station that is inelastic-but-loose** (calls any size) distinct from a **fish that is elastic-but-scared** (fit-or-fold) — the one axis that defines their difference is a single dial.

**Solution.**
- Add two OPTIONAL pack levers:
  - `call_looseness` → the flat CALL-merit multiplier (today's line 531 use). Unset → falls back to `stickiness`.
  - `size_elasticity` → drives the `_price_factor` exponent. Unset → falls back to the legacy `stickiness`-derived exponent.
- Resolve at the top of the decision body: `looseness = pf.call_looseness if pf.call_looseness is not None else pf.stickiness`. For the price exponent, branch on whether elasticity was explicitly set (see below); thread the resolved exponent into `_price_factor` and `looseness` into the call-merit line.
- **Exponent formula — legacy vs opt-in branch (fixes reviewer #1 crash + direction reversal).** The legacy exponent `SENSITIVITY * stickiness**(-DAMP)` is INVERSE (higher stickiness → smaller exponent → *less* price response) — reusing it for `size_elasticity` would both crash at 0 (`0**-0.15` → `ZeroDivisionError`) AND reverse the intended meaning. So:
  - `size_elasticity is None` → `exponent = SENSITIVITY * stickiness**(-DAMP)` (legacy; byte-identical to today).
  - `size_elasticity` set → `exponent = SENSITIVITY * size_elasticity` (DIRECT: `0` → exponent 0 → flat/size-blind; higher → steeper). 0 is safe (no negative power). Intuitive scale: `≈1.0` reproduces a normal price response (exponent ≈ 2.2), `0` is size-blind, `>1` is scared.
- **Keep the 4 α buckets** — the continuous-price reformulation is DESCOPED (reviewer #2: byte-identity risk, no W2 payoff; the direct-exponent split already delivers station-flat / fish-steep).
- Content: station `size_elasticity = 0.0` (size-blind) + `call_looseness` ≈ current stickiness; fish `size_elasticity ≈ 1.2–1.5` (scared) + moderate `call_looseness`. Others: leave unset (byte-identical) unless a clear identity gain (each set value re-records fixtures).

**Byte-identity invariant.** A pack with neither new lever set is **byte-identical** to today (looseness resolves to `stickiness`; exponent uses the legacy branch). Verified via captured NORMALIZED weights + seeded decision stream (not "same stream" informally — reviewer #2).

**Monotonicity pins (rewrite onto new levers).**
- `call_looseness↑` never lowers CALL freq (replaces `test_monotonicity_stickiness_never_lowers_call_freq`; raise `call_looseness`, hold `stickiness` constant so the elasticity fallback stays fixed and the call axis is isolated — reviewer #9).
- `size_elasticity↑` never lowers FOLD freq vs a bigger size (higher elasticity ⇒ steeper fold-rise with size, via the direct exponent).
- The `_price_factor` monotone-non-decreasing-across-SMALL→OVERBET property still holds for any fixed exponent.

**Pass/fail (executable — reviewer #7).**
- Station config (`size_elasticity = 0.0`): fold-rate at OVERBET − fold-rate at SMALL ≈ 0 (|Δ| < a small tol, seeded n≥500) — flat curve.
- Fish config (`size_elasticity ≈ 1.3`): fold-rate at OVERBET − fold-rate at SMALL ≥ a positive slope bound (seeded n≥500) — steep curve.
- `call_looseness↑` never lowers call freq (seeded).
- `size_elasticity = 0.0` unit test: `_price_factor`/exponent path does NOT raise, returns a size-flat factor.
- Un-opted-in packs byte-identical: captured normalized weights + seeded decision identical for a persona with neither lever set.

---

## Slice W2-b — semi-bluff draw-jam gate + weak-draw equity gate

**Problem.** Two coupled EV bugs in the commit/draw path:
- **F5 (forced air-jam):** the SPR-commit block (lines 577-588) zeros FOLD merit and boosts agg for ANY hand with `_RUNG[bucket] ≥ OVERPAIR_TPTK OR draw is STRONG`. A naked air+strong-draw is force-jammed with no fold mass — a no-fold commit that ignores price.
- **F7 (weak-draw over-chase):** `_DRAW_CALL_BONUS[WEAK] = 0.20` is ~2.5× the AIR call base (0.08); a fold-side brake alone can't overpower it, so bots chase weak draws too far.

**Solution (directional, heuristic — F\* dropped per owner decision + reviewers #4).**
Both reviewers flagged the roadmap's "set fold merit so normalized fold prob ≈ F\*" as a conflation: semi-bluff F\* is the OPPONENT's required fold frequency, but the fold merit controls the BOT's OWN fold probability — different quantities. Owner decision: **directional own-action policy, drop forced-F\***. Rigorous F\* → Later.

- **Equity proxy** `_draw_equity(draw, board)` (heuristic, no solve; rule-of-4-and-2). Derive street from `len(board)` — do NOT depend on the optional `street` kwarg being passed (reviewer #7):
  - STRONG draw (~8–9 outs): flop (len 3) ≈ 0.36 (2 cards), turn (len 4) ≈ 0.18 (1 card).
  - WEAK draw (~4 outs): flop ≈ 0.16, turn ≈ 0.08.
  - River (len 5): draw is always NONE (no draw equity) — the made-hand path governs.
- **Made-hand bypass (reviewer #6 + #3):** for `_RUNG[bucket] ≥ OVERPAIR_TPTK`, resolve `e = 1.0` and apply the EXISTING zero-fold / agg-boost transform **unchanged** — bypass ALL W2-b draw damping (an overpair can also carry a draw; damping its bonus would break byte-identity). The value-jam path is byte-identical to today.
- **T1 value-commit gate (draw side only):** compute the value-commit threshold from the already-corrected faced fraction — `threshold = faced_frac / (1 + 2·faced_frac)` (= `B/(P+2B)`; a faced-price CALL-commit proxy for the stack-off, NOT a full jam-EV solve — labeled heuristic, uses only existing inputs, reviewer #3). Zero FOLD merit ONLY when the draw's `e ≥ threshold`. Below threshold, do NOT zero fold — the existing price-aware fold merit (`_FOLD_BASE * _price_factor`) stands, already shaped by size + persona elasticity.
- **B5b draw-bonus damp (below T1):** damp `_DRAW_CALL_BONUS` (and draw raise/agg bonus) by commitment `c` when the draw is NOT value-committed, so a naked weak draw stops stacking off. Applied to the CALL/RAISE side only; fold merit is left to the existing price machinery.
- **The 3×-pot threshold is 42.9%** (`faced_frac = 3` → 3/7), NOT 60%. STRONG draw (0.36) < 0.429 ⇒ CAN fold to a 3×-pot overbet (fold no longer zeroed); the SAME draw pot-committed (small faced_frac → low threshold, 0.36 ≥ threshold) still JAMS.

**Pass/fail (executable — reviewer #7; use jam-only / fixed legal fixtures + seeds).**
- STRONG draw pot-committed (low SPR, small faced_frac): fold prob = 0 (inside T1, fold zeroed) → still commits.
- Same STRONG draw vs a 3×-pot overbet in the commit regime: fold prob > 0 (was exactly 0) AND strictly greater than the pot-committed case — measured over seeded n.
- Naked WEAK draw at high commitment: stack-off (BET/RAISE/CALL) frequency strictly LOWER than today (B5b damp), seeded.
- Made hand ≥OVERPAIR at/below `spr_commit`: captured normalized weights BYTE-IDENTICAL to today (bypass verified).

---

## Contracts touched (brownfield)
- **Softmax law (frozen):** merits clamp ≥0, normalize, `rng.choices` always. Every W2 magnitude is a FIT SEED, not an observed frequency. No argmax.
- **First `rng.choices` = the action draw:** neither slice may insert an rng draw before it (capture-rngs / node-trace key on it). W2-a/b add no new rng draw.
- **Default-off byte-identity:** new levers default to `stickiness`; new commit logic must reduce to today's behavior for the un-gated case (verify: a made hand ≥OVERPAIR pot-committed still commits identically).
- **`spot_signature()` frozen** — untouched.
- **Domain purity** — no web/DB imports in the changed domain files.
- **`PersonaPostflop` schema:** the two new fields are OPTIONAL (`| None = None`) so every existing `content/personas/*.json` still validates without edits. No Alembic migration (this is content-model, not DB).

## Fixtures (re-record protocol, established P1/P2a/W1)
Both slices move bot behavior when a persona opts in / the commit path changes ⇒ shared-rng stream displacement ⇒ the three seeded fixtures drift. Re-record per-slice, documented in each fixture's docstring, under the standing authorization. **Tolerance BANDS stay frozen to W4-b** — this is a seeded-fixture re-record, NOT a population-band re-anchor. Coverage RATIO is the invariant (must hold/improve vs the immutable `persona-realism-start` floor 28.3%).
- If a slice sets NO content lever and the commit path doesn't fire in the deterministic sweep, that fixture stays byte-identical (like W1-b for coverage) — re-record only what actually moves.
- **Per-persona guard (reviewer #8):** before overwriting any fixture, regenerate and diff OLD-vs-new restricted to the personas with NEITHER new lever set (W2-a) / whose commit path did not change (W2-b); assert that subset is byte-identical FIRST, then overwrite the full fixture. This prevents a byte-identity break in an un-opted-in persona from being silently absorbed into the new baseline.

## Verify-by (end-to-end)
- `./scripts/verify.sh` green (backend tests + boot probe).
- `cd backend && ruff check .` clean.
- Domain-purity + node-trace + capture-rngs suites green.
- New W2-a identity tests (station-flat / fish-steep D4 curves; looseness monotone) + W2-b commit/draw-gate tests pass.
- Un-opted-in persona byte-identity spot-check passes (a persona with neither new lever set samples an unchanged decision stream).
