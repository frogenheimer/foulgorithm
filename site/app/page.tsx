import FixtureCard from "@/components/FixtureCard";
import { Callout, SectionHead, StatTile, TileGrid } from "@/components/ui";
import { getRound } from "@/lib/data";
import { count, fouls, kickoffDay, shortDate } from "@/lib/format";
import styles from "./round.module.css";

export default function ThisRound() {
  const round = getRound();
  const fixtures = round.fixtures;

  const byDay = fixtures.reduce<Record<string, typeof fixtures>>((acc, f) => {
    const day = kickoffDay(f.kickoff);
    (acc[day] ||= []).push(f);
    return acc;
  }, {});

  const mean = fixtures.reduce((a, f) => a + f.expectedFouls, 0) / fixtures.length;
  const busiest = [...fixtures].sort((a, b) => b.expectedFouls - a.expectedFouls)[0];
  const quietest = [...fixtures].sort((a, b) => a.expectedFouls - b.expectedFouls)[0];
  const thin = fixtures.filter((f) => f.thinEvidence.length).length;

  return (
    <div className="stack">
      <section className={styles.intro}>
        <h1 className={styles.h1}>This round</h1>
        <p className={styles.lede}>
          Predicted total fouls for the next {fixtures.length} Premier League fixtures, from a model
          trained on {count(round.trainedOn.matches)} matches between {round.trainedOn.firstSeason}{" "}
          and {round.trainedOn.lastSeason}. Prices shown are <strong>fair odds</strong> derived from
          our own probabilities, with no margin. They are not bookmaker prices.
        </p>
      </section>

      <section>
        <TileGrid>
          <StatTile label="Fixtures" value={String(fixtures.length)} note={`Generated ${shortDate(round.generatedAt)}`} />
          <StatTile label="Average expected fouls" value={fouls(mean)} note="Across the round" />
          <StatTile
            label="Busiest"
            value={fouls(busiest.expectedFouls)}
            note={`${busiest.home} v ${busiest.away}`}
          />
          <StatTile
            label="Quietest"
            value={fouls(quietest.expectedFouls)}
            note={`${quietest.home} v ${quietest.away}`}
          />
        </TileGrid>
      </section>

      <section>
        <Callout>
          The model predicts <strong>match totals only</strong>. Player markets, meaning fouls
          committed and fouls drawn per player, need player-level match data that our only viable
          free source cannot currently supply. Those markets are defined and waiting, not forgotten.
          {thin > 0 && (
            <>
              {" "}
              {thin} of {fixtures.length} fixtures this round carry a thin-evidence flag and are
              marked as such.
            </>
          )}
        </Callout>
      </section>

      {Object.entries(byDay).map(([day, dayFixtures]) => (
        <section key={day}>
          <SectionHead title={day} />
          <div className={styles.grid}>
            {dayFixtures.map((f) => (
              <FixtureCard key={`${f.home}-${f.away}`} fixture={f} />
            ))}
          </div>
        </section>
      ))}

      <section>
        <SectionHead title="What these numbers are worth">
          Over 6,080 walk-forward predictions this model beats a league-average baseline by 4.64% on
          log loss, with mean absolute error of 3.93 fouls against the baseline&apos;s 4.14. That is a
          real but modest edge, which is what match totals should look like: they are the most
          efficiently priced market we touch. Read the{" "}
          <a href="/methodology" className={styles.link}>
            methodology
          </a>{" "}
          before treating any of this as useful.
        </SectionHead>
      </section>
    </div>
  );
}
