import Link from "next/link";
import FixtureLive from "@/components/fixture/FixtureLive";
import Explorer from "@/components/explorer/Explorer";
import SlipRail from "@/components/five/SlipRail";
import GameSheet from "@/components/matchday/GameSheet";
import { PageHeader, SectionHead } from "@/components/kit";
import ClubChip from "@/components/kit/ClubChip";
import type { Bet, Explorer as ExplorerData, Formations, HouseSheet as Sheet, MatchdayFixture } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import {
  fixtureSlug,
  getArchivedFixtures,
  getExplorer,
  getMatchday,
  getPlayers,
} from "@/lib/data";
import s from "./fixture.module.css";

export function generateStaticParams() {
  const current = Object.keys(getPlayers().fixtureSlips).map((label) => fixtureSlug(label));
  const archived = Object.keys(getArchivedFixtures());
  return [...new Set([...current, ...archived])].map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const label =
    Object.keys(getPlayers().fixtureSlips).find((l) => fixtureSlug(l) === slug) ??
    getArchivedFixtures()[slug]?.label;
  return { title: label ? `${label} · Foulgorithm` : "Fixture · Foulgorithm" };
}

/** Everything one fixture page needs, whichever store it came from. */
type FixtureView = {
  label: string;
  kickoff: string | null;
  referee: string | null;
  /** Named on hand-fed cup ties; null on league games. */
  competition: string | null;
  lineupNote: string | null;
  houseSheet: Sheet | null;
  bets: Record<string, Record<string, Bet>> | null;
  characters: { id: string; name: string; generation?: number }[];
  explorer: ExplorerData;
  formations: Formations[string] | undefined;
  sheetFixture: MatchdayFixture | null;
  outcomes: Outcomes | null;
  result: {
    score: [number, number] | null;
    fouls: [number | null, number | null];
    cards: [number | null, number | null];
  } | null;
};

function liveView(label: string): FixtureView {
  const data = getPlayers();
  const board = data.board.find((f) => `${f.home} v ${f.away}` === label);
  const matchday = getMatchday();
  return {
    label,
    kickoff: board?.kickoff ?? null,
    referee: board?.referee ?? null,
    competition: board?.competition ?? null,
    lineupNote: board?.lineupConfirmed
      ? "XI confirmed"
      : "XI predicted from current squads",
    houseSheet: board?.houseSheet ?? null,
    bets: data.slates.byGame?.[label] ?? null,
    characters: data.picks.map((p) => ({ id: p.id, name: p.name, generation: p.generation })),
    explorer: getExplorer(),
    formations: data.formations[label],
    sheetFixture:
      matchday.fixtures.find((f) => `${f.home} v ${f.away}` === label) ?? null,
    outcomes: null,
    result: null,
  };
}

function archivedView(slug: string): FixtureView | null {
  const a = getArchivedFixtures()[slug];
  if (!a) return null;
  const r = a.result?.result;
  return {
    label: a.label,
    kickoff: a.kickoff || null,
    referee: a.referee,
    competition: a.competition ?? null,
    lineupNote: null,
    houseSheet: a.houseSheet ?? null,
    bets: a.bets ?? null,
    characters: a.characters,
    explorer: a.explorer,
    formations: a.formations ?? undefined,
    sheetFixture: a.matchday?.fixture ?? null,
    outcomes: a.outcomes ?? {},
    result: a.result
      ? {
          score: a.result.score,
          fouls: [r?.home?.fouls ?? null, r?.away?.fouls ?? null],
          cards: [r?.home?.cards ?? null, r?.away?.cards ?? null],
        }
      : null,
  };
}

/**
 * ONE template for every state of a game (docs/39): upcoming, live and
 * played render the same page in the same order. The only thing a result
 * changes is the results strip at the top, actual beside what we said, and
 * the outcome marks that flow through the bets. The data
 * arrives from the live payload while the round is on and from the frozen
 * archive afterwards; the reader never needs to know which.
 */
