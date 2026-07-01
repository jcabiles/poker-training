# Tickets — Cheap-wins bundle (first build of the learning-rebalance)

Approved first build. Highest visible improvement for lowest cost/risk. Backs onto the verified research
docs 05/06/08 (present in-repo) and the SOTA UX findings. Doctrine: simplified-but-winning.

## Backend / accuracy errata (owner: one backend agent — shared test files, so NOT parallelized)
- **CW-1 — Preflop content errata** (doc 05): `content/preflop/rfi.json` drop **UTG KQo** + **HJ QJo**;
  `content/preflop/vs_4bet.json` trim **QQ** from CO-facing-UTG call. Update affected tests.
- **CW-2 — Postflop grader errata** (doc 06): `backend/app/domain/postflop.py` — wire the computed-but-unread
  `Texture.suitedness` (monotone → c-bet less often/smaller) + `Texture.pairing` (paired → elevated defender
  check-raise) into the merit fns; add the **ace-high exception** to `range_advantage()`. Follow doc 06's target
  freqs. Riskiest ticket — minimal, documented changes + tests.
- **CW-3 — hand_rank pairs** (doc 08): `backend/app/domain/hand_rank.py` — fix pocket-pair undervaluation per
  the computed equity ordering; keep deterministic tie-break. + tests.
- **Done:** `cd backend && python -m pytest -q` green + `ruff check .` clean. (Skip the boot probe — dev server
  already occupies :8008 and the sandbox can't bind a second.)

## Frontend / UX cheap wins (owner: App.tsx is a hotspot — sequential, not parallel across these)
- **CW-4 — 2-axis mode IA** *(Wave 1)*: `frontend/src/App.tsx` — reorganize the flat 7-button MODES row into
  **labeled groups** (Preflop-practice: Random/Review/Leak-focus/Exploit · Postflop-situations: Postflop/Facing
  c-bet/Facing check-raise). Frontend-only regroup+labels (backend `mode` enum unchanged). `npm run typecheck && build`.
- **CW-5 — Feedback teaches the why** *(Wave 3)*: `FeedbackPanel.tsx` — surface `rationale`/`rationale_tags`
  (verify API exposes them; add to response+types if not). Consistent decision-quality tier styling.
- **CW-6 — Study vs test** *(Wave 3)*: render the answer grid **absent pre-decision, reveal after answer** + a
  study/test toggle. `App.tsx` + `RangeGrid.tsx`.
- **CW-7 — Accessibility** *(Wave 3)*: ARIA (W3C APG grid+toolbar) on `RangeGrid`/`DecisionBar`; live-region
  announce feedback; fix focus stranding on disabled buttons post-grade.

## Waves
- **Wave 1 (now, parallel, disjoint):** CW-1/2/3 (backend errata agent) ‖ CW-4 (frontend IA agent).
- **Wave 2:** refuter/verify (maker ≠ checker) — backend correctness of CW-2/CW-3 + pytest/ruff; frontend build + nav check.
- **Wave 3:** CW-5 · CW-6 · CW-7 (frontend, sequential on shared files) → verify.

## Follow-ups (from the Wave-2 refuter — non-blocking, logged at commit of Wave 1)
- **CW-3b — equity-anchor pocket-pair ranks.** CW-3's `0.03→0.045` coefficient bump was **REVERTED during the
  merge with `main`** (#7 Challenge mode): the bump broke `test_hand_rank.py`'s `TIED_PAIRS` invariants (it
  un-ties pairs like 88≈KQo) and shifts the rank order Challenge's edge-score depends on. It had also nudged
  66 above AJo. The proper fix per doc 08 is to anchor pair ranks to the **computed equity ordering** — and it
  must reconcile with `test_hand_rank.py`'s determinism/tie model (update those expectations deliberately, don't
  just bump a coefficient). Dedicated ticket; pocket-pair undervaluation persists until then (zero grading
  blast radius today — no shipped chart's `_range_floor` is a low pair).
- **CW-2b — vs-check-raise pairing note.** Doc 06 named `_merits_vs_check_raise` alongside `_merits_vs_cbet` for
  the missing `texture.pairing` read; Wave 1 patched only the latter (defensible — no solver data for hero's
  post-check-raise re-raise, and the doc protects that fn's fold-heavy live prior). Add a one-line code comment
  documenting the deliberate scope call; revisit if solver data lands (Phase 3).
- **Pre-existing:** `HAND_RANK` dict tie-break is `PYTHONHASHSEED`-dependent (not introduced by this diff; no test
  flakiness across 7 seeds). Note only.
