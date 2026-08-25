/**
 * Derivations for the structured game sheet, held out of the component so
 * the display can change without touching who counts as the likely eleven.
 */

import type { ExplorerRow } from "./data";

/** The eleven most likely to play lead; the rest wait in the drawer.
 *  Confirmed starters always outrank probabilities. */
export function xiSplit(rows: ExplorerRow[]): { eleven: ExplorerRow[]; drawer: ExplorerRow[] } {
  const ranked = [...rows].sort((a, b) => {
    if (a.confirmed !== b.confirmed) return a.confirmed ? -1 : 1;
    const pa = a.startProbability ?? 0;
    const pb = b.startProbability ?? 0;
    if (pa !== pb) return pb - pa;
    return (b.minutes ?? 0) - (a.minutes ?? 0);
  });
  return { eleven: ranked.slice(0, 11), drawer: ranked.slice(11) };
}

/** Widths for a mirrored bar pair, as integer percent shares of their sum. */
export function mirrorShares(a: number | null, b: number | null): [number, number] {
  const va = a ?? 0;
  const vb = b ?? 0;
  const total = va + vb;
  if (total <= 0) return [0, 0];
  const left = Math.round((va / total) * 100);
  return [left, 100 - left];
}
