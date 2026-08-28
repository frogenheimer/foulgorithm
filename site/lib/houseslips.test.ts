/**
 * Mirrors tests/test_league.py's house-slip cases so the port cannot drift.
 */

import { describe, expect, it } from "vitest";
import { houseSlipsFrom } from "./houseslips";
import { who } from "./who";
import type { Explorer, ExplorerRow } from "./data";

const MODELS = ["alan", "tayler"];
const HOUSE = 1;

function row(name: string, committed: number[], drawn: number[]): ExplorerRow {
  const grid = (ps: number[]) => [0, 1, 2, 3].map((i) => MODELS.map((_, m) => (m === HOUSE ? (ps[i] ?? 0) : 0)));
  return {
    player: name, fullName: `Full ${name}`, position: "MID", team: "A", opponent: "B", fixture: "A v B",
    kickoff: "2026-09-05T14:00:00Z", minutes: 90, startProbability: 1, confirmed: true, thin: false,
    expected: { committed: 1, drawn: 1, involvements: 2 }, career: null,
    committed: grid(committed), drawn: grid(drawn), involvements: grid([0, 0, 0, 0]),
    pmf: { committed: [], drawn: [], involvements: [] },
  } as ExplorerRow;
}

// Twenty players at falling prices; P0 clears the 3+ floor at 0.28.
const ROWS = Array.from({ length: 20 }, (_, i) =>
  row(`P${i}`, [0.9 - i * 0.02, 0.6 - i * 0.02, Math.max(0.03, 0.28 - i * 0.01), 0.01], [0.5 - i * 0.02, 0.2 - i * 0.01, 0.05, 0.01])
);
const EXPLORER: Explorer = { models: MODELS, lines: [0.5, 1.5, 2.5, 3.5], markets: ["committed", "drawn", "involvements"], house: "tayler", rows: ROWS };
const ALL = new Set(ROWS.map((r) => who(r.fullName)));

describe("houseSlipsFrom", () => {
  it("builds the three tiers to their counts", () => {
    const slips = houseSlipsFrom(EXPLORER, "A v B", ALL);
    for (const [tier, units] of [["safe", 4], ["optimistic", 5], ["rogue", 6]] as const) {
      const bet = slips[tier]!;
      expect(bet.legs.reduce((n, l) => n + l.fouls, 0)).toBe(units);
      expect(bet.legs.every((l) => l.prob === l.houseProb)).toBe(true);
    }
  });

  it("escalates in shape: four 1+, a 2+ lead, a 3+ lead above the floor", () => {
    const slips = houseSlipsFrom(EXPLORER, "A v B", ALL);
    expect(slips.safe!.legs.map((l) => l.fouls)).toEqual([1, 1, 1, 1]);
    expect([...slips.optimistic!.legs.map((l) => l.fouls)].sort()).toEqual([1, 1, 1, 2]);
    expect([...slips.rogue!.legs.map((l) => l.fouls)].sort()).toEqual([1, 2, 3]);
  });

  it("falls back to two 2+ legs when nobody clears the 3+ floor", () => {
    const flat = { ...EXPLORER, rows: ROWS.map((r) => ({ ...r, committed: r.committed.map((line, i) => (i === 2 ? line.map(() => 0.1) : line)) })) };
    const slips = houseSlipsFrom(flat, "A v B", ALL);
    expect([...slips.rogue!.legs.map((l) => l.fouls)].sort()).toEqual([1, 1, 2, 2]);
  });

  it("only reads players on the pitch", () => {
    const without = new Set(ALL);
    without.delete(who("Full P0"));
    const slips = houseSlipsFrom(EXPLORER, "A v B", without);
    expect(slips.safe!.legs.map((l) => l.player)).not.toContain("P0");
  });
});
