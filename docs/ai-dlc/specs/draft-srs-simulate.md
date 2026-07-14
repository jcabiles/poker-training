# DRAFT spec — SRS integration for Simulate spots

> **STATUS: DRAFT — Gate-1 interview NOT held. Do not build.** Prepared 2026-07-12.
> Roadmap: NEXT item "SRS integration for Simulate spots."

## Goal (one line, provisional)
Let genuine, signature-clean Simulate blunders seed the spaced-repetition queue so the
mistakes you make in-game become the reps you review — without polluting the queue with
off-depth/multiway noise (the reason this was held out of v1).

## Known facts (from current code/contracts)
- `spot_signature()` is FROZEN (invariant — changing it orphans SRS history). Any sim
  spot entering SRS must map to an EXISTING canonical signature, not a new shape.
- S10's `grade_map` already produces canonical `Spot`s for HU-canonical shapes only —
  exactly the signature-clean subset. Its mapped Spot CAN legally flow to
  `record_attempt()` (the S10 prohibition existed because S10 explicitly wrote no SRS).
- Coverage gate (`NOT_FOUND` ⇒ no persistence) already prevents junk writes.
- SRS reviews happen in Practice's due queue (`srs_item` + review flow) — no new UI
  strictly needed; sim-seeded items would just appear as due spots.

## Open Gate-1 questions (user must answer)
1. Seed on which verdicts — blunders only, or mistakes too?
2. Depth filter: only ~100bb spots (packs assume it), or a tolerance band (e.g. 80–120)?
3. Should a sim-seeded SRS item be marked/visible as "from Simulate" in the due queue?
4. Frequency cap — one SRS write per signature per session, or every occurrence?
5. Does the user want an opt-out toggle?

## Constraints (inherited, non-negotiable)
`spot_signature()` untouched · only `grade_map`-mapped (HU-canonical, full-confidence)
spots may reach `record_attempt` · coverage gate stays load-bearing · every schema change
ships a migration (likely none needed) · no SRS write for no-baseline decisions ever.

## Verify-by (provisional)
A sim blunder on a mapped spot creates/updates exactly one `srs_item` with an existing
signature shape; multiway/off-depth spots create zero; Practice queue shows it due;
verify.sh green.
