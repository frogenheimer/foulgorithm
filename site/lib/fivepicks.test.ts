/**
 * The matrix's rows were born inside a component, which meant the sort that
 * decides who "the five agree on" had no tests when the matrix moved from the
 * fixture page to The five page. Moving display code is exactly when a silent
 * derivation bug slips in, so the derivation now lives in lib where it can be
 * held still while the display around it moves.
 */

import { describe, expect, it } from "vitest";
import { matrixRows, slateFixtures } from "./fivepicks";
import type { FixtureBoard, Slates, SlipLeg } from "./data";

function leg(
  player: string,
  fixture: string,
  fouls = 1,
  market: "committed" | "drawn" = "committed",
  fullName?: string
): SlipLeg {
  return {
    player,
    fullName: fullName ?? `A ${player}`,
    fixture,
    market,
    fouls,
    line: fouls - 0.5,
    prob: 0.6,
    outOf100: 60,
  } as unknown as SlipLeg;
}

function slates(byCharacter: Slates["byCharacter"]): Slates {
  return {
    shapes: [
      { key: "six-ones", label: "Six at 1+", legs: 6 },
      { key: "three-twos", label: "Three at 2+", legs: 3 },
    ],
    byCharacter,
    note: "",
  } as Slates;
}

function board(label: string, kickoff: string): FixtureBoard {
  const [home, away] = label.split(" v ");
  return { home, away, kickoff } as unknown as FixtureBoard;
}

const GAME = "Arsenal v Coventry";

describe("matrixRows", () => {
  it("counts a character once per player, even across two shapes", () => {
    const rows = matrixRows(
      slates({
        alan: {
          "six-ones": { legs: [leg("Saliba", GAME, 1)], label: "" },
          "three-twos": { legs: [leg("Saliba", GAME, 2)], label: "" },
        },
      }),
      GAME,
      ["alan"]
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].backers).toBe(1);
    // The first shape's line is the one shown.
    expect(rows[0].byCharacter.alan).toBe("1+");
  });

  it("skips legs from other fixtures", () => {
    const rows = matrixRows(
      slates({
        alan: {
          "six-ones": {
            legs: [leg("Saliba", GAME), leg("Caicedo", "Chelsea v Brighton")],
            label: "",
          },
        },
      }),
      GAME,
      ["alan"]
    );
    expect(rows.map((r) => r.player)).toEqual(["Saliba"]);
  });

  it("keeps fouls committed and fouls won as separate rows for one player", () => {
    const rows = matrixRows(
      slates({
        alan: {
          "six-ones": {
            legs: [leg("Saliba", GAME, 1, "committed"), leg("Saliba", GAME, 1, "drawn")],
            label: "",
          },
        },
      }),
      GAME,
      ["alan"]
    );
    expect(rows).toHaveLength(2);
    expect(new Set(rows.map((r) => r.market))).toEqual(new Set(["committed", "drawn"]));
  });

  it("floats agreement to the top, then sorts by name", () => {
    const rows = matrixRows(
      slates({
        alan: { "six-ones": { legs: [leg("Zubimendi", GAME), leg("Saliba", GAME)], label: "" } },
        lily: { "six-ones": { legs: [leg("Saliba", GAME), leg("Andersen", GAME)], label: "" } },
      }),
      GAME,
      ["alan", "lily"]
    );
    expect(rows.map((r) => r.player)).toEqual(["Saliba", "Andersen", "Zubimendi"]);
    expect(rows[0].backers).toBe(2);
  });

  it("tolerates a character with no slates and a shape a character passed on", () => {
    const rows = matrixRows(
      slates({
        alan: { "six-ones": { legs: [leg("Saliba", GAME)], label: "" }, "three-twos": null },
      }),
      GAME,
      ["alan", "lily"]
    );
    expect(rows).toHaveLength(1);
  });

  it("keys rows on the full name, so two short names cannot merge", () => {
    const rows = matrixRows(
      slates({
        alan: {
          "six-ones": {
            legs: [
              leg("Ward", GAME, 1, "committed", "Daniel Ward"),
              leg("Ward", GAME, 1, "committed", "Joel Ward"),
            ],
            label: "",
          },
        },
      }),
      GAME,
      ["alan"]
    );
    expect(rows).toHaveLength(2);
    expect(rows[0].key).not.toBe(rows[1].key);
  });
});

describe("slateFixtures", () => {
  const BY: Slates["byCharacter"] = {
    alan: { "six-ones": { legs: [leg("Saliba", "Arsenal v Coventry")], label: "" } },
    lily: {
      "six-ones": {
        legs: [leg("Mateta", "Palace v Wolves"), leg("Saliba", "Arsenal v Coventry")],
        label: "",
      },
    },
  };

  it("unions every game the slates touch, once each, in kickoff order", () => {
    const games = slateFixtures(slates(BY), [
      board("Palace v Wolves", "2026-08-28T19:00:00Z"),
      board("Arsenal v Coventry", "2026-08-30T15:00:00Z"),
    ]);
    expect(games).toEqual(["Palace v Wolves", "Arsenal v Coventry"]);
  });

  it("sorts games the board does not know alphabetically, after the known ones", () => {
    const games = slateFixtures(slates(BY), [
      board("Arsenal v Coventry", "2026-08-30T15:00:00Z"),
    ]);
    expect(games).toEqual(["Arsenal v Coventry", "Palace v Wolves"]);
  });
});
