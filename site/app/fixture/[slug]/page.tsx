import Link from "next/link";
import FixtureLive from "@/components/fixture/FixtureLive";
import Explorer from "@/components/explorer/Explorer";
import Bets from "@/components/five/Bets";
import GameSheet from "@/components/matchday/GameSheet";
import SlipGrid from "@/components/fixture/SlipGrid";
import { PageHeader, SectionHead } from "@/components/kit";
import ClubChip from "@/components/kit/ClubChip";
import type { ArchivedFixture } from "@/lib/data";
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

/**
 * One game, in the order a reader asks about it: who is on the pitch, what
 * does the model say about every player, what have these clubs actually been
 * doing, and, at the foot, the ladder of what each character would combine at
 * each price. Swaps on the pitch rebuild that ladder, so both ends of the page
 * share state through FixtureLive. The five's committed picks live on The five
 * page as a matrix, side by side across the whole round, not repeated here.
 */
export default async function Fixture({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = getPlayers();
  const label = Object.keys(data.fixtureSlips).find((l) => fixtureSlug(l) === slug);
  if (!label) {
    const archived = getArchivedFixtures()[slug];
    return archived ? <PastFixture a={archived} /> : null;
  }

  const board = data.board.find((f) => `${f.home} v ${f.away}` === label);
  const matchday = getMatchday();
  const sheetFixture = matchday.fixtures.find((f) => `${f.home} v ${f.away}` === label);
  const sheet = Boolean(sheetFixture);
  const shape = data.formations[label];
  const [home, away] = label.split(" v ");
  const kickoff = board?.kickoff ? new Date(board.kickoff) : null;

  return (
    <div className="stack">
      <div>
        <Link href="/" className={s.back}>
          &larr; Today
        </Link>
        <div className={s.clubs} aria-hidden>
          <ClubChip name={home} size="lg" temper={temperOf(sheetFixture, home)} />
          <ClubChip name={away} size="lg" temper={temperOf(sheetFixture, away)} />
        </div>
        <PageHeader
          title={label}
          lede={
            <>
              {kickoff &&
                kickoff.toLocaleString("en-GB", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              {board?.referee && ` · ${board.referee}`}
              {board?.lineupConfirmed ? " · XI confirmed" : " · XI predicted from current squads"}
            </>
          }
        />
      </div>

      <FixtureLive
        fixture={label}
        shapes={shape}
        explorer={getExplorer()}
        published={data.fixtureSlips[label] ?? {}}
        characters={data.picks.map((p) => ({ id: p.id, name: p.name }))}
      >
        {sheet && (
          <section>
            <SectionHead
              title="The game sheet"
              note={`Both clubs face to face on everything we hold, averages across ${matchday.seasons.join(" and ")} with league ranks, then the players likely to be on the pitch. Actual numbers can be checked against a scoreboard; Expected ones are our model's, and the sheet says which is showing.`}
            />
            <GameSheet
              fixture={sheetFixture!}
              rows={getExplorer().rows.filter((r) => r.fixture === label)}
            />
          </section>
        )}

        <section>
          <SectionHead
            title="Every player in this game"
            note="Fouls conceded, fouls won, and both together. The most likely foulers lead; open the rest if you want the full squads. Open a row for the whole distribution behind the number."
          />
          <Explorer data={getExplorer()} only={`${home} v ${away}`} collapsedTo={10} />
        </section>

        {data.slates.byGame?.[label] && (
          <section>
            <SectionHead
              title={
                (data.slates.confirmedFixtures ?? []).includes(label)
                  ? "The bets on this game"
                  : "The bets on this game *"
              }
              note="Three bets from every competitor, the five and the challengers alike, the ones the league table scores. * means the eleven is not confirmed yet: these regenerate automatically when the team sheets land, an hour before kickoff, and each bet's last version before kickoff is the one that counts."
            />
            <Bets
              bets={data.slates.byGame[label]}
              characters={data.picks.map((p) => ({ id: p.id, name: p.name, generation: p.generation }))}
              shapes={data.slates.shapes}
            />
          </section>
        )}
      </FixtureLive>
    </div>
  );
}

/**
 * A played fixture, from the archive: what was on the board when the game
 * started, marked against what happened. The ladder leads, because the
 * reader's question changed at full time from "what would they combine" to
 * "and did it come in". Nothing here regenerates; the page is the record.
 */
function PastFixture({ a }: { a: ArchivedFixture }) {
  const kickoff = a.kickoff ? new Date(a.kickoff) : null;
  const score = a.result?.score;
  const fouls = a.result?.result;
  const [home, away] = a.label.split(" v ");
  const homeFouls = fouls?.home?.fouls;
  const awayFouls = fouls?.away?.fouls;

  return (
    <div className="stack">
      <div>
        <Link href="/" className={s.back}>
          &larr; Today
        </Link>
        <div className={s.clubs} aria-hidden>
          <ClubChip name={home} size="lg" temper={temperOf(a.matchday?.fixture, home)} />
          <ClubChip name={away} size="lg" temper={temperOf(a.matchday?.fixture, away)} />
        </div>
        <PageHeader
          title={a.label}
          lede={
            <>
              {kickoff &&
                `Played ${kickoff.toLocaleString("en-GB", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  hour: "2-digit",
                  minute: "2-digit",
                })}`}
              {a.referee && ` · ${a.referee}`}
              {score && ` · ${home} ${score[0]}–${score[1]} ${away}`}
              {homeFouls != null && awayFouls != null && ` · Fouls ${homeFouls}–${awayFouls}`}
            </>
          }
        />
      </div>

      {a.bets && (
        <section>
          <SectionHead
            title="The bets, marked"
            note="Three bets per character, the ones the league table scores, exactly as committed before kickoff. A tick is a leg that landed, a cross one that did not, and a struck-through leg is void: its player had no graded outcome, so the bet settled on its remaining legs."
          />
          <Bets
            bets={a.bets}
            characters={a.characters}
            shapes={getPlayers().slates.shapes}
            outcomes={a.outcomes ?? {}}
            gameOver={Boolean(a.result)}
          />
        </section>
      )}

      <section>
        <SectionHead
          title="The ladder, marked"
          note="The prices exactly as published before kickoff, never rebuilt, with every combination and leg marked against what happened. Came in means every leg landed; no means at least one did not; open means a leg has no graded outcome yet."
        />
        <SlipGrid
          slips={a.ladder}
          characters={a.characters.map((c) => c.id)}
          names={Object.fromEntries(a.characters.map((c) => [c.id, c.name]))}
          outcomes={a.outcomes ?? {}}
        />
      </section>

      <section>
        <SectionHead
          title="Every player in this game"
          note="The numbers as published before kickoff. The most likely foulers lead; open the rest for the full squads."
        />
        <Explorer data={a.explorer} only={a.label} collapsedTo={10} />
      </section>

      {a.matchday && (
        <section>
          <SectionHead
            title="The game sheet, as it stood"
            note={`Both clubs face to face on everything we held before kickoff, averages across ${a.matchday.seasons.join(" and ")}, then the players as we rated them. Actual numbers were checkable against a scoreboard; Expected ones were our model's.`}
          />
          <GameSheet fixture={a.matchday.fixture} rows={a.explorer.rows} />
        </section>
      )}
    </div>
  );
}

/** The temper ring's inputs for one club, from a matchday sheet if present. */
function temperOf(fixture: { teams: Record<string, { averages: Record<string, { value: number | null; rank?: number; rankOf?: number }> }> } | null | undefined, club: string) {
  const held = fixture?.teams?.[club]?.averages?.foulsFor;
  if (!held || held.value == null || held.rank == null || held.rankOf == null) return undefined;
  return { value: held.value, rank: held.rank, of: held.rankOf };
}
