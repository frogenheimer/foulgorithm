/**
 * The five's bets, per game: ordering and pricing rules the display leans
 * on. Games render in kickoff order because that is the order a reader
 * plans a weekend in; a game the board does not know sorts last rather
 * than crashing the page. A bet's price is the product of its own legs'
 * probabilities, and an empty bet has no price rather than a certain one.
 */

import { describe, expect, it } from "vitest";
import { betOutOf100, gameOrder } from "./bets";
import type { FixtureBoard, SlipLeg } from "./data";

function board(label: string, kickoff: string): FixtureBoard {
  const [home, away] = label.split(" v ");
  return { home, away, kickoff } as unknown as FixtureBoard;
}

const leg = (prob: number) => ({ prob } as unknown as SlipLeg);

describe("gameOrder", () => {
  it("orders games by kickoff, not alphabet", () => {
    const order = gameOrder(
      ["Arsenal v Coventry", "Palace v Wolves"],
      [
        board("Palace v Wolves", "2026-08-28T19:00:00Z"),
        board("Arsenal v Coventry", "2026-08-30T15:00:00Z"),
      ]
    );
    expect(order).toEqual(["Palace v Wolves", "Arsenal v Coventry"]);
  });

  it("sorts games the board does not know last, alphabetically", () => {
    const order = gameOrder(
      ["Z v Y", "A v B", "Arsenal v Coventry"],
      [board("Arsenal v Coventry", "2026-08-30T15:00:00Z")]
    );
    expect(order).toEqual(["Arsenal v Coventry", "A v B", "Z v Y"]);
  });
});

describe("betOutOf100", () => {
  it("is the product of the legs' own probabilities", () => {
    expect(betOutOf100([leg(0.5), leg(0.5)])).toBe(25);
  });

  it("an empty bet has no price rather than a certain one", () => {
    expect(betOutOf100([])).toBeNull();
  });
});
