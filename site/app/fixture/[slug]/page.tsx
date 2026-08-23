import Link from "next/link";
import Lineups from "@/components/fixture/Lineups";
import SlipGrid from "@/components/fixture/SlipGrid";
import { Card, MicroLabel, PageHeader, SectionHead } from "@/components/kit";
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

export default async function Fixture({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = getPlayers();
  const label = Object.keys(data.fixtureSlips).find((l) => fixtureSlug(l) === slug);
  if (!label) return null;

  const slips = data.fixtureSlips[label];
  const board = data.board.find((f) => `${f.home} v ${f.away}` === label);
  const sheet = getMatchday().fixtures.find((f) => `${f.home} v ${f.away}` === label);
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

            <section>
        <SectionHead
          title="The five, at matched risk"
          note={
            shape
              ? "Each character builds a combination to each price, from the eleven on the pitch. Swap anyone and all five rebuild. Same ladder for all of them, so a cautious one cannot look better by picking near-certainties and a bold one cannot look better by reaching."
              : "Each character builds a combination to each price. Same ladder for all five, so a cautious one cannot look better by picking near-certainties and a bold one cannot look better by reaching. Click any cell for its legs."
          }
        />
        {shape ? (
          <Lineups
            fixture={label}
            shapes={shape}
            explorer={getExplorer()}
            published={slips}
          />
        ) : (
          <SlipGrid slips={slips} characters={data.picks.map((p) => p.id)} />
        )}
      </section>

      {sheet && (
        <section>
          <SectionHead
            title="What both clubs have actually been doing"
            note={`Per match across ${getMatchday().seasons.join(" and ")}, with whether the line landed in each of the last ${getMatchday().window}. No model in any of these numbers.`}
          />
          <Card flush>
            <div className={s.compare}>
              <div className={s.compareHead}>
                <span className={s.club}>{home}</span>
                <span className={s.refBox}>
                  <MicroLabel>Referee</MicroLabel>
                  <span className={s.refName}>{sheet.referee.name ?? "Not appointed"}</span>
                  {sheet.referee.matches > 0 && (
                    <span className={s.refStat}>
                      {sheet.referee.foulsPerMatch} fouls · {sheet.referee.yellowsPerMatch} cards
                    </span>
                  )}
                </span>
                <span className={`${s.club} ${s.right}`}>{away}</span>
              </div>
              {Object.keys(sheet.teams[home]?.averages ?? {}).map((key) => {
                const h = sheet.teams[home]?.averages[key];
                const a = sheet.teams[away]?.averages[key];
                if (!h || !a) return null;
                return (
                  <div key={key} className={s.row}>
                    <span className={s.val}>{h.value ?? "—"}</span>
                    <span className={s.metric}>{h.label}</span>
                    <span className={`${s.val} ${s.right}`}>{a.value ?? "—"}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        </section>
      )}

    </div>
  );
}
