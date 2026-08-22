import { CHARACTER_COLOUR } from "@/components/characters/Portrait";
import type { Disagreement as Row } from "@/lib/data";
import s from "./disagreement.module.css";

/**
 * The centrepiece: where the five disagree.
 *
 * Every fixture on one axis, five markers each, the spread drawn between them.
 * The most interesting number the site produces and previously buried in a
 * table nobody scrolled to.
 *
 * Server component, so it costs no client JavaScript. The character colours are
 * a validated five-slot categorical set, and every marker carries a name in the
 * legend so colour never carries identity alone.
 */
export default function Disagreement({
  rows,
  characters,
}: {
  rows: Row[];
  characters: { id: string; name: string }[];
}) {
  if (!rows.length) return null;

  const values = rows.flatMap((r) => Object.values(r.means));
  const lo = Math.floor(Math.min(...values) * 2) / 2 - 0.3;
  const hi = Math.ceil(Math.max(...values) * 2) / 2 + 0.3;
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;

  const ticks: number[] = [];
  for (let t = Math.ceil(lo); t <= hi; t += 1) ticks.push(t);

  return (
    <figure className={s.wrap}>
      <div className={s.legend}>
        {characters.map((c) => (
          <span key={c.id} className={s.legendItem}>
            <i className={s.swatch} style={{ background: CHARACTER_COLOUR[c.id] }} />
            {c.name}
          </span>
        ))}
      </div>

      <div className={s.plot}>
        <div className={s.grid} aria-hidden="true">
          {ticks.map((t) => (
            <span key={t} className={s.gridline} style={{ left: `${x(t)}%` }}>
              <span className={s.tick}>{t}</span>
            </span>
          ))}
        </div>

        {rows.map((r) => {
          const vals = Object.values(r.means);
          const min = Math.min(...vals);
          const max = Math.max(...vals);
          return (
            <div key={r.key} className={s.row}>
              <span className={s.fixture}>
                {r.home} <span className={s.v}>v</span> {r.away}
              </span>
              <span className={s.track}>
                <span
                  className={s.span}
                  style={{ left: `${x(min)}%`, width: `${x(max) - x(min)}%` }}
                />
                {characters.map((c) => (
                  <span
                    key={c.id}
                    className={s.dot}
                    style={{ left: `${x(r.means[c.id])}%`, background: CHARACTER_COLOUR[c.id] }}
                    title={`${c.name}: ${r.means[c.id]}`}
                  />
                ))}
              </span>
              <span className={s.spread}>{r.spread.toFixed(2)}</span>
            </div>
          );
        })}
      </div>

      <figcaption className={s.caption}>
        Expected total fouls per fixture, one marker per model. The bar is the gap between the
        highest and lowest reading of identical evidence. A wide bar is a fixture the models
        genuinely cannot agree on.
      </figcaption>
    </figure>
  );
}
