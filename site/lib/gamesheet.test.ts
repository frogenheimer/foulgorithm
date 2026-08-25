/**
 * The structured game sheet: team facts face to face, then the players who
 * will actually be on the pitch. The rules worth pinning: the eleven most
 * likely to play lead and the rest wait in the drawer (confirmed starters
 * always outrank probabilities); the mirrored bars split by share so the
 * longer record always reads longer; and a club with no data mirrors to
 * nothing rather than a full bar.
 */

import { describe, expect, it } from "vitest";
import { mirrorShares, xiSplit } from "./gamesheet";
import type { ExplorerRow } from "./data";

function row(player: string, team: string, start: number | null, confirmed = false, minutes = 80): ExplorerRow {
  return { player, fullName: `${player} F`, team, startProbability: start, confirmed, minutes } as unknown as ExplorerRow;
}

describe("xiSplit", () => {
  it("puts the likely eleven first and the rest in the drawer", () => {
    const rows = [
      ...Array.from({ length: 14 }, (_, i) => row(`A${i}`, "X", 0.9 - i * 0.05)),
    ];
    const { eleven, drawer } = xiSplit(rows);
    expect(eleven).toHaveLength(11);
    expect(drawer).toHaveLength(3);
    expect(eleven[0].player).toBe("A0");
  });

  it("a confirmed starter outranks any probability", () => {
    const rows = [
      row("Sub", "X", 0.95),
      ...Array.from({ length: 11 }, (_, i) => row(`S${i}`, "X", 0.5, true)),
    ];
    const { eleven, drawer } = xiSplit(rows);
    expect(drawer.map((r) => r.player)).toContain("Sub");
    expect(eleven.every((r) => r.confirmed)).toBe(true);
  });

  it("copes with fewer than eleven rows", () => {
    const { eleven, drawer } = xiSplit([row("A", "X", 0.9)]);
    expect(eleven).toHaveLength(1);
    expect(drawer).toHaveLength(0);
  });
});

describe("mirrorShares", () => {
  it("splits by share of the pair", () => {
    expect(mirrorShares(6, 12)).toEqual([33, 67]);
  });

  it("nothing mirrors to nothing, not a full bar", () => {
    expect(mirrorShares(null, 8)).toEqual([0, 100]);
    expect(mirrorShares(null, null)).toEqual([0, 0]);
  });
});
