# Spec — S10: Grading wired in (live badge + end-of-hand recap + tagged attempts)

> Slice S10 of `docs/ai-dlc/roadmap/simulate-table.md` (mark `[x]` when pass/fail below holds).
> Contract map: `docs/ai-dlc/contracts/simulate-s10-s11.md`. Gate-1 decisions embedded below.
> Outcome-link: primary metric (per-street decision accuracy / EV-loss) becomes measurable in-sim.

## Goal (one line)
Grade each hero decision in a Simulate hand via the existing `StrategyProvider` stack (baseline only), show a per-decision color badge + an end-of-hand recap, record tagged attempts, and expose a minimal all-time per-street report — without any SRS write and without ever grading an unmapped spot silently.

## Gate-1 decisions (locked 2026-07-11; report stretch added 2026-07-12)
- **Storage = both tables.** `sim_decision` (new) holds the rich per-decision verdict for badge + recap. A tagged `drill_attempt` row (`source='simulate'`) is ALSO written so sim leaks flow into stats. **No `record_attempt` call, no SRS row.**
- **Scope = accept sparse baseline.** Grade only HU-canonical spots that match existing content (preflop RFI/vs-RFI HU; HU flop c-bet). Everything else (multiway, off-size, off-pack, turn/river multiway) → `Coverage.NOT_FOUND` → "no baseline yet." Multiway grading stays a Next item.
- **UI = badge on hero pod + new `SimRecap` sibling.** SimShowdown stays settlement-only.
- **Per-street report (scope add 2026-07-12, explicit user vision: "track my decisions at
  each street → show me analytics on good/bad/acceptable per street").** One aggregate
  endpoint over `sim_decision` — ALL-TIME (across sessions), grouped by street: graded
  count, verdict-tier mix, EV-loss sum (≈ label), no-baseline count. Rates EXCLUDE
  no-baseline rows (same aggregate rule as the recap); coverage shown as its own count so
  sparse v1 grading is honest, not hidden. FE = one compact numbers-only panel in the
  Simulate view (visible with or without a live session). NO charts, NO per-session
  filtering, NO positional breakdown — those are the promoted "session analytics" NEXT item.

## Files / interfaces to touch
**Backend**
- `backend/app/db/models.py` — new `SimDecision` model; add `source: str = Field(default="practice")` to `DrillAttempt`.
- `backend/alembic/versions/0010_sim_decision_and_source.py` — additive: create `sim_decision` table (0009 pattern, `owner_id=""` sentinel, FK-ish indexes on `session_id`/`sim_hand_id`); add nullable-with-default `source` column to `drill_attempt`. Symmetric `downgrade()`.
- `backend/app/domain/table/` — NEW pure-domain helper(s) mapping a live hero decision point → `Spot | None` (returns `None` = unmappable). Must stay web/DB-free (purity test); add module to the `test_domain_purity.py` allowlist. Classifies only HU-canonical shapes; returns `None` for anything it can't build with full confidence.
- `backend/app/services/sim_session.py` — in `apply_hero_action`, BEFORE `apply()` mutates state: map pre-decision state → `Spot`; if mapped, `await provider.evaluate(spot, decision)`; apply the coverage gate; on non-NOT_FOUND, write a `SimDecision` row + a tagged `DrillAttempt(source='simulate')` row; on NOT_FOUND (or unmappable), write a `SimDecision` row flagged "no baseline yet" (for recap completeness) and NO `drill_attempt`. Reuse the `drill.py` provider singleton. Surface the just-taken verdict on the response.
  **Transaction boundary (refuter med-1):** `db.add()` the `SimDecision`/`DrillAttempt` rows but do NOT `commit()` them separately — let them ride the single existing `db.commit()` at the end of `apply_hero_action` (`sim_session.py:288`), so a decision whose `apply()` raises `ValueError` (illegal action/size, `:278`) never leaves an orphaned graded row. Do NOT copy `drill.py`'s eager two-commit pattern (`drill.py:347`).
- `backend/app/schemas/simulate.py` — add `last_grade` (verdict for the decision just taken, nullable, includes a "no baseline yet" state) to the hand view; add a recap payload (per-decision verdict list for the finished hand) to the hand-over branch.
- `backend/app/api/v1/simulate.py` — endpoints return the new fields; a recap read path for the finished hand's `sim_decision` rows; a per-street report endpoint (all-time aggregate over `sim_decision`, shape per the Gate-1 report decision).
- `backend/app/services/stats.py` — add `WHERE source == 'practice'` to `leak_stats`, `summary`, `calendar`, `recap`, `hand_error_weights` so Practice dashboards exclude sim rows.

**Frontend**
- `frontend/src/api/types.ts` — mirror the new `last_grade` + recap response fields.
- `frontend/src/components/simulate/SimTable.tsx` — render a color badge (verdict tier / "no baseline yet") on the hero pod after a decision.
- `frontend/src/components/simulate/SimRecap.tsx` — NEW: per-street recap with freq/EV (≈ labels) + tiered "why" expanded for mistakes/blunders; mounts beside SimShowdown in the hand-over branch. **Aggregate rule (refuter low-4):** any freq/EV *summary* figure excludes NOT_FOUND/"no baseline yet" rows (they carry `correctness=None`, `ev_loss_bb=0.0` and would dilute accuracy/EV-loss); the per-decision list still shows them as a distinct "no baseline yet" badge state.
- `frontend/src/components/SimulateView.tsx` — thread `last_grade` into the badge; render `SimRecap` on `hand_over`; mount the per-street report panel (NEW small component, e.g. `SimStreetReport.tsx`, in the side column — visible with or without a live session).
- `frontend/src/styles/app.css` — new `.sim-*` classes for badge tiers + recap (tokens-only, AA both themes).

## Out of scope
Multiway / off-archetype grading (Next: exploit-aware + multiway teaching); SRS writes from Simulate; exploit-/persona-aware verdicts (baseline only); rich session analytics — charts/graphs, per-session filtering, positional breakdowns (promoted NEXT item; this slice ships ONLY the minimal numbers-only per-street report); pacing/polish (S11); solver EVs (labels stay ≈ approximate). No changes to `record_attempt`, `spot_signature()`, or any grader logic/thresholds.

## Constraints (invariants)
- Domain core (`app/domain/`) stays web/DB-import-free — the Spot mapper lives in domain and is purity-tested.
- Results are frequency + EV, never boolean.
- Grading stays behind the one async `StrategyProvider` (reuse the singleton).
- Every schema change ships an Alembic migration (0010, additive, up/down clean).
- `spot_signature()` frozen; sim `Spot` never enters it or `record_attempt`.
- No SRS writes from Simulate; `drill_attempt` gets tagged rows only.
- Never grade an unmapped spot silently — NOT_FOUND / unmappable ⇒ "no baseline yet," no `drill_attempt`.
- FE types hand-maintained in `types.ts`; CSS from tokens only; AA contrast + visible focus both themes.

## Verify-by (end-to-end)
- `./scripts/verify.sh` → `BACKEND VERIFY OK`; `cd backend && ruff check .`; `cd frontend && npm run typecheck && npm run build`.
- A deliberately-bad preflop HU play shows a red badge + blunder recap with non-tautological reasoning.
- A multiway/off-pack decision renders "no baseline yet" and writes NO `drill_attempt` row.
- Migration 0010 applies up AND down clean; existing `drill_attempt`/`sim_*` rows read back unchanged.
- Sim-tagged attempt rows carry `source='simulate'`; Practice `leak_stats`/`summary`/`recap`/`calendar`/`hand_error_weights` exclude them (test); a sim leak is queryable by source.
- Zero SRS (`srs_item`) rows created by a Simulate session (test).
- Per-street report: after playing graded + ungraded decisions, the panel buckets them by street; rates exclude no-baseline rows and the no-baseline count is displayed (test on the endpoint aggregate; visual check on the panel).
