# RES-A — Preflop Range Research: RFI-by-position + all node contexts, live $2/$3

**Status:** research spike (decision doc only). **No app code, no `content/` edits** — R4 consumes this.
**Last updated:** 2026-07-15
**Anchors:** `docs/research/01-preflop-strategy.md` (doc 01), `docs/research/05-preflop-validation.md` (doc 05).

---

## 1. Goal, scope, out-of-scope

**Goal.** Fill the preflop content coverage gap for the early seats **UTG+1 / UTG+2** (the repo enum
names them `UTG1` / `UTG2`) across every node context, and audit whether any *other* seat × context
cell is missing from today's content. Deliver a positions × node-context coverage matrix plus a
proposed combo string (sourced or explicitly heuristic-derived) for each missing cell.

**In scope.** Live $2/$3, ~100BB, 9-handed. Node contexts: `RFI`, `vs_RFI`, `vs_3bet`, `vs_4bet`,
`blind_defense`, `vs_limpers`. Range *membership* + `sizing_bb`, expressed as combo strings in the
existing pack notation.

**Out of scope (hard).** No content-file edits (that is R4). No solver tables — heuristic + published
strategy only, EVs stay labeled *approximate*. No new node contexts (`squeeze` gap-fill is doc 05's
territory, not re-litigated here). No `hand_rank`/equity-ordering changes. No sizing research beyond the
existing conventions (that is RES-B).

---

## 2. Table-engine seat model — blocker investigation (roadmap flag resolved)

The roadmap flagged a potential blocker: *"confirm the table engine's seat model can cleanly expose
UTG1/UTG2."* **It already does — no engine work is needed for R4.** Findings:

- `Position` enum (`backend/app/domain/spot.py:29-38`) already lists `UTG1`/`UTG2` as first-class
  members, in correct seat order between `UTG` and `LJ`.
- The dealer rotation `backend/app/domain/table/deck.py:19-29` (`_ROTATION`) and
  `positions_for_button()` already place `UTG1`/`UTG2` in the clockwise seat order — the table engine
  deals and labels these seats today.
- Preflop action order `backend/app/domain/scenarios.py:35-45` (`_SEAT_ORDER`) already threads
  `UTG1`/`UTG2` in the right slots; `grading.py:45-46,61-62` and `postflop.py:77-78` already map them to
  `RFI_EP` / seat indices 3–4.
- **The only gap is data.** `RFI_POSITIONS` (`scenarios.py:48-55`) and the content packs omit
  `UTG1`/`UTG2`, so no scenarios are generated and no provider lookup succeeds for them. Scenario
  generation is content-driven: `_find_entry(ctx, pos, facing)` (`scenarios.py:307`) and the content
  index key `(node_context, position, facing, limper_count, villain_type)`
  (`domain/content/registry.py:20-37`) resolve directly against pack entries. **Add the entries →
  the seats light up.** (R4 will also need to add `UTG1`/`UTG2` to `RFI_POSITIONS` so the RFI
  scenario generator emits them — noted in §9.)

**`spot_signature()` is safe.** The preflop signature (`backend/app/domain/srs.py:48-68`) hashes
`spot.hero.position.value` as a raw string among its parts. A `UTG1`/`UTG2` row therefore produces a
**brand-new, distinct** signature hash that cannot collide with any existing UTG/LJ/HJ/CO/BTN/SB hash.
Appending these rows is purely **additive** — no existing signature byte changes. Constraint respected
(see §8).

---

## 3. Coverage matrix (positions × node context)

