# R4 — Preflop coverage: fill UTG+1/UTG+2 + all node contexts

**Status:** spec (Gate-2 pending) · **Consumes:** `docs/ai-dlc/research/RES-A-preflop-ranges.md` · **Wave:** W1 (‖ R3 ‖ R5) · **Appetite:** ~1 epic.

## 1. Goal / outcome-link
Early seats UTG+1 / UTG+2 have no preflop ranges → hero is un-gradeable and the preflop chart shows "no chart yet" there. Fill them so a UTG1/UTG2 hero gets a baseline verdict + a populated chart. Moves the north-star **preflop-decision coverage** metric toward ≥90%.

## 2. Locked interview decisions (2026-07-16)
- **Minimal persona scope:** add UTG1/UTG2 to `content/preflop/*` (grading + chart coverage) only. **Leave `nit`/`calling_station`/`passive_fish` on their existing wildcard node** — no persona stat-band re-tune, no S3/S4 regression risk. `tag`/`lag`/`maniac` already carry explicit UTG1/UTG2 nodes (no change).
- **Single representative vs-3bet facing per new seat** (per RES-A: range shape is facing-invariant at these stakes — breadth, not strategy). Author exactly the entries RES-A §10 specifies.
- Node contexts in scope: **RFI, vs_RFI, vs_3bet** for UTG1/UTG2 (RES-A §10). `vs_4bet` / `blind_defense` / `vs_limpers` for these seats are **non-spots** (RES-A §7) → author nothing; they stay `None`/unmappable structurally.

## 3. Contract map (from R4 scan, file:line anchors)
- **`RFI_POSITIONS` is the live gate** — `backend/app/domain/scenarios.py:48-55`, currently `[UTG, LJ, HJ, CO, BTN, SB]`. `_OPEN_SIZE` (`scenarios.py:60-69`) **already** has `UTG1:3.0`/`UTG2:3.0` — not the gate. Adding UTG1/UTG2 here is required for the RFI sampler to select the seat.
  - **Shared with Challenge mode** (`backend/app/domain/challenge.py:70,103,136,166,208`): the list is one pool; adding seats grows Challenge's `(position,hand)` sampling space 6→8. **Accepted/expected** (Challenge covering more seats is a feature, not a regression) — call it out in the ticket + re-run `test_challenge.py`.
- **`_find_entry` / registry lookup is a pure ungated linear scan** — `scenarios.py:307-316`, `backend/app/domain/content/registry.py:20-37`. Once JSON entries exist, every consumer (sampler, `grade_map_preflop._preflop_spot`, chart) resolves them with zero code change.
- **`spot_signature()` additive-safe** — `backend/app/domain/srs.py:48-68` hashes `spot.hero.position.value` raw as one `|`-joined part. New strings `"UTG1"`/`"UTG2"` mint new hashes; every existing part is byte-identical. **No renumbering.** (Risk only if the signature *function* is touched — out of scope.)
- **`grade_map_preflop` has no position allowlist** — `backend/app/domain/table/grade_map_preflop.py:62-229` gates only on `_BLIND_POSITIONS` + sizing bands. UTG1/UTG2 pass through unchanged once content exists. `_map_vs_3bet` (line 131) rejects only blind hero openers → UTG1/UTG2 openers facing a 3-bet grade as soon as a `vs_3bet` entry with the authored facing exists.
- **Content JSON schema already enumerates UTG1/UTG2** — `content/schema/contentpack.schema.json:142-156`, `persona.schema.json:91-105`. **No schema-file edit.** Pydantic `Entry.position: Position` (`content/models.py:41-49`) already accepts them.
- **Entry shapes to author** (exact fields): RFI `content/preflop/rfi.json:7-13` `{node_context, position, actions:[{action:"raise",combos,frequency:1.0}], sizing_bb, rationale}`; vs_RFI `vs_rfi.json:8-16` adds `facing` + `call` action; vs_3bet `vs_3bet.json:9-16` `position`=opener(hero), `facing`=3-bettor, actions `raise`(4bet)+`call`.
- **Preflop chart is content-driven** — `GET /simulate/{id}/preflop-chart` (`backend/app/api/v1/simulate.py:90-99`) → `sim_session.preflop_chart` (`sim_session.py:636-665`) → `range_grid(lookup(...))` + `_node_label`. UTG1/UTG2 spots render with **zero code change** once content exists. `_node_label` (`sim_session.py:597-610`) emits "UTG1 open (RFI)" etc. from `position.value`. FE `SimRangeChart` + `PokerTable.tsx:11` `RING` already include UTG1/UTG2.
- **Leak categorization already maps UTG1/UTG2** → `grading.py:44-46,61-62` (`RFI_EP`, seat priority). Pre-existing, not R4's work.

