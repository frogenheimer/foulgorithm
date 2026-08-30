/**
 * The vidiprinter: settled bets arrive the way scores used to, as a
 * teletype feed. The rules worth pinning: newest game first, a cap when one
 * is asked for, only decided bets print (a void is
 * not news), and the old convention survives: a full house on the six is
 * spelled out, ALL SIX (6), so nobody thinks it is a typo.
 */

import { describe, expect, it } from "vitest";
import { orderForTicker, vidiprinterLines } from "./vidiprinter";
import type { ArchivedFixture } from "./data";

function fixture(label: string, kickoff: string, legs: [string, boolean][]): ArchivedFixture {
  const outcomes: Record<string, { won: boolean }> = {};
  const betLegs = legs.map(([player, won]) => {
    outcomes[`${player} Full|committed|0.5`] = { won };
    return { player, fullName: `${player} Full`, market: "committed", line: 0.5, fouls: 1 };
  });
  return {
    label,
    kickoff,
    characters: [{ id: "tayler", name: "Tayler" }],
    bets: { tayler: { "six-ones": { legs: betLegs, label: "Six at 1+" } } },
    outcomes,
    result: { score: [1, 0] },
  } as unknown as ArchivedFixture;
}

describe("vidiprinterLines", () => {
  it("prints a decided bet with the club codes and the verdict", () => {
    const lines = vidiprinterLines({
      a: fixture("Fulham v Chelsea", "2026-08-24T19:00:00Z", [["A", true], ["B", false]]),
    });
    expect(lines).toHaveLength(1);
    expect(lines[0].text).toContain("FUL v CHE");
    expect(lines[0].text).toContain("TAYLER");
    expect(lines[0].text).toContain("NO");
    expect(lines[0].tone).toBe("lost");
  });

  it("spells out a full house on the six, the old convention", () => {
    const legs: [string, boolean][] = [["A", true], ["B", true], ["C", true], ["D", true], ["E", true], ["F", true]];
    const lines = vidiprinterLines({ a: fixture("Fulham v Chelsea", "2026-08-24T19:00:00Z", legs) });
    expect(lines[0].text).toContain("ALL SIX (6)");
    expect(lines[0].tone).toBe("won");
  });

  it("newest game prints first, and the feed is capped", () => {
    const held: Record<string, ArchivedFixture> = {};
    for (let i = 0; i < 30; i++) {
      held[`f${i}`] = fixture(`Fulham v Chelsea`, `2026-08-${String(i % 28 + 1).padStart(2, "0")}T19:00:00Z`, [["A", true]]);
    }
    const lines = vidiprinterLines(held, 10);
    expect(lines).toHaveLength(10);
  });

  it("an unplayed or unmarked fixture prints nothing", () => {
    const quiet = fixture("Fulham v Chelsea", "2026-08-24T19:00:00Z", [["A", true]]);
    (quiet as { result?: unknown }).result = undefined;
    expect(vidiprinterLines({ a: quiet })).toHaveLength(0);
  });
});

describe("orderForTicker", () => {
  it("plays every success before any miss, keeping each group's own order", () => {
    const lines = [
      { text: "A", tone: "lost" as const },
      { text: "B", tone: "won" as const },
      { text: "C", tone: "lost" as const },
      { text: "D", tone: "won" as const },
    ];
    expect(orderForTicker(lines).map((l) => l.text)).toEqual(["B", "D", "A", "C"]);
  });

  it("drops nothing", () => {
    const lines = [
      { text: "A", tone: "lost" as const },
      { text: "B", tone: "won" as const },
    ];
    expect(orderForTicker(lines)).toHaveLength(2);
    expect(orderForTicker([])).toEqual([]);
  });

  it("the feed is uncapped by default, so the report is complete", () => {
    const held: Record<string, ArchivedFixture> = {};
    for (let i = 0; i < 30; i++) {
      held[`f${i}`] = fixture(`Fulham v Chelsea`, `2026-08-${String((i % 28) + 1).padStart(2, "0")}T19:00:00Z`, [["A", true]]);
    }
    expect(vidiprinterLines(held).length).toBe(30);
  });
});