Legend: **present** = an entry exists in `content/preflop/*.json` today · **MISSING** = no entry, none
proposed here (out of this spike's remit) · **PROPOSED** = filled by this doc (§4–§6) ·
**n/a** = structurally impossible / not a real spot at a 9-handed table.

`vs_RFI`, `vs_3bet`, `vs_4bet`, `blind_defense` cells are shown as **hero-position rows**; the specific
`facing` opponent seats are enumerated in §5–§6. A hero seat is "present" only if *some* facing entry
exists; the per-facing gaps are detailed below.

| Hero seat | RFI | vs_RFI (facing an open) | vs_3bet | vs_4bet | blind_defense | vs_limpers |
|---|---|---|---|---|---|---|
| **UTG**  | present | n/a¹ | present (vs BTN) | MISSING² | n/a³ | MISSING⁴ |
| **UTG1** | **PROPOSED** | **PROPOSED** (vs UTG) | **PROPOSED** (vs later 3-bettors) | MISSING² | n/a³ | MISSING⁴ |
| **UTG2** | **PROPOSED** | **PROPOSED** (vs UTG/UTG1) | **PROPOSED** (vs later 3-bettors) | MISSING² | n/a³ | MISSING⁴ |
| **LJ**   | present | doc 05 gap-fill (vs UTG)⁵ | MISSING² | MISSING² | n/a³ | MISSING⁴ |
| **HJ**   | present | present (vs UTG) | MISSING² | MISSING² | n/a³ | MISSING⁴ |
| **CO**   | present | present (vs UTG/HJ) + doc 05 (vs LJ)⁵ | present (vs BTN/SB) | present (vs UTG) | n/a³ | present (1 limper) |
| **BTN**  | present | present (vs UTG/HJ/CO) + doc 05 (vs LJ)⁵ | present (vs BB/SB) | present (vs CO) | n/a³ | present (1–2 limpers) |
| **SB**   | present | n/a⁶ | MISSING² | MISSING² | present (vs BTN/CO) | MISSING⁴ |
| **BB**   | n/a⁷ | n/a⁶ | MISSING² | present (vs BTN) | present (vs UTG/CO/BTN) | MISSING⁴ |

**Footnotes.**
1. UTG opens first; it can never *face* an RFI (`vs_RFI` requires an earlier opener). n/a.
2. **Out of this spike's remit.** These are pre-existing thin-coverage gaps in the packs (many hero
   seats never appear as the 3-bettor / 4-bettor / iso-raiser). Doc 05 §2.3 explicitly scoped them out
   ("noted as an aside, **not** in the requested gap-fill scope"). RES-A's charter is UTG1/UTG2 + a
   *flag* of other gaps — flagged here, not filled. R4 or a later spike may address them.
3. `blind_defense` is by definition an SB/BB context; non-blind seats have n/a.
4. `vs_limpers` currently only has CO/BTN entries (doc 05 §2.6). Every other seat is a pre-existing gap,
   out of remit — flagged, not filled.
5. Doc 05 §3.3 already proposed these `vs_RFI` fills (LJ-as-hero, CO/BTN vs LJ). Not re-derived here;
   pointer only, so R4 has one place to look.
6. Facing an open *from the blinds* is `blind_defense`, not `vs_RFI`. SB/BB `vs_RFI` = n/a by design.
7. BB is never first-in unopened (it has already posted); "BB RFI" is n/a. BB's unopened-pot action is
   `blind_defense` (vs SB) — not in the RFI pack.

**Bottom line for this spike:** the cells RES-A owns and fills are the **UTG1 and UTG2 rows** for
`RFI`, `vs_RFI`, and `vs_3bet` — **6 seat×context cells** (2 seats × 3 contexts), plus the derivation
that makes them defensible. `vs_4bet`, `blind_defense`, `vs_limpers` for UTG1/UTG2 are **not** real
authored spots at these stakes (UTG1/UTG2 are never the 3-bettor-who-gets-4-bet in the shipped tree,
are never in the blinds, and live EP seats do not iso-limpers with a distinct pack row) — see §7.

---

## 4. RFI — UTG1 / UTG2 (the CO→UTG monotonic-tightening derivation)

### 4.1 Method

The authored UTG (tightest) and LJ ranges are the two fixed anchors. UTG1 and UTG2 are the two seats
between them, so they must **nest monotonically**: each later seat opens a strict superset of the seat
before it. Formally the derivation target is

> **UTG ⊆ UTG1 ⊆ UTG2 ⊆ LJ**

Because UTG and LJ are byte-locked (cannot change), UTG1/UTG2 are constructed to (a) contain all of UTG,
(b) be contained in LJ, and (c) tighten strictly monotonically in between. Where LJ's authored shape and
a naive linear interpolation disagree (LJ is not a strict superset of a "half-way" range on every axis),
**LJ wins as the ceiling** — a later seat must never be *tighter* than an earlier one on any hand class.
This is grounded, not invented: published 9-max solver grids (PokerCoaching, MyPokerCoaching — see §8)
show exactly this progression, with **offsuit broadways (KQo) entering around UTG+2** and the
suited-connector floor descending one notch per seat. The app deliberately sits **tighter than those
solver grids** (rake + live equity-realization + memorizability — doc 05 §1, doc 01 §1 "Rake Reality"),
so we import the *shape*, not the solver's exact combos.

