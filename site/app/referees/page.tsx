import Table from "@/components/referees/Table";
import { Callout, Metric, MetricRow } from "@/components/kit";
import { getOverview } from "@/lib/data";
import s from "../round.module.css";

export const metadata = { title: "Referees · Foulgorithm" };

export default function Referees() {
  const d = getOverview();
  const refs = d.referees;
  const total = refs.reduce((a, r) => a + r.matches, 0);
  const mean = refs.reduce((a, r) => a + r.foulsPerMatch * r.matches, 0) / total;
  const strictest = [...refs]
    .filter((r) => r.cardsPerFoul !== null)
    .sort((a, b) => (b.cardsPerFoul ?? 0) - (a.cardsPerFoul ?? 0))[0];
  const busiest = [...refs].sort((a, b) => b.foulsPerMatch - a.foulsPerMatch)[0];
  const spread = busiest.foulsPerMatch - refs[refs.length - 1].foulsPerMatch;

  return (
    <div className="stack">
      <section className={s.intro}>
        <h1 className={s.h1}>Referees</h1>
        <p className={s.lede}>
          What each referee&apos;s matches actually looked like, and who has which fixture
          this round. {refs.length} referees over {d.recentWindow}.
        </p>
      </section>

      <Callout>
        <strong>None of this is a referee effect.</strong> A referee handed more derbies
        shows more fouls and more cards without being any stricter, and separating the two
        needs a model that knows which teams he had. These are observations. The foul model
        does not use them, deliberately, because a raw ratio of averages is exactly the kind
        of confounded number that looks like a signal and is not.
      </Callout>

      <section>
        <MetricRow>
          <Metric
            label="League average"
            value={mean.toFixed(1)}
            tone={1}
            note="fouls per match across every referee here"
          />
          <Metric
            label="Widest spread"
            value={`${spread.toFixed(1)} fouls`}
            tone={2}
            note={`${busiest.referee} down to ${refs[refs.length - 1].referee}`}
          />
          <Metric
            label="Quickest to book"
            value={strictest?.cardsPerFoul ? `${(strictest.cardsPerFoul * 100).toFixed(1)}%` : "—"}
            note={strictest ? `${strictest.referee}, share of fouls that draw a card` : undefined}
          />
        </MetricRow>
      </section>

      <Table rows={refs} appointments={d.appointments} />

      <section className={s.footNote}>
        <p>
          <strong>Fouls booked</strong> is the column worth reading, and it is the share of
          a referee&apos;s fouls that draw a card. Cards per match rises with how physical a
          game was, so it partly measures the fixtures he drew rather than the man. This
          asks how likely he is to book an offence he has already given.
        </p>
        <p>
          It also separates them less than it looks. Cards per match spreads 42% across
          these {refs.length} referees, fouls per match 20%, and fouls booked 26%. Most of
          what looks like a strict referee is a referee who was given scrappier matches.
        </p>
        <p>
          A minimum of 20 matches applies, so a referee new to the league has no row rather
          than a number built on four games. Where a season&apos;s file carried results
          without cards, those matches are excluded from the card columns rather than
          counted as zero, which would read as never booking anyone.
        </p>
      </section>
    </div>
  );
}
