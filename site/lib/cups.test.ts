/**
 * The cup data contract, checked on the site side too.
 *
 * The Python publisher has its own tests for what it writes. These check what
 * the site does with it, and the important one is the same rule from the other
 * end: a tie involving a Championship club must not be able to render a player
 * pick, whatever arrives in the JSON.
 */

import { describe, expect, it } from "vitest";
import {
  cupFromSlug,
  cupHref,
  cupPath,
  showsHouseSheet,
  sideNote,
  totalHeadline,
} from "./cups";
import type { CupTie } from "./cups";

const tie = (over: Partial<CupTie> = {}): CupTie => ({
  slug: "arsenal-v-wrexham-fa-cup",
  competition: "FA Cup",
  round: "3rd Round",
  home: "Arsenal",
  away: "Wrexham",
  kickoff: "2026-09-01T19:00:00+00:00",
  kind: "total",
  referee: null,
  refereePending: true,
  compare: [],
  crossDivision: null,
  record: {
    home: { team: "Arsenal", matches: 39, spell: "39 in the Premier League", division: "E0", crossedDivisions: false },
    away: { team: "Wrexham", matches: 47, spell: "47 in the Championship", division: "E1", crossedDivisions: false },
  },
  headToHead: { meetings: 0, rows: [], fouls: {}, totalFouls: null },
  total: null,
  houseSheet: null,
  lineups: null,
  ...over,
});

describe("route mapping", () => {
  it("maps each competition to its own path", () => {
    expect(cupPath("FA Cup")).toBe("/fa-cup");
    expect(cupPath("League Cup")).toBe("/league-cup");
  });

  it("never puts the two cups on one path", () => {
    expect(cupPath("FA Cup")).not.toBe(cupPath("League Cup"));
  });

  it("builds a tie href under its own cup", () => {
    expect(cupHref(tie())).toBe("/fa-cup/arsenal-v-wrexham-fa-cup");
  });

  it("reads a competition back from a route segment", () => {
    expect(cupFromSlug("fa-cup")).toBe("FA Cup");
    expect(cupFromSlug("league-cup")).toBe("League Cup");
    expect(cupFromSlug("nonsense")).toBeNull();
  });
});

describe("house sheet gating", () => {
  it("shows picks for a Premier League tie that has them", () => {
    const t = tie({ kind: "full", houseSheet: { groups: [] } });
    expect(showsHouseSheet(t)).toBe(true);
  });

  it("hides picks on a cross-division tie even when the JSON carries them", () => {
    // Belt and braces against the publisher. No player-level foul data exists
    // for the second tier, so nothing player-shaped may render there.
    const t = tie({ kind: "total", houseSheet: { groups: [] } });
    expect(showsHouseSheet(t)).toBe(false);
  });

  it("hides picks on a full tie that simply has none yet", () => {
    expect(showsHouseSheet(tie({ kind: "full", houseSheet: null }))).toBe(false);
  });
});

describe("the sample line", () => {
  it("names how many matches and where they were played", () => {
    expect(sideNote(tie().record.home)).toContain("39 in the Premier League");
  });

  it("says plainly when there is nothing to go on", () => {
    const empty = { team: "X", matches: 0, spell: null, division: null, crossedDivisions: false };
    expect(sideNote(empty)).toBe("No matches on record");
  });
});

describe("the total headline", () => {
  it("reads as expected fouls", () => {
    const t = tie({ total: { expectedFouls: 21.4, lines: [], unpriced: [], crossDivision: true, note: "" } });
    expect(totalHeadline(t)).toBe("21 expected fouls");
  });

  it("is absent when no total was published", () => {
    expect(totalHeadline(tie())).toBeNull();
  });

  it("flags a club the model could not price at all", () => {
    const t = tie({
      total: { expectedFouls: 21.4, lines: [], unpriced: ["Wrexham"], crossDivision: true, note: "" },
    });
    expect(totalHeadline(t)).toContain("Wrexham");
  });
});