### 4.2 The anchors and the two new rows

| Seat | Combos | `sizing_bb` | Combo-label count |
|---|---|---|---|
| UTG (authored, fixed) | `77+, A7s+, A5s, KJs+, QJs, JTs, AJo+` | 3.0 | 23 |
| **UTG1 (proposed)** | `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, AJo+` | 3.0 | 27 |
| **UTG2 (proposed)** | `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, 98s, AJo+, KQo` | 3.0 | 29 |
| LJ (authored, fixed) | `66+, A5s+, KTs+, QTs+, JTs, T9s, 98s, AJo+, KQo` | 3.0 | 30 |

Verified nesting (each ⊆ holds exactly; no seat is wider than the seat after it):

- **UTG ⊆ UTG1** ✓ — UTG1 adds `{66, KTs, QTs, T9s}`.
- **UTG1 ⊆ UTG2** ✓ — UTG2 adds `{98s, KQo}`.
- **UTG2 ⊆ LJ** ✓ — LJ adds `{A6s}` (its `A5s+` fill), keeping LJ genuinely the widest of the four.

Counts climb strictly 23 → 27 → 29 → 30, confirming monotonic tightening in the correct direction
(earlier = tighter). `sizing_bb = 3.0` matches UTG and LJ (all EP/EP-boundary opens open 3.0bb per
`scenarios.py:60-69`).

### 4.3 Rationales (mirroring the `rationale` field voice in the packs)

**UTG1 — RFI, `sizing_bb` 3.0:**
> One seat later than UTG with 6–7 players still to act, UTG+1 loosens only slightly off the tightest
> EP range: it adds 66 (marginally better set-mining odds with one fewer player behind), the suited
> broadways KTs/QTs, and the suited connectors down to T9s, whose straight/flush potential now clears
> the equity-realization bar that UTG's fuller field denied them. It stays strictly EP — no offsuit KQ,
> no small pairs below 66 — because a raise from here still runs into 6–7 potential wake-ups and gets
> dominated too often when called. Heuristic-derived (CO→UTG monotonic interpolation, UTG⊆UTG1⊆LJ),
> shape-corroborated by 9-max solver UTG+1 grids (PokerCoaching 14.3%, MyPokerCoaching 13.2% — §8);
> the app sits tighter for rake and live realization (doc 01 §1, doc 05 §1).

**UTG2 — RFI, `sizing_bb` 3.0:**
> The EP→MP transition seat: with 5–6 players left, UTG+2 adds 98s (extending the suited-connector
> floor one more notch) and **KQo** — the first offsuit broadway to enter, exactly where the solver
> grids introduce it, because now few enough players remain that KQo's top-pair value and blockers
> outweigh its domination risk. It still holds the EP pair floor at 66 (small pairs' implied odds stay
> thin here) and the A7s+/A5s suited-ace convention, leaving LJ its `A6s` step so LJ remains the widest
> of the early seats. Heuristic-derived (UTG1⊆UTG2⊆LJ), corroborated by 9-max solver UTG+2 grids where
> KQo and 98s/87s appear (PokerCoaching 15.7% — §8); the app trims to a value-lean EP range for rake and
> live realization (doc 01 §13.8 "Fix EP range leaks", doc 05 §1).

