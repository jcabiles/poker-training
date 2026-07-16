# 09 — Preflop Ranges: Early Position (UTG+1 / UTG+2)

**Purpose:** Fill the preflop content coverage gap for the early seats **UTG+1 / UTG+2** (repo enum `UTG1` / `UTG2`) across every real node context, and record the CO→UTG monotonic-tightening derivation that makes the proposed ranges defensible. These seats had no authored ranges; this doc supplies range membership + `sizing_bb` for the cells that are genuine spots at these stakes. Scope: live $2/$3, ~100BB, 9-handed. Node contexts covered: `RFI`, `vs_RFI`, `vs_3bet` (the three where UTG1/UTG2 are real). All ranges are **heuristic + published-strategy grounded, never solver-exact** — the app deliberately runs tighter than solver grids for rake, live equity-realization, and memorizability; EVs stay labeled *approximate*.

**Source / full decision doc:** `docs/ai-dlc/research/RES-A-preflop-ranges.md` (RES-A). This entry captures the substance; the full spike also carries the seat-model blocker investigation, the coverage matrix footnotes, and the R4 hand-off tables. **Consumed by build slice R4** (appends these entries to `content/preflop/*.json` and adds `UTG1`/`UTG2` to `RFI_POSITIONS`). No content or code was edited by the research.

> **Correction to older corpus:** This doc **supersedes `docs/research/05-preflop-validation.md` §3.2**, which proposed non-nesting UTG1/UTG2 RFI strings (its `UTG2: 55+, A4s+, …` was *wider than the authored LJ*, violating monotonicity). The nesting-verified strings in §2 below replace them. This is the one substantive correction the spike makes to prior research.

---

## 1. Method — CO→UTG monotonic tightening

The authored **UTG** (tightest) and **LJ** ranges are fixed anchors (they are byte-locked; changing them would orphan SRS history via `spot_signature()`). UTG1 and UTG2 are the two seats between them, so they must **nest monotonically** — each later seat opens a strict superset of the seat before it:

> **UTG ⊆ UTG1 ⊆ UTG2 ⊆ LJ**

UTG1/UTG2 are constructed to (a) contain all of UTG, (b) be contained in LJ, and (c) tighten strictly monotonically in between. Where LJ's authored shape and a naive linear interpolation disagree, **LJ wins as the ceiling** — a later seat must never be tighter than an earlier one on any hand class.

This is grounded, not invented: published 9-max solver grids (PokerCoaching, MyPokerCoaching, RangeConverter — §4) show exactly this progression, with **offsuit broadways (KQo) entering around UTG+2** and the suited-connector floor descending one notch per seat. The app imports the *shape* (which hand classes enter at which seat), not the solver's exact combos, and sits deliberately **tighter** than those grids.

---

## 2. RFI — proposed ranges (`node_context: RFI`, `sizing_bb 3.0`)

| Seat | Combos | `sizing_bb` | Label count |
|---|---|---|---|
| UTG (authored, fixed) | `77+, A7s+, A5s, KJs+, QJs, JTs, AJo+` | 3.0 | 23 |
| **UTG1 (proposed)** | `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, AJo+` | 3.0 | 27 |
| **UTG2 (proposed)** | `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, 98s, AJo+, KQo` | 3.0 | 29 |
| LJ (authored, fixed) | `66+, A5s+, KTs+, QTs+, JTs, T9s, 98s, AJo+, KQo` | 3.0 | 30 |

**Verified nesting** (each ⊆ holds exactly; no seat wider than the seat after it):
- **UTG ⊆ UTG1** — UTG1 adds `{66, KTs, QTs, T9s}`.
- **UTG1 ⊆ UTG2** — UTG2 adds `{98s, KQo}`.
- **UTG2 ⊆ LJ** — LJ adds `{A6s}` (its `A5s+` fill), keeping LJ genuinely the widest of the four.

Counts climb strictly 23 → 27 → 29 → 30, confirming monotonic tightening in the correct direction (earlier = tighter). `sizing_bb = 3.0` matches UTG and LJ (all EP/EP-boundary opens open 3.0bb).

**Rationale — UTG1:** One seat later than UTG with 6–7 players still to act, UTG+1 loosens only slightly off the tightest EP range: it adds `66` (marginally better set-mining odds with one fewer player behind), the suited broadways `KTs/QTs`, and the suited connectors down to `T9s`, whose straight/flush potential now clears the equity-realization bar UTG's fuller field denied them. It stays strictly EP — no offsuit KQ, no small pairs below 66 — because a raise here still runs into 6–7 potential wake-ups and gets dominated too often when called. Heuristic-derived (UTG⊆UTG1⊆LJ), shape-corroborated by 9-max solver UTG+1 grids (PokerCoaching ≈14.3%, MyPokerCoaching ≈13.2%); the app sits tighter for rake and live realization.

**Rationale — UTG2:** The EP→MP transition seat. With 5–6 players left, UTG+2 adds `98s` (extending the suited-connector floor one more notch) and **`KQo`** — the first offsuit broadway to enter, exactly where the solver grids introduce it, because now few enough players remain that KQo's top-pair value and blockers outweigh its domination risk. It still holds the EP pair floor at 66 and the `A7s+/A5s` suited-ace convention, leaving LJ its `A6s` step so LJ remains the widest early seat. Heuristic-derived (UTG1⊆UTG2⊆LJ), corroborated by 9-max UTG+2 grids where KQo and 98s/87s appear (PokerCoaching ≈15.7%); the app trims to a value-lean EP range.

---

## 3. vs_RFI and vs_3bet — proposed ranges

### 3.1 vs_RFI (facing an open, `sizing_bb 10.0`)

