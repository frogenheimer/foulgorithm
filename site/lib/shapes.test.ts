import { describe, expect, it } from "vitest";
import { shapesFor } from "./shapes";

const TIERS = [
  { key: "safe", label: "Safe", units: 4 },
  { key: "optimistic", label: "Optimistic", units: 5 },
  { key: "rogue", label: "Rogue", units: 6 },
];
const OLD_BETS = {
  alan: { "six-ones": { legs: [], label: "Six at 1+" }, "three-twos": { legs: [], label: "Three at 2+" } },
};

describe("shapesFor", () => {
  it("prefers the shapes the slice was published with", () => {
    const own = [{ key: "six-ones", label: "Six at 1+", legs: 6 }];
    expect(shapesFor(OLD_BETS, own, TIERS)).toBe(own);
  });

  it("reads old-shape bets off the bets when the payload has moved on", () => {
    expect(shapesFor(OLD_BETS, null, TIERS).map((s) => s.key)).toEqual(["six-ones", "three-twos"]);
    expect(shapesFor(OLD_BETS, null, TIERS)[0].label).toBe("Six at 1+");
  });

  it("uses the current shapes when the bets match them", () => {
    const bets = { alan: { safe: { legs: [], label: "Safe" } } };
    expect(shapesFor(bets, null, TIERS)).toBe(TIERS);
  });
});
