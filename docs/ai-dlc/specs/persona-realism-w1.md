# Spec — persona-realism W1 (low-risk wins)

**Roadmap slice:** `docs/ai-dlc/roadmap/persona-realism.md` → W1 (W1-a/b/c).
**Contracts:** `docs/ai-dlc/contracts/persona-realism-w1.md`.
**Theory contract:** `docs/ai-dlc/contracts/persona-realism-theory-contract.md`
(softmax law · FIT SEED discipline · §7 denominator unification).
**Fit loop:** `docs/ai-dlc/contracts/persona-realism-fit-loop.md`.

**Goal (one line):** three grounded, contained bot-realism fixes on
`personas_postflop.py` — floor the middle-pair river value-bet, fix the
same-street re-raise faced-price denominator (consuming the merged W0-a helper),
and tighten made-value aggression as opponents rise.

**Packaging:** ONE branch `feat/persona-realism-w1`, three commits (A → B → C,
serial on the shared file), ONE PR. Codex Sol + Claude refuter +
persona-realism-theory-reviewer fan-in on THIS spec before build.

**Out of scope:** any band re-anchor (WTSD/AF — deferred to W4-b, single
re-anchor rule); the raise-floor P2a set; sizing distributions; OVERPAIR_TPTK
value damping; 5+way multiway magnitudes; the commitment/EV work (W2); position/
texture context (W3). No new metric framework (W0-b already shipped six).

---

## Constraints (from profile invariants)
- Domain purity: no web/DB import in `app/domain/` (test-enforced).
- Softmax law preserved: clamp ≥0 → normalize → `rng.choices`. No argmax.
- First `rng.choices` call stays the action draw (capture-rng + node-trace key on it).
- Default-off byte-identity: new sampler kwargs default to today's formula;
  harness + direct unit tests unchanged. Only engine + estimator opt in.
- `spot_signature()` frozen; SRS `spr_bucket` untouched; anti-sizing-tell intact.
- Every magnitude is a FIT SEED tuned to a W0 metric + sanity-checked on the
  node-trace pack (`tests/node_trace.py`), not a drop-in constant.

---

## Slice A — River one-pair BET floor (MIDDLE_PAIR only) · fixes F6

**Change (`personas_postflop.py`):**
- Add structural constant near `_RIVER_RAISE_FLOOR`:
  `_RIVER_BET_FLOOR = (StrengthBucket.MIDDLE_PAIR,)` with a comment: a middle
  pair on the river is a bluff-catcher, never a value bet, under a conservative
  HU/balanced-villain DEFAULT (it CAN value-bet vs capped/station ranges — a rank
  approximation, not a theorem; strictly NARROWER than the raise-floor which also
  covers TOP_PAIR/OVERPAIR).
- In the unopened / matched-with-option branch, NON-bluff path (the `else:` at
  ~519), when `agg_action is ActionType.BET and street is Street.RIVER and bucket
  in _RIVER_BET_FLOOR`: set `agg_merit = 0.0`. Placed alongside the existing
  river RAISE floor (~525-530), as a sibling condition for the BET case.

**Must NOT:** touch `_RIVER_RAISE_FLOOR`; floor TOP_PAIR/OVERPAIR BET; fire
pre-river; edit any band.

**Test to SPLIT (theory-reviewer H1 — required, this is the ONLY sanctioned
early-wave unit-assertion edit per theory-contract §7, NOT a band re-anchor):**
`test_river_check_raise_branch_floored_bet_untouched`
(`tests/test_personas_postflop.py`) currently loops `_ONE_PAIR_FLOOR =
(MIDDLE_PAIR, TOP_PAIR, OVERPAIR_TPTK)` and asserts the unopened river BET is
byte-identical river-vs-streetless for ALL THREE — Slice A breaks the MIDDLE_PAIR
iteration. Split it: MIDDLE_PAIR unopened river BET now asserts `P(BET) == 0`
(floored); TOP_PAIR + OVERPAIR_TPTK keep the byte-identical-to-streetless
assertion. Name this test explicitly in the ticket; the implementer must not read
its failure as a regression.

