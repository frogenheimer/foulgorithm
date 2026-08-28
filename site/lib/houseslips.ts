/**
 * The house's three slips, rebuilt client-side from whoever is on the pitch.
 *
 * A PORT of league.house_slips and its recipes (publish/league.py), and it
 * has to stay one: safe is four 1+ calls, optimistic leads with a 2+, rogue
 * with a 3+ where a player clears the floor, else two 2+ legs; each slot is
 * filled with the best-priced unused player at that line by the house's own
 * number; 3+ only on rogue and only above 20/100 (docs/45).
 *
 * The published slips show until a reader swaps someone on the pitch; from
 * then on these recompute from the elevens now standing there, which is how
 * an astute reader extracts the house's picks from a lineup they think
 * likelier than ours.
 */

import { who } from "./who";
import type { Bet, Explorer, ExplorerRow, SlipLeg } from "./data";

const RECIPES: Record<string, number[][]> = {
  safe: [[1, 1, 1, 1]],
  optimistic: [[2, 1, 1, 1]],
  rogue: [
    [3, 2, 1],
    [2, 2, 1, 1],
  ],
};
const LABELS: Record<string, string> = { safe: "Safe", optimistic: "Optimistic", rogue: "Rogue" };
const UNITS: Record<string, number> = { safe: 4, optimistic: 5, rogue: 6 };
const ROGUE_3PLUS_FLOOR = 0.2;

type Candidate = { row: ExplorerRow; market: "committed" | "drawn"; events: number; p: number };

function candidates(explorer: Explorer, fixture: string, onPitch: Set<string>): Candidate[] {
  const houseIdx = explorer.models.indexOf(explorer.house);
  const out: Candidate[] = [];
  for (const row of explorer.rows) {
    if (row.fixture !== fixture || !onPitch.has(who(row.fullName))) continue;
    for (const market of ["committed", "drawn"] as const) {
      for (const events of [1, 2, 3]) {
        const li = explorer.lines.indexOf(events - 0.5);
        const p = li >= 0 ? row[market]?.[li]?.[houseIdx] : undefined;
        if (p != null && p > 0) out.push({ row, market, events, p });
      }
    }
  }
  return out;
}

function admissible(c: Candidate, tier: string): boolean {
  if (c.events < 3) return true;
  return tier === "rogue" && c.p >= ROGUE_3PLUS_FLOOR;
}

function leg(c: Candidate): SlipLeg {
  const p = Math.round(c.p * 10000) / 10000;
  return {
    player: c.row.player,
    fullName: c.row.fullName,
    team: c.row.team,
    fixture: c.row.fixture,
    kickoff: c.row.kickoff,
    market: c.market,
    line: c.events - 0.5,
    fouls: c.events,
    prob: p,
    outOf100: Math.round(c.p * 100),
    packProb: p,
    edge: 0,
    band: "",
    thin: Boolean(c.row.thin),
    houseProb: p,
  } as SlipLeg;
}

function recipeSlip(pool: Candidate[], tier: string, recipe: number[]): Bet {
  const chosen: Candidate[] = [];
  const used = new Set<string>();
  for (const events of recipe) {
    const pick = pool
      .filter((c) => c.events === events && admissible(c, tier) && !used.has(c.row.fullName))
      .sort((a, b) => b.p - a.p)[0];
    if (!pick) return null;
    chosen.push(pick);
    used.add(pick.row.fullName);
  }
  const legs = chosen.map(leg);
  return {
    legs,
    label: LABELS[tier],
    tier,
    units: UNITS[tier],
    housePrice: Math.round(legs.reduce((p, l) => p * (l.houseProb ?? 1), 1) * 10000) / 10000,
  };
}

export function houseSlipsFrom(
  explorer: Explorer,
  fixture: string,
  onPitch: Set<string>
): Record<string, Bet> {
  const pool = candidates(explorer, fixture, onPitch);
  const out: Record<string, Bet> = {};
  for (const tier of Object.keys(RECIPES)) {
    out[tier] = null;
    for (const recipe of RECIPES[tier]) {
      const slip = recipeSlip(pool, tier, recipe);
      if (slip) {
        out[tier] = slip;
        break;
      }
    }
  }
  return out;
}
