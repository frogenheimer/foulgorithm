import Link from "next/link";
import Lineups from "@/components/fixture/Lineups";
import Explorer from "@/components/explorer/Explorer";
import FivePicks from "@/components/fixture/FivePicks";
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
 * One game, three questions, in the order a reader asks them: what are the
 * five backing here, what does the model say about every player, and what
 * have these clubs actually been doing. The odds-tier ladder that used to
 * lead the page is gone: the committed slates are the picks that score, so
 * they are the picks the page shows.
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
  const confirmed = (data.slates.confirmedFixtures ?? []).includes(label);
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

      <section>
        <SectionHead
          title={confirmed ? "The five on this game" : "The five on this game *"}
          note="The committed picks that count for the league table, side by side. A filled cell is a pick at that line, in that character's colour; the players they agree on rise to the top."
        />
        <FivePicks
          slates={data.slates}
          fixture={label}
          characters={data.picks.map((p) => ({ id: p.id, name: p.name }))}
          confirmed={confirmed}
        />
      </section>

      {shape && (
        <section>
          <SectionHead
            title="The eleven on the pitch"
            note="Drawn from the league's own formation lines, so a back three and a back four actually look different."
          />
          <Lineups fixture={label} shapes={shape} explorer={getExplorer()} published={data.fixtureSlips[label]} />
        </section>
      )}

      <section>
        <SectionHead
          title="Every player in this game"
          note="Fouls conceded, fouls won, and both together. Open a row for the whole distribution behind the number, not just the headline."
        />
        <Explorer data={getExplorer()} only={`${home} v ${away}`} />
      </section>

      {sheet && (
        <section>
          <SectionHead
            title="What both clubs have actually been doing"
            note={`No model in any of these numbers: averages per match across ${matchday.seasons.join(" and ")}, and whether each line landed in the last ${matchday.window}, most recent on the left. Every figure can be checked against a scoreboard.`}
          />
          <Sheet data={matchday} only={label} />
        </section>
      )}
    </div>
  );
}
