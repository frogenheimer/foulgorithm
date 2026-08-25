/**
 * Club identity as data: kit colour pairs and short codes, for the badges.
 *
 * Kit colours are facts about kits, never crest artwork; see docs/39 for why
 * the badges are generic. An unknown club falls back to a neutral badge with
 * a code derived from its name, so a cup visitor or a promotion never
 * crashes a page.
 */

import CLUBS from "./clubs.json";

export type ClubIdentity = {
  code: string;
  primary: string;
  secondary: string;
  ink: string;
};

const TABLE = CLUBS as unknown as Record<string, ClubIdentity>;

export function clubIdentity(name: string): ClubIdentity {
  const held = TABLE[name];
  if (held && !name.startsWith("_")) return held;
  return { ...TABLE._default, code: derivedCode(name) };
}

function derivedCode(name: string): string {
  const letters = name.toUpperCase().replace(/[^A-Z]/g, "");
  return (letters + "XXX").slice(0, 3);
}

/** The temper ring: this club's share of the hottest fouls-per-match rate. */
export function temperFraction(value: number, leagueMax: number): number {
  if (!leagueMax || leagueMax <= 0) return 0;
  return Math.min(Math.max(value / leagueMax, 0), 1);
}

/** Ring fill from a league rank when no scale is at hand: 1st fills fully. */
export function rankFraction(rank: number, of: number): number {
  if (!of || of <= 0 || !rank || rank <= 0) return 0;
  return Math.min(Math.max((of - rank + 1) / of, 0), 1);
}
