/**
 * Ordering and pricing for the five's per-game bets (docs/38).
 *
 * Games render in kickoff order, the order a reader plans a weekend in;
 * slate legs carry no kickoff of their own, so the board supplies it, and a
 * game the board does not know sorts after the known ones, alphabetically.
 */

import type { FixtureBoard, SlipLeg } from "./data";

export function gameOrder(labels: string[], board: FixtureBoard[]): string[] {
  const kickoff = new Map(board.map((f) => [`${f.home} v ${f.away}`, f.kickoff]));
  return [...labels].sort((a, b) => {
    const ka = kickoff.get(a);
    const kb = kickoff.get(b);
    if (ka && kb && ka !== kb) return ka < kb ? -1 : 1;
    if (ka && !kb) return -1;
    if (!ka && kb) return 1;
    return a.localeCompare(b);
  });
}

/** A bet's price out of 100: the product of its own legs' probabilities. */
export function betOutOf100(legs: SlipLeg[]): number | null {
  if (!legs.length) return null;
  return Math.round(legs.reduce((p, l) => p * l.prob, 1) * 100);
}
