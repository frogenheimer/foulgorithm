/**
 * Did the line land, in each of the last few matches. Most recent on the left.
 *
 * The device is borrowed from printed tip sheets and it earns its place: a
 * reader can check it. "Four of the last five" is verifiable against a
 * scoreboard in a way a probability never is, which is why this page uses it
 * and the model pages do not.
 *
 * Filled and hollow rather than two colours, so it survives greyscale and
 * colour blindness without needing a legend.
 */

import s from "./matchday.module.css";

export default function Dots({
  hits,
  window,
  label,
}: {
  hits: boolean[];
  window: number;
  label: string;
}) {
  const missing = Math.max(0, window - hits.length);
  return (
    <span
      className={s.dots}
      role="img"
      aria-label={`${label}: ${hits.filter(Boolean).length} of ${hits.length}`}
    >
      {hits.map((hit, i) => (
        <span key={i} className={hit ? s.hit : s.miss} />
      ))}
      {/* Drawn as gaps, not as misses. Fewer matches played is not a run of
          failures, and padding it out would say it was. */}
      {Array.from({ length: missing }, (_, i) => (
        <span key={`gap${i}`} className={s.gap} />
      ))}
    </span>
  );
}