## 4. Changes
**Content (the bulk):**
1. `content/preflop/rfi.json` — add UTG1, UTG2 RFI entries (RES-A §10 combos, `sizing_bb:3.0`).
2. `content/preflop/vs_rfi.json` — add UTG1, UTG2 vs_RFI entries (facings per RES-A §10).
3. `content/preflop/vs_3bet.json` — add UTG1, UTG2 vs_3bet entries (single representative facing per RES-A).

**Backend (one line + tests):**
4. `backend/app/domain/scenarios.py:48` — add `Position.UTG1, Position.UTG2` to `RFI_POSITIONS`.

**No FE code change** — chart + seat ring already data-driven.

## 5. Pass/fail
- A hand where hero is UTG1/UTG2 gets a baseline verdict (not "no baseline yet") for **RFI** and **vs_RFI** spots, and a populated preflop chart (grid, not "no chart yet"). *(test: build a HandState with hero at UTG1 folded-to, assert `map_decision_point` returns a Spot + `preflop_chart` `available=True`.)*
- **vs_3bet coverage is partial by design** (refuter med): only the single representative facing RES-A §10 authors is gradeable; a UTG1/UTG2 opener 3-bet by a *different* seat resolves to `None` (unmappable) — structurally identical to today's UTG-vs-BTN-only gap (`content/preflop/vs_3bet.json` authors one facing per opener; `registry._key` requires exact facing equality). Acceptable per RES-A; do NOT claim full vs_3bet coverage.
- **Update `test_grade_map.py::test_off_pack_rfi_position_returns_none`** (refuter HIGH): it currently uses **UTG1** as its canonical "off-pack ⇒ None" example (`test_grade_map.py:473-476`). Once UTG1 RFI content exists this test flips — repoint it to a position that stays genuinely unmapped (or assert UTG1 now maps). **This test is in R4's ownership even though §7's original file list omitted it.**
- **Existing preflop `spot_signature()` values byte-unchanged** — golden test over the pre-R4 position set (UTG/LJ/HJ/CO/BTN/SB/BB) still produces identical hashes.
- Persona VPIP/PFR/3-bet **stat bands still hold** (`test_personas.py::test_persona_stat_bands`) — unchanged because personas untouched.
- vs_4bet/blind_defense/vs_limpers at UTG1/UTG2 still return `None` (non-spots — assert unmappable).
- `test_challenge.py` green with the grown position pool.
- `verify.sh` + `cd frontend && npm run typecheck && npm run build` green.

## 6. Refuter-target risks (verify before build)
- Does adding UTG1/UTG2 to `RFI_POSITIONS` break any **seeded-distribution test** that assumes a fixed position count (beyond `test_persona_stat_bands`, which derives membership dynamically)? Sweep `test_scenarios.py` / `test_challenge.py` for hardcoded `len(RFI_POSITIONS)==6` or sample-count assumptions.
- Does the `PersonaNode._node_ordering` validator (`content/models.py:184-208`) matter here? Only if persona files are touched — they are NOT in the minimal scope. Confirm no persona edit sneaks in.
- Confirm RES-A §10 combos actually nest (UTG⊆UTG1⊆UTG2⊆LJ) as RES-A claims — a golden nesting assertion.

## 7. File ownership (W1 disjointness)
R4 owns: `content/preflop/*.json`, `scenarios.py` (`RFI_POSITIONS` line), `grade_map_preflop.py` (if any tweak needed — likely none), new tests. **Does NOT touch** `postflop.py`, `grade_map_postflop.py`, `sim_session.py` hero-actions, `content/personas/*`, FE action bar. No overlap with R3/R5.

## 8. Tickets (outline)
- **T1** — Author UTG1/UTG2 RFI + vs_RFI + vs_3bet content entries from RES-A §10; nesting golden test (UTG⊆UTG1⊆UTG2⊆LJ).
- **T2** — Add UTG1/UTG2 to `RFI_POSITIONS`; sweep + fix any fixed-count test assumptions; refresh stale `challenge.py:60,109,160` "6 RFI seats / 6x169" docstrings → 8 (refuter LOW; code already dynamic).
- **T3** — Golden test: preflop `spot_signature()` byte-stable for the legacy position set; UTG1/UTG2 RFI+vs_RFI gradeable + chart-populated; non-spots stay `None`. **Repoint `test_off_pack_rfi_position_returns_none`** off UTG1 (refuter HIGH).
