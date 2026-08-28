/**
 * The match players table's rules, out where they can be tested (docs/46).
 *
 * Who is in the eleven (predicted until the sheets land, confirmed after),
 * which house slip a player sits on, what he actually did once the game is
 * played, and how each column sorts.
 */

import type { Bet, ExplorerRow, Formations } from "./data";
import type { Outcomes } from "./graded";
import { findPlayer, who } from "./who";

export type MatchRow = {
  r: ExplorerRow;
  xi: boolean;
  /** The house slip (safe / optimistic / rogue) whose legs include him, if any. */
  tier: string | null;
  actualFouls: number | null;
  actualFouled: number | null;
};

/** The eleven a side, by canonical name, and whether the sheets are confirmed. */
export function elevenOf(
  rows: ExplorerRow[],
  shapes: Formations[string] | undefined
): { names: Set<string>; confirmed: boolean } {
  const names = new Set<string>();
  let confirmed = false;
  for (const [club, shape] of Object.entries(shapes ?? {})) {
    if (!shape) continue;
    if (shape.predicted === false) confirmed = true;
    const squad = rows.filter((r) => r.team === club);
    for (const spot of shape.lines.flat()) {
      const row = findPlayer(squad, spot.player);
      if (row) names.add(who(row.fullName));
    }
  }
  return { names, confirmed };
}

const TIER_ORDER = ["safe", "optimistic", "rogue"];

/** fullName key -> the safest house slip the player appears on. */
export function houseTiers(slips: Record<string, Bet> | null | undefined): Map<string, string> {
  const out = new Map<string, string>();
  for (const key of TIER_ORDER) {
    const bet = slips?.[key];
    if (!bet) continue;
    for (const leg of bet.legs) {
      const name = who(leg.fullName ?? leg.player);
      if (!out.has(name)) out.set(name, key);
    }
  }
  return out;
}

function observed(outcomes: Outcomes | undefined, row: ExplorerRow, market: string): number | null {
  const held = outcomes?.[`${row.fullName}|${market}|0.5`];
  return held?.observed ?? null;
}

export function buildRows(
  rows: ExplorerRow[],
  shapes: Formations[string] | undefined,
  slips: Record<string, Bet> | null | undefined,
  outcomes?: Outcomes
): { rows: MatchRow[]; confirmed: boolean } {
  const { names, confirmed } = elevenOf(rows, shapes);
  const tiers = houseTiers(slips);
  return {
    confirmed,
    rows: rows.map((r) => ({
      r,
      xi: names.has(who(r.fullName)),
      tier: tiers.get(who(r.fullName)) ?? null,
      actualFouls: observed(outcomes, r, "committed"),
      actualFouled: observed(outcomes, r, "drawn"),
    })),
  };
}

export type SortKey =
  | "player"
  | "xi"
  | "mins"
  | "fouls"
  | "fouled"
  | "involvements"
  | "actualFouls"
  | "actualFouled"
  | "house";

const num = (v: number | null | undefined) => (v == null ? -1 : v);

export function compare(key: SortKey): (a: MatchRow, b: MatchRow) => number {
  switch (key) {
    case "player":
      return (a, b) => a.r.player.localeCompare(b.r.player);
    case "xi":
      return (a, b) => Number(b.xi) - Number(a.xi);
    case "mins":
      return (a, b) => num(b.r.minutes) - num(a.r.minutes);
    case "fouls":
      return (a, b) => num((b.r.expected?.committed ?? null)) - num((a.r.expected?.committed ?? null));
    case "fouled":
      return (a, b) => num((b.r.expected?.drawn ?? null)) - num((a.r.expected?.drawn ?? null));
    case "involvements":
      return (a, b) => num((b.r.expected?.involvements ?? null)) - num((a.r.expected?.involvements ?? null));
    case "actualFouls":
      return (a, b) => num(b.actualFouls) - num(a.actualFouls);
    case "actualFouled":
      return (a, b) => num(b.actualFouled) - num(a.actualFouled);
    case "house":
      return (a, b) =>
        (a.tier ? TIER_ORDER.indexOf(a.tier) : 9) - (b.tier ? TIER_ORDER.indexOf(b.tier) : 9);
  }
}

/** Per-90 from a player's record, or null when he has none. */
export function per90(r: ExplorerRow, market: "committed" | "drawn" | "involvements"): number | null {
  return r.career?.[market] ?? null;
}
