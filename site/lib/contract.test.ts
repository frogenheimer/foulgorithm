import { describe, expect, it } from "vitest";
import { contractCopy } from "./contract";

const PRICED = [{ key: "banker", label: "Banker", target: 0.15 }];
const SHAPES = [{ key: "six-ones", label: "Six at 1+", legs: 6 }];

describe("the contract, said once", () => {
  it("reads the era off the shapes", () => {
    expect(contractCopy(SHAPES).priced).toBe(false);
    expect(contractCopy(PRICED).priced).toBe(true);
  });

  it("describes the priced bands and the fouls-based draw from matchweek 3", () => {
    const c = contractCopy(PRICED);
    expect(c.bets).toMatch(/banker/);
    expect(c.scoring).toMatch(/one foul short/);
  });

  it("describes the shapes and the leg-based draw before", () => {
    const c = contractCopy(SHAPES);
    expect(c.bets).toMatch(/six players at 1\+/);
    expect(c.scoring).toMatch(/all but one/);
  });

  it("always speaks of the eleven, never the five", () => {
    expect(contractCopy(PRICED).bets).not.toMatch(/\bfive\b/);
    expect(contractCopy(SHAPES).bets).not.toMatch(/\bfive\b/);
  });
});
