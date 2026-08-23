/**
 * The four dials that actually separate the five.
 *
 * They see identical evidence and differ only in how far they trust it: how far
 * back they look, how hard they shrink a thin sample, how much they read the
 * matchup, how far they push a deviation from average. Drawing those is more
 * honest than five portraits, which imply five different opinions where there
 * are five settings of one calculation.
 *
 * Each dial also marks where the other four sit, so a bar reads as a position
 * among five rather than as a score out of ten.
 */

import s from "./signature.module.css";

export type Settings = {
  half_life_days: number;
  prior_matches: number;
  opponent_weight: number;
  amplify: number;
};

type Dial = {
  key: keyof Settings;
  label: string;
  /** The observed range across the five, so the scale is theirs, not invented. */
  min: number;
  max: number;
  format: (v: number) => string;
};

const DIALS: Dial[] = [
  { key: "half_life_days", label: "Memory", min: 70, max: 1200, format: (v) => `${v}d` },
  { key: "prior_matches", label: "Caution", min: 2, max: 30, format: (v) => `${v}` },
  { key: "opponent_weight", label: "Matchup", min: 0.4, max: 1.6, format: (v) => v.toFixed(1) },
  { key: "amplify", label: "Boldness", min: 1.0, max: 1.3, format: (v) => v.toFixed(2) },
];

export default function Signature({
  id,
  settings,
  peers,
  big = false,
}: {
  id: string;
  settings: Settings;
  /** Every character's settings, for the peer marks. */
  peers?: Settings[];
  big?: boolean;
}) {
  const place = (d: Dial, v: number) =>
    Math.max(0, Math.min(1, (v - d.min) / (d.max - d.min))) * 100;

  return (
    <div
      className={big ? `${s.sig} ${s.big}` : s.sig}
      style={{ ["--char" as string]: `var(--ch-${id})` }}
    >
      {DIALS.map((d) => {
        const v = settings[d.key];
        return (
          <div key={d.key} className={s.dial}>
            <span className={s.label}>{d.label}</span>
            <span className={s.track}>
              {peers?.map((p, i) => (
                <span
                  key={i}
                  className={s.peer}
                  style={{ left: `${place(d, p[d.key])}%` }}
                  aria-hidden
                />
              ))}
              <span className={s.fill} style={{ right: `${100 - place(d, v)}%` }} />
            </span>
            <span className={s.value}>{d.format(v)}</span>
          </div>
        );
      })}
    </div>
  );
}
