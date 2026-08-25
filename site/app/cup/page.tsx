import CompetitionSwitcher from "@/components/home/CompetitionSwitcher";
import CupCard from "@/components/home/CupCard";
import { Callout, PageHeader } from "@/components/kit";
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
            const stars = (f.houseSheet?.groups ?? []).flatMap((g) =>
              g.picks
                .filter((p) => p.star)
                .map((p) => ({ player: p.player, outOf100: p.outOf100, line: g.line, market: g.market }))
            );
            return (
              <CupCard
                key={f.key}
                label={label}
                href={`/fixture/${fixtureSlug(label)}-cup`}
                competition={f.competition ?? "Cup"}
                kickoffLine={kickoff.toLocaleString("en-GB", {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                  timeZone: "Europe/London",
                })}
                expected={
                  d?.expectedTotals?.[`${label} (${f.competition ?? "Cup"})`]?.expected ??
                  d?.expectedTotals?.[label]?.expected
                }
                call={f.summary?.topFouler ?? null}
                lineupConfirmed={f.lineupConfirmed}
                stars={stars}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
