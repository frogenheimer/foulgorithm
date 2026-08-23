/**
 * Rebuild a character's combination from whoever is actually on the pitch.
 *
 * A port of `_slip_at_odds` in the Python pipeline, and it has to stay a port:
 * if the two ever disagree, the site shows one thing and grades another.
 *
 * It works client-side because everything a swap changes is already shipped.
 * Within one fixture the opponent and head-to-head factors are fixed, so each
 * player carries a settled probability per market, line and model. Swapping a
 * player swaps his contribution and nothing else, which is why this is a
 * recalculation rather than a request.
 */

import type { ExplorerRow, Slip, SlipLeg } from "@/lib/data";

/** Matches MAX_LEGS_PER_TIER in the pipeline. */
const MAX_LEGS = 6;
/** Matches PROP_MARGIN in foulgorithm.markets.odds. */
const MARGIN = 0.15;
const EDGE = 0.1;

export type Candidate = {
  player: string;
  fullName: string;
  team: string;
  market: "committed" | "drawn";
  line: number;
  probs: number[];
  thin: boolean;
};

/** Every leg available from the players currently selected. */
export function candidatesFor(
  rows: ExplorerRow[],
  lines: number[],
  onPitch: Set<string>
): Candidate[] {
  const out: Candidate[] = [];
  for (const r of rows) {
    if (!onPitch.has(r.player)) continue;
    for (const market of ["committed", "drawn"] as const) {
      r[market].forEach((probs, i) => {
        // The pipeline drops anything nobody rates and anything everybody does:
        // a 3% leg is noise and a 98% leg adds no price.
        if (Math.max(...probs) < 0.12 || Math.min(...probs) > 0.97) return;
        out.push({
          player: r.player,
          fullName: r.fullName,
          team: r.team,
          market,
          line: lines[i],
          probs,
          thin: r.thin,
        });
      });
    }
  }
  return out;
}

/**
 * One character's best combination landing near a target price.
 *
 * Legs are added in that character's preference order until the combined
 * probability reaches 1/target. The leg COUNT is free, which is what makes the
 * tiers comparable: reaching 21.0 takes more legs or bolder ones, and each
 * character gets there its own way.
 */
export function slipAtOdds(
  candidates: Candidate[],
  modelIndex: number,
  target: number,
  targetLabel: string
): Slip | null {
  const wanted = 1 / target;
  const ranked = [...candidates].sort(
    (a, b) => preference(b, modelIndex) - preference(a, modelIndex)
  );

  const chosen: Candidate[] = [];
  const seen = new Set<string>();
  let combined = 1;

  for (const row of ranked) {
    if (chosen.length >= MAX_LEGS) break;
    if (seen.has(row.player)) continue;
    const after = combined * row.probs[modelIndex];
    // Stop before overshooting: a slip priced longer than asked for is not the
    // tier it claims to be.
    if (after < wanted * 0.75 && chosen.length) continue;
    chosen.push(row);
    seen.add(row.player);
    combined = after;
    if (combined <= wanted) break;
  }

  if (!chosen.length || combined > wanted * 1.6) return null;

  const fair = 1 / combined;
  const legs = chosen.length;
  return {
    target,
    targetLabel,
    actualOdds: round(fair, 2),
    probability: round(combined, 4),
    outOf100: Math.round(combined * 100),
    estimatedOffer: round(fair / Math.pow(1 + MARGIN, legs), 2),
    legCount: legs,
    takeOut: round(1 - 1 / Math.pow(1 + MARGIN, legs), 3),
    floor: round(fair * (1 + EDGE), 2),
    legs: chosen.map((c): SlipLeg => {
      const others = c.probs.filter((_, i) => i !== modelIndex);
      const pack = others.reduce((a, b) => a + b, 0) / others.length;
      return {
        player: c.player,
        fullName: c.fullName,
        team: c.team,
        fixture: "",
        market: c.market,
        line: c.line,
        fouls: Math.round(c.line + 0.5),
        prob: round(c.probs[modelIndex], 4),
        outOf100: Math.round(c.probs[modelIndex] * 100),
        packProb: round(pack, 4),
        edge: round(c.probs[modelIndex] - pack, 4),
        band: "",
        thin: c.thin,
      };
    }),
  };
}

/**
 * How much a character wants a leg.
 *
 * Distance from the pack, so a character reaches for what it alone believes
 * rather than for whatever is most likely. Agreement is not an opinion.
 */
function preference(c: Candidate, modelIndex: number): number {
  const p = c.probs[modelIndex];
  const others = c.probs.filter((_, i) => i !== modelIndex);
  const pack = others.reduce((a, b) => a + b, 0) / others.length;
  return p - pack + p * 0.1;
}

const round = (n: number, dp: number) => Number(n.toFixed(dp));
