/**
 * The pitch has produced the same class of bug four times.
 *
 * A player cloned across two slots. An accent breaking a lookup. A dropdown
 * offering a short name into a slot holding a long one. A shirt number left
 * behind by the player who used to wear it. None of those are rendering bugs,
 * so none of them needed React to reproduce, and none of them were caught
 * because this logic had no tests at all.
 */

import { describe, expect, it } from "vitest";
import {
  benchFrom,
  lines,
  markerFor,
  occupancy,
  outOfPosition,
  placeInto,
  positionCode,
  shirtIndex,
} from "./pitch";
import { findPlayer, who } from "./who";
import type { ExplorerRow, Spot, TeamShape } from "./data";

function row(fullName: string, position = "MID", player?: string): ExplorerRow {
  return {
    player: player ?? fullName.split(" ").slice(-1)[0],
    fullName,
    position,
    team: "Newcastle",
    opponent: "Liverpool",
    fixture: "Newcastle v Liverpool",
    kickoff: "2026-08-25T19:00:00Z",
    minutes: 90,
    startProbability: 1,
    confirmed: true,
    thin: false,
    expected: { committed: 1.2, drawn: 0.8, involvements: 2.0 },
    committed: [],
    drawn: [],
  } as unknown as ExplorerRow;
}

function spot(player: string, position: string, shirt: number | null = null): Spot {
  return { player, position, detail: "", shirt };
}

const SHAPE: TeamShape = {
  formation: "4-3-3",
  lines: [
    [spot("Nick Pope", "G", 22)],
    [
      spot("Kieran Trippier", "D", 2),
      spot("Fabian Schar", "D", 5),
      spot("Sven Botman", "D", 4),
      spot("Lewis Hall", "D", 20),
    ],
    [spot("Bruno Guimaraes", "M", 39), spot("Joelinton", "M", 7), spot("Sandro Tonali", "M", 8)],
    [spot("Jacob Murphy", "F", 23), spot("Nick Woltemade", "F", 27), spot("Anthony Gordon", "F", 10)],
  ],
  bench: [spot("Dan Burn", "D", 33), spot("Harvey Barnes", "M", 15)],
};

const SQUAD: ExplorerRow[] = [
  row("Nick Pope", "GKP"),
  row("Kieran Trippier", "DEF"),
  row("Fabian Schar", "DEF"),
  row("Sven Botman", "DEF"),
  row("Lewis Hall", "DEF"),
  row("Bruno Guimaraes", "MID"),
  row("Joelinton", "MID"),
  row("Sandro Tonali", "MID"),
  row("Jacob Murphy", "MID"),
  row("Nick Woltemade", "FWD"),
  row("Anthony Gordon", "FWD"),
  row("Dan Burn", "DEF"),
  row("Harvey Barnes", "MID"),
  row("Luka Vušković", "DEF"),
];

const here = () => occupancy(SHAPE, SQUAD, {}, findPlayer, "NEW");

describe("the marker on a player's chest", () => {
  const shirts = shirtIndex(SHAPE);

  it("is his own number, not the slot's", () => {
    const burn = SQUAD.find((r) => r.fullName === "Dan Burn")!;
    const midfieldSlot = SHAPE.lines[2][0];
    expect(markerFor(shirts, burn, midfieldSlot)).toBe("33");
    expect(markerFor(shirts, burn, midfieldSlot)).not.toBe("39");
  });

  it("falls back to his position when he has no number in the squad", () => {
    const outsider = row("Rio Ngumoha", "MID");
    expect(markerFor(shirts, outsider, SHAPE.lines[1][0])).toBe("M");
  });

  it("uses the slot only when the slot is empty", () => {
    expect(markerFor(shirts, undefined, SHAPE.lines[0][0])).toBe("22");
  });

  it("indexes bench numbers too, so a substitute keeps his", () => {
    expect(shirts.get(who("Harvey Barnes"))).toBe(15);
  });
});

describe("position codes", () => {
  it("maps both codings onto one letter", () => {
    expect(positionCode("DEF")).toBe("D");
    expect(positionCode("D")).toBe("D");
    expect(positionCode("GKP")).toBe("G");
    expect(positionCode("FWD")).toBe("F");
  });

  it("treats anything unrecognised as midfield rather than throwing", () => {
    expect(positionCode("")).toBe("M");
    expect(positionCode("???")).toBe("M");
  });

  it("marks a defender standing in midfield", () => {
    const burn = SQUAD.find((r) => r.fullName === "Dan Burn")!;
    expect(outOfPosition(burn, SHAPE.lines[2][0])).toBe(true);
    expect(outOfPosition(burn, SHAPE.lines[1][0])).toBe(false);
  });

  it("says nothing about an empty slot", () => {
    expect(outOfPosition(undefined, SHAPE.lines[1][0])).toBe(false);
  });
});

describe("the shape never reflows", () => {
  it("keeps the published lines when nothing has been swapped", () => {
    expect(lines(SHAPE, here(), false).map((l) => l.length)).toEqual([1, 4, 3, 3]);
  });

  it("keeps them after a swap, because one change must not move eleven markers", () => {
    const next = placeInto({}, here(), "NEW|5", who("Dan Burn"));
    const after = occupancy(SHAPE, SQUAD, next, findPlayer, "NEW");
    expect(lines(SHAPE, after, false).map((l) => l.length)).toEqual([1, 4, 3, 3]);
  });

  it("mirrors for the away side without changing the grouping", () => {
    expect(lines(SHAPE, here(), true).map((l) => l.length)).toEqual([3, 3, 4, 1]);
  });
});

