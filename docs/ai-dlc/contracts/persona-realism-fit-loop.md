# Persona-Realism Harness Fit Loop (D11)

> The repeatable loop every behavior slice runs to turn a grounded *direction*
> into a *fitted magnitude*, plus the single-re-anchor rule. Referenced from the
> W0 spec (`persona-realism-w0-foundation.md`) and the roadmap's cross-cutting
> discipline (`docs/ai-dlc/roadmap/persona-realism.md`).

## Why a loop, not a constant (the softmax law)

The engine clamps each candidate merit `≥0`, normalizes by the sum, then draws
via `rng.choices`. **A merit multiplier is therefore NOT the observed frequency
change** (theory contract §2). Dropping `×0.75` / `×0.50` into the code and
closing the slice ships a *cosmetic* change — the observed stat has not moved to
target. Every magnitude in the build spec is a **fit seed**, not an answer.

## The loop (per behavior slice)

1. **State the target as an observed stat**, not a merit. A CBet-flop split, an
   AF, a WTSD, a size-bucketed fold-to-cbet slope — a number a harness metric
   emits (theory contract §5/§6). Not "the multiplier is 0.5".
2. **Seed the multiplier** with the build-spec's directional value.
3. **Measure** the relevant metric via the harness (`_persona_stats` for the
   three HARD-today stats; `_persona_stats_ext` for the six W0-b metrics).
4. **Adjust the seed** toward the target band and re-measure. Repeat until the
   *observed* stat lands (or is provably directional if the metric is not yet
   HARD-gatable — see the Metric-DoD rule).
5. **Check the node, not just the number** — run the seeded node-trace pack
   (`backend/tests/node_trace.py`) for the affected personas/spots and confirm
   the *shape* of the decision is coherent (e.g. a maniac hitting its aggression
   number by bluffing air, not by over-valuing made hands). This catches "right
   stat, WRONG node".

## Precedents already in the tree

- **The band fit loop** that produced the current `BANDS` is documented inline
  at `backend/tests/test_personas_postflop.py:1337-1480` (measure → 3σ CI →
  round outward). Reuse that method; do not invent a second.
- **The six new metrics** (`_persona_stats_ext`) are the measuring tape for the
  mechanics that were previously prose-only.
- **The node-trace pack** (`node_trace.py`) is the anti-degeneracy check.

## Two rules that bound the loop

- **Metric-DoD (D7):** a slice may not close on a HARD gate until the metric it
  needs is *live AND showing the expected direction*. Until then the gate is
  DIRECTIONAL, not HARD (theory contract §6). W0-b made the six metrics live;
  each later slice supplies the direction.
- **Single re-anchor at the cluster end (D11):** the population WTSD/AF bands are
  moved by several mechanics (P3/P5/P6/P8). **Re-anchor them ONCE, after the
  whole cluster lands (Wave 4)** — never mid-spine. Re-anchor levers-first (tune
  pack levers before widening test bands). The only early-wave test edit is P5's
  unit-assertion split. Chasing bands across waves re-fits values that the next
  slice moves again (theory contract §7).
