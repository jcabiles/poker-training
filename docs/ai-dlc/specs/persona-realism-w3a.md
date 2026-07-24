# W3-a — Just-ahead context plumbing (A2/A3/A4)

**Slice of:** `docs/ai-dlc/roadmap/persona-realism.md` → W3 (context). First PR of the
two-PR W3 packaging (plumbing seam); W3-b/c/d ship as the second PR.

## Goal (one line)
Thread three derived situational inputs into the postflop sampler as a **walking
skeleton** — derived + unit-tested now, consumed later — so the position/street/texture
mechanics (W3-b/c/d) each have the one boolean they need.

## The three inputs (defaults = today's behavior)
- **A2 `in_position`** — true iff no still-live opponent acts after this seat on this
  street. Excludes FOLDED + ALL-IN seats (they don't act). BB **is** in position vs SB
  postflop; 3+-handed = the last live seat; lone live seat = trivially in position.
- **A3 `bet_prev_street`** — did this seat BET/RAISE on the immediately-preceding street?
  Per-street aggressor memory that separates a **barrel** (bet prev → True) from a
  **delayed stab** (checked prev → False) — the signal a correct c-bet-vs-barrel sizing
  node needs. Preflop RAISE counts as the flop's previous-street aggression (PFR c-bet).
  Fixes the whole-hand `is_aggressor` mislabel (F17) **at its source**; the sizing-node
  rewire is W3-c's consumption, not here.
- **A4 `busted_draw`** — provenance of a draw that missed by the river, preserved past
  the river's `DrawCategory.NONE` reset: `NONE < FLUSH < STRAIGHT` (IntEnum; a busted
  straight is more disguised than a busted flush whose missed suit shows on board — a
  PROXY, validate via LBR before treating the preference as hard). Fires only on a
  complete board where the turn subboard held a draw and the river left the hand unmade
  (still AIR/ACE_HIGH).

## Files
- **NEW** `app/domain/table/postflop_context.py` — `BustedDraw`, `PostflopContext`
  (NamedTuple, all defaults = today), the three pure derivations + `derive_postflop_context`.
- `app/domain/personas_postflop.py` — add `context: PostflopContext | None = None` to
  `sample_postflop_decision` (TYPE_CHECKING import to avoid a runtime cycle). **Not read
  yet.**
- `app/domain/table/play.py` — `bot_decision` derives the context, threads it through
  `_postflop_decision` into the sampler.
- **NEW** `tests/test_postflop_context.py` — derivation unit tests.

## Out of scope
No consumer of any input (no behavior change). No `is_aggressor`/sizing-node rewire
(W3-c). No persona lever (`position_sensitivity` etc. are W3-b+). No content edits.

## Invariants honored
Domain purity (new module has no web/DB import; reuses the ONE `strength_bucket`
classifier). Grading still flows through the sampler unchanged. `spot_signature()`
untouched. FE types untouched (no API change).

## Verify-by
`./scripts/verify.sh` green; `ruff check .` clean. **Byte-identity:** golden
(`test_personas_postflop`), coverage (`test_coverage_baseline`), and limper
(`test_limper_coverage_belt`) fixtures pass **with no re-record** — proof the walking
skeleton adds no rng-stream displacement. New derivation unit tests cover A2
(multiway / BvB / all-in / folded / button / lone), A3 (barrel vs delayed stab, PFR,
turn→river, no-predecessor, two-back), A4 (busted flush/straight, completed, no-draw,
pre-river, ordering) + the bundle.

## Review dispositions
_(folded from the refuter + Codex Sol fan-in — see the PR.)_
