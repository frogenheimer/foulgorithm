import Link from "next/link";
import FixtureLive from "@/components/fixture/FixtureLive";
import Explorer from "@/components/explorer/Explorer";
import Sheet from "@/components/matchday/Sheet";
import { PageHeader, SectionHead } from "@/components/kit";
import { fixtureSlug, getExplorer, getMatchday, getPlayers } from "@/lib/data";
import s from "./fixture.module.css";

export function generateStaticParams() {
  return Object.keys(getPlayers().fixtureSlips).map((label) => ({ slug: fixtureSlug(label) }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const label = Object.keys(getPlayers().fixtureSlips).find((l) => fixtureSlug(l) === slug);
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
  if (!label) return null;

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
