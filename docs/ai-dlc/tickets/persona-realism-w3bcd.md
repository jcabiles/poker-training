# W3-b/c/d tickets (position / street / texture)

Spec: `docs/ai-dlc/specs/persona-realism-w3bcd.md`. Serial, one PR (shared hotspot).

- [x] **T1 — W3-b position.** `position_sensitivity` lever (models + tag/nit/lag content);
  `_position_agg_mult` on the unopened BET candidate. **Done:** CBet_IP > CBet_OOP for opted
  personas; station/fish/maniac + un-opted callers byte-identical; facing/matched-raise
  untouched. 7 unit tests.
- [x] **T2 — W3-c street schedule.** `_STREET_AGG_MULT` / `_STREET_WEAK_DRAW_MULT` decay
  bluff + semi-bluff (value untouched); busted-draw river bluff via `bet_prev_street` +
  `busted_draw`. **Done:** flop byte-identical; air bluff decays flop>turn>river; busted
  barrel boosts; weak semi-bluff → 0 by river. 5 unit tests + updated street pins.
- [x] **T3 — W3-d texture brakes.** `_overcard_count`/`_overcard_bet_damp` (B2) +
  `_wetness_bet_mult` (B3) on MIDDLE_PAIR/TOP_PAIR BET only. **Done:** made-pair bet-rate
  falls by overcard count + wetness; overpair/set untouched. 6 unit tests.
- [x] **T4 — fixtures + WTSD stabilization.** Re-recorded golden/coverage/limper
  (slice-authorized); WTSD assertions moved to fixed `_WTSD_ORDER_N=2500` (owner-approved
  "more hands") — bands + ordering stable, band values frozen. Coverage ratio dip flagged.
- [x] **T5 — verify gate.** `./scripts/verify.sh` green (931 passed, 1 skipped), boot OK,
  `ruff check .` clean; both WTSD tests stable across repeats.
- [ ] **T6 — fan-in review + PR.** refuter + Codex Sol on the diff; fold findings; open PR 2.
