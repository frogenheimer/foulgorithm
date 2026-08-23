/**
 * Did the things we called 60% happen 60% of the time.
 *
 * This is the only question that matters about a probability, and a hit rate
 * cannot answer it: a model that calls everything 50% and is right half the
 * time looks identical to one that knows what it is talking about.
 *
 * Bucket size is drawn, not tucked into a tooltip. A bucket holding three
 * claims will sit at 0% or 100% by luck alone, and shown at the same visual
 * weight as a bucket of eighty it would read as the model being wildly wrong
 * about confident calls rather than as us not having many yet.
 */

import s from "./record.module.css";

type Bucket = { lo: number; hi: number; n: number; predicted: number; observed: number };

/** Below this a bucket is decoration. Drawn, but never read as evidence. */
const MEANINGFUL = 20;

export default function Reliability({ buckets }: { buckets: Bucket[] }) {
  const shown = buckets.filter((b) => b.n > 0);
  if (!shown.length) return null;
  const widest = Math.max(...shown.map((b) => b.n));

  return (
    <div className={s.reliability}>
      <div className={s.relHead}>
        <span className={s.relBand}>Band</span>
        <span>We said, then what happened</span>
        <span>Said &rarr; got</span>
        <span className={s.relRight}>Claims</span>
      </div>

      {shown.map((b) => {
        const thin = b.n < MEANINGFUL;
        const gap = b.observed - b.predicted;
        return (
          <div key={b.lo} className={thin ? `${s.relRow} ${s.relThin}` : s.relRow}>
            <span className={s.relBand}>
              {Math.round(b.lo * 100)}&ndash;{Math.round(b.hi * 100)}%
            </span>

            <span className={s.track}>
              {/* Both marks on one axis, so the distance between them IS the
                  error. Two separate bars would need the reader to subtract. */}
              <span
                className={s.said}
                style={{ left: `${b.predicted * 100}%` }}
                title={`We said ${(b.predicted * 100).toFixed(0)}%`}
              />
              <span
                className={s.happened}
                style={{ left: `${b.observed * 100}%` }}
                title={`It happened ${(b.observed * 100).toFixed(0)}%`}
              />
              <span
                className={s.gap}
                style={{
                  left: `${Math.min(b.predicted, b.observed) * 100}%`,
                  width: `${Math.abs(gap) * 100}%`,
                }}
              />
            </span>

            <span className={s.relNums}>
              <span className={s.relSaid}>{Math.round(b.predicted * 100)}</span>
              <span className={s.relArrow}>&rarr;</span>
              <span className={s.relGot}>{Math.round(b.observed * 100)}</span>
            </span>

            <span className={s.relRight}>
              <span className={s.count} style={{ width: `${(b.n / widest) * 100}%` }} />
              <span className={s.countNum}>{b.n}</span>
            </span>
          </div>
        );
      })}

      <p className={s.relNote}>
        Rows in grey hold fewer than {MEANINGFUL} claims. At that size a band lands
        at 0% or 100% on luck alone, so read the width of the bar on the right
        before reading the gap on the left.
      </p>
    </div>
  );
}