describe("placing a player", () => {
  it("puts him in the slot", () => {
    const next = placeInto({}, here(), "NEW|5", who("Dan Burn"));
    expect(next["NEW|5"]).toBe(who("Dan Burn"));
  });

  it("exchanges two players already on the pitch rather than cloning one", () => {
    const next = placeInto({}, here(), "NEW|5", who("Joelinton"));
    const after = occupancy(SHAPE, SQUAD, next, findPlayer, "NEW");
    const names = after.filter((o) => o.row).map((o) => who(o.row!.fullName));
    expect(new Set(names).size).toBe(names.length);
    expect(names.filter((n) => n === who("Joelinton"))).toHaveLength(1);
  });

  it("leaves the swapped-out player nowhere when he came from the bench", () => {
    const next = placeInto({}, here(), "NEW|5", who("Harvey Barnes"));
    const after = occupancy(SHAPE, SQUAD, next, findPlayer, "NEW");
    const names = after.filter((o) => o.row).map((o) => who(o.row!.fullName));
    expect(names).not.toContain(who("Bruno Guimaraes"));
    expect(new Set(names).size).toBe(names.length);
  });

  it("does nothing when he is already in that slot", () => {
    const start = placeInto({}, here(), "NEW|5", who("Dan Burn"));
    const after = occupancy(SHAPE, SQUAD, start, findPlayer, "NEW");
    expect(placeInto(start, after, "NEW|5", who("Dan Burn"))).toEqual(start);
  });

  it("survives accents, which is how Boscagli ended up on the pitch three times", () => {
    const next = placeInto({}, here(), "NEW|1", who("Luka Vušković"));
    const after = occupancy(SHAPE, SQUAD, next, findPlayer, "NEW");
    const names = after.filter((o) => o.row).map((o) => who(o.row!.fullName));
    expect(new Set(names).size).toBe(names.length);
    expect(names).toContain("luka vuskovic");
  });
});

describe("the bench", () => {
  it("holds everyone not currently on the pitch", () => {
    const bench = benchFrom(SQUAD, here());
    expect(bench.map((r) => r.fullName)).toContain("Dan Burn");
    expect(bench.map((r) => r.fullName)).not.toContain("Nick Pope");
  });

  it("gains the player who was displaced by a substitution", () => {
    const next = placeInto({}, here(), "NEW|5", who("Dan Burn"));
    const after = occupancy(SHAPE, SQUAD, next, findPlayer, "NEW");
    const bench = benchFrom(SQUAD, after).map((r) => r.fullName);
    expect(bench).toContain("Bruno Guimaraes");
    expect(bench).not.toContain("Dan Burn");
  });

  it("never lists the same player twice", () => {
    const next = placeInto({}, here(), "NEW|5", who("Harvey Barnes"));
    const after = occupancy(SHAPE, SQUAD, next, findPlayer, "NEW");
    const bench = benchFrom(SQUAD, after).map((r) => who(r.fullName));
    expect(new Set(bench).size).toBe(bench.length);
  });
});

describe("a slot whose player cannot be resolved", () => {
  /**
   * The screenshot showed "Rio Ngumoha" on the pitch with a dash for a rate,
   * while Ngumoha also sat in Liverpool's bench list. One player, two places.
   *
   * The cause: when the lookup missed, the slot fell back to the name the team
   * sheet printed, so it drew the previous occupant as though he were standing
   * there. He was not, which is why he was also on the bench and why he had no
   * number. A slot nobody resolves to is empty, and has to look empty.
   */
  const GHOST: TeamShape = {
    formation: "4-3-3",
    lines: [[spot("Nick Pope", "G", 22), spot("Someone Unknown", "D", 99)]],
    bench: [],
  };

  it("does not draw the team sheet's name when nobody matches it", () => {
    const here = occupancy(GHOST, SQUAD, {}, findPlayer, "NEW");
    const ghost = here[1];
    expect(ghost.row).toBeUndefined();
    expect(ghost.name).not.toBe("Someone Unknown");
    expect(ghost.vacant).toBe(true);
  });

  it("does not draw the previous occupant when a swap fails to resolve", () => {
    const here = occupancy(GHOST, SQUAD, { "NEW|0": "nobody at all" }, findPlayer, "NEW");
    expect(here[0].row).toBeUndefined();
    expect(here[0].name).not.toBe("Nick Pope");
    expect(here[0].vacant).toBe(true);
  });

  it("leaves a resolved slot alone", () => {
    const here = occupancy(GHOST, SQUAD, {}, findPlayer, "NEW");
    expect(here[0].row?.fullName).toBe("Nick Pope");
    expect(here[0].vacant).toBe(false);
  });

  it("never lists a player on the pitch and on the bench at once", () => {
    const here = occupancy(GHOST, SQUAD, {}, findPlayer, "NEW");
    const bench = benchFrom(SQUAD, here).map((r) => r.fullName);
    const onPitch = here.filter((o) => o.row).map((o) => o.row!.fullName);
    expect(bench.filter((n) => onPitch.includes(n))).toEqual([]);
  });
});

describe("two teams, one selection map", () => {
  it("a swap on one pitch never touches the other side's slots", () => {
    // The bug: keys were the bare index, both teams shared "0" to "10", and
    // subbing into one side made the same-index player VANISH from the other.
    const next = placeInto({}, here(), "NEW|5", who("Dan Burn"));
    const away = occupancy(SHAPE, SQUAD, next, findPlayer, "LIV");
    expect(away.filter((o) => o.vacant)).toHaveLength(0);
    expect(away.map((o) => o.name)).toEqual(here().map((o) => o.name));
  });
});
