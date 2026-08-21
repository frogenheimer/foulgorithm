/**
 * Typed reads of the JSON the Python pipeline writes.
 *
 * The site has no backend. When the database lands, only this file changes.
 */

import fs from "node:fs";
import path from "node:path";

/* ---------- historical overview ---------- */

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
  coverage: { seasons: number; matches: number; firstSeason: string; lastSeason: string };
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
  homeAway: { homeFouls: number; awayFouls: number; homeYellows: number; awayYellows: number };
  recentWindow: string;
};

/* ---------- this round's predictions ---------- */

export type LinePrice = {
  line: number;
  probOver: number;
  fairOddsOver: number;
  fairOddsUnder: number;
};

export type FixturePrediction = {
  kickoff: string;
  home: string;
  away: string;
  referee: string | null;
  expectedFouls: number;
  lines: LinePrice[];
  pmf: number[];
  pmfFrom: number;
  thinEvidence: string[];
  effectiveMatches: { home: number; away: number; referee: number };
};

export type Round = {
  generatedAt: string;
  model: { id: string; version: string; config: Record<string, number> };
  market: string;
  trainedOn: { matches: number; firstSeason: string; lastSeason: string };
  fixtures: FixturePrediction[];
};

function read<T>(file: string): T {
  return JSON.parse(
    fs.readFileSync(path.join(process.cwd(), "public/data", file), "utf8")
  ) as T;
}

export const getOverview = () => read<Overview>("overview.json");
export const getRound = () => read<Round>("round.json");

/* ---------- the five characters ---------- */

export type CharacterLine = {
  line: number;
  probOver: number;
  fairOddsOver: number;
};

export type CharacterFixture = {
  key: string;
  home: string;
  away: string;
  kickoff: string;
  referee: string | null;
  expectedFouls: number;
  lines: CharacterLine[];
  pmf: number[];
  pmfFrom: number;
};

export type CharacterBlock = {
  id: string;
  name: string;
  emotion: string;
  tagline: string;
  philosophy: string;
  onLosing: string;
  weakness: string;
  edge: string;
  model: { id: string; version: string; config: Record<string, number> };
  fixtures: CharacterFixture[];
};

export type Disagreement = {
  key: string;
  home: string;
  away: string;
  kickoff: string;
  referee: string | null;
  means: Record<string, number>;
  consensus: number;
  spread: number;
  highest: string;
  lowest: string;
  boldest: string;
};

export type CharactersData = {
  generatedAt: string;
  market: string;
  trainedOn: { matches: number; firstSeason: string; lastSeason: string };
  characters: CharacterBlock[];
  disagreement: Disagreement[];
};

export const getCharacters = () => read<CharactersData>("characters.json");
