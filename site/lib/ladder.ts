/**
 * The swap-and-rebuild contract, out where it can be tested.
 *
 * The ladder shows what the pipeline published until a reader changes a slot
 * on the pitch; from the first change it is rebuilt, client-side, from whoever
 * is now standing on both pitches. The rebuild itself is rebuild.ts (a port of
 * the pipeline's `_slip_at_odds` that has to stay a port); this file owns the
 * orchestration around it: which rows, which players, published or rebuilt.
 */

import type { Explorer, ExplorerRow, Formations, Slip } from "./data";
import { findPlayer, who } from "./who";
import { candidatesFor, slipAtOdds } from "../components/fixture/rebuild";

/** target odds and the label a slip carries for reaching them. */
export const TIERS: [number, string][] = [
  [3, "2/1"],
  [4, "3/1"],
  [6, "5/1"],
  [11, "10/1"],
  [21, "20/1"],
];

/** Both clubs' rows for one fixture, keyed by club. */
export function squadsFor(
  explorer: Explorer,
  fixture: string,
  clubs: string[]
): Record<string, ExplorerRow[]> {
  const out: Record<string, ExplorerRow[]> = {};
  for (const club of clubs) {
    out[club] = explorer.rows.filter((r) => r.fixture === fixture && r.team === club);
  }
  return out;
}

/** Who is on the pitch right now: the published eleven with any swaps applied. */
export function onPitchFrom(
  shapes: Formations[string],
  clubs: string[],
  selected: Record<string, string>,
  squads: Record<string, ExplorerRow[]>
): Set<string> {
  const names = new Set<string>();
  for (const club of clubs) {
    shapes[club]?.lines.forEach((line, i) =>
      line.forEach((spot, j) => {
        // Slots hold a canonical key once swapped and a lineup-feed name
        // before that. Both resolve to the same row, and the candidate list
        // keys on that row's own short name.
        const chosen = selected[`${club}|${i}|${j}`];
        const row = chosen
          ? (squads[club] ?? []).find((r) => who(r.fullName) === chosen)
          : findPlayer(squads[club] ?? [], spot.player);
        if (row) names.add(row.player);
      })
    );
  }
  return names;
}

/**
 * The ladder to show: the published one, verbatim, until a reader changes
 * something; rebuilt from the players on the pitches after that. A model that
 * cannot fill a single tier from the chosen eleven drops out rather than
 * showing an empty column.
 */
export function ladderFor(
  explorer: Explorer,
  fixture: string,
  onPitch: Set<string>,
  changed: boolean,
  published: Record<string, Slip[]>
): Record<string, Slip[]> {
  if (!changed) return published;
  const rows = explorer.rows.filter((r) => r.fixture === fixture);
  const candidates = candidatesFor(rows, explorer.lines, onPitch);
  const out: Record<string, Slip[]> = {};
  explorer.models.forEach((model, i) => {
    const ladder = TIERS.map(([t, label]) => slipAtOdds(candidates, i, t, label)).filter(
      (x): x is Slip => x !== null
    );
    if (ladder.length) out[model] = ladder;
  });
  return out;
}
