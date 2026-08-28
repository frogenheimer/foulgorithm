import { Callout, Card, SectionHead } from "@/components/kit";
import { getPlayers, getRound } from "@/lib/data";
import { contractCopy } from "@/lib/contract";
import { count } from "@/lib/format";
import styles from "../round.module.css";
import prose from "./methodology.module.css";

export const metadata = { title: "Methodology · Foulgorithm" };

export default function Methodology() {
  const round = getRound();
  const contract = contractCopy(getPlayers().slates.shapes);

  return (
    <div className="stack">
      <section className={styles.intro}>
        <h1 className={styles.h1}>Methodology</h1>
        <p className={styles.lede}>
          What the model does, what it cannot do, and where it has been wrong. If this page ever
          reads like marketing, it is broken.
        </p>
      </section>

      <section>
        <SectionHead title="What we predict" />
        <div className={prose.body}>
          <p>
            Three markets: <strong>total fouls in a match</strong>, and per player,{" "}
            <strong>fouls committed</strong> and <strong>fouls won</strong>, plus their sum as
            involvements. Every model returns a full probability distribution rather than a single
            number, so every line is priced from one fit and the answers cannot contradict each
            other across lines.
          </p>
          <p>
            Prices shown are <strong>fair odds</strong>: the reciprocal of our probability, with no
            margin. They are not bookmaker prices and they are not a claim that a bookmaker is
            wrong. We publish no odds comparison because no free, licensed source of player-market
            odds exists.
          </p>
        </div>
      </section>

      <section>
        <SectionHead title="How it works" />
        <div className={prose.body}>
          <p>
            For a player, four things go into the number. His own rate per 90 minutes, with recent
            matches counting more and thin records pulled toward what players in his position do.
            How long he is likely to play, split into starting, coming off the bench and not
            featuring, because those are three different matches. Who he is playing, measured from
            match data that is current to the latest round. And around the resulting average, a
            spread, because the honest answer to how many fouls is never one number.
          </p>
          <p>
            Where we have not watched a player&rsquo;s matches, his rate leans on the league&rsquo;s
            own official season totals, and the site marks those numbers as estimates rather than
            letting them sit beside a watched record looking identical. Published probabilities are
            corrected only at the lines where a correction measurably helps held-out predictions;
            the rest are published exactly as the model says them.
          </p>
          <p>
            Then eleven characters read the same evidence and disagree on purpose: different
            memory lengths, different trust in thin samples, different faith in the matchup. Their
            numbers are opinions by design, which is why the house figure is shown beside every
            pick. {contract.bets} They are scored like a league: {contract.scoring}
          </p>
          <p>
            Match totals work the same way at team level: committed and drawn rates per club,
            recent form weighted, a hard-shrunk referee factor, and a negative binomial over the
            result, because foul counts are overdispersed and the tails are exactly what a line is
            priced on.
          </p>
        </div>
        <Card title="Current champion">
          <dl className={prose.spec}>
            <div>
              <dt>Model</dt>
              <dd>
                {round.model.id} {round.model.version}
              </dd>
            </div>
            <div>
              <dt>Trained on</dt>
              <dd>
                {count(round.trainedOn.matches)} matches, {round.trainedOn.firstSeason} to{" "}
                {round.trainedOn.lastSeason}
              </dd>
            </div>
            <div>
              <dt>Half-life</dt>
              <dd>{round.model.config.half_life_days} days</dd>
            </div>
            <div>
              <dt>Walk-forward log loss</dt>
              <dd>0.5749, against 0.6028 for a league-average baseline</dd>
            </div>
            <div>
              <dt>Mean absolute error</dt>
              <dd>3.93 fouls, against 4.14 for the baseline</dd>
            </div>
            <div>
              <dt>Calibration error</dt>
              <dd>0.0069 over 6,080 predictions</dd>
            </div>
          </dl>
        </Card>
      </section>

      <section>
        <SectionHead title="How we avoid fooling ourselves" />
        <div className={prose.body}>
          <p>
            Every fact carries the timestamp at which it became publicly knowable. Features are built
            as of a moment, and may only use facts known before it. Models never touch the database,
            so they cannot reach past that filter.
          </p>
          <p>
            The test suite includes a deliberately cheating model that reads the answer it is being
            asked to predict. If the harness ever stops catching it, the build fails. There is also a
            synthetic dataset containing no signal at all, where any model that beats the average is
            by definition leaking.
          </p>
          <p>
            This matters because the previous version of this project failed exactly here: it
            evaluated itself using season averages that already included the matches being predicted,
            and reported a success rate that meant nothing.
          </p>
        </div>
      </section>

      <section>
        <SectionHead title="What this model cannot do" />
        <div className={prose.body}>
          <ul className={prose.list}>
            <li>
              <strong>No value claims.</strong> We cannot systematically compare our probabilities
              against bookmaker prices, so we do not claim an edge over them. Calibration, whether
              the things we call 60% happen 60% of the time, is the measure we hold ourselves to.
            </li>
            <li>
              <strong>Per-match player history has a gap.</strong> The archive behind player rates
              stops in September 2025. The league&rsquo;s official season totals fill most of what
              that costs, measured at 78% on committed and 87% on won, and every settled round now
              adds real per-match rows, but the gap itself cannot be recovered.
            </li>
            <li>
              <strong>The track record is young.</strong> The first predictions were published for
              the round beginning 21 August 2026, and the site says plainly when a sample is too
              small to mean anything.
            </li>
            <li>
              <strong>A lot of irreducible noise.</strong> Mean error on match totals is about 3.9
              fouls against an average of 22. Most of that gap is not going away.
            </li>
          </ul>
        </div>
      </section>

      <section>
        <SectionHead title="Where we have already been wrong" />
        <Callout>
          The plan assumed lopsided fixtures would produce <em>more</em> fouls, because an underdog
          spends the match defending. The data says the opposite, clearly: the most even quartile of
          fixtures averages 22.69 fouls and the most lopsided 19.92. A dominant team keeps the ball,
          and you cannot foul someone who has it. That hypothesis is recorded as wrong in the
          modelling log rather than quietly deleted.
        </Callout>
      </section>
    </div>
  );
}
