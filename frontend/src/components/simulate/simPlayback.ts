import type { EventView } from "../../api/types";

const STREET_BOARD_COUNT: Record<string, number> = {
  preflop: 0,
  flop: 3,
  turn: 4,
  river: 5,
};

export interface StagedTableState {
  street: string;
  board: string[];
}

function boardCountForStreet(street: string): number {
  return STREET_BOARD_COUNT[street] ?? 0;
}

export function stagedTableState({
  startStreet,
  finalStreet,
  finalBoard,
  events,
  stagedIndex,
}: {
  startStreet?: string | null;
  finalStreet: string;
  finalBoard: string[];
  events: EventView[];
  stagedIndex: number;
}): StagedTableState {
  if (events.length === 0 || stagedIndex >= events.length) {
    return { street: finalStreet, board: finalBoard };
  }

  const shown = events.slice(0, Math.max(0, stagedIndex));
  const street =
    shown.length > 0
      ? shown[shown.length - 1].street
      : startStreet ?? events[0]?.street ?? finalStreet;
  return {
    street,
    board: finalBoard.slice(0, Math.min(finalBoard.length, boardCountForStreet(street))),
  };
}
