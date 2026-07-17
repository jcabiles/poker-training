import { describe, it, expect } from "vitest";

import type { StreetReportRow } from "../../api/types";
import { aggregateRates, goodPct, optimalPct } from "./simGrade";

function makeRow(overrides: Partial<StreetReportRow> = {}): StreetReportRow {
  return {
    street: "preflop",
    graded: 0,
    optimal: 0,
    acceptable: 0,
    mistake: 0,
    blunder: 0,
    ev_loss_bb: 0,
    no_baseline: 0,
    ...overrides,
  };
}

describe("goodPct / optimalPct", () => {
  it("computes integer percentages on a normal row", () => {
    const row = makeRow({ graded: 10, optimal: 6, acceptable: 2, mistake: 1, blunder: 1 });
    expect(goodPct(row)).toBe(80);
    expect(optimalPct(row)).toBe(60);
  });

  it("returns null when graded === 0", () => {
    const row = makeRow({ graded: 0, no_baseline: 5 });
    expect(goodPct(row)).toBeNull();
    expect(optimalPct(row)).toBeNull();
  });
});

describe("aggregateRates", () => {
  it("sums counts across mixed street rows and derives rates from the summed totals", () => {
    const rows: StreetReportRow[] = [
      makeRow({ street: "preflop", graded: 10, optimal: 6, acceptable: 2, mistake: 1, blunder: 1, no_baseline: 3 }),
      makeRow({ street: "flop", graded: 8, optimal: 3, acceptable: 3, mistake: 1, blunder: 1, no_baseline: 0 }),
      makeRow({ street: "turn", graded: 5, optimal: 1, acceptable: 1, mistake: 2, blunder: 1, no_baseline: 2 }),
      makeRow({ street: "river", graded: 0, optimal: 0, acceptable: 0, mistake: 0, blunder: 0, no_baseline: 4 }),
    ];

    const result = aggregateRates(rows);

    const graded = 10 + 8 + 5 + 0;
    const optimal = 6 + 3 + 1 + 0;
    const acceptable = 2 + 3 + 1 + 0;
    const no_baseline = 3 + 0 + 2 + 4;

    expect(result.graded).toBe(graded);
    expect(result.optimal).toBe(optimal);
    expect(result.acceptable).toBe(acceptable);
    expect(result.no_baseline).toBe(no_baseline);
    expect(result.goodPct).toBe(Math.round(((optimal + acceptable) / graded) * 100));
    expect(result.optimalPct).toBe(Math.round((optimal / graded) * 100));
  });

  it("returns null rates when only no_baseline is present (all-zero-graded rows)", () => {
    const rows: StreetReportRow[] = [
      makeRow({ street: "preflop", no_baseline: 4 }),
      makeRow({ street: "flop", no_baseline: 2 }),
    ];

    const result = aggregateRates(rows);

    expect(result.graded).toBe(0);
    expect(result.goodPct).toBeNull();
    expect(result.optimalPct).toBeNull();
    expect(result.no_baseline).toBe(6);
  });

  it("handles an empty rows array", () => {
    const result = aggregateRates([]);

    expect(result.graded).toBe(0);
    expect(result.optimal).toBe(0);
    expect(result.acceptable).toBe(0);
    expect(result.no_baseline).toBe(0);
    expect(result.goodPct).toBeNull();
    expect(result.optimalPct).toBeNull();
  });
});
