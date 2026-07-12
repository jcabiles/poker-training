import type { CSSProperties } from "react";

import type { GradeView, SeatView, ShowdownSeatView, SimulateHandView } from "../../api/types";
import Card from "../Card";
import { tierOf } from "./simGrade";

// Simulate S9 table. A purpose-built felt for the persistent session: it reuses
// PokerTable's felt/ring/rail CSS classes and elliptical geometry verbatim (so
// it reads as the same room), but renders the richer per-seat data S9 owns and
// PokerTable does not carry — persona badge, chips-in-front, live status, and
// showdown reveals. PokerTable.tsx itself stays untouched (Practice/Quiz still
// use it). Privacy: a non-hero seat's hole cards are rendered ONLY when that
// seat is in `showdown` — folded/live villains stay face-down.

// Canonical 9-max seating order (clockwise) — same ring PokerTable uses.
const RING = ["UTG", "UTG1", "UTG2", "LJ", "HJ", "CO", "BTN", "SB", "BB"];

// Seat-pod coordinates on the elliptical rail (same math as PokerTable's
// slotStyle — geometry DATA, not styling). Slot 0 (hero) sits bottom-center.
// Sim-owned copy: the vertical radius is asymmetric (PokerTable keeps 38 all
// around) — the TOP half of the ellipse spreads to 41 so the HJ/CO pods clear
// the five-card board on the wave-4.5 taller sim ring, while the bottom half
// keeps 38 (the hero pod hangs below the rail by design; 41 pushed it past
// .stage's overflow:hidden). Verified by bounding-box sweep at 1440/1280/1024.
function slotStyle(i: number, n: number): CSSProperties {
  const theta = Math.PI / 2 + (i * 2 * Math.PI) / n;
  const sin = Math.sin(theta);
  const x = 50 + 43 * Math.cos(theta);
  const y = 50 + (sin < 0 ? 41 : 38) * sin;
  return { left: `${x}%`, top: `${y}%` };
}

