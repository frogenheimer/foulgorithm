import { describe, expect, it } from "vitest";
import { buildRows, compare, houseTiers } from "./matchplayers";
import type { ExplorerRow } from "./data";

function row(player: string, fullName: string, team: string, committed: number, drawn: number, minutes = 85): ExplorerRow {
  return {
    player, fullName, position: "MF", team, opponent: "B", fixture: "A v B",
    kickoff: "2026-08-29T14:00:00Z", minutes, startProbability: 0.9, confirmed: false, thin: false,
    expected: { committed, drawn, involvements: committed + drawn },
    career: { committed: committed + 0.1, drawn: drawn - 0.1, involvements: committed + drawn, nineties: 20 },
    committed: [], drawn: [], involvements: [], pmf: { committed: [], drawn: [], involvements: [] },
  } as ExplorerRow;
}

const ROWS = [row("Nyoni", "Trey Nyoni", "A", 1.2, 0.5), row("Gakpo", "Cody Gakpo", "A", 0.9, 1.1), row("Sub", "Some Sub", "A", 0.3, 0.2, 10)];
const SHAPES = {
  A: { formation: null, predicted: true, lines: [[{ player: "Trey Nyoni", position: "M", detail: "", shirt: 1 }], [{ player: "Cody Gakpo", position: "F", detail: "", shirt: 2 }]], bench: [] },
};
const SLIPS = {
  safe: { legs: [{ player: "Nyoni", fullName: "Trey Nyoni", market: "committed", line: 0.5, fouls: 1, prob: 0.5, outOf100: 50 }], label: "Safe" },
  rogue: { legs: [{ player: "Nyoni", fullName: "Trey Nyoni", market: "committed", line: 1.5, fouls: 2, prob: 0.2, outOf100: 20 }, { player: "Gakpo", fullName: "Cody Gakpo", market: "drawn", line: 0.5, fouls: 1, prob: 0.6, outOf100: 60 }], label: "Rogue" },
};

describe("the match players table", () => {
  it("marks the eleven from the shape and reads whether it is confirmed", () => {
    const built = buildRows(ROWS, SHAPES as never, SLIPS as never);
    expect(built.confirmed).toBe(false);
    expect(built.rows.map((x) => x.xi)).toEqual([true, true, false]);
  });

  it("badges a player with the safest house slip he sits on", () => {
    const tiers = houseTiers(SLIPS as never);
    expect(tiers.get("trey nyoni")).toBe("safe");
    expect(tiers.get("cody gakpo")).toBe("rogue");
  });

  it("reads actuals off the outcomes once played", () => {
    const outcomes = { "Trey Nyoni|committed|0.5": { won: true, observed: 3 }, "Trey Nyoni|drawn|0.5": { won: false, observed: 0 } };
    const built = buildRows(ROWS, SHAPES as never, SLIPS as never, outcomes);
    expect(built.rows[0].actualFouls).toBe(3);
    expect(built.rows[0].actualFouled).toBe(0);
    expect(built.rows[1].actualFouls).toBeNull();
  });

  it("sorts every column, expected figures descending", () => {
    const built = buildRows(ROWS, SHAPES as never, SLIPS as never).rows;
    expect([...built].sort(compare("fouled")).map((x) => x.r.player)).toEqual(["Gakpo", "Nyoni", "Sub"]);
    expect([...built].sort(compare("house")).map((x) => x.r.player)[0]).toBe("Nyoni");
    expect([...built].sort(compare("xi")).map((x) => x.xi)).toEqual([true, true, false]);
  });
});
