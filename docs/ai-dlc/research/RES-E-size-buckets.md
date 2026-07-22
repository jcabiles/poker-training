# RES-E — Size-bucket taxonomy (the residual RES-B pre-answered)

**Spike, Epic 4 (bot-math-fix). Output = decision doc. NO app code.** Created 2026-07-21.

**Why this is light:** Epic-2's **RES-B** (`docs/ai-dlc/research/RES-B-bet-sizing.md`) already
found the persona sizing *values* correct/defensible for live $2/$3 (the reported unrealism was
the node-agnostic flat distribution + missing turn/river nodes, not wrong numbers). So RES-E's
only job is to name the **discrete size buckets** F1's defense logic and F2's bluff logic key
on, and map the existing engine sizes onto them. It invents **no new sizing numbers**.

---

## 1. The existing size vocabulary (from the code, not new research)
- **Persona `postflop.sizing` keys** (all packs): `0.33, 0.5, 0.75, 1.0`, plus the maniac's
  `1.5` overbet key. **[SOURCED — content/personas/*.json + RES-B §5.2]**
- **`POSTFLOP_BET_FRACS`** (`sizing.py`, single source for offered/graded bet sizes): flop
  `(0.33, 0.75)`, turn `(0.5, 0.75)`, river `(0.5, 1.0)`. **[SOURCED — sizing.py]**
- **`FACING_RAISE_MULTS`**: check_raise `(2.5, 3.5)`, raise `(2.5, 3.0)` (multipliers on the
  faced bet, not pot-fractions — resolve to a pot-fraction via the raise formula). **[SOURCED]**

## 2. The bucket taxonomy (finalizes RES-D §2's provisional cutoffs) — **[DERIVED]**
Four buckets, keyed to the α fold-ceiling line (RES-D §1a) so F1's faced-size→fold logic and
F2's chosen-size→bluff logic share one vocabulary:

| Bucket | Pot-fraction range | Engine sizes that land here | α (fold ceiling) | polar bluff share |
|---|---|---|---|---|
| **SMALL** | ≤ 0.40 | 0.33 | ~25% | ~20% |
| **MEDIUM** | 0.41 – 0.70 | 0.5, 0.67 | ~33–40% | ~25–29% |
| **LARGE** | 0.71 – 1.10 | 0.75, 1.0 | ~43–50% | ~33% |
| **OVERBET** | > 1.10 | 1.5 (maniac) | ~67% | ~40% |

**Boundary rulings (locked):**
- Cutoffs are on **pot-fraction = faced_or_chosen_bb / pot_bb**, computed at decision time —
  NOT on the discrete authored keys (a bot/hero bet is a continuous bb amount; F1 maps it to a
  bucket by its live pot-fraction). This is what lets F1 respond to *any* faced size, including
  irregular ones.
- `1.0` (pot) sits in **LARGE**, not its own bucket — its α (50%) is within the LARGE band's
  spread and keeping one fewer bucket keeps the tables legible; the α value used is still the
  size-exact one (RES-D §1a) when the fraction is a recognized key.
- The maniac `1.5` is the only current OVERBET size; the bucket exists so F1/F2 don't have to
  special-case it and so future overbets route correctly.

## 3. How F1 / F2 consume this
- **F1 (faced defense):** compute the faced pot-fraction → bucket → look up the persona's
  fold-to-bet target band for that bucket (RES-D §2). The **monotone-in-size** invariant means
  the four buckets must produce a strictly non-decreasing fold rate per persona.
- **F2 (chosen bluffing):** when a persona chooses a size (sampled from its `postflop.sizing`
  distribution), map that size → bucket → apply the bucket's target value:bluff (RES-D §3). The
  size is still drawn independently of hand strength (anti-sizing-tell); F2 only makes the
  *bluff frequency* consistent with the chosen bucket.

## 4. Pass/fail (self-check)
- [x] Names the size buckets + their pot-fraction cutoffs.
- [x] Maps every existing engine size (`0.33/0.5/0.67/0.75/1.0/1.5` + `POSTFLOP_BET_FRACS`) onto
      a bucket.
- [x] Cites RES-B for the values; introduces **no new sizing numbers**.
- [x] No app code; no bet-size sliders; sizes stay FIXED.

**Open call to F1/F2:** whether to store the α/bluff targets as a per-bucket table or compute
them size-exactly from the RES-D closed forms is a code-shape choice for the build slice; this
doc fixes the bucket boundaries and the mapping rule, not the storage.
