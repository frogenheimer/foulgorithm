"use client";

/**
 * The distribution behind a headline number.
 *
 * "73 in 100 commit at least one foul" is one reading of a shape, and it hides
 * that the same player has a real chance of committing three. This draws the
 * whole thing, so the number in the table stops looking like the answer and
 * starts looking like a summary of one.
 *
 * Bars, not a curve. The quantity is a count of fouls and a curve implies
 * values between the bars that cannot happen.
 *
 * The bars are the model's raw shape. The ladder beside them uses the published
 * numbers, which carry a calibration correction the raw shape does not, so the
 * two differ by a point or two. The ladder wins, because it is what the table
 * shows and what a claim is graded against.
 */

import s from "./shape.module.css";

export default function Shape({
  pmf,
  lines,
  published,
  selected,
  noun,
}: {
  pmf: number[];
  /** The half-lines the site publishes, e.g. 0.5, 1.5. */
  lines: number[];
  /** Published probability per line, already calibration-corrected. */
  published: number[];
  selected: number;
  noun: string;
}) {
  const peak = Math.max(...pmf, 0.0001);

  return (
    <div className={s.wrap}>
      <div className={s.chart} role="img" aria-label={`Distribution of ${noun}`}>
        {pmf.map((p, k) => {
          const included = k > lines[selected];
          return (
            <div key={k} className={s.col}>
              <div className={s.barBox}>
                <div
                  className={included ? s.barOn : s.bar}
                  style={{ height: `${(p / peak) * 100}%` }}
                  title={`${k} ${noun}: ${(p * 100).toFixed(1)} in 100`}
                />
              </div>
              <div className={s.tick}>{k}</div>
              <div className={s.pct}>{Math.round(p * 100)}</div>
            </div>
          );
        })}
      </div>

      <table className={s.ladder}>
        <caption className={s.caption}>Every line we publish</caption>
        <tbody>
          {lines.map((l, i) => {
            // These come from the published, calibration-corrected numbers, not
            // from the raw shape above. Deriving them from the bars would put a
            // different figure here than the table shows for the same bet.
            const p = published[i];
            return (
              <tr key={l} className={i === selected ? s.rowOn : undefined}>
                <th scope="row">{l + 0.5}+</th>
                <td>{Math.round(p * 100)} in 100</td>
                <td className={s.price}>{p > 0 ? (1 / p).toFixed(2) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
