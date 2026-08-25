/**
 * The club badge: generic on purpose, an instrument by design.
 *
 * A two-tone circle in the club's kit colours with a diagonal sash and a
 * three-letter code; crest artwork is deliberately absent (docs/39). The
 * interesting element is the temper ring: a thin outer arc filled by the
 * club's fouls per match against the league's hottest, so the badge wears
 * what this site is about. The ring never speaks alone: the chip's title
 * carries the number and rank in words.
 */

import { clubIdentity, rankFraction, temperFraction } from "@/lib/clubs";
import s from "./club.module.css";

const R = 19;
const CIRC = 2 * Math.PI * R;

export default function ClubChip({
  name,
  size = "md",
  temper,
}: {
  name: string;
  size?: "sm" | "md" | "lg";
  /** Fouls per match and this club's rank; max scales the ring exactly,
   *  and the rank approximates it when no scale is at hand. */
  temper?: { value: number; max?: number; rank: number; of: number };
}) {
  const c = clubIdentity(name);
  const frac = temper
    ? temper.max != null
      ? temperFraction(temper.value, temper.max)
      : rankFraction(temper.rank, temper.of)
    : null;
  const title = temper
    ? `${name}: ${temper.value} fouls per match, ${temper.rank} of ${temper.of}`
    : name;
  const clip = `club-clip-${c.code}`;

  return (
    <span className={`${s.chip} ${s[size]}`} title={title} role="img" aria-label={title}>
      <svg viewBox="0 0 40 40" aria-hidden focusable="false">
        {frac != null && <circle cx="20" cy="20" r={R} className={s.track} />}
        {frac != null && frac > 0 && (
          <circle
            cx="20"
            cy="20"
            r={R}
            className={s.arc}
            strokeDasharray={`${(frac * CIRC).toFixed(1)} ${CIRC.toFixed(1)}`}
            transform="rotate(-90 20 20)"
          />
        )}
        <clipPath id={clip}>
          <circle cx="20" cy="20" r="15.5" />
        </clipPath>
        <circle cx="20" cy="20" r="15.5" fill={c.primary} className={s.face} />
        <rect
          x="8"
          y="-8"
          width="9"
          height="56"
          fill={c.secondary}
          transform="rotate(35 20 20)"
          clipPath={`url(#${clip})`}
        />
        <text
          x="20"
          y="20"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={11}
          fill={c.ink}
          className={s.code}
        >
          {c.code}
        </text>
      </svg>
    </span>
  );
}