**Verify-by:**
- New/split unit assertions: a MIDDLE_PAIR unopened river BET spot → sampled
  `P(BET) == 0` (floored); a TOP_PAIR and an OVERPAIR_TPTK unopened river BET spot
  → `P(BET) > 0` (untouched); a MIDDLE_PAIR unopened **flop/turn** BET → unchanged
  vs pre-change (floor is river-gated).
- Existing suite byte-identical except (a) the intended river MIDDLE_PAIR shift
  and (b) the named split assertion above. No band re-anchor.

---

## Slice B — faced_frac increment fix (ENGINE-ONLY) · fixes F9 · depends W0-a

> **Scope collapsed after the fan-in (Codex #1, verified against code).** The
> range estimator builds `LegalAction(action=k)` with `min_bb=None`
> (range_estimate.py:276), so its faced_frac NUMERATOR (`to_call`) is
> structurally **0** → estimator faced_frac is always 0 (SMALL) regardless of the
> denominator. The denominator fix is therefore **inert for the estimator** —
> threading the increment into `_Ctx` would be dead code. And the statistical
> harness has its OWN `_postflop_decision` wrapper
> (tests/test_personas_postflop.py:1196) that does NOT pass the new kwarg → it
> stays on the legacy formula → **bands byte-identical, no re-anchor** (honors the
> W1 no-go). So Slice B is a **production-engine-only** change proven by dedicated
> unit tests, NOT an estimator/harness/`_Ctx` change.

**Change (`personas_postflop.py`):**
- Append a trailing param `latest_aggressor_contribution_bb: float | None = None`
  to `sample_postflop_decision` — **NO `*` separator** (the signature has none;
  do not convert existing params to keyword-only — refuter L1). Default `None`
  reproduces today's formula for every un-opted-in caller (harness, estimator,
  direct unit tests) → byte-identical.
- Replace the faced_frac line (:492):
  ```python
  if latest_aggressor_contribution_bb is None:
      faced_frac = to_call_bb / max(pot_bb - max(current_bet_to, to_call_bb), 0.01)
  else:
      faced_frac = to_call_bb / max(pot_bb - latest_aggressor_contribution_bb, 0.01)
  ```
  The NUMERATOR stays `to_call_bb` (the facing seat's call increment — the correct
  pot-fraction numerator; only the denominator was ever wrong — theory M3). This
  is a denominator-only fix.
- Rewrite the ":484-490 Known limitation" comment. Fix the DIRECTION: the legacy
  formula subtracts the whole bet-TO (`current_bet_to`), which is LARGER than the
  aggressor's true increment when the aggressor already had street chips, so the
  denominator is too small and the legacy formula **OVERSTATES** faced_frac →
  **over-folds** (Codex #3; the current ":487 understates" wording is backwards —
  empirically old_frac 1.5 > new_frac 1.2 at the probe spot). State it is now
  FIXED when the caller supplies the increment; drop the "Epic-4 follow-up"
  deferral (theory L4). The legacy branch remains only for un-opted-in direct
  callers, whose over-subtraction is the documented approximation THERE.

