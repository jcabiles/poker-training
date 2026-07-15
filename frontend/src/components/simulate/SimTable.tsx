import type { CSSProperties } from "react";

import type { GradeView, SeatView, ShowdownSeatView, SimulateHandView } from "../../api/types";
import Card from "../Card";
import { fmtBb, fmtEvLoss, tierOf } from "./simGrade";

// Simulate S9 table. A purpose-built felt for the persistent session: it reuses
// PokerTable's felt/ring/rail CSS classes and elliptical geometry verbatim (so
// it reads as the same room), but renders the richer per-seat data S9 owns and
// PokerTable does not carry — persona badge, chips-in-front, live status, and
// showdown reveals. PokerTable.tsx itself stays untouched (Practice/Quiz still
// use it). Privacy: a non-hero seat's hole cards are rendered ONLY when that
// seat is in `showdown` or the hero explicitly revealed it after folding (R1,
// `revealedBySeat`) — otherwise folded/live villains stay face-down.

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

// Last action verbs arrive lowercase on the wire (fold/check/call/bet/raise);
// Title-case the single word for the felt label above each seat's cards.
function actionLabel(action: string): string {
  return action.charAt(0).toUpperCase() + action.slice(1);
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
  openRangeSeat,
  onToggleRange,
  revealedBySeat,
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
  // Villain-range reveal (V2): the seat_index whose estimated-range panel is
  // currently open (one at a time), or null. SimTable renders a small "range"
  // affordance on live (non-hero, non-STAGED-folded) villain pods; clicking
  // toggles that seat via onToggleRange. The button uses the SAME staged fold
  // computation the pod display uses — never raw seat.status — so it must not
  // vanish before the fold is narrated (spec low-2).
  openRangeSeat: number | null;
  onToggleRange: (seatIndex: number) => void;
  // R1: seat_index → hole cards the hero chose to reveal after folding (via the
  // reveal buttons). Empty until a reveal is requested. These flip the felt
  // face-up exactly like a genuine showdown, but sourced on-demand — the client
  // holds no villain cards until the reveal endpoint returns them.
  revealedBySeat: Map<number, readonly [string, string]>;
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
            <div className="pot">Pot {fmtBb(pot_bb)}bb</div>
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
            // Cards to show face-up: a genuine showdown (settlement) OR an
            // on-demand R1 reveal after a hero fold. R1 reveals can include
            // FOLDED seats ("Reveal All"), so a revealed card overrides the
            // face-down/hidden default even when the seat folded.
            const revealedCards: readonly [string, string] | undefined = reveal
              ? reveal.hole_cards
              : revealedBySeat.get(seat.seat_index);
            const style = slotStyle(i, ordered.length);

            // Chips-in-front: this street's commitment, shown as a small puck in
            // front of the seat. Suppressed for folded seats (nothing to show)
            // and until this seat's action is narrated (lockstep).
            const chips =
              revealed && seat.invested_street_bb > 0 && !folded ? (
                <span className="sim-chips" title="chips in front">
                  {fmtBb(seat.invested_street_bb)}bb
                </span>
              ) : null;

            // Last-action verb, sat above the cards (and the chips puck). Gated on
            // the SAME lockstep `revealed` flag as chips/fold state, so the felt
            // never shows a verb before the event log narrates it. Per-street:
            // the backend clears it when the street advances (null ⇒ no label).
            // "Fold" persists for folded seats (backend override).
            const lastAction =
              revealed && seat.last_action ? (
                <span className="sim-last-action" title="last action">
                  {actionLabel(seat.last_action)}
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
                  {lastAction}
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
                    · <span className="sim-stack num">{fmtBb(hero.stack_bb)}bb</span>
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
                {lastAction}
                {chips}
                {revealedCards ? (
                  <span className="cards sim-reveal" aria-label={`${seat.position} shows`}>
                    {revealedCards.map((c, j) => (
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
                  {fmtBb(seat.stack_bb)}bb
                  {allin && <span className="sim-allin"> all-in</span>}
                </span>
                {/* Range reveal (V2): live villain pods only. Gated on the
                    STAGED fold state (`folded` above) — same value the pod
                    display uses — so the button stays until the fold narrates
                    (spec low-2), not the instant server-truth flips. Also
                    requires a persona (no estimate without a pack). Hidden at
                    hand_over: the felt reveals real cards, an estimate is noise. */}
                {seat.persona_type && !folded && !hand.hand_over && (
                  <button
                    type="button"
                    className={
                      "sim-vrange-btn" +
                      (openRangeSeat === seat.seat_index ? " sim-vrange-btn-on" : "")
                    }
                    onClick={() => onToggleRange(seat.seat_index)}
                    aria-pressed={openRangeSeat === seat.seat_index}
                    aria-label={`${
                      openRangeSeat === seat.seat_index ? "Hide" : "Show"
                    } estimated range for ${seat.position}`}
                  >
                    range
                  </button>
                )}
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
          ? `Verdict: ${meta.label}${showLoss ? `, gave up about ${fmtEvLoss(grade.ev_loss_bb)}` : ""}`
          : "No baseline for this spot yet"
      }
    >
      <span className="sim-badge-word">{meta.label}</span>
      {showLoss && (
        <span className="sim-badge-ev num">{fmtEvLoss(grade.ev_loss_bb)}</span>
      )}
    </div>
  );
}
