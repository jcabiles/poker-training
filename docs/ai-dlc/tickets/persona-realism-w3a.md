# W3-a tickets (Just-ahead context plumbing)

Spec: `docs/ai-dlc/specs/persona-realism-w3a.md`. Build serial, one PR. Owned hotspots
(`personas_postflop.py`, `play.py`) are single-owner — no parallel worker touches them.

- [x] **T1 — new pure module.** `app/domain/table/postflop_context.py`: `BustedDraw`
  IntEnum, `PostflopContext` NamedTuple (defaults = today), `derive_in_position` (A2),
  `bet_prev_street` (A3), `busted_draw_kind` (A4), `derive_postflop_context`. Domain-pure,
  reuses `strength_bucket`. **Done:** module imports with no cycle.
- [x] **T2 — sampler param.** Add `context: PostflopContext | None = None` to
  `sample_postflop_decision` (TYPE_CHECKING import); docstring note; **not read**.
  **Done:** `ruff` clean; existing sampler callers byte-identical.
- [x] **T3 — production wire.** `bot_decision` derives + threads context through
  `_postflop_decision`. **Done:** coverage + limper fixtures pass with no re-record.
- [x] **T4 — derivation unit tests.** `tests/test_postflop_context.py` — 18 tests across
  A2/A3/A4 + bundle. **Done:** all pass.
- [x] **T5 — verify gate.** `./scripts/verify.sh` green (912 passed, 1 skipped — the W2
  maniac WTSD defer), boot probe OK, `ruff check .` clean.
- [ ] **T6 — fan-in review + PR.** refuter + Codex Sol on the diff; fold findings; open PR 1.
