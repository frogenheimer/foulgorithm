/**
 * The client-side port of the pipeline's `_house_sheet`, exercised on the
 * same cases as tests/test_house_sheet.py so the two can never drift: same
 * top-three ranking, same 3+ floor, same safest-first tiers, a player badged once.
 */

import { describe, expect, it } from "vitest";
import { houseSheetFrom } from "./housesheet";
import { who } from "./who";
import type { Explorer, ExplorerRow } from "./data";

const MODELS = ["alan", "tayler"];
const HOUSE_IDX = 1;

function row(name: string, committed: number[], drawn: number[]): ExplorerRow {
  const grid = (ps: number[]) =>
    [0, 1, 2, 3].map((i) => MODELS.map((_, m) => (m === HOUSE_IDX ? (ps[i] ?? 0) : 0)));
  return {
    player: name,
    fullName: `Full ${name}`,
    position: "MID",
    team: "A",
    opponent: "B",
    fixture: "A v B",
    kickoff: "2026-08-28T19:00:00Z",
    minutes: 90,
    startProbability: 1,
    confirmed: true,
    thin: false,
    expected: { committed: 1, drawn: 1, involvements: 2 },
    career: null,
    committed: grid(committed),
    drawn: grid(drawn),
    involvements: grid([0, 0, 0, 0]),
    pmf: { committed: [], drawn: [], involvements: [] },
  };
}

const ROWS = [
  row("Sangare", [0.73, 0.41, 0.22, 0.05], [0.3, 0.1, 0.02, 0]),
  row("Anderson", [0.68, 0.36, 0.15, 0.03], [0.4, 0.15, 0.03, 0]),
  row("Tanaka", [0.61, 0.3, 0.1, 0.02], [0.64, 0.33, 0.08, 0]),
  row("Aina", [0.35, 0.12, 0.03, 0.01], [0.58, 0.28, 0.06, 0]),
];

const EXPLORER: Explorer = {
  models: MODELS,
  lines: [0.5, 1.5, 2.5, 3.5],
  markets: ["committed", "drawn", "involvements"],
  house: "tayler",
  rows: ROWS,
};

const ON_PITCH = new Set(ROWS.map((r) => who(r.fullName)));

describe("houseSheetFrom", () => {
  it("holds the top three by the house price", () => {
    const sheet = houseSheetFrom(EXPLORER, "A v B", ON_PITCH);
    const onePlus = sheet.groups.find((g) => g.market === "committed" && g.line === 1)!;
    expect(onePlus.picks.map((p) => p.player)).toEqual(["Sangare", "Anderson", "Tanaka"]);
    expect(onePlus.picks[0].outOf100).toBe(73);
  });

  it("shows 3+ only when somebody prices there", () => {
    const sheet = houseSheetFrom(EXPLORER, "A v B", ON_PITCH);
    const lines = sheet.groups.map((g) => `${g.market}${g.line}`);
    expect(lines).toContain("committed3");
    expect(lines).not.toContain("drawn3");
  });

  it("badges three tiers safest first, a player at most once", () => {
    const sheet = houseSheetFrom(EXPLORER, "A v B", ON_PITCH);
    const tier = (market: string, line: number) =>
      sheet.groups.find((g) => g.market === market && g.line === line)?.picks.find((p) => p.tier);
    expect(tier("committed", 1)?.player).toBe("Sangare");
    expect(tier("committed", 1)?.tier).toBe("safe");
    expect(tier("drawn", 1)?.player).toBe("Tanaka");
    expect(tier("committed", 2)?.player).toBe("Anderson");
    expect(tier("committed", 2)?.tier).toBe("optimistic");
    expect(tier("drawn", 2)?.player).toBe("Aina");
    expect(tier("committed", 3)).toBeUndefined();
    const names = sheet.groups.flatMap((g) => g.picks.filter((p) => p.tier).map((p) => p.player));
    expect(new Set(names).size).toBe(names.length);
  });

  it("only reads players who are on the pitch", () => {
    const without = new Set(ON_PITCH);
    without.delete(who("Full Sangare"));
    const sheet = houseSheetFrom(EXPLORER, "A v B", without);
    const onePlus = sheet.groups.find((g) => g.market === "committed" && g.line === 1)!;
    expect(onePlus.picks.map((p) => p.player)).toEqual(["Anderson", "Tanaka", "Aina"]);
  });
});
