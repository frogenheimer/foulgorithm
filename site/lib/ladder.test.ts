/**
 * The ladder came back to the bottom of the fixture page after a spell off it,
 * and the swap machinery that feeds it had spent that spell computing into a
 * dead value. Wiring it back up meant lifting state out of the pitch section,
 * which is exactly the moment the "published until touched, rebuilt after"
 * contract could quietly invert. So the contract lives here, testable without
 * React: untouched means the published object itself, and a rebuild only ever
 * uses whoever is actually standing on the pitches.
 */

import { describe, expect, it } from "vitest";
import { ladderFor, onPitchFrom, squadsFor, TIERS } from "./ladder";
import { who } from "./who";
import type { Explorer, ExplorerRow, Formations, Slip } from "./data";

function row(fullName: string, team: string, prob = 0.9): ExplorerRow {
  return {
    player: fullName.split(" ").slice(-1)[0],
    fullName,
    position: "MID",
    team,
    opponent: team === "Arsenal" ? "Coventry" : "Arsenal",
    fixture: "Arsenal v Coventry",
    kickoff: "2026-08-30T15:00:00Z",
    minutes: 90,
    startProbability: 1,
    confirmed: true,
    thin: false,
    expected: { committed: 1.2, drawn: 0.8, involvements: 2.0 },
    // One line, two models, high enough to build the short tiers from.
    committed: [[prob, prob - 0.05]],
    drawn: [[0.2, 0.2]],
  } as unknown as ExplorerRow;
}

function explorer(rows: ExplorerRow[]): Explorer {
  return {
    models: ["alan", "lily"],
    lines: [0.5],
    markets: ["committed", "drawn"],
    house: "house",
    rows,
  } as Explorer;
}

const SQUAD = [
  row("William Saliba", "Arsenal"),
  row("Declan Rice", "Arsenal"),
  row("Martin Odegaard", "Arsenal"),
  row("Jack Rudoni", "Coventry"),
  row("Josh Eccles", "Coventry"),
  row("Ben Sheaf", "Coventry"),
];

const PUBLISHED: Record<string, Slip[]> = { alan: [] };

describe("ladderFor", () => {
  it("returns the published ladder itself until a reader changes something", () => {
    const out = ladderFor(explorer(SQUAD), "Arsenal v Coventry", new Set(), false, PUBLISHED);
    expect(out).toBe(PUBLISHED);
  });

  it("rebuilds only from the players on the pitch once something changed", () => {
    const onPitch = new Set(SQUAD.slice(0, 5).map((r) => r.player));
    const out = ladderFor(explorer(SQUAD), "Arsenal v Coventry", onPitch, true, PUBLISHED);
    expect(Object.keys(out).length).toBeGreaterThan(0);
    const labels = new Set(TIERS.map(([, l]) => l));
    for (const slips of Object.values(out)) {
      for (const slip of slips) {
        expect(labels.has(slip.targetLabel)).toBe(true);
        for (const leg of slip.legs) expect(onPitch.has(leg.player)).toBe(true);
      }
    }
    // Sheaf is off the pitch, so no rebuilt combination may lean on him.
    const legs = Object.values(out).flatMap((s) => s.flatMap((slip) => slip.legs));
    expect(legs.some((l) => l.player === "Sheaf")).toBe(false);
  });

  it("rebuilds to an empty ladder when nobody is on the pitch", () => {
    const out = ladderFor(explorer(SQUAD), "Arsenal v Coventry", new Set(), true, PUBLISHED);
    expect(out).toEqual({});
  });

  it("ignores rows from other fixtures", () => {
    const stray = { ...row("Moises Caicedo", "Chelsea"), fixture: "Chelsea v Brighton" };
    const onPitch = new Set([...SQUAD.map((r) => r.player), "Caicedo"]);
    const out = ladderFor(
      explorer([...SQUAD, stray as ExplorerRow]),
      "Arsenal v Coventry",
      onPitch,
      true,
      PUBLISHED
    );
    const legs = Object.values(out).flatMap((s) => s.flatMap((slip) => slip.legs));
    expect(legs.some((l) => l.player === "Caicedo")).toBe(false);
  });
});

describe("squadsFor", () => {
  it("splits one fixture's rows by club and keeps other fixtures out", () => {
    const stray = { ...row("Moises Caicedo", "Chelsea"), fixture: "Chelsea v Brighton" };
    const squads = squadsFor(
      explorer([...SQUAD, stray as ExplorerRow]),
      "Arsenal v Coventry",
      ["Arsenal", "Coventry"]
    );
    expect(squads.Arsenal.map((r) => r.player)).toEqual(["Saliba", "Rice", "Odegaard"]);
    expect(squads.Coventry).toHaveLength(3);
  });
});

describe("onPitchFrom", () => {
  const shapes = {
    Arsenal: {
      formation: "1-1",
      lines: [[{ player: "Saliba", position: "DEF", detail: "", shirt: 2 }]],
      bench: [],
    },
  } as unknown as Formations[string];
  const squads = { Arsenal: SQUAD.slice(0, 3) };

  it("resolves the published eleven from the team-sheet names", () => {
    const names = onPitchFrom(shapes, ["Arsenal"], {}, squads);
    expect(names).toEqual(new Set(["Saliba"]));
  });

  it("prefers a swap over the published name in the same slot", () => {
    const names = onPitchFrom(
      shapes,
      ["Arsenal"],
      { "Arsenal|0|0": who("Declan Rice") },
      squads
    );
    expect(names).toEqual(new Set(["Rice"]));
  });
});
