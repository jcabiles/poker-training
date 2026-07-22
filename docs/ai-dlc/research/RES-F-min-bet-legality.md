# RES-F — Min-bet-legality root-cause ("20BB pot but hero can only bet 1BB")

**Spike, Epic 4 (bot-math-fix). Output = decision doc + fix options. NO app code.**
Created 2026-07-21.

---

## 1. Reproducing condition
Hero is on a postflop street where the pot is large (e.g. ~20BB) but hero's node is **not an
aggressor c-bet/barrel/raise node** — e.g. hero cold-called preflop and now has the option to
**donk/lead** the flop OOP, or a probe/delayed-c-bet/checked-to spot. Hero's bet UI offers only
a **~1BB minimum bet**, with no pot-proportional size.

## 2. Root cause (exact, from the code) — **[CONFIRMED]**
Not an illegality — a degenerate **offer**. Two layers:

1. **`sim_session.py::_hero_postflop_size_bb` (lines 354–362).** Hero's predetermined size is
   `HERO_NODE_SIZE.get(postflop_node_key(...))`. `HERO_NODE_SIZE` (`sizing.py:22`) has **only 6
   keys**: `cbet_dry, cbet_wet, cbet_mono, turn_barrel, river_value, raise`. Any other node —
   donk/lead, probe, delayed c-bet, hero-not-the-aggressor — is a `.get()` **miss → returns
   None**. The docstring says it outright: *"None for a node without a baseline (donk/lead) ⇒ FE
   falls back to min-raise."*
2. **`engine.py::legal_actions` (lines 187–192).** The BET `LegalAction` is built with
   `min_bb = round(min(state.min_raise_to_bb, all_in_to), 2)`. Postflop `min_raise_to_bb`
   resets to `_BB` (= 1BB; `engine.py:231,241`). So the engine's minimum legal bet is **1 big
   blind** — which is the *correct* NLHE rule (min bet = one big blind, independent of pot).

**Net:** when layer 1 returns None, the FE has no predetermined pot-fraction to show, so it
falls back to layer 2's legal minimum — a lone 1BB option into a 20BB pot. **The 1BB bet is
legal; the bug is that it's the ONLY thing offered.** The pot-size is never consulted when the
node is unmapped.

## 3. Blast-radius map (what reads these)
- `legal_actions` (the 1BB min) is read by **bots** (`personas_postflop.sample_postflop_decision`),
  the **range estimator**, and **grading** — so changing the engine's min-bet is high-risk and
  wrong (it would corrupt the real legal minimum everywhere).
- `_hero_postflop_size_bb` feeds **only the hero UI's offered size** — changing it is low-risk
  and localized.
- The offered hero size is later recognized by the **canonical-bet grader**
  (`grade_map_postflop`, gated on `POSTFLOP_BET_FRACS[street]` fractions within a 1dp
  tolerance). So any new default size must be a **recognized street fraction** or the decision
  becomes an honest "no baseline yet" (ungraded) — never a mis-grade.

## 4. Fix options
| # | Option | What changes | Blast radius | Verdict |
|---|---|---|---|---|
| **1** | **Offer-layer pot-fraction default (recommended).** When `_hero_postflop_size_bb` would return None, instead return the street's **small `POSTFLOP_BET_FRACS` fraction** × pot (flop 0.33, turn 0.5, river 0.5), clamped into the legal `[min_bb, max_bb]`. | `sim_session.py` hero-offer only. | **Low** — hero UI only; bots/grader/legal-actions untouched. Because it snaps to a recognized street fraction, the canonical-bet grader still maps it where a grader exists; where none exists (RES-C "no baseline yet"), hero gets a realistic size to *choose* and the decision is honestly ungraded. | **DO THIS (F6).** |
| 2 | Extend `HERO_NODE_SIZE` with donk/lead/probe/delayed-c-bet keys + researched sizes. | `sizing.py` + research. | Med — new nodes, and most have **no grader** (RES-C `docs/ai-dlc/research/RES-C-postflop-ranges.md §12` "no baseline yet" list), so it offers sizes hero can't be graded on. | Defer — half a feature until those nodes get graders; Option 1 already removes the 1BB degeneracy for all of them at once. |
| 3 | Clamp the engine BET `min_bb` to a pot-fraction floor when pot ≫ 1BB. | `engine.py::legal_actions`. | **High** — changes the legal minimum for **bots, range-estimate, and grading**; also factually wrong (1BB IS the legal min). | **Reject.** The bug is the offer, not legality. |

## 5. Recommendation for F6 (the build slice)
- Implement **Option 1** in `_hero_postflop_size_bb`: replace the `None`-return with the street's
  small `POSTFLOP_BET_FRACS` fraction (× current pot), clamped to the legal bracket. Keep the
  short-stack collapse behavior consistent with the existing `_barrel_two_sizes` /
  `_preflop_two_sizes` distinctness fallback (if the clamped size equals the legal min, offer
  the single legal size — don't fabricate a second).
- **Do NOT touch `engine.py::legal_actions`** — 1BB stays the legal minimum bet.
- **Pass/fail for F6:** in the reproducing spot (large-pot donk/lead node) hero is offered a
  pot-proportional size (≈⅓-pot), not a lone 1BB; the offered size is either graded by the
  canonical-bet mapper or honestly "no baseline yet" (never mis-graded); no new grading holes
  are introduced elsewhere; the hero-fold-path playout regression (the 3×-recurring FE fold bug,
  Epic-2 header) is re-verified; `spot_signature()` unchanged.

## 6. Pass/fail (this spike, self-check)
- [x] Identifies the exact code path (`sim_session.py:354-362` offer miss + `engine.py:187-192`
      1BB legal min) and the trigger (unmapped/non-aggressor node with a large pot).
- [x] Gives a reproducing spot (large-pot donk/lead OOP).
- [x] Recommends a fix (Option 1, offer-layer) with trade-offs vs two rejected alternatives and
      the grader blast-radius noted.
- [x] No app code; no `spot_signature()` change.
