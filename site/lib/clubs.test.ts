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
import { clubIdentity, rankFraction, temperFraction } from "./clubs";
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
    // Salford are League Two. Wrexham used to be the example and can no
    // longer be: they are in the Championship, which the cup pages hold.
    const c = clubIdentity("Salford");
    expect(c.code).toBe("SAL");
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

describe("rankFraction", () => {
  it("first place fills the ring, last barely marks it", () => {
    expect(rankFraction(1, 20)).toBe(1);
    expect(rankFraction(20, 20)).toBeCloseTo(0.05);
  });

  it("nonsense ranks fill nothing", () => {
    expect(rankFraction(0, 20)).toBe(0);
    expect(rankFraction(3, 0)).toBe(0);
  });
});

describe("Championship clubs", () => {
  it("every club in the second tier has a real badge, not the fallback", () => {
    // Twenty-four grey badges would look broken on an FA Cup page. The set
    // mirrors identity/teams.py CHAMPIONSHIP_CLUBS.
    const CHAMPIONSHIP = [
      "Birmingham", "Blackburn", "Bolton", "Bristol City", "Burnley", "Cardiff",
      "Charlton", "Derby", "Lincoln", "Middlesbrough", "Millwall", "Norwich",
      "Portsmouth", "Preston", "QPR", "Sheffield United", "Southampton",
      "Stoke", "Swansea", "Watford", "West Brom", "West Ham", "Wolves", "Wrexham",
    ];
    // The derived-code fallback also returns three letters, so checking the
    // code proves nothing. The neutral grey is what gives a fallback away.
    const fallback = clubIdentity("Nowhere United").primary;
    for (const club of CHAMPIONSHIP) {
      const id = clubIdentity(club);
      expect(id.primary, `${club} fell back to the neutral badge`).not.toBe(fallback);
    }
  });

  it("still falls back safely for a club we hold nothing for", () => {
    // Salford in a third-round draw. Never a crash.
    const id = clubIdentity("Salford");
    expect(id.code).toBe("SAL");
  });
});
