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
  /** What the model expects in THIS match. Not an average of anything. */
  expected: { committed: number; drawn: number; involvements: number };
  /**
   * Where the number mostly comes from.
   *
   * "promoted-club" means we have never seen this player in this division and
   * are leaning on how his club fouled in the one below. "season-totals"
   * means no watched matches sit behind the number yet, only the league's
   * official totals for him. Both are estimates and must not sit beside a
   * real record looking identical.
   */
  priorFrom?: "own-record" | "position" | "promoted-club" | "season-totals" | null;
  clubFactor?: number | null;
  /** His plain per-90 across everything we hold. Null if he has never played. */
  career: {
    committed: number | null;
    drawn: number | null;
    involvements: number | null;
    nineties: number;
  } | null;
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
  calibration: { lo: number; hi: number; n: number; predicted: number; observed: number }[];
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

export type CharacterSettings = {
  half_life_days: number;
  prior_matches: number;
  opponent_weight: number;
  dispersion: number;
  amplify: number;
  reads_head_to_head?: boolean;
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
    expected_fouls?: number;
    opponentFactor: number;
    headToHeadFactor?: number;
    refereeFactor: number;
    effectiveMatches: number;
    startProbability?: number | null;
    minutesIfStarting?: number;
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

export type SlipLeg = {
  player: string;
  fullName?: string;
  team: string;
  fixture: string;
  market: "committed" | "drawn";
  line: number;
  fouls: number;
  prob: number;
  outOf100: number;
  packProb: number;
  edge: number;
  band: string;
  thin: boolean;
  /**
   * Why this character backed this leg, in his own voice.
   *
   * Optional because it is generated alongside the probability it describes.
   * A slip rebuilt in the browser after a lineup change has new numbers and no
   * sentence, and showing the old sentence next to a new number is precisely
   * the drift the generator exists to prevent. Absent is better than stale.
   */
  reason?: string;
};

export type Slip = {
  target: number;
  targetLabel: string;
  actualOdds: number;
  probability: number;
  outOf100: number;
  /** Derived from the fair price by removing a margin. An estimate, never observed. */
  estimatedOffer: number;
  legCount: number;
  /** Share of the combination the margin removes. Compounds per leg. */
  takeOut: number;
  floor: number;
  legs: SlipLeg[];
};

export type Spot = {
  player: string;
  position: string;
  /** "Right Full Back", "Centre Defensive Midfielder". Places a slot left or right. */
  detail: string;
  shirt: number | null;
  captain?: boolean;
};

export type TeamShape = {
  formation: string | null;
  /** True when the eleven is our guess rather than the league's team sheet. */
  predicted?: boolean;
  /** Goalkeeper first, then each line up the pitch. Published by the league. */
  lines: Spot[][];
  bench: Spot[];
};

/** fixture label -> club -> shape */
export type Formations = Record<string, Record<string, TeamShape>>;

export type FixtureOption = {
  band: string;
  character: string;
  /** The name as written. Not the id with a CSS capitalize on it. */
  characterName: string;
  tier: string;
  odds: number;
  outOf100: number;
  /**
   * The blended five-model number for the same combination. The character's
   * figure is an opinion on purpose; this is the stated baseline beside it,
   * so a reader never has to guess which of the two carries the calibration.
   * Absent on cards versioned before 2026-08-24.
   */
  houseOutOf100?: number;
  totalFouls: number;
  gap: number;
  /** How many of the five models sit behind the card. */
  backers?: number;
  /** False while this card was built on a predicted eleven; the picks
   *  regenerate automatically when the team sheets land at T-60. */
  lineupsConfirmed?: boolean;
  legs: { player: string; fouls: number; market: string; outOf100: number; backers?: number }[];
};

export type SettledOption = Omit<FixtureOption, "legs"> & {
  /** True landed, false missed, null not settled yet. */
  landed: boolean | null;
  legs: (FixtureOption["legs"][number] & { landed: boolean | null })[];
};

export type BestPick = {
  character: string;
  tier: string;
  odds: number;
  outOf100: number;
  totalFouls: number;
  /** How far this character sits from the other four on the same legs. */
  gap: number;
  legs: { player: string; fouls: number; market: "committed" | "drawn"; outOf100: number }[];
};

/** fixture label -> character id -> ladder of slips */
export type FixtureSlips = Record<string, Record<string, Slip[]>>;

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
  fixtureSlips: FixtureSlips;
  bestPicks: Record<string, BestPick>;
  /** What we said each fixture would produce, kept after it is played. */
  expectedTotals: Record<string, { expected: number; publishedAt: string }>;
  /** Past cards, each leg marked landed / missed / undecided. */
  settledCards: Record<string, { version: number; options: SettledOption[] }>;
  /** Up to three calls per fixture, short price to long. */
  fixtureOptions: Record<string, FixtureOption[]>;
  formations: Formations;
  slates: Slates;
  standings: Standing[];
};