**Note on doc 05's earlier proposal.** Doc 05 §3.2 proposed `UTG1: 66+, A7s+, A5s, KTs+, QJs, JTs, T9s,
AJo+` and `UTG2: 55+, A4s+, KTs+, QTs+, J9s+, ATo+, KJo+`. Those strings **do not nest** (UTG2 there
opens `55+` and `A4s+`, making it *wider than the authored LJ*, which opens only `66+`/`A5s+` — a later
seat looser than an earlier one, violating monotonicity; and its `ATo+, KJo+, J9s+` jump past LJ's
offsuit/suited shape). RES-A supersedes doc 05 §3.2 with the nesting-verified strings in §4.2. This is
the one substantive correction this spike makes to prior research.

---

## 5. vs_RFI — UTG1 / UTG2 facing an open

**Which facings are real.** UTG1 can only face an open from **UTG** (the only earlier seat). UTG2 can
face an open from **UTG or UTG1**. All other openers sit *behind* these hero seats, so those `vs_RFI`
cells are structurally impossible. This yields three real entries: **UTG1 vs UTG**, **UTG2 vs UTG**,
**UTG2 vs UTG1**.

**Method.** Facing the tightest possible open (UTG's range), a live pool that under-3-bet-bluffs
(doc 01 §5, §12) means **value-only merged** continuation. The value 3-bet stays the pack-standard
`QQ+, AKs, AKo, A5s` (the wheel-ace blocker is the lone bluff, exactly as authored HJ/CO/LJ-vs-UTG
entries do). The **call** range is a tight, high-equity band that widens by one pair per seat as we move
from the seat right behind UTG (UTG1, narrowest) toward LJ (widest), mirroring the authored
`HJ vs UTG` (calls `77-JJ, …`) and doc 05's `LJ vs UTG` (calls `88-JJ, …`). Cold-calling with many
players still behind (squeeze exposure) keeps these deliberately tight — an OK-simplification the packs
already make (doc 05 §2.2).

Monotonic call-floor chain (pair floor drops one step per seat toward LJ; all heuristic-derived):

| Hero (facing UTG) | 3-bet (value + wheel bluff) | call | `sizing_bb` |
|---|---|---|---|
| **UTG1** | `QQ+, AKs, AKo, A5s` | `TT, JJ, AQs, AJs, KQs, KJs, QJs` | 10.0 |
| **UTG2** | `QQ+, AKs, AKo, A5s` | `99, TT, JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |
| (LJ vs UTG, doc 05) | `QQ+, AKs, AKo, A5s` | `88-JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |
| (HJ vs UTG, authored) | `QQ+, AKs, AKo, A5s` | `77-JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |

Pair floor tightens correctly by seat: HJ `77` → LJ `88` → UTG2 `99` → UTG1 `TT` (earlier seat = fewer
pairs continue, because it is deeper in the field and more exposed to a squeeze). `sizing_bb 10.0`
matches every authored `vs_RFI`-facing-UTG entry.