// Persona archetypes arrive as SCREAMING_SNAKE VillainType values; render them
// as short Title Case labels for the seat badge.
function personaLabel(persona: string): string {
  return persona
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function SimTable({
  hand,
  stagedIndex,
  revealAt,
  lastGrade,
}: {
  hand: SimulateHandView;
  // How many of the current events batch have been narrated (shared with the
  // event log — SimulateView owns it). Drives the LOCKSTEP reveal below.
  stagedIndex: number;
  // position → 1-based staged-index threshold at which that seat's LAST action
  // in this batch is narrated. A seat's resolved fold/all-in/chips state is
  // held back until stagedIndex reaches this threshold, so the felt never runs
  // ahead of the log. Positions absent from the map settled before this batch
  // (hero, seats already folded) → revealed from the start.
  revealAt: Map<string, number>;
  // S10 verdict for the hero's just-taken action, or null. SimulateView owns
  // the gating: it passes the grade only once it's safe to show (the hero's own
  // decision isn't part of the bot playback, so this can appear immediately —
  // but SimulateView still withholds it once the NEXT view lands / on a deal).
  lastGrade: GradeView | null;
}) {
  const { seats, board, pot_bb, hero, to_act_seat, button_seat } = hand;
  const showdownBySeat = new Map<number, ShowdownSeatView>(
    hand.showdown.map((s) => [s.seat_index, s]),
  );

  // Has this seat's action in the current batch been narrated yet? Seats with no
  // entry acted before this batch (or never) and are always considered revealed.
  const isRevealed = (position: string): boolean => {
    const threshold = revealAt.get(position);
    return threshold == null || stagedIndex >= threshold;
  };

  // Rotate the ring so the hero pod is always bottom-center, exactly like
  // PokerTable. Seats arrive indexed 0..8; position tells us where each sits on
  // the felt. Order the felt slots by the RING, anchored on the hero.
  const byPos = new Map<string, SeatView>(seats.map((s) => [s.position, s]));
  const ring = RING.filter((pos) => byPos.has(pos));
  const heroIdx = Math.max(ring.indexOf(hero.position), 0);
  const ordered = ring.map((_, i) => byPos.get(ring[(heroIdx + i) % ring.length])!);

  return (
    <div className="stage">
      <div className="felt felt-staged">
        <div className="ctx">
          Simulate · 0.5/1 · 9-max · hand{" "}
          <span className="sim-ctx-no">{hand.hand_no}</span> · {hand.street}
        </div>
        <div
          className={"tablering" + (hand.hand_over ? " sim-ring-over" : "")}
          role="group"
          aria-label="table seats"
        >
          <div className="rail" aria-hidden="true" />
          <div className="table-center">
            {board.length > 0 && (
              <div className="board" aria-label="community cards">
                {board.map((c, i) => (
                  <Card key={i} card={c} />
                ))}
              </div>
            )}
            <div className="pot">Pot {pot_bb}bb</div>
          </div>

          {ordered.map((seat, i) => {
            const isButton = seat.seat_index === button_seat;
            // Lockstep gate: a bot seat's resolved status (fold-dim / all-in)
            // and its this-street chips are held back until the log has narrated
            // that seat's action. Pre-reveal the seat reads as still live — no
            // premature felt state ahead of the call sheet. The hero pod is
            // never gated (it acts by the player's own click, not the batch).
            const revealed = seat.is_hero || isRevealed(seat.position);
            const folded = revealed && seat.status === "folded";
            const allin = revealed && seat.status === "allin";
            const isToAct = to_act_seat != null && seat.seat_index === to_act_seat;
            const reveal = showdownBySeat.get(seat.seat_index);
            const style = slotStyle(i, ordered.length);

            // Chips-in-front: this street's commitment, shown as a small puck in
            // front of the seat. Suppressed for folded seats (nothing to show)
            // and until this seat's action is narrated (lockstep).
            const chips =
              revealed && seat.invested_street_bb > 0 && !folded ? (
                <span className="sim-chips" title="chips in front">
                  {seat.invested_street_bb}bb
                </span>
              ) : null;

            if (seat.is_hero) {
              return (
                <div
                  className={
                    "tseat heroseat sim-seat" + (isToAct ? " sim-seat-act" : "")
                  }
                  key={seat.seat_index}
                  style={style}
                >
                  {chips}
                  <div className={"hero-ring" + (isToAct ? " sim-ring-live" : "")}>
                    <div className="cards">
                      {hero.hole_cards.map((c, j) => (
                        <Card key={j} card={c} />
                      ))}
                    </div>
                  </div>
                  <div className="herometa">
                    {hero.position}
                    {isButton && (
                      <span className="dealer" aria-label="dealer button">
                        D
                      </span>
                    )}{" "}
                    · <span className="sim-stack num">{hero.stack_bb}bb</span>
                    {isToAct && (
                      <>
                        {" "}
                        · <span className="toact">your turn</span>
                      </>
                    )}
                  </div>
                  {lastGrade && <SimVerdictBadge grade={lastGrade} />}
                </div>
              );
            }

            return (
              <div
                className={
                  "tseat sim-seat" +
                  (folded ? " tseat-folded" : "") +
                  (isToAct ? " sim-seat-act" : "")
                }
                key={seat.seat_index}
                style={style}
              >
                {chips}
                {reveal ? (
                  <span className="cards sim-reveal" aria-label={`${seat.position} shows`}>
                    {reveal.hole_cards.map((c, j) => (
                      <Card key={j} card={c} />
                    ))}
                  </span>
                ) : (
                  !folded && (
                    <span className="tseat-cards">
                      <Card faceDown />
                      <Card faceDown />
                    </span>
                  )
                )}
                <span className="pos">
                  {seat.position}
                  {isButton && (
                    <span className="dealer" aria-label="dealer button">
                      D
                    </span>
                  )}
                </span>
                {seat.persona_type && (
                  <span className="sim-persona" title={personaLabel(seat.persona_type)}>
                    {personaLabel(seat.persona_type)}
                  </span>
                )}
                <span className="stack num">
                  {seat.stack_bb}bb
                  {allin && <span className="sim-allin"> all-in</span>}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// S10 verdict seal on the hero pod — the struck ruling for the action the hero
// just took. The tier WORD always carries the meaning; the tone tint is
// redundant (color is never the only cue). A "no baseline yet" grade (multiway
// / off-pack / unmappable spot) renders as its own muted state, never faked
// into a tier. Non-fold graded rows carry the ≈EV-loss so the cost is legible
// at the table; the recap is where the full "why" lives.
function SimVerdictBadge({ grade }: { grade: GradeView }) {
  const meta = tierOf(grade.correctness);
  const graded = grade.correctness != null;
  const showLoss = graded && grade.ev_loss_bb > 0;
  return (
    <div
      className={"sim-badge sim-tier-" + meta.tone}
      role="status"
      aria-label={
        graded
          ? `Verdict: ${meta.label}${showLoss ? `, gave up about ${grade.ev_loss_bb.toFixed(1)} big blinds` : ""}`
          : "No baseline for this spot yet"
      }
    >
      <span className="sim-badge-word">{meta.label}</span>
      {showLoss && (
        <span className="sim-badge-ev num">≈{grade.ev_loss_bb.toFixed(1)}bb</span>
      )}
    </div>
  );
}
