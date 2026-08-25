import Reliability from "@/components/record/Reliability";
import { DataTable } from "@/components/kit";
import { Callout, Card, Metric, MetricRow } from "@/components/kit";
import { getTrackRecord } from "@/lib/data";
import { modelName } from "@/lib/names";
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
        <MetricRow>
          <Metric
            label="Claims graded"
            value={String(d.gradedClaims)}
            tone={1}
            note={`${d.withoutOutcome} had no outcome to settle against`}
          />
          <Metric
            label="We said"
            value={pct(house.claimed)}
            tone={2}
            note="average probability across every claim"
          />
          <Metric
            label="It happened"
            value={pct(house.actual)}
            note={`${signed(house.gap)} against what we said`}
          />
        </MetricRow>
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
        flush
      >
        <DataTable
          rows={models}
          rowKey={([id]) => id}
          columns={[
            { key: "model", head: "Model", cell: ([id]) => modelName(id) },
            { key: "n", head: "Claims", numeric: true, cell: ([, m]) => m.n },
            { key: "said", head: "We said", numeric: true, cell: ([, m]) => pct(m.claimed) },
            { key: "got", head: "It happened", numeric: true, cell: ([, m]) => pct(m.actual) },
            {
              key: "gap",
              head: "Gap",
              numeric: true,
              cell: ([, m]) => (
                <span className={m.n < MEANINGFUL ? t.thin : Math.abs(m.gap) < 0.05 ? t.good : t.bad}>
                  {signed(m.gap)}
                </span>
              ),
            },
            { key: "ll", head: "Log loss", numeric: true, cell: ([, m]) => m.logLoss.toFixed(4) },
            { key: "ece", head: "Calibration error", numeric: true, cell: ([, m]) => m.ece.toFixed(4) },
          ]}
        />
      </Card>

      {house.calibration?.length > 0 && (
        <Card
          title="Were we right about how sure we were"
          subtitle="A hit rate cannot answer this. A model that calls everything 50% and lands half of them looks identical to one that knows what it is talking about."
        >
          <Reliability buckets={house.calibration} />
          <p className={styles.reading}>
            <strong>Early reading, and it points the wrong way.</strong> Almost every
            band comes in above what we said rather than below: 6% called and 14%
            happened, 36% called and 50% happened. Published probabilities carry a
            correction for measured OVERconfidence, and this is the opposite. It is
            {" "}
            {house.n} claims across two matchdays, which is far too few to act on, so
            nothing has been changed. If it holds over a few more rounds the correction
            is the first thing that should go.
          </p>
        </Card>
      )}

      <Card
        title="What the numbers mean"
        subtitle="The technical figure on the left, plain terms on the right. A hit rate on its own is the number a tipster shows you; these are the ones that keep us honest."
      >
        <dl className={t.twin}>
          <dt>We said {pct(house.claimed)}</dt>
          <dd>Across every bet we published, on average we claimed this chance.</dd>
          <dt>It happened {pct(house.actual)}</dt>
          <dd>Those things actually occurred this often. The closer these two sit,
          the more our numbers mean what they say.</dd>
          <dt>Gap</dt>
          <dd>The distance between the two. Near zero is the goal; negative means we
          were overconfident.</dd>
          <dt>Log loss</dt>
          <dd>How expensive our misses were. Being confident and wrong costs far more
          than being unsure and wrong, which is exactly how it should sting.</dd>
          <dt>Calibration error</dt>
          <dd>The same honesty check, band by band: when we say 30% it should happen
          about 30% of the time, and being too high in one band cannot hide behind
          being too low in another.</dd>
        </dl>
      </Card>
    </div>
  );
}