export default async function Fixture({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = getPlayers();
  const liveLabel = Object.keys(data.fixtureSlips).find((l) => fixtureSlug(l) === slug);
  const v = liveLabel ? liveView(liveLabel) : archivedView(slug);
  if (!v) return null;

  const [home, away] = v.label.split(" v ");
  const kickoff = v.kickoff ? new Date(v.kickoff) : null;
  const played = Boolean(v.result);
  const outcomes = v.outcomes ?? undefined;
  const weSaid = data.expectedTotals?.[v.label]?.expected;
  const confirmedSet = new Set(data.slates.confirmedFixtures ?? []);
  const medals = Object.fromEntries(
    (data.standings ?? [])
      .filter((r) => r.played > 0)
      .slice(0, 3)
      .map((r, i) => [r.id, (i + 1) as 1 | 2 | 3])
  );
  const totalFouls =
    v.result && v.result.fouls[0] != null && v.result.fouls[1] != null
      ? (v.result.fouls[0] ?? 0) + (v.result.fouls[1] ?? 0)
      : null;

  return (
    <div className="stack">
      <div>
        <Link href={v.competition ? "/cup" : "/"} className={s.back}>
          &larr; {v.competition ? "The cups" : "Today"}
        </Link>
        <div className={s.clubs} aria-hidden>
          <ClubChip name={home} size="lg" temper={temperOf(v.sheetFixture, home)} />
          <ClubChip name={away} size="lg" temper={temperOf(v.sheetFixture, away)} />
        </div>
        <PageHeader
          kicker={
            played
              ? "Full time"
              : v.competition
                ? `${v.competition} · exhibition`
                : "Fixture"
          }
          title={v.label}
          lede={
            <>
              {kickoff &&
                `${played ? "Played " : ""}${kickoff.toLocaleString("en-GB", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  hour: "2-digit",
                  minute: "2-digit",
                })}`}
              {v.referee && ` · ${v.referee}`}
              {!played && v.lineupNote && ` · ${v.lineupNote}`}
            </>
          }
        />
      </div>

      {played && v.result && (
        <div className={s.resultStrip}>
          <span className={s.resultScore}>
            {v.result.score ? `${v.result.score[0]}\u2013${v.result.score[1]}` : "\u2014"}
          </span>
          <span className={s.resultStat}>
            Fouls{" "}
            <strong>
              {v.result.fouls[0] ?? "\u2014"}
              {"\u2013"}
              {v.result.fouls[1] ?? "\u2014"}
            </strong>
          </span>
          <span className={s.resultStat}>
            Cards{" "}
            <strong>
              {v.result.cards[0] ?? "\u2014"}
              {"\u2013"}
              {v.result.cards[1] ?? "\u2014"}
            </strong>
          </span>
          {weSaid != null && totalFouls != null && (
            <span className={s.resultStat}>
              We said <strong>{weSaid.toFixed(0)}</strong>, it was <strong>{totalFouls}</strong>
            </span>
          )}
        </div>
      )}

      <FixtureLive
        fixture={v.label}
        shapes={v.formations}
        explorer={v.explorer}
        houseSheet={v.houseSheet}
      >
        {v.sheetFixture && (
          <section>
            <SectionHead
              title={played ? "The game sheet, as it stood" : "The game sheet"}
              note="Both clubs face to face on everything we hold, with league ranks and recent form, then the players likely to be on the pitch. Actual numbers can be checked against a scoreboard; Expected ones are our model's, and the sheet says which is showing."
            />
            <GameSheet
              fixture={v.sheetFixture}
              rows={v.explorer.rows.filter((r) => r.fixture === v.label)}
              outcomes={outcomes}
              gameOver={played}
            />
          </section>
        )}

        <section>
          <SectionHead
            title="Every player in this game"
            note="Fouls conceded, fouls won, and both together. The most likely foulers lead; open the rest if you want the full squads. Open a row for the whole distribution behind the number."
          />
          <Explorer data={v.explorer} only={v.label} collapsedTo={10} />
        </section>

        {v.bets && (
          <section>
            <SectionHead
              title={
                played
                  ? "The bets, marked"
                  : confirmedSet.has(v.label)
                    ? "The bets on this game"
                    : "The bets on this game *"
              }
              note={
                played
                  ? "Three bets from every competitor, exactly as committed before kickoff. A tick landed, a cross did not, and a struck-through leg is void: its player had no graded outcome, so the bet settled on its remaining legs."
                  : v.competition
                    ? "Exhibition. The same three bets from every competitor, published for the ride: nothing here is recorded, graded or scored in the league table. The team-sheet feed is league-only, so these are built from predicted elevens."
                    : "Three bets from every competitor, the five and the challengers alike, the ones the league table scores. * means the eleven is not confirmed yet: these regenerate automatically when the team sheets land, an hour before kickoff, and each bet\u2019s last version before kickoff is the one that counts."
              }
            />
            <SlipRail
              bets={v.bets}
              characters={v.characters}
              shapes={data.slates.shapes}
              outcomes={outcomes}
              gameOver={played}
              medals={medals}
            />
          </section>
        )}
      </FixtureLive>
    </div>
  );
}

/** The temper ring\u2019s inputs for one club, from a matchday sheet if present. */
function temperOf(
  fixture:
    | {
        teams: Record<
          string,
          { averages: Record<string, { value: number | null; rank?: number; rankOf?: number }> }
        >;
      }
    | null
    | undefined,
  club: string
) {
  const held = fixture?.teams?.[club]?.averages?.foulsFor;
  if (!held || held.value == null || held.rank == null || held.rankOf == null) return undefined;
  return { value: held.value, rank: held.rank, of: held.rankOf };
}
