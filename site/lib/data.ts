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
  /** Null where the season files carried results without cards. */
  cardsPerMatch: number | null;
  redsPerMatch: number | null;
  /** How often a given foul becomes a booking. Less confounded than per match. */
  cardsPerFoul: number | null;
  cardedMatches: number;
  vsLeague: number;
};

export type Appointment = { referee: string; fixture: string; kickoff: string };

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
  appointments: Appointment[];
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

/* ---------- the explorer ---------- */

/**
 * One player, every market, every line, every model.
 *
 * Probabilities are held as `[line][model]` arrays rather than nested objects.
 * The whole table ships to the browser so filtering is instant, and the array
 * form is roughly a third of the bytes of the readable equivalent.
 */
export type ExplorerRow = {
  player: string;
  fullName: string;
  position: string;
  team: string;
  opponent: string;
  fixture: string;
  kickoff: string;
  minutes: number;
  startProbability: number | null;
  confirmed: boolean;
  thin: boolean;
  expected: { committed: number; drawn: number; involvements: number };
  committed: number[][];
  drawn: number[][];
  involvements: number[][];
  pmf: { committed: number[]; drawn: number[]; involvements: number[] };
};

export type Explorer = {
  models: string[];
  lines: number[];
  markets: ("committed" | "drawn" | "involvements")[];
  house: string;
  rows: ExplorerRow[];
};

/* ---------- graded record ---------- */

export type ModelRecord = {
  n: number;
  claimed: number;
  actual: number;
  gap: number;
  logLoss: number;
  brier: number;
  ece: number;
  calibration: { from: number; to: number; n: number; predicted: number; observed: number }[];
};

export type TrackRecord = {
  generatedAt: string;
  settledPlayers: number;
  gradedClaims: number;
  withoutOutcome: number;
  models: Record<string, ModelRecord>;
};

/** Null until the first round has been graded, so the page can say so. */
export function getTrackRecord(): TrackRecord | null {
  try {
    return read<TrackRecord>("track-record.json");
  } catch {
    return null;
  }
}

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
  confirmed?: boolean;
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

export type TierLeg = {
  player: string; team: string; fixture: string; market: string;
  line: number; fouls: number; prob: number; outOf100: number;
  packProb: number; edge: number; band: string; thin: boolean;
};

export type OddsTier = {
  target: number; actualOdds: number; probability: number; outOf100: number;
  legs: TierLeg[];
};

export type CharacterPicks = {
  id: string; name: string; emotion: string; tagline: string;
  settings: Record<string, number>;
  picks: Pick[];
  combinedProb: number; combinedFair: number | null; averageProb: number;
  averageEdge: number; inBand: boolean;
  tiers: OddsTier[];
};

export type TicketLeg = {
  player: string; team: string; line: number; fouls: number; prob: number; market: string;
};

export type Ticket = {
  target: number; shape: string; probability: number; outOf100: number; fair: number;
  legs: TicketLeg[];
};

export type FixtureBoard = {
  key: string; home: string; away: string; kickoff: string; referee: string | null;
  lineupConfirmed?: boolean;
  teams: Record<string, PlayerRow[]>;
  tickets?: Record<string, Ticket[]>;
  stats?: Record<string, Record<string, { player: string; value: number }[]>>;
  summary?: {
    expectedFouls: number;
    topFouler: { player: string; team: string; outOf100: number };
    topWinner: { player: string; team: string; outOf100: number };
    players: number;
  };
  compare?: {
    rows: { label: string; home: number | null; away: number | null; higher: string | null }[];
    matches: { home: number; away: number };
  };
};

export type LeagueLeaders = Record<
  string,
  { label: string; leaders: { player: string; team: string; value: number; rank: number }[] }
>;

export type PlayersData = {
  generatedAt: string;
  trainedOn: { playerMatches: number; players: number; from: string; to: string };
  edgeMargin: number;
  squads: { source: string; players: number; resolved: number; unresolved: number };
  lineups: { source: string; confirmed: number; note: string };
  oddsTiers: number[];
  leagueLeaders: LeagueLeaders;
  topFoulers: PlayerRow[];
  board: FixtureBoard[];
  picks: CharacterPicks[];
  explorer: Explorer;
};

export const getPlayers = () => read<PlayersData>("players.json");
export const getExplorer = (): Explorer => getPlayers().explorer;

/* ---------- the stats sheet ---------- */

/**
 * Pure history. No model output appears in this file, and a Python test
 * enforces that, because the value of the page is that every number can be
 * checked against a scoreboard.
 */
export type HitRate = {
  line: number;
  /** Most recent first. Shorter than the window when the history is shorter. */
  hits: boolean[];
  n: number;
  rate: number | null;
};

export type TeamAverage = { label: string; value: number | null; matches: number };

export type DefensiveRow = {
  player: string;
  matches: number;
  minutes: number;
  foulsPer90: number;
  tacklesPer90: number;
  yellows: number;
  form: HitRate;
  watch: string[];
};

export type OffensiveRow = {
  player: string;
  matches: number;
  minutes: number;
  wonPer90: number;
  form: HitRate;
  formTwo: HitRate;
  watch: string[];
};

export type TeamSheet = {
  averages: Record<string, TeamAverage>;
  form: Record<string, HitRate | null>;
  division: string;
  players: { defensive: DefensiveRow[]; offensive: OffensiveRow[] };
};

export type MatchdayFixture = {
  home: string;
  away: string;
  kickoff: string;
  referee: {
    name: string | null;
    matches: number;
    foulsPerMatch: number | null;
    yellowsPerMatch: number | null;
    redsPerMatch: number | null;
  };
  teams: Record<string, TeamSheet>;
};

export type Matchday = {
  generatedAt: string;
  window: number;
  seasons: string[];
  note: string;
  fixtures: MatchdayFixture[];
};

export const getMatchday = () => read<Matchday>("matchday.json");
