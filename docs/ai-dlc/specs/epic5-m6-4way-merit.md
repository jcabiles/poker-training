# Spec — M6: 4-way merit extension (RES-H H2, direction-only)

**Wave 2** (after Wave 1 merges — mutates the shared `_apply_multiway` M4 composes with).
Branch: `feat/epic5-m6` stacked off the Wave-1 tip. Spike LAW: `RES-H-mw-extension.md` §2 + §5-H2.

## Goal
Make `_apply_multiway`'s scalars **opponent-count-aware** so 4-way pots grade with the correct
DIRECTION (bluff merit collapses faster, catcher-fold rises), and extend the `map_mw_*` mappers to
fire when hero closes a **4-way** SRP shape. Direction-only — **no published 4-way baseline exists**
(§2.1); never present a 4-way frequency as calibrated. 5+ stays binary bucket / "no baseline yet."

## Files / interfaces
- `backend/app/domain/postflop.py` — **MODIFY** `_apply_multiway` (:424):
  - Add an `opp` param = **opponent count (villains only), NOT total players.** Exact formula:
    `opp = players_in_pot(spot) - 1` (`players_in_pot`, `spot.py:164`, counts hero + live villains;
    HU ⇒ `players_in_pot==2` ⇒ `opp==1`). **Off-by-one warning:** passing `players_in_pot(spot)`
    directly as `opp` breaks the HU-byte-identical invariant (`max(2-1,0)=1 → base**1 ≠ 1.0`). Add a
    named helper `opponent_count(spot) -> int` (docstring pinning the `-1`) so maker and refuter check
    the SAME formula, not two independent re-derivations.
  - Replace the flat `_MW_*` constants with geometric forms `base ** max(opp-1, 0)` (F4
    `_MW_CATCH_TIGHTEN = 1.15 ** max(opp-1,0)` shape). Set each `base` = **today's flat constant**,
    so `opp=2` (3-way) ⇒ `base**1` == current value ⇒ 3-way byte-identical; HU never enters the gate
    (and `opp=1` ⇒ `base**0`=1.0 anyway). Each `_MW_*` is used in exactly ONE positive-merit multiply
    (verified: 7 existing call sites), so `base**1 == base` is arithmetically exact for 3-way.
  - **Thread `opp` through EVERY call site** of `_apply_multiway` — **10 total on this stacked
    branch**: `grade_cbet`, `grade_vs_cbet`, `grade_vs_check_raise`, `grade_turn_barrel`,
    `grade_vs_turn_bet`, `grade_river_barrel`, `grade_vs_river_bet`, M4's `grade_vs_caller_raise`,
    and M5's `grade_limped_lead`/`grade_limped_vs_lead`. Each passes `opp=opponent_count(spot)`.
- `backend/app/domain/table/grade_map_postflop.py` — **MODIFY** `_mw_srp_preflop` / `map_mw_*` to
  fire on a **4-way** SRP shape **only when hero closes** (all players behind hero have acted —
  verify from ACTION ORDER per RES-H §1.2 / the N5 closing-seat lesson; never "BB closes"). A 4-way
  spot with a live player behind hero → `None`. Cap at 4-way; 5+ → binary bucket / `None`.
- Tests: new `tests/domain/test_apply_multiway_opp.py` + 4-way mapper gate tests.

## Out of scope
5+-way calibrated tiers (label = binary bucket, never a frequency). Any MDF / per-opponent pot-odds
constant. New graders (M6 only scales existing merits + widens existing mappers). Hero-seat widening
(that's M7).

## Constraints (invariants)
- **HU byte-identical** (opp=1 ⇒ exponent 0 ⇒ 1.0) **and 3-way byte-identical** (`base**1` ==
  current constant) — hash-pins unchanged, assert both.
- Direction-only: removing the multiplier recovers the HU merits exactly (test). No MDF constants.
- `spot_signature()` frozen; `_apply_multiway` reads NOTHING but merits/cat/side/opp — never persona.
- "No baseline yet" first-class: 4-way with a live player behind hero → `None`; 5+ not a calibrated tier.
- Domain purity; freq+EV never boolean.

## Verify-by (RES-H §5-H2 verbatim)
1. HU byte-identical AND 3-way byte-identical to today (assert both; hash-pins).
2. **Monotone-in-opponents:** fixed air/draw + texture → aggressive (bluff) merit non-increasing
   HU→3-way→4-way; fixed weak_made catcher → facing FOLD merit non-decreasing across the same.
3. **Direction-only:** no MDF/per-opponent pot-odds constant (code-review + a test that removing the
   multiplier recovers HU merits exactly).
4. A 4-way SRP spot where hero **closes** maps and grades; a 4-way spot with a live player **behind**
   hero returns `None` — assert both from engine-driven states (§1.2 shows both occur).
5. 5+-way not claimed calibrated (label = binary bucket); `verify.sh` + build green; refuter + Codex
   Sol PASS.
