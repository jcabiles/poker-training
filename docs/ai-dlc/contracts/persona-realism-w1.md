# Contract map — persona-realism W1 (behavior-changing wave)

Read-only scout of the invisible contracts the three W1 slices touch. Situated
inside `docs/ai-dlc/roadmap/persona-realism.md` (W1 — low-risk wins). All three
slices own `backend/app/domain/personas_postflop.py` ⇒ they run **serially** on
that spine (one W1 branch, three commits, one PR).

## Integration points (callers of the hotspot)

`sample_postflop_decision(pack, hole, board, legal, pot_bb, stack_bb, opponents,
rng, *, noise, current_bet_to, is_aggressor, street)` has **three** caller
classes — the contract every slice must preserve:

1. **Live engine** — `table/play.py:203` `_postflop_decision(...)` → passes
   `current_bet_to=state.current_bet_bb`, `is_aggressor`, `street`. Has
   `state.action_history` + `state.street` in scope (already calls
   `last_aggressor_position(state.action_history)` at play.py:202). This is the
   ONLY path that must change behavior.
2. **Range estimator** — `table/range_estimate.py:278` `_postflop_action_dist`
   drives the sampler through a `_CaptureRng` that records the FIRST `choices()`
   call (the action distribution) and returns `population[0]`. Builds context
   from `_Ctx` (range_estimate.py:86) reconstructed by `_replay_contexts`
   (chip-walk of `PublicActionHistory`). Estimator output must stay
   byte-identical EXCEPT on the exact spots a slice intentionally corrects.
3. **Statistical harness + unit tests** — call the sampler directly with a real
   seeded `random.Random`, WITHOUT the new kwargs. Must be byte-identical.

## Invariant contracts (must not break)

- **Softmax law** — merits clamp ≥0, normalize by sum, ALWAYS `rng.choices`
  (never argmax). A merit multiplier ≠ an observed-frequency change. Every
  magnitude is a FIT SEED tuned to a measured stat.
- **First-rng-call = action draw** — the estimator's `_CaptureRng` and the
  node-trace pack key on the action `choices()` being the sampler's FIRST
  `rng.choices`. No slice may insert an rng draw before it.
- **Default-off byte-identity** — any new sampler kwarg defaults to the value
  that reproduces today's formula, so un-opted-in direct callers (harness/tests)
  are byte-identical. Only the engine + estimator opt in.
- **Anti-sizing-tell** — strength never steers the size draw (value hands keep
  the authored sizing distribution). None of these slices touch sizing.
- **Domain purity** — `app/domain/` has no web/DB import (test-enforced).
- **`spot_signature()` frozen** — untouched (no SRS surface here).
- **Frozen SRS `spr_bucket`** — the SPR-commit block uses LIVE `stack/pot`, never
  `srs.spr_bucket`. Untouched.

## Per-slice contract notes

### Slice A — river one-pair BET floor (MIDDLE_PAIR only)
- Touches the **unopened / matched-with-option** branch (personas_postflop.py
  ~514-532), the NON-bluff path only (MIDDLE_PAIR is never a `bluff_cell`; that
  is AIR/ACE_HIGH). The existing P2a river logic already floors the matched RAISE
  (check-raise) for `_RIVER_RAISE_FLOOR = (MIDDLE_PAIR, TOP_PAIR, OVERPAIR_TPTK)`
  but the comment at :522-524 explicitly leaves the unopened BET legal. This
  slice adds a NARROWER floor `_RIVER_BET_FLOOR = (MIDDLE_PAIR,)` on the unopened
  BET only.
- **Contract:** must NOT touch `_RIVER_RAISE_FLOOR` or its set; must NOT floor
  TOP_PAIR/OVERPAIR BET (they stay thin-value legal); gated on `street is
  Street.RIVER` so pre-river is byte-identical; no band edits (WTSD/AF re-anchor
  deferred to W4).

### Slice B — faced_frac increment fix (consumes W0-a) + estimator parity
- Touches the **facing-chips** branch, personas_postflop.py:491-492:
  `faced_frac = to_call_bb / max(pot_bb - max(current_bet_to, to_call_bb), 0.01)`.
  The `max(current_bet_to, …)` over-subtracts on a **self-re-raise** (aggressor
  raising over their own earlier same-street bet: `current_bet_to` includes
  their pre-raise street chips), understating `faced_frac` by up to one bucket →
  over-fold. The backwards "Known limitation" comment at :484-490 must be fixed.
- **Fix mechanism:** new sampler kwarg `latest_aggressor_contribution_bb: float
  | None = None`. `None` → legacy formula (byte-identical for harness/tests).
  Provided → `faced_frac = to_call_bb / max(pot_bb - contribution, 0.01)`, where
  `contribution` is the W0-a
  `pot_before_current_aggression(...).latest_aggressor_contribution_bb`.
- **Byte-identity proof (why this is genuinely low-risk):** for a fresh bet or a
  raise by a player with ZERO prior street chips, `contribution ==
  current_bet_to == to_call`, so `pot_bb - contribution == pot_bb -
  max(current_bet_to, to_call)` — **identical**. The two formulas diverge ONLY on
  self-re-raise, which is exactly the bug. So every non-self-re-raise engine AND
  estimator spot is unchanged; only self-re-raise lines are corrected.
- **Engine wiring:** play.py computes `contribution =
  pot_before_current_aggression(state.action_history, state.street)
  .latest_aggressor_contribution_bb` and threads it through `_postflop_decision`.
- **Divergence scope (fan-in Codex #2):** the fix bites whenever the latest
  aggressor had ANY prior street investment — self-re-raise (bet→raise) OR
  back-raise-after-call (call→raise). Fresh aggression is byte-identical.
- **Direction (fan-in Codex #3):** the legacy formula OVERSTATES faced_frac (it
  subtracts the whole bet-TO, larger than the true increment) → over-folds. The
  ":487 understates" comment is backwards and must be fixed.
- **Estimator — NO CHANGE (fan-in Codex #1, verified):** the estimator builds
  `LegalAction(action=k)` with `min_bb=None` (range_estimate.py:276), so its
  faced_frac NUMERATOR (`to_call`) is structurally 0 → faced_frac always 0 (SMALL);
  the denominator fix is INERT there. Threading the increment into `_Ctx` would be
  dead code, so `_Ctx`/`_replay_contexts` are NOT touched (and there was no
  positional-unpack risk — the sole `_Ctx(...)` site is all-keyword). The
  estimator's faced-price-blindness is a pre-existing approximation → recorded as a
  deferred follow-up, out of W1 scope.
- **Harness — NO CHANGE:** the statistical harness has its own `_postflop_decision`
  wrapper (test_personas_postflop.py:1196) that never passes the kwarg → legacy
  formula → bands byte-identical (honors the no-band-re-anchor no-go). The fix is
  proven by dedicated unit tests, not a band shift.

### Slice C — multiway made-value tightening
- Touches the **unopened non-bluff** aggressive merit (personas_postflop.py:520),
  mirroring the existing `bluff_mass *= multiway_bluff_damp ** max(opponents-1,0)`
  (bluff side, :446) and `_MW_CATCH_TIGHTEN ** max(opponents-1,0)` (fold side,
  :497). This closes the value side (F13).
- **Contract:** HU (`opponents == 1`) → exponent 0 → byte-identical (invariant:
  the harness/estimator HU spots must not move). Capped at a labeled 4-way tier
  (exponent clamps at 3 added opponents; 5+way unresearched → Later). Monotone
  non-increasing in `opponents` (pass/fail test). Directional-only — no multiway
  value metric asserted (none exists yet).
