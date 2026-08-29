/**
 * The primitives registry, enforced (docs/41).
 *
 * Every role below has ONE implementation. A page that renders the role
 * must import it from that path, and no second component may take a name
 * that claims the role. The cup pages once grew a second pitch and lost the
 * position badges, the out-of-position ring and the bench values; this test
 * is what makes that a failing build rather than a review comment.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "..");

/** role -> the one file that implements it, relative to site/. */
const REGISTRY: Record<string, string> = {
  pitch: "components/fixture/Pitch.tsx",
  houseSheet: "components/fixture/HouseSheet.tsx",
  houseSlips: "components/fixture/HouseSlips.tsx",
  matchPlayers: "components/fixture/MatchPlayers.tsx",
  slipRail: "components/five/SlipRail.tsx",
  slipCard: "components/five/Bets.tsx",
  standings: "components/five/Standings.tsx",
  gameSheet: "components/matchday/GameSheet.tsx",
  dataTable: "components/kit/index.tsx",
  clubChip: "components/kit/ClubChip.tsx",
  contractCopy: "lib/contract.ts",
  bouncingShort: "components/kit/BouncingShort.tsx",
};

/** Filename fragments that claim a role. A new file matching one of these
 *  outside the registry is a fork, and forks drift. */
const CLAIMS: [RegExp, string][] = [
  [/Pitch/, "pitch"],
  [/HouseSheet|HousePicks/, "houseSheet"],
  [/Slip/, "slipRail"],
  [/Standings|LeagueTable/, "standings"],
  [/GameSheet|StatTable|SideBySide/, "gameSheet"],
  [/MatchPlayers|PlayerTable|SquadTable/, "matchPlayers"],
  [/ClubChip|Badge(?!\.)|Crest/, "clubChip"],
];

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(tsx|ts)$/.test(name) && !/\.test\./.test(name)) out.push(full);
  }
  return out;
}

describe("primitives", () => {
  it("every registered primitive exists", () => {
    for (const path of Object.values(REGISTRY)) {
      expect(() => statSync(join(ROOT, path)), path).not.toThrow();
    }
  });

  it("no second component claims a registered role", () => {
    const files = walk(join(ROOT, "components")).map((f) => f.slice(ROOT.length + 1));
    const registered = new Set(Object.values(REGISTRY));
    const forks = files.filter(
      (f) => !registered.has(f) && CLAIMS.some(([re]) => re.test(f.split("/").pop() ?? ""))
    );
    expect(forks, `forks of a primitive: ${forks.join(", ")}`).toEqual([]);
  });

  it("the contract copy is never written inline on a page", () => {
    const pages = walk(join(ROOT, "app")).filter((f) => f.endsWith("page.tsx"));
    const inline = pages.filter((f) => {
      const text = readFileSync(f, "utf8");
      return /six players at 1\+|fixed slates|all but one is a draw/.test(text);
    });
    expect(inline.map((f) => f.slice(ROOT.length + 1))).toEqual([]);
  });

  it("the methodology page reads the contract from lib/contract", () => {
    const text = readFileSync(join(ROOT, "app/methodology/page.tsx"), "utf8");
    expect(text).toMatch(/from "@\/lib\/contract"/);
  });
});