**UTG2 vs UTG1.** UTG1's open is our new `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, AJo+` — a hair wider than
UTG's, but still EP-strong. UTG2 (one seat behind UTG1) re-values essentially as it does vs UTG, a
touch wider on the flat because UTG1's range is marginally looser: `3-bet QQ+, AKs, AKo, A5s`; `call
99, TT, JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` (same as UTG2-vs-UTG — the one-notch-wider opener does
not justify loosening past this against a value-heavy pool that rarely opens EP light). `sizing_bb 10.0`.

**Rationale (UTG1 vs UTG — representative; UTG2 rows mirror the authored HJ/LJ voice):**
> UTG opens the strongest range at the table and UTG+1 sits directly behind it with the whole field
> still to act, so this is the tightest vs-RFI spot in the pack: 3-bet only genuine value (QQ+, AK)
> plus the A5s blocker-bluff, and flat a narrow high-equity band (TT–JJ, AQs–AJs, suited Broadways) —
> dominated offsuit hands and thin suited hands can't continue profitably against a range this strong,
> and cold-calling with 5+ players still to act invites a squeeze, so the flat stays disciplined.
> Value-only merged per live under-3-bet-bluff pool (doc 01 §5, §12); heuristic-derived, mirrors the
> authored `HJ vs UTG` / doc 05 `LJ vs UTG` shape one seat tighter.

---

## 6. vs_3bet — UTG1 / UTG2 (you opened EP and face a 3-bet)

**Which facings are real.** If UTG1/UTG2 open and get 3-bet, the 3-bettor is any *later* seat
(UTG2 through BB). The shipped `vs_3bet` pack keys on hero-position × 3-bettor-position but only ever
authored a handful of representative facings (UTG vs BTN, CO vs BTN/SB, BTN vs BB/SB). Following that
precedent, RES-A proposes **one representative facing per new hero seat**: the 3-bettor most likely to
apply pressure to an EP open at these stakes is a **late/blind aggressor**, so we use the widest-3-bet
opponent the tree exercises — **vs BTN** — mirroring the authored `UTG vs BTN` entry exactly in shape.

**Method.** UTG1/UTG2 open the tightest ranges at the table, so a 3-bet has them dominated by the value
half of almost any range (doc 01 §6; the pool under-3-bet-bluffs). This is the pack's tightest-defense
region: **4-bet only KK+/AKs, flat QQ/JJ/AKo/AQs, fold everything else.** This is identical to the
authored `UTG vs BTN` row — correct, because UTG1/UTG2 open essentially the same strength tier as UTG.

| Hero (facing a BTN 3-bet) | 4-bet (value) | call | `sizing_bb` |
|---|---|---|---|
| (UTG vs BTN, authored) | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |
| **UTG1 vs BTN** | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |
| **UTG2 vs BTN** | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |

`sizing_bb 22.0` matches the authored EP `vs_3bet` entries. No wheel-ace 4-bet-bluff here (EP OOP vs a
value-heavy 3-bettor — the packs strip bluffs OOP; doc 01 §6, doc 05 §2.3).

**Rationale (UTG1/UTG2 vs BTN — mirrors authored UTG vs BTN voice):**
> You opened from an early seat with the tightest range at the table, so a BTN 3-bet has you dominated
> by the value half of most ranges: 4-bet only the hands that beat a calling 4-bet (KK+, AKs) and flat
> QQ/JJ/AKo/AQs to keep the pot controlled from out of position; everything below folds because live
> players under-3-bet-bluff, so their 3-bets are rarely light (doc 01 §6).

---

## 7. Why UTG1/UTG2 have no vs_4bet / blind_defense / vs_limpers rows

Documented so R4 doesn't chase phantom cells:

- **vs_4bet** — a UTG1/UTG2 `vs_4bet` row would require UTG1/UTG2 to be the *3-bettor who then gets
  4-bet*. That is a `vs_3bet`-hero-elsewhere spot from the opener's view; the `vs_4bet` pack keys on the
  **3-bettor** as hero, and at these stakes an EP seat that 3-bets and faces a 4-bet holds only KK+/AK
  (the universal live "4-bets are nutted" jam/call/fold — doc 01 §7). If R4 wants completeness it can
  add `UTG1 vs <opener>` / `UTG2 vs <opener>` rows identical in shape to the authored `CO vs UTG`
  (`raise AA,KK; call AKs,AKo`), but this is **not** a UTG1/UTG2-specific gap — it is the same
  thin-coverage aside as every other missing `vs_4bet` hero seat (matrix footnote 2). Flagged, not
  filled.
- **blind_defense** — SB/BB only by definition. UTG1/UTG2 = n/a.
- **vs_limpers** — the pack authors iso rows only for the seats that most profitably isolate (CO/BTN,
  doc 05 §2.6). An EP seat facing a limper still opens its RFI range for value (doc 01 §9, §11) and does
  not get a distinct iso-pack row today. Adding EP iso rows is a separate live-specific expansion, not a
  UTG1/UTG2 gap. Flagged, not filled.

---

## 8. Sources

**External (fetched this spike, corroborating the RFI progression shape):**
- PokerCoaching — Free Preflop Charts (GTO & Exploitative): 9-max UTG+1 ≈ 14.3% (`66+, A4s+, K9s+,
  Q9s+, J9s+, T9s, 98s, AJo+, KQo`), UTG+2 ≈ 15.7% (adds `A2s+, 87s, 76s`).
  https://pokercoaching.com/preflop-charts/
- MyPokerCoaching — Optimal 100bb Opening Ranges (full ring): UTG ≈ 11.4%, UTG+1 ≈ 13.2%
  (`77+, A3s+, K8s+, QTs+, JTs, T9s, AJo+, KQo`), LJ ≈ 15.7%, HJ ≈ 19.6% — confirms the
  monotonic widening and KQo entering by UTG+1/UTG+2.
  https://www.mypokercoaching.com/optimal-cash-game-opening-ranges-100bb/
- RangeConverter — 9-Max 100bb NLHE Charts (primary 9-max grid incl. UTG+1/UTG+2; doc 05's baseline).
  https://rangeconverter.com/articles/poker-charts-9-max-100bb-no-limit-texas-holdem

  *These solver grids run wider than the app's proposed rows on purpose — the app is tighter for rake,
  live equity-realization, and memorizability. They are used for shape (which hand classes enter at
  which seat), not exact combos.*

**Repo (primary anchors):**
- `docs/research/01-preflop-strategy.md` — §1 Rake Reality, §3A EP ranges & exclusions, §5 3-bet
  (value-only merged live), §6 responding to 3-bets, §7 4-bets nutted, §9/§11 limpers/multiway,
  §12 exploit deviations, §13.8 "Fix EP range leaks."
- `docs/research/05-preflop-validation.md` — §1 methodology & tighter-than-solver doctrine,
  §2.2 vs_RFI value-only, §3.2 (UTG1/UTG2 RFI — **superseded by §4.2 here for nesting**), §3.3 vs_RFI
  LJ/CO/BTN gap-fills (pointer, matrix footnote 5).
- Content packs: `content/preflop/{rfi,vs_rfi,vs_3bet,vs_4bet,blind_defense,vs_limpers}.json`.
- Engine: `backend/app/domain/spot.py`, `table/deck.py`, `scenarios.py`, `srs.py`,
  `domain/content/registry.py` (§2).

---

## 9. Constraints confirmed

- **No content-file edits.** No `content/*.json` was modified by this spike. ✓
- **No app code.** No source edited. (A throwaway range-expansion script was written to the scratchpad
  only, to verify nesting — not in the repo.) ✓
- **Additive / no-renumber.** Every proposed row is a **new** `(node_context, position, facing)` entry
  for `UTG1`/`UTG2`. The content index key `(node_context, position, facing, limper_count,
  villain_type)` (`registry.py:20`) makes these purely additive — no existing UTG/LJ/HJ/CO/BTN/SB entry
  is touched, renumbered, or mutated. `spot_signature()` hashes `position.value` as a raw string
  (`srs.py:60`), so new seats mint new, non-colliding hashes; existing persisted SRS history is
  untouched. ✓
- **No solver tables.** Every range is either shape-corroborated by published charts or explicitly
  labeled heuristic-derived, with rationale. EVs untouched (stay *approximate*). ✓

---

## 10. Hand-off to R4

R4 (the build slice) appends the following entries to the existing packs. **All strings are final and
nesting-verified — copy verbatim.** Add `UTG1`/`UTG2` to `RFI_POSITIONS` in
`backend/app/domain/scenarios.py:48` so the RFI generator emits the two new seats.

**`content/preflop/rfi.json`** — append 2 entries (`node_context: "RFI"`):

| position | actions[0].combos (raise, freq 1.0) | sizing_bb |
|---|---|---|
| `UTG1` | `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, AJo+` | 3.0 |
| `UTG2` | `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, 98s, AJo+, KQo` | 3.0 |

**`content/preflop/vs_rfi.json`** — append 3 entries (`node_context: "vs_RFI"`):

| position | facing | raise | call | sizing_bb |
|---|---|---|---|---|
| `UTG1` | `UTG` | `QQ+, AKs, AKo, A5s` | `TT, JJ, AQs, AJs, KQs, KJs, QJs` | 10.0 |
| `UTG2` | `UTG` | `QQ+, AKs, AKo, A5s` | `99, TT, JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |
| `UTG2` | `UTG1` | `QQ+, AKs, AKo, A5s` | `99, TT, JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |

**`content/preflop/vs_3bet.json`** — append 2 entries (`node_context: "vs_3bet"`):

| position | facing | raise | call | sizing_bb |
|---|---|---|---|---|
| `UTG1` | `BTN` | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |
| `UTG2` | `BTN` | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |

Use the §4.3 / §5 / §6 rationale text for each entry's `rationale` field.

**Not in R4's UTG1/UTG2 scope (pre-existing gaps, flagged only):** `vs_4bet`, `blind_defense`,
`vs_limpers` for UTG1/UTG2 (§7); the doc 05 §3.3 `vs_RFI` LJ/CO/BTN fills (matrix footnote 5); and every
other thin-coverage cell (matrix footnote 2). These are separate decisions — do not silently bundle
them into the UTG1/UTG2 slice.

---

### Open question R4 must resolve

**Representative-facing choice for `vs_3bet`.** RES-A proposes a single `vs BTN` facing per new EP seat
(mirroring the authored `UTG vs BTN` and the pack's one-facing-per-seat precedent). If R4 wants the
scenario generator to exercise UTG1/UTG2 getting 3-bet from *other* seats (SB, BB, CO), it must decide
whether to author those extra facings — the range shape is identical (`4-bet KK+/AKs; call QQ/JJ/AKo/AQs`
vs any of them at these stakes), so it is a coverage-breadth call, not a strategy call. Recommend
shipping the single `vs BTN` facing first and widening only if play-testing surfaces uncovered UTG1/UTG2
3-bet spots.
