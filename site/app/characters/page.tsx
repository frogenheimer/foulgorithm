import Link from "next/link";
import Portrait, { CHARACTER_COLOUR } from "@/components/characters/Portrait";
import { Callout, Card, SectionHead } from "@/components/ui";
import { getCharacters } from "@/lib/data";
import { count, fouls } from "@/lib/format";
import styles from "../round.module.css";
import c from "./characters.module.css";

export const metadata = { title: "The five · Foulgorithm" };

export default function Characters() {
  const data = getCharacters();
  const widest = data.disagreement[0];

  return (
    <div className="stack">
      <section className={styles.intro}>
        <h1 className={styles.h1}>The five</h1>
        <p className={styles.lede}>
          Five algorithms built around five temperaments, competing on the same fixtures with the
          same {count(data.trainedOn.matches)} matches of history. None of them is a joke model.
          Each is a research philosophy a real analyst could defend, which is why any of them can
          win.
        </p>
      </section>

      <section>
        <div className={c.grid}>
          {data.characters.map((ch) => (
            <Link key={ch.id} href={`/characters/${ch.id}`} className={c.card}>
              <div className={c.cardTop}>
                <Portrait id={ch.id} size={84} label={ch.name} />
                <div>
                  <h2 className={c.name} style={{ color: CHARACTER_COLOUR[ch.id] }}>
                    {ch.name}
                  </h2>
                  <p className={c.emotion}>{ch.emotion}</p>
                </div>
              </div>
              <p className={c.tagline}>&ldquo;{ch.tagline}&rdquo;</p>
              <dl className={c.spec}>
                <div>
                  <dt>Memory</dt>
                  <dd>{Math.round(ch.model.config.half_life_days)} day half-life</dd>
                </div>
                <div>
                  <dt>Blind spot</dt>
                  <dd className={c.weakness}>{ch.weakness}</dd>
                </div>
              </dl>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <SectionHead title="Where they disagree">
          Every character sees the same fixtures and the same history, so agreement is
          uninformative and disagreement is the whole point. Spread is the gap between the highest
          and lowest expected total.
        </SectionHead>
        <Card padded={false}>
          <div className="scroll-x">
            <table className={c.table}>
              <thead>
                <tr>
                  <th>Fixture</th>
                  {data.characters.map((ch) => (
                    <th key={ch.id} className={c.num}>
                      <span className={c.swatchRow}>
                        <i className={c.swatch} style={{ background: CHARACTER_COLOUR[ch.id] }} />
                        {ch.name}
                      </span>
                    </th>
                  ))}
                  <th className={c.num}>Spread</th>
                </tr>
              </thead>
              <tbody>
                {data.disagreement.map((d) => (
                  <tr key={d.key}>
                    <td className={c.fixture}>
                      {d.home} v {d.away}
                    </td>
                    {data.characters.map((ch) => {
                      const v = d.means[ch.id];
                      const extreme = ch.id === d.highest || ch.id === d.lowest;
                      return (
                        <td
                          key={ch.id}
                          className={c.num}
                          style={{
                            color: extreme ? CHARACTER_COLOUR[ch.id] : "var(--text-secondary)",
                            fontWeight: extreme ? 600 : 400,
                          }}
                        >
                          {fouls(v)}
                        </td>
                      );
                    })}
                    <td className={`${c.num} ${c.spread}`}>{fouls(d.spread)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Callout>
          Widest split this round is <strong>{widest.home} v {widest.away}</strong>, where{" "}
          {widest.highest} and {widest.lowest} are {fouls(widest.spread)} fouls apart. That gap is
          not noise: it is two different readings of the same evidence, and by Tuesday one of them
          will be closer.
        </Callout>
      </section>

      <section>
        <SectionHead title="No track record yet">
          The five were frozen on 21 August 2026 and have published nothing that has settled. Until
          enough predictions have been graded there is no leaderboard, because a leaderboard built
          on a handful of results would be noise presented as a ranking. Their backtest scores are
          on each character&apos;s page, clearly labelled as backtest rather than live.
        </SectionHead>
      </section>
    </div>
  );
}
