import { Callout, Card, StatTile, TileGrid } from "@/components/ui";
import { getTrackRecord } from "@/lib/data";
import styles from "../round.module.css";
import t from "./record.module.css";

export const metadata = { title: "Track record · Foulgorithm" };

/** Below this, a record is noise and the page says so rather than ranking it. */
const MEANINGFUL = 100;

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const signed = (n: number) => `${n >= 0 ? "+" : ""}${(n * 100).toFixed(1)}%`;

export default function Record() {
  const d = getTrackRecord();

  if (!d || Object.keys(d.models).length === 0) {
    return (
      <div className="stack">
        <section className={styles.intro}>
          <h1 className={styles.h1}>Track record</h1>
          <p className={styles.lede}>
            Every prediction we publish, graded after the match. Nothing is removed and
            nothing is hidden.
          </p>
        </section>
        <Callout>
          <strong>Nothing graded yet.</strong> The first round has not settled. This page
          will fill itself in rather than being written, and the losing weeks stay on it.
        </Callout>
      </div>
    );
  }

  const models = Object.entries(d.models).sort((a, b) => b[1].n - a[1].n);
  const [, house] = models.find(([id]) => id === "house") ?? models[0];
  const thin = models.filter(([, m]) => m.n < MEANINGFUL).length;

  return (
    <div className="stack">
      <section className={styles.intro}>
        <h1 className={styles.h1}>Track record</h1>
        <p className={styles.lede}>
          Every prediction we publish, graded after the match. {d.gradedClaims} claims
          settled across {d.settledPlayers} players. Nothing is removed and nothing is
          hidden, including the weeks that went badly.
        </p>
      </section>

      <section>
        <TileGrid>
          <StatTile
            label="Claims graded"
            value={String(d.gradedClaims)}
            tone="series1"
            note={`${d.withoutOutcome} had no outcome to settle against`}
          />
          <StatTile
            label="We said"
            value={pct(house.claimed)}
            tone="series2"
            note="average probability across every claim"
          />
          <StatTile
            label="It happened"
            value={pct(house.actual)}
            note={`${signed(house.gap)} against what we said`}
          />
        </TileGrid>
      </section>

      {thin > 0 && (
        <Callout>
          <strong>Most of this is still noise.</strong> {thin} of {models.length} models
          have under {MEANINGFUL} graded claims. At that size a 100% record and a 0% record
          say the same thing, which is nothing. They are shown anyway, because dropping the
          early sample is where a track record starts being edited.
        </Callout>
      )}

      <Card
        title="By model"
        subtitle="Claimed against actual is the honest column. A hit rate alone can hide a model that is confidently wrong."
        padded={false}
      >
        <div className={t.scroller}>
          <table className={t.table}>
            <thead>
              <tr>
                <th>Model</th>
                <th>Claims</th>
                <th>We said</th>
                <th>It happened</th>
                <th>Gap</th>
                <th>Log loss</th>
                <th>Calibration error</th>
              </tr>
            </thead>
            <tbody>
              {models.map(([id, m]) => {
                const noisy = m.n < MEANINGFUL;
                return (
                  <tr key={id} className={noisy ? t.thin : undefined}>
                    <td>{id}</td>
                    <td>{m.n}</td>
                    <td>{pct(m.claimed)}</td>
                    <td>{pct(m.actual)}</td>
                    <td className={noisy ? undefined : Math.abs(m.gap) < 0.05 ? t.good : t.bad}>
                      {signed(m.gap)}
                    </td>
                    <td>{m.logLoss.toFixed(4)}</td>
                    <td>{m.ece.toFixed(4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="What these columns mean"
        subtitle="Because a hit rate on its own is the number a tipster shows you."
      >
        <ul className={t.list}>
          <li>
            <strong>We said</strong>, the average probability across every claim. If we
            call twenty things at 30%, this reads 30%.
          </li>
          <li>
            <strong>It happened</strong>, how often those things actually occurred. Six of
            those twenty reads 30%, and that is a model working.
          </li>
          <li>
            <strong>Gap</strong>, the distance between the two. Near zero is the goal.
            Negative means we were overconfident.
          </li>
          <li>
            <strong>Log loss</strong>, how costly the misses were. It punishes being
            confident and wrong far harder than being unsure and wrong.
          </li>
          <li>
            <strong>Calibration error</strong>, the same gap measured within each
            confidence band rather than pooled, so being too high in one band and too low
            in another cannot cancel out and look correct.
          </li>
        </ul>
      </Card>
    </div>
  );
}
