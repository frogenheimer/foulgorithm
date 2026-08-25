import Link from "next/link";
import CompetitionSwitcher from "@/components/home/CompetitionSwitcher";
import { Callout, PageHeader } from "@/components/kit";
import ClubChip from "@/components/kit/ClubChip";
import { fixtureSlug, getCup } from "@/lib/data";
import s from "./cup.module.css";

export const metadata = { title: "Cups · Foulgorithm" };

/**
 * The cup slate: exhibition ties between clubs we hold real data for,
 * predicted by the same engine and rendered on the same fixture template,
 * but recorded nowhere. These pages are only reachable from the switcher,
 * so the league stays the league (docs/38).
 */
export default function Cup() {
  const d = getCup();
  const board = d?.board ?? [];

  return (
    <div className="stack">
      <CompetitionSwitcher active="cup" />
      <PageHeader
        kicker="Exhibition · beta"
        title="The cups"
        lede={
          <>
            Cup ties between clubs the engine holds real data for, predicted exactly like
            a league game. Exhibition only: nothing here is recorded, graded or scored in
            the league table.
          </>
        }
      />

      {board.length === 0 && (
        <Callout>
          <strong>No cup tie on the slate.</strong> Fixtures are added by hand when two
          of our twenty clubs draw each other. This page fills itself in when one lands.
        </Callout>
      )}

      {board.length > 0 && (
        <div className={s.grid}>
          {board.map((f) => {
            const label = `${f.home} v ${f.away}`;
            const kickoff = new Date(f.kickoff);
            const expected = d?.expectedTotals?.[label]?.expected;
            const call = f.summary?.topFouler;
            return (
              <Link key={f.key} href={`/fixture/${fixtureSlug(label)}`} className={s.card}>
                <span className={s.day}>
                  {f.competition ?? "Cup"}
                  {" · "}
                  {kickoff.toLocaleString("en-GB", {
                    weekday: "short",
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span className={s.clubs} aria-hidden>
                  <ClubChip name={f.home} />
                  <ClubChip name={f.away} />
                </span>
                <span className={s.title}>{label}</span>
                {expected != null && (
                  <span className={s.fouls}>
                    {Math.round(expected)}
                    <em>expected fouls</em>
                  </span>
                )}
                {call && (
                  <span className={s.call}>
                    {call.player} commits 1+ · {call.outOf100}/100
                  </span>
                )}
                <span className={s.note}>
                  {f.lineupConfirmed ? "XI confirmed" : "XI predicted from current squads"}
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