/** "Arsenal v Coventry" -> "arsenal-coventry" */
export const fixtureSlug = (label: string) =>
  label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

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

/* ---------- the season ---------- */

export type TeamResult = { fouls?: number; won?: number; cards?: number };

export type SeasonFixture = {
  matchweek: number;
  home: string;
  away: string;
  kickoff: string;
  /** "U" upcoming, "L" live, "C" complete, from the league's own feed. */
  status: string;
  referee: string | null;
  score?: [number, number];
  /** What actually happened. Team-level, from the league, not an estimate. */
  result?: { home?: TeamResult; away?: TeamResult };
};

export type Season = {
  generatedAt: string;
  matchweeks: number[];
  currentMatchweek: number;
  fixtures: SeasonFixture[];
};

export const getSeason = () => read<Season>("season.json");

/* ---------- teams ---------- */

export type TeamPlayer = {
  player: string;
  position: string;
  matches: number;
  minutes: number;
  foulsPer90: number;
  wonPer90: number;
  tacklesPer90: number;
  cards: number;
  /** Under three full matches of playing time, so the rates are weak evidence. */
  thin: boolean;
};

export type TableRow = {
  team: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  /** From the longer window, not the table season. */
  foulsPerMatch: number | null;
  foulsWonPerMatch: number | null;
  cardsPerMatch: number | null;
  rateMatches: number;
  players: TeamPlayer[];
  /** Squad members with no minutes in the window, so no rate to show. */
  noHistory: number;
};

export type Standing = {
  id: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  legsLanded: number;
  legsMissed: number;
  difference: number;
  points: number;
};

export type SlateShape = { key: string; label: string; legs: number };

/** One committed bet: a shape filled with legs, or null where the character
 *  passed because the game's pool could not fill it. */
export type Bet = { legs: SlipLeg[]; label: string } | null;

export type Slates = {
  shapes: SlateShape[];
  /** fixture label -> character id -> slate key -> the bet. Three bets per
   *  character per game; the contract, see docs/38. */
  byGame: Record<string, Record<string, Record<string, Bet>>>;
  /** Fixtures whose confirmed elevens are in. Bets for the rest regenerate
   *  automatically when the team sheets land, an hour before kickoff. */
  confirmedFixtures?: string[];
  note: string;
};

export type Teams = {
  generatedAt: string;
  seasons: string[];
  /** The season the points and positions cover. */
  tableSeason: string;
  /** The window the foul rates cover, which is longer. */
  rateSeasons: string;
  table: TableRow[];
};

export const getTeams = () => read<Teams>("teams.json");

/* ---------- the fixture archive ---------- */

/** One played (or pending) fixture's page data, frozen at its last
 *  pre-kickoff publish. Written by the pipeline's publish/archive.py;
 *  outcomes and the result arrive when settle runs after the game. */
export type ArchivedFixture = {
  label: string;
  slug: string;
  publishedAt: string;
  kickoff: string;
  referee: string | null;
  characters: { id: string; name: string }[];
  ladder: Record<string, Slip[]>;
  /** This game's fifteen bets (character id -> slate key -> bet), when the
   *  payload was per-game. Absent on archives from the round-wide era. */
  bets?: Record<string, Record<string, Bet>> | null;
  formations: Record<string, TeamShape> | null;
  explorer: Explorer;
  matchday: {
    window: number;
    seasons: string[];
    note: string;
    fixture: MatchdayFixture;
  } | null;
  outcomes?: Record<string, { won: boolean; observed?: number | null }>;
  result?: {
    score: [number, number] | null;
    result: Record<string, { fouls?: number; won?: number; cards?: number } | null> | null;
    matchweek?: number | null;
  } | null;
};

/** slug -> archived fixture. Empty when the pipeline has archived nothing. */
export function getArchivedFixtures(): Record<string, ArchivedFixture> {
  const dir = path.join(process.cwd(), "public/data/fixtures");
  if (!fs.existsSync(dir)) return {};
  const out: Record<string, ArchivedFixture> = {};
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith(".json")) continue;
    const held = JSON.parse(fs.readFileSync(path.join(dir, file), "utf8")) as ArchivedFixture;
    out[held.slug] = held;
  }
  return out;
}
