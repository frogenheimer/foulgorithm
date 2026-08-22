import type { FixtureBoard } from "@/lib/data";
import s from "./h2h.module.css";

/**
 * Mirrored comparison. The pattern a reader can decide from.
 *
 * Two separate tables make you hold a number in your head while you find its
 * opposite. One row with a shared centre label means the comparison happens by
 * looking across, which is the whole point.
 *
 * The split bar carries the comparison visually and the numbers stay for anyone
 * who wants them. Both sides are the same blue: a red-versus-green split would
 * read as good-versus-bad, and more fouls is neither.
 */
export default function HeadToHead({ fixture }: { fixture: FixtureBoard }) {
  const rows = fixture.compare?.rows ?? [];
  if (!rows.length) return null;

  return (
    <div className={s.wrap}>
      <div className={s.head}>
        <span className={s.team}>{fixture.home}</span>
        <span className={s.vs}>versus</span>
        <span className={`${s.team} ${s.away}`}>{fixture.away}</span>
      </div>

      <dl className={s.rows}>
        {rows.map((r) => {
          const h = r.home ?? 0;
          const a = r.away ?? 0;
          const total = h + a || 1;
          const known = r.home !== null && r.away !== null;
          return (
            <div key={r.label} className={s.row}>
              <dd className={`${s.value} ${r.higher === "home" ? s.lead : ""}`}>
                {r.home === null ? <span className={s.none}>no data</span> : r.home}
              </dd>

              <div className={s.middle}>
                <dt className={s.label}>{r.label}</dt>
                {known && (
                  <div className={s.bar} aria-hidden="true">
                    <span className={s.left} style={{ width: `${(h / total) * 100}%` }} />
                    <span className={s.right} style={{ width: `${(a / total) * 100}%` }} />
                  </div>
                )}
              </div>

              <dd className={`${s.value} ${s.alignRight} ${r.higher === "away" ? s.lead : ""}`}>
                {r.away === null ? <span className={s.none}>no data</span> : r.away}
              </dd>
            </div>
          );
        })}
      </dl>

      <p className={s.note}>
        Team rates from the last 400 days.{" "}
        {fixture.compare?.matches.home === 0 || fixture.compare?.matches.away === 0
          ? "One side is newly promoted and has no top-flight record, which is a fact rather than a gap. Their players fall back to positional averages."
          : `Based on ${fixture.compare?.matches.home} and ${fixture.compare?.matches.away} matches.`}
      </p>
    </div>
  );
}
