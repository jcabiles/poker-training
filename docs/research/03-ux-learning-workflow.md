# UX & Learning Workflow Research
## Poker Training App — Solo NLHE Cash Game Player

**Scope:** UX patterns and learning-science pedagogy for a local single-player web app.
**Target user:** Competent novice winning at $1/$2 live NLHE, moving to $2/$3.
**Date:** 2026-06-27

---

## Table of Contents

1. [Part A — Learning Science & Pedagogy](#part-a--learning-science--pedagogy)
   - [Deliberate Practice (Ericsson)](#1-deliberate-practice-ericsson)
   - [Spaced Repetition & Retrieval Practice](#2-spaced-repetition--retrieval-practice)
   - [Interleaving vs Blocked Practice](#3-interleaving-vs-blocked-practice)
   - [Immediate, Explanatory Feedback](#4-immediate-explanatory-feedback)
   - [Mastery-Based Progression & Scaffolding](#5-mastery-based-progression--scaffolding)
   - [Error Review & Leak-Tracking Loops](#6-error-review--leak-tracking-loops)
   - [Motivation & Adherence — Gamification](#7-motivation--adherence--gamification)
   - [Transfer to the Table](#8-transfer-to-the-table)
2. [Part B — Concrete UX/UI Patterns](#part-b--concrete-uxui-patterns-for-poker-training)
   - [Hand Display](#1-hand-display)
   - [Range Visualization](#2-range-visualization)
   - [Feedback Panels](#3-feedback-panels)
   - [Session & Drill Structure](#4-session--drill-structure)
   - [Progress Tracking & Analytics](#5-progress-tracking--analytics)
   - [Input Speed & Keyboard Shortcuts](#6-input-speed--keyboard-shortcuts)
   - [Lessons from Adjacent Apps](#7-lessons-from-adjacent-apps)
3. [Part C — Novice-Specific Differences](#part-c--novice-specific-differences)
4. [Recommended Learning-Loop Blueprint](#recommended-learning-loop-blueprint)
5. [Sources](#sources)

---

## Part A — Learning Science & Pedagogy

### 1. Deliberate Practice (Ericsson)

**Core principle.** Ericsson's research establishes that expert performance is produced by "individualized training activities specially designed to improve specific aspects of an individual's performance through repetition and successive refinement" — not accumulated hours of undirected play. Raw talent plays a far smaller role than commonly assumed ([Casino.org](https://www.casino.org/blog/practice-in-poker/)).

**Four defining characteristics for poker:**

| Characteristic | What this means for a poker training app |
|---|---|
| **Specificity** | Each drill targets one narrow situation (e.g., "BTN open vs BB 3-bet, facing a flop c-bet on a two-tone board"). Not "practice poker." |
| **Beyond-current-skill challenge** | Drills should sit at the edge of the player's ability — slightly harder than comfortable. The app must not default to easy, familiar spots. |
| **Immediate, accurate feedback** | This is poker's hard problem: live play gives delayed, noisy feedback (luck conflates with skill). The app substitutes a GTO solver as the feedback oracle, surfacing the ground truth on every decision. |
| **Effortful repetition** | Drills must be cognitively engaging, not passive. Clicking through hands without reflection does not qualify. The app should interrupt flow after mistakes to force reflection. |

**Key constraint.** Intensive deliberate practice sessions should cap at 2–3 hours. Beyond that, decision quality degrades sharply ([PokerNews](https://www.pokernews.com/strategy/deliberate-practice-four-steps-to-improve-your-poker-game-20411.htm)). The app's session design should respect this ceiling and recommend short, focused blocks (15–30 minute drills) over marathon sessions.

**Weakness-first, not strength-first.** A common failure mode is studying what you already know because it feels good. Deliberate practice demands allocating 60–70% of study time to demonstrated weaknesses, not comfortable spots ([Casino.org](https://www.casino.org/blog/practice-in-poker/)). The app must surface the player's weakest positions/spot-types prominently, not bury them.

**Self-coaching substitute.** Without a coach to identify weaknesses externally, the app takes on that role. GTO Wizard's leak-fix workflow ([GTO Wizard Blog](https://blog.gtowizard.com/fixing-a-poker-leak-part-1-spotting-and-correcting-errors/)) demonstrates the model: the player's own drill accuracy data replaces coach observation. The app should auto-detect the player's worst-performing spot categories and push them to the top of the study queue.

---

### 2. Spaced Repetition & Retrieval Practice

**The testing effect.** Retrieval practice (forcing recall before review) produces substantially stronger long-term retention than re-study. The act of attempting retrieval — even if the attempt fails — enhances subsequent encoding ([ScienceDirect: Retrieval Practice](https://www.sciencedirect.com/science/article/pii/S0959475225001434); [MIT TLL](https://tll.mit.edu/teaching-resources/how-to-teach/help-students-retain-organize-and-integrate-knowledge/)). For poker, this means the app should make the player commit to an action *before* revealing correct play — never show the answer first.

**Spaced repetition mechanics.** Spaced repetition (SRS) schedules re-exposure to a card/concept just before the learner is likely to forget it, using algorithms like SM-2 (Anki's historical algorithm) or the newer FSRS. Intervals expand with each correct recall: minutes → days → weeks → months. Getting it wrong resets to a shorter interval. Applied to poker:

- A decision spot the player consistently gets right should recur less frequently.
- A spot the player consistently fumbles should recur more aggressively.
- The Chessable MoveTrainer demonstrates the granularity: the learner reads one move's commentary, commits the move, reads more commentary, commits again — tiny loops with immediate validation, then spaced re-exposure ([Chessable](https://www.chessable.com/blog/welcome-series-1-spaced-repetition/)).

**Poker-specific SRS application.** Apply SRS at the level of *situation archetypes*, not individual hands. An archetype is defined by: position + action history + board texture category + stack depth. Example: "EP open, BB defend, dry flop, c-bet decision." The player's success rate on each archetype drives its scheduling. Rare or complex archetypes (UTG vs UTG+1 4-bets) warrant less aggressive resurfacing than high-frequency common spots.

**Key limitation.** SRS works best for discrete, isolable decisions with clear correct answers. Abstract strategic concepts ("how to play a draw-heavy board as the aggressor") resist pure SRS treatment. Reserve SRS for concrete decision points; use longer-form review sessions for conceptual understanding.

---

### 3. Interleaving vs Blocked Practice

**Research verdict.** Interleaved practice — alternating among different spot types within a session — outperforms blocked practice (all similar spots grouped together) for long-term retention and transfer. Studies report learning performance increases of approximately 30% with interleaving. The mechanism is the "contextual interference effect": frequent task-switching requires more effortful processing, which deepens encoding ([MLPP](https://mlpp.pressbooks.pub/mavlearn/chapter/spaced-and-interleaved-practice/); [NCBI PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8589969/)).

**Critical nuance for novices.** Research on low achievers shows that pure interleaving too early poses "undesirable difficulty." For learners who haven't yet developed basic schema for a problem type, blocked practice first builds necessary declarative knowledge. Only then does interleaving produce superior long-term retention ([Wiley/Lang Learning 2025](https://onlinelibrary.wiley.com/doi/10.1111/lang.12659)). The chess training literature (ChessSolve, Lichess documentation) reinforces this: when learning a new tactical theme, doing 30 fork puzzles in a row builds the pattern template before mixing with other themes.

**App design implication.** Implement a two-phase model:
1. **Blocked phase** (new spot type): When introducing a new situation category, deliver 15–20 consecutive repetitions of that type until basic accuracy is established (>65% correct).
2. **Interleaved phase** (maintenance/SRS): Once a category is in the learner's active deck, mix it with other categories in review sessions.

---

### 4. Immediate, Explanatory Feedback

**Explanatory > correct-only.** Research is unambiguous: explanatory feedback (principle-based "why" of the correct answer) produces better transfer of learning than merely knowing whether an answer was right or wrong ([ResearchGate](https://www.researchgate.net/publication/263936578_Explanation_Feedback_Is_Better_Than_Correct_Answer_Feedback_for_Promoting_Transfer_of_Learning)). For poker, "fold is correct" is weak feedback. "Fold is correct because your hand has insufficient equity (28%) versus villain's 3-bet range, and you lack position to bluff profitably" is what drives understanding.

**GTO Wizard's feedback model** ([GTO Wizard Help](https://help.gtowizard.com/how-to-use-the-trainer/)) represents the current best practice in poker training:
- Displays: player's action, GTO-optimal action, EV difference (in bb/100), action frequencies.
- When "learning mode" is on: the info panel auto-opens after any mistake, showing relevant ranges and strategy.
- Pause-after-mistake: interrupts before the next hand, enforcing reflection.
- Scores actions by their GTO frequency (best action = max points; lower-frequency actions scored proportionally).

**Timing.** Feedback should appear *immediately* after the decision, not after the hand resolves. This is critical: if the player makes a preflop mistake and then sees two more streets of cards before seeing feedback, the causal link between decision and consequence blurs. The app should surface feedback at the decision point.

**Levels of feedback depth.** Design feedback in expandable layers to avoid overwhelming:
1. **Quick indicator** (1 second): Color flash — green (best), yellow (OK), orange (inaccurate), red (blunder) + EV delta.
2. **Summary panel** (auto-expand on mistakes): Correct action + EV cost + one-sentence reason.
3. **Deep dive** (user-triggered): Full range display, strategy breakdown, board texture analysis.

---

### 5. Mastery-Based Progression & Scaffolding

**Mastery gating.** Mastery-based learning withholds advancement until genuine competency is demonstrated at the current level — not time-on-task or completion-of-content. Adaptive learning platforms implement this by preventing advancement to a next module until the learner satisfies a mastery threshold ([Ingenuity.ph](https://www.ingenuity.ph/the-future-of-learning-is-built-on-mastery-how-edtech-founders-can-drive-real-learning-outcomes/)). For poker: the player cannot unlock "3-bet pot postflop" drills until they demonstrate >80% accuracy on single-raised-pot flop drills.

**Scaffolding and cognitive load.** Cognitive Load Theory holds that working memory has finite capacity. Instructional design must minimize *extraneous* cognitive load (confusion about the interface, irrelevant information) to free capacity for *germane* load (actually processing the poker decision). Practical implications ([EducationalTechnology.net](https://educationaltechnology.net/cognitive-load-theory-principles-learning-processes-and-implications-for-instructional-design/)):
- Show only the information needed for the current decision (hide irrelevant fields).
- Use progressive disclosure: beginners see simplified action choices (fold/call/bet), advanced players see sizing options.
- GTO Wizard's three difficulty tiers model this well: Simple (action type only) → Grouped (size categories) → Standard (exact sizing).

**Sequence recommendation (cash game focus):**
1. Preflop opens by position (EP → CO → BTN → SB)
2. Preflop vs. 3-bet (facing 3-bet from each position)
3. Single-raised-pot flop play (IP vs OOP)
4. Single-raised-pot turn/river decisions
5. 3-bet pot postflop
6. Squeeze pots and multi-way dynamics

Rationale from practitioner literature: "jumping to turn or river spots before preflop is solid is a common reason players plateau — the postflop solver answers depend on the preflop ranges being correct" ([vip-grinders.com](https://www.vip-grinders.com/poker-tools/gto-wizard-review/)).

---

### 6. Error Review & Leak-Tracking Loops

**Frequency × severity matrix.** GTO Wizard's leak analysis framework ([GTO Wizard Blog](https://blog.gtowizard.com/fixing-a-poker-leak-part-1-spotting-and-correcting-errors/)) provides the best-practice model: prioritize leaks by *frequency multiplied by EV cost*, not by EV cost alone. A small leak in a common spot (BTN vs BB) outweighs a large mistake in a rare spot (UTG vs UTG+1 4-bets). The app should rank the player's leaks by this combined metric and surface the top 3 in the home dashboard.

**Error classification.** Two types of mistakes in GTO terms:
- **Pure mistakes (EV mistakes):** Player chose a zero-frequency action — always wrong in equilibrium. Highest priority to eliminate.
- **Frequency mistakes:** Player took a theoretically valid action but at the wrong frequency (e.g., bluffing 70% when GTO says 40%). Lower priority, more nuanced to fix.

**The review loop architecture.** A well-designed poker improvement cycle includes five stages (synthesized from GTO Wizard workflow + Casino.org deliberate practice framework + Kolb's experiential learning model):

```
IDENTIFY (what leaked) → STUDY (fill knowledge gap) → DRILL (reps on the leak)
→ ANALYZE (review mistakes within drills) → VALIDATE (confirm EV loss reduced)
→ loop back to IDENTIFY
```

**Mistake logging.** After each drill session, the app should auto-log:
- Spots where accuracy < 70%
- EV loss per spot category
- Improvement trend vs. previous sessions on same spot type

This log becomes the input to the next session's drill selection. The player should never have to manually decide "what should I study?" — the system answers that.

**Resurfacing tagged mistakes.** Any spot the player answered incorrectly should enter the SRS queue for re-review. The "pain" of seeing the same spot recur until correct is intentional — it mirrors the deliberate practice principle of targeting weaknesses specifically.

---

### 7. Motivation & Adherence — Gamification

**What the research shows.** A meta-analysis of 41 studies (n=5,071) found gamification produces a significant large effect size (g=0.822) on learning outcomes when implemented well, improving knowledge retention and skill acquisition ([Frontiers in Psychology](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1253549/full)). However, longitudinal studies show intrinsic motivation can *decline* over time with heavy gamification exposure — the novelty effect fades ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10448467/)).

**The overjustification risk.** The overjustification effect (Deci, Lepper): providing expected external incentives for an intrinsically motivating activity can *reduce* intrinsic motivation. Tangible rewards (points, badges) significantly undermine intrinsic motivation; rewards that convey *competence information* (e.g., "you hit 90% accuracy on BTN opens — that's a professional threshold") reduce this harm ([Overjustification Effect - Wikipedia](https://en.wikipedia.org/wiki/Overjustification_effect); [NTNU Research](https://www.ntnu.edu/documents/139799/1279149990/04+Article+Final_camildah_fors%C3%B8k_2017-12-06-13-53-55_TPD4505.Camilla.Dahlstr%C3%B8m.pdf)).

**Duolingo's validated gamification mechanics** ([925Studios](https://www.925studios.co/blog/duolingo-design-breakdown); [Orizon](https://www.orizon.co/blog/duolingos-gamification-secrets)):
- **Streak:** Loss aversion drives consistency. When Duolingo introduced an iOS widget showing the streak, user commitment increased 60%. Users engaging with streak mechanics complete significantly more lessons.
- **XP + Leagues:** Users in leagues complete 40% more lessons/week. Introducing leagues increased lesson completion 25%.
- However, these effects are strongest for *daily engagement* habits, not necessarily *deep skill acquisition*. Streaks make people show up; they don't automatically make practice higher quality.

**Gamification do's for poker training:**
- **Do** use streaks to build daily study habits.
- **Do** reward *measurable skill progress* (accuracy thresholds, EV loss reduction) rather than time-on-task.
- **Do** use mastery badges that unlock access (e.g., "unlock 3-bet pots after hitting 80% on SRP flops").
- **Do** display progress trends (accuracy over time per category) — competence-informing feedback.
- **Do** make error counts visible — the player should feel the weight of mistakes as data, not shame.

**Gamification don'ts for poker training:**
- **Don't** make points/XP the primary feedback mechanism. Points divorced from EV/accuracy are vanity metrics.
- **Don't** let streaks be earnable through low-quality rapid clicking. Tie streak credit to completing a minimum-quality threshold session.
- **Don't** add social leaderboards (this is a solo local app — but the principle applies: competitive external comparison can shift focus from skill improvement to score gaming).
- **Don't** reward completion of content consumption (watching videos, reading) the same as active retrieval practice. Passive consumption is not deliberate practice.

---

### 8. Transfer to the Table

**The representative practice principle.** For skills to transfer from training to real performance, practice conditions must resemble the conditions under which the skill will be used (Thorndike's principle of identical elements; sports science "specificity of training"). In poker, transfer risks:
- Training with unlimited time → no time pressure at the table.
- Training on sanitized "obvious" spots → not building recognition on ambiguous real-table situations.
- Training with full information visible → not building confidence to act with incomplete information.

**How to maximize transfer:**
1. **Time pressure:** GTO Wizard's timebank feature (7/15/25 seconds) models this. The app should offer a time-pressure mode once a spot is in the "mastery maintenance" phase.
2. **Realistic visual representation:** PeakGTO's Chip Mode research ([PokerCoaching](https://pokercoaching.com/blog/realistic-poker-training-how-peakgtos-new-chip-mode-changes-the-way-you-practice/)) found that seeing chips move across a table — rather than abstract bb numbers — creates habits that carry to live play. The app should use chip/dollar denomination display matching the player's actual stakes ($1/$2, $2/$3).
3. **Multi-table drilling:** GTO Wizard supports up to 4 simultaneous tables. For a player accustomed to one table, single-table drilling is appropriate; this is not a primary concern.
4. **Scenario authenticity:** Use realistic stack depths (100bb), realistic player counts (6-max or 9-handed for live), and realistic bet-size options that match what the player will actually encounter at $2/$3 (i.e., not highly theoretical solver bet-trees).
5. **Recognition training:** Chess puzzle research (ChessSolve) shows pattern-recognition builds when drills are sequenced to develop *templates* — the player should be able to identify "this is a draw-heavy board structure" before processing the specific decision. Taxonomy labeling of drill scenarios (by board texture, position, action history) builds this vocabulary.

---

## Part B — Concrete UX/UI Patterns for Poker Training

### 1. Hand Display

**Standard display elements (required on every drill card):**
- **Hole cards:** Large, centered, high-contrast card faces. Suit colors: standard (red/black) with colorblind option (4-color deck).
- **Community cards:** Street-separated (flop as group, turn, river). Current street being decided should be visually distinguished.
- **Positions:** Labeled around a table graphic or as a positional strip. At minimum: Hero position + Villain position. Full table positions (UTG/MP/CO/BTN/SB/BB) as labels.
- **Stack sizes:** Displayed in both bb and dollar amount (at player's stakes). Both matter: bb for studying strategy, dollars for transfer to real play.
- **Pot size:** Current pot prominently labeled. Calculated pot-odds displayed automatically when facing a bet.
- **Action history:** All previous actions visible (e.g., "BTN raised 3bb, SB folded, BB called") — this contextualizes the current decision.
- **Effective stack depth:** The smaller of the two relevant stacks. Critical for GTO vs exploitative adjustments.

**What NOT to show on the drill card (cognitive load reduction):**
- Irrelevant players' cards.
- Complex range percentages during decision phase — save for feedback panel.
- Historical session statistics during active drilling.

**Table layout philosophy:** Semi-realistic (oval table, positional labels, chip stacks as visual element) rather than purely abstract. PeakGTO's Chip Mode research supports realism for transfer. However, for a web app, avoid heavy 3D graphics that slow render performance on drill transitions.

---

### 2. Range Visualization

**The 13×13 grid is the standard.** All positions in a 13×13 matrix: rows = first card rank (A to 2, top to bottom), columns = second card rank (A to 2, left to right). Pocket pairs on the diagonal. Suited combos above diagonal, offsuit below. This convention is universal in poker software and users should not be taught a different format.

**Color encoding system:**
- **Heatmap for frequency:** Each cell color-coded by action frequency (e.g., green = raise 100%, yellow = raise 60%/call 40%, red = fold 100%). Use a continuous color gradient.
- **Multi-action split:** Single cells divided into color bars when the GTO solution is a mixed strategy. Common in practice — most cells have multiple actions at varying frequencies.
- **Equity heatmap (secondary):** Alternative view showing each combo's equity vs. villain's range. Toggle between frequency view and equity view.
- **Player's range vs. GTO range:** Side-by-side comparison view. Left grid = what player did (derived from drill history), right grid = GTO. Divergence highlights = where the leak lives.

**Interaction:**
- Hover/click a cell for exact frequencies and EV.
- Filter by hand class (premium hands, middle pairs, draws, bluff candidates).
- Range notation input for manual range construction (e.g., "AK, QQ+, AJs+").

---

### 3. Feedback Panels

**Three-tier feedback architecture (described in Part A):**

**Tier 1 — Instant visual indicator (always shown):**
- Color flash on action button: green / yellow / orange / red.
- EV delta badge: e.g., "-0.4 bb" in red. This tells the player the cost of their mistake in the universal poker currency.
- Best action label: "GTO: Raise 2.5bb (100%)"

**Tier 2 — Summary panel (auto-expands on mistake, collapsible on correct action):**
```
[Action taken: Call]          [GTO action: Fold]
EV of Call:  -0.23 bb
EV of Fold:   0.00 bb
EV loss:      0.23 bb

Why: You have insufficient equity (31%) vs villain's 3-bet range
     from this position. You lack the range advantage to profitably 
     continue out of position.
```
The *why* in plain language is non-negotiable. Numbers alone do not build understanding.

**Tier 3 — Deep dive panel (user-triggered, modal or right-side panel):**
- Full 13×13 range grid for both players at this decision point.
- Villain's 3-bet range displayed, filtered to combos still in play on this board.
- EV tree: hover any action to see downstream EV propagation.
- Board texture label: "Dry board, low card, villain range advantage."
- Link to relevant knowledge article (if content library exists).

**Feedback timing rules:**
- Show Tier 1 immediately upon action — no delay.
- Show Tier 2 automatically if action was incorrect (orange or red).
- Never auto-advance to next hand during Tier 2 — player must explicitly dismiss.
- Provide a "Replay" button to try the spot again from the decision point with the same scenario.

---

### 4. Session & Drill Structure

**Drill modes (mirroring GTO Wizard's model, adapted for this app):**

| Mode | Description | Use case |
|---|---|---|
| **Spot drill** | Single decision point, rapid reps | SRS queue, high-frequency spot training |
| **Street drill** | All decisions on one street (e.g., flop only) | Focused postflop work |
| **Full hand** | Preflop → River with all decision points | Holistic play, simulation of real sessions |
| **Leak focus** | Auto-selected spots from the player's worst categories | Primary daily training mode |
| **Free explore** | Player manually selects scenario parameters | Self-directed deep dives |

**Daily session shape:**
- **Recommended session length:** 20–30 minutes of focused drilling per day. This aligns with deliberate practice research (quality over quantity) and practitioner consensus (15–20 minute blocks before fatigue impacts decision quality).
- **Session open:** Dashboard shows "today's priority leaks" and recommended drill mode. One click to start.
- **Core block:** 20–40 hands in the selected drill mode.
- **Session close:** 2-minute review — accuracy rate for session, EV loss per category, biggest single mistake, and one question prompting reflection ("What pattern do you notice in your fold-to-3bet decisions from EP?").

**Quiz flow principles:**
- One decision at a time. No multi-step forms.
- Action buttons: Fold / Call / Raise (+ sizing input when relevant). Large tap targets.
- After decision: instant Tier 1 feedback → option to expand Tier 2/3 → button to continue.
- "I want to think about this" button: flags the spot for additional deep-dive review later, without holding up the drill queue.

**Session cadence recommendation:**
- Monday–Friday: 20–30 min drill sessions (Spot/Leak-focus mode)
- Weekend: one longer 45–60 min session combining Full Hand mode with deep-dive review of the week's flagged spots.

---

### 5. Progress Tracking & Analytics

**The rule: track metrics that drive behavior change, not vanity metrics.**

**Actionable metrics to display (dashboard):**
- **Accuracy by spot category:** Bar chart. Top 5 worst categories highlighted in red. This is the primary driver of drill selection.
- **EV loss per category over time:** Line chart per category. Shows whether drilling is actually reducing the leak.
- **Session streak:** Number of consecutive days with ≥1 qualifying session.
- **Mastery progress per module:** Progress bar per topic (preflop EP, preflop BTN, SRP flop IP, etc.) with accuracy threshold gates (e.g., "78% — need 80% to unlock next").
- **Top 3 leaks this week:** Ranked by frequency × EV loss. Auto-updated.
- **Most improved this week:** One category showing biggest accuracy gain. Positive reinforcement tied to actual performance.

**Metrics to avoid (or de-emphasize):**
- Total hands played (rewards grinding, not quality practice).
- Time spent in app (same problem).
- Hands "completed" vs. total score (gameable via low-effort rapid clicking).

**Visualization principles:**
- Accuracy trends need at least 50 reps per category to be statistically meaningful. Display confidence intervals or minimum-rep warnings.
- Separate "drill accuracy" from actual win rate at the table — the app cannot measure the latter, and conflating them causes confusion.
- Show per-position matrices: a grid of positions (UTG/MP/CO/BTN/SB/BB) × decision types (open, 3bet, call 3bet, c-bet, etc.) colored by accuracy. Instantly identifies spatial leak patterns.

---

### 6. Input Speed & Keyboard Shortcuts

**Why speed matters for deliberate practice.** Slow input breaks cognitive flow during drilling and reduces rep density per session. High-quality chess puzzle training on Lichess/Chess.com relies on fast input (clicking a square) that feels immediate. Slow UX is a friction cost on every rep.

**Recommended keyboard mapping:**
- `F` — Fold
- `C` — Call / Check
- `R` — Raise / Bet
- `Space` — Continue / next hand (after feedback dismissal)
- `D` — Deep dive (expand Tier 3 feedback)
- `T` — Tag for review / I want to think about this
- Number keys `1–5` — Raise sizing presets (e.g., 1=25%, 2=33%, 3=50%, 4=75%, 5=pot)

**ShortcutFoo/KeyCombiner research** ([ShortcutFoo](https://www.shortcutfoo.com/)) confirms that drilling keyboard shortcuts with immediate feedback (muscle memory formation) requires the same spaced repetition principles as content learning. Display available shortcuts in a persistent HUD overlay, toggleable by the player.

**Mobile consideration.** For a local desktop web app, desktop-first is appropriate. However, the player may want to review analytics or the drill queue from a mobile device. Dashboard and analytics should be mobile-responsive; drill interface can be desktop-only (input precision and screen space are critical for drilling).

**Speed modes:**
- **Normal:** 7-second timebank per decision (comfortable).
- **Fast:** 3-second timebank (pressure mode for maintenance/SRS phase).
- **Turbo:** No timebank — immediate click required. Used only in highest-mastery maintenance phase.

---

### 7. Lessons from Adjacent Apps

**Chessable MoveTrainer ([Chessable](https://www.chessable.com/blog/welcome-series-1-spaced-repetition/); [Andy Matuschak Notes](https://notes.andymatuschak.org/zDr94hP6bG3jJYrdYy8B5hx)):**
- Granular SRS at the individual-move level with prose commentary interleaved between moves.
- Transfer to poker: Interleave brief strategy notes with decision drills. After answering, show one-sentence principle ("On ace-high dry boards, IP prefers small c-bet with polarized range") before dismissal.
- Key pattern: *read one concept → immediately apply it → spaced review of both*.

**Lichess/Chess.com Puzzles ([Lichess](https://lichess.org/@/CheckRaiseMate/blog/spaced-repetition/eteyH8MT); [ChessSolve](https://chesssolve.com/blog/chess-puzzle-training-guide)):**
- Single-decision puzzles, rated by difficulty, with a rating system that matches puzzle difficulty to player skill.
- Failed puzzles resurface at 1-day, 3-day, and 7-day intervals.
- Key pattern for poker: the puzzle *rating* (difficulty) drives adaptive matching — the app should have a difficulty estimate per spot type, and serve spots at or slightly above the player's current skill ceiling.

**Duolingo ([925Studios](https://www.925studios.co/blog/duolingo-design-breakdown); [Scrimmage](https://scrimmage.co/the-psychology-behind-duolingos-success/)):**
- 5 key principles: active learning, spaced practice, personalized learning, short lesson design, and immediate feedback.
- Key pattern: Lesson completion is framed as a daily habit, not a marathon. The streak is the primary habit-formation mechanism.
- Caution for poker training: Duolingo's hearts (error limit per session) could be adapted — but in poker training, it's more useful to push through errors and see explanations than to penalize and stop.

**What transfers to poker training:**
| Pattern | Source | Poker Training Adaptation |
|---|---|---|
| Spaced resurfacing of failed items | Chessable, Lichess | Failed spots enter SRS queue; resurface on schedule |
| Difficulty rating per item | Chess.com Puzzles | Each spot type gets a difficulty score; serve at +1 above current accuracy |
| Commentary + immediate application loop | Chessable | One-sentence principle shown after every feedback dismissal |
| Streak for daily habit | Duolingo | Daily session streak; streak breaks at <1 qualifying session per day |
| Progress visualization | All three | Accuracy heat map by category; mastery bars |
| Short lesson design (5–10 min units) | Duolingo | 10–15 hand mini-sessions with a clear goal |

**What does NOT transfer:**
- Duolingo's lives/hearts (disrupts high-rep drilling flow).
- Chess.com's ELO rating system for players (not relevant to solo training — accuracy % is a better metric).
- Social leaderboards (solo app, irrelevant).

---

## Part C — Novice-Specific Differences

### Who is this player?

This player is a **competent novice** — winning at $1/$2, possessing a functional TAG (tight-aggressive) preflop strategy, basic positional awareness, and reliable value-betting fundamentals. They are NOT a total beginner. They already have a working mental model of poker. The training goal is **calibration and range-based elevation**, not foundational construction.

### What is DIFFERENT vs. designing for a total beginner

**1. Skip hand rankings, pot odds basics, position vocabulary.**
A total beginner needs these. This player does not. Starting the app with "Poker Basics" modules would be condescending and a waste of study time. Begin with preflop range construction, not "which hand beats which."

**2. Do NOT overwrite existing winning intuitions — build on them.**
This player has working intuitions developed from real winning sessions. Many training programs make the mistake of replacing intuition with pure GTO mechanically, causing a transitional performance dip and psychological disorientation. The app should frame GTO training as *refining* existing decisions, not discarding them. Example: "Your fold-to-3bet from EP is already directionally correct (you're tight). We're going to calibrate the threshold." This preserves confidence while tightening precision.

**3. Range-based thinking is the primary new paradigm.**
The key cognitive upgrade from novice to competent intermediate is the shift from "what do I have?" to "what hands am I representing / what hands am I facing?" The app's drills should make this explicit at every opportunity. Show the player their implied range on every decision, not just their hole cards. The 13×13 grid should be a constant companion, not an optional tool.

**4. Frequency-based thinking over binary correctness.**
Beginners need binary rules: "always fold 72o UTG." Intermediates need frequency reasoning: "3-bet bluff AXs from CO at 30% frequency vs. this villain's opening range." The app's feedback panels should speak in frequencies, not absolutes. Display "GTO: raise 65%, call 35%" not just "GTO: raise."

**5. Calibrating confidence, not just building it.**
The player moving from $1/$2 to $2/$3 will face more aggressive player pools and more 3-bet pressure. Overconfidence is a real failure mode: the player's strategies that crushed $1/$2 may be suboptimal at $2/$3. The app should use accuracy data to give the player calibrated confidence signals: "Your BTN open vs BB plays at 84% accuracy — this is a strength. Your response to BB check-raise on turns is at 51% — don't trust your instincts here yet." This is more useful than generic encouragement.

**6. Leak-plugging > new concept introduction.**
A beginner needs to learn everything. This player already knows a lot. The highest-value training is identifying the *specific* leaks that cost money and drilling those relentlessly. A training system that asks "what would you like to learn today?" is less effective than one that says "your biggest leak this week is calling 3-bets too wide from EP — let's drill that for 20 minutes." The system should pull the player toward identified weaknesses, not let them drift to comfortable topics.

**7. Mental game and variance awareness.**
Moving up in stakes increases variance and exposes the player to better opponents who will apply more pressure. The mental game (tilt management, confidence calibration, bankroll discipline) becomes more important, not less. The app cannot address the mental game through drills alone, but should:
- Display variance context ("Your 3-session downswing is within normal statistical range for a 5bb/100 winner") to prevent tilt-driven decisions.
- Frame accuracy metrics in terms of long-run EV rather than session results.
- Include a pre-session ritual: a brief mental readiness prompt ("Set your focus for today's session. What's the one leak you're targeting?").

**8. Bankroll and move-up readiness signals.**
$1/$2 to $2/$3 is not a 3x increase in difficulty, but it is meaningfully different: more aggressive regulars, less open-limping, more 3-bet pressure. The app should include a "move-up readiness" checklist (not a drill module — a diagnostic) covering:
- Bankroll criteria (20–30 buy-ins recommended minimum for a shot).
- Accuracy thresholds on key $2/$3-relevant spot categories.
- Mental game readiness self-assessment.

This avoids the common mistake of moving up prematurely because win rate at current stakes "feels" good.

**9. Avoiding info overload.**
The intermediate player is likely consuming coaching content, solver outputs, forum discussions, and training videos simultaneously. The risk is *too much* context from too many conflicting sources, creating analysis paralysis at the table. The app's role should be focused execution training, not yet another strategy channel. Design should emphasize narrow, deep drilling over broad curriculum coverage.

**10. Exploitative overlays on GTO foundations.**
Beginners learn GTO as the only framework. Intermediates are ready to layer exploitative adjustments: "your opponent open-limps 40% from UTG at $1/$2 — here's how to isolate." At $2/$3, pure GTO is a stronger baseline but exploitative reads still matter. The app should flag when a spot's solver-optimal play diverges significantly from what a $2/$3 live pool will require, and note the exploit. However, the primary training foundation remains GTO.

---

## Recommended Learning-Loop Blueprint

The core daily loop for this app should implement a **4-phase iterative cycle** grounded in both Kolb's experiential learning model and GTO Wizard's proven study workflow:

```
┌─────────────────────────────────────────────────────────────┐
│                  DAILY TRAINING LOOP                        │
│                                                             │
│  1. IDENTIFY (System)                                       │
│     App surfaces top 3 leaks ranked by freq × EV cost.     │
│     Player selects focus area (or accepts recommendation).  │
│                          ↓                                  │
│  2. DRILL (Player)                                          │
│     20–30 hands in Spot/Leak-focus mode.                   │
│     SRS queue mixed with new spot introductions.            │
│     Immediate 3-tier feedback on every decision.            │
│     Time pressure optional (Normal / Fast / Turbo).        │
│                          ↓                                  │
│  3. REVIEW (Player + System)                                │
│     Session summary: accuracy by category, EV loss delta,   │
│     biggest mistake of session, improvement vs. last week.  │
│     Deep-dive on flagged spots (Tier 3 feedback panels).    │
│                          ↓                                  │
│  4. SCHEDULE (System)                                       │
│     SRS algorithm updates intervals for all practiced       │
│     spots. Failed spots scheduled for 1/3/7 day return.    │
│     Mastery gates check if new modules should unlock.       │
│     Next session's priority queue generated.                │
└─────────────────────────────────────────────────────────────┘
                          ↓ (repeat daily)
                    WEEKLY REVIEW SESSION
         (45–60 min, Full Hand mode + flagged spot deep dives,
          weekly leak trend report, mastery progress update)
```

**Module progression ladder (mastery-gated):**

```
Level 1: Preflop opens by position (EP → BTN → Blinds)
  ↓ [gate: 80% accuracy across all positions]
Level 2: Preflop vs. 3-bet (calling / 4-betting ranges)
  ↓ [gate: 80% accuracy]
Level 3: Single-raised-pot flop decisions (c-bet, check-raise, float)
  ↓ [gate: 80% accuracy]
Level 4: SRP turn/river decisions
  ↓ [gate: 80% accuracy]
Level 5: 3-bet pot postflop
  ↓ [gate: 80% accuracy]
Level 6: Squeeze pots, multi-way, special scenarios
```

**SRS integration:**
- New spots: blocked phase first (15–20 reps) → enters SRS deck.
- SRS deck reviewed in every session's opening 5–10 hands.
- Failed spot (< correct): resurfaces in 1 day.
- Correct once: resurfaces in 3 days.
- Correct twice: resurfaces in 7 days.
- Correct three times: resurfaces in 21 days (maintenance mode).

**Feedback protocol:**
- Every decision: Tier 1 (instant color + EV delta).
- Every mistake: Tier 2 auto-expand (correct action + why in plain language).
- Every session: Deep-dive option on worst mistake.
- Weekly: EV loss trend chart per category (shows if drilling is working).

**Gamification guardrails:**
- Streak: earnable only by completing a session with ≥20 decisions and average decision quality above "poor" (i.e., not just clicking randomly).
- Mastery badges: unlock next module, visually prominent but tied to real accuracy thresholds.
- No points/XP divorced from accuracy.
- No time-on-app rewards.

**Transfer mechanisms:**
- Dollar denomination display matching player's stakes.
- Time pressure mode (activate after a spot hits 80% accuracy in normal mode).
- Realistic stack depths, position labels matching live game.
- Pre-session focus ritual (1 question: "what are you targeting today?").
- Post-session reflection prompt (1 question: "what pattern did you notice?").

---

## Sources

- Ericsson, K.A. — Deliberate Practice: [PokerNews](https://www.pokernews.com/strategy/deliberate-practice-four-steps-to-improve-your-poker-game-20411.htm) | [Casino.org](https://www.casino.org/blog/practice-in-poker/) | [PokerListings](https://pokerlistings.com/pick-a-game-and-master-it-how-deliberate-practice-works-in-poker/)
- Spaced Repetition & Retrieval Practice: [MIT TLL](https://tll.mit.edu/teaching-resources/how-to-teach/help-students-retain-organize-and-integrate-knowledge/) | [ScienceDirect](https://www.sciencedirect.com/article/pii/S0959475225001434) | [CIRL Eton](https://cirl.etoncollege.com/strategies-for-making-learning-last-retrieval-practice-spaced-practice-and-interleaving/) | [PMC Spaced Practice](https://pmc.ncbi.nlm.nih.gov/articles/PMC6410796/)
- Interleaving vs Blocked Practice: [MLPP Pressbooks](https://mlpp.pressbooks.pub/mavlearn/chapter/spaced-and-interleaved-practice/) | [NCBI PMC Physics](https://pmc.ncbi.nlm.nih.gov/articles/PMC8589969/) | [Wiley Language Learning 2025](https://onlinelibrary.wiley.com/doi/10.1111/lang.12659) | [PMC Music Learning](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4989027/)
- Explanatory Feedback: [ResearchGate](https://www.researchgate.net/publication/263936578_Explanation_Feedback_Is_Better_Than_Correct_Answer_Feedback_for_Promoting_Transfer_of_Learning) | [RetrievalPractice.org](https://www.retrievalpractice.org/strategies/2018/5/25/feedback)
- Mastery & Cognitive Load: [EducationalTechnology.net](https://educationaltechnology.net/cognitive-load-theory-principles-learning-processes-and-implications-for-instructional-design/) | [Ingenuity.ph](https://www.ingenuity.ph/the-future-of-learning-is-built-on-mastery-how-edtech-founders-can-drive-real-learning-outcomes/)
- Gamification Research: [Frontiers in Psychology Meta-Analysis](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2023.1253549/full) | [PMC Gamification Motivation](https://pmc.ncbi.nlm.nih.gov/articles/PMC10448467/) | [Springer Intrinsic Motivation](https://link.springer.com/article/10.1007/s11423-023-10337-7) | [Overjustification Effect - Wikipedia](https://en.wikipedia.org/wiki/Overjustification_effect)
- Duolingo Design: [925Studios](https://www.925studios.co/blog/duolingo-design-breakdown) | [Scrimmage](https://scrimmage.co/the-psychology-behind-duolingos-success/) | [Orizon](https://www.orizon.co/blog/duolingos-gamification-secrets)
- GTO Wizard: [Help — Trainer](https://help.gtowizard.com/how-to-use-the-trainer/) | [Leak Fix Blog](https://blog.gtowizard.com/fixing-a-poker-leak-part-1-spotting-and-correcting-errors/) | [VIP Grinders Review](https://www.vip-grinders.com/poker-tools/gto-wizard-review/)
- Chessable & SRS: [Chessable Blog](https://www.chessable.com/blog/welcome-series-1-spaced-repetition/) | [Andy Matuschak Notes](https://notes.andymatuschak.org/zDr94hP6bG3jJYrdYy8B5hx) | [Zwischenzug SRS](https://www.zwischenzug.gg/p/spaced-repetition)
- Chess Puzzles & Training: [ChessSolve](https://chesssolve.com/blog/chess-puzzle-training-guide) | [Lichess SRS Discussion](https://lichess.org/@/CheckRaiseMate/blog/spaced-repetition/eteyH8MT)
- Poker Leak Detection: [GTO Wizard Leak Fix](https://blog.gtowizard.com/fixing-a-poker-leak-part-1-spotting-and-correcting-errors/) | [BlackRain79](https://www.blackrain79.com/2017/11/study-your-poker-hands-find-leaks.html) | [SplitSuit LeakFinder](https://www.splitsuit.com/leakfinder)
- Realistic Training & Transfer: [PeakGTO Chip Mode](https://pokercoaching.com/blog/realistic-poker-training-how-peakgtos-new-chip-mode-changes-the-way-you-practice/)
- Mental Game: [Amazon — Mental Game of Poker (Tendler)](https://www.amazon.com/Mental-Game-Poker-Strategies-Confidence/dp/0615436137) | [PMC Cognitive/Emotional Regulation in Poker](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12420057/) | [Poker.org Confidence Calibration](https://www.poker.org/poker-strategy/beyond-confidence-the-mental-game-concept-every-poker-player-should-master-au3bf4A5JrFY/)
- Range Visualization UX: [Poker Copilot 13x13 Guide](https://pokercopilot.com/userguide/7/en/topic/13x13-formatted-matrix-heat-map) | [ApexTell](https://www.apextell.net/) | [OpenPokerTools](https://openpokertools.com/)
- Input Speed: [ShortcutFoo](https://www.shortcutfoo.com/) | [KeyCombiner](https://keycombiner.com/)
- Moving Up Stakes: [LeakSeek](https://www.leakseek.poker/) | [SmartPokerStudy Micro Stakes Guide](https://smartpokerstudy.com/micro-stakes-cash-game-online-poker-training-ultimate-guide/)
- Learning Loop Theory: [HubKen Learning Loop](https://www.hubkengroup.com/resources/what-is-a-learning-loop)
