/**
 * A probability as 100 squares, of which some are filled.
 *
 * Natural frequencies are read correctly far more often than percentages,
 * which is the whole reason this is not a number in a cell. Gigerenzer's work
 * on this is the reason the site says "68 of 100" rather than "68%" wherever
 * it has the room.
 *
 * Ten by ten rather than a bar, because a bar invites reading the length as a
 * quantity of fouls. This reads as a count of matches, which is what it is.
 */

import s from "./explorer.module.css";

export default function Bars({ p }: { p: number }) {
  const filled = Math.round(Math.max(0, Math.min(1, p)) * 100);
  return (
    <span className={s.bars}>
      <span className={s.grid} aria-hidden>
        {Array.from({ length: 100 }, (_, i) => (
          <span key={i} className={i < filled ? s.cellOn : s.cell} />
        ))}
      </span>
      <span className={s.barsValue}>
        <strong>{filled}</strong>
        <span className={s.barsUnit}>of 100</span>
      </span>
    </span>
  );
}
