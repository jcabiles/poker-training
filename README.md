# Poker Trainer — local NLHE trainer

A local web app to drill and train live No-Limit Texas Hold'em strategy, tailored
for the $1/$2 → $2/$3 climb. Simplified-but-sound (not pure GTO), preflop first.

Plan: `docs/ai-dlc/roadmap.md` · Strategy research: `docs/research/` · Spec/tickets: `docs/ai-dlc/`.

## Layout
```
backend/   FastAPI API + pure domain core + SQLite/Alembic
frontend/  React + Vite
content/   strategy content packs + JSON schema
docs/      research, roadmap, specs, tickets
scripts/   dev.sh, verify.sh
```

## Architecture (why it scales)
- **Pure domain core** (`backend/app/domain/`) — Spot, Decision, EvaluationResult,
  content packs, SRS, leaks. No web/DB imports (enforced by a test).
- **Swappable `StrategyProvider`** — grading is one async interface. Today a
  heuristic provider; a solver-table provider drops in later with no rebuild.
- **Strategy as versioned data** — ranges live in content packs, not code.
- **Freq + EV results, never boolean** — feedback/SRS/leaks all consume the rich shape.

## Screenshots
| Preflop trainer | Facing aggression | Exploit archetypes | Postflop equity |
| --- | --- | --- | --- |
| ![Preflop trainer](docs/assets/preflop-trainer.png) | ![Facing aggression](docs/assets/facing-aggression.png) | ![Exploit archetypes](docs/assets/exploit-archetypes.png) | ![Postflop equity](docs/assets/postflop-equity.png) |

## Setup & run

**Backend** (Python ≥ 3.12):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

**Frontend** (Node ≥ 20):
```bash
cd frontend
npm install
```

**Run** (one command — backend on :8008 + frontend on :5173, backend dies on exit):
```bash
./scripts/dev.sh
```
Open `http://localhost:5173`. API health: `http://localhost:8008/api/v1/health` · interactive docs at `/docs`.

Or run separately (two terminals):
```bash
# backend — API on :8008
cd backend && uvicorn app.main:app --port 8008 --reload
# frontend — UI on :5173
cd frontend && npm run dev
```

**Checks:**
```bash
./scripts/verify.sh          # backend tests + boot probe
cd backend && ruff check .   # lint
cd frontend && npm run typecheck && npm run build
```

## Status
**Phase 0** (foundations) complete & verified. **Phase 1a** (real preflop trainer) built:
research-backed ranges for RFI / facing-an-open / blind defense / vs-limpers, frequency-tolerant
grading, SM-2 spaced repetition, auto leak tracking, drill modes (random / review / leak-focus),
and a lean React UI (multi-action bar, mode selector, colored 13×13 grid, stats strip).
**Phase 1b** adds facing-aggression (vs-3-bet 4bet/call/fold, vs-4-bet jam/call/fold) + a
betting-line display + light stack-depth variety. **Phase 1c** adds exploit / villain-archetype drills
(calling station / nit / LAG / fish) with a GTO-vs-exploit contrast on high-leverage nodes.

**Phase 2a — first postflop slice — built & verified (128 backend tests green):** a pure-Python
equity engine (7-card evaluator + Monte-Carlo `equity_vs_range` with dead-card filtering), a
rule-based board-texture classifier, a dedicated flop **c-bet grader** (texture + positional
range-advantage heuristic, *not* equity-backed — that's 2b), a `CompositeProvider` routing by street
(preflop → heuristic, flop → postflop), a flop-c-bet drill mode, and two foundational quizzes
(board-texture classification, equity estimation) with tolerance-band grading. Postflop spots get a
texture/SPR-bucketed signature; preflop hashes are byte-identical to before. No new DB migration.

**Phase 2b — facing a flop c-bet (defense) — built & verified (141 backend tests green):** the other
side of the 2a spot — hero (BB) defends vs a flop c-bet with **fold / call / raise (check-raise)**,
graded by a defender-perspective range-advantage rule + `grade_vs_cbet` (texture + range advantage +
pot-odds/MDF + a bet-size term), a `vs_cbet` spot builder + drill mode, and a **faced-bet bucket** in
the postflop signature so small vs big c-bets stay in separate SRS items. Still not equity-backed; no
new DB migration.

**Phase 2c — postflop SRS review — built & verified (148 backend tests green; migration 0004):** the
flop **c-bet** and **vs-c-bet** spots now re-surface in `mode=review` via SM-2, keyed on their
texture/SPR/faced-bet archetype. `srs_item` gains 4 nullable postflop columns; `record_attempt`
persists + backfills them; `_rebuild_postflop` reconstructs a due archetype from the 2a/2b builders; a
`Spot.srs_signature` override guarantees the due row graduates even when reconstruction is approximate.
This closes the core *surface → drill → re-surface until mastered* loop for postflop.

**Phase 2d — equity-backed range advantage — investigated, then deferred to Phase 3.** A bounded
Monte-Carlo over the simplified ranges can't recover a stable range-advantage signal (mean equity is
flat ~0.5; combo-share is range-width-biased; top-of-range strength is noisy/counterintuitive) — real
range advantage is a solver/EV property. The stable positional+texture heuristic was kept; the swap to
solver-backed range advantage lands in Phase 3 behind the existing `StrategyProvider`. (FeedbackPanel
polish — per-action sizes — shipped.)

**Phase 2e-0 — foundational fixes — built & verified (163 backend tests green):** paydown before
turn/river. There was no street-level dispatch past preflop — a turn/river spot would be silently
graded as a flop. Fixed: the postflop provider now street-gates to the flop (turn/river →
`NOT_FOUND`); `faced_bet_bucket` is raise-aware (reads the current `CALL`, subtracting hero's prior
street investment) instead of scanning history for a max bet; `_hand_category` now detects made
straights/flushes AND demotes plain top pair from `strong` to `weak_made` (a live bug that had
`grade_vs_cbet` recommending "never fold" with a marginal top pair); all `texture.classify()` call
sites slice `board[:3]` explicitly. No new migration.

**Phase 2e-1 — facing a flop check-raise — built & verified (183 backend tests green):** hero c-bet,
the defender check-raised, and hero (the original aggressor) decides **fold / call / raise (sized
4-bet)**. `grade_vs_check_raise` encodes the live-$1/$2 read that *check-raises are rarely bluffs* as a
markedly higher fold baseline than the c-bet-defense grader — modulated (not overridden) by texture, so
air still folds on dry boards. A `build_check_raise_spot` builder (with the correct *incremental* call
size — `raise_to − cbet`, not the raw raise total), a `vs_check_raise` drill mode + SRS-review
reconstruction, leak `VS_CHECK_RAISE=202`, and a frontend mode + a street-scoped betting-line fix (a
flop check-raise no longer mislabels as a preflop "3-bet"). Closes the flop c-bet loop. No new migration.

Next: turn play (2nd barrel, needs street-aware texture) → facing a turn bet → river value/bluff →
facing a river bet → multiway → full-hand mode. Sequenced one-epic-per-session in `docs/ai-dlc/roadmap.md`
(§ Phase 2), with the contract scan in `docs/ai-dlc/contracts/postflop-turn-river.md`.

## How this was built
Developed with an AI-assisted, spec-first workflow: each phase started from written research and a
delta spec (`docs/`), was broken into tickets, then implemented and verified against tests before the
next phase. The architecture (pure domain core, swappable strategy provider, content-as-data) was
chosen up front so later phases extend rather than rewrite.
