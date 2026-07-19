import { describe, expect, it } from "vitest";

import type { EventView } from "../../api/types";
import { stagedTableState } from "./simPlayback";

function event(street: string, position = "BTN"): EventView {
  return {
    seat_index: 1,
    position,
    action: "call",
    amount_bb: 1,
    street,
  };
}

describe("stagedTableState", () => {
  const finalBoard = ["As", "Kd", "7c", "2h", "Jd"];

  it("keeps a preflop fold playout from revealing the final board early", () => {
    const events = [event("preflop", "BTN"), event("preflop", "SB")];

    expect(
      stagedTableState({
        finalStreet: "flop",
        finalBoard: finalBoard.slice(0, 3),
        events,
        stagedIndex: 0,
      }),
    ).toEqual({ street: "preflop", board: [] });

    expect(
      stagedTableState({
        finalStreet: "flop",
        finalBoard: finalBoard.slice(0, 3),
        events,
        stagedIndex: events.length,
      }),
    ).toEqual({ street: "flop", board: finalBoard.slice(0, 3) });
  });

  it("keeps a big-blind preflop fold face-down when the first remaining bot action is on the flop", () => {
    const events = [event("flop", "SB"), event("flop", "BTN")];

    expect(
      stagedTableState({
        startStreet: "preflop",
        finalStreet: "river",
        finalBoard,
        events,
        stagedIndex: 0,
      }),
    ).toEqual({ street: "preflop", board: [] });

    expect(
      stagedTableState({
        startStreet: "preflop",
        finalStreet: "river",
        finalBoard,
        events,
        stagedIndex: 1,
      }),
    ).toEqual({ street: "flop", board: finalBoard.slice(0, 3) });
  });

  it("reveals streets only when the narrated event prefix reaches them", () => {
    const events = [
      event("preflop", "BTN"),
      event("flop", "SB"),
      event("turn", "BB"),
      event("river", "BTN"),
    ];

    expect(
      stagedTableState({ finalStreet: "river", finalBoard, events, stagedIndex: 1 }),
    ).toEqual({ street: "preflop", board: [] });
    expect(
      stagedTableState({ finalStreet: "river", finalBoard, events, stagedIndex: 2 }),
    ).toEqual({ street: "flop", board: finalBoard.slice(0, 3) });
    expect(
      stagedTableState({ finalStreet: "river", finalBoard, events, stagedIndex: 3 }),
    ).toEqual({ street: "turn", board: finalBoard.slice(0, 4) });
    expect(
      stagedTableState({ finalStreet: "river", finalBoard, events, stagedIndex: 4 }),
    ).toEqual({ street: "river", board: finalBoard });
  });

  it("keeps the current postflop board visible before the next bot action narrates", () => {
    const events = [event("flop", "SB"), event("flop", "BB")];

    expect(
      stagedTableState({
        finalStreet: "turn",
        finalBoard: finalBoard.slice(0, 4),
        events,
        stagedIndex: 0,
      }),
    ).toEqual({ street: "flop", board: finalBoard.slice(0, 3) });
  });
});