**Divergence scope (Codex #2 — wider than "self-re-raise"):** the two formulas
diverge whenever the **latest aggressor had ANY prior street investment** before
their bet/raise — a self-re-raise (bet then raise) OR a **back-raise after
calling** (call then raise, e.g. a check-raise or squeeze by a prior caller).
Both are corrected in the same (less-over-fold) direction. Fresh aggression
(aggressor with zero prior street chips) is byte-identical — empirically
re-verified by the refuter across fresh-bet / fresh-raise / multiway / incomplete
all-in cases.

**Engine wiring (`table/play.py`):**
- Import `pot_before_current_aggression` from `app.domain.table.sizing`.
- In the postflop branch (~198-214), compute `contribution =
  pot_before_current_aggression(state.action_history,
  state.street).latest_aggressor_contribution_bb` and thread it through
  `_postflop_decision` → `sample_postflop_decision(
  latest_aggressor_contribution_bb=contribution)`. `_postflop_decision` gains a
  forwarded param. This is the ONLY behavior change in the slice.

**Estimator + harness: UNTOUCHED** (inert / separate wrapper — see the scope box).

**Discovered follow-up (document, do NOT fix here):** the estimator is
faced-price-BLIND (numerator 0) — a latent approximation predating W1. Giving it
a real `to_call` (reconstruct `min(cur - inv_street[s], stacks[s])` into `_Ctx`)
is a separate, higher-blast-radius slice that would move range estimates and need
its own re-anchor. Out of W1 scope; note it in the roadmap's Next/Later.

**Must NOT:** change fresh-aggression behavior; touch the estimator or harness
wrapper; insert an rng draw; touch sizing.

**Verify-by (dedicated unit tests — Slice B's line of defense, refuter L2):**
- NEW `test_faced_frac_selfreraise_folds_less`: at a bucket-STRADDLING
  self-re-raise spot (verified: SB bet 2, BB raise 6, SB re-raise 13 → legacy
  faced_frac 0.875 LARGE vs fixed 0.700 MEDIUM), compare the sampler's exact
  captured P(FOLD) weights legacy (no kwarg) vs fixed (kwarg) — assert fixed <
  legacy. Use captured weights, not sampled counts.
- NEW `test_faced_frac_backraise_after_call_corrected`: a call-then-raise
  (back-raise) geometry — assert `contribution < current_bet_to` and the fold
  weight drops (Codex #2 coverage).
- NEW `test_faced_frac_fresh_raise_byte_identical`: a fresh raise (0-prior-chip
  raiser) — sampler output identical with vs without the kwarg.
- NEW wiring assertion: drive a real hand via `apply()` to a self-re-raise faced
  spot; assert `pot_before_current_aggression(...).latest_aggressor_contribution_bb
  < state.current_bet_bb` (the fix is active on the engine path).
- Existing faced_frac / fresh-raiser tests stay green, byte-identical; full
  suite (879 baseline) green.

---

## Slice C — Multiway made-value tightening · fixes F13 · directional

**Change (`personas_postflop.py`):**
- Add FIT SEED constants near `_MW_CATCH_TIGHTEN`:
  `_MW_VALUE_DAMP = 0.8` (per-added-opponent geometric damp on made-value
  aggression — the value-side mirror of `multiway_bluff_damp`/`_MW_CATCH_TIGHTEN`;
  RES-D §6 direction-only, modest by design) and `_MW_VALUE_CAP = 3` (labeled
  4-way tier; 5+way unresearched → Later) and
  `_MW_VALUE_BUCKETS = (StrengthBucket.TOP_PAIR, StrengthBucket.MIDDLE_PAIR)`.
- In the unopened non-bluff aggressive path (~519-521), after computing the made
  `agg_merit`, **gated on `agg_action is ActionType.BET`** (Codex #4 — the `else:`
  block also handles the matched-with-option check-RAISE; only the unopened BET is
  in scope): `if agg_action is ActionType.BET and bucket in _MW_VALUE_BUCKETS:
  agg_merit *= _MW_VALUE_DAMP ** min(max(opponents - 1, 0), _MW_VALUE_CAP)`.
- **Serial-authoring note (refuter L3):** author this against Slice A's
  already-mutated file (they touch the same `else:` block; the two edits commute —
  floor-to-0 and damp are order-independent — but the line numbers here are
  pre-Slice-A).
- **FIT SEED honesty (theory M2):** `0.8` is an UNFIT directional seed left
  un-tuned *because no multiway made-value metric is live* (W0-b shipped six; none
  covers this) — NOT an observed 20%-per-opponent frequency drop. Under softmax
  normalization (check_merit fixed) the observed bet-rate change is far smaller
  than `0.8**k` implies. Gate is DIRECTIONAL-only per the Metric-DoD escape hatch.

**Bucket-scope decision (flagged for reviewers):** the damp is scoped to the
THIN-value buckets (TOP_PAIR, MIDDLE_PAIR) — the opponent-count-sensitive ones —
and deliberately NOT to MONSTER/TWO_PAIR_PLUS/OVERPAIR_TPTK (strong value you bet
multiway regardless; damping them would make monsters check too often multiway,
a poker-incorrect regression). The roadmap's "made-value aggression" phrasing is
generic; this narrowing is the grounded reading (mirrors the W3 overcard slice's
MIDDLE_PAIR/TOP_PAIR-only restraint). **If the fan-in prefers all made buckets,
fold that instead.**

**Must NOT:** move HU (`opponents == 1` → exponent 0 → byte-identical); extend
past the 4-way cap; assert any multiway value magnitude/level (direction only).

**Verify-by:**
- Monotone test via EXACT captured P(BET) weights (Codex #6 — NOT sampled
  counts, which vary with RNG): capture the sampler's first `rng.choices` weights
  at `opponents` 1→2→3→4 for a TOP_PAIR/MIDDLE_PAIR unopened spot; assert
  normalized P(BET) is non-increasing and plateaus at opponents≥4 (verified
  numerically: 0.55→0.494→0.439→0.385, flat past 4).
- HU byte-identity: `opponents == 1` → exponent 0 → every existing HU spot + the
  full suite unchanged.
- Node-trace multiway spot (`flop_multiway_toppair`) still well-formed.

---

## Verify-by (whole wave)
`cd backend && source .venv/bin/activate && ruff check . && python -m pytest -q`
all green (**879 baseline** + the new W1 tests) — use `python -m pytest` (bare
`pytest -q` errors `ModuleNotFoundError: No module named 'tests'`; refuter note),
or `./scripts/verify.sh`. Domain-purity test green, node-trace tests green,
`cd frontend && npm run typecheck` unaffected (no API/type change). Per-slice:
each commit leaves the suite green (serial, not stacked-broken).

---

## Review dispositions — fan-in 2026-07-24 (refuter + theory-reviewer + Codex Sol)

- **theory H1 (HIGH)** — Slice A breaks an unnamed byte-identity test → FOLDED:
  names + splits `test_river_check_raise_branch_floored_bet_untouched`.
- **Codex #1 (HIGH)** — estimator numerator is structurally 0 → FOLDED: Slice B
  collapsed to engine-only; `_Ctx`/estimator threading DROPPED (dead code);
  estimator price-blindness recorded as a deferred follow-up.
- **Codex #2 (MED)** — divergence wider than self-re-raise (back-raise-after-call)
  → FOLDED: scope wording widened + a back-raise test added.
- **Codex #3 (MED)** — direction backwards (OVERSTATES) → FOLDED (comment rewrite;
  confirmed 1.5→1.2).
- **Codex #4 (MED)** — Slice C `else:` also damps check-RAISE → FOLDED (gated BET).
- **Codex #6 / refuter (LOW)** — sampled monotone test RNG-flaky → FOLDED (exact weights).
- **theory M2/M3/L4 (MED/LOW)** — label 0.8 unfit seed; numerator stays `to_call`;
  drop "Epic-4 follow-up" → all FOLDED.
- **refuter L1 (LOW)** — no `*` separator → FOLDED (trailing param).
- **refuter L2 (LOW)** — no node-trace self-re-raise spot → ACCEPTED gap; mitigated
  by 4 dedicated unit tests; node-trace plumbing deferred.
- **refuter L3 (LOW)** — Slices A & C share the block → FOLDED (serial-authoring note).
- **refuter verdict: PASS** (byte-identity/`_Ctx`/rng-ordering/monotonicity
  empirically re-verified; baseline 879 passed). **theory: GO after H1.** **Codex:
  3 real corrections folded.**
