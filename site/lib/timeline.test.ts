/**
 * The homepage card went on a diet, and the one rule that must survive any
 * future redesign is which face a card shows: a played game shows what
 * happened, an upcoming game may show the crossover, and a game under way
 * shows neither, because the picks bind at kickoff and a card advertising
 * them mid-match would be advertising something no longer on offer.
 */

import { describe, expect, it } from "vitest";
import { cardKind } from "./timeline";

describe("cardKind", () => {
  it("shows the result the moment there is one, whatever else exists", () => {
    expect(cardKind("past", true, true)).toBe("played");
    expect(cardKind("live", true, false)).toBe("played");
  });

  it("offers the crossover only before kickoff", () => {
    expect(cardKind("upcoming", false, true)).toBe("crossover");
    expect(cardKind("live", false, true)).toBe("quiet");
    expect(cardKind("past", false, true)).toBe("quiet");
  });

  it("stays quiet with nothing to say", () => {
    expect(cardKind("upcoming", false, false)).toBe("quiet");
  });
});
