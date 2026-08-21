import fs from "node:fs";
import path from "node:path";

export type SeasonRow = {
  season: string;
  matches: number;
  foulsPerMatch: number;
  cardsPerMatch: number;
  stdev: number;
};

export type RefereeRow = {
  referee: string;
  matches: number;
  foulsPerMatch: number;
  cardsPerMatch: number;
  vsLeague: number;
};

export type TeamRow = {
  team: string;
  matches: number;
  committedPerMatch: number;
  drawnPerMatch: number;
};

export type Overview = {
  generatedAt: string;
  coverage: {
    seasons: number;
    matches: number;
    firstSeason: string;
    lastSeason: string;
  };
  headline: {
    foulsPerMatchNow: number;
    foulsPerMatchThen: number;
    changePct: number;
    meanAllTime: number;
    spanYears: number;
  };
  seasons: SeasonRow[];
  distribution: { fouls: number; matches: number; share: number }[];
  referees: RefereeRow[];
  teams: TeamRow[];
  homeAway: {
    homeFouls: number;
    awayFouls: number;
    homeYellows: number;
    awayYellows: number;
  };
  recentWindow: string;
};

/**
 * Read at build time. The site has no backend: Python computes everything and
 * writes this file. When the database lands, only this function changes.
 */
export function getOverview(): Overview {
  const file = path.join(process.cwd(), "public/data/overview.json");
  return JSON.parse(fs.readFileSync(file, "utf8")) as Overview;
}
