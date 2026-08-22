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

/* ---------- players ---------- */

export type MarketBlock = {
  why: {
    ratePer90: number;
    expectedMinutes: number;
    opponentFactor: number;
    refereeFactor: number;
    effectiveMatches: number;
  };
  exact0: number;
  p1plus: number; p2plus: number; p3plus: number;
  fair1: number | null; fair2: number | null; fair3: number | null;
  floor1: number | null; floor2: number | null; floor3: number | null;
  band1: string; band2: string; band3: string;
  outOf100: number;
};

export type PlayerRow = {
  player: string; fullName?: string; position?: string; hasHistory?: boolean;
  team: string; opponent: string; fixture: string; kickoff: string;
  expectedMinutes: number; effectiveMatches: number; thin: boolean;
  committed: MarketBlock; drawn: MarketBlock;
};

export type Pick = {
  player: string; team: string; fixture: string; kickoff: string;
  market: "committed" | "drawn"; line: number; prob: number; band: string;
  outOf100: number; fair: number; floor: number; thin: boolean;
  packProb: number; edge: number; position?: string;
  why: MarketBlock["why"];
};

export type CharacterPicks = {
  id: string; name: string; emotion: string; tagline: string;
  settings: Record<string, number>;
  picks: Pick[];
  combinedProb: number; combinedFair: number | null; averageProb: number;
  averageEdge: number; inBand: boolean;
};

export type FixtureBoard = {
  key: string; home: string; away: string; kickoff: string; referee: string | null;
  teams: Record<string, PlayerRow[]>;
};

export type PlayersData = {
  generatedAt: string;
  trainedOn: { playerMatches: number; players: number; from: string; to: string };
  edgeMargin: number;
  squads: { source: string; players: number; resolved: number; unresolved: number };
  topFoulers: PlayerRow[];
  board: FixtureBoard[];
  picks: CharacterPicks[];
};

export const getPlayers = () => read<PlayersData>("players.json");
