/**
 * Zeros are a state, not an absence.
 *
 * The league table renders whether or not anything has settled; the only
 * thing a fresh season changes is the one-line note under it. This predicate
 * decides the note, never the table.
 */

import type { Standing } from "./data";

export function anyPlayed(standings: Standing[]): boolean {
  return standings.some((r) => r.played > 0);
}
