/**
 * The league table once swapped itself for a note before the first round
 * settled, and its disappearance was reported as a bug. The rule that fixed
 * it: zeros are a state, not an absence. The table always renders; the only
 * thing a fresh season changes is the one-line note under it. That rule moved
 * home with the table (The five page to the track record), which is exactly
 * when it could have been lost, so it is pinned here.
 */

import { describe, expect, it } from "vitest";
import { anyPlayed } from "./standings";
import type { Standing } from "./data";

function standing(played: number): Standing {
  return {
    id: "alan",
    played,
    won: 0,
    drawn: 0,
    lost: 0,
    legsLanded: 0,
    legsMissed: 0,
    difference: 0,
    points: 0,
  } as Standing;
}

describe("anyPlayed", () => {
  it("says a fresh season has not started, so the note shows", () => {
    expect(anyPlayed([standing(0), standing(0)])).toBe(false);
  });

  it("drops the note the moment one slate settles", () => {
    expect(anyPlayed([standing(0), standing(1)])).toBe(true);
  });

  it("treats an empty table as unplayed rather than crashing", () => {
    expect(anyPlayed([])).toBe(false);
  });
});
