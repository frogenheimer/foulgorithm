import Link from "next/link";
import FixtureLive from "@/components/fixture/FixtureLive";
import Explorer from "@/components/explorer/Explorer";
import Sheet from "@/components/matchday/Sheet";
import SlipGrid from "@/components/fixture/SlipGrid";
import { PageHeader, SectionHead } from "@/components/kit";
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
  const sheet = matchday.fixtures.some((f) => `${f.home} v ${f.away}` === label);
  const shape = data.formations[label];
  const [home, away] = label.split(" v ");
  const kickoff = board?.kickoff ? new Date(board.kickoff) : null;

  return (
    <div className="stack">
      <div>
        <Link href="/" className={s.back}>
          &larr; Today
        </Link>
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
              title="What both clubs have actually been doing"
              note={`No model in any of these numbers: averages per match across ${matchday.seasons.join(" and ")}, and whether each line landed in the last ${matchday.window}, most recent on the left. Every figure can be checked against a scoreboard.`}
            />
            <Sheet data={matchday} only={label} />
          </section>
        )}

        <section>
          <SectionHead
            title="Every player in this game"
            note="Fouls conceded, fouls won, and both together. The most likely foulers lead; open the rest if you want the full squads. Open a row for the whole distribution behind the number."
          />
          <Explorer data={getExplorer()} only={`${home} v ${away}`} collapsedTo={10} />
        </section>
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
            title="What both clubs had been doing"
            note={`No model in any of these numbers: averages per match across ${a.matchday.seasons.join(" and ")}, as they stood before this game. Every figure can be checked against a scoreboard.`}
          />
          <Sheet
            data={{
              generatedAt: a.publishedAt,
              window: a.matchday.window,
              seasons: a.matchday.seasons,
              note: a.matchday.note,
              fixtures: [a.matchday.fixture],
            }}
            only={a.label}
          />
        </section>
      )}
    </div>
  );
}
