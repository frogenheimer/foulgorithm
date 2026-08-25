/**
 * Club badges are data, and the data must never crash a page.
 *
 * Every club in the league resolves to a kit colour pair and a short code;
 * a club we have never heard of (a cup visitor, a promotion) falls back to
 * a neutral badge with a code derived from its name rather than throwing.
 * Codes stay unique, because two clubs wearing the same three letters is a
 * lie in a table. The temper ring's arithmetic clamps, because a freak
 * fixture must bend the ring, never break the circle.
 */

import { describe, expect, it } from "vitest";
import { clubIdentity, temperFraction } from "./clubs";
import CLUBS from "./clubs.json";

describe("clubIdentity", () => {
  it("knows every club in the current league", () => {
    for (const name of Object.keys(CLUBS)) {
      if (name.startsWith("_")) continue;
      const c = clubIdentity(name);
      expect(c.code).toHaveLength(3);
      expect(c.primary).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it("codes are unique across the league", () => {
    const codes = Object.entries(CLUBS)
      .filter(([k]) => !k.startsWith("_"))
      .map(([, v]) => (v as { code: string }).code);
    expect(new Set(codes).size).toBe(codes.length);
  });

  it("an unknown club gets a neutral badge and a derived code, not a crash", () => {
    const c = clubIdentity("Wrexham");
    expect(c.code).toBe("WRE");
    expect(c.primary).toBe("#6b7075");
  });

  it("derives codes from the meaningful part of an awkward name", () => {
    expect(clubIdentity("St Albans City").code).toBe("STA");
  });
});

describe("temperFraction", () => {
  it("is the club's share of the hottest temper in the league", () => {
    expect(temperFraction(6, 12)).toBe(0.5);
  });

  it("clamps at the full circle and at nothing", () => {
    expect(temperFraction(99, 12)).toBe(1);
    expect(temperFraction(-1, 12)).toBe(0);
    expect(temperFraction(5, 0)).toBe(0);
  });
});