**Which facings are real.** UTG1 can only face an open from **UTG** (the only earlier seat). UTG2 can face **UTG or UTG1**. All other openers sit behind these hero seats, so those cells are structurally impossible. Three real entries result.

**Method.** Facing the tightest possible open against a live pool that under-3-bet-bluffs, continuation is **value-only merged**: the value 3-bet stays the pack-standard `QQ+, AKs, AKo, A5s` (the wheel-ace blocker is the lone bluff, mirroring authored HJ/CO-vs-UTG entries). The **call** range is a tight, high-equity band that widens by one pair per seat as we move from the seat right behind UTG (UTG1, narrowest) toward LJ (widest). Cold-calling with many players still behind (squeeze exposure) keeps these deliberately tight.

| Hero (facing UTG) | 3-bet (value + wheel bluff) | call | `sizing_bb` |
|---|---|---|---|
| **UTG1** | `QQ+, AKs, AKo, A5s` | `TT, JJ, AQs, AJs, KQs, KJs, QJs` | 10.0 |
| **UTG2** | `QQ+, AKs, AKo, A5s` | `99, TT, JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |
| (LJ vs UTG, doc 05) | `QQ+, AKs, AKo, A5s` | `88-JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |
| (HJ vs UTG, authored) | `QQ+, AKs, AKo, A5s` | `77-JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` | 10.0 |

Pair floor tightens correctly by seat: HJ `77` → LJ `88` → UTG2 `99` → UTG1 `TT` (earlier seat = fewer pairs continue, deeper in the field, more exposed to a squeeze).

**UTG2 vs UTG1.** UTG1's open is our new `66+, A7s+, A5s, KTs+, QTs+, JTs, T9s, AJo+` — a hair wider than UTG's but still EP-strong. UTG2 re-values essentially as it does vs UTG: `3-bet QQ+, AKs, AKo, A5s`; `call 99, TT, JJ, AQs, AJs, ATs, KQs, KJs, QJs, JTs` (same as UTG2-vs-UTG — the one-notch-wider opener does not justify loosening past this against a value-heavy pool). `sizing_bb 10.0`.

### 3.2 vs_3bet (you opened EP and face a 3-bet, `sizing_bb 22.0`)

**Which facing.** Following the pack's one-representative-facing-per-seat precedent, RES-A proposes a single **vs BTN** facing per new EP seat — the late/blind aggressor is the widest-3-bet opponent the tree exercises, mirroring the authored `UTG vs BTN` entry exactly in shape.

**Method.** UTG1/UTG2 open the tightest ranges at the table, so a 3-bet has them dominated by the value half of almost any range (the pool under-3-bet-bluffs). This is the pack's tightest-defense region: **4-bet only KK+/AKs, flat QQ/JJ/AKo/AQs, fold everything else** — identical to the authored `UTG vs BTN` row, because UTG1/UTG2 open essentially the same strength tier as UTG. No wheel-ace 4-bet-bluff (EP OOP vs a value-heavy 3-bettor — the packs strip bluffs OOP).

| Hero (facing a BTN 3-bet) | 4-bet (value) | call | `sizing_bb` |
|---|---|---|---|
| (UTG vs BTN, authored) | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |
| **UTG1 vs BTN** | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |
| **UTG2 vs BTN** | `KK+, AKs` | `QQ, JJ, AKo, AQs` | 22.0 |

---

## 4. What UTG1/UTG2 do NOT get, and why

Documented so R4 does not chase phantom cells:

- **`vs_4bet`** — would require UTG1/UTG2 to be the 3-bettor who then gets 4-bet. At these stakes an EP seat that 3-bets and faces a 4-bet holds only KK+/AK (the universal live "4-bets are nutted" jam/call/fold). This is not a UTG1/UTG2-specific gap — it is the same thin-coverage aside as every other missing `vs_4bet` hero seat. **Flagged, not filled.**
- **`blind_defense`** — SB/BB only by definition. UTG1/UTG2 = n/a.
- **`vs_limpers`** — the packs author iso rows only for the seats that most profitably isolate (CO/BTN). An EP seat facing a limper still opens its RFI range for value and gets no distinct iso-pack row. **Flagged, not filled.**

---

## 5. Sources

**External (corroborate the RFI progression *shape*, not exact combos — these solver grids run wider than the app on purpose):**
- PokerCoaching — Free Preflop Charts: 9-max UTG+1 ≈ 14.3%, UTG+2 ≈ 15.7% (adds `A2s+, 87s, 76s`). https://pokercoaching.com/preflop-charts/
- MyPokerCoaching — Optimal 100bb Opening Ranges: UTG ≈ 11.4%, UTG+1 ≈ 13.2% (`77+, A3s+, K8s+, QTs+, JTs, T9s, AJo+, KQo`), LJ ≈ 15.7% — confirms the monotonic widening and KQo entering by UTG+1/UTG+2. https://www.mypokercoaching.com/optimal-cash-game-opening-ranges-100bb/
- RangeConverter — 9-Max 100bb NLHE Charts (doc 05's baseline grid). https://rangeconverter.com/articles/poker-charts-9-max-100bb-no-limit-texas-holdem

**Repo anchors:**
- `docs/research/01-preflop-strategy.md` — §1 Rake Reality, §3A EP ranges, §5 value-only-merged 3-bet, §6 responding to 3-bets, §7 4-bets nutted, §13.8 "Fix EP range leaks."
- `docs/research/05-preflop-validation.md` — §1 tighter-than-solver doctrine, §2.2 vs_RFI value-only, §3.2 (**superseded here for nesting**), §3.3 vs_RFI LJ/CO/BTN gap-fills (pointer only).
- `docs/ai-dlc/research/RES-A-preflop-ranges.md` — the full decision doc, incl. the seat-model blocker investigation and the R4 hand-off tables.
