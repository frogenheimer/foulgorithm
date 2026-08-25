/**
 * A played fixture's ladder is marked against what happened, and the marking
 * follows betting arithmetic, not optimism: one lost leg kills a slip even
 * while other legs are open, a slip only "came in" when every leg landed,
 * and a leg the grading never reached stays open rather than counting
 * either way. Outcome keys join on the full name, market and line, exactly
 * as the archive writes them.
 */

import { describe, expect, it } from "vitest";
import { betVerdict, legKey, legMark, slipVerdict } from "./graded";
import type { Slip, SlipLeg } from "./data";

function leg(fullName: string, line = 0.5, market = "committed"): SlipLeg {
  return { player: fullName.split(" ").slice(-1)[0], fullName, market, line, fouls: line + 0.5 } as unknown as SlipLeg;
}

function slip(...legs: SlipLeg[]): Slip {
  return { legs } as unknown as Slip;
}

const OUTCOMES = {
  "Sander Berge|committed|0.5": { won: false, observed: 0 },
  "Kevin Schade|committed|0.5": { won: true, observed: 2 },
};

describe("legMark", () => {
  it("joins on full name, market and line", () => {
    expect(legKey(leg("Sander Berge"))).toBe("Sander Berge|committed|0.5");
    expect(legMark(leg("Sander Berge"), OUTCOMES)).toBe(false);
    expect(legMark(leg("Kevin Schade"), OUTCOMES)).toBe(true);
  });

  it("leaves an ungraded leg open rather than guessing", () => {
    expect(legMark(leg("Nobody Here"), OUTCOMES)).toBeNull();
    expect(legMark(leg("Kevin Schade"), undefined)).toBeNull();
  });
});

describe("slipVerdict", () => {
  it("came in only when every leg landed", () => {
    expect(slipVerdict(slip(leg("Kevin Schade")), OUTCOMES)).toBe("came in");
  });

  it("one lost leg kills the slip even while others are open", () => {
    expect(
      slipVerdict(slip(leg("Sander Berge"), leg("Nobody Here")), OUTCOMES)
    ).toBe("no");
  });

  it("stays open while any leg is ungraded and none has lost", () => {
    expect(
      slipVerdict(slip(leg("Kevin Schade"), leg("Nobody Here")), OUTCOMES)
    ).toBe("open");
  });
});

describe("betVerdict", () => {
  it("voids an ungraded leg once the game is over, and settles on the rest", () => {
    expect(betVerdict([leg("Kevin Schade"), leg("Nobody Here")], OUTCOMES, true)).toBe(
      "came in"
    );
    expect(betVerdict([leg("Sander Berge"), leg("Nobody Here")], OUTCOMES, true)).toBe(
      "no"
    );
  });

  it("a bet whose every leg voids is void, not a win", () => {
    expect(betVerdict([leg("Nobody Here")], OUTCOMES, true)).toBe("void");
  });

  it("keeps a bet open before the game is over", () => {
    expect(betVerdict([leg("Kevin Schade"), leg("Nobody Here")], OUTCOMES, false)).toBe(
      "open"
    );
  });
});
