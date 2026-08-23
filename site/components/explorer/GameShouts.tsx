"use client";

/**
 * Each character's one call per game, drawn from both markets at once.
 *
 * Previously a character picked from fouls conceded and fouls won separately,
 * which meant the strongest read in a game could be crowded out by a weaker one
 * simply because it sat in the other table. The pick is now the best thing that
 * character sees in that fixture, whichever market it comes from.
 *
 * "Best" is that character's probability minus what the other four say about the
 * same bet. A high probability everyone agrees on is not a shout, it is a
 * consensus, and there is no reason to listen to any particular character for it.
 */

import { useMemo, useState } from "react";
import type { Explorer as Data, ExplorerRow } from "@/lib/data";
import s from "./shouts.module.css";

type Market = "committed" | "drawn" | "involvements";

const VERB: Record<Market, string> = {
  committed: "concedes",
  drawn: "wins",
  involvements: "is involved in",
};

/** Ignore anything under this: an edge on a coin flip is not a read. */
const FLOOR = 0.25;

type Shout = {
  row: ExplorerRow;
  market: Market;
  line: number;
  p: number;
  pack: number;
};

export default function GameShouts({ data }: { data: Data }) {
  const fixtures = useMemo(
    () => Array.from(new Set(data.rows.map((r) => r.fixture))).sort(),
    [data.rows]
  );
  const [fixture, setFixture] = useState(fixtures[0] ?? "");

  const shouts = useMemo(() => {
    const inGame = data.rows.filter((r) => r.fixture === fixture);
    return data.models.map((model, mi) => {
      const found: Shout[] = [];
      for (const row of inGame) {
        for (const market of ["committed", "drawn"] as Market[]) {
          row[market].forEach((probs, li) => {
            const p = probs[mi];
            if (p < FLOOR) return;
            const others = probs.filter((_, i) => i !== mi);
            const pack = others.reduce((a, b) => a + b, 0) / others.length;
            found.push({ row, market, line: data.lines[li], p, pack });
          });
        }
      }
      found.sort((a, b) => b.p - b.pack - (a.p - a.pack));
      return { model, shout: found[0] ?? null };
    });
  }, [data, fixture]);

  if (!fixtures.length) return null;

  return (
    <div className={s.wrap}>
      <div className={s.head}>
        <h2 className={s.title}>What each of them likes here</h2>
        <select
          className={s.select}
          value={fixture}
          onChange={(e) => setFixture(e.target.value)}
          aria-label="Fixture"
        >
          {fixtures.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      <p className={s.note}>
        One call each, taken from fouls conceded and fouls won together rather than
        market by market. Ranked by how far that character sits from the other four,
        because a number everyone agrees on is a consensus, not a shout.
      </p>

      <div className={s.grid}>
        {shouts.map(({ model, shout }) => (
          <article
            key={model}
            className={s.card}
            style={{ ["--char" as string]: `var(--ch-${model})` }}
          >
            <header className={s.cardHead}>
              <span className={s.swatch} aria-hidden />
              <span className={s.model}>{model}</span>
              {model === data.house && <span className={s.house}>house</span>}
            </header>

            {shout ? (
              <>
                <p className={s.call}>
                  <strong>{shout.row.player}</strong> {VERB[shout.market]}{" "}
                  <strong>{shout.line + 0.5}+</strong>
                </p>
                <p className={s.freq}>
                  <span className={s.big}>{Math.round(shout.p * 100)}</span>
                  <span className={s.of}>in 100</span>
                </p>
                <dl className={s.facts}>
                  <div>
                    <dt>Others say</dt>
                    <dd>{Math.round(shout.pack * 100)}</dd>
                  </div>
                  <div>
                    <dt>Gap</dt>
                    <dd className={shout.p > shout.pack ? s.up : s.down}>
                      {shout.p > shout.pack ? "+" : ""}
                      {Math.round((shout.p - shout.pack) * 100)}
                    </dd>
                  </div>
                  <div>
                    <dt>Fair price</dt>
                    <dd>{(1 / shout.p).toFixed(2)}</dd>
                  </div>
                </dl>
                {shout.row.thin && (
                  <p className={s.caveat}>Thin evidence on this player.</p>
                )}
              </>
            ) : (
              <p className={s.nothing}>
                Nothing here it likes enough to call. That is an answer, not a gap.
              </p>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
