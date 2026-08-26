/**
 * The cup data contract, and the one rule the site enforces on its own.
 *
 * `showsHouseSheet` deliberately re-checks what the publisher already decided.
 * No player-level foul data exists for the Championship at any price, so a tie
 * involving one of those clubs must never render a player pick, and that is
 * too important to hold in exactly one place. If the JSON ever arrives with a
 * sheet attached to a cross-division tie, the page still refuses it.
 *
 * Kept apart from the cup pages themselves because `lib/data.ts` reads the
 * filesystem, so anything importing from it lands in the server bundle.
 */

export type Competition = "FA Cup" | "League Cup";

/** Which model output a tie is allowed to carry. See sources/cup_slate.py. */
export type TieKind = "full" | "total";

export type Division = "E0" | "E1";

export type SideRecord = {
  team: string;
  matches: number;
  /** "38 in the Premier League, 8 in the Championship". */
  spell: string | null;
  division: Division | null;
  crossedDivisions: boolean;
};

export type CompareRow = {
  label: string;
  home: number | null;
  away: number | null;
  higher: "home" | "away" | null;
  /** "+1.4 v Championship". Each side against its OWN division, never a shared one. */
  homeNote: string | null;
  awayNote: string | null;
  homeRank: string | null;
  awayRank: string | null;
};

export type CompareBlock = { title: string; rows: CompareRow[] };

export type RefereeBlock = {
  referee: string;
  matches: number;
  foulsPerMatch: number | null;
  cardsPerMatch: number | null;
  cardsPerFoul: number | null;
  thin: boolean;
  clubs: Record<"home" | "away", {
    matches: number;
    foulsPerMatch: number | null;
    yellowsPerMatch: number | null;
  }>;
  note: string;
};

export type MeetingRow = {
  date: string;
  season: string | null;
  division: string | null;
  home: string;
  away: string;
  homeGoals: number | null;
  awayGoals: number | null;
  homeFouls: number;
  awayFouls: number;
  homeYellows: number | null;
  awayYellows: number | null;
  referee: string | null;
};

export type MatchTotal = {
  expectedFouls: number;
  lines: { line: number; probOver: number; fairOddsOver: number }[];
  /** Clubs we could not price at all, named rather than hidden. */
  unpriced: string[];
  crossDivision: boolean;
  note: string;
};

export type CupPlayer = {
  player: string;
  position: string;
  shirt: number | null;
  appearances: number;
  minutes: number;
  foulsPer90: number | null;
  foulsWonPer90: number | null;
  tacklesPer90: number | null;
  fouls: number;
  foulsWon: number;
  tackles: number;
  yellows: number;
  reds: number;
  /** Under 450 minutes, so the rate is mostly noise. Shown, never hidden. */
  thin: boolean;
  /** "900 minutes in the Premier League, 450 in the Championship". */
  spell: string;
};

export type CupEleven = {
  team: string;
  /** False until the real sheet lands, roughly an hour before kickoff. */
  confirmed: boolean;
  /** The rotation warning. Present on every predicted eleven, absent on a real one. */
  note: string | null;
  short: boolean;
  /** The club's own formation, only ever from a real team sheet. */
  formation: string | null;
  /** Our own arrangement from position codes. Never a formation, and the page
   *  must not print it as one: a wing-back codes as a defender. */
  grouping: string | null;
  /** Goalkeeper first, then each line up the pitch. */
  lines: CupPlayer[][];
  bench: CupPlayer[];
  players: CupPlayer[];
};

export type CupLineups = {
  home: { team: string; formation: string | null; starters: string[] } | null;
  away: { team: string; formation: string | null; starters: string[] } | null;
};

export type CupTie = {
  slug: string;
  competition: Competition;
  round: string | null;
  home: string;
  away: string;
  kickoff: string;
  kind: TieKind;
  referee: RefereeBlock | null;
  /** True when no official has been appointed yet, which is most of the time. */
  refereePending: boolean;
  compare: CompareBlock[];
  crossDivision: string | null;
  record: { home: SideRecord; away: SideRecord };
  headToHead: {
    meetings: number;
    rows: MeetingRow[];
    fouls: Record<string, number>;
    totalFouls: number | null;
  };
  total: MatchTotal | null;
  /** Both elevens with their records. Null before any squad sweep has run. */
  players: { home: CupEleven; away: CupEleven } | null;
  houseSheet: { groups: unknown[] } | null;
  lineups: CupLineups | null;
};

export type CupData = {
  generatedAt: string;
  competition: Competition;
  /** Exhibition. Nothing here is graded, scored or carried into the record. */
  recorded: false;
  ties: CupTie[];
};

const PATHS: Record<Competition, string> = {
  "FA Cup": "/fa-cup",
  "League Cup": "/league-cup",
};

const FILES: Record<Competition, string> = {
  "FA Cup": "fa-cup.json",
  "League Cup": "league-cup.json",
};

export const COMPETITIONS: Competition[] = ["League Cup", "FA Cup"];

export const cupPath = (competition: Competition) => PATHS[competition];

export const cupFile = (competition: Competition) => FILES[competition];

export const cupHref = (tie: CupTie) => `${cupPath(tie.competition)}/${tie.slug}`;

export function cupFromSlug(segment: string): Competition | null {
  const found = COMPETITIONS.find((c) => PATHS[c] === `/${segment}`);
  return found ?? null;
}

/**
 * May this tie render player picks?
 *
 * Only a Premier League tie that actually has a sheet. A cross-division tie is
 * refused here as well as in the publisher: the second tier has no player foul
 * data at any price, so a pick there would be a positional prior wearing a
 * probability, and one guard for that is not enough.
 */
export function showsHouseSheet(tie: CupTie): boolean {
  return tie.kind === "full" && tie.houseSheet != null;
}

/** The sample line under a side's column. */
export function sideNote(side: SideRecord): string {
  if (!side.matches || !side.spell) return "No matches on record";
  return side.spell;
}

/** The card's one headline number, or nothing if no total was published. */
export function totalHeadline(tie: CupTie): string | null {
  if (!tie.total) return null;
  const base = `${Math.round(tie.total.expectedFouls)} expected fouls`;
  if (!tie.total.unpriced.length) return base;
  return `${base}, ${tie.total.unpriced.join(" and ")} priced at the league average`;
}
