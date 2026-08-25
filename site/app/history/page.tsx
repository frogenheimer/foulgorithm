import DistributionChart from "@/components/charts/DistributionChart";
import DotPlot from "@/components/charts/DotPlot";
import TrendChart from "@/components/charts/TrendChart";
import { Callout, Card, SectionHead, Metric, MetricRow } from "@/components/kit";
import { getOverview } from "@/lib/data";
import { count, fouls, shortDate, signedPct } from "@/lib/format";
import styles from "../round.module.css";
import tableStyles from "./history.module.css";

export const metadata = { title: "History · Foulgorithm" };

export default function History() {
  const d = getOverview();
  const h = d.headline;
  const cardsThen = d.seasons[0].cardsPerMatch;
  const cardsNow = d.seasons[d.seasons.length - 1].cardsPerMatch;
  const cardsChange = ((cardsNow - cardsThen) / cardsThen) * 100;
  const leagueMean =
    d.referees.reduce((a, r) => a + r.foulsPerMatch * r.matches, 0) /
    d.referees.reduce((a, r) => a + r.matches, 0);

  return (
    <div className="stack">
      <section className={styles.intro}>
        <h1 className={styles.h1}>History</h1>
        <p className={styles.lede}>
          The picture the model is built on: {count(d.coverage.matches)} Premier League matches
          across {d.coverage.seasons} seasons, {d.coverage.firstSeason} to {d.coverage.lastSeason}.
        </p>
      </section>

      <section>
        <MetricRow>
          <Metric
            label="Fouls per match now"
            value={String(h.foulsPerMatchNow)}
            tone={1}
            note={`${signedPct(h.changePct)} since ${d.coverage.firstSeason}`}
          />
          <Metric
            label="Cards per match now"
            value={String(cardsNow)}
            tone={2}
            note={`${signedPct(cardsChange)} since ${d.coverage.firstSeason}`}
          />
          <Metric label="Matches analysed" value={count(d.coverage.matches)} note={`${d.coverage.seasons} seasons`} />
          <Metric
            label="Away yellow penalty"
            value={signedPct(
              ((d.homeAway.awayYellows - d.homeAway.homeYellows) / d.homeAway.homeYellows) * 100,
              0
            )}
            note={`${d.homeAway.awayYellows} away vs ${d.homeAway.homeYellows} home`}
          />
        </MetricRow>
      </section>

      <section>
        <SectionHead title="Fouls are falling. Cards are not.">
          Both indexed to 100 in {d.coverage.firstSeason}, because fouls run at around 22 a match and
          cards at around 4. Sharing a raw axis would flatten cards along the floor, and separate
          axes would let the scales tell any story we liked.
        </SectionHead>
        <Card>
          <TrendChart seasons={d.seasons} />
        </Card>
        <Callout>
          Referees call {Math.abs(h.changePct)}% fewer fouls than in {d.coverage.firstSeason} while
          booking players {cardsChange.toFixed(0)}% more often. A foul today is far more likely to be
          punished than a foul in 2000, so old seasons are not equal evidence. The model applies
          exponential time decay with a 400 day half-life.
        </Callout>
      </section>

      <section>
        <SectionHead title="What a match actually looks like">
          Total fouls across all {count(d.coverage.matches)} matches. Discrete, right-skewed and
          bounded at zero, which is why the model fits count distributions rather than a normal curve.
        </SectionHead>
        <Card>
          <DistributionChart bins={d.distribution} />
        </Card>
      </section>

      <section>
        <SectionHead title={`Referees, ${d.recentWindow}`}>
          Raw fouls per match, minimum 20 appearances. An observation, not a rating: these numbers
          are confounded by which teams each referee was assigned. Separating the two needs a model
          that estimates both at once, and dividing one average by another is precisely the mistake
          this rebuild exists to avoid.
        </SectionHead>
        <Card title="Fouls per match by referee" subtitle={`All ${d.referees.length} referees against the league mean`}>
          <DotPlot
            unit="fouls per match"
            reference={leagueMean}
            referenceLabel="league mean"
            rows={d.referees.map((r) => ({
              label: r.referee,
              value: r.foulsPerMatch,
              sub: `${r.matches} matches · ${r.cardsPerMatch} yellows per match · ${signedPct(
                (r.vsLeague - 1) * 100
              )} vs league mean`,
            }))}
          />
        </Card>
      </section>

      <section>
        <SectionHead title={`Teams, ${d.recentWindow}`}>
          Fouls committed and fouls won per match, minimum 20 matches. These are separate
          behaviours, not one number: defenders and holding midfielders commit fouls, while dribblers
          and forwards draw them.
        </SectionHead>
        <Card flush>
          <div className="scroll-x">
            <table className={tableStyles.table}>
              <thead>
                <tr>
                  <th>Team</th>
                  <th className={tableStyles.num}>Matches</th>
                  <th className={tableStyles.num}>Committed</th>
                  <th className={tableStyles.num}>Drawn</th>
                  <th className={tableStyles.num}>Net</th>
                </tr>
              </thead>
              <tbody>
                {d.teams.map((t) => (
                  <tr key={t.team}>
                    <td>{t.team}</td>
                    <td className={tableStyles.num}>{t.matches}</td>
                    <td className={tableStyles.num}>{fouls(t.committedPerMatch)}</td>
                    <td className={tableStyles.num}>{fouls(t.drawnPerMatch)}</td>
                    <td className={tableStyles.num}>
                      {(t.committedPerMatch - t.drawnPerMatch >= 0 ? "+" : "") +
                        (t.committedPerMatch - t.drawnPerMatch).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <p className="muted" style={{ fontSize: "var(--t-sm)", marginTop: "var(--s3)" }}>
          Generated {shortDate(d.generatedAt)} from football-data.co.uk.
        </p>
      </section>
    </div>
  );
}
