/**
 * The club badge: generic on purpose, an instrument by design.
 *
 * The kit block (concept B, ratified 2026-08-25): a sharp square wearing the
 * kit as horizontal bands, shirt over shorts, with the three-letter code on
 * the shirt. Crest artwork is deliberately absent (docs/39); zero radius on
 * purpose, matching the site's chrome. The interesting element survives the
 * redesign: the temper gauge, now a thin strip printed along the badge's
 * foot, filled by the club's fouls per match against the league's hottest.
 * The gauge never speaks alone: the chip's title carries the number and
 * rank in words.
 */

import { clubIdentity, rankFraction, temperFraction } from "@/lib/clubs";
import s from "./club.module.css";

/** The badge's inner drawing area, in viewBox units. */
const X = 1.5;
const W = 37;
/** Where the shirt ends and the shorts begin. */
const SPLIT = 26;
/** The temper gauge strip, printed inside the badge's foot. */
const GAUGE_Y = 34.5;
const GAUGE_H = 3;

export default function ClubChip({
  name,
  size = "md",
  temper,
}: {
  name: string;
  size?: "sm" | "md" | "lg";
  /** Fouls per match and this club's rank; max scales the gauge exactly,
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

  return (
    <span className={`${s.chip} ${s[size]}`} title={title} role="img" aria-label={title}>
      <svg viewBox="0 0 40 40" aria-hidden focusable="false">
        <rect x={X} y={X} width={W} height={W} fill={c.primary} className={s.face} />
        <rect x={X} y={SPLIT} width={W} height={X + W - SPLIT} fill={c.secondary} />
        {frac != null && (
          <rect x={X} y={GAUGE_Y} width={W} height={GAUGE_H} className={s.gaugeTrack} />
        )}
        {frac != null && frac > 0 && (
          <rect
            x={X}
            y={GAUGE_Y}
            width={(frac * W).toFixed(1)}
            height={GAUGE_H}
            className={s.gaugeFill}
          />
        )}
        <text
          x="20"
          y={(X + SPLIT) / 2 + 0.5}
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
